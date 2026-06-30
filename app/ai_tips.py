from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from groq import Groq

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqResumeCoach:
	"""Generate AI analysis and resume coaching using the Groq API."""

	def __init__(self, api_key: str | None = None, model: str | None = None):
		self.api_key = api_key or os.environ.get("GROQ_API_KEY")
		self.model = model or os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
		self.client = Groq(api_key=self.api_key) if self.api_key else None

	def is_available(self) -> bool:
		return self.client is not None

	def _parse_json(self, raw: str) -> Optional[Dict[str, Any]]:
		content = (raw or "").strip()
		if content.startswith("```json"):
			content = content[7:]
		if content.startswith("```"):
			content = content[3:]
		if content.endswith("```"):
			content = content[:-3]
		content = content.strip()
		try:
			return json.loads(content)
		except json.JSONDecodeError:
			return None

	def _chat_json(self, system: str, user: str, max_tokens: int = 1200) -> Optional[Dict[str, Any]]:
		if not self.is_available():
			return None
		try:
			resp = self.client.chat.completions.create(
				model=self.model,
				messages=[
					{"role": "system", "content": system},
					{"role": "user", "content": user},
				],
				temperature=0.35,
				max_tokens=max_tokens,
			)
			raw = resp.choices[0].message.content or ""
			return self._parse_json(raw)
		except Exception as exc:
			logger.error("Groq API request failed: %s", exc)
			return None

	def _gap_lines(self, gaps: List[Dict[str, Any]]) -> str:
		if not gaps:
			return "- None identified"
		return "\n".join(
			f"- {gap.get('skill', gap.get('skill_id', 'skill'))}: "
			f"current {gap.get('current', '?')}%, target {gap.get('required', '?')}% "
			f"({gap.get('priority_label', 'Medium')} priority)"
			for gap in gaps
		)

	def _resource_lines(self, resources: List[Dict[str, Any]]) -> str:
		if not resources:
			return "- None"
		lines: List[str] = []
		for group in resources:
			skill = group.get("skill") or group.get("skill_id", "skill")
			for resource in group.get("resources", []):
				covers = ", ".join((resource.get("covers") or [])[:4])
				lines.append(
					f"- [{skill}] {resource.get('title')} on {resource.get('platform')} "
					f"(covers: {covers or 'n/a'})"
				)
		return "\n".join(lines) if lines else "- None"

	def _pair_lines(self, recommendations: List[Dict[str, Any]]) -> str:
		if not recommendations:
			return "- None"
		lines: List[str] = []
		for rec in recommendations:
			resource = rec.get("resource") or {}
			gap = rec.get("gap") or {}
			title = resource.get("title")
			if not title:
				continue
			skill = gap.get("skill_id") or resource.get("skill_id", "gap")
			covers = ", ".join((resource.get("covers") or [])[:3])
			lines.append(f"- [{skill}] {title} (covers: {covers or 'n/a'})")
		return "\n".join(lines) if lines else "- None"

	def generate_analysis(
		self,
		session: Dict[str, Any],
		gaps: List[Dict[str, Any]],
		resource_groups: List[Dict[str, Any]],
	) -> Dict[str, Any]:
		"""Short Groq summary for the analysis panel."""
		if not self.is_available():
			return {"summary": None, "is_ai": False}

		domain = session.get("detected_domain", "your field")
		prompt = f"""You are a career coach. A candidate completed a skills assessment.

Detected domain: {domain}

Skill gaps (from quiz scores):
{self._gap_lines(gaps)}

Curated learning resources (from verified catalog):
{self._resource_lines(resource_groups)}

Return ONLY valid JSON:
{{
  "summary": "2 sentences on what to focus on next, referencing their real gaps and resources"
}}
"""
		payload = self._chat_json(
			"You are a career coach. Return ONLY valid JSON.",
			prompt,
			max_tokens=400,
		)
		if payload and payload.get("summary"):
			return {"summary": payload["summary"], "is_ai": True}
		return {"summary": None, "is_ai": False}

	def generate(
		self,
		session: Dict[str, Any],
		recommendations: List[Dict[str, Any]],
		gaps: Optional[List[Dict[str, Any]]] = None,
	) -> Dict[str, Any]:
		"""Legacy flat resume tips + resource explanations for /recommendations."""
		if not self.is_available():
			return {
				"summary": None,
				"resource_explanations": {},
				"resume_tips": [],
				"is_ai": False,
			}

		domain = session.get("detected_domain", "your field")
		gap_lines = self._gap_lines(gaps or [])
		resources_summary = self._pair_lines(recommendations)

		prompt = f"""You are a career coach. A candidate just completed a skills assessment.

Detected domain: {domain}
Skill gaps:
{gap_lines}

Recommended learning resources:
{resources_summary}

Return ONLY valid JSON:
{{
  "summary": "2-sentence personalised summary of what the candidate should focus on",
  "resource_explanations": {{
    "<resource_title>": "1-sentence explanation of why this resource closes their gap"
  }},
  "resume_tips": [
    "Actionable resume tip 1",
    "Actionable resume tip 2",
    "Actionable resume tip 3"
  ]
}}
"""
		payload = self._chat_json(
			"You are a career coach. Return ONLY valid JSON.",
			prompt,
			max_tokens=900,
		)
		if not payload:
			return {
				"summary": None,
				"resource_explanations": {},
				"resume_tips": [],
				"is_ai": False,
			}
		payload["is_ai"] = True
		return payload

	def generate_coaching(
		self,
		session: Dict[str, Any],
		gaps: List[Dict[str, Any]],
		recommendations: Optional[List[Dict[str, Any]]] = None,
		resource_groups: Optional[List[Dict[str, Any]]] = None,
	) -> Dict[str, Any]:
		"""Structured resume sections + weekly schedule for the Resume Tips tab."""
		if not self.is_available():
			return {"tips": [], "schedule": [], "summary": None, "is_ai": False}

		domain = session.get("detected_domain", "your field")
		skills = session.get("skill_scores") or {}
		skill_names = ", ".join(sorted(skills.keys())[:12]) or "assessed skills"
		resource_block = self._resource_lines(resource_groups or [])
		if recommendations and not resource_groups:
			resource_block = self._pair_lines(recommendations)

		prompt = f"""You are an expert resume coach. Use the candidate's real assessment data only.

Detected domain: {domain}
Assessed skills: {skill_names}

Skill gaps:
{self._gap_lines(gaps)}

Learning resources to reference:
{resource_block}

Return ONLY valid JSON:
{{
  "summary": "1-2 sentence coaching headline",
  "tips": [
    {{"section": "Summary", "icon": "01", "tips": ["...", "..."]}},
    {{"section": "Experience", "icon": "02", "tips": ["...", "..."]}},
    {{"section": "Skills", "icon": "03", "tips": ["...", "..."]}},
    {{"section": "Keywords", "icon": "04", "tips": ["...", "..."]}}
  ],
  "schedule": [
    {{"week": "Week 1", "focus": "...", "tasks": ["...", "..."]}},
    {{"week": "Week 2", "focus": "...", "tasks": ["...", "..."]}},
    {{"week": "Week 3", "focus": "...", "tasks": ["...", "..."]}},
    {{"week": "Week 4", "focus": "...", "tasks": ["...", "..."]}}
  ]
}}
"""
		payload = self._chat_json(
			"You are a professional resume writer. Return ONLY valid JSON.",
			prompt,
			max_tokens=2200,
		)
		if not payload or not isinstance(payload.get("tips"), list):
			return {"tips": [], "schedule": [], "summary": None, "is_ai": False}

		return {
			"summary": payload.get("summary"),
			"tips": payload["tips"],
			"schedule": payload.get("schedule") or [],
			"is_ai": True,
		}

	def generate_resume_upload_analysis(
		self,
		resume_text: str,
		target_role: str,
		detected_skills: List[Dict[str, Any]],
		missing_keywords: List[Dict[str, Any]],
		weak_sections: List[Dict[str, Any]],
	) -> Optional[Dict[str, Any]]:
		"""Structured tips for an uploaded resume."""
		if not self.is_available():
			return None

		skills = ", ".join(
			item.get("skill_name") or item.get("skill") or item.get("skill_id", "")
			for item in detected_skills[:15]
		)
		keywords = ", ".join(item.get("skill", "") for item in missing_keywords[:12])
		weak = ", ".join(item.get("section", "") for item in weak_sections[:8])
		prompt = f"""You are an ATS-focused resume coach. Use only the supplied resume text and analysis.

Target role: {target_role}
Detected skills: {skills or "none"}
Missing keywords: {keywords or "none"}
Weak sections: {weak or "none"}

Resume text:
{resume_text}

Return ONLY valid JSON:
{{
  "summary": "1-2 sentence resume diagnosis",
  "tips": [
    {{"section": "Summary", "icon": "01", "tips": ["...", "..."]}},
    {{"section": "Experience", "icon": "02", "tips": ["...", "..."]}},
    {{"section": "Skills", "icon": "03", "tips": ["...", "..."]}},
    {{"section": "Keywords", "icon": "04", "tips": ["...", "..."]}},
    {{"section": "Projects", "icon": "05", "tips": ["...", "..."]}},
    {{"section": "Formatting", "icon": "06", "tips": ["...", "..."]}}
  ],
  "ats_improvements": ["...", "...", "..."]
}}
"""
		payload = self._chat_json(
			"You are a professional resume writer. Return ONLY valid JSON.",
			prompt,
			max_tokens=1800,
		)
		if not payload or not isinstance(payload.get("tips"), list):
			return None
		return {
			"summary": payload.get("summary"),
			"tips": payload["tips"],
			"ats_improvements": payload.get("ats_improvements") or [],
		}

	def extract_telegram_job(self, raw_text: str) -> Optional[Dict[str, Any]]:
		"""Extract structured job fields from a raw Telegram job post."""
		if not self.is_available():
			return None

		prompt = f"""You extract job postings from Telegram messages. Use only the supplied text.

Raw Telegram post:
{raw_text[:5000]}

Return ONLY valid JSON:
{{
  "job_title": "role title",
  "company": "company if present",
  "role": "short role family",
  "category": "backend-dev, frontend-dev, fullstack-dev, mobile-dev, devops-engineer, data-analyst, data-scientist, ml-engineer, ui-ux-designer, Information Technology (IT), or Other",
  "required_skills": ["skill names from the post"],
  "optional_skills": ["nice-to-have skills"],
  "location": "location or Remote/Hybrid/Onsite",
  "salary": "salary text if present",
  "apply_link": "application URL if present",
  "exp_level": "intern, junior, mid, or senior",
  "job_type": "full-time, part-time, contract, or internship"
}}
"""
		return self._chat_json(
			"You extract jobs from Telegram posts. Return ONLY valid JSON.",
			prompt,
			max_tokens=700,
		)
