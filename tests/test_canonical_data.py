import os
import sys
from itertools import islice

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.canonical import (
    build_data_folder_report,
    iter_quiz_questions_from_json,
    load_job_skill_links_from_sqlite,
    load_jobs_from_csv,
    load_learning_resources,
    load_skills,
    profile_from_manual_input,
    profile_from_quiz_result,
    validate_job,
    validate_learning_resource,
    validate_profile,
    validate_skill,
)


def test_skills_taxonomy_loads_as_canonical_skills():
    skills = load_skills()

    assert skills
    assert all(not validate_skill(skill) for skill in skills[:20])
    assert any(skill.skill_id == "lang-py" for skill in skills)


def test_learning_resources_load_as_canonical_resources():
    resources = load_learning_resources()
    taxonomy_ids = {skill.skill_id for skill in load_skills()}

    assert resources
    assert all(not validate_learning_resource(resource) for resource in resources[:20])
    assert all(resource.skill_id for resource in resources[:20])
    assert all(resource.skill_id in taxonomy_ids for resource in resources)


def test_jobs_csv_and_db_skill_links_load_as_canonical_jobs():
    links = load_job_skill_links_from_sqlite()
    jobs = load_jobs_from_csv(skill_links=links, limit=10)

    assert links
    assert jobs
    assert all(not validate_job(job) for job in jobs)
    assert jobs[0].job_id.startswith("job-")


def test_quiz_question_parts_load_as_canonical_questions():
    questions = list(islice(iter_quiz_questions_from_json(limit=5), 5))

    assert questions
    assert questions[0].question_id
    assert questions[0].stem
    assert questions[0].difficulty


def test_manual_and_quiz_profiles_share_canonical_shape():
    manual = profile_from_manual_input(
        ["Python", "SQL", "React"],
        experience_level="junior",
        target_role="backend-dev",
    )
    quiz = profile_from_quiz_result(
        {
            "session_id": "test-session",
            "detected_domain": "SOFTWARE",
            "detected_role": "backend-dev",
            "detected_skills": ["lang-py"],
            "skill_scores": {"lang-py": 0.8},
            "overall_score": 0.8,
            "confidence": 80,
            "experience_level": "junior",
        }
    )

    assert manual.source == "manual"
    assert quiz.source == "quiz"
    assert "lang-py" in manual.skill_ids
    assert "lang-py" in quiz.skill_ids
    assert not validate_profile(manual)
    assert not validate_profile(quiz)


def test_data_folder_report_uses_current_project_data():
    report = build_data_folder_report(sample_job_limit=5, sample_question_limit=5)

    assert report["skills"] > 0
    assert report["learning_resources"] > 0
    assert report["job_rows"] > 0
    assert report["job_skill_links"] > 0
    assert report["sample_questions_validated"] > 0
