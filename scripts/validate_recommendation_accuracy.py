"""Validate Step 8 two-stage retrieval and reranking behavior."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.recommender import RecommendationEngine


def main() -> None:
    engine = RecommendationEngine(load_resources=False)
    profile = {
        "skill_ids": [
            "lang-py",
            "be-fastapi",
            "be-rest",
            "ops-docker",
            "lang-sql",
        ],
        "skill_scores": {
            "lang-py": 0.82,
            "be-fastapi": 0.65,
            "be-rest": 0.65,
            "ops-docker": 0.65,
            "lang-sql": 0.65,
        },
        "experience_level": "mid",
        "target_role": "backend-dev",
        "location": "remote",
    }

    results = engine.rank_jobs(profile, top_n=10)
    repeated = engine.rank_jobs(profile, top_n=10)
    if not results:
        raise SystemExit(
            "No recommendations were returned. Run scripts/seed_db.py first."
        )
    if [item["job_id"] for item in results] != [
        item["job_id"] for item in repeated
    ]:
        raise SystemExit("Repeated matching did not produce stable ordering.")

    info = engine.info()
    if info["candidate_count"] < len(results):
        raise SystemExit("Candidate count is smaller than displayed results.")
    if not info.get("retrieval_sources"):
        raise SystemExit("No candidate retrieval sources were recorded.")
    if not any(
        source in info["retrieval_sources"]
        for source in ("exact_skill_overlap", "semantic_embedding")
    ):
        raise SystemExit("No skill or embedding candidate source was used.")

    top_five = results[:5]
    if not any(item.get("matched_skills") for item in top_five):
        raise SystemExit("Top results do not show exact skill overlap.")
    if not any(
        "backend" in str(item.get("job_title", "")).lower()
        or item.get("category") == "backend-dev"
        for item in top_five
    ):
        raise SystemExit("Top results do not look relevant to backend-dev.")

    required_rerank_factors = {
        "exact_skill_overlap",
        "seniority_fit",
        "location_fit",
        "semantic_similarity",
    }
    for result in results:
        if result.get("job_validated") is not True:
            raise SystemExit(f"Job was not validated: {result['job_id']}")
        if result.get("validation_errors"):
            raise SystemExit(
                f"Validation errors leaked for {result['job_id']}."
            )
        if not result.get("retrieval_sources"):
            raise SystemExit(f"Missing retrieval sources for {result['job_id']}.")
        if required_rerank_factors - set(result.get("rerank_factors", {})):
            raise SystemExit(f"Missing rerank factors for {result['job_id']}.")

    output = {
        "engine": info,
        "stable_ordering": True,
        "top_results": [
            {
                "job_id": item["job_id"],
                "title": item["job_title"],
                "match_percent": item["match_percent"],
                "retrieval_sources": item["retrieval_sources"],
                "rerank_factors": item["rerank_factors"],
                "matched_skills": item["matched_skill_names"],
                "missing_skills": item["missing_skill_names"][:5],
            }
            for item in top_five
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
