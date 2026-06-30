from __future__ import annotations

import io
import json
import re
import zipfile
from typing import Any, Dict, Iterable, List, Optional
from xml.etree import ElementTree

from app.ai_tips import GroqResumeCoach
from app.skill_normalizer import SkillNormalizer


class ResumeUploadError(ValueError):
	"""Raised when an uploaded resume cannot be processed."""


SECTION_PATTERNS = {
	"summary": r"\b(summary|profile|objective)\b",
	"experience": r"\b(experience|employment|work history|professional history)\b",
	"skills": r"\b(skills|technical skills|core competencies)\b",
	"projects": r"\b(projects|portfolio)\b",
	"education": r"\b(education|certifications|certificate)\b",
}


class ResumeUploadService:
	"""Extract resume text and return ATS-focused improvement guidance."""

	def __init__(
		self,
		normalizer: Optional[SkillNormalizer] = None,
		ai_coach: Optional[GroqResumeCoach] = None,
	):
		self.normalizer = normalizer or SkillNormalizer()
		self.ai_coach = ai_coach or GroqResumeCoach()

	def process_upload(
		self,
		filename: str,
		content: bytes,
		profile: Optional[Dict[str, Any]] = None,
		recommendations: Optional[Iterable[Dict[str, Any]]] = None,
		target_role: Optional[str] = None,
	) -> Dict[str, Any]:
		file_type = self._file_type(filename)
		text = self.extract_text(filename, content)
		if len(text.strip()) < 20:
			raise ResumeUploadError("Could not extract enough resume text.")
		return self.analyze_text(
			text,
			filename=filename,
			file_type=file_type,
			profile=profile or {},
			recommendations=list(recommendations or []),
			target_role=target_role,
		)

	def extract_text(self, filename: str, content: bytes) -> str:
		file_type = self._file_type(filename)
		if file_type == "txt":
			return self._extract_txt(content)
		if file_type == "docx":
			return self._extract_docx(content)
		if file_type == "pdf":
			return self._extract_pdf(content)
		raise ResumeUploadError("Unsupported resume file type. Upload PDF, DOCX, or TXT.")

	def analyze_text(
		self,
		text: str,
		filename: str = "resume.txt",
		file_type: str = "txt",
		profile: Optional[Dict[str, Any]] = None,
		recommendations: Optional[Iterable[Dict[str, Any]]] = None,
		target_role: Optional[str] = None,
	) -> Dict[str, Any]:
		profile = profile or {}
		recommendations = list(recommendations or [])
		detected_skills = self._detected_skills(text)
		resume_skill_ids = {item["skill_id"] for item in detected_skills}
		profile_skill_ids = set(self._profile_skill_ids(profile))
		missing_keywords = self._missing_keywords(
			resume_skill_ids,
			profile_skill_ids,
			recommendations,
		)
		weak_sections = self._weak_sections(text)
		role = (
			target_role
			or profile.get("target_role")
			or profile.get("detected_role")
			or profile.get("top_category")
			or profile.get("category")
			or "target role"
		)
		fallback = self._fallback_payload(
			text,
			filename,
			file_type,
			role,
			detected_skills,
			missing_keywords,
			weak_sections,
		)
		ai_payload = self._ai_payload(
			text,
			role,
			detected_skills,
			missing_keywords,
			weak_sections,
		)
		if ai_payload:
			fallback.update(ai_payload)
			fallback["is_ai"] = True
		return fallback

	def _file_type(self, filename: str) -> str:
		extension = (filename or "").rsplit(".", 1)[-1].lower()
		if extension not in {"pdf", "docx", "txt"}:
			raise ResumeUploadError("Unsupported resume file type. Upload PDF, DOCX, or TXT.")
		return extension

	def _extract_txt(self, content: bytes) -> str:
		for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
			try:
				return content.decode(encoding)
			except UnicodeDecodeError:
				continue
		raise ResumeUploadError("Could not decode TXT resume.")

	def _extract_docx(self, content: bytes) -> str:
		try:
			with zipfile.ZipFile(io.BytesIO(content)) as archive:
				parts = [
					name
					for name in archive.namelist()
					if name.startswith("word/")
					and name.endswith(".xml")
					and (
						name == "word/document.xml"
						or name.startswith("word/header")
						or name.startswith("word/footer")
					)
				]
				text_parts: List[str] = []
				namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
				for part in parts:
					root = ElementTree.fromstring(archive.read(part))
					for node in root.iter(f"{namespace}t"):
						if node.text:
							text_parts.append(node.text)
				return "\n".join(text_parts)
		except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
			raise ResumeUploadError("Could not extract DOCX resume text.") from exc

	def _extract_pdf(self, content: bytes) -> str:
		try:
			from pypdf import PdfReader
		except Exception as exc:  # pragma: no cover - environment dependent
			raise ResumeUploadError(
				"PDF extraction requires pypdf. Install project requirements first."
			) from exc
		try:
			reader = PdfReader(io.BytesIO(content))
			return "\n".join(page.extract_text() or "" for page in reader.pages)
		except Exception as exc:
			raise ResumeUploadError("Could not extract PDF resume text.") from exc

	def _detected_skills(self, text: str) -> List[Dict[str, Any]]:
		return [
			{
				"skill_id": match.skill_id,
				"skill_name": match.skill_name,
				"matched_text": match.matched_text,
				"confidence": match.confidence,
			}
			for match in self.normalizer.extract_matches(text)
		]

	def _profile_skill_ids(self, profile: Dict[str, Any]) -> List[str]:
		raw_skills = (
			profile.get("skill_ids")
			or profile.get("detected_skills")
			or profile.get("skills")
			or []
		)
		return self.normalizer.normalize_list([str(skill) for skill in raw_skills])

	def _missing_keywords(
		self,
		resume_skill_ids: set[str],
		profile_skill_ids: set[str],
		recommendations: Iterable[Dict[str, Any]],
	) -> List[Dict[str, Any]]:
		candidates: Dict[str, Dict[str, Any]] = {}
		for skill_id in profile_skill_ids:
			if skill_id not in resume_skill_ids:
				candidates[skill_id] = {
					"skill_id": skill_id,
					"skill": self.normalizer.name_for(skill_id),
					"priority": "profile",
					"source_jobs": [],
				}

		for index, rec in enumerate(recommendations, start=1):
			for raw_skill in rec.get("missing_skills") or []:
				skill_id = self.normalizer.to_skill_id(str(raw_skill)) or str(raw_skill)
				if not skill_id or skill_id in resume_skill_ids:
					continue
				item = candidates.setdefault(
					skill_id,
					{
						"skill_id": skill_id,
						"skill": self.normalizer.name_for(skill_id),
						"priority": "job",
						"source_jobs": [],
					},
				)
				item["priority"] = "job"
				item["source_jobs"].append(
					{
						"job_id": str(rec.get("job_id") or ""),
						"title": rec.get("job_title") or rec.get("title") or f"Job {index}",
					}
				)

		return sorted(
			candidates.values(),
			key=lambda item: (
				0 if item["priority"] == "job" else 1,
				-item.get("source_jobs", []).__len__(),
				item["skill"],
			),
		)[:12]

	def _weak_sections(self, text: str) -> List[Dict[str, str]]:
		lower = text.casefold()
		weak: List[Dict[str, str]] = []
		for section, pattern in SECTION_PATTERNS.items():
			if not re.search(pattern, lower):
				weak.append(
					{
						"section": section,
						"issue": f"Missing or unclear {section} section.",
						"recommendation": f"Add a clear {section} heading with role-relevant evidence.",
					}
				)
		if not re.search(r"\b\d+%|\$\d+|\b\d+\+?\s+(users|customers|projects|tickets|reports|apis)\b", lower):
			weak.append(
				{
					"section": "metrics",
					"issue": "Few measurable outcomes were detected.",
					"recommendation": "Add numbers for scope, speed, quality, users, revenue, or delivery impact.",
				}
			)
		return weak

	def _fallback_payload(
		self,
		text: str,
		filename: str,
		file_type: str,
		target_role: str,
		detected_skills: List[Dict[str, Any]],
		missing_keywords: List[Dict[str, Any]],
		weak_sections: List[Dict[str, str]],
	) -> Dict[str, Any]:
		word_count = len(re.findall(r"\b\w+\b", text))
		keyword_names = [item["skill"] for item in missing_keywords[:5]]
		weak_names = [item["section"] for item in weak_sections[:4]]
		tips = [
			{
				"section": "Summary",
				"icon": "01",
				"tips": [
					f"Open with a 2-line summary naming {target_role} and your strongest matched skills.",
					"Replace generic objectives with a role-specific value statement.",
				],
			},
			{
				"section": "Experience",
				"icon": "02",
				"tips": [
					"Rewrite bullets with action, technical scope, and measurable outcome.",
					"Put the most relevant backend, data, or delivery evidence in the first two bullets.",
				],
			},
			{
				"section": "Skills",
				"icon": "03",
				"tips": [
					"Group skills by workflow so ATS and recruiters can scan them quickly.",
					"Keep only skills you can defend with project or work evidence.",
				],
			},
			{
				"section": "Keywords",
				"icon": "04",
				"tips": [
					"Add missing role keywords: " + (", ".join(keyword_names) or "none detected"),
					"Mirror job posting terms naturally in experience bullets, not only in the skills list.",
				],
			},
			{
				"section": "Projects",
				"icon": "05",
				"tips": [
					"Add one project with problem, tools, result, and link if work experience is thin.",
					"Use project bullets to prove the highest-priority missing keyword.",
				],
			},
			{
				"section": "Formatting",
				"icon": "06",
				"tips": [
					"Use standard section headings: Summary, Experience, Skills, Projects, Education.",
					"Keep layout ATS-friendly: text-based bullets, no tables, no image-only content.",
				],
			},
		]
		ats_improvements = [
			"Use standard headings for every major section.",
			"Include exact role keywords where they are supported by evidence.",
			"Start bullets with strong verbs and include measurable outcomes.",
			"Avoid tables, icons, and image-only text that ATS parsers may miss.",
		]
		if weak_names:
			ats_improvements.insert(0, "Fix weak sections: " + ", ".join(weak_names) + ".")

		return {
			"resume": {
				"filename": filename,
				"file_type": file_type,
				"word_count": word_count,
				"character_count": len(text),
				"text_preview": text.strip()[:700],
			},
			"target_role": target_role,
			"detected_skills": detected_skills,
			"missing_keywords": missing_keywords,
			"weak_sections": weak_sections,
			"tips": tips,
			"ats_improvements": ats_improvements,
			"is_ai": False,
		}

	def _ai_payload(
		self,
		text: str,
		target_role: str,
		detected_skills: List[Dict[str, Any]],
		missing_keywords: List[Dict[str, Any]],
		weak_sections: List[Dict[str, str]],
	) -> Optional[Dict[str, Any]]:
		if not self.ai_coach.is_available():
			return None
		return self.ai_coach.generate_resume_upload_analysis(
			resume_text=text[:6000],
			target_role=target_role,
			detected_skills=detected_skills,
			missing_keywords=missing_keywords,
			weak_sections=weak_sections,
		)


def loads_json_field(value: Any, default: Any) -> Any:
	if value in (None, ""):
		return default
	if isinstance(value, (dict, list)):
		return value
	try:
		return json.loads(str(value))
	except json.JSONDecodeError:
		return default
