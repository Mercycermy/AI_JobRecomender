"""
Smoke tests for Flask API routes.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

pytest.importorskip("flask")

from app.routes import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_recommend_requires_body(client):
    response = client.post("/recommend", json={})
    assert response.status_code == 200
    data = response.get_json()
    assert "recommendations" in data


def test_recommend_with_profile(client):
    response = client.post(
        "/recommend",
        json={
            "skills": ["python", "sql"],
            "experience": "junior",
            "category": "backend-dev",
            "location": "remote",
            "top_n": 3,
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "recommendations" in data
    assert data["count"] <= 3
    assert data["skill_profile"]["source"] == "manual"
    assert "lang-py" in data["skill_profile"]["skill_ids"]
    assert data["engine"]["retrieval_mode"] in {
        "database",
        "semantic+database",
    }
    assert data["engine"]["weights"]["skill_fit"] == 40
    if data["recommendations"]:
        first = data["recommendations"][0]
        assert "explanation" in first
        assert "weighted_contributions" in first
        assert "freshness" in first["breakdown"]
        assert "role_match" in first["breakdown"]


def test_normalize_manual_profile(client):
    response = client.post(
        "/profile/normalize",
        json={
            "skills": ["Python", "SQL", "React"],
            "experience": "junior",
            "category": "backend-dev",
            "location": "remote",
        },
    )

    assert response.status_code == 200
    profile = response.get_json()["skill_profile"]
    assert profile["source"] == "manual"
    assert profile["target_role"] == "backend-dev"
    assert "lang-py" in profile["skill_ids"]
    assert profile["detected_skills"] == profile["skill_ids"]


def test_normalize_quiz_profile(client):
    response = client.post(
        "/profile/normalize",
        json={
            "source": "quiz",
            "session_id": "quiz-test",
            "detected_domain": "SOFTWARE",
            "detected_role": "backend-dev",
            "detected_skills": ["lang-py"],
            "skill_scores": {"lang-py": 0.8},
            "experience_level": "junior",
            "confidence": 80,
        },
    )

    assert response.status_code == 200
    profile = response.get_json()["skill_profile"]
    assert profile["source"] == "quiz"
    assert profile["detected_role"] == "backend-dev"
    assert profile["skill_scores"]["lang-py"] == 0.8
    assert profile["confidence"] == 0.8


def test_normalize_rejects_non_list_skills(client):
    response = client.post(
        "/profile/normalize",
        json={"skills": "Python, SQL"},
    )

    assert response.status_code == 400
    assert "skills must be a list" in response.get_json()["error"]


def test_normalize_skill_phrases_reports_matches_and_unknowns(client):
    response = client.post(
        "/skills/normalize",
        json={
            "skills": [
                "HTML/CSS/JavaScript",
                "Built REST APIs with Python and Docker",
                "Unknown Future Skill",
            ]
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert {"fe-html", "fe-css", "lang-js", "be-rest", "lang-py", "ops-docker"} <= set(
        data["skill_ids"]
    )
    assert data["unresolved"] == ["Unknown Future Skill"]


def test_skill_suggestions_endpoint(client):
    response = client.get("/skills/suggest?q=react&limit=5")

    assert response.status_code == 200
    suggestions = response.get_json()["suggestions"]
    assert suggestions
    assert suggestions[0]["skill_id"] == "fe-react"


def test_recommend_manual_profile_returns_evidence_aware_scores(client):
    response = client.post(
        "/recommend",
        json={
            "skills": ["Python", "React", "Unknown Future Skill"],
            "skill_levels": {
                "Python": "beginner",
                "React": "advanced",
            },
            "experience": "junior",
            "experience_years": 1.5,
            "has_projects": True,
            "portfolio_url": "https://example.com/work",
            "category": "backend-dev",
            "top_n": 1,
        },
    )

    assert response.status_code == 200
    profile = response.get_json()["skill_profile"]
    assert profile["skill_scores"]["lang-py"] == 0.4
    assert profile["skill_scores"]["fe-react"] == 0.82
    assert profile["evidence"]["unresolved_skills"] == ["Unknown Future Skill"]
    assert profile["evidence"]["has_projects"] is True


def test_manual_profile_analysis_does_not_require_quiz_session(client):
    response = client.post(
        "/analysis",
        json={
            "skill_profile": {
                "source": "manual",
                "skills": ["Python"],
                "skill_levels": {"Python": "advanced"},
                "category": "backend-dev",
            },
            "recommendations": [
                {
                    "job_id": "job-test",
                    "missing_skills": ["ops-docker", "lang-sql"],
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["gaps"]
    assert {gap["skill_id"] for gap in data["gaps"]} == {
        "ops-docker",
        "lang-sql",
    }
    assert "resources" in data


def test_manual_profile_resume_tips_do_not_require_quiz_session(client):
    response = client.post(
        "/resume-tips",
        json={
            "skill_profile": {
                "source": "manual",
                "skills": ["Python"],
                "skill_levels": {"Python": "advanced"},
                "category": "backend-dev",
            },
            "recommendations": [
                {
                    "job_id": "job-test",
                    "missing_skills": ["ops-docker"],
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["tips"]
    assert data["schedule"]
    assert data["is_ai"] is False


def test_cors_only_allows_configured_frontend(client):
    allowed = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    denied = client.get(
        "/health",
        headers={"Origin": "https://untrusted.example"},
    )

    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "Access-Control-Allow-Origin" not in denied.headers


def test_resume_tips_fallback(client):
    from app.quiz_engine import QuizEngine
    engine = QuizEngine()
    session = engine.create_session()

    response = client.post(
        "/resume-tips",
        json={
            "session_id": session["session_id"]
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "tips" in data
    assert "schedule" in data
    assert "summary" in data
    assert data["is_ai"] is False  # No GROQ_API_KEY in test environment


