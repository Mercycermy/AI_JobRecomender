import os
import sqlite3
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

pytest.importorskip("flask")

from app import routes
from app.recommender import RecommendationEngine
from app.telegram_jobs import TelegramJobIngestionService


@pytest.fixture
def client(tmp_path):
	routes.app.config["TESTING"] = True
	original_service = routes._telegram_job_service
	routes._telegram_job_service = TelegramJobIngestionService(
		db_path=tmp_path / "jobs.db",
		feed_path=tmp_path / "telegram_jobs.json",
		today=date(2026, 6, 30),
	)
	with routes.app.test_client() as c:
		yield c
	routes._telegram_job_service = original_service


def sample_post(message_id="42"):
	return {
		"channel_name": "python_jobs",
		"message_id": message_id,
		"posted_at": "2026-06-30",
		"raw_text": (
			"Title: Backend Developer\n"
			"Company: Acme Analytics\n"
			"Skills: Python, SQL, Docker, REST API\n"
			"Location: Remote\n"
			"Salary: $90k-$110k\n"
			"Deadline: July 5, 2026\n"
			"Apply: https://example.com/apply"
		),
	}


def test_telegram_ingestion_stores_valid_jobs_and_feed(tmp_path):
	service = TelegramJobIngestionService(
		db_path=tmp_path / "jobs.db",
		feed_path=tmp_path / "telegram_jobs.json",
		today=date(2026, 6, 30),
	)

	result = service.ingest_posts([sample_post(), sample_post(message_id="43")])

	assert result["inserted"] == 1
	assert result["deduped"] == 1
	assert result["skipped"] == 0
	job = result["jobs"][0]
	assert job["job_title"] == "Backend Developer"
	assert job["source"] == "Telegram: python_jobs"
	assert job["posted_at"] == "2026-06-30"
	assert job["deadline_date"] == "2026-07-05"
	assert {"lang-py", "lang-sql", "ops-docker", "be-rest"} <= set(job["required_skills"])
	assert job["is_valid"] is True

	conn = sqlite3.connect(tmp_path / "jobs.db")
	try:
		stored = conn.execute("SELECT job_title, source FROM jobs WHERE job_id = ?", (job["job_id"],)).fetchone()
		skills = {
			row[0]
			for row in conn.execute("SELECT skill_id FROM job_skills WHERE job_id = ?", (job["job_id"],))
		}
	finally:
		conn.close()

	assert stored == ("Backend Developer", "Telegram: python_jobs")
	assert {"lang-py", "lang-sql", "ops-docker", "be-rest"} <= skills
	assert service.list_jobs(query="docker")["count"] == 1


def test_telegram_ingestion_skips_expired_deadline(tmp_path):
	service = TelegramJobIngestionService(
		db_path=tmp_path / "jobs.db",
		feed_path=tmp_path / "telegram_jobs.json",
		today=date(2026, 6, 30),
	)
	expired = sample_post()
	expired["message_id"] = "expired"
	expired["raw_text"] = expired["raw_text"].replace("July 5, 2026", "June 29, 2026")

	result = service.ingest_posts([expired])

	assert result["inserted"] == 0
	assert result["skipped"] == 1
	assert "deadline passed" in result["errors"][0]["errors"]
	assert service.list_jobs()["count"] == 0


def test_telegram_public_html_posts_are_parsed(tmp_path):
	service = TelegramJobIngestionService(
		db_path=tmp_path / "jobs.db",
		feed_path=tmp_path / "telegram_jobs.json",
		today=date(2026, 6, 30),
	)
	html = """
	<section>
	  <div class="tgme_widget_message_wrap js-widget_message_wrap">
	    <div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="freelance_ethio/123">
	      <div class="tgme_widget_message_text js-message_text" dir="auto">
	        Title: Frontend Developer<br/>
	        Company: Web Studio<br/>
	        Skills: React, JavaScript, CSS<br/>
	        Deadline: July 10, 2026<br/>
	        Apply: https://example.com/frontend
	      </div>
	      <time datetime="2026-06-29T12:00:00+00:00"></time>
	    </div>
	  </div>
	</section>
	"""

	posts = service._posts_from_channel_html("freelance_ethio", html, limit=10)

	assert len(posts) == 1
	assert posts[0]["channel_name"] == "@freelance_ethio"
	assert posts[0]["message_id"] == "123"
	assert posts[0]["posted_at"] == "2026-06-29"
	assert "Frontend Developer" in posts[0]["raw_text"]


def test_telegram_ingestion_skips_invalid_posts(tmp_path):
	service = TelegramJobIngestionService(
		db_path=tmp_path / "jobs.db",
		feed_path=tmp_path / "telegram_jobs.json",
		today=date(2026, 6, 30),
	)

	result = service.ingest_posts([
		{
			"channel_name": "updates",
			"message_id": "1",
			"raw_text": "Company update: we are growing our community and will post roles later.",
		}
	])

	assert result["inserted"] == 0
	assert result["skipped"] == 1
	assert "missing required_skills" in result["errors"][0]["errors"]
	assert service.list_jobs()["count"] == 0


def test_telegram_ingested_jobs_are_matchable(tmp_path):
	service = TelegramJobIngestionService(
		db_path=tmp_path / "jobs.db",
		feed_path=tmp_path / "telegram_jobs.json",
		today=date(2026, 6, 30),
	)
	service.ingest_posts([sample_post()])

	engine = RecommendationEngine(
		load_resources=False,
		db_path=str(tmp_path / "jobs.db"),
		today=date(2026, 6, 30),
	)
	results = engine.rank_jobs(
		{
			"skill_ids": ["lang-py", "lang-sql", "ops-docker", "be-rest"],
			"skill_scores": {"lang-py": 0.8, "lang-sql": 0.75, "ops-docker": 0.6, "be-rest": 0.8},
			"experience_level": "mid",
			"target_role": "backend-dev",
			"location": "remote",
		},
		top_n=3,
	)

	assert results
	assert results[0]["source"] == "Telegram: python_jobs"
	assert "telegram_feed" in results[0]["retrieval_sources"]


def test_telegram_jobs_routes_ingest_and_list(client):
	response = client.post("/telegram/jobs/ingest", json={"posts": [sample_post()]})

	assert response.status_code == 200
	data = response.get_json()
	assert data["inserted"] == 1
	assert data["jobs"][0]["job_title"] == "Backend Developer"

	list_response = client.get("/telegram/jobs?q=python")
	assert list_response.status_code == 200
	list_data = list_response.get_json()
	assert list_data["count"] == 1
	assert list_data["jobs"][0]["source_channel"] == "python_jobs"


def test_telegram_jobs_refresh_route_uses_public_channels(client):
	service = routes._telegram_job_service

	def fake_fetch_channel_posts(channel, limit=12):
		return [sample_post(message_id=f"{channel}-1")]

	service.fetch_channel_posts = fake_fetch_channel_posts
	response = client.post(
		"/telegram/jobs/refresh",
		json={"channels": ["@freelance_ethio"], "per_channel_limit": 1},
	)

	assert response.status_code == 200
	data = response.get_json()
	assert data["fetched_posts"] == 1
	assert data["inserted"] == 1
	assert data["channels"][0]["channel"] == "@freelance_ethio"


def test_telegram_jobs_route_rejects_non_list_posts(client):
	response = client.post("/telegram/jobs/ingest", json={"posts": {"raw_text": "not a list"}})

	assert response.status_code == 400
	assert "posts must be a list" in response.get_json()["error"]
