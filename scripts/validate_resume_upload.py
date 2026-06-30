"""Validate Step 11 resume upload extraction and ATS tips."""

from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.resume_upload import ResumeUploadService


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


def _validate_payload(payload: dict) -> None:
    if payload["resume"]["word_count"] <= 10:
        raise SystemExit("Resume text extraction returned too few words.")
    if not payload.get("detected_skills"):
        raise SystemExit("No resume skills were detected.")
    if not payload.get("missing_keywords"):
        raise SystemExit("No missing keywords were detected.")
    if not payload.get("weak_sections"):
        raise SystemExit("No weak sections were detected.")
    required_sections = {
        "Summary",
        "Experience",
        "Skills",
        "Keywords",
        "Projects",
        "Formatting",
    }
    tip_sections = {tip.get("section") for tip in payload.get("tips", [])}
    missing_sections = required_sections - tip_sections
    if missing_sections:
        raise SystemExit(f"Missing tip sections: {sorted(missing_sections)}.")
    if not payload.get("ats_improvements"):
        raise SystemExit("No ATS improvements were returned.")


def main() -> None:
    service = ResumeUploadService()
    profile = {
        "skill_ids": ["lang-py", "lang-sql", "be-rest"],
        "skill_scores": {"lang-py": 0.82, "lang-sql": 0.7},
        "target_role": "backend-dev",
    }
    recommendations = [
        {
            "job_id": "backend-1",
            "job_title": "Backend Developer",
            "missing_skills": ["ops-docker", "ops-aws"],
        }
    ]
    text_resume = """
    Jane Doe
    Experience
    Built Python APIs and SQL reports for support teams.
    Skills
    Python, SQL, REST API
    Education
    BSc Computer Science
    """
    txt_payload = service.process_upload(
        "resume.txt",
        text_resume.encode("utf-8"),
        profile=profile,
        recommendations=recommendations,
    )
    docx_payload = service.process_upload(
        "resume.docx",
        _docx_bytes(text_resume),
        profile=profile,
        recommendations=recommendations,
    )
    _validate_payload(txt_payload)
    _validate_payload(docx_payload)

    output = {
        "txt": {
            "word_count": txt_payload["resume"]["word_count"],
            "detected_skills": [
                item["skill_name"] for item in txt_payload["detected_skills"][:5]
            ],
            "missing_keywords": [
                item["skill"] for item in txt_payload["missing_keywords"][:5]
            ],
            "weak_sections": [
                item["section"] for item in txt_payload["weak_sections"][:5]
            ],
        },
        "docx": {
            "word_count": docx_payload["resume"]["word_count"],
            "detected_skills": [
                item["skill_name"] for item in docx_payload["detected_skills"][:5]
            ],
        },
        "is_ai": txt_payload["is_ai"],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
