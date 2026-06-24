"""Canonical data models and adapters for the AI Job Recommender.

This module is the implementation of step 2 in the project roadmap.  It gives
the app one shared vocabulary for skills, profiles, jobs, resources, resumes,
Telegram jobs, and quiz content while adapting the current files in ``data/``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from app.skill_normalizer import SkillNormalizer


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TAXONOMY_PATH = DATA_DIR / "skills_taxonomy.json"
JOBS_CSV_PATH = DATA_DIR / "jobs.csv"
RECOMMENDER_DB_PATH = DATA_DIR / "db.sqlite3"
QUIZ_DB_PATH = DATA_DIR / "jobs.db"
LEARNING_RESOURCES_PATH = DATA_DIR / "learning_resources.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or fallback


def stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{slugify(prefix)}-{digest}"


def canonical_job_id(raw_job_id: Any, source: str = "job") -> str:
    raw = str(raw_job_id or "").strip()
    if not raw:
        return stable_id(source, "missing")
    if raw.lower().startswith("job-"):
        return slugify(raw)
    return f"job-{slugify(raw)}"


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        return [part.strip() for part in re.split(r"[,;|]", text) if part.strip()]
    return [str(value).strip()]


def _json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return default
    return default


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "free"}


@dataclass
class CanonicalSkill:
    skill_id: str
    skill_name: str
    aliases: List[str] = field(default_factory=list)
    category: str = ""
    level: Optional[str] = None
    related_roles: List[str] = field(default_factory=list)
    description: Optional[str] = None
    parent_skill_id: Optional[str] = None
    is_active: bool = True
    domain: Optional[str] = None
    weight: float = 1.0


@dataclass
class CanonicalProfile:
    profile_id: str
    user_id: Optional[str]
    source: str
    detected_domain: Optional[str] = None
    detected_role: Optional[str] = None
    target_role: Optional[str] = None
    experience_level: str = "junior"
    location: str = "remote"
    skill_ids: List[str] = field(default_factory=list)
    skill_scores: Dict[str, float] = field(default_factory=dict)
    category_scores: Dict[str, float] = field(default_factory=dict)
    domain_scores: Dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    confidence: float = 0.0
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass
class CanonicalQuizQuestion:
    question_id: str
    gate: int
    difficulty: str
    domain_scope: str
    role_targets: List[str]
    question_type: str
    answer_mode: str
    stem: str
    context: Optional[str] = None
    options: Optional[Any] = None
    scoring: Dict[str, Any] = field(default_factory=dict)
    ai_prompt: Optional[str] = None
    job_evidence: List[Dict[str, Any]] = field(default_factory=list)
    route_strong: Optional[str] = None
    route_partial: Optional[str] = None
    route_weak: Optional[str] = None
    estimated_minutes: Optional[int] = None
    is_active: bool = True


@dataclass
class CanonicalJob:
    job_id: str
    source: str
    source_ref: Optional[str]
    title: str
    company: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    seniority: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None
    raw_text: Optional[str] = None
    required_skills: List[str] = field(default_factory=list)
    optional_skills: List[str] = field(default_factory=list)
    posted_at: Optional[str] = None
    url: Optional[str] = None
    status: str = "active"


@dataclass
class CanonicalJobSkillLink:
    job_id: str
    skill_id: str
    required: bool = True
    weight: float = 1.0
    source: str = "data/db.sqlite3"


@dataclass
class CanonicalLearningResource:
    resource_id: str
    skill_id: str
    title: str
    platform: Optional[str] = None
    url: Optional[str] = None
    difficulty: Optional[str] = None
    estimated_hours: Optional[float] = None
    is_free: bool = False
    covers: List[str] = field(default_factory=list)
    best_for: List[str] = field(default_factory=list)
    gap_priority: Optional[str] = None
    description: Optional[str] = None


@dataclass
class CanonicalResumeRecord:
    resume_id: str
    user_id: Optional[str]
    source_file: Optional[str]
    file_type: Optional[str]
    extracted_text: str = ""
    parsed_sections: Dict[str, Any] = field(default_factory=dict)
    matched_skills: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)
    generated_files: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class CanonicalTelegramPost:
    telegram_post_id: str
    channel_name: str
    message_id: str
    raw_text: str
    extracted_job_id: Optional[str] = None
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    posted_at: Optional[str] = None
    processed_at: Optional[str] = None


@dataclass
class RecommendationResult:
    job_id: str
    match_score: float
    breakdown: Dict[str, float] = field(default_factory=dict)
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    explanation: Optional[str] = None


@dataclass
class GapResult:
    skill_id: str
    skill_name: str
    current: int
    required: int
    priority: int
    priority_label: str


@dataclass
class ResumeCoachingResult:
    summary: Optional[str] = None
    tips: List[Dict[str, Any]] = field(default_factory=list)
    schedule: List[Dict[str, Any]] = field(default_factory=list)
    resource_explanations: Dict[str, str] = field(default_factory=dict)


def to_dict(item: Any) -> Dict[str, Any]:
    return asdict(item)


def validate_required(item: Dict[str, Any], required_fields: Iterable[str]) -> List[str]:
    errors = []
    for field_name in required_fields:
        value = item.get(field_name)
        if value is None or value == "" or value == []:
            errors.append(f"missing {field_name}")
    return errors


def validate_skill(skill: CanonicalSkill) -> List[str]:
    data = to_dict(skill)
    errors = validate_required(data, ["skill_id", "skill_name"])
    if skill.skill_id != slugify(skill.skill_id):
        errors.append("skill_id must be lowercase kebab-case")
    return errors


def validate_profile(profile: CanonicalProfile) -> List[str]:
    data = to_dict(profile)
    errors = validate_required(data, ["profile_id", "source", "experience_level"])
    for skill_id in profile.skill_ids:
        if skill_id != slugify(skill_id):
            errors.append(f"invalid skill_id: {skill_id}")
    for skill_id, score in profile.skill_scores.items():
        if score < 0 or score > 1:
            errors.append(f"skill score must be 0-1: {skill_id}")
    return errors


def validate_job(job: CanonicalJob) -> List[str]:
    data = to_dict(job)
    errors = validate_required(data, ["job_id", "source", "title"])
    if not job.description and not job.raw_text:
        errors.append("job should keep description or raw_text")
    return errors


def validate_quiz_question(question: CanonicalQuizQuestion) -> List[str]:
    data = to_dict(question)
    errors = validate_required(
        data,
        ["question_id", "difficulty", "domain_scope", "question_type", "answer_mode", "stem"],
    )
    if question.gate < 0:
        errors.append("gate must be non-negative")
    if question.answer_mode == "single_choice" and not question.options:
        errors.append("single_choice questions should include options")
    return errors


def validate_learning_resource(resource: CanonicalLearningResource) -> List[str]:
    data = to_dict(resource)
    return validate_required(data, ["resource_id", "skill_id", "title"])


def skill_from_taxonomy(item: Dict[str, Any]) -> CanonicalSkill:
    return CanonicalSkill(
        skill_id=slugify(item.get("skill_id")),
        skill_name=str(item.get("skill_name") or item.get("canonical_name") or "").strip(),
        aliases=_as_list(item.get("aliases")),
        category=str(item.get("category") or item.get("domain") or "").strip(),
        level=item.get("level"),
        related_roles=_as_list(item.get("related_roles") or item.get("differentiation_tags")),
        description=item.get("description"),
        parent_skill_id=item.get("parent_skill_id"),
        is_active=_boolish(item.get("is_active", True)),
        domain=item.get("domain"),
        weight=float(item.get("weight") or 1.0),
    )


def load_skills(path: Path | str = TAXONOMY_PATH) -> List[CanonicalSkill]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [skill_from_taxonomy(item) for item in payload.get("skills", [])]


def learning_resource_from_json(
    item: Dict[str, Any],
    normalizer: Optional[SkillNormalizer] = None,
) -> CanonicalLearningResource:
    normalizer = normalizer or SkillNormalizer()
    alignment = item.get("job_gap_alignment") or {}
    raw_skill_id = item.get("skill_id")
    skill_id = normalizer.to_skill_id(str(raw_skill_id)) or slugify(raw_skill_id)
    return CanonicalLearningResource(
        resource_id=str(item.get("resource_id") or stable_id("resource", item.get("title"))),
        skill_id=skill_id,
        title=str(item.get("title") or "").strip(),
        platform=item.get("platform"),
        url=item.get("url"),
        difficulty=item.get("difficulty"),
        estimated_hours=item.get("estimated_hours"),
        is_free=_boolish(item.get("is_free")),
        covers=_as_list(item.get("covers")),
        best_for=_as_list(item.get("best_for")),
        gap_priority=alignment.get("gap_priority"),
        description=item.get("description") or item.get("notes") or alignment.get("why_this_resource"),
    )


def load_learning_resources(path: Path | str = LEARNING_RESOURCES_PATH) -> List[CanonicalLearningResource]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    normalizer = SkillNormalizer()
    return [
        learning_resource_from_json(item, normalizer)
        for item in payload.get("resources", [])
    ]


def load_job_skill_links_from_sqlite(
    db_path: Path | str = RECOMMENDER_DB_PATH,
    normalizer: Optional[SkillNormalizer] = None,
) -> List[CanonicalJobSkillLink]:
    if not Path(db_path).exists():
        return []

    normalizer = normalizer or SkillNormalizer()
    links: List[CanonicalJobSkillLink] = []
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT job_id, skill_id, is_required FROM job_skills").fetchall()
    finally:
        conn.close()

    for job_id, raw_skill_id, is_required in rows:
        skill_id = normalizer.to_skill_id(str(raw_skill_id)) or slugify(raw_skill_id)
        required = _boolish(is_required)
        links.append(
            CanonicalJobSkillLink(
                job_id=canonical_job_id(job_id),
                skill_id=skill_id,
                required=required,
                weight=1.0 if required else 0.5,
                source="data/db.sqlite3",
            )
        )
    return links


def _job_skill_map(
    links: Optional[Iterable[CanonicalJobSkillLink]],
) -> Dict[str, Dict[str, List[str]]]:
    mapping: Dict[str, Dict[str, List[str]]] = {}
    for link in links or []:
        bucket = mapping.setdefault(link.job_id, {"required": [], "optional": []})
        key = "required" if link.required else "optional"
        if link.skill_id not in bucket[key]:
            bucket[key].append(link.skill_id)
    return mapping


def job_from_csv_row(
    row: Dict[str, Any],
    skill_map: Optional[Dict[str, Dict[str, List[str]]]] = None,
) -> CanonicalJob:
    job_id = canonical_job_id(row.get("job_id"))
    skills = (skill_map or {}).get(job_id, {"required": [], "optional": []})
    source = str(row.get("source") or "data/jobs.csv").strip()
    raw_title = str(row.get("job_title") or row.get("title") or "").strip()
    title = raw_title or "Untitled Job"
    status = "active" if raw_title else "incomplete"
    return CanonicalJob(
        job_id=job_id,
        source=source,
        source_ref=str(row.get("job_id") or "").strip() or None,
        title=title,
        company=row.get("company"),
        role=slugify(row.get("role") or raw_title or ""),
        category=row.get("category"),
        seniority=row.get("exp_level") or row.get("seniority"),
        location=row.get("location"),
        salary=row.get("salary"),
        description=row.get("description"),
        raw_text=row.get("description"),
        required_skills=skills.get("required", []),
        optional_skills=skills.get("optional", []),
        posted_at=row.get("date_added") or row.get("posted_at"),
        url=row.get("url") or row.get("apply_link"),
        status=status,
    )


def iter_jobs_from_csv(
    csv_path: Path | str = JOBS_CSV_PATH,
    skill_links: Optional[Iterable[CanonicalJobSkillLink]] = None,
    limit: Optional[int] = None,
) -> Iterator[CanonicalJob]:
    skill_map = _job_skill_map(skill_links)
    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            if limit is not None and index >= limit:
                break
            yield job_from_csv_row(row, skill_map)


def load_jobs_from_csv(
    csv_path: Path | str = JOBS_CSV_PATH,
    skill_links: Optional[Iterable[CanonicalJobSkillLink]] = None,
    limit: Optional[int] = None,
) -> List[CanonicalJob]:
    return list(iter_jobs_from_csv(csv_path, skill_links=skill_links, limit=limit))


def quiz_question_from_payload(item: Dict[str, Any]) -> CanonicalQuizQuestion:
    routing = item.get("routing") or {}
    return CanonicalQuizQuestion(
        question_id=str(item.get("question_id") or item.get("id") or "").strip(),
        gate=int(item.get("gate") or 0),
        difficulty=str(item.get("difficulty") or "beginner"),
        domain_scope=str(item.get("domain_scope") or "ALL"),
        role_targets=_as_list(item.get("role_targets")),
        question_type=str(item.get("question_type") or "multiple_choice"),
        answer_mode=str(item.get("answer_mode") or "single_choice"),
        stem=str(item.get("stem") or item.get("text") or "").strip(),
        context=item.get("context"),
        options=_json_value(item.get("options"), item.get("options")),
        scoring=_json_value(item.get("scoring"), {}),
        ai_prompt=item.get("ai_prompt") or item.get("ai_evaluation_prompt"),
        job_evidence=_json_value(item.get("job_evidence"), []),
        route_strong=item.get("route_strong") or routing.get("strong"),
        route_partial=item.get("route_partial") or routing.get("partial"),
        route_weak=item.get("route_weak") or routing.get("weak"),
        estimated_minutes=item.get("estimated_minutes"),
        is_active=_boolish(item.get("is_active", True)),
    )


def iter_quiz_questions_from_json(
    data_dir: Path | str = DATA_DIR,
    include_role_interviews: bool = True,
    limit: Optional[int] = None,
) -> Iterator[CanonicalQuizQuestion]:
    paths = sorted(Path(data_dir).glob("questions_part*.json"))
    if include_role_interviews:
        role_path = Path(data_dir) / "questions_role_interviews.json"
        if role_path.exists():
            paths.append(role_path)

    seen: set[str] = set()
    emitted = 0
    for path in paths:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        questions = payload.get("questions", payload if isinstance(payload, list) else [])
        for item in questions:
            question = quiz_question_from_payload(item)
            if not question.question_id or question.question_id in seen:
                continue
            seen.add(question.question_id)
            yield question
            emitted += 1
            if limit is not None and emitted >= limit:
                return


def profile_from_manual_input(
    skills: Iterable[str],
    experience_level: str = "junior",
    target_role: Optional[str] = None,
    location: str = "remote",
    user_id: Optional[str] = None,
    normalizer: Optional[SkillNormalizer] = None,
) -> CanonicalProfile:
    normalizer = normalizer or SkillNormalizer()
    skill_ids = normalizer.normalize_list(skills)
    skill_scores = {skill_id: 1.0 for skill_id in skill_ids}
    overall = 1.0 if skill_scores else 0.0
    return CanonicalProfile(
        profile_id=stable_id("profile", "manual", user_id, ",".join(skill_ids), target_role, location),
        user_id=user_id,
        source="manual",
        detected_domain=None,
        detected_role=target_role,
        target_role=target_role,
        experience_level=experience_level or "junior",
        location=location or "remote",
        skill_ids=skill_ids,
        skill_scores=skill_scores,
        overall_score=overall,
        confidence=0.7 if skill_ids else 0.0,
    )


def profile_from_quiz_result(
    result: Dict[str, Any],
    user_id: Optional[str] = None,
    normalizer: Optional[SkillNormalizer] = None,
) -> CanonicalProfile:
    normalizer = normalizer or SkillNormalizer()
    raw_scores = result.get("skill_scores") or {}
    skill_scores: Dict[str, float] = {}
    for skill_id, score in raw_scores.items():
        values = score if isinstance(score, list) else [score]
        numeric = [float(value) for value in values if isinstance(value, (int, float))]
        if numeric:
            resolved = normalizer.to_skill_id(str(skill_id)) or slugify(skill_id)
            skill_scores[resolved] = round(sum(numeric) / len(numeric), 3)

    skill_ids = normalizer.normalize_list(result.get("detected_skills", []))
    for skill_id in skill_scores:
        if skill_id not in skill_ids:
            skill_ids.append(skill_id)

    overall = result.get("overall_score")
    if overall is None:
        overall = round(sum(skill_scores.values()) / len(skill_scores), 3) if skill_scores else 0.0

    confidence = result.get("confidence", overall)
    if confidence and confidence > 1:
        confidence = round(float(confidence) / 100, 3)

    return CanonicalProfile(
        profile_id=stable_id("profile", "quiz", user_id, result.get("session_id"), ",".join(skill_ids)),
        user_id=user_id,
        source="quiz",
        detected_domain=result.get("detected_domain"),
        detected_role=result.get("detected_role"),
        target_role=result.get("target_role") or result.get("top_category"),
        experience_level=result.get("experience_level") or result.get("skill_level") or "junior",
        location=result.get("location") or "remote",
        skill_ids=skill_ids,
        skill_scores=skill_scores,
        category_scores={str(k): float(v) for k, v in (result.get("category_scores") or {}).items()},
        domain_scores={str(k): float(v) for k, v in (result.get("domain_scores") or {}).items()},
        overall_score=float(overall or 0.0),
        confidence=float(confidence or 0.0),
    )


def count_csv_rows(csv_path: Path | str = JOBS_CSV_PATH) -> int:
    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def build_data_folder_report(sample_job_limit: int = 25, sample_question_limit: int = 25) -> Dict[str, Any]:
    skills = load_skills()
    resources = load_learning_resources()
    links = load_job_skill_links_from_sqlite()
    sample_jobs = load_jobs_from_csv(skill_links=links, limit=sample_job_limit)
    sample_questions = list(iter_quiz_questions_from_json(limit=sample_question_limit))

    skill_errors = sum(1 for skill in skills if validate_skill(skill))
    resource_errors = sum(1 for resource in resources if validate_learning_resource(resource))
    job_errors = sum(1 for job in sample_jobs if validate_job(job))

    return {
        "data_dir": str(DATA_DIR),
        "skills": len(skills),
        "skill_validation_errors": skill_errors,
        "learning_resources": len(resources),
        "learning_resource_validation_errors": resource_errors,
        "job_rows": count_csv_rows(),
        "job_skill_links": len(links),
        "sample_jobs_validated": len(sample_jobs),
        "sample_job_validation_errors": job_errors,
        "sample_questions_validated": len(sample_questions),
        "sample_question_ids": [question.question_id for question in sample_questions[:5]],
    }


def build_full_data_folder_report() -> Dict[str, Any]:
    """Validate every current data-folder record that can be streamed safely."""
    skills = load_skills()
    resources = load_learning_resources()
    links = load_job_skill_links_from_sqlite()

    skill_errors = sum(1 for skill in skills if validate_skill(skill))
    resource_errors = sum(1 for resource in resources if validate_learning_resource(resource))

    job_count = 0
    job_errors = 0
    first_job_errors: List[Dict[str, Any]] = []
    for job in iter_jobs_from_csv(skill_links=links):
        job_count += 1
        errors = validate_job(job)
        if errors:
            job_errors += 1
            if len(first_job_errors) < 5:
                first_job_errors.append({"job_id": job.job_id, "errors": errors})

    question_count = 0
    question_errors = 0
    first_question_errors: List[Dict[str, Any]] = []
    for question in iter_quiz_questions_from_json():
        question_count += 1
        errors = validate_quiz_question(question)
        if errors:
            question_errors += 1
            if len(first_question_errors) < 5:
                first_question_errors.append(
                    {"question_id": question.question_id, "errors": errors}
                )

    return {
        "data_dir": str(DATA_DIR),
        "skills": len(skills),
        "skill_validation_errors": skill_errors,
        "learning_resources": len(resources),
        "learning_resource_validation_errors": resource_errors,
        "jobs_validated": job_count,
        "job_validation_errors": job_errors,
        "first_job_errors": first_job_errors,
        "job_skill_links": len(links),
        "quiz_questions_validated": question_count,
        "quiz_question_validation_errors": question_errors,
        "first_question_errors": first_question_errors,
    }
