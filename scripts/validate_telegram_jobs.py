"""Validate Step 13 Telegram job ingestion and matching."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.recommender import RecommendationEngine
from app.telegram_jobs import TelegramJobIngestionService


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        service = TelegramJobIngestionService(
            db_path=tmp_path / "jobs.db",
            feed_path=tmp_path / "telegram_jobs.json",
            today=date(2026, 6, 30),
        )
        post = {
            "channel_name": "python_jobs",
            "message_id": "42",
            "posted_at": "2026-06-30",
            "raw_text": (
                "Title: Backend Developer\n"
                "Company: Acme Analytics\n"
                "Skills: Python, SQL, Docker, REST API\n"
                "Location: Remote\n"
                "Salary: $90k-$110k\n"
                "Apply: https://example.com/apply"
            ),
        }
        result = service.ingest_posts([post, {**post, "message_id": "43"}])
        if result["inserted"] != 1 or result["deduped"] != 1:
            raise SystemExit("Telegram dedupe did not keep exactly one structured job.")

        job = result["jobs"][0]
        required = set(job["required_skills"])
        expected = {"lang-py", "lang-sql", "ops-docker", "be-rest"}
        if not expected <= required:
            raise SystemExit("Telegram job skills were not normalized.")
        if not job["raw_text"] or not job["source_channel"] or not job["posted_at"]:
            raise SystemExit("Telegram raw/source/date metadata is incomplete.")

        conn = sqlite3.connect(tmp_path / "jobs.db")
        try:
            row = conn.execute(
                "SELECT job_title, source, date_added FROM jobs WHERE job_id = ?",
                (job["job_id"],),
            ).fetchone()
            skill_count = conn.execute(
                "SELECT COUNT(*) FROM job_skills WHERE job_id = ?",
                (job["job_id"],),
            ).fetchone()[0]
        finally:
            conn.close()
        if row != ("Backend Developer", "Telegram: python_jobs", "2026-06-30"):
            raise SystemExit("Telegram job was not stored in the jobs table correctly.")
        if skill_count < 4:
            raise SystemExit("Telegram job skills were not stored in the database.")

        engine = RecommendationEngine(
            load_resources=False,
            db_path=str(tmp_path / "jobs.db"),
            today=date(2026, 6, 30),
        )
        matches = engine.rank_jobs(
            {
                "skill_ids": ["lang-py", "lang-sql", "ops-docker", "be-rest"],
                "skill_scores": {
                    "lang-py": 0.8,
                    "lang-sql": 0.75,
                    "ops-docker": 0.6,
                    "be-rest": 0.8,
                },
                "experience_level": "mid",
                "target_role": "backend-dev",
                "location": "remote",
            },
            top_n=3,
        )
        if not matches or "telegram_feed" not in matches[0]["retrieval_sources"]:
            raise SystemExit("Telegram job was not searchable by the matching engine.")

        feed = service.list_jobs(query="docker")
        if feed["count"] != 1:
            raise SystemExit("Telegram JSON feed search failed.")

        print(json.dumps({
            "inserted": result["inserted"],
            "deduped": result["deduped"],
            "job_id": job["job_id"],
            "skills": job["required_skill_names"],
            "match_percent": matches[0]["match_percent"],
            "feed_count": feed["count"],
        }, indent=2))


if __name__ == "__main__":
    main()
