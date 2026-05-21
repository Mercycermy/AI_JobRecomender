from __future__ import annotations

import json
import os
from typing import Dict, Iterable, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAXONOMY_PATH = os.path.join(BASE_DIR, "data", "skills_taxonomy.json")


class SkillNormalizer:
	"""Normalize skill names to taxonomy IDs and resolve display labels."""

	def __init__(self, taxonomy_path: str = TAXONOMY_PATH):
		self.taxonomy_path = taxonomy_path
		self._id_to_name: Dict[str, str] = {}
		self._alias_to_id: Dict[str, str] = {}
		self._load_taxonomy()

	def _load_taxonomy(self) -> None:
		if not os.path.exists(self.taxonomy_path):
			return

		with open(self.taxonomy_path, "r", encoding="utf-8") as handle:
			data = json.load(handle)

		for item in data.get("skills", []):
			skill_id = item.get("skill_id")
			canonical = item.get("canonical_name")
			if not skill_id or not canonical:
				continue

			self._id_to_name[skill_id] = canonical
			self._alias_to_id[canonical.lower()] = skill_id

			for alias in item.get("aliases", []):
				if alias:
					self._alias_to_id[str(alias).lower()] = skill_id

			# Allow passing the ID itself as an alias.
			self._alias_to_id[skill_id.lower()] = skill_id

	def to_skill_id(self, value: Optional[str]) -> Optional[str]:
		if not value:
			return None
		return self._alias_to_id.get(value.strip().lower())

	def name_for(self, skill_id: Optional[str]) -> str:
		if not skill_id:
			return "Unknown"
		return self._id_to_name.get(skill_id, skill_id.replace("-", " ").title())

	def normalize_list(self, values: Iterable[str]) -> list[str]:
		normalized = []
		for value in values:
			resolved = self.to_skill_id(value) if value else None
			if resolved and resolved not in normalized:
				normalized.append(resolved)
		return normalized
