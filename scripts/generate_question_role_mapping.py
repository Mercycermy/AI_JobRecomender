from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.quiz_engine import (
    CATEGORY_LABELS,
    CATEGORY_TO_ROLES,
    DOMAIN_SIGNAL_KEYS,
    ROLE_DISPLAY_LABELS,
    ROLE_LABELS,
    ROLE_TO_CATEGORY,
)


DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"
QUESTION_MAPPING_PATH = DATA_DIR / "question_role_mapping.json"
CATEGORY_DOC_PATH = DOCS_DIR / "question_role_mapping.md"


def _normalise_questions(raw: Any) -> list[dict]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("questions", "data", "items"):
            value = raw.get(key)
            if isinstance(value, list):
                return value
    return []


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _unique(values: Iterable[Any]) -> list[str]:
    seen: dict[str, None] = {}
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen[text] = None
    return list(seen)


def _role_label(role: str) -> str:
    if role in ROLE_DISPLAY_LABELS:
        return ROLE_DISPLAY_LABELS[role]
    labels = ROLE_LABELS.get(role) or []
    if labels:
        return labels[0].title()
    return role.replace("-", " ").replace("_", " ").title()


def _stage_for_question(question: dict) -> str:
    qid = str(question.get("id") or "")
    gate = question.get("gate")
    qtype = str(question.get("question_type") or "").lower()
    difficulty = str(question.get("difficulty") or "").lower()
    experience = str(question.get("experience_level_target") or "").lower()

    if qid.startswith("Q_G0_DOMAIN"):
        return "Domain Detection"
    if gate == 0:
        return "Domain Detection"
    if gate == 1:
        return "Sub-domain Narrowing"
    if "tie" in qid.lower() or "tiebreak" in qtype:
        return "Tie-breaker"
    if gate == 2 and (experience in {"junior", "mid", "senior"} or difficulty):
        return "Experience-Level / Role Evidence"
    if gate == 2:
        return "Role Scoring"
    return "General Assessment"


def _option_signal_roles(question: dict) -> list[str]:
    options = question.get("options") or {}
    if isinstance(options, dict):
        option_values = options.values()
    elif isinstance(options, list):
        option_values = options
    else:
        option_values = []

    roles: list[str] = []
    for option in option_values:
        if not isinstance(option, dict):
            continue
        for signal in (option.get("signals") or {}).keys():
            signal_text = str(signal)
            if signal_text.upper() not in DOMAIN_SIGNAL_KEYS:
                roles.append(signal_text)
    return roles


def _question_roles(question: dict) -> list[str]:
    scoring = question.get("scoring") or {}
    category_weights = scoring.get("category_weights") or {}
    evidence_categories = [
        evidence.get("category")
        for evidence in question.get("job_evidence") or []
        if str(evidence.get("category") or "").lower() != "all"
    ]

    return _unique(
        list(question.get("role_targets") or [])
        + list(category_weights.keys())
        + _option_signal_roles(question)
        + evidence_categories
    )


def _question_job_titles(question: dict) -> list[str]:
    titles: list[str] = []
    for evidence in question.get("job_evidence") or []:
        for title in _as_list(evidence.get("job_titles")):
            title_text = str(title).strip()
            if title_text and title_text.lower() != "all":
                titles.append(title_text)
    return _unique(titles)


def _validate_role_categories(roles_in_questions: set[str]) -> None:
    memberships: dict[str, list[str]] = {}
    for category, roles in CATEGORY_TO_ROLES.items():
        for role in roles:
            memberships.setdefault(role, []).append(category)

    duplicates = {role: cats for role, cats in memberships.items() if len(cats) > 1}
    if duplicates:
        raise SystemExit(f"Roles assigned to multiple categories: {duplicates}")

    missing = sorted(role for role in roles_in_questions if role not in ROLE_TO_CATEGORY)
    if missing:
        raise SystemExit(f"Roles missing from CATEGORY_TO_ROLES: {missing}")

    unused = sorted(role for role in ROLE_TO_CATEGORY if role not in roles_in_questions)
    if unused:
        raise SystemExit(f"Category roles not referenced by questions: {unused}")


def build_mapping() -> dict:
    question_parts = sorted(DATA_DIR.glob("questions_part*.json"))
    entries: list[dict] = []
    roles_in_questions: set[str] = set()

    for index, path in enumerate(question_parts, start=1):
        with path.open(encoding="utf-8") as handle:
            questions = _normalise_questions(json.load(handle))

        for question in questions:
            canonical_roles = _question_roles(question)
            roles_in_questions.update(canonical_roles)

            unknown = sorted(role for role in canonical_roles if role not in ROLE_TO_CATEGORY)
            if unknown:
                raise SystemExit(
                    f"{path.name}:{question.get('id')} references uncategorized roles: {unknown}"
                )

            category_keys = _unique(ROLE_TO_CATEGORY[role] for role in canonical_roles)
            job_titles = _question_job_titles(question)
            display_roles = job_titles or [_role_label(role) for role in canonical_roles]

            entries.append(
                {
                    "question_id": question.get("id") or question.get("question_id"),
                    "question": question.get("stem")
                    or question.get("question")
                    or question.get("question_text"),
                    "part": f"Part {index}",
                    "source_file": path.name,
                    "assessment_stage": _stage_for_question(question),
                    "canonical_roles": canonical_roles,
                    "roles": display_roles,
                    "categories": [CATEGORY_LABELS.get(key, key) for key in category_keys],
                }
            )

    _validate_role_categories(roles_in_questions)

    categories = [
        {
            "category": CATEGORY_LABELS.get(category, category),
            "category_key": category,
            "roles": [
                {
                    "role_key": role,
                    "role": _role_label(role),
                }
                for role in roles
            ],
        }
        for category, roles in CATEGORY_TO_ROLES.items()
    ]

    return {
        "source_files": [path.name for path in question_parts],
        "question_count": len(entries),
        "category_count": len(categories),
        "role_count": sum(len(item["roles"]) for item in categories),
        "categories": categories,
        "questions": entries,
    }


def write_category_doc(mapping: dict) -> None:
    lines = [
        "# Category -> Roles",
        "",
        "Generated from `data/questions_part1.json` through `data/questions_part5.json`.",
        f"Complete question mapping: `{QUESTION_MAPPING_PATH.relative_to(BASE_DIR).as_posix()}`",
        "",
    ]

    for category in mapping["categories"]:
        lines.append(category["category"])
        for role in category["roles"]:
            lines.append(f"- {role['role']} (`{role['role_key']}`)")
        lines.append("")

    lines.extend(
        [
            "## Questions -> Roles Mapping",
            "",
            f"The complete table contains {mapping['question_count']:,} entries in "
            f"`{QUESTION_MAPPING_PATH.relative_to(BASE_DIR).as_posix()}`.",
            "Each entry includes `question_id`, `question`, `part`, "
            "`assessment_stage`, `roles`, `canonical_roles`, and `categories`.",
            "",
            "Sample:",
            "",
        ]
    )

    for entry in mapping["questions"][:5]:
        lines.append(f"Question ID: {entry['question_id']}")
        lines.append(f"Question: {entry['question']}")
        lines.append(f"Part: {entry['part']} - {entry['assessment_stage']}")
        lines.append("Roles:")
        for role in entry["roles"]:
            lines.append(f"- {role}")
        lines.append("Category:")
        for category in entry["categories"]:
            lines.append(f"- {category}")
        lines.append("")

    CATEGORY_DOC_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    mapping = build_mapping()
    QUESTION_MAPPING_PATH.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    write_category_doc(mapping)
    print(
        f"Wrote {mapping['question_count']} question mappings, "
        f"{mapping['role_count']} roles, {mapping['category_count']} categories."
    )


if __name__ == "__main__":
    main()
