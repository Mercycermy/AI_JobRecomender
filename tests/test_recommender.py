"""
Tests for the RecommendationEngine.
"""

import os
import sys
import time

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
    engine = RecommendationEngine()

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
    engine = RecommendationEngine()
    engine.index = None
    engine.model = None
    engine.job_ids = []

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


def test_engine_loads_with_vectors():
    if not _vector_stack_ready():
        print("SKIP test_engine_loads_with_vectors (run seed_db.py + build_vectors.py)")
        return

    engine = RecommendationEngine()
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

    assert elapsed_ms < 100, (
        f"rank_jobs took {elapsed_ms:.1f}ms; expected < 100ms after model/index load"
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
