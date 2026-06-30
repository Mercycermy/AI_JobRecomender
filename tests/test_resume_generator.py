import base64
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

pytest.importorskip("flask")

from app.resume_generator import ResumeGeneratorError, ResumeGeneratorService
from app.routes import app


@pytest.fixture
def client():
	app.config["TESTING"] = True
	with app.test_client() as c:
		yield c


def sample_resume():
	return {
		"name": "Jordan Lee",
		"title": "Backend Developer",
		"email": "jordan@example.com",
		"phone": "555-0100",
		"location": "Remote",
		"summary": "Backend developer who builds Python APIs and reporting workflows.",
		"skills": "Python, SQL, Docker, REST APIs",
		"experience": [
			{
				"title": "Software Developer",
				"company": "Acme Analytics",
				"location": "Remote",
				"start": "2023",
				"end": "Present",
				"bullets": [
					"Built REST APIs for customer reporting workflows.",
					"Improved dashboard refresh time by 30%.",
				],
			}
		],
		"education": [
			{
				"school": "State University",
				"degree": "BS Computer Science",
				"year": "2022",
				"details": ["Coursework in databases and software engineering"],
			}
		],
		"projects": [
			{
				"name": "Job Match Dashboard",
				"link": "https://example.com/project",
				"bullets": ["Built a Flask and React dashboard for job matching."],
			}
		],
		"certifications": "AWS Cloud Practitioner",
		"links": [{"label": "Portfolio", "url": "https://example.com"}],
	}


def test_resume_generator_returns_downloadable_assets():
	result = ResumeGeneratorService().generate(sample_resume())

	assert result["filename"] == "jordan-lee-resume"
	assert result["resume"]["contact"]["name"] == "Jordan Lee"
	assert result["resume"]["skills"] == ["Python", "SQL", "Docker", "REST APIs"]
	assert result["resume"]["quality_checks"]["has_experience"] is True
	assert result["html"].startswith("<article")
	assert result["svg"].startswith("<svg")
	assert base64.b64decode(result["pdf_base64"]).startswith(b"%PDF-1.4")
	assert "Software Developer at Acme Analytics" in result["plain_text"]


def test_resume_generator_escapes_preview_html():
	result = ResumeGeneratorService().generate(
		{
			"name": "<script>alert(1)</script>",
			"title": "Engineer",
			"summary": "<img src=x onerror=alert(1)>",
		}
	)

	assert "<script" not in result["html"].casefold()
	assert "&lt;script&gt;" in result["html"]
	assert "&lt;img" in result["html"]


def test_resume_generator_requires_name_and_title():
	service = ResumeGeneratorService()

	with pytest.raises(ResumeGeneratorError):
		service.generate({"title": "Engineer"})
	with pytest.raises(ResumeGeneratorError):
		service.generate({"name": "Jordan Lee"})


def test_resume_generate_route_returns_assets(client):
	response = client.post("/resume/generate", json=sample_resume())

	assert response.status_code == 200
	data = response.get_json()
	assert data["resume"]["contact"]["title"] == "Backend Developer"
	assert data["filename"] == "jordan-lee-resume"
	assert data["html"]
	assert data["svg"]
	assert base64.b64decode(data["pdf_base64"]).startswith(b"%PDF-1.4")


def test_resume_generate_route_rejects_missing_name(client):
	response = client.post("/resume/generate", json={"title": "Engineer"})

	assert response.status_code == 400
	assert "Name is required" in response.get_json()["error"]
