from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from app.skill_normalizer import SkillNormalizer


class GapAnalyzer:
	"""Summarize the highest-impact skill gaps from recommendation results."""

	def __init__(self, normalizer: Optional[SkillNormalizer] = None):
		self.normalizer = normalizer or SkillNormalizer()

	def analyze(
		self,
		profile: Optional[Dict[str, Any]],
		recommendations: Iterable[Dict[str, Any]],
		top_n: int = 10,
		limit: int = 8,
	) -> List[Dict[str, Any]]:
		recs = list(recommendations)[:max(1, top_n)] if recommendations else []
		if not recs:
			return []

		missing_counts: Counter[str] = Counter()
		for rec in recs:
			missing = rec.get("missing_skills") or []
			for skill_id in missing:
				if skill_id:
					missing_counts[str(skill_id)] += 1

		if not missing_counts:
			return []

		total = max(len(recs), 1)
		gaps: List[Dict[str, Any]] = []

		for skill_id, count in missing_counts.most_common(limit):
			priority = round((count / total) * 100)
			if priority >= 70:
				level = "Advanced"
			elif priority >= 40:
				level = "Intermediate"
			else:
				level = "Beginner"

			current = max(10, 70 - round(priority * 0.5))
			required = min(95, current + 30)

			gaps.append(
				{
					"skill_id": skill_id,
					"skill": self.normalizer.name_for(skill_id),
					"priority": priority,
					"level": level,
					"current": current,
					"required": required,
					"occurrences": count,
				}
			)

		return gaps
