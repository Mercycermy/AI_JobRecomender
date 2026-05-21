from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.ai_client import AIClient

logger = logging.getLogger(__name__)

DEFAULT_TIPS = [
	{
		"section": "Summary",
		"icon": "01",
		"tips": [
			"Lead with a measurable role target, not a generic objective.",
			"Name your strongest domain signal in the first sentence.",
		],
	},
	{
		"section": "Experience",
		"icon": "02",
		"tips": [
			"Turn project bullets into impact statements with metrics.",
			"Show the decision you influenced, not only the task you completed.",
		],
	},
	{
		"section": "Skills",
		"icon": "03",
		"tips": [
			"Group tools by workflow: analysis, delivery, collaboration.",
			"Keep your top matched skills visible above older tools.",
		],
	},
	{
		"section": "Keywords",
		"icon": "04",
		"tips": [
			"Mirror job posting language for core skills without keyword stuffing.",
			"Include role-specific nouns such as experimentation, dashboards, APIs, and research synthesis.",
		],
	},
]

DEFAULT_SCHEDULE = [
	{
		"week": "Week 1",
		"focus": "Core Skill Alignment",
		"tasks": [
			"Identify the single highest frequency skill gap from your recommendations.",
			"Review official documentation and complete a basic hello-world or tutorial project."
		]
	},
	{
		"week": "Week 2",
		"focus": "Practical Application",
		"tasks": [
			"Build a small, standalone project utilizing your new skills.",
			"Commit the project to GitHub and write a clear README explaining your implementation."
		]
	},
	{
		"week": "Week 3",
		"focus": "Resume Integration",
		"tasks": [
			"Update your resume's experience section using impact statements and metrics.",
			"Add the newly acquired skills to your technical skills section under a relevant group."
		]
	},
	{
		"week": "Week 4",
		"focus": "Community & Outreach",
		"tasks": [
			"Share your project on LinkedIn or local developer communities for feedback.",
			"Apply to 2 targeted roles that list your newly learned skills as requirements."
		]
	}
]


class ResumeCoach:
	"""AI Resume Coach module that generates resume optimization suggestions and schedules."""

	def __init__(self, ai_client: Optional[AIClient] = None):
		self.ai_client = ai_client or AIClient()

	def get_coaching(
		self,
		profile: Dict[str, Any],
		gaps: List[Dict[str, Any]],
	) -> Dict[str, Any]:
		"""Get personalized coaching. Falls back to static tips if AI client is unavailable or fails."""
		skills = profile.get("detected_skills") or []
		target_category = profile.get("top_category") or "General"

		if self.ai_client.is_available():
			try:
				result = self.ai_client.generate_resume_tips(skills, gaps, target_category)
				if result and isinstance(result, dict) and "tips" in result:
					return {
						"tips": result["tips"],
						"schedule": result.get("schedule") or DEFAULT_SCHEDULE,
						"is_ai": True
					}
			except Exception as e:
				logger.error(f"Failed to get AI coaching: {e}")

		# Fallback static content
		return {
			"tips": DEFAULT_TIPS,
			"schedule": DEFAULT_SCHEDULE,
			"is_ai": False
		}
