from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import AppConfig
from app.migrations import run_migrations
from app.reliability import rate_limiter
from app.routes import app


@pytest.fixture
def client():
    original = {
        "TESTING": app.config.get("TESTING"),
        "API_KEY": app.config.get("API_KEY"),
        "REQUIRE_API_KEY": app.config.get("REQUIRE_API_KEY"),
        "RATE_LIMIT_ENABLED": app.config.get("RATE_LIMIT_ENABLED"),
        "RATE_LIMIT_PUBLIC_PER_MINUTE": app.config.get("RATE_LIMIT_PUBLIC_PER_MINUTE"),
        "RATE_LIMIT_WRITE_PER_MINUTE": app.config.get("RATE_LIMIT_WRITE_PER_MINUTE"),
    }
    app.config["TESTING"] = True
    app.config["API_KEY"] = ""
    app.config["REQUIRE_API_KEY"] = False
    app.config["RATE_LIMIT_ENABLED"] = False
    rate_limiter.clear()
    with app.test_client() as test_client:
        yield test_client
    app.config.update(original)
    rate_limiter.clear()


def test_production_config_requires_real_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)

    config = AppConfig()

    with pytest.raises(RuntimeError, match="FLASK_SECRET_KEY"):
        config.validate_startup()


def test_json_404_includes_request_id(client):
    response = client.get("/does-not-exist", headers={"X-Request-Id": "req-test"})

    assert response.status_code == 404
    assert response.headers["X-Request-Id"] == "req-test"
    assert response.get_json()["request_id"] == "req-test"


def test_optional_api_key_protects_telegram_write_routes(client):
    app.config["API_KEY"] = "secret-key"

    denied = client.post("/telegram/jobs/ingest", json={"posts": []})
    allowed = client.post(
        "/telegram/jobs/ingest",
        json={"posts": []},
        headers={"X-API-Key": "secret-key"},
    )

    assert denied.status_code == 401
    assert denied.get_json()["error"] == "API key required"
    assert allowed.status_code == 200
    assert allowed.get_json()["received"] == 0


def test_rate_limit_returns_429_json(client):
    app.config["RATE_LIMIT_ENABLED"] = True
    app.config["RATE_LIMIT_PUBLIC_PER_MINUTE"] = 1
    rate_limiter.clear()
    headers = {"X-Forwarded-For": "203.0.113.10"}

    first = client.get("/missing-rate-target", headers=headers)
    second = client.get("/missing-rate-target", headers=headers)

    assert first.status_code == 404
    assert second.status_code == 429
    assert second.get_json()["error"] == "Rate limit exceeded"
    assert second.headers["X-RateLimit-Remaining"] == "0"


def test_runtime_migrations_are_idempotent(tmp_path):
    db_path = tmp_path / "jobs.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            job_title TEXT,
            description TEXT,
            category TEXT,
            source TEXT,
            exp_level TEXT,
            job_type TEXT,
            location TEXT,
            date_added TEXT
        );
        CREATE TABLE job_skills (
            job_id TEXT,
            skill_id TEXT,
            is_required INTEGER DEFAULT 1
        );
        """
    )
    conn.close()

    first = run_migrations(db_path)
    second = run_migrations(db_path)

    assert first["count"] >= 1
    assert second["count"] == 0
    conn = sqlite3.connect(db_path)
    try:
        migration_count = conn.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]
        telegram_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'telegram_posts'"
        ).fetchone()
    finally:
        conn.close()

    assert migration_count == len(first["applied"])
    assert telegram_table is not None
