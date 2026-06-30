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


@dataclass(frozen=True)
class AppConfig:
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    recommender_db_path: Path = BASE_DIR / "data" / "db.sqlite3"
    quiz_db_path: Path = BASE_DIR / "data" / "jobs.db"
    jobs_index_path: Path = BASE_DIR / "data" / "jobs_faiss.index"
    jobs_id_map_path: Path = BASE_DIR / "data" / "jobs_id_map.json"
    telegram_jobs_feed_path: Path = BASE_DIR / "data" / "telegram_jobs.json"
    taxonomy_path: Path = BASE_DIR / "data" / "skills_taxonomy.json"
    resources_path: Path = BASE_DIR / "data" / "learning_resources.json"
    embedding_model: str = field(
        default_factory=lambda: os.environ.get(
            "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
    )
    secret_key: str = field(
        default_factory=lambda: os.environ.get(
            "FLASK_SECRET_KEY", "dev-secret-change-me"
        )
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


settings = AppConfig()
