from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional

from app.skill_normalizer import SkillNormalizer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_PATH = os.path.join(BASE_DIR, "data", "learning_resources.json")


_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2, "": 3, None: 3}


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

		self._resources = payload.get("resources", [])

	def recommend_resources(
		self,
		skill_ids: Iterable[str],
		limit_per_skill: int = 3,
	) -> List[Dict[str, Any]]:
		skill_ids = [sid for sid in skill_ids if sid]
		if not skill_ids or not self._resources:
			return []

		grouped: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid in skill_ids}
		for resource in self._resources:
			sid = resource.get("skill_id")
			if sid in grouped:
				grouped[sid].append(resource)

		result: List[Dict[str, Any]] = []
		for sid in skill_ids:
			items = grouped.get(sid, [])
			if not items:
				continue

			items.sort(
				key=lambda item: _PRIORITY_ORDER.get(
					item.get("job_gap_alignment", {}).get("gap_priority"), 3
				)
			)

			trimmed = items[:limit_per_skill]
			result.append(
				{
					"skill_id": sid,
					"skill": self.normalizer.name_for(sid),
					"resources": [
						{
							"resource_id": item.get("resource_id"),
							"title": item.get("title"),
							"platform": item.get("platform"),
							"level": item.get("difficulty"),
							"hours": item.get("estimated_hours"),
							"url": item.get("url"),
							"resource_type": item.get("resource_type"),
							"gap_priority": item.get("job_gap_alignment", {}).get("gap_priority"),
						}
						for item in trimmed
					],
				}
			)

		return result
