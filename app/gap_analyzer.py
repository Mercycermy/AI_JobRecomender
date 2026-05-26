from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from app.skill_normalizer import SkillNormalizer


SKILL_THRESHOLD = 0.60
MAX_GAPS = 4

# Maps skill_ids to human-readable search phrases for FAISS queries.
SKILL_QUERY_MAP = {
	"it-support": "IT support networking troubleshooting",
	"tech-docker": "Docker containers DevOps deployment",
	"admin-hr": "human resources recruiting performance",
	"wellness-fitness": "personal trainer fitness anatomy",
	"sales-inbound": "inbound sales CRM closing strategies",
	"marketing-digital": "digital marketing SEO social media",
	"finance-excel": "Excel financial formulas pivot tables",
	"design-uiux": "UI UX design Figma prototyping",
	"eng-autocad": "AutoCAD 2D drafting civil mechanical",
	"eng-construction-mgmt": "construction project management scheduling",
	"admin-data-entry": "data entry typing speed accuracy",
	"freelance-management": "freelance client acquisition proposals",
	"admin-event-planning": "event planning vendor management logistics",
	"supply-chain-mgmt": "supply chain logistics warehouse operations",
	"logistics-safety": "workplace safety OSHA warehouse hazards",
	"craft-culinary": "culinary arts cooking knife skills",
	"med-health-science": "health sciences anatomy physiology nursing",
	"edu-instructional-design": "instructional design curriculum teaching",
	"prod-six-sigma": "six sigma quality control process improvement",
	"hosp-management": "hospitality hotel management guest experience",
	"hosp-food-safety": "food safety sanitation ServSafe",
	"fac-management": "facility management building operations",
	"sec-physical": "physical security threat assessment safety",
}


def get_session_gaps(session: Dict[str, Any]) -> List[Dict[str, Any]]:
	"""Return ranked skill gaps from a completed quiz session.

	Each gap is shaped as: {skill_id, score, query}.
	"""
	skill_scores = session.get("skill_scores", {}) or {}
	if not isinstance(skill_scores, dict):
		return []

	gaps: List[Dict[str, Any]] = []
	for skill_id, score in skill_scores.items():
		if score is None:
			continue
		avg = sum(score) / len(score) if isinstance(score, list) and score else score
		try:
			avg_value = float(avg)
		except (TypeError, ValueError):
			continue

		if avg_value < SKILL_THRESHOLD:
			query = SKILL_QUERY_MAP.get(str(skill_id), str(skill_id).replace("-", " "))
			gaps.append({
				"skill_id": str(skill_id),
				"score": round(avg_value, 3),
				"query": query,
			})

	gaps.sort(key=lambda g: g["score"])
	return gaps[:MAX_GAPS]


class GapAnalyzer:
	"""Summarize the highest-impact skill gaps from recommendation results."""

	def __init__(self, normalizer: Optional[SkillNormalizer] = None):
		self.normalizer = normalizer or SkillNormalizer()

	def analyze(
		self,
		profile: Optional[Dict[str, Any]],
		recommendations: Iterable[Dict[str, Any]],
		top_n: int = 3,
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
				priority_label = "High"
			elif priority >= 40:
				level = "Intermediate"
				priority_label = "Medium"
			else:
				level = "Beginner"
				priority_label = "Low"

			current = max(10, 70 - round(priority * 0.5))
			required = min(95, current + 30)

			gaps.append(
				{
					"skill_id": skill_id,
					"skill": self.normalizer.name_for(skill_id),
					"priority": priority,
					"priority_label": priority_label,
					"level": level,
					"current": current,
					"required": required,
					"occurrences": count,
				}
			)

		return gaps
