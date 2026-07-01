"""Idempotent SQLite migrations for runtime-managed tables and indexes."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Tuple


Migration = Tuple[str, Callable[[sqlite3.Connection], None]]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _executescript(conn: sqlite3.Connection, script: str) -> None:
    conn.executescript(script)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _jobs_indexes(conn: sqlite3.Connection) -> None:
    if not (_table_exists(conn, "jobs") and _table_exists(conn, "job_skills")):
        return
    _executescript(
        conn,
        """
        CREATE INDEX IF NOT EXISTS idx_job_skills_skill_id
            ON job_skills(skill_id, job_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_category_date
            ON jobs(category, date_added DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_source_date
            ON jobs(source, date_added DESC);
        """,
    )


def _telegram_posts(conn: sqlite3.Connection) -> None:
    _executescript(
        conn,
        """
        CREATE TABLE IF NOT EXISTS telegram_posts (
            telegram_post_id TEXT PRIMARY KEY,
            channel_name TEXT NOT NULL,
            message_id TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            extracted_job_id TEXT,
            extracted_fields TEXT DEFAULT '{}',
            confidence REAL DEFAULT 0,
            posted_at TEXT,
            processed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_telegram_posts_channel_message
            ON telegram_posts(channel_name, message_id);
        CREATE INDEX IF NOT EXISTS idx_telegram_posts_job
            ON telegram_posts(extracted_job_id);
        """,
    )


MIGRATIONS: Iterable[Migration] = (
    ("001_jobs_lookup_indexes", _jobs_indexes),
    ("002_telegram_post_audit_table", _telegram_posts),
)


def run_migrations(db_path: str | Path) -> dict:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    applied = []
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        existing = {
            row[0]
            for row in conn.execute("SELECT version FROM schema_migrations")
        }
        for version, migration in MIGRATIONS:
            if version in existing:
                continue
            migration(conn)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, _now()),
            )
            applied.append(version)
        conn.commit()
    finally:
        conn.close()
    return {"db_path": str(path), "applied": applied, "count": len(applied)}
