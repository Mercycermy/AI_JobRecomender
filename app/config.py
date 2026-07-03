"""Central application configuration.

Environment-dependent paths and settings live here so service modules do not
each invent their own configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


BASE_DIR = Path(__file__).resolve().parent.parent


def _csv_env(name: str, default: str) -> Tuple[str, ...]:
    raw = os.environ.get(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _path_env(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser() if raw else default


@dataclass(frozen=True)
class AppConfig:
    base_dir: Path = BASE_DIR
    app_env: str = field(
        default_factory=lambda: os.environ.get("APP_ENV", "development").lower()
    )
    data_dir: Path = field(
        default_factory=lambda: _path_env("DATA_DIR", BASE_DIR / "data")
    )
    recommender_db_path: Path = field(
        default_factory=lambda: _path_env(
            "RECOMMENDER_DB_PATH",
            BASE_DIR / "data" / "db.sqlite3",
        )
    )
    quiz_db_path: Path = field(
        default_factory=lambda: _path_env("QUIZ_DB_PATH", BASE_DIR / "data" / "jobs.db")
    )
    jobs_index_path: Path = field(
        default_factory=lambda: _path_env(
            "JOBS_INDEX_PATH",
            BASE_DIR / "data" / "jobs_faiss.index",
        )
    )
    jobs_id_map_path: Path = field(
        default_factory=lambda: _path_env(
            "JOBS_ID_MAP_PATH",
            BASE_DIR / "data" / "jobs_id_map.json",
        )
    )
    telegram_jobs_feed_path: Path = field(
        default_factory=lambda: _path_env(
            "TELEGRAM_JOBS_FEED_PATH",
            BASE_DIR / "data" / "telegram_jobs.json",
        )
    )
    taxonomy_path: Path = field(
        default_factory=lambda: _path_env(
            "TAXONOMY_PATH",
            BASE_DIR / "data" / "skills_taxonomy.json",
        )
    )
    resources_path: Path = field(
        default_factory=lambda: _path_env(
            "LEARNING_RESOURCES_PATH",
            BASE_DIR / "data" / "learning_resources.json",
        )
    )
    embedding_model: str = field(
        default_factory=lambda: os.environ.get(
            "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
    )
    secret_key: str = field(
        default_factory=lambda: os.environ.get("FLASK_SECRET_KEY", "")
    )
    api_key: str = field(default_factory=lambda: os.environ.get("API_KEY", ""))
    admin_access_key: str = field(
        default_factory=lambda: os.environ.get("ADMIN_ACCESS_KEY", "admin-local-access")
    )
    require_api_key: bool = field(
        default_factory=lambda: _bool_env("REQUIRE_API_KEY", False)
    )
    cors_origins: Tuple[str, ...] = field(
        default_factory=lambda: _csv_env(
            "CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        )
    )
    host: str = field(
        default_factory=lambda: os.environ.get("HOST", "127.0.0.1")
    )
    port: int = field(
        default_factory=lambda: int(os.environ.get("PORT", "5000"))
    )
    debug: bool = field(
        default_factory=lambda: os.environ.get("FLASK_DEBUG") == "1"
    )
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO").upper()
    )
    max_content_length: int = field(
        default_factory=lambda: _int_env("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)
    )
    rate_limit_enabled: bool = field(
        default_factory=lambda: _bool_env("RATE_LIMIT_ENABLED", True)
    )
    rate_limit_public_per_minute: int = field(
        default_factory=lambda: _int_env("RATE_LIMIT_PUBLIC_PER_MINUTE", 120)
    )
    rate_limit_write_per_minute: int = field(
        default_factory=lambda: _int_env("RATE_LIMIT_WRITE_PER_MINUTE", 30)
    )
    run_migrations_on_startup: bool = field(
        default_factory=lambda: _bool_env("RUN_MIGRATIONS_ON_STARTUP", True)
    )

    @property
    def is_production(self) -> bool:
        return self.app_env in {"prod", "production"}

    @property
    def effective_secret_key(self) -> str:
        if self.secret_key:
            return self.secret_key
        return "local-dev-secret-do-not-use-in-production"

    def validate_startup(self) -> None:
        errors = []
        if self.is_production and not self.secret_key:
            errors.append("FLASK_SECRET_KEY must be set in production.")
        if self.is_production and "*" in self.cors_origins:
            errors.append("CORS_ORIGINS cannot contain '*' in production.")
        if self.is_production and not self.admin_access_key:
            errors.append("ADMIN_ACCESS_KEY must be set in production.")
        if self.require_api_key and not self.api_key:
            errors.append("API_KEY must be set when REQUIRE_API_KEY=1.")
        if self.rate_limit_public_per_minute < 1:
            errors.append("RATE_LIMIT_PUBLIC_PER_MINUTE must be at least 1.")
        if self.rate_limit_write_per_minute < 1:
            errors.append("RATE_LIMIT_WRITE_PER_MINUTE must be at least 1.")
        if errors:
            raise RuntimeError("Invalid application configuration: " + " ".join(errors))


settings = AppConfig()
