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


def _clamp_percent(value: float, minimum: int = 0, maximum: int = 100) -> int:
	return max(minimum, min(maximum, round(value)))


def _level_from_percent(value: int) -> str:
	if value >= 75:
		return "Advanced"
	if value >= 45:
		return "Intermediate"
	return "Beginner"


def _priority_metadata(priority: int) -> Dict[str, str]:
	if priority >= 70:
		return {
			"priority_label": "High",
			"level": "Advanced",
			"priority_group": "learn_first",
		}
	if priority >= 40:
		return {
			"priority_label": "Medium",
			"level": "Intermediate",
			"priority_group": "build_next",
		}
	return {
		"priority_label": "Low",
		"level": "Beginner",
		"priority_group": "watchlist",
	}


def _learning_path(
	skill_name: str,
	current: int,
	required: int,
	priority_label: str,
) -> List[Dict[str, Any]]:
	if current < 40:
		start = f"Learn the core concepts and common vocabulary for {skill_name}."
	elif current < 70:
		start = f"Practice job-style tasks that use {skill_name} in a realistic workflow."
	else:
		start = f"Polish advanced {skill_name} examples and prepare interview talking points."

	return [
		{
			"order": 1,
			"title": "Close the foundation gap",
			"description": start,
		},
		{
			"order": 2,
			"title": "Build proof",
			"description": (
				f"Create or update one project that shows {skill_name} at "
				f"roughly {required}% readiness."
			),
		},
		{
			"order": 3,
			"title": "Apply to matched roles",
			"description": (
				f"Add {skill_name} evidence to your resume before applying to "
				f"{priority_label.lower()} priority matches."
			),
		},
	]


def get_session_gaps(
	session: Dict[str, Any],
	normalizer: Optional[SkillNormalizer] = None,
) -> List[Dict[str, Any]]:
	"""Return ranked skill gaps from a completed quiz session.

	Each gap is shaped as: {skill_id, score, query}.
	"""
	normalizer = normalizer or SkillNormalizer()
	skill_scores = session.get("skill_scores", {}) or {}
	if not isinstance(skill_scores, dict):
		return []

	gaps: List[Dict[str, Any]] = []
	for skill_id, score in skill_scores.items():
		if not normalizer.is_match_skill(str(skill_id)):
			continue
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


def format_gaps_for_ui(
	session: Dict[str, Any],
	normalizer: Optional[SkillNormalizer] = None,
) -> List[Dict[str, Any]]:
	"""Map quiz session gaps to the shape expected by the results UI."""
	normalizer = normalizer or SkillNormalizer()
	formatted: List[Dict[str, Any]] = []

	for gap in get_session_gaps(session, normalizer):
		score = float(gap.get("score", 0.0))
		current = max(5, min(99, round(score * 100)))
		required = min(95, max(current + 20, 75))
		priority = round((1.0 - score) * 100)
		meta = _priority_metadata(priority)
		skill_name = normalizer.name_for(gap["skill_id"])

		formatted.append(
			{
				"skill_id": gap["skill_id"],
				"skill": skill_name,
				"priority": priority,
				"priority_label": meta["priority_label"],
				"priority_group": meta["priority_group"],
				"level": meta["level"],
				"current": current,
				"required": required,
				"current_level": _level_from_percent(current),
				"required_level": _level_from_percent(required),
				"learning_path": _learning_path(
					skill_name,
					current,
					required,
					meta["priority_label"],
				),
				"score": gap.get("score"),
			}
		)

	formatted.sort(key=lambda item: item["priority"], reverse=True)
	return formatted


class GapAnalyzer:
	"""Summarize the highest-impact skill gaps from recommendation results."""

	def __init__(self, normalizer: Optional[SkillNormalizer] = None):
		self.normalizer = normalizer or SkillNormalizer()

	def _profile_skill_set(self, profile: Optional[Dict[str, Any]]) -> set[str]:
		if not profile:
			return set()
		raw_skills = (
			profile.get("skill_ids")
			or profile.get("detected_skills")
			or profile.get("skills")
			or []
		)
		skills: set[str] = set()
		for skill in raw_skills:
			text = str(skill or "").strip()
			if not text:
				continue
			resolved = self.normalizer.to_skill_id(text)
			if resolved and self.normalizer.is_match_skill(resolved):
				skills.add(resolved)
				continue
			if self.normalizer.is_match_skill(text):
				skills.add(text)
		return skills

	def _skill_score(
		self,
		profile: Optional[Dict[str, Any]],
		skill_id: str,
		user_skills: set[str],
	) -> float:
		if not profile:
			return 0.0
		scores = profile.get("skill_scores") or {}
		candidates = [skill_id]
		resolved = self.normalizer.to_skill_id(skill_id)
		if resolved and resolved not in candidates:
			candidates.append(resolved)
		for candidate in candidates:
			try:
				return max(0.0, min(1.0, float(scores[candidate])))
			except (KeyError, TypeError, ValueError):
				continue
		return 0.65 if skill_id in user_skills else 0.0

	def _missing_skills_for_job(
		self,
		rec: Dict[str, Any],
		user_skills: set[str],
	) -> List[str]:
		missing = rec.get("missing_skills")
		if missing is None and rec.get("required_skills"):
			missing = [
				skill_id
				for skill_id in rec.get("required_skills", [])
				if str(skill_id) not in user_skills
			]
		if not isinstance(missing, list):
			return []
		filtered: List[str] = []
		for skill_id in missing:
			text = str(skill_id or "").strip()
			if not text:
				continue
			resolved = self.normalizer.to_skill_id(text) or text
			if self.normalizer.is_match_skill(resolved):
				filtered.append(text)
		return filtered

	def _job_summary(self, rec: Dict[str, Any], rank: int) -> Dict[str, Any]:
		return {
			"job_id": str(rec.get("job_id") or rec.get("id") or ""),
			"title": (
				rec.get("job_title")
				or rec.get("title")
				or f"Recommended job {rank}"
			),
			"rank": rank,
			"match_percent": rec.get("match_percent", rec.get("match_score")),
			"required_skill_count": rec.get("required_skill_count"),
		}

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
		affected_jobs: Dict[str, List[Dict[str, Any]]] = {}
		user_skills = self._profile_skill_set(profile)
		for index, rec in enumerate(recs, start=1):
			missing = self._missing_skills_for_job(rec, user_skills)
			for skill_id in dict.fromkeys(missing):
				if skill_id:
					missing_counts[str(skill_id)] += 1
					affected_jobs.setdefault(str(skill_id), []).append(
						self._job_summary(rec, index)
					)

		if not missing_counts:
			return []

		total = max(len(recs), 1)
		gaps: List[Dict[str, Any]] = []

		for skill_id, count in missing_counts.most_common(limit):
			priority = round((count / total) * 100)
			meta = _priority_metadata(priority)
			score = self._skill_score(profile, skill_id, user_skills)
			current = _clamp_percent(score * 100, minimum=5, maximum=95)
			if score == 0.0 and skill_id not in user_skills:
				current = 15
			required = min(
				95,
				max(current + 20, 70 + round(priority * 0.2)),
			)
			skill_name = self.normalizer.name_for(skill_id)

			gaps.append(
				{
					"skill_id": skill_id,
					"skill": skill_name,
					"priority": priority,
					"priority_label": meta["priority_label"],
					"priority_group": meta["priority_group"],
					"level": meta["level"],
					"current": current,
					"required": required,
					"current_level": _level_from_percent(current),
					"required_level": _level_from_percent(required),
					"occurrences": count,
					"frequency": round(count / total, 3),
					"job_count": total,
					"job_ids": [
						job["job_id"]
						for job in affected_jobs.get(skill_id, [])
						if job.get("job_id")
					],
					"affected_jobs": affected_jobs.get(skill_id, []),
					"learning_path": _learning_path(
						skill_name,
						current,
						required,
						meta["priority_label"],
					),
					"first_action": (
						f"Start with {skill_name}; it is missing from "
						f"{count} of the top {total} matched jobs."
					),
				}
			)

		return gaps
