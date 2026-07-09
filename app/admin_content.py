"""Backend-managed content edited from the admin dashboard."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.config import settings
from app.migrations import run_migrations


CONTENT_TYPES = {
    "learning-resources": "learning_resource",
    "learning_resource": "learning_resource",
    "resume-tips": "resume_tip",
    "resume_tip": "resume_tip",
}


def _slug(value: Any, fallback: str = "item") -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return text or fallback


class AdminContentService:
    """Persist admin-managed learning and resume content in SQLite."""

    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = Path(db_path or settings.recommender_db_path)

    def _conn(self) -> sqlite3.Connection:
        run_migrations(self.db_path)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _content_type(value: str) -> str:
        key = str(value or "").strip()
        content_type = CONTENT_TYPES.get(key)
        if not content_type:
            raise ValueError("Unsupported admin content type.")
        return content_type

    @staticmethod
    def _safe_text(value: Any, limit: int = 500) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]

    @staticmethod
    def _safe_lines(value: Any, limit: int = 12) -> List[str]:
        if isinstance(value, list):
            raw_values = value
        else:
            raw_values = re.split(r"[\n;]+", str(value or ""))
        cleaned: List[str] = []
        for item in raw_values:
            text = AdminContentService._safe_text(item, 500)
            if text and text not in cleaned:
                cleaned.append(text)
            if len(cleaned) >= limit:
                break
        return cleaned

    def _normalize_learning_resource(self, payload: Dict[str, Any], item_id: str = "") -> Dict[str, Any]:
        title = self._safe_text(payload.get("title") or payload.get("name"), 220)
        if not title:
            raise ValueError("Resource title is required.")
        hours = payload.get("hours") or payload.get("estimated_hours") or ""
        return {
            "id": self._safe_text(item_id or payload.get("id") or payload.get("resource_id"), 160)
            or f"admin-resource-{_slug(title)}-{uuid.uuid4().hex[:8]}",
            "role": self._safe_text(payload.get("role") or payload.get("role_filter"), 120),
            "skill": self._safe_text(payload.get("skill") or payload.get("skill_name"), 160),
            "skill_id": self._safe_text(payload.get("skill_id"), 120),
            "title": title,
            "platform": self._safe_text(payload.get("platform") or payload.get("source"), 160),
            "level": self._safe_text(payload.get("level") or payload.get("difficulty"), 80),
            "hours": self._safe_text(hours, 40),
            "url": self._safe_text(payload.get("url") or payload.get("link"), 500),
            "updated": self._safe_text(payload.get("updated"), 80) or "Managed by admin",
            "source": "admin",
        }

    def _normalize_resume_tip(self, payload: Dict[str, Any], item_id: str = "") -> Dict[str, Any]:
        section = self._safe_text(payload.get("section") or payload.get("title"), 180)
        if not section:
            raise ValueError("Resume section is required.")
        tips = self._safe_lines(payload.get("tips") or payload.get("tipsText") or payload.get("tip"))
        if not tips:
            raise ValueError("At least one resume tip is required.")
        return {
            "id": self._safe_text(item_id or payload.get("id"), 160)
            or f"admin-resume-{_slug(section)}-{uuid.uuid4().hex[:8]}",
            "role": self._safe_text(payload.get("role") or payload.get("role_filter"), 120),
            "section": section,
            "title": section,
            "icon": self._safe_text(payload.get("icon"), 12) or "AD",
            "tips": tips,
            "updated": self._safe_text(payload.get("updated"), 80) or "Managed by admin",
            "source": "admin",
        }

    def _normalize_payload(
        self,
        content_type: str,
        payload: Dict[str, Any],
        item_id: str = "",
    ) -> Dict[str, Any]:
        if content_type == "learning_resource":
            return self._normalize_learning_resource(payload, item_id=item_id)
        if content_type == "resume_tip":
            return self._normalize_resume_tip(payload, item_id=item_id)
        raise ValueError("Unsupported admin content type.")

    @staticmethod
    def _matches_role(item: Dict[str, Any], role: str) -> bool:
        if not role:
            return True
        item_role = str(item.get("role") or "").strip().lower()
        role_text = str(role or "").strip().lower()
        return not item_role or item_role == role_text

    def _row_to_item(self, row: sqlite3.Row) -> Dict[str, Any]:
        try:
            payload = json.loads(row["payload"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        payload["id"] = row["id"]
        payload["role"] = payload.get("role") or row["role"] or ""
        payload["title"] = payload.get("title") or row["title"]
        payload["updated_at"] = row["updated_at"]
        payload["is_active"] = bool(row["is_active"])
        return payload

    def list_items(
        self,
        content_type: str,
        role: str = "",
        include_inactive: bool = False,
    ) -> Dict[str, Any]:
        normalized_type = self._content_type(content_type)
        clauses = ["content_type = ?"]
        params: List[Any] = [normalized_type]
        if not include_inactive:
            clauses.append("is_active = 1")
        where_sql = " AND ".join(clauses)

        conn = self._conn()
        try:
            rows = conn.execute(
                f"""
                SELECT *
                FROM admin_content
                WHERE {where_sql}
                ORDER BY updated_at DESC, created_at DESC
                """,
                params,
            ).fetchall()
        finally:
            conn.close()

        items = [
            item
            for item in (self._row_to_item(row) for row in rows)
            if self._matches_role(item, role)
        ]
        return {"items": items, "count": len(items)}

    def upsert_item(
        self,
        content_type: str,
        payload: Dict[str, Any],
        item_id: str = "",
    ) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Content payload must be an object.")
        normalized_type = self._content_type(content_type)
        item = self._normalize_payload(normalized_type, payload, item_id=item_id)

        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO admin_content (
                    id, content_type, role, title, payload, is_active, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    content_type = excluded.content_type,
                    role = excluded.role,
                    title = excluded.title,
                    payload = excluded.payload,
                    is_active = 1,
                    updated_at = datetime('now')
                """,
                (
                    item["id"],
                    normalized_type,
                    item.get("role", ""),
                    item.get("title") or item.get("section"),
                    json.dumps(item),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return item

    def delete_item(self, content_type: str, item_id: str) -> bool:
        normalized_type = self._content_type(content_type)
        conn = self._conn()
        try:
            cursor = conn.execute(
                """
                UPDATE admin_content
                SET is_active = 0, updated_at = datetime('now')
                WHERE id = ? AND content_type = ?
                """,
                (item_id, normalized_type),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def learning_groups(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        groups: Dict[str, Dict[str, Any]] = {}
        for index, item in enumerate(items, start=1):
            label = item.get("skill") or item.get("role") or "Admin recommended"
            key = item.get("skill_id") or _slug(label, "admin-learning")
            group = groups.setdefault(
                key,
                {
                    "skill_id": key,
                    "skill": label,
                    "priority_label": "Admin",
                    "resources": [],
                    "source": "admin",
                },
            )
            group["resources"].append(
                {
                    "resource_id": item.get("id") or f"admin-resource-{index}",
                    "skill_id": item.get("skill_id") or key,
                    "title": item.get("title"),
                    "platform": item.get("platform") or "Admin catalog",
                    "level": item.get("level") or "Recommended",
                    "hours": item.get("hours") or "",
                    "url": item.get("url") or "#",
                    "link": item.get("url") or "#",
                    "resource_type": "admin",
                    "gap_priority": "Admin",
                    "covers": [value for value in [item.get("skill"), item.get("role")] if value],
                    "is_free": True,
                    "cost": "free",
                    "best_for": [item.get("role")] if item.get("role") else [],
                    "rank": len(group["resources"]) + 1,
                    "recommendation_score": 100,
                    "explanation": (
                        item.get("explanation")
                        or f"Added by admin for {item.get('role') or label}."
                    ),
                    "source": "admin",
                }
            )
        return list(groups.values())
