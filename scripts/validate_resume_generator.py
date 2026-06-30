"""Validate Step 12 resume generator preview and exports."""

from __future__ import annotations

import base64
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.resume_generator import ResumeGeneratorService


def main() -> None:
    payload = {
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

    result = ResumeGeneratorService().generate(payload)
    pdf_bytes = base64.b64decode(result["pdf_base64"])

    if not result["html"].startswith("<article"):
        raise SystemExit("Resume HTML preview was not generated.")
    if not result["svg"].startswith("<svg"):
        raise SystemExit("Resume SVG image output was not generated.")
    if not pdf_bytes.startswith(b"%PDF-1.4"):
        raise SystemExit("Resume PDF output is invalid.")
    if "Jordan Lee" not in result["plain_text"]:
        raise SystemExit("Resume text output is missing candidate name.")
    if not result["resume"]["quality_checks"]["has_experience"]:
        raise SystemExit("Resume quality checks did not detect experience.")

    print(json.dumps({
        "filename": result["filename"],
        "skills": result["resume"]["skills"],
        "html_bytes": len(result["html"].encode("utf-8")),
        "svg_bytes": len(result["svg"].encode("utf-8")),
        "pdf_bytes": len(pdf_bytes),
        "checks": result["resume"]["quality_checks"],
    }, indent=2))


if __name__ == "__main__":
    main()
