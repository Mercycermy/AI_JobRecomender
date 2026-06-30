"""Validate Step 10 learning-resource ranking for skill gaps."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.gap_analyzer import GapAnalyzer
from app.learning_path import LearningPath


def main() -> None:
    profile = {
        "skill_ids": ["lang-py"],
        "skill_scores": {"lang-py": 0.82},
        "target_role": "backend-dev",
    }
    recommendations = [
        {
            "job_id": "job-backend-1",
            "job_title": "Backend Developer",
            "match_percent": 72,
            "missing_skills": ["ops-docker", "lang-sql"],
        },
        {
            "job_id": "job-backend-2",
            "job_title": "API Developer",
            "match_percent": 68,
            "missing_skills": ["ops-docker"],
        },
    ]

    gaps = GapAnalyzer().analyze(profile, recommendations, top_n=2, limit=4)
    if not gaps:
        raise SystemExit("No gaps were produced for learning resources.")

    groups = LearningPath().recommend_resources(gaps, limit_per_skill=3)
    if not groups:
        raise SystemExit("No learning resources were returned.")

    resource_skills = {group["skill_id"] for group in groups}
    expected_skills = {"ops-docker", "lang-sql"}
    missing_skills = expected_skills - resource_skills
    if missing_skills:
        raise SystemExit(f"Missing resources for {sorted(missing_skills)}.")

    priorities = [group.get("priority") or 0 for group in groups]
    if priorities != sorted(priorities, reverse=True):
        raise SystemExit("Resource groups are not ordered by gap priority.")

    for group in groups:
        resources = group.get("resources") or []
        if not resources:
            raise SystemExit(f"No resources for {group['skill_id']}.")
        scores = [resource["recommendation_score"] for resource in resources]
        if scores != sorted(scores, reverse=True):
            raise SystemExit(f"Resources for {group['skill_id']} are not ranked.")
        for resource in resources:
            required_fields = {
                "title",
                "platform",
                "level",
                "hours",
                "is_free",
                "cost",
                "link",
                "explanation",
                "recommendation_score",
            }
            missing_fields = [
                field
                for field in required_fields
                if resource.get(field) in (None, "", [])
            ]
            if missing_fields:
                raise SystemExit(
                    f"Resource {resource.get('resource_id')} is missing {missing_fields}."
                )
            if resource["cost"] not in {"free", "paid"}:
                raise SystemExit(f"Invalid resource cost: {resource['cost']}.")

    output = {
        "gap_count": len(gaps),
        "resource_group_count": len(groups),
        "groups": [
            {
                "skill_id": group["skill_id"],
                "skill": group["skill"],
                "priority": group.get("priority"),
                "top_resource": group["resources"][0]["title"],
                "score": group["resources"][0]["recommendation_score"],
                "cost": group["resources"][0]["cost"],
                "explanation": group["resources"][0]["explanation"],
            }
            for group in groups
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
