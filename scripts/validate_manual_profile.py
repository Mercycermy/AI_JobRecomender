"""Validate the evidence-aware manual profile flow."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.profile_service import ProfileService


def main() -> int:
    service = ProfileService()
    low_evidence = service.from_payload(
        {
            "skills": ["Python", "React", "Unknown Future Skill"],
            "skill_levels": {
                "Python": "beginner",
                "React": "advanced",
            },
            "experience": "junior",
            "category": "backend-dev",
        }
    )
    strong_evidence = service.from_payload(
        {
            "skills": ["Python", "React"],
            "skill_levels": {
                "Python": "beginner",
                "React": "advanced",
            },
            "experience": "junior",
            "experience_years": 2,
            "has_projects": True,
            "portfolio_url": "https://example.com/portfolio",
            "category": "backend-dev",
        }
    )
    suggestions = service.suggest_skills("pyth")

    report = {
        "skill_ids": strong_evidence.skill_ids,
        "skill_scores": strong_evidence.skill_scores,
        "overall_score": strong_evidence.overall_score,
        "low_evidence_confidence": low_evidence.confidence,
        "strong_evidence_confidence": strong_evidence.confidence,
        "unresolved_skills": low_evidence.evidence["unresolved_skills"],
        "suggestions": suggestions["suggestions"][:3],
    }
    print(json.dumps(report, indent=2))

    errors = bool(
        strong_evidence.skill_scores.get("lang-py") != 0.4
        or strong_evidence.skill_scores.get("fe-react") != 0.82
        or strong_evidence.confidence <= low_evidence.confidence
        or low_evidence.evidence["unresolved_skills"] != ["Unknown Future Skill"]
        or not suggestions["suggestions"]
        or suggestions["suggestions"][0]["skill_id"] != "lang-py"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
