from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.config import settings
from app.skill_normalizer import SkillNormalizer


class TelegramJobIngestionError(ValueError):
    """Raised when Telegram job ingestion input is invalid."""


ROLE_RULES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("backend-dev", ("backend", "back end", "api", "django", "flask", "fastapi", "java developer", "python developer")),
    ("frontend-dev", ("frontend", "front end", "react", "vue", "angular", "ui developer", "web developer")),
    ("fullstack-dev", ("full stack", "fullstack", "mern", "software developer")),
    ("mobile-dev", ("mobile", "android", "ios", "flutter", "react native")),
    ("devops-engineer", ("devops", "sre", "site reliability", "cloud engineer", "platform", "kubernetes")),
    (
        "data-analyst",
        (
            "data analyst",
            "data analysis",
            "data analytics",
            "bi analyst",
            "business intelligence",
            "reporting analyst",
            "power bi",
            "powerbi",
            "tableau",
            "dashboard",
            "excel analyst",
            "sql analyst",
            "statistics",
            "data collection",
            "data enumerator",
        ),
    ),
    ("data-scientist", ("data scientist", "data science", "predictive", "statistical modeling")),
    ("ml-engineer", ("machine learning", "ml engineer", "ai engineer", "nlp")),
    ("ui-ux-designer", ("ux", "ui ux", "product designer", "figma")),
)

SENIORITY_RULES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("intern", ("intern", "internship", "trainee")),
    ("junior", ("junior", "jr", "entry level", "0-2", "0 to 2")),
    ("senior", ("senior", "sr", "lead", "principal", "staff", "6+")),
    ("mid", ("mid", "middle", "intermediate", "2+", "3+", "3-5")),
)

DEFAULT_TELEGRAM_CHANNELS: Tuple[str, ...] = (
    "@freelance_ethio",
    "@effoyjobs",
    "@josad_software",
    "@ethiojobsofficial",
    "@geezjobs_ethiopia",
    "@Maroset",
)


def _ethiopia_today() -> date:
    return datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=3))
    ).date()


class TelegramJobIngestionService:
    """Extract, validate, dedupe, and store Telegram job posts."""

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        feed_path: Optional[str | Path] = None,
        normalizer: Optional[SkillNormalizer] = None,
        ai_extractor: Optional[Any] = None,
        today: Optional[date] = None,
    ):
        self.db_path = Path(db_path or settings.recommender_db_path)
        self.feed_path = Path(feed_path or settings.telegram_jobs_feed_path)
        self.normalizer = normalizer or SkillNormalizer()
        self.ai_extractor = ai_extractor
        self.today = today or _ethiopia_today()

    def ingest_posts(self, posts: Sequence[Any]) -> Dict[str, Any]:
        if not isinstance(posts, Sequence) or isinstance(posts, (str, bytes)):
            raise TelegramJobIngestionError("posts must be a list of Telegram messages.")

        self._ensure_tables()
        feed = self._read_feed()
        feed_jobs = {
            str(job.get("job_id")): job
            for job in feed.get("jobs", [])
            if job.get("job_id")
        }
        batch_seen: set[str] = set()
        result = {
            "received": len(posts),
            "inserted": 0,
            "updated": 0,
            "deduped": 0,
            "skipped": 0,
            "jobs": [],
            "errors": [],
        }

        for index, raw_post in enumerate(posts, start=1):
            try:
                post = self._normalize_post(raw_post, index)
                extracted = self.extract_job(post)
                if not extracted["is_valid"]:
                    self._store_post(post, extracted)
                    result["skipped"] += 1
                    result["errors"].append({
                        "message_id": post["message_id"],
                        "errors": extracted["validation_errors"],
                    })
                    continue

                job_id = extracted["job_id"]
                if job_id in batch_seen:
                    self._store_post(post, extracted)
                    result["deduped"] += 1
                    continue

                existed = self._job_exists(job_id) or job_id in feed_jobs
                self._store_job(extracted)
                self._store_post(post, extracted)
                feed_jobs[job_id] = extracted
                batch_seen.add(job_id)
                if existed:
                    result["updated"] += 1
                else:
                    result["inserted"] += 1
                result["jobs"].append(extracted)
            except Exception as exc:
                result["skipped"] += 1
                result["errors"].append({"message_id": str(index), "errors": [str(exc)]})

        self._write_feed(feed_jobs.values())
        return result

    def refresh_channels(
        self,
        channels: Optional[Sequence[str]] = None,
        per_channel_limit: int = 12,
    ) -> Dict[str, Any]:
        """Fetch recent public Telegram channel posts and ingest active jobs."""
        selected_channels = channels or DEFAULT_TELEGRAM_CHANNELS
        safe_limit = max(1, min(30, int(per_channel_limit or 12)))
        posts: List[Dict[str, Any]] = []
        channel_results: List[Dict[str, Any]] = []

        for channel in selected_channels:
            handle = self._channel_handle(channel)
            if not handle:
                channel_results.append({
                    "channel": str(channel),
                    "fetched": 0,
                    "error": "invalid channel",
                })
                continue

            try:
                channel_posts = self.fetch_channel_posts(handle, limit=safe_limit)
                posts.extend(channel_posts)
                channel_results.append({
                    "channel": f"@{handle}",
                    "fetched": len(channel_posts),
                    "error": None,
                })
            except Exception as exc:
                channel_results.append({
                    "channel": f"@{handle}",
                    "fetched": 0,
                    "error": str(exc),
                })

        if posts:
            result = self.ingest_posts(posts)
        else:
            result = {
                "received": 0,
                "inserted": 0,
                "updated": 0,
                "deduped": 0,
                "skipped": 0,
                "jobs": [],
                "errors": [],
            }
        result["channels"] = channel_results
        result["fetched_posts"] = len(posts)
        result["active_total"] = self.list_jobs(limit=1)["total"]
        return result

    def fetch_channel_posts(self, channel: str, limit: int = 12) -> List[Dict[str, Any]]:
        """Read a Telegram public /s page without requiring Telegram credentials."""
        handle = self._channel_handle(channel)
        if not handle:
            raise TelegramJobIngestionError("invalid Telegram channel")

        request = urllib.request.Request(
            f"https://t.me/s/{handle}",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise TelegramJobIngestionError(f"Telegram returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise TelegramJobIngestionError(f"Telegram fetch failed: {exc.reason}") from exc

        return self._posts_from_channel_html(handle, body, limit=limit)

    def extract_job(self, post: Dict[str, Any]) -> Dict[str, Any]:
        local = self._extract_locally(post)
        ai_payload = self._extract_with_ai(post["raw_text"])
        merged = self._merge_ai_payload(local, ai_payload)
        normalized = self._normalize_job_fields(post, merged)
        errors = self.validate_job(normalized)
        normalized["validation_errors"] = errors
        normalized["is_valid"] = not errors
        return normalized

    def validate_job(self, job: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        if not job.get("job_title"):
            errors.append("missing job_title")
        if not job.get("description"):
            errors.append("missing description")
        if not job.get("category"):
            errors.append("missing category")
        if not job.get("required_skills"):
            errors.append("missing required_skills")
        if not job.get("source_channel"):
            errors.append("missing source_channel")
        if not job.get("posted_at"):
            errors.append("missing posted_at")
        if self._is_expired(job):
            errors.append("deadline passed")
        return errors

    def list_jobs(self, query: str = "", limit: int = 50, role: str = "") -> Dict[str, Any]:
        feed = self._read_feed()
        jobs = [
            self._ensure_apply_target(job)
            for job in feed.get("jobs", [])
            if not self._is_expired(job)
        ]
        query_text = self._clean(query).casefold()
        if query_text:
            jobs = [
                job for job in jobs
                if query_text in self._search_blob(job)
            ]
        role_text = self._clean(role).casefold()
        if role_text and role_text not in {"all", "all roles", "all work types"}:
            jobs = [job for job in jobs if self._matches_role_filter(job, role_text)]
        jobs = sorted(
            jobs,
            key=lambda job: (
                str(job.get("posted_at") or job.get("date_added") or ""),
                str(job.get("job_id") or ""),
            ),
            reverse=True,
        )
        safe_limit = max(1, min(100, int(limit or 50)))
        return {
            "jobs": jobs[:safe_limit],
            "count": len(jobs[:safe_limit]),
            "total": len(jobs),
            "updated_at": feed.get("updated_at"),
        }

    def _extract_with_ai(self, raw_text: str) -> Optional[Dict[str, Any]]:
        if not self.ai_extractor or not getattr(self.ai_extractor, "is_available", lambda: False)():
            return None
        extractor = getattr(self.ai_extractor, "extract_telegram_job", None)
        if not extractor:
            return None
        payload = extractor(raw_text)
        return payload if isinstance(payload, dict) else None

    def _merge_ai_payload(
        self,
        local: Dict[str, Any],
        ai_payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not ai_payload:
            local["extraction_method"] = "local"
            return local
        merged = dict(local)
        for key in (
            "job_title",
            "company",
            "role",
            "category",
            "location",
            "salary",
            "apply_link",
            "deadline",
            "exp_level",
            "job_type",
        ):
            value = self._clean(ai_payload.get(key))
            if value:
                merged[key] = value
        for key in ("required_skills", "optional_skills"):
            values = ai_payload.get(key)
            if values:
                merged[key] = values
        merged["extraction_method"] = "groq+local"
        return merged

    def _extract_locally(self, post: Dict[str, Any]) -> Dict[str, Any]:
        raw_text = post["raw_text"]
        lines = self._lines(raw_text)
        title = (
            self._field_value(lines, ("title", "position", "role", "job"))
            or self._title_from_lines(lines)
        )
        company = self._field_value(lines, ("company", "org", "organization"))
        location = self._field_value(lines, ("location", "loc", "work location"))
        salary = self._field_value(lines, ("salary", "compensation", "pay"))
        apply_link = self._field_value(lines, ("apply", "apply link", "link"))
        deadline = (
            self._field_value(
                lines,
                (
                    "deadline",
                    "closing date",
                    "application deadline",
                    "apply before",
                    "apply by",
                    "due date",
                ),
            )
            or self._extract_deadline_date(raw_text)
        )
        required_raw = self._skills_from_labels(lines, ("skills", "requirements", "required", "tech stack", "stack"))
        optional_raw = self._skills_from_labels(lines, ("nice to have", "preferred", "bonus"))
        if not apply_link:
            apply_link = self._first_url(raw_text)
        if not location:
            location = self._infer_location(raw_text)

        text_for_inference = " ".join([title, raw_text])
        return {
            "job_title": title,
            "company": company,
            "role": self._infer_role(text_for_inference),
            "category": self._infer_category(text_for_inference),
            "location": location,
            "salary": salary,
            "apply_link": apply_link,
            "deadline": deadline,
            "exp_level": self._infer_seniority(text_for_inference),
            "job_type": self._infer_job_type(raw_text),
            "required_skills": required_raw,
            "optional_skills": optional_raw,
            "description": raw_text,
            "extraction_method": "local",
        }

    def _normalize_job_fields(
        self,
        post: Dict[str, Any],
        extracted: Dict[str, Any],
    ) -> Dict[str, Any]:
        raw_text = post["raw_text"]
        title = self._clean(extracted.get("job_title"), max_length=140)
        company = self._clean(extracted.get("company"), max_length=100)
        required_skills = self._normalize_skills(
            extracted.get("required_skills"),
            fallback_text=f"{title}\n{raw_text}",
        )
        optional_skills = [
            skill for skill in self._normalize_skills(extracted.get("optional_skills"))
            if skill not in required_skills
        ]
        category = self._clean(extracted.get("category")) or self._infer_category(f"{title} {raw_text}")
        posted_at = self._date_only(post.get("posted_at")) or self.today.isoformat()
        deadline = (
            self._date_only(extracted.get("deadline"))
            or self._extract_deadline_date(raw_text)
        )
        apply_link = self._clean(extracted.get("apply_link"), max_length=500)
        key_parts = [title.casefold(), company.casefold(), apply_link.casefold()]
        if not (title and (company or apply_link)):
            key_parts.append(self._fingerprint_text(raw_text))
        job_key = "|".join(key_parts)
        job_id = "telegram-" + hashlib.sha1(job_key.encode("utf-8")).hexdigest()[:12]
        confidence = self._confidence(title, category, required_skills, extracted)
        channel = post["channel_name"]
        source_ref = self._clean(post.get("source_ref") or extracted.get("apply_link"), max_length=500)
        application_url = apply_link or source_ref

        return {
            "job_id": job_id,
            "job_title": title,
            "title": title,
            "company": company,
            "role": self._clean(extracted.get("role")) or category,
            "category": category,
            "source": f"Telegram: {channel}",
            "source_channel": channel,
            "source_ref": source_ref,
            "message_id": post["message_id"],
            "telegram_post_id": post["telegram_post_id"],
            "description": self._clean(extracted.get("description") or raw_text, max_length=2000),
            "raw_text": raw_text,
            "required_skills": required_skills,
            "required_skill_names": [self.normalizer.name_for(skill_id) for skill_id in required_skills],
            "optional_skills": optional_skills,
            "optional_skill_names": [self.normalizer.name_for(skill_id) for skill_id in optional_skills],
            "seniority": self._clean(extracted.get("exp_level")) or "mid",
            "exp_level": self._clean(extracted.get("exp_level")) or "mid",
            "job_type": self._clean(extracted.get("job_type")) or "full-time",
            "location": self._clean(extracted.get("location")) or "Not specified",
            "salary": self._clean(extracted.get("salary")),
            "apply_link": application_url,
            "direct_apply_link": apply_link,
            "url": application_url,
            "deadline": deadline,
            "deadline_date": deadline,
            "posted_at": posted_at,
            "date_added": posted_at,
            "processed_at": self._now_iso(),
            "confidence": confidence,
            "extraction_method": extracted.get("extraction_method", "local"),
        }

    def _normalize_post(self, raw_post: Any, index: int) -> Dict[str, Any]:
        if isinstance(raw_post, str):
            data = {"raw_text": raw_post}
        elif isinstance(raw_post, dict):
            data = dict(raw_post)
        else:
            raise TelegramJobIngestionError("Each post must be a string or object.")

        raw_text = self._clean_multiline(
            data.get("raw_text") or data.get("text") or data.get("message"),
            max_length=5000,
        )
        if len(raw_text) < 20:
            raise TelegramJobIngestionError("Telegram post text is too short.")

        channel = self._clean(
            data.get("channel_name") or data.get("channel") or data.get("source_channel") or "manual-import",
            max_length=120,
        )
        message_id = self._clean(
            data.get("message_id") or data.get("id") or data.get("post_id") or str(index),
            max_length=80,
        )
        posted_at = self._date_only(data.get("posted_at") or data.get("date")) or self.today.isoformat()
        post_key = f"{channel}|{message_id}|{self._fingerprint_text(raw_text)}"
        return {
            "telegram_post_id": "tg-" + hashlib.sha1(post_key.encode("utf-8")).hexdigest()[:12],
            "channel_name": channel,
            "message_id": message_id,
            "raw_text": raw_text,
            "posted_at": posted_at,
            "source_ref": self._clean(data.get("source_ref") or data.get("url") or data.get("link"), max_length=500),
        }

    def _normalize_skills(self, value: Any, fallback_text: str = "") -> List[str]:
        raw_values: List[str] = []
        if isinstance(value, str):
            raw_values.extend(re.split(r"[,;/\n|]+", value))
        elif isinstance(value, list):
            raw_values.extend(str(item) for item in value)
        elif value:
            raw_values.append(str(value))

        skills = self.normalizer.normalize_list(raw_values)
        if fallback_text:
            for skill_id in self.normalizer.extract_skills(fallback_text):
                if skill_id not in skills:
                    skills.append(skill_id)
        return skills[:18]

    def _ensure_tables(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    job_title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source TEXT,
                    exp_level TEXT,
                    job_type TEXT,
                    location TEXT,
                    date_added TEXT,
                    tfidf_vector BLOB
                );
                CREATE TABLE IF NOT EXISTS job_skills (
                    job_id TEXT,
                    skill_id TEXT,
                    is_required INTEGER DEFAULT 1,
                    PRIMARY KEY (job_id, skill_id)
                );
                CREATE INDEX IF NOT EXISTS idx_job_skills_skill_id
                    ON job_skills(skill_id, job_id);
                CREATE INDEX IF NOT EXISTS idx_jobs_category_date
                    ON jobs(category, date_added DESC);
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
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _store_job(self, job: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO jobs (
                    job_id, job_title, description, category, source,
                    exp_level, job_type, location, date_added
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    job["job_id"],
                    job["job_title"],
                    job["description"],
                    job["category"],
                    job["source"],
                    job["exp_level"],
                    job["job_type"],
                    job["location"],
                    job["date_added"],
                ),
            )
            conn.execute("DELETE FROM job_skills WHERE job_id = ?", (job["job_id"],))
            for skill_id in job["required_skills"]:
                conn.execute(
                    "INSERT OR IGNORE INTO job_skills (job_id, skill_id, is_required) VALUES (?,?,1)",
                    (job["job_id"], skill_id),
                )
            for skill_id in job["optional_skills"]:
                conn.execute(
                    "INSERT OR IGNORE INTO job_skills (job_id, skill_id, is_required) VALUES (?,?,0)",
                    (job["job_id"], skill_id),
                )
            conn.commit()
        finally:
            conn.close()

    def _store_post(self, post: Dict[str, Any], extracted: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO telegram_posts (
                    telegram_post_id, channel_name, message_id, raw_text,
                    extracted_job_id, extracted_fields, confidence,
                    posted_at, processed_at
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    post["telegram_post_id"],
                    post["channel_name"],
                    post["message_id"],
                    post["raw_text"],
                    extracted.get("job_id") if extracted.get("is_valid") else None,
                    json.dumps(extracted, ensure_ascii=True),
                    float(extracted.get("confidence") or 0),
                    post["posted_at"],
                    self._now_iso(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _job_exists(self, job_id: str) -> bool:
        if not self.db_path.exists():
            return False
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT 1 FROM jobs WHERE job_id = ? LIMIT 1", (job_id,)).fetchone()
            return row is not None
        finally:
            conn.close()

    def _read_feed(self) -> Dict[str, Any]:
        if not self.feed_path.exists():
            return {"jobs": [], "updated_at": None}
        try:
            with open(self.feed_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return {"jobs": [], "updated_at": None}
        if isinstance(payload, list):
            return {"jobs": payload, "updated_at": None}
        return {
            "jobs": payload.get("jobs", []) if isinstance(payload, dict) else [],
            "updated_at": payload.get("updated_at") if isinstance(payload, dict) else None,
        }

    def _write_feed(self, jobs: Iterable[Dict[str, Any]]) -> None:
        self.feed_path.parent.mkdir(parents=True, exist_ok=True)
        active_jobs = [
            self._ensure_apply_target(job)
            for job in jobs
            if not self._is_expired(job)
        ]
        sorted_jobs = sorted(
            active_jobs,
            key=lambda job: (
                str(job.get("posted_at") or job.get("date_added") or ""),
                str(job.get("job_id") or ""),
            ),
            reverse=True,
        )
        with open(self.feed_path, "w", encoding="utf-8") as handle:
            json.dump(
                {"updated_at": self._now_iso(), "jobs": sorted_jobs},
                handle,
                indent=2,
                ensure_ascii=True,
            )

    def _field_value(self, lines: Sequence[str], labels: Sequence[str]) -> str:
        label_pattern = "|".join(re.escape(label) for label in labels)
        pattern = re.compile(rf"^\s*(?:{label_pattern})\s*[:\-]\s*(.+)$", re.IGNORECASE)
        for line in lines:
            match = pattern.search(line)
            if match:
                return self._clean(match.group(1))
        return ""

    def _skills_from_labels(self, lines: Sequence[str], labels: Sequence[str]) -> List[str]:
        value = self._field_value(lines, labels)
        return re.split(r"[,;/|]+", value) if value else []

    def _title_from_lines(self, lines: Sequence[str]) -> str:
        title_words = re.compile(
            r"\b(developer|engineer|analyst|designer|manager|specialist|architect|scientist|administrator)\b",
            re.IGNORECASE,
        )
        for line in lines[:6]:
            clean = self._clean(re.sub(r"^(hiring|job|vacancy|we are hiring)\s*[:\-]\s*", "", line, flags=re.IGNORECASE))
            if title_words.search(clean):
                return clean[:140]
        return self._clean(lines[0] if lines else "", max_length=140)

    def _posts_from_channel_html(
        self,
        handle: str,
        body: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        posts: List[Dict[str, Any]] = []
        pattern = re.compile(
            r'<div class="tgme_widget_message[^"]*"[^>]*data-post="([^"]+)"[^>]*>'
            r"(.*?)(?=<div class=\"tgme_widget_message_wrap|</section>|</body>)",
            re.IGNORECASE | re.DOTALL,
        )

        for match in pattern.finditer(body):
            data_post = html.unescape(match.group(1))
            block = match.group(2)
            text = self._message_text_from_html(block)
            if len(text) < 20:
                continue
            post_handle, message_id = self._split_data_post(data_post, handle)
            posts.append({
                "channel_name": f"@{post_handle}",
                "message_id": message_id,
                "posted_at": self._message_datetime(block) or self.today.isoformat(),
                "raw_text": text,
                "source_ref": f"https://t.me/{post_handle}/{message_id}",
            })

        return posts[-max(1, limit):]

    def _message_text_from_html(self, block: str) -> str:
        match = re.search(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            block,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return ""
        text_html = re.sub(r"<br\s*/?>", "\n", match.group(1), flags=re.IGNORECASE)
        text_html = re.sub(r"</p\s*>", "\n", text_html, flags=re.IGNORECASE)
        text_html = re.sub(r"<[^>]+>", "", text_html)
        return self._clean_multiline(html.unescape(text_html), max_length=5000)

    def _message_datetime(self, block: str) -> str:
        match = re.search(r'<time[^>]+datetime="([^"]+)"', block, re.IGNORECASE)
        return self._date_only(html.unescape(match.group(1))) if match else ""

    def _split_data_post(self, data_post: str, fallback_handle: str) -> Tuple[str, str]:
        if "/" not in data_post:
            return fallback_handle, self._fingerprint_text(data_post)
        channel, message_id = data_post.split("/", 1)
        return self._channel_handle(channel) or fallback_handle, self._clean(message_id, max_length=80)

    def _channel_handle(self, channel: Any) -> str:
        text = str(channel or "").strip()
        text = text.replace("https://t.me/s/", "").replace("https://t.me/", "")
        text = text.lstrip("@").split("/", 1)[0]
        return re.sub(r"[^A-Za-z0-9_]", "", text)

    def _infer_role(self, text: str) -> str:
        category = self._infer_category(text)
        return category.replace("-", " ") if category else ""

    def _infer_category(self, text: str) -> str:
        lowered = text.casefold()
        for category, phrases in ROLE_RULES:
            if any(phrase in lowered for phrase in phrases):
                return category
        if any(word in lowered for word in ("developer", "engineer", "software", "qa", "database")):
            return "Information Technology (IT)"
        return "Other"

    def _infer_seniority(self, text: str) -> str:
        lowered = text.casefold()
        for level, phrases in SENIORITY_RULES:
            if any(phrase in lowered for phrase in phrases):
                return level
        return "mid"

    def _infer_job_type(self, text: str) -> str:
        lowered = text.casefold()
        if "part-time" in lowered or "part time" in lowered:
            return "part-time"
        if "contract" in lowered or "freelance" in lowered:
            return "contract"
        if "internship" in lowered:
            return "internship"
        return "full-time"

    def _infer_location(self, text: str) -> str:
        lowered = text.casefold()
        if "remote" in lowered:
            return "Remote"
        if "hybrid" in lowered:
            return "Hybrid"
        if "onsite" in lowered or "on-site" in lowered:
            return "Onsite"
        return ""

    def _first_url(self, text: str) -> str:
        match = re.search(r"https?://[^\s)>\]]+", text)
        return match.group(0).rstrip(".,") if match else ""

    def _confidence(
        self,
        title: str,
        category: str,
        required_skills: Sequence[str],
        extracted: Dict[str, Any],
    ) -> float:
        score = 0.25
        if title:
            score += 0.2
        if category and category != "Other":
            score += 0.15
        if required_skills:
            score += min(0.25, 0.07 * len(required_skills))
        if extracted.get("location"):
            score += 0.05
        if extracted.get("apply_link"):
            score += 0.05
        if extracted.get("company"):
            score += 0.05
        return round(min(score, 0.98), 2)

    def _date_only(self, value: Any) -> str:
        if not value:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
            return text
        try:
            normalized = text.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).date().isoformat()
        except ValueError:
            pass

        clean = re.sub(r"(?i)(\d)(st|nd|rd|th)\b", r"\1", text)
        clean = re.sub(r"\s+", " ", clean).strip(" .,:;-")
        formats = (
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%m-%d-%Y",
            "%B %d",
            "%b %d",
            "%d %B",
            "%d %b",
        )
        for fmt in formats:
            try:
                parsed = datetime.strptime(clean, fmt).date()
                if "%Y" not in fmt:
                    parsed = parsed.replace(year=self.today.year)
                return parsed.isoformat()
            except ValueError:
                continue
        return ""

    def _extract_deadline_date(self, text: str) -> str:
        date_pattern = (
            r"(\d{4}-\d{1,2}-\d{1,2}|"
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
            r"[A-Za-z]{3,9}\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?|"
            r"\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}(?:\s+\d{4})?)"
        )
        label_pattern = (
            r"(?:deadline|closing date|application deadline|apply before|"
            r"apply by|due date|until|before)"
        )
        for match in re.finditer(
            rf"{label_pattern}\s*[:\-]?\s*{date_pattern}",
            text,
            re.IGNORECASE,
        ):
            parsed = self._date_only(match.group(1))
            if parsed:
                return parsed
        return ""

    def _is_expired(self, job: Dict[str, Any]) -> bool:
        deadline = self._date_only(job.get("deadline_date") or job.get("deadline"))
        if not deadline:
            return False
        try:
            return date.fromisoformat(deadline) < self.today
        except ValueError:
            return False

    def _lines(self, value: str) -> List[str]:
        return [
            self._clean(re.sub(r"^[\-\*\u2022\s]+", "", line))
            for line in value.splitlines()
            if self._clean(line)
        ]

    def _clean(self, value: Any, max_length: int = 500) -> str:
        if value is None:
            return ""
        text = re.sub(r"\s+", " ", str(value)).strip()
        return text[:max_length]

    def _clean_multiline(self, value: Any, max_length: int = 5000) -> str:
        if value is None:
            return ""
        text = str(value).replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        compact = "\n".join(line for line in lines if line)
        return compact[:max_length]

    def _fingerprint_text(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]

    def _search_blob(self, job: Dict[str, Any]) -> str:
        values = [
            job.get("job_title"),
            job.get("company"),
            job.get("location"),
            job.get("salary"),
            job.get("source_channel"),
            " ".join(job.get("required_skill_names") or []),
            job.get("raw_text"),
        ]
        return " ".join(str(value or "") for value in values).casefold()

    def _matches_role_filter(self, job: Dict[str, Any], role_text: str) -> bool:
        role_values = [
            job.get("category"),
            job.get("role"),
            job.get("job_title"),
            job.get("title"),
            job.get("company"),
            job.get("description"),
            " ".join(job.get("required_skill_names") or []),
            " ".join(job.get("required_skills") or []),
        ]
        blob = " ".join(str(value or "") for value in role_values).casefold()
        normalized_role = role_text.replace("_", " ").replace("-", " ")
        normalized_blob = blob.replace("_", " ").replace("-", " ")
        return role_text in blob or normalized_role in normalized_blob

    def _ensure_apply_target(self, job: Dict[str, Any]) -> Dict[str, Any]:
        output = dict(job)
        fallback = output.get("source_ref") or output.get("url")
        if not output.get("apply_link") and fallback:
            output["apply_link"] = fallback
        if not output.get("url") and output.get("apply_link"):
            output["url"] = output["apply_link"]
        return output

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
