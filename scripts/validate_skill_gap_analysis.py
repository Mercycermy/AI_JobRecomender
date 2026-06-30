"""Validate Step 9 skill-gap analysis for top matched jobs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.gap_analyzer import GapAnalyzer
from app.recommender import RecommendationEngine


def main() -> None:
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

    recommendations = RecommendationEngine(load_resources=False).rank_jobs(
        profile,
        top_n=8,
    )
    if not recommendations:
        raise SystemExit(
            "No recommendations were returned. Run scripts/seed_db.py first."
        )

    analyzer = GapAnalyzer()
    gaps = analyzer.analyze(profile, recommendations, top_n=5, limit=8)
    if not gaps:
        raise SystemExit("No skill gaps were returned for top recommendations.")

    priorities = [gap["priority"] for gap in gaps]
    if priorities != sorted(priorities, reverse=True):
        raise SystemExit("Skill gaps are not sorted by priority.")

    gap_ids = {gap["skill_id"] for gap in gaps}
    for rec in recommendations[:5]:
        missing = set(rec.get("missing_skills") or [])
        if missing and not (missing & gap_ids):
            raise SystemExit(
                f"No top gap references missing skills for {rec['job_id']}."
            )

    for gap in gaps:
        required_fields = {
            "skill_id",
            "skill",
            "priority",
            "priority_label",
            "priority_group",
            "current",
            "required",
            "current_level",
            "required_level",
            "affected_jobs",
            "learning_path",
            "first_action",
        }
        missing_fields = required_fields - set(gap)
        if missing_fields:
            raise SystemExit(
                f"Gap {gap.get('skill_id')} is missing {sorted(missing_fields)}."
            )
        if gap["current"] >= gap["required"]:
            raise SystemExit(f"Gap {gap['skill_id']} has no level delta.")
        if not gap["affected_jobs"]:
            raise SystemExit(f"Gap {gap['skill_id']} has no affected jobs.")
        if len(gap["learning_path"]) < 3:
            raise SystemExit(f"Gap {gap['skill_id']} has an incomplete path.")

    output = {
        "top_job_count": len(recommendations[:5]),
        "gap_count": len(gaps),
        "top_gaps": [
            {
                "skill_id": gap["skill_id"],
                "skill": gap["skill"],
                "priority": gap["priority"],
                "priority_group": gap["priority_group"],
                "current": gap["current"],
                "required": gap["required"],
                "affected_jobs": [
                    job["title"]
                    for job in gap["affected_jobs"][:3]
                ],
                "first_action": gap["first_action"],
            }
            for gap in gaps[:5]
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
