"""
Adaptive quiz engine using SQLite-backed routing.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "jobs.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "scripts", "schema.sql")

DOMAIN_DETECT_THRESHOLD = 25
STRONG_THRESHOLD = 0.75
PARTIAL_THRESHOLD = 0.45


class QuizEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self) -> None:
        needs_seed = not os.path.exists(self.db_path)
        conn = self._conn()
        try:
            with open(SCHEMA_PATH, encoding="utf-8") as fh:
                conn.executescript(fh.read())

            if not needs_seed:
                row = conn.execute("SELECT COUNT(*) FROM questions").fetchone()
                needs_seed = row[0] == 0

            if needs_seed:
                self._seed_questions(conn)
        finally:
            conn.close()

    def _seed_questions(self, conn):
        files = sorted(glob.glob(os.path.join(BASE_DIR, "data", "questions_part*.json")))
        for filepath in files:
            with open(filepath, encoding="utf-8") as fh:
                raw = json.load(fh)

            if isinstance(raw, list):
                questions = raw
            elif isinstance(raw, dict):
                for key in ("questions", "data", "items"):
                    if key in raw:
                        questions = raw[key]
                        break
                else:
                    questions = list(raw.values())[0]
            else:
                questions = []

            for q in questions:
                qid = q.get("id") or q.get("question_id")
                stem = q.get("stem") or q.get("question") or q.get("question_text")
                if not qid or not stem:
                    continue

                routing = q.get("routing", {})

                conn.execute(
                    """
                    INSERT OR REPLACE INTO questions (
                        id, gate, domain_scope, question_type,
                        role_targets, difficulty, experience_level_target,
                        stem, context, answer_mode,
                        options, practical_task, scoring,
                        ai_evaluation_prompt, job_evidence,
                        route_strong, route_partial, route_weak,
                        estimated_minutes
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        qid,
                        q.get("gate", 0),
                        q.get("domain_scope", "ALL"),
                        q.get("question_type", "multiple_choice"),
                        json.dumps(q.get("role_targets", [])),
                        q.get("difficulty", "beginner"),
                        q.get("experience_level_target", "any"),
                        stem,
                        q.get("context"),
                        q.get("answer_mode", "single_choice"),
                        json.dumps(q["options"]) if q.get("options") else None,
                        json.dumps(q["practical_task"]) if q.get("practical_task") else None,
                        json.dumps(q.get("scoring", {})),
                        q.get("ai_evaluation_prompt"),
                        json.dumps(q.get("job_evidence", [])),
                        routing.get("strong"),
                        routing.get("partial"),
                        routing.get("weak"),
                        q.get("estimated_minutes"),
                    ),
                )
        conn.commit()

    def _q(self, row) -> Optional[dict]:
        if not row:
            return None
        q = dict(row)
        for field in ("options", "practical_task", "scoring", "job_evidence", "role_targets"):
            if q.get(field) and isinstance(q[field], str):
                try:
                    q[field] = json.loads(q[field])
                except Exception:
                    pass
        return q

    def create_session(self, user_id: Optional[str] = None) -> dict:
        conn = self._conn()
        try:
            sid = str(uuid.uuid4())
            gate0 = conn.execute(
                "SELECT id FROM questions WHERE gate=0 AND is_active=1 LIMIT 1"
            ).fetchone()
            first_q_id = gate0[0] if gate0 else None
            conn.execute(
                """
                INSERT INTO quiz_sessions (id, user_id, current_question_id)
                VALUES (?,?,?)
                """,
                (sid, user_id, first_q_id),
            )
            conn.commit()
            return {"session_id": sid, "first_question_id": first_q_id}
        finally:
            conn.close()

    def load_session(self, session_id: str) -> dict:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM quiz_sessions WHERE id=?", (session_id,)
            ).fetchone()
        finally:
            conn.close()
        if not row:
            raise ValueError(f"Session not found: {session_id}")
        session = dict(row)
        for field in ("domain_scores", "skill_scores", "category_scores", "questions_asked"):
            if session.get(field):
                session[field] = json.loads(session[field])
            else:
                session[field] = {} if field != "questions_asked" else []
        return session

    def _save_session(self, conn, session: dict):
        conn.execute(
            """
            UPDATE quiz_sessions SET
                domain_scores       = ?,
                detected_domain     = ?,
                detected_role       = ?,
                current_question_id = ?,
                questions_asked     = ?,
                skill_scores        = ?,
                category_scores     = ?,
                overall_score       = ?,
                status              = ?,
                completed_at        = ?
            WHERE id = ?
            """,
            (
                json.dumps(session["domain_scores"]),
                session.get("detected_domain"),
                session.get("detected_role"),
                session.get("current_question_id"),
                json.dumps(session["questions_asked"]),
                json.dumps(session["skill_scores"]),
                json.dumps(session["category_scores"]),
                session.get("overall_score", 0),
                session.get("status", "active"),
                session.get("completed_at"),
                session["id"],
            ),
        )
        conn.commit()

    def get_question(self, question_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM questions WHERE id=? AND is_active=1", (question_id,)
            ).fetchone()
            return self._q(row)
        finally:
            conn.close()

    def get_current_question(self, session: dict) -> Optional[dict]:
        qid = session.get("current_question_id")
        return self.get_question(qid) if qid else None

    def apply_signals(self, session: dict, selected_option: dict) -> dict:
        signals = selected_option.get("signals", {})
        for domain, score in signals.items():
            session["domain_scores"][domain] = session["domain_scores"].get(domain, 0) + score
        return session

    def detect_domain(self, session: dict) -> Optional[str]:
        scores = session["domain_scores"]
        if not scores:
            return None
        top = max(scores, key=scores.get)
        return top if scores[top] >= DOMAIN_DETECT_THRESHOLD else None

    def classify_performance(self, ai_score: float) -> str:
        if ai_score >= STRONG_THRESHOLD:
            return "strong"
        if ai_score >= PARTIAL_THRESHOLD:
            return "partial"
        return "weak"

    def next_question_id(self, question: dict, performance: str, session: dict) -> Optional[str]:
        route_key = f"route_{performance}"
        next_id = question.get(route_key)
        if next_id and next_id not in session["questions_asked"]:
            return next_id
        return self._fallback_next(question, session)

    def _fallback_next(self, current_q: dict, session: dict) -> Optional[str]:
        conn = self._conn()
        asked = session["questions_asked"]
        domain = session.get("detected_domain", "ALL")
        role = session.get("detected_role")
        gate = (current_q.get("gate") or 0) + 1

        placeholders = ",".join("?" * len(asked)) if asked else "''"

        if role:
            row = conn.execute(
                f"""
                SELECT id FROM questions
                WHERE gate = ?
                  AND is_active = 1
                  AND id NOT IN ({placeholders})
                  AND (domain_scope = ? OR domain_scope = 'ALL')
                  AND role_targets LIKE ?
                ORDER BY RANDOM() LIMIT 1
                """,
                [gate] + asked + [domain, f"%{role}%"],
            ).fetchone()
            if row:
                conn.close()
                return row[0]

        row = conn.execute(
            f"""
            SELECT id FROM questions
            WHERE gate = ?
              AND is_active = 1
              AND id NOT IN ({placeholders})
              AND (domain_scope = ? OR domain_scope = 'ALL')
            ORDER BY RANDOM() LIMIT 1
            """,
            [gate] + asked + [domain],
        ).fetchone()

        conn.close()
        return row[0] if row else None

    def submit_answer(
        self,
        session_id: str,
        question_id: str,
        answer_raw: str,
        answer_key: Optional[str] = None,
        ai_evaluation: Optional[dict] = None,
    ) -> dict:
        conn = self._conn()
        session = self.load_session(session_id)
        question = self.get_question(question_id)

        if not question:
            conn.close()
            raise ValueError(f"Question {question_id} not found")

        if answer_key and question.get("options"):
            options = question["options"]
            chosen = {}

            if isinstance(options, dict):
                chosen = options.get(answer_key, {})
            elif isinstance(options, list):
                for option in options:
                    if not isinstance(option, dict):
                        continue
                    key = option.get("value") or option.get("id") or option.get("label")
                    if key == answer_key:
                        chosen = option
                        break
            session = self.apply_signals(session, chosen)

            if question.get("gate") == 0 and not session.get("detected_domain"):
                detected = self.detect_domain(session)
                if detected:
                    session["detected_domain"] = detected

        ai_score = (ai_evaluation or {}).get("score", 0)
        performance = self.classify_performance(ai_score)

        if ai_evaluation:
            for skill, score in (ai_evaluation.get("skill_scores") or {}).items():
                prev = session["skill_scores"].get(skill, [])
                if not isinstance(prev, list):
                    prev = [prev]
                prev.append(score)
                session["skill_scores"][skill] = prev

            for cat, delta in (ai_evaluation.get("category_score_deltas") or {}).items():
                session["category_scores"][cat] = session["category_scores"].get(cat, 0) + delta

        next_id = self.next_question_id(question, performance, session)
        next_q = self.get_question(next_id) if next_id else None
        if next_id and not next_q:
            next_id = self._fallback_next(question, session)
            next_q = self.get_question(next_id) if next_id else None

        conn.execute(
            """
            INSERT INTO quiz_responses (
                session_id, question_id, answer_raw, answer_key, performance,
                ai_score, ai_feedback, ai_skill_scores, ai_category_deltas,
                ai_follow_up, ai_confidence, evaluated
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                session_id,
                question_id,
                answer_raw,
                answer_key,
                performance,
                ai_score,
                (ai_evaluation or {}).get("feedback"),
                json.dumps((ai_evaluation or {}).get("skill_scores", {})),
                json.dumps((ai_evaluation or {}).get("category_score_deltas", {})),
                (ai_evaluation or {}).get("follow_up_question"),
                (ai_evaluation or {}).get("confidence"),
                1 if ai_evaluation else 0,
            ),
        )

        session["questions_asked"].append(question_id)
        session["current_question_id"] = next_id
        if not next_id:
            session["status"] = "completed"
            session["completed_at"] = datetime.utcnow().isoformat()

        self._save_session(conn, session)
        conn.close()

        if next_id and next_q:
            return {
                "status": "continue",
                "performance": performance,
                "feedback": (ai_evaluation or {}).get("feedback"),
                "follow_up": (ai_evaluation or {}).get("follow_up_question"),
                "next_question": self._format_question_for_frontend(next_q, session),
                "progress": self._progress(session),
            }

        return {
            "status": "done",
            "profile": self._build_profile(session),
            "progress": self._progress(session),
        }

    def _format_question_for_frontend(self, q: dict, session: dict) -> Optional[dict]:
        if not q:
            return None
        return {
            "id": q["id"],
            "gate": q.get("gate"),
            "stem": q.get("stem"),
            "context": q.get("context"),
            "answer_mode": q.get("answer_mode"),
            "question_type": q.get("question_type"),
            "options": q.get("options"),
            "practical_task": q.get("practical_task"),
            "estimated_minutes": q.get("estimated_minutes"),
            "difficulty": q.get("difficulty"),
        }

    def _progress(self, session: dict) -> dict:
        asked = len(session["questions_asked"])
        total_estimate = 12
        return {
            "questions_answered": asked,
            "estimated_total": total_estimate,
            "percent": min(100, round(asked / total_estimate * 100)),
            "detected_domain": session.get("detected_domain"),
            "detected_role": session.get("detected_role"),
        }

    def _build_profile(self, session: dict) -> dict:
        skill_avgs = {}
        for skill, scores in session["skill_scores"].items():
            vals = scores if isinstance(scores, list) else [scores]
            skill_avgs[skill] = round(sum(vals) / len(vals), 3)

        overall = round(sum(skill_avgs.values()) / len(skill_avgs), 3) if skill_avgs else 0

        return {
            "session_id": session["id"],
            "detected_domain": session.get("detected_domain"),
            "detected_role": session.get("detected_role"),
            "domain_scores": session["domain_scores"],
            "skill_scores": skill_avgs,
            "category_scores": session["category_scores"],
            "overall_score": overall,
        }
