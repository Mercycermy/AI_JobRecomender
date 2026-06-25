import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.profile_service import ProfileService, ProfileValidationError


def test_manual_payload_is_normalized_to_canonical_skill_ids():
    service = ProfileService()
    profile = service.from_payload(
        {
            "detected_skills": ["Python", "SQL", "React"],
            "experience_level": "mid",
            "top_category": "backend-dev",
            "location": "remote",
        }
    )

    assert profile.source == "manual"
    assert profile.experience_level == "mid"
    assert profile.target_role == "backend-dev"
    assert "lang-py" in profile.skill_ids
    assert all(0 <= score <= 1 for score in profile.skill_scores.values())


def test_quiz_payload_uses_same_canonical_profile_type():
    service = ProfileService()
    profile = service.from_payload(
        {
            "source": "quiz",
            "session_id": "session-1",
            "detected_domain": "DATA_AI",
            "detected_role": "data-analyst",
            "detected_skills": ["lang-py", "data-sql"],
            "skill_scores": {"lang-py": [0.6, 0.8], "data-sql": 0.9},
            "confidence": 75,
        }
    )

    assert profile.source == "quiz"
    assert profile.skill_scores["lang-py"] == 0.7
    assert profile.confidence == 0.75
    assert service.to_recommender_input(profile)["skill_ids"] == profile.skill_ids


def test_invalid_manual_skills_are_rejected():
    service = ProfileService()

    with pytest.raises(ProfileValidationError):
        service.from_payload({"skills": "Python, SQL"})


def test_manual_skill_levels_create_realistic_scores():
    service = ProfileService()
    profile = service.from_payload(
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
        }
    )

    assert profile.skill_scores["lang-py"] == 0.4
    assert profile.skill_scores["fe-react"] == 0.82
    assert profile.overall_score == 0.61
    assert profile.evidence["experience_years"] == 2.0
    assert profile.evidence["has_projects"] is True
    assert profile.confidence >= 0.75


def test_manual_profile_preserves_unresolved_skill_feedback():
    service = ProfileService()
    profile = service.from_payload(
        {
            "skills": ["Python", "Unknown Future Skill"],
            "skill_levels": {"Python": "intermediate"},
        }
    )

    assert profile.skill_ids == ["lang-py"]
    assert profile.evidence["unresolved_skills"] == ["Unknown Future Skill"]


def test_skill_suggestions_return_taxonomy_metadata():
    service = ProfileService()
    result = service.suggest_skills("pyth")

    assert result["suggestions"][0]["skill_id"] == "lang-py"
    assert result["suggestions"][0]["skill_name"] == "Python"
    assert result["suggestions"][0]["domain"]


def test_serialized_manual_profile_stays_manual_when_reloaded():
    service = ProfileService()
    original = service.from_payload(
        {
            "skills": ["Python"],
            "skill_levels": {"Python": "advanced"},
            "experience_years": 2,
            "has_projects": True,
        }
    )
    reloaded = service.from_payload(service.serialize(original))

    assert reloaded.source == "manual"
    assert reloaded.skill_scores == original.skill_scores
    assert reloaded.evidence["has_projects"] is True
