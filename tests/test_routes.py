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


