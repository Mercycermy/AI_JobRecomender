from __future__ import annotations

import io
import json
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("flask")

from app.routes import app
from app.resume_upload import ResumeUploadService


@pytest.fixture
def client():
	app.config["TESTING"] = True
	with app.test_client() as test_client:
		yield test_client


def _docx_bytes(text: str) -> bytes:
	buffer = io.BytesIO()
	xml = (
		'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
		'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
		"<w:body>"
	)
	for line in text.splitlines():
		xml += f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>"
	xml += "</w:body></w:document>"
	with zipfile.ZipFile(buffer, "w") as archive:
		archive.writestr("[Content_Types].xml", "<Types></Types>")
		archive.writestr("word/document.xml", xml)
	return buffer.getvalue()


def test_resume_upload_service_extracts_docx_and_analyzes_gaps():
	service = ResumeUploadService()
	content = _docx_bytes(
		"""
		Jane Doe
		Experience
		Built Python APIs and SQL reports for internal teams.
		Skills
		Python, SQL, REST API
		Education
		BSc Computer Science
		"""
	)

	result = service.process_upload(
		filename="resume.docx",
		content=content,
		profile={
			"skill_ids": ["lang-py", "lang-sql", "be-rest"],
			"skill_scores": {"lang-py": 0.8},
			"target_role": "backend-dev",
		},
		recommendations=[
			{
				"job_id": "job-1",
				"job_title": "Backend Developer",
				"missing_skills": ["ops-docker"],
			}
		],
	)

	assert result["resume"]["file_type"] == "docx"
	assert {item["skill_id"] for item in result["detected_skills"]} >= {
		"lang-py",
		"lang-sql",
		"be-rest",
	}
	assert result["missing_keywords"][0]["skill_id"] == "ops-docker"
	assert {tip["section"] for tip in result["tips"]} == {
		"Summary",
		"Experience",
		"Skills",
		"Keywords",
		"Projects",
		"Formatting",
	}
	assert result["ats_improvements"]
	assert result["is_ai"] is False


def test_resume_upload_route_accepts_txt_resume(client):
	resume_text = """
	Jane Doe
	Summary
	Backend developer building Python APIs.
	Experience
	Created REST API services and SQL reports for 12 projects.
	Skills
	Python, SQL, REST API
	Education
	BSc Computer Science
	"""
	response = client.post(
		"/resume/upload",
		data={
			"resume": (io.BytesIO(resume_text.encode("utf-8")), "resume.txt"),
			"profile": json.dumps(
				{
					"skills": ["Python", "SQL"],
					"category": "backend-dev",
					"experience": "junior",
				}
			),
			"recommendations": json.dumps(
				[
					{
						"job_id": "job-1",
						"job_title": "Backend Developer",
						"missing_skills": ["ops-docker"],
					}
				]
			),
		},
		content_type="multipart/form-data",
	)

	assert response.status_code == 200
	data = response.get_json()
	assert data["resume"]["file_type"] == "txt"
	assert data["resume"]["word_count"] > 10
	assert any(item["skill_id"] == "lang-py" for item in data["detected_skills"])
	assert any(item["skill_id"] == "ops-docker" for item in data["missing_keywords"])
	assert "weak_sections" in data
	assert data["ats_improvements"]


def test_resume_upload_route_rejects_unsupported_files(client):
	response = client.post(
		"/resume/upload",
		data={
			"resume": (io.BytesIO(b"not a resume"), "resume.png"),
			"profile": json.dumps({"skills": ["Python"]}),
		},
		content_type="multipart/form-data",
	)

	assert response.status_code == 400
	assert "Unsupported resume file type" in response.get_json()["error"]
