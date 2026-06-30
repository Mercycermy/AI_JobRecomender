from __future__ import annotations

import base64
import html
import re
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


class ResumeGeneratorError(ValueError):
    """Raised when resume generator input is incomplete or invalid."""


@dataclass(frozen=True)
class PdfLine:
    text: str
    size: int = 10
    bold: bool = False
    x: int = 54
    gap_before: int = 0
    leading: int = 4


class ResumeGeneratorService:
    """Normalize resume-builder input and render downloadable resume assets."""

    def generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        resume = self.normalize(payload)
        lines = self._pdf_lines(resume)
        pdf_bytes = self._build_pdf(lines)
        return {
            "resume": resume,
            "html": self._render_html(resume),
            "svg": self._render_svg(resume, lines),
            "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "plain_text": self._plain_text(resume),
            "filename": f"{resume['slug']}-resume",
        }

    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ResumeGeneratorError("Resume payload must be a JSON object.")

        contact = payload.get("contact") if isinstance(payload.get("contact"), dict) else {}
        name = self._clean(payload.get("name") or contact.get("name"))
        title = self._clean(payload.get("title") or contact.get("title"))
        email = self._clean(payload.get("email") or contact.get("email"))
        phone = self._clean(payload.get("phone") or contact.get("phone"))
        location = self._clean(payload.get("location") or contact.get("location"))

        if not name:
            raise ResumeGeneratorError("Name is required to generate a resume.")
        if not title:
            raise ResumeGeneratorError("Professional title is required to generate a resume.")

        resume = {
            "contact": {
                "name": name,
                "title": title,
                "email": email,
                "phone": phone,
                "location": location,
                "links": self._normalize_links(payload.get("links") or contact.get("links")),
            },
            "summary": self._clean(payload.get("summary"), max_length=900),
            "skills": self._normalize_string_list(payload.get("skills"), max_items=32),
            "experience": self._normalize_experience(payload.get("experience")),
            "education": self._normalize_education(payload.get("education")),
            "projects": self._normalize_projects(payload.get("projects")),
            "certifications": self._normalize_string_list(payload.get("certifications"), max_items=14),
            "template": self._clean(payload.get("template") or "modern", max_length=30),
        }
        resume["quality_checks"] = self._quality_checks(resume)
        resume["slug"] = self._slug(name)
        return resume

    def _normalize_experience(self, value: Any) -> List[Dict[str, Any]]:
        items = self._ensure_list(value)[:8]
        normalized: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            entry = {
                "title": self._clean(item.get("title")),
                "company": self._clean(item.get("company")),
                "location": self._clean(item.get("location")),
                "start": self._clean(item.get("start")),
                "end": self._clean(item.get("end")),
                "bullets": self._normalize_string_list(item.get("bullets"), max_items=8),
            }
            if entry["title"] or entry["company"] or entry["bullets"]:
                normalized.append(entry)
        return normalized

    def _normalize_education(self, value: Any) -> List[Dict[str, Any]]:
        items = self._ensure_list(value)[:6]
        normalized: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            entry = {
                "school": self._clean(item.get("school")),
                "degree": self._clean(item.get("degree")),
                "location": self._clean(item.get("location")),
                "year": self._clean(item.get("year")),
                "details": self._normalize_string_list(item.get("details"), max_items=5),
            }
            if entry["school"] or entry["degree"] or entry["details"]:
                normalized.append(entry)
        return normalized

    def _normalize_projects(self, value: Any) -> List[Dict[str, Any]]:
        items = self._ensure_list(value)[:6]
        normalized: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            entry = {
                "name": self._clean(item.get("name")),
                "link": self._clean(item.get("link")),
                "bullets": self._normalize_string_list(item.get("bullets"), max_items=6),
            }
            if entry["name"] or entry["bullets"]:
                normalized.append(entry)
        return normalized

    def _normalize_links(self, value: Any) -> List[Dict[str, str]]:
        links: List[Dict[str, str]] = []
        for item in self._ensure_list(value)[:6]:
            if isinstance(item, dict):
                label = self._clean(item.get("label") or item.get("name"))
                url = self._clean(item.get("url") or item.get("link"))
            else:
                label = ""
                url = self._clean(item)
            if url:
                links.append({"label": label or url, "url": url})
        return links

    def _normalize_string_list(self, value: Any, max_items: int) -> List[str]:
        if isinstance(value, str):
            raw_items = re.split(r"[\n,;]+", value)
        else:
            raw_items = self._ensure_list(value)
        cleaned = []
        seen = set()
        for item in raw_items:
            text = self._clean(item)
            key = text.casefold()
            if text and key not in seen:
                cleaned.append(text)
                seen.add(key)
            if len(cleaned) >= max_items:
                break
        return cleaned

    def _quality_checks(self, resume: Dict[str, Any]) -> Dict[str, bool]:
        contact = resume["contact"]
        return {
            "has_contact": bool(contact["email"] or contact["phone"]),
            "has_summary": bool(resume["summary"]),
            "has_experience": bool(resume["experience"]),
            "has_skills": bool(resume["skills"]),
            "has_education": bool(resume["education"]),
            "has_projects": bool(resume["projects"]),
        }

    def _render_html(self, resume: Dict[str, Any]) -> str:
        contact = resume["contact"]
        parts = [
            '<article class="generated-resume-template">',
            "<header>",
            f"<h1>{self._e(contact['name'])}</h1>",
            f"<p>{self._e(contact['title'])}</p>",
            f"<div>{self._e(self._contact_line(contact))}</div>",
            "</header>",
        ]
        if resume["summary"]:
            parts.append(self._html_section("Summary", f"<p>{self._e(resume['summary'])}</p>"))
        if resume["skills"]:
            skills = "".join(f"<li>{self._e(skill)}</li>" for skill in resume["skills"])
            parts.append(self._html_section("Skills", f"<ul class=\"skill-cloud\">{skills}</ul>"))
        if resume["experience"]:
            parts.append(self._html_section("Experience", self._html_roles(resume["experience"])))
        if resume["projects"]:
            parts.append(self._html_section("Projects", self._html_projects(resume["projects"])))
        if resume["education"]:
            parts.append(self._html_section("Education", self._html_education(resume["education"])))
        if resume["certifications"]:
            certs = "".join(f"<li>{self._e(item)}</li>" for item in resume["certifications"])
            parts.append(self._html_section("Certifications", f"<ul>{certs}</ul>"))
        if contact["links"]:
            links = "".join(
                f"<li>{self._e(link['label'])}: {self._e(link['url'])}</li>"
                for link in contact["links"]
            )
            parts.append(self._html_section("Links", f"<ul>{links}</ul>"))
        parts.append("</article>")
        return "".join(parts)

    def _html_roles(self, roles: Iterable[Dict[str, Any]]) -> str:
        chunks = []
        for role in roles:
            meta = self._join_nonempty([role["company"], role["location"], self._date_range(role)])
            bullets = "".join(f"<li>{self._e(item)}</li>" for item in role["bullets"])
            chunks.append(
                "<div class=\"resume-entry\">"
                f"<h3>{self._e(role['title'] or role['company'])}</h3>"
                f"<p>{self._e(meta)}</p>"
                f"<ul>{bullets}</ul>"
                "</div>"
            )
        return "".join(chunks)

    def _html_projects(self, projects: Iterable[Dict[str, Any]]) -> str:
        chunks = []
        for project in projects:
            bullets = "".join(f"<li>{self._e(item)}</li>" for item in project["bullets"])
            link = f"<p>{self._e(project['link'])}</p>" if project["link"] else ""
            chunks.append(
                "<div class=\"resume-entry\">"
                f"<h3>{self._e(project['name'])}</h3>"
                f"{link}<ul>{bullets}</ul>"
                "</div>"
            )
        return "".join(chunks)

    def _html_education(self, education: Iterable[Dict[str, Any]]) -> str:
        chunks = []
        for item in education:
            meta = self._join_nonempty([item["school"], item["location"], item["year"]])
            details = "".join(f"<li>{self._e(detail)}</li>" for detail in item["details"])
            chunks.append(
                "<div class=\"resume-entry\">"
                f"<h3>{self._e(item['degree'] or item['school'])}</h3>"
                f"<p>{self._e(meta)}</p>"
                f"<ul>{details}</ul>"
                "</div>"
            )
        return "".join(chunks)

    def _html_section(self, title: str, body: str) -> str:
        return f"<section><h2>{self._e(title)}</h2>{body}</section>"

    def _render_svg(self, resume: Dict[str, Any], lines: List[PdfLine]) -> str:
        height = max(1123, 170 + len(lines) * 19)
        text_nodes = []
        y = 72
        for line in lines:
            y += line.gap_before
            fill = "#17324d" if line.bold else "#27384a"
            weight = "700" if line.bold else "400"
            text_nodes.append(
                f'<text x="{line.x + 28}" y="{y}" font-size="{line.size + 2}" '
                f'font-weight="{weight}" fill="{fill}">{self._e(line.text)}</text>'
            )
            y += line.size + line.leading + 4

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="794" height="{height}" '
            f'viewBox="0 0 794 {height}" role="img" aria-label="Generated resume">'
            '<rect width="794" height="100%" fill="#f7fbff"/>'
            '<rect x="42" y="34" width="710" height="100%" rx="10" fill="#ffffff"/>'
            '<rect x="42" y="34" width="10" height="100%" fill="#2e86c1"/>'
            '<g font-family="Arial, Helvetica, sans-serif">'
            + "".join(text_nodes)
            + "</g></svg>"
        )

    def _plain_text(self, resume: Dict[str, Any]) -> str:
        lines = []
        for line in self._pdf_lines(resume):
            if line.text:
                lines.append(line.text)
        return "\n".join(lines)

    def _pdf_lines(self, resume: Dict[str, Any]) -> List[PdfLine]:
        contact = resume["contact"]
        lines = [
            PdfLine(contact["name"], size=20, bold=True, gap_before=0),
            PdfLine(contact["title"], size=12, bold=True),
            PdfLine(self._contact_line(contact), size=9),
        ]
        self._add_section(lines, "Summary", [resume["summary"]])
        self._add_section(lines, "Skills", [", ".join(resume["skills"])])

        if resume["experience"]:
            self._add_heading(lines, "Experience")
            for item in resume["experience"]:
                title = self._join_nonempty([item["title"], item["company"]], sep=" at ")
                lines.append(PdfLine(title, bold=True, gap_before=2))
                meta = self._join_nonempty([item["location"], self._date_range(item)])
                if meta:
                    lines.append(PdfLine(meta, size=9))
                self._add_bullets(lines, item["bullets"])

        if resume["projects"]:
            self._add_heading(lines, "Projects")
            for project in resume["projects"]:
                lines.append(PdfLine(project["name"], bold=True, gap_before=2))
                if project["link"]:
                    lines.append(PdfLine(project["link"], size=9))
                self._add_bullets(lines, project["bullets"])

        if resume["education"]:
            self._add_heading(lines, "Education")
            for item in resume["education"]:
                lines.append(PdfLine(item["degree"] or item["school"], bold=True, gap_before=2))
                meta = self._join_nonempty([item["school"], item["location"], item["year"]])
                if meta:
                    lines.append(PdfLine(meta, size=9))
                self._add_bullets(lines, item["details"])

        self._add_section(lines, "Certifications", resume["certifications"])
        if contact["links"]:
            link_lines = [f"{link['label']}: {link['url']}" for link in contact["links"]]
            self._add_section(lines, "Links", link_lines)
        return lines

    def _add_section(self, lines: List[PdfLine], title: str, values: List[str]) -> None:
        values = [value for value in values if value]
        if not values:
            return
        self._add_heading(lines, title)
        if len(values) == 1:
            for wrapped in self._wrap(values[0], width=96):
                lines.append(PdfLine(wrapped))
        else:
            self._add_bullets(lines, values)

    def _add_heading(self, lines: List[PdfLine], title: str) -> None:
        lines.append(PdfLine(title.upper(), size=11, bold=True, gap_before=12, leading=3))

    def _add_bullets(self, lines: List[PdfLine], bullets: Iterable[str]) -> None:
        for bullet in bullets:
            for index, wrapped in enumerate(self._wrap(bullet, width=88)):
                prefix = "- " if index == 0 else "  "
                lines.append(PdfLine(prefix + wrapped, x=68))

    def _build_pdf(self, lines: List[PdfLine]) -> bytes:
        pages = self._paginate(lines)
        max_id = 4 + len(pages) * 2
        font_regular_id = 3
        font_bold_id = 4
        objects: Dict[int, bytes] = {
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            font_regular_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            font_bold_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        }
        page_ids = []
        for index, page_lines in enumerate(pages):
            page_id = 5 + index * 2
            content_id = page_id + 1
            page_ids.append(page_id)
            objects[page_id] = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("ascii")
            stream = self._pdf_content(page_lines).encode("latin-1", "replace")
            objects[content_id] = (
                f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
                + stream
                + b"\nendstream"
            )
        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")

        pdf = b"%PDF-1.4\n"
        offsets = [0]
        for object_id in range(1, max_id + 1):
            offsets.append(len(pdf))
            pdf += f"{object_id} 0 obj\n".encode("ascii") + objects[object_id] + b"\nendobj\n"
        xref_position = len(pdf)
        pdf += f"xref\n0 {max_id + 1}\n".encode("ascii")
        pdf += b"0000000000 65535 f \n"
        for offset in offsets[1:]:
            pdf += f"{offset:010d} 00000 n \n".encode("ascii")
        pdf += (
            f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_position}\n%%EOF\n"
        ).encode("ascii")
        return pdf

    def _paginate(self, lines: List[PdfLine]) -> List[List[PdfLine]]:
        pages: List[List[PdfLine]] = []
        current: List[PdfLine] = []
        y = 746
        for line in lines:
            needed = line.gap_before + line.size + line.leading
            if current and y - needed < 52:
                pages.append(current)
                current = []
                y = 746
            current.append(line)
            y -= needed
        if current:
            pages.append(current)
        return pages or [[PdfLine("Resume")]]

    def _pdf_content(self, lines: List[PdfLine]) -> str:
        commands = ["BT"]
        y = 746
        for line in lines:
            y -= line.gap_before
            font = "F2" if line.bold else "F1"
            commands.append(f"/{font} {line.size} Tf")
            commands.append(f"1 0 0 1 {line.x} {y} Tm")
            commands.append(f"({self._pdf_escape(line.text)}) Tj")
            y -= line.size + line.leading
        commands.append("ET")
        return "\n".join(commands)

    def _wrap(self, value: str, width: int) -> List[str]:
        return textwrap.wrap(value, width=width, break_long_words=False) or []

    def _contact_line(self, contact: Dict[str, Any]) -> str:
        links = [link["url"] for link in contact["links"][:2]]
        return self._join_nonempty([
            contact["email"],
            contact["phone"],
            contact["location"],
            *links,
        ])

    def _date_range(self, item: Dict[str, str]) -> str:
        return self._join_nonempty([item.get("start", ""), item.get("end", "")], sep=" - ")

    def _join_nonempty(self, values: Iterable[str], sep: str = " | ") -> str:
        return sep.join(str(value) for value in values if value)

    def _ensure_list(self, value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _clean(self, value: Any, max_length: int = 240) -> str:
        if value is None:
            return ""
        text = re.sub(r"\s+", " ", str(value)).strip()
        return text[:max_length]

    def _slug(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
        return slug or "candidate"

    def _e(self, value: str) -> str:
        return html.escape(str(value), quote=True)

    def _pdf_escape(self, value: str) -> str:
        return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
