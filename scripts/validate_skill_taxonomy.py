"""Audit taxonomy coverage across jobs, resources, and quiz questions."""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings
from app.skill_normalizer import SkillNormalizer


def _question_skill_terms() -> Counter[str]:
    terms: Counter[str] = Counter()
    paths = sorted(glob.glob(str(settings.data_dir / "questions_part*.json")))
    role_path = settings.data_dir / "questions_role_interviews.json"
    if role_path.exists():
        paths.append(str(role_path))

    for path in paths:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        for question in payload.get("questions", []):
            values = list((question.get("scoring") or {}).get("skill_weights", {}))
            options = question.get("options")
            if isinstance(options, dict):
                for option in options.values():
                    if isinstance(option, dict):
                        values.extend(option.get("skills") or [])
            for evidence in question.get("job_evidence") or []:
                raw = evidence.get("evidence_skills")
                if isinstance(raw, list):
                    values.extend(raw)
                elif isinstance(raw, str):
                    values.extend(
                        part.strip() for part in raw.split(",") if part.strip()
                    )
            terms.update(str(value).strip() for value in values if str(value).strip())
    return terms


def build_report() -> dict:
    normalizer = SkillNormalizer()

    conn = sqlite3.connect(str(settings.recommender_db_path))
    try:
        db_skills = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT skill_id FROM job_skills ORDER BY skill_id"
            )
        ]
    finally:
        conn.close()

    with open(settings.resources_path, "r", encoding="utf-8") as handle:
        resource_payload = json.load(handle)
    resource_skills = sorted(
        {
            str(resource.get("skill_id") or "").strip()
            for resource in resource_payload.get("resources", [])
            if resource.get("skill_id")
        }
    )

    question_terms = _question_skill_terms()

    unresolved_db = [
        skill for skill in db_skills if normalizer.to_skill_id(skill) is None
    ]
    unresolved_resources = [
        skill for skill in resource_skills if normalizer.to_skill_id(skill) is None
    ]

    unresolved_questions: Counter[str] = Counter()
    ignored_questions: Counter[str] = Counter()
    for term, count in question_terms.items():
        if normalizer.normalize_list([term]):
            continue
        if normalizer.is_ignored(term):
            ignored_questions[term] += count
        else:
            unresolved_questions[term] += count

    collisions = normalizer.alias_collisions()
    return {
        "canonical_skills": normalizer.skill_count,
        "aliases": len(normalizer._alias_to_ids),
        "ambiguous_aliases": len(collisions),
        "ambiguous_aliases_with_deterministic_resolution": sum(
            1 for alias in collisions if normalizer.to_skill_id(alias)
        ),
        "job_skill_ids": len(db_skills),
        "unresolved_job_skill_ids": unresolved_db,
        "resource_skill_ids": len(resource_skills),
        "unresolved_resource_skill_ids": unresolved_resources,
        "question_skill_terms": len(question_terms),
        "question_skill_mentions": sum(question_terms.values()),
        "unresolved_question_terms": dict(unresolved_questions.most_common()),
        "unresolved_question_mentions": sum(unresolved_questions.values()),
        "ignored_non_skill_terms": dict(ignored_questions.most_common()),
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2))
    has_errors = bool(
        report["unresolved_job_skill_ids"]
        or report["unresolved_resource_skill_ids"]
        or report["unresolved_question_terms"]
    )
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
