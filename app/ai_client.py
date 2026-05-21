from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
import anthropic

logger = logging.getLogger(__name__)


class AIClient:
	"""Anthropic Claude API client wrapper for resume coaching."""

	def __init__(self):
		self.api_key = os.environ.get("ANTHROPIC_API_KEY")
		self.client = None
		if self.api_key:
			try:
				self.client = anthropic.Anthropic(api_key=self.api_key)
			except Exception as e:
				logger.error(f"Failed to initialize Anthropic client: {e}")

	def is_available(self) -> bool:
		return self.client is not None

	def generate_resume_tips(
		self,
		skills: List[str],
		gaps: List[Dict[str, Any]],
		target_category: str,
	) -> Optional[Dict[str, Any]]:
		"""Call Claude to generate custom, actionable resume tips and a weekly study schedule."""
		if not self.is_available() or not self.client:
			return None

		gaps_str = "\n".join(
			[
				f"- {gap.get('skill', 'Unknown')} ({gap.get('priority_label', 'High')} Priority gap: current level {gap.get('current', 10)}%, required {gap.get('required', 70)}%)"
				for gap in gaps
			]
		)

		prompt = f"""You are an expert AI Resume Coach. Analyze the user's skill profile, identified gaps, and target job category to generate personalized resume optimization tips and a weekly study schedule.

User Skills: {', '.join(skills)}
Skill Gaps:
{gaps_str}
Target Job Category: {target_category}

Return a JSON object containing:
1. "tips": A list of exactly 4 sections: "Summary" (icon "01"), "Experience" (icon "02"), "Skills" (icon "03"), and "Keywords" (icon "04"). Each section must have a list of at least 2 personalized, highly actionable resume tips targeting the identified gaps and highlighting how to represent their current skills.
2. "schedule": A weekly study schedule for 4 weeks. Each week must have a "week" string (e.g. "Week 1"), a "focus" string (the core skill or gap to focus on), and a list of "tasks" (at least 2 concrete tasks to close that gap, like building a specific project, learning a framework, or taking a class).

IMPORTANT: Return ONLY a valid JSON object. Do not include any explanations, introductory text, or markdown code block markers (like ```json). The output must be pure JSON.
"""

		try:
			message = self.client.messages.create(
				model="claude-3-5-sonnet-20241022",
				max_tokens=2500,
				temperature=0.3,
				system="You are a professional resume writer and career development coach. You always respond in raw, structured JSON without conversational fluff or markdown formatting.",
				messages=[
					{
						"role": "user",
						"content": prompt,
					}
				],
			)
			content = message.content[0].text.strip() if message.content else ""
			
			# Clean up markdown code blocks if the model included them
			if content.startswith("```json"):
				content = content[7:]
			if content.startswith("```"):
				content = content[3:]
			if content.endswith("```"):
				content = content[:-3]
			content = content.strip()

			return json.loads(content)
		except Exception as e:
			logger.error(f"Claude API request failed: {e}")
			return None
