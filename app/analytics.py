"""Small event log for admin analytics without browser-side history."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.config import settings
from app.migrations import run_migrations


class AnalyticsService:
    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = Path(db_path or settings.recommender_db_path)

    def _conn(self) -> sqlite3.Connection:
        run_migrations(self.db_path)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _safe_list(values: Any, limit: int = 16) -> List[str]:
        if not isinstance(values, list):
            return []
        cleaned = []
        for value in values:
            text = str(value or "").strip()
            if text and text not in cleaned:
                cleaned.append(text[:120])
            if len(cleaned) >= limit:
                break
        return cleaned

    @staticmethod
    def _safe_text(value: Any, limit: int = 220) -> str:
        return str(value or "").strip()[:limit]

    def record_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Analytics payload must be an object.")

        event_type = self._safe_text(payload.get("event_type") or payload.get("type"), 60)
        if not event_type:
            raise ValueError("event_type is required.")

        source = self._safe_text(payload.get("source"), 40)
        session_id = self._safe_text(payload.get("session_id"), 120)
        role = self._safe_text(payload.get("role") or payload.get("target_role"), 120)
        job_id = self._safe_text(payload.get("job_id"), 140)
        job_title = self._safe_text(payload.get("job_title"), 180)
        matched_skills = self._safe_list(payload.get("matched_skills"))
        gap_skills = self._safe_list(payload.get("gap_skills"))
        try:
            match_score = float(payload.get("match_score"))
        except (TypeError, ValueError):
            match_score = None

        stored_payload = {
            "profile_id": self._safe_text(payload.get("profile_id"), 120),
            "summary": self._safe_text(payload.get("summary"), 280),
        }

        conn = self._conn()
        try:
            cursor = conn.execute(
                """
                INSERT INTO user_flow_events (
                    event_type, source, session_id, role, job_id, job_title,
                    match_score, matched_skills, gap_skills, payload
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    event_type,
                    source,
                    session_id,
                    role,
                    job_id,
                    job_title,
                    match_score,
                    json.dumps(matched_skills),
                    json.dumps(gap_skills),
                    json.dumps(stored_payload),
                ),
            )
            conn.commit()
            return {"recorded": True, "id": cursor.lastrowid}
        finally:
            conn.close()

    def _events(self, limit: int = 1000) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit or 1000), 5000))
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT *
                FROM user_flow_events
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        finally:
            conn.close()

        events = []
        for row in rows:
            item = dict(row)
            for field in ("matched_skills", "gap_skills"):
                try:
                    item[field] = json.loads(item.get(field) or "[]")
                except json.JSONDecodeError:
                    item[field] = []
            try:
                item["payload"] = json.loads(item.get("payload") or "{}")
            except json.JSONDecodeError:
                item["payload"] = {}
            events.append(item)
        return events

    @staticmethod
    def _parse_created_at(value: Any) -> Optional[datetime]:
        text = str(value or "").strip()
        if not text:
            return None
        for candidate in (text, text.replace("Z", "+00:00")):
            try:
                parsed = datetime.fromisoformat(candidate)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                continue
        return None

    @staticmethod
    def _top_counts(counter: Counter, limit: int = 8) -> List[Dict[str, Any]]:
        return [
            {"label": label, "count": count}
            for label, count in counter.most_common(limit)
            if label
        ]

    @staticmethod
    def _count_since(events: Iterable[Dict[str, Any]], since: datetime) -> int:
        count = 0
        for event in events:
            created_at = AnalyticsService._parse_created_at(event.get("created_at"))
            if created_at and created_at >= since:
                count += 1
        return count

    def summary(self, limit: int = 1000) -> Dict[str, Any]:
        events = self._events(limit=limit)
        intake_events = [
            event for event in events if event.get("event_type") == "intake_completed"
        ]
        job_view_events = [
            event for event in events if event.get("event_type") == "job_viewed"
        ]
        resume_events = [
            event
            for event in events
            if str(event.get("event_type") or "").startswith("resume_")
        ]

        role_counts = Counter(
            event.get("role") or "General"
            for event in intake_events
            if event.get("role")
        )
        source_counts = Counter(
            event.get("source") or "unknown"
            for event in intake_events
        )
        matched_skill_counts = Counter(
            skill
            for event in intake_events
            for skill in event.get("matched_skills", [])
        )
        gap_counts = Counter(
            skill
            for event in intake_events
            for skill in event.get("gap_skills", [])
        )
        watched_jobs = Counter(
            event.get("job_title") or event.get("job_id")
            for event in job_view_events
            if event.get("job_title") or event.get("job_id")
        )

        now = datetime.now(timezone.utc)
        periods = {
            "daily": self._count_since(intake_events, now - timedelta(days=1)),
            "weekly": self._count_since(intake_events, now - timedelta(days=7)),
            "monthly": self._count_since(intake_events, now - timedelta(days=30)),
            "yearly": self._count_since(intake_events, now - timedelta(days=365)),
        }

        return {
            "totals": {
                "events": len(events),
                "intakes": len(intake_events),
                "quiz_intakes": source_counts.get("quiz", 0),
                "manual_intakes": source_counts.get("manual", 0),
                "job_views": len(job_view_events),
                "resume_events": len(resume_events),
            },
            "periods": periods,
            "intake_by_source": self._top_counts(source_counts),
            "roles": self._top_counts(role_counts, limit=12),
            "matched_skills": self._top_counts(matched_skill_counts, limit=12),
            "gaps": self._top_counts(gap_counts, limit=12),
            "watched_jobs": self._top_counts(watched_jobs, limit=12),
            "recent_intakes": intake_events[:12],
        }
