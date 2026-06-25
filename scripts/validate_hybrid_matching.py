"""Validate Step 7 hybrid matching against the project job database."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.recommender import MATCH_WEIGHTS, RecommendationEngine


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
        raise SystemExit("No recommendations were returned.")
    if [item["job_id"] for item in results] != [
        item["job_id"] for item in repeated
    ]:
        raise SystemExit("Repeated matching did not produce stable ordering.")

    expected_factors = set(MATCH_WEIGHTS)
    for result in results:
        if not expected_factors <= set(result["weighted_contributions"]):
            raise SystemExit(
                f"Missing weighted factors for {result['job_id']}."
            )
        contribution_total = sum(result["weighted_contributions"].values())
        if abs(contribution_total - result["match_score"]) > 0.2:
            raise SystemExit(
                f"Contribution total mismatch for {result['job_id']}."
            )
        if not result.get("explanation"):
            raise SystemExit(f"Missing explanation for {result['job_id']}.")

    output = {
        "engine": engine.info(),
        "stable_ordering": True,
        "top_results": [
            {
                "job_id": item["job_id"],
                "title": item["job_title"],
                "match_score": item["match_score"],
                "matched_skills": item["matched_skill_names"],
                "missing_skills": item["missing_skill_names"],
                "breakdown": item["breakdown"],
                "explanation": item["explanation"],
            }
            for item in results[:5]
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
