from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from groq import Groq

DEFAULT_RESUME_TIPS = [
	"Showcase one measurable project that closes your top gap.",
	"Mirror role keywords in your summary and skills section.",
	"Add a results-focused bullet for each key tool you learned.",
]


class GroqResumeCoach:
	"""Generate AI analysis and resume tips using Groq."""

	def __init__(self, api_key: str | None = None, model: str = "llama3-70b-8192"):
		self.api_key = api_key or os.environ.get("GROQ_API_KEY")
		self.model = model
		self.client = Groq(api_key=self.api_key) if self.api_key else None

	def is_available(self) -> bool:
		return self.client is not None

	def _fallback(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
		resource_explanations = {
			rec.get("resource", {}).get("title", ""): "Suggested to close a detected gap."
			for rec in recommendations
			if rec.get("resource", {}).get("title")
		}
		return {
			"summary": "Focus on your highest-priority gaps with targeted practice and a showcase project.",
			"resource_explanations": resource_explanations,
			"resume_tips": DEFAULT_RESUME_TIPS,
			"is_ai": False,
		}

	def generate(self, session: Dict[str, Any], recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
		if not self.is_available():
			return self._fallback(recommendations)

		domain = session.get("detected_domain", "your field")
		gaps = [rec.get("gap", {}).get("skill_id", "").replace("-", " ") for rec in recommendations]
		gaps = [gap for gap in gaps if gap]

		resources_summary = "\n".join(
			f"- [{rec['resource'].get('skill_id', rec['gap'].get('skill_id', 'gap'))}] "
			f"{rec['resource']['title']} (covers: {', '.join(rec['resource'].get('covers', [])[:3])})"
			for rec in recommendations
			if rec.get("resource", {}).get("title")
		)

		prompt = f"""
You are a career coach. A candidate just completed a skills assessment.

Detected domain: {domain}
Skill gaps identified: {', '.join(gaps) or 'None'}

Recommended learning resources:
{resources_summary or '- None'}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "summary": "2-sentence personalised summary of what the candidate should focus on",
  "resource_explanations": {{
    "<resource_title>": "1-sentence explanation of exactly why this resource closes their specific gap"
  }},
  "resume_tips": [
    "Actionable resume tip 1 based on their gaps",
    "Actionable resume tip 2",
    "Actionable resume tip 3"
  ]
}}
"""

		try:
			resp = self.client.chat.completions.create(
				model=self.model,
				messages=[
					{"role": "system", "content": "You are a career coach. Return ONLY valid JSON."},
					{"role": "user", "content": prompt},
				],
				temperature=0.4,
				max_tokens=800,
			)
			raw = resp.choices[0].message.content.strip()
			raw = raw.replace("```json", "").replace("```", "").strip()
			payload = json.loads(raw)
			payload["is_ai"] = True
			return payload
		except Exception:
			return self._fallback(recommendations)
