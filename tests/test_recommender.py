"""
Tests for the RecommendationEngine.
"""

import os
import sqlite3
import sys
import time
from datetime import date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.recommender import (
    RecommendationEngine,
    INDEX_PATH,
    MAPPER_PATH,
    DB_PATH,
)


def _vector_stack_ready() -> bool:
    return (
        os.path.exists(DB_PATH)
        and os.path.exists(INDEX_PATH)
        and os.path.exists(MAPPER_PATH)
    )


@pytest.fixture(scope="module")
def warm_recommendation_engine():
    """Load model/index once per module; warm up encode+search path."""
    if not _vector_stack_ready():
        return None
    engine = RecommendationEngine()
    if engine.model is None:
        return None
    engine.rank_jobs(
        {
            "skills": ["python"],
            "experience": "junior",
            "category": "backend-dev",
            "location": "remote",
        },
        top_n=1,
    )
    return engine


def test_experience_weight():
    engine = RecommendationEngine(load_resources=False)

    assert engine._get_experience_weight("senior", "mid") == 1.0
    assert engine._get_experience_weight("mid", "mid") == 1.0
    assert engine._get_experience_weight("junior", "intern") == 1.0
    assert engine._get_experience_weight("senior", "intern") == 1.0

    assert engine._get_experience_weight("junior", "mid") == 0.5
    assert engine._get_experience_weight("mid", "senior") == 0.5
    assert engine._get_experience_weight("intern", "junior") == 0.5

    assert engine._get_experience_weight("intern", "mid") == 0.1
    assert engine._get_experience_weight("junior", "senior") == 0.1

    assert engine._get_experience_weight("intern", "senior") == 0.0


def test_rank_jobs_fallback():
    engine = RecommendationEngine(load_resources=False)

    profile = {
        "skills": ["python", "sql", "git"],
        "experience": "mid",
        "category": "backend-dev",
        "location": "remote",
    }

    results = engine.rank_jobs(profile, top_n=5)

    assert isinstance(results, list)
    if len(results) > 0:
        first = results[0]
        assert "job_id" in first
        assert "job_title" in first
        assert "match_score" in first
        assert "breakdown" in first


def test_explainable_hybrid_score_contains_all_factors():
    engine = RecommendationEngine(
        load_resources=False,
        today=date(2026, 6, 26),
    )
    result = engine._score_job(
        job={
            "job_id": "job-score-test",
            "job_title": "Backend Python Engineer",
            "description": "Build REST APIs with Python, FastAPI, and Docker.",
            "category": "backend-dev",
            "source": "test",
            "exp_level": "mid",
            "job_type": "full-time",
            "location": "Remote",
            "date_added": "2026-06-20",
        },
        required_skills={"lang-py", "be-fastapi", "ops-docker"},
        user_skills={"lang-py", "be-fastapi"},
        skill_scores={"lang-py": 0.82, "be-fastapi": 0.65},
        user_exp="mid",
        target_role="backend-dev",
        location_pref="remote",
    )

    assert {
        "skill_fit",
        "semantic_similarity",
        "experience_match",
        "role_match",
        "location_match",
        "freshness",
    } <= set(result["breakdown"])
    assert abs(
        sum(result["weighted_contributions"].values())
        - result["match_score"]
    ) <= 0.2
    assert result["match_percent"] == result["match_score"]
    assert result["matched_skill_names"] == ["Python", "FastAPI"]
    assert result["missing_skill_names"] == ["Docker"]
    assert "Main skills to develop: Docker." in result["explanation"]


def test_score_jobs_ranks_supplied_telegram_jobs_with_same_formula():
    engine = RecommendationEngine(
        load_resources=False,
        today=date(2026, 6, 30),
    )
    profile = {
        "skill_ids": ["da-powerbi", "da-excel", "lang-sql"],
        "skill_scores": {"da-powerbi": 0.85, "da-excel": 0.8, "lang-sql": 0.75},
        "experience_level": "junior",
        "target_role": "data-analyst",
        "location": "remote",
    }
    results = engine.score_jobs(
        profile,
        [
            {
                "job_id": "telegram-data",
                "job_title": "Power BI Dashboard Analyst",
                "description": "Build dashboards with Power BI, Excel, and SQL.",
                "category": "data-analyst",
                "source": "Telegram: data_jobs",
                "source_channel": "data_jobs",
                "required_skills": ["da-powerbi", "da-excel", "lang-sql"],
                "exp_level": "junior",
                "location": "Remote",
                "posted_at": "2026-06-30",
            },
            {
                "job_id": "telegram-sales",
                "job_title": "Sales Representative",
                "description": "Grow customer accounts and manage field sales.",
                "category": "sales-representative",
                "source": "Telegram: sales_jobs",
                "source_channel": "sales_jobs",
                "required_skills": ["sales-crm"],
                "exp_level": "junior",
                "location": "Remote",
                "posted_at": "2026-06-30",
            },
        ],
        top_n=2,
        source_label="telegram_feed",
    )

    assert [item["job_id"] for item in results] == ["telegram-data", "telegram-sales"]
    assert results[0]["match_score"] > results[1]["match_score"]
    assert results[0]["matched_skill_names"] == ["SQL", "Power BI", "Excel"]
    assert "telegram_feed" in results[0]["retrieval_sources"]


def test_location_and_freshness_are_real_scoring_signals():
    engine = RecommendationEngine(
        load_resources=False,
        today=date(2026, 6, 26),
    )

    assert engine._location_score("Nairobi", "Nairobi, Kenya") == 1.0
    assert engine._location_score("Nairobi", "Remote") == 0.75
    assert engine._location_score("remote", "Addis Ababa") == 0.25
    assert engine._freshness_score("2026-06-24") == 1.0
    assert engine._freshness_score("2026-05-20") == 0.75
    assert engine._freshness_score("2025-01-01") == 0.2


def test_data_analyst_role_family_recognizes_data_collection_titles():
    engine = RecommendationEngine(load_resources=False)

    score = engine._role_score(
        "data-analyst",
        {
            "job_title": "Baseline Data Enumerator",
            "category": "Information Technology (IT)",
        },
    )

    assert score >= 0.9


def test_database_ranking_is_deterministic_and_explainable():
    engine = RecommendationEngine(load_resources=False)
    profile = {
        "skill_ids": ["lang-py", "be-fastapi", "be-rest", "ops-docker"],
        "skill_scores": {
            "lang-py": 0.82,
            "be-fastapi": 0.65,
            "be-rest": 0.65,
            "ops-docker": 0.65,
        },
        "experience_level": "mid",
        "target_role": "backend-dev",
        "location": "remote",
    }

    first = engine.rank_jobs(profile, top_n=5)
    second = engine.rank_jobs(profile, top_n=5)

    assert first
    assert [item["job_id"] for item in first] == [
        item["job_id"] for item in second
    ]
    assert [item["match_score"] for item in first] == sorted(
        (item["match_score"] for item in first),
        reverse=True,
    )
    assert all(item["explanation"] for item in first)
    assert all(item["score_weights"] for item in first)


def test_rank_jobs_exposes_two_stage_retrieval_metadata():
    engine = RecommendationEngine(load_resources=False)
    profile = {
        "skill_ids": ["lang-py", "be-fastapi", "be-rest", "ops-docker"],
        "skill_scores": {
            "lang-py": 0.82,
            "be-fastapi": 0.65,
            "be-rest": 0.65,
            "ops-docker": 0.65,
        },
        "experience_level": "mid",
        "target_role": "backend-dev",
        "location": "remote",
    }

    results = engine.rank_jobs(profile, top_n=5)
    info = engine.info()

    assert results
    assert info["candidate_count"] >= len(results)
    assert info["retrieval_sources"]["exact_skill_overlap"] > 0
    first = results[0]
    assert first["job_validated"] is True
    assert first["validation_errors"] == []
    assert first["retrieval_sources"]
    assert {
        "exact_skill_overlap",
        "seniority_fit",
        "location_fit",
        "semantic_similarity",
    } <= set(first["rerank_factors"])


def test_retrieval_includes_telegram_jobs_and_filters_invalid_jobs(tmp_path):
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
    conn.executemany(
        """
        INSERT INTO jobs (
            job_id, job_title, description, category, source,
            exp_level, job_type, location, date_added
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                "telegram-backend",
                "Backend Developer",
                "Build Python APIs from Telegram job feed.",
                "backend-dev",
                "Telegram",
                "mid",
                "full-time",
                "Remote",
                "2026-06-29",
            ),
            (
                "board-backend",
                "Backend Developer",
                "Build Python APIs from job board data.",
                "backend-dev",
                "Job Board",
                "mid",
                "full-time",
                "Remote",
                "2026-06-28",
            ),
            (
                "invalid-job",
                "",
                "This row has skills but no display title.",
                "backend-dev",
                "Job Board",
                "mid",
                "full-time",
                "Remote",
                "2026-06-28",
            ),
        ],
    )
    conn.executemany(
        "INSERT INTO job_skills (job_id, skill_id, is_required) VALUES (?,?,1)",
        [
            ("telegram-backend", "lang-py"),
            ("telegram-backend", "be-rest"),
            ("board-backend", "lang-py"),
            ("invalid-job", "lang-py"),
            ("invalid-job", "be-rest"),
        ],
    )
    conn.commit()
    conn.close()

    engine = RecommendationEngine(
        load_resources=False,
        db_path=str(db_path),
        today=date(2026, 6, 30),
    )
    results = engine.rank_jobs(
        {
            "skill_ids": ["lang-py", "be-rest"],
            "skill_scores": {"lang-py": 0.8, "be-rest": 0.7},
            "experience_level": "mid",
            "target_role": "backend-dev",
            "location": "remote",
        },
        top_n=5,
    )

    result_ids = {item["job_id"] for item in results}
    assert "telegram-backend" in result_ids
    assert "invalid-job" not in result_ids
    assert engine.info()["retrieval_sources"]["telegram_feed"] == 1
    telegram = next(item for item in results if item["job_id"] == "telegram-backend")
    assert "telegram_feed" in telegram["retrieval_sources"]


def test_engine_loads_with_vectors():
    if not _vector_stack_ready():
        print("SKIP test_engine_loads_with_vectors (run seed_db.py + build_vectors.py)")
        return

    engine = RecommendationEngine()
    if engine.model is None:
        pytest.skip("SentenceTransformer model could not be loaded (likely offline / sandboxed environment)")
    assert engine.model is not None
    assert engine.index is not None
    assert len(engine.job_ids) > 0
    assert engine.index.ntotal == len(engine.job_ids)


def test_rank_jobs_semantic_profile(warm_recommendation_engine):
    if warm_recommendation_engine is None:
        pytest.skip("run seed_db.py + build_vectors.py")

    engine = warm_recommendation_engine
    profile = {
        "detected_skills": ["fastapi", "docker", "rest", "python"],
        "experience_level": "mid",
        "top_category": "backend-dev",
        "location": "remote",
    }

    start = time.perf_counter()
    results = engine.rank_jobs(profile, top_n=10)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert isinstance(results, list)
    assert len(results) > 0

    first = results[0]
    assert first["match_score"] > 0
    assert "breakdown" in first
    assert first["breakdown"]["semantic_similarity"] >= 0

    assert elapsed_ms < 300, (
        f"rank_jobs took {elapsed_ms:.1f}ms; expected < 300ms after model/index load"
    )


def test_semantic_query_returns_backend_roles(warm_recommendation_engine):
    """Profiles with API/backend skills should rank software roles when index exists."""
    if warm_recommendation_engine is None:
        pytest.skip("run seed_db.py + build_vectors.py")

    engine = warm_recommendation_engine
    profile = {
        "skills": ["fastapi", "docker", "rest", "python", "sql"],
        "experience": "mid",
        "category": "backend-dev",
        "location": "remote",
    }
    results = engine.rank_jobs(profile, top_n=5)
    assert len(results) >= 1

    titles = " ".join(r["job_title"].lower() for r in results)
    categories = {r.get("category", "").lower() for r in results}
    backend_signal = (
        "backend" in titles
        or "engineer" in titles
        or "developer" in titles
        or "backend-dev" in categories
    )
    assert backend_signal, f"Expected backend/engineering roles, got: {titles[:200]}"


if __name__ == "__main__":
    test_experience_weight()
    print("✓ test_experience_weight PASSED")

    test_rank_jobs_fallback()
    print("✓ test_rank_jobs_fallback PASSED")

    test_engine_loads_with_vectors()
    print("✓ test_engine_loads_with_vectors PASSED (or skipped)")

    warm = warm_recommendation_engine()
    if warm is not None:
        test_rank_jobs_semantic_profile(warm)
        print("✓ test_rank_jobs_semantic_profile PASSED")
        test_semantic_query_returns_backend_roles(warm)
        print("✓ test_semantic_query_returns_backend_roles PASSED")
    else:
        print("SKIP semantic tests (run seed_db.py + build_vectors.py)")

    print("\n==============================")
    print("RECOMMENDER TESTS PASSED ✓")
