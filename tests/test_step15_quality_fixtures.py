from __future__ import annotations

import base64
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.gap_analyzer import GapAnalyzer
from app.learning_path import LearningPath
from app.profile_service import ProfileService
from app.recommender import RecommendationEngine
from app.resume_generator import ResumeGeneratorService
from app.telegram_jobs import TelegramJobIngestionService


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "step15"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_step15_manual_profile_fixture_normalizes_stably():
    fixture = _fixture("manual_backend_profile.json")
    expected = fixture["expected"]
    service = ProfileService()

    profile = service.from_payload(fixture["input"])
    serialized = service.serialize(profile)
    reloaded = service.from_payload(serialized)

    assert profile.skill_ids == expected["skill_ids"]
    assert profile.target_role == expected["target_role"]
    assert profile.location == expected["location"]
    assert profile.evidence["unresolved_skills"] == expected["unresolved_skills"]
    assert profile.confidence >= expected["min_confidence"]
    assert profile.skill_scores == expected["skill_scores"]
    assert reloaded.skill_ids == profile.skill_ids
    assert reloaded.skill_scores == profile.skill_scores


def test_step15_matching_gap_and_resource_outputs_are_stable():
    fixture = _fixture("manual_backend_profile.json")
    profile = ProfileService().from_payload(fixture["input"])
    recommender_input = ProfileService().to_recommender_input(profile)
    engine = RecommendationEngine(load_resources=False)

    first = engine.rank_jobs(recommender_input, top_n=6)
    second = engine.rank_jobs(recommender_input, top_n=6)

    assert first
    assert [item["job_id"] for item in first] == [item["job_id"] for item in second]
    assert [item["match_score"] for item in first] == sorted(
        (item["match_score"] for item in first),
        reverse=True,
    )
    assert all(item["job_validated"] is True for item in first)
    assert all(item["validation_errors"] == [] for item in first)
    assert all(item["explanation"] for item in first)

    gaps = GapAnalyzer().analyze(recommender_input, first, top_n=5, limit=5)
    assert gaps
    assert [gap["priority"] for gap in gaps] == sorted(
        (gap["priority"] for gap in gaps),
        reverse=True,
    )

    resource_fixture = _fixture("learning_gap_inputs.json")
    resource_groups = LearningPath().recommend_resources(
        resource_fixture["gaps"],
        limit_per_skill=resource_fixture["expected"]["limit_per_skill"],
    )
    assert resource_groups
    assert [group["skill_id"] for group in resource_groups] == resource_fixture[
        "expected"
    ]["skill_ids"]
    assert all(group["resources"] for group in resource_groups)
    for group in resource_groups:
        scores = [item["recommendation_score"] for item in group["resources"]]
        assert scores == sorted(scores, reverse=True)
        assert group["resources"][0]["link"]
        assert group["resources"][0]["explanation"]


def test_step15_resume_fixture_generates_preview_and_exports():
    fixture = _fixture("resume_generator_payload.json")
    expected = fixture["expected"]

    result = ResumeGeneratorService().generate(fixture["payload"])
    pdf_bytes = base64.b64decode(result["pdf_base64"])

    assert result["filename"] == expected["filename"]
    assert result["html"].startswith("<article")
    assert result["svg"].startswith("<svg")
    assert pdf_bytes.startswith(b"%PDF-1.4")
    for text in expected["plain_text_contains"]:
        assert text in result["plain_text"]
    assert result["resume"]["quality_checks"] == expected["quality_checks"]


def test_step15_telegram_fixture_dedupes_and_matches(tmp_path):
    fixture = _fixture("telegram_backend_posts.json")
    expected = fixture["expected"]
    service = TelegramJobIngestionService(
        db_path=tmp_path / "jobs.db",
        feed_path=tmp_path / "telegram_jobs.json",
        today=date.fromisoformat(fixture["today"]),
    )

    result = service.ingest_posts(fixture["posts"])

    assert result["inserted"] == expected["inserted"]
    assert result["deduped"] == expected["deduped"]
    assert len(result["jobs"]) == 1
    job = result["jobs"][0]
    assert set(expected["required_skills"]) <= set(job["required_skills"])
    assert job["is_valid"] is True

    feed = service.list_jobs(query=expected["query"])
    assert feed["count"] == 1
    assert feed["jobs"][0]["job_id"] == job["job_id"]

    engine = RecommendationEngine(
        load_resources=False,
        db_path=str(tmp_path / "jobs.db"),
        today=date.fromisoformat(fixture["today"]),
    )
    matches = engine.rank_jobs(fixture["match_profile"], top_n=3)

    assert matches
    assert matches[0]["job_id"] == job["job_id"]
    assert matches[0]["match_score"] >= expected["min_match_score"]
    assert "telegram_feed" in matches[0]["retrieval_sources"]
