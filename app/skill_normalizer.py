"""Taxonomy-backed skill normalization and text extraction."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAXONOMY_PATH = os.path.join(BASE_DIR, "data", "skills_taxonomy.json")
OVERRIDES_PATH = os.path.join(BASE_DIR, "data", "skill_alias_overrides.json")

# These short words are valid exact skills but are too ambiguous to extract
# automatically from normal prose.
_TEXT_ALIAS_BLOCKLIST = {
    "ai",
    "c",
    "go",
    "hr",
    "it",
    "ml",
    "pr",
    "r",
}


@dataclass(frozen=True)
class SkillMatch:
    skill_id: str
    skill_name: str
    matched_text: str
    normalized_text: str
    confidence: float
    method: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_skill_text(value: Any) -> str:
    """Normalize punctuation and spacing without destroying C++, C#, or .NET."""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[/_,;:(){}\[\]|\\]+", " ", text)
    text = re.sub(r"[-–—]+", " ", text)
    text = re.sub(r"[^a-z0-9+#.\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class SkillNormalizer:
    """Resolve aliases, legacy IDs, and free text to canonical skill IDs."""

    def __init__(
        self,
        taxonomy_path: str = TAXONOMY_PATH,
        overrides_path: str = OVERRIDES_PATH,
    ):
        self.taxonomy_path = taxonomy_path
        self.overrides_path = overrides_path
        self._id_to_name: Dict[str, str] = {}
        self._id_to_item: Dict[str, Dict[str, Any]] = {}
        self._id_to_weight: Dict[str, float] = {}
        self._id_to_tags: Dict[str, Tuple[str, ...]] = {}
        self._alias_to_ids: Dict[str, List[str]] = {}
        self._alias_to_id: Dict[str, str] = {}
        self._preferred_aliases: Dict[str, str] = {}
        self._legacy_skill_ids: Dict[str, str] = {}
        self._ignored_terms: set[str] = set()
        self._extract_aliases: List[str] = []
        self._extract_pattern: Optional[re.Pattern[str]] = None
        self._load_taxonomy()

    def _add_alias(self, alias: Any, skill_id: str) -> None:
        normalized = normalize_skill_text(alias)
        if not normalized:
            return
        ids = self._alias_to_ids.setdefault(normalized, [])
        if skill_id not in ids:
            ids.append(skill_id)

    def _load_taxonomy(self) -> None:
        if not os.path.exists(self.taxonomy_path):
            return

        with open(self.taxonomy_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        for item in data.get("skills", []):
            skill_id = str(item.get("skill_id") or "").strip()
            canonical = str(item.get("canonical_name") or "").strip()
            if not skill_id or not canonical:
                continue

            self._id_to_name[skill_id] = canonical
            self._id_to_item[skill_id] = item
            try:
                self._id_to_weight[skill_id] = max(
                    0.1,
                    float(item.get("weight") or 1.0),
                )
            except (TypeError, ValueError):
                self._id_to_weight[skill_id] = 1.0
            self._id_to_tags[skill_id] = tuple(
                str(tag).strip()
                for tag in item.get("differentiation_tags", [])
                if str(tag).strip()
            )
            self._add_alias(skill_id, skill_id)
            self._add_alias(canonical, skill_id)
            for alias in item.get("aliases", []):
                self._add_alias(alias, skill_id)

        overrides: Dict[str, Any] = {}
        if os.path.exists(self.overrides_path):
            with open(self.overrides_path, "r", encoding="utf-8") as handle:
                overrides = json.load(handle)

        self._preferred_aliases = {
            normalize_skill_text(alias): str(skill_id)
            for alias, skill_id in (overrides.get("preferred_aliases") or {}).items()
        }
        self._legacy_skill_ids = {
            normalize_skill_text(alias): str(skill_id)
            for alias, skill_id in (overrides.get("legacy_skill_ids") or {}).items()
        }
        self._ignored_terms = {
            normalize_skill_text(term)
            for term in (overrides.get("ignored_terms") or [])
            if normalize_skill_text(term)
        }

        for skill_id, aliases in (overrides.get("extra_aliases") or {}).items():
            if skill_id not in self._id_to_name:
                continue
            for alias in aliases:
                self._add_alias(alias, skill_id)

        for legacy_id, canonical_id in self._legacy_skill_ids.items():
            if canonical_id in self._id_to_name:
                self._add_alias(legacy_id, canonical_id)

        for alias, ids in self._alias_to_ids.items():
            self._alias_to_id[alias] = self._choose_candidate(alias, ids)

        self._extract_aliases = sorted(
            (
                alias
                for alias in self._alias_to_id
                if alias not in _TEXT_ALIAS_BLOCKLIST
                and (len(alias) >= 3 or any(char in alias for char in "+#."))
            ),
            key=lambda item: (-len(item), item),
        )
        if self._extract_aliases:
            alternatives = "|".join(re.escape(alias) for alias in self._extract_aliases)
            self._extract_pattern = re.compile(
                rf"(?<![a-z0-9])(?P<alias>{alternatives})(?![a-z0-9])"
            )

    def _choose_candidate(self, alias: str, ids: Iterable[str]) -> str:
        candidates = list(dict.fromkeys(ids))
        preferred = self._preferred_aliases.get(alias)
        if preferred in candidates:
            return preferred

        def rank(skill_id: str) -> Tuple[float, str]:
            item = self._id_to_item.get(skill_id, {})
            return (float(item.get("weight") or 1.0), skill_id)

        return max(candidates, key=rank)

    def to_skill_id(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        normalized = normalize_skill_text(value)
        if not normalized:
            return None
        if normalized in self._legacy_skill_ids:
            target = self._legacy_skill_ids[normalized]
            return target if target in self._id_to_name else None
        if value in self._id_to_name:
            return value
        return self._alias_to_id.get(normalized)

    def candidates_for(self, value: Optional[str]) -> List[str]:
        normalized = normalize_skill_text(value)
        if not normalized:
            return []
        if normalized in self._legacy_skill_ids:
            return [self._legacy_skill_ids[normalized]]
        return list(self._alias_to_ids.get(normalized, []))

    def name_for(self, skill_id: Optional[str]) -> str:
        if not skill_id:
            return "Unknown"
        resolved = self.to_skill_id(skill_id) or skill_id
        return self._id_to_name.get(
            resolved, str(resolved).replace("-", " ").title()
        )

    def metadata_for(self, skill_id: Optional[str]) -> Dict[str, Any]:
        """Return a copy of the canonical taxonomy metadata for a skill."""
        if not skill_id:
            return {}
        resolved = self.to_skill_id(skill_id) or skill_id
        return dict(self._id_to_item.get(resolved, {}))

    def weight_for(self, skill_id: Optional[str]) -> float:
        """Return the taxonomy importance weight used by explainable matching."""
        if not skill_id:
            return 1.0
        resolved = (
            skill_id
            if skill_id in self._id_to_weight
            else self.to_skill_id(skill_id) or skill_id
        )
        return self._id_to_weight.get(resolved, 1.0)

    def tags_for(self, skill_id: Optional[str]) -> List[str]:
        """Return role/differentiation tags for lightweight semantic matching."""
        if not skill_id:
            return []
        resolved = (
            skill_id
            if skill_id in self._id_to_tags
            else self.to_skill_id(skill_id) or skill_id
        )
        return list(self._id_to_tags.get(resolved, ()))

    def is_match_skill(self, skill_id: Optional[str]) -> bool:
        """Return true for hard skills that should drive matching and gaps."""
        if not skill_id:
            return False
        item = self.metadata_for(skill_id)
        if not item:
            return True
        category = normalize_skill_text(item.get("category"))
        domain = normalize_skill_text(item.get("domain"))
        tags = {normalize_skill_text(tag) for tag in item.get("differentiation_tags", [])}
        return not (
            category in {"soft skills", "languages"}
            or domain in {"soft skills", "soft skills and languages"}
            or "language" in tags
        )

    def extract_matches(self, text: Optional[str]) -> List[SkillMatch]:
        if not text or self._extract_pattern is None:
            return []

        normalized_text = normalize_skill_text(text)
        best_by_skill: Dict[str, SkillMatch] = {}
        for match in self._extract_pattern.finditer(normalized_text):
            alias = match.group("alias")
            skill_id = self._alias_to_id.get(alias)
            if not skill_id:
                continue

            candidates = self._alias_to_ids.get(alias, [])
            confidence = 0.93 if len(candidates) == 1 else 0.84
            current = best_by_skill.get(skill_id)
            candidate = SkillMatch(
                skill_id=skill_id,
                skill_name=self.name_for(skill_id),
                matched_text=alias,
                normalized_text=alias,
                confidence=confidence,
                method="phrase",
            )
            if current is None or len(alias) > len(current.normalized_text):
                best_by_skill[skill_id] = candidate

        return sorted(
            best_by_skill.values(),
            key=lambda item: (-item.confidence, item.skill_name),
        )

    def extract_skills(self, text: Optional[str]) -> List[str]:
        return [match.skill_id for match in self.extract_matches(text)]

    def normalize_list(self, values: Iterable[str]) -> List[str]:
        normalized: List[str] = []
        for value in values:
            if not value:
                continue
            resolved = self.to_skill_id(value)
            candidates = [resolved] if resolved else self.extract_skills(value)
            for skill_id in candidates:
                if skill_id and skill_id not in normalized:
                    normalized.append(skill_id)
        return normalized

    def normalize_with_unresolved(
        self, values: Iterable[str]
    ) -> Tuple[List[str], List[str]]:
        normalized: List[str] = []
        unresolved: List[str] = []
        for value in values:
            resolved = self.normalize_list([value])
            if resolved:
                for skill_id in resolved:
                    if skill_id not in normalized:
                        normalized.append(skill_id)
            elif str(value or "").strip():
                unresolved.append(str(value).strip())
        return normalized, unresolved

    def suggest(self, query: Optional[str], limit: int = 8) -> List[Dict[str, Any]]:
        normalized_query = normalize_skill_text(query)
        if not normalized_query:
            return []

        ranked: List[Tuple[int, float, str, str]] = []
        for skill_id, item in self._id_to_item.items():
            name = self._id_to_name[skill_id]
            normalized_name = normalize_skill_text(name)
            aliases = {
                normalize_skill_text(alias)
                for alias in [skill_id, name, *(item.get("aliases") or [])]
                if normalize_skill_text(alias)
            }

            if normalized_query == normalized_name or normalized_query == normalize_skill_text(skill_id):
                match_rank = 0
            elif normalized_name.startswith(normalized_query):
                match_rank = 1
            elif any(alias.startswith(normalized_query) for alias in aliases):
                match_rank = 2
            elif normalized_query in normalized_name:
                match_rank = 3
            elif any(normalized_query in alias for alias in aliases):
                match_rank = 4
            else:
                continue

            ranked.append(
                (
                    match_rank,
                    -float(item.get("weight") or 1.0),
                    name.casefold(),
                    skill_id,
                )
            )

        suggestions = []
        for _, _, _, skill_id in sorted(ranked)[: max(1, min(limit, 25))]:
            item = self._id_to_item[skill_id]
            suggestions.append(
                {
                    "skill_id": skill_id,
                    "skill_name": self._id_to_name[skill_id],
                    "domain": item.get("domain"),
                    "category": item.get("category"),
                }
            )
        return suggestions

    def alias_collisions(self) -> Dict[str, List[str]]:
        return {
            alias: list(ids)
            for alias, ids in self._alias_to_ids.items()
            if len(ids) > 1
        }

    def is_ignored(self, value: Optional[str]) -> bool:
        return normalize_skill_text(value) in self._ignored_terms

    @property
    def skill_count(self) -> int:
        return len(self._id_to_name)
