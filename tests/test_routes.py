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
