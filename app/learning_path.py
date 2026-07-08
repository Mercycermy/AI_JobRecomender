from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional

from app.config import settings
from app.skill_normalizer import SkillNormalizer, normalize_skill_text

RESOURCES_PATH = str(settings.resources_path)


_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2, "": 3, None: 3}
_DIFFICULTY_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2, "expert": 3}
_GAP_PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


class LearningPath:
	"""Return curated learning resources for a set of skill gaps."""

	def __init__(self, resources_path: str = RESOURCES_PATH, normalizer: Optional[SkillNormalizer] = None):
		self.resources_path = resources_path
		self.normalizer = normalizer or SkillNormalizer()
		self._resources: List[Dict[str, Any]] = []
		self._load_resources()

	def _load_resources(self) -> None:
		if not os.path.exists(self.resources_path):
			return

		with open(self.resources_path, "r", encoding="utf-8") as handle:
			payload = json.load(handle)

		self._resources = []
		for resource in payload.get("resources", []):
			item = dict(resource)
			raw_skill_id = item.get("skill_id")
			item["skill_id"] = self.normalizer.to_skill_id(raw_skill_id) or raw_skill_id
			self._resources.append(item)

	def _normalize_gap_inputs(
		self,
		gaps_or_skill_ids: Iterable[Any],
	) -> List[Dict[str, Any]]:
		gaps: List[Dict[str, Any]] = []
		seen: set[str] = set()
		for raw in gaps_or_skill_ids:
			if isinstance(raw, dict):
				skill_id = raw.get("skill_id")
				gap = dict(raw)
			else:
				skill_id = raw
				gap = {"skill_id": raw}
			resolved = self.normalizer.to_skill_id(skill_id) or str(skill_id or "").strip()
			if not resolved or resolved in seen:
				continue
			if not self.normalizer.is_match_skill(resolved):
				continue
			seen.add(resolved)
			gap["skill_id"] = resolved
			gap.setdefault("skill", self.normalizer.name_for(resolved))
			gaps.append(gap)
		return gaps

	def _difficulty_fit(self, resource: Dict[str, Any], gap: Dict[str, Any]) -> float:
		current = int(gap.get("current") or 0)
		target_level = "beginner"
		if current >= 65:
			target_level = "advanced"
		elif current >= 35:
			target_level = "intermediate"
		resource_level = str(resource.get("difficulty") or "").lower()
		distance = abs(
			_DIFFICULTY_ORDER.get(resource_level, 1)
			- _DIFFICULTY_ORDER.get(target_level, 1)
		)
		return max(0.0, 1.0 - (distance * 0.35))

	def _priority_fit(self, resource: Dict[str, Any], gap: Dict[str, Any]) -> float:
		resource_priority = str(
			resource.get("job_gap_alignment", {}).get("gap_priority") or ""
		).lower()
		gap_label = str(gap.get("priority_label") or "").lower()
		if resource_priority and resource_priority == gap_label:
			return 1.0
		return {
			"high": 0.85,
			"medium": 0.7,
			"low": 0.55,
		}.get(resource_priority, 0.45)

	def _usefulness_score(self, resource: Dict[str, Any], gap: Dict[str, Any]) -> float:
		score = 0.35
		quality = str(resource.get("source_quality") or "").lower()
		if quality in {"official", "vendor", "university"}:
			score += 0.25
		if resource.get("verification_status") == "verified":
			score += 0.15
		if resource.get("covers"):
			score += min(0.15, len(resource.get("covers", [])) * 0.03)
		best_for = [str(item).lower() for item in resource.get("best_for", [])]
		category = str(gap.get("target_role") or gap.get("category") or "").lower()
		if category and any(item in category or category in item for item in best_for):
			score += 0.10
		return min(1.0, score)

	def _score_resource(self, resource: Dict[str, Any], gap: Dict[str, Any]) -> float:
		priority_score = self._priority_fit(resource, gap)
		difficulty_score = self._difficulty_fit(resource, gap)
		usefulness_score = self._usefulness_score(resource, gap)
		free_score = 1.0 if bool(resource.get("is_free")) else 0.55
		return (
			priority_score * 0.35
			+ difficulty_score * 0.25
			+ usefulness_score * 0.30
			+ free_score * 0.10
		)

	def _relatedness_score(self, resource: Dict[str, Any], gap: Dict[str, Any]) -> float:
		gap_skill_id = gap.get("skill_id")
		resource_skill_id = resource.get("skill_id")
		if not gap_skill_id or not resource_skill_id:
			return 0.0
		if resource_skill_id == gap_skill_id:
			return 1.0

		gap_meta = self.normalizer.metadata_for(gap_skill_id)
		resource_meta = self.normalizer.metadata_for(resource_skill_id)
		if not gap_meta or not resource_meta:
			return 0.0

		score = 0.0
		if gap_meta.get("domain") and gap_meta.get("domain") == resource_meta.get("domain"):
			score += 0.20
		if gap_meta.get("category") and gap_meta.get("category") == resource_meta.get("category"):
			score += 0.35

		gap_tags = set(self.normalizer.tags_for(gap_skill_id))
		resource_tags = set(self.normalizer.tags_for(resource_skill_id))
		shared_tags = gap_tags & resource_tags
		if shared_tags:
			score += min(0.45, len(shared_tags) * 0.18)

		gap_name = self.normalizer.name_for(gap_skill_id).lower()
		resource_name = self.normalizer.name_for(resource_skill_id).lower()
		if gap_name and resource_name and (gap_name in resource_name or resource_name in gap_name):
			score += 0.20

		resource_text = normalize_skill_text(
			" ".join(
				str(item or "")
				for item in [
					resource.get("title"),
					resource.get("platform"),
					resource_name,
					*(resource.get("covers") or []),
				]
			)
		)
		gap_text = normalize_skill_text(
			" ".join(
				str(item or "")
				for item in [
					gap_name,
					gap_meta.get("category"),
				]
			)
		)
		gap_terms = {
			term
			for term in gap_text.split()
			if len(term) >= 4 and term not in {"management", "general"}
		}
		if gap_terms and any(term in resource_text for term in gap_terms):
			score += 0.20

		return min(1.0, score)

	def _explanation(self, resource: Dict[str, Any], gap: Dict[str, Any]) -> str:
		alignment = resource.get("job_gap_alignment", {})
		reason = alignment.get("why_this_resource")
		if reason:
			return reason
		skill_name = gap.get("skill") or self.normalizer.name_for(gap.get("skill_id"))
		level = resource.get("difficulty") or "practical"
		cost = "free" if resource.get("is_free") else "paid"
		return (
			f"Recommended for {skill_name} because it is a {level} {cost} "
			"resource aligned with this gap."
		)

	def _resource_payload(
		self,
		item: Dict[str, Any],
		gap: Dict[str, Any],
		rank: int,
		score: float,
	) -> Dict[str, Any]:
		is_free = bool(item.get("is_free"))
		return {
			"resource_id": item.get("resource_id"),
			"skill_id": item.get("skill_id"),
			"title": item.get("title"),
			"platform": item.get("platform"),
			"level": item.get("difficulty"),
			"hours": item.get("estimated_hours"),
			"url": item.get("url"),
			"link": item.get("url"),
			"resource_type": item.get("resource_type"),
			"gap_priority": item.get("job_gap_alignment", {}).get("gap_priority"),
			"covers": item.get("covers", []),
			"is_free": is_free,
			"cost": "free" if is_free else "paid",
			"best_for": item.get("best_for", []),
			"rank": rank,
			"recommendation_score": round(score * 100, 1),
			"explanation": self._explanation(item, gap),
		}

	def recommend_resources(
		self,
		skill_ids: Iterable[Any],
		limit_per_skill: int = 3,
	) -> List[Dict[str, Any]]:
		gaps = self._normalize_gap_inputs(skill_ids)
		if not gaps or not self._resources:
			return []

		grouped: Dict[str, List[Dict[str, Any]]] = {gap["skill_id"]: [] for gap in gaps}
		for resource in self._resources:
			sid = resource.get("skill_id")
			if sid in grouped:
				grouped[sid].append(resource)

		result: List[Dict[str, Any]] = []
		for gap in sorted(
			gaps,
			key=lambda item: (
				_GAP_PRIORITY_ORDER.get(item.get("priority_label"), 3),
				-int(item.get("priority") or 0),
				item.get("skill_id", ""),
			),
		):
			sid = gap["skill_id"]
			items = grouped.get(sid, [])
			if not items:
				items = [
					item
					for item in self._resources
					if self._relatedness_score(item, gap) >= 0.65
				]
			if not items:
				continue

			scored = sorted(
				(
					(
						self._score_resource(item, gap)
						* (0.7 + 0.3 * self._relatedness_score(item, gap)),
						item,
					)
					for item in items
				),
				key=lambda pair: (
					-pair[0],
					_PRIORITY_ORDER.get(
						pair[1].get("job_gap_alignment", {}).get("gap_priority"), 3
					),
					0 if pair[1].get("is_free") else 1,
					pair[1].get("estimated_hours") or 9999,
					pair[1].get("title") or "",
				),
			)

			trimmed = scored[:limit_per_skill]
			result.append(
				{
					"skill_id": sid,
					"skill": self.normalizer.name_for(sid),
					"priority": gap.get("priority"),
					"priority_label": gap.get("priority_label"),
					"gap_current": gap.get("current"),
					"gap_required": gap.get("required"),
					"resources": [
						self._resource_payload(item, gap, rank, score)
						for rank, (score, item) in enumerate(trimmed, start=1)
					],
				}
			)

		return result
