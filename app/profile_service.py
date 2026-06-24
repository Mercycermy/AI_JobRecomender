"""Canonical profile boundary shared by manual input, quiz, and matching."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from app.canonical import (
    CanonicalProfile,
    profile_from_manual_input,
    profile_from_quiz_result,
    stable_id,
    validate_profile,
)
from app.skill_normalizer import SkillNormalizer


class ProfileValidationError(ValueError):
    """Raised when a request cannot be converted to a usable profile."""


class ProfileService:
    def __init__(self, normalizer: Optional[SkillNormalizer] = None):
        self.normalizer = normalizer or SkillNormalizer()

    def from_payload(
        self,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
        source_hint: Optional[str] = None,
    ) -> CanonicalProfile:
        if not isinstance(payload, dict):
            raise ProfileValidationError("Profile must be a JSON object.")

        source = source_hint or payload.get("source")
        if source == "quiz" or self._looks_like_quiz_profile(payload):
            profile = profile_from_quiz_result(
                payload,
                user_id=user_id,
                normalizer=self.normalizer,
            )
        else:
            raw_skills = (
                payload.get("skill_ids")
                or payload.get("detected_skills")
                or payload.get("skills")
                or []
            )
            if not isinstance(raw_skills, list):
                raise ProfileValidationError("skills must be a list.")

            profile = profile_from_manual_input(
                skills=raw_skills,
                experience_level=(
                    payload.get("experience_level")
                    or payload.get("experience")
                    or "junior"
                ),
                target_role=(
                    payload.get("target_role")
                    or payload.get("detected_role")
                    or payload.get("top_category")
                    or payload.get("category")
                ),
                location=payload.get("location") or "remote",
                user_id=user_id or payload.get("user_id"),
                normalizer=self.normalizer,
            )
            if raw_skills and not profile.skill_ids:
                raise ProfileValidationError(
                    "No supplied skills matched the project skill taxonomy."
                )
            profile.detected_domain = payload.get("detected_domain")
            profile.detected_role = (
                payload.get("detected_role") or profile.target_role
            )

        if payload.get("profile_id"):
            profile.profile_id = str(payload["profile_id"])
        elif not profile.profile_id:
            profile.profile_id = stable_id("profile", profile.source, user_id)

        errors = validate_profile(profile)
        if errors:
            raise ProfileValidationError("; ".join(errors))
        return profile

    def to_recommender_input(self, profile: CanonicalProfile) -> Dict[str, Any]:
        category = (
            profile.target_role
            or profile.detected_role
            or profile.detected_domain
            or ""
        )
        return {
            "profile_id": profile.profile_id,
            "source": profile.source,
            "skill_ids": list(profile.skill_ids),
            "detected_skills": list(profile.skill_ids),
            "skills": list(profile.skill_ids),
            "skill_scores": dict(profile.skill_scores),
            "top_category": category,
            "category": category,
            "detected_domain": profile.detected_domain,
            "detected_role": profile.detected_role,
            "experience_level": profile.experience_level,
            "location": profile.location,
            "confidence": profile.confidence,
        }

    def serialize(self, profile: CanonicalProfile) -> Dict[str, Any]:
        data = asdict(profile)
        # Compatibility aliases for the current frontend and recommender.
        data["detected_skills"] = list(profile.skill_ids)
        data["top_category"] = (
            profile.target_role
            or profile.detected_role
            or profile.detected_domain
        )
        return data

    def normalize_skills(self, values: Any) -> Dict[str, Any]:
        if not isinstance(values, list):
            raise ProfileValidationError("skills must be a list.")
        skill_ids, unresolved = self.normalizer.normalize_with_unresolved(values)
        return {
            "skill_ids": skill_ids,
            "skills": [
                {
                    "skill_id": skill_id,
                    "skill_name": self.normalizer.name_for(skill_id),
                }
                for skill_id in skill_ids
            ],
            "unresolved": unresolved,
        }

    @staticmethod
    def _looks_like_quiz_profile(payload: Dict[str, Any]) -> bool:
        return bool(
            payload.get("session_id")
            or payload.get("skill_scores")
            or payload.get("domain_scores")
            or payload.get("category_scores")
        )
