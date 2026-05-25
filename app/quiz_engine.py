"""
Adaptive quiz engine using SQLite-backed routing.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from app.skill_normalizer import SkillNormalizer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "jobs.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "scripts", "schema.sql")

DOMAIN_DETECT_THRESHOLD = 25
STRONG_THRESHOLD = 0.75
PARTIAL_THRESHOLD = 0.45
TARGET_QUESTIONS = 12
TERMINAL_ROUTE_IDS = {"PASS", "FAIL", "DONE", "END", "STOP"}

DOMAIN_SIGNAL_KEYS = {
    "SOFTWARE",
    "DATA_AI",
    "CREATIVE",
    "BUSINESS",
    "SALES_MKT",
    "ACCOUNTING",
    "ADMIN",
    "ENGINEERING",
    "EDUCATION",
    "LOGISTICS",
    "ALL",
}

DOMAIN_SCOPE_ALIASES = {
    "SOFTWARE": ["SOFTWARE", "TECH"],
    "DATA_AI": ["DATA_AI", "TECH"],
    "CREATIVE": ["CREATIVE"],
    "SALES_MKT": ["SALES_MKT", "SALES_MARKETING"],
    "ACCOUNTING": ["ACCOUNTING", "FINANCE"],
    "ADMIN": ["ADMIN"],
    "ENGINEERING": ["ENGINEERING", "TECH"],
    "BUSINESS": ["BUSINESS", "GENERAL"],
    "EDUCATION": ["EDUCATION"],
    "LOGISTICS": ["LOGISTICS", "GENERAL"],
}

ROLE_SCOPE_ALIASES = {
    "frontend-dev": ["SOFTWARE", "TECH"],
    "backend-dev": ["SOFTWARE", "TECH"],
    "fullstack-dev": ["SOFTWARE", "TECH"],
    "mobile-dev": ["SOFTWARE", "TECH"],
    "devops": ["SOFTWARE", "TECH"],
    "data-analyst": ["DATA_AI", "TECH"],
    "data-scientist": ["DATA_AI", "TECH"],
    "ml-engineer": ["DATA_AI", "TECH"],
    "data-engineer": ["DATA_AI", "TECH"],
    "graphic-designer": ["CREATIVE"],
    "ui-ux-designer": ["CREATIVE"],
    "video-editor": ["CREATIVE"],
    "sales": ["SALES_MKT", "SALES_MARKETING"],
    "digital-marketer": ["SALES_MKT", "SALES_MARKETING"],
    "accounting": ["ACCOUNTING", "FINANCE"],
    "finance": ["ACCOUNTING", "FINANCE"],
    "admin": ["ADMIN"],
    "project-manager": ["BUSINESS", "GENERAL"],
    "architect": ["ENGINEERING", "TECH"],
}

ROLE_LABELS = {
    "frontend-dev": ["frontend developer", "react developer", "web developer"],
    "backend-dev": ["backend developer", "api developer", "software developer"],
    "fullstack-dev": ["full stack developer", "fullstack developer"],
    "mobile-dev": ["mobile developer", "flutter developer"],
    "devops": ["devops", "devops engineer"],
    "data-analyst": ["data analyst", "business analyst"],
    "data-scientist": ["data scientist"],
    "ml-engineer": ["machine learning engineer", "ml engineer"],
    "data-engineer": ["data engineer"],
    "graphic-designer": ["graphic designer", "graphics designer"],
    "ui-ux-designer": ["ui designer", "ux designer", "ui/ux designer"],
    "video-editor": ["video editor"],
    "sales": ["sales", "sales representative"],
    "digital-marketer": ["digital marketer", "marketing"],
    "accounting": ["accountant", "accounting", "cashier"],
    "finance": ["finance", "banking"],
    "admin": ["admin", "secretary", "office manager", "hr"],
    "project-manager": ["project manager"],
    "architect": ["architect", "site engineer", "civil engineer"],
}

SPECIFIC_ROLE_KEYS = set(ROLE_LABELS)
BROAD_CATEGORY_KEYS = {
    "tech",
    "general",
    "finance",
    "sales_marketing",
    "creative",
    "business",
}

SUPPORT_QUESTIONS = [
    {
        "id": "Q_G0_SUBDOMAIN_001",
        "gate": 0,
        "domain_scope": "ALL",
        "question_type": "multiple_choice",
        "role_targets": [
            "frontend-dev",
            "backend-dev",
            "fullstack-dev",
            "data-analyst",
            "data-scientist",
            "graphic-designer",
            "sales",
            "accounting",
            "admin",
            "architect",
        ],
        "difficulty": "beginner",
        "experience_level_target": "any",
        "stem": "Which focus area best matches the work you want to be tested for?",
        "context": None,
        "answer_mode": "single_choice",
        "options": {
            "A": {
                "text": "Frontend web apps, React, UI behavior, and responsive pages",
                "signals": {"frontend-dev": 35},
                "skills": ["fe-react", "fe-css", "lang-js", "fe-responsive"],
                "quality_level": "strong",
            },
            "B": {
                "text": "Backend APIs, databases, services, and server-side logic",
                "signals": {"backend-dev": 35},
                "skills": ["be-rest", "be-fastapi", "db-schema", "lang-sql"],
                "quality_level": "strong",
            },
            "C": {
                "text": "Full-stack work across frontend, backend, and databases",
                "signals": {"fullstack-dev": 35},
                "skills": ["fe-react", "be-rest", "db-schema", "lang-js"],
                "quality_level": "strong",
            },
            "D": {
                "text": "Data analysis, dashboards, reporting, and SQL insights",
                "signals": {"data-analyst": 35},
                "skills": ["lang-sql", "da-pandas", "da-tableau", "da-excel"],
                "quality_level": "strong",
            },
            "E": {
                "text": "Machine learning, data science, and AI model work",
                "signals": {"data-scientist": 30, "ml-engineer": 20},
                "skills": ["lang-py", "ds-sklearn", "ds-model-eval", "ml-pipelines"],
                "quality_level": "strong",
            },
            "F": {
                "text": "Graphic design, UI/UX, brand visuals, or creative production",
                "signals": {"graphic-designer": 25, "ui-ux-designer": 25},
                "skills": ["fe-figma", "des-branding", "des-wireframe", "des-prototype"],
                "quality_level": "strong",
            },
            "G": {
                "text": "Sales, digital marketing, campaigns, and customer growth",
                "signals": {"sales": 25, "digital-marketer": 25},
                "skills": ["mkt-social", "mkt-seo", "mkt-analytics", "soft-comm"],
                "quality_level": "strong",
            },
            "H": {
                "text": "Accounting, finance, cash handling, or financial reporting",
                "signals": {"accounting": 35},
                "skills": ["fin-accounting", "fin-excel", "da-excel"],
                "quality_level": "strong",
            },
            "I": {
                "text": "Administration, office coordination, HR, and executive support",
                "signals": {"admin": 35},
                "skills": ["soft-mgmt", "soft-time", "soft-docs", "da-excel"],
                "quality_level": "strong",
            },
            "J": {
                "text": "Architecture, construction, CAD, or civil engineering",
                "signals": {"architect": 35},
                "skills": ["des-rhino", "soft-problem", "soft-docs"],
                "quality_level": "strong",
            },
        },
        "practical_task": None,
        "scoring": {
            "max_score": 100,
            "pass_score": 70,
            "category_weights": {},
            "skill_weights": {},
            "rubric": [],
            "red_flags": [],
            "partial_credit_rules": [],
        },
        "ai_evaluation_prompt": None,
        "job_evidence": [],
        "route_strong": None,
        "route_partial": None,
        "route_weak": None,
        "estimated_minutes": 1,
    }
]


class QuizEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.normalizer = SkillNormalizer()
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
            self._seed_support_questions(conn)
        finally:
            conn.close()

    def _seed_support_questions(self, conn) -> None:
        for q in SUPPORT_QUESTIONS:
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
                    q["id"],
                    q.get("gate", 0),
                    q.get("domain_scope", "ALL"),
                    q.get("question_type", "multiple_choice"),
                    json.dumps(q.get("role_targets", [])),
                    q.get("difficulty", "beginner"),
                    q.get("experience_level_target", "any"),
                    q.get("stem"),
                    q.get("context"),
                    q.get("answer_mode", "single_choice"),
                    json.dumps(q["options"]) if q.get("options") else None,
                    json.dumps(q["practical_task"]) if q.get("practical_task") else None,
                    json.dumps(q.get("scoring", {})),
                    q.get("ai_evaluation_prompt"),
                    json.dumps(q.get("job_evidence", [])),
                    q.get("route_strong"),
                    q.get("route_partial"),
                    q.get("route_weak"),
                    q.get("estimated_minutes"),
                ),
            )
        conn.commit()

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

    def _is_domain_signal(self, key: str) -> bool:
        text = str(key)
        return text in DOMAIN_SIGNAL_KEYS or (text == text.upper() and text.upper() in DOMAIN_SIGNAL_KEYS)

    def _domain_scopes(self, domain: Optional[str], role: Optional[str] = None) -> List[str]:
        scopes: List[str] = []
        if domain:
            scopes.extend(DOMAIN_SCOPE_ALIASES.get(str(domain).upper(), [str(domain).upper()]))
        if role:
            scopes.extend(ROLE_SCOPE_ALIASES.get(str(role), []))
        scopes.append("ALL")
        return list(dict.fromkeys(scopes))

    def _role_search_terms(self, role: Optional[str]) -> List[str]:
        if not role:
            return []
        terms = [role, role.replace("-", " ")]
        terms.extend(ROLE_LABELS.get(role, []))
        return list(dict.fromkeys(term for term in terms if term))

    def _normalise_skill_id(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        resolved = self.normalizer.to_skill_id(text)
        if resolved:
            return resolved
        lowered = text.lower()
        if lowered in self.normalizer._id_to_name:
            return lowered
        return None

    def _add_skill_score(self, session: dict, skill: Any, score: float) -> None:
        skill_id = self._normalise_skill_id(skill)
        if not skill_id:
            return
        prev = session["skill_scores"].get(skill_id, [])
        if not isinstance(prev, list):
            prev = [prev]
        prev.append(max(0.0, min(1.0, float(score))))
        session["skill_scores"][skill_id] = prev

    def _question_evidence_skills(self, question: dict) -> List[str]:
        skills: List[str] = []

        scoring = question.get("scoring") or {}
        skills.extend((scoring.get("skill_weights") or {}).keys())

        for evidence in question.get("job_evidence") or []:
            raw = evidence.get("evidence_skills")
            if isinstance(raw, list):
                skills.extend(str(item) for item in raw)
            elif isinstance(raw, str):
                skills.extend(part.strip() for part in raw.split(","))

        return list(dict.fromkeys(skill for skill in skills if skill))

    def _update_detected_role(self, session: dict) -> None:
        scores = {
            str(cat): float(score)
            for cat, score in (session.get("category_scores") or {}).items()
            if not self._is_domain_signal(str(cat))
        }
        if not scores:
            return

        specific = {cat: score for cat, score in scores.items() if cat in SPECIFIC_ROLE_KEYS}
        if specific:
            session["detected_role"] = max(specific, key=specific.get)
            return

        narrow = {cat: score for cat, score in scores.items() if cat not in BROAD_CATEGORY_KEYS}
        if narrow and not session.get("detected_role"):
            session["detected_role"] = max(narrow, key=narrow.get)

    def _merge_ai_evidence(
        self,
        session: dict,
        question: dict,
        selected_option: Optional[dict],
        ai_evaluation: Optional[dict],
        ai_score: float,
    ) -> None:
        score = max(0.0, min(1.0, float(ai_score)))
        evaluation = ai_evaluation or {}

        for skill, skill_score in (evaluation.get("skill_scores") or {}).items():
            self._add_skill_score(session, skill, skill_score)

        for skill in (selected_option or {}).get("skills", []):
            self._add_skill_score(session, skill, score)

        if not (evaluation.get("skill_scores") or {}):
            for skill in self._question_evidence_skills(question):
                self._add_skill_score(session, skill, score)

        for cat, delta in (evaluation.get("category_score_deltas") or {}).items():
            cat = str(cat)
            if self._is_domain_signal(cat):
                session["domain_scores"][cat.upper()] = session["domain_scores"].get(cat.upper(), 0) + delta
            else:
                session["category_scores"][cat] = session["category_scores"].get(cat, 0) + delta

        self._update_detected_role(session)

    def apply_signals(self, session: dict, selected_option: dict) -> dict:
        signals = selected_option.get("signals", {})
        for key, score in signals.items():
            key = str(key)
            if self._is_domain_signal(key):
                domain = key.upper()
                session["domain_scores"][domain] = session["domain_scores"].get(domain, 0) + score

        detected = self.detect_domain(session)
        if detected:
            session["detected_domain"] = detected
        self._update_detected_role(session)
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
        if len(session["questions_asked"]) + 1 >= TARGET_QUESTIONS:
            return None

        route_key = f"route_{performance}"
        next_id = question.get(route_key)
        excluded = set(session["questions_asked"])
        excluded.add(question["id"])
        if (
            next_id
            and str(next_id).upper() not in TERMINAL_ROUTE_IDS
            and next_id not in excluded
            and self.get_question(next_id)
        ):
            return next_id
        return self._fallback_next(question, session)

    def _select_question(
        self,
        conn,
        excluded: Iterable[str],
        gates: Iterable[int],
        scopes: Optional[Iterable[str]] = None,
        role_terms: Optional[Iterable[str]] = None,
    ) -> Optional[str]:
        excluded = list(dict.fromkeys(item for item in excluded if item))
        gates = list(dict.fromkeys(gates))
        scopes = list(dict.fromkeys(scopes or []))
        role_terms = list(dict.fromkeys(role_terms or []))

        clauses = ["is_active = 1"]
        params: List[Any] = []

        if excluded:
            clauses.append(f"id NOT IN ({','.join('?' for _ in excluded)})")
            params.extend(excluded)
        if gates:
            clauses.append(f"gate IN ({','.join('?' for _ in gates)})")
            params.extend(gates)
        if scopes:
            clauses.append(f"domain_scope IN ({','.join('?' for _ in scopes)})")
            params.extend(scopes)
        if role_terms:
            role_clauses = []
            for term in role_terms:
                role_clauses.append("role_targets LIKE ?")
                params.append(f"%{term}%")
                role_clauses.append("job_evidence LIKE ?")
                params.append(f"%{term}%")
            clauses.append(f"({' OR '.join(role_clauses)})")

        row = conn.execute(
            f"""
            SELECT id FROM questions
            WHERE {' AND '.join(clauses)}
            ORDER BY
              CASE
                WHEN gate = 1 THEN 0
                WHEN gate = 2 THEN 1
                ELSE 2
              END,
              id
            LIMIT 1
            """,
            params,
        ).fetchone()
        return row[0] if row else None

    def _fallback_next(self, current_q: dict, session: dict) -> Optional[str]:
        conn = self._conn()
        try:
            excluded = set(session["questions_asked"])
            excluded.add(current_q["id"])

            domain = session.get("detected_domain")
            role = session.get("detected_role")
            scopes = self._domain_scopes(domain, role)
            role_terms = self._role_search_terms(role)

            current_gate = current_q.get("gate") or 0
            if current_gate <= 0:
                gate_plan = [1, 2]
            elif current_gate == 1:
                gate_plan = [1, 2]
            else:
                gate_plan = [2, 1]

            if role_terms:
                next_id = self._select_question(conn, excluded, gate_plan, scopes, role_terms)
                if next_id:
                    return next_id

            next_id = self._select_question(conn, excluded, gate_plan, scopes)
            if next_id:
                return next_id

            broad_scopes = [scope for scope in scopes if scope not in {"ALL"}]
            next_id = self._select_question(conn, excluded, [2], broad_scopes)
            if next_id:
                return next_id

            next_id = self._select_question(conn, excluded, [2], ["GENERAL"])
            if next_id:
                return next_id

            return self._select_question(conn, excluded, [1, 2])
        finally:
            conn.close()

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

        chosen: Optional[dict] = None
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

        ai_score = (ai_evaluation or {}).get("score", 0)
        performance = self.classify_performance(ai_score)

        self._merge_ai_evidence(session, question, chosen, ai_evaluation, ai_score)

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
        session["overall_score"] = self._overall_score(session)
        if not next_id:
            session["status"] = "completed"
            session["completed_at"] = datetime.now(timezone.utc).isoformat()

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

    def _skill_averages(self, session: dict) -> Dict[str, float]:
        skill_avgs: Dict[str, float] = {}
        for skill, scores in session["skill_scores"].items():
            vals = scores if isinstance(scores, list) else [scores]
            numeric = [float(v) for v in vals if isinstance(v, (int, float))]
            if numeric:
                skill_avgs[skill] = round(sum(numeric) / len(numeric), 3)
        return skill_avgs

    def _overall_score(self, session: dict) -> float:
        skill_avgs = self._skill_averages(session)
        return round(sum(skill_avgs.values()) / len(skill_avgs), 3) if skill_avgs else 0

    def _experience_level(self, overall: float) -> str:
        if overall >= 0.82:
            return "senior"
        if overall >= 0.68:
            return "mid"
        if overall >= 0.4:
            return "junior"
        return "intern"

    def _top_category(self, session: dict) -> Optional[str]:
        if session.get("detected_role"):
            return session["detected_role"]
        scores = {
            cat: score
            for cat, score in (session.get("category_scores") or {}).items()
            if not self._is_domain_signal(cat)
        }
        return max(scores, key=scores.get) if scores else session.get("detected_domain")

    def _progress(self, session: dict) -> dict:
        asked = len(session["questions_asked"])
        total_estimate = TARGET_QUESTIONS
        overall = self._overall_score(session)
        return {
            "questions_answered": asked,
            "estimated_total": total_estimate,
            "percent": min(100, round(asked / total_estimate * 100)),
            "detected_domain": session.get("detected_domain"),
            "detected_role": session.get("detected_role"),
            "detected_skills": len(session.get("skill_scores") or {}),
            "skill_level": self._experience_level(overall),
            "confidence": round(overall * 100),
        }

    def _build_profile(self, session: dict) -> dict:
        skill_avgs = self._skill_averages(session)
        overall = round(sum(skill_avgs.values()) / len(skill_avgs), 3) if skill_avgs else 0
        top_category = self._top_category(session)

        return {
            "source": "adaptive_quiz",
            "session_id": session["id"],
            "detected_domain": session.get("detected_domain"),
            "detected_role": session.get("detected_role"),
            "detected_skills": list(skill_avgs.keys()),
            "top_category": top_category,
            "experience_level": self._experience_level(overall),
            "skill_level": self._experience_level(overall),
            "domain_scores": session["domain_scores"],
            "skill_scores": skill_avgs,
            "category_scores": session["category_scores"],
            "overall_score": overall,
            "confidence": round(overall * 100),
            "question_count": len(session["questions_asked"]),
            "profile_vector": None,
        }
