import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.answer_evaluator import evaluate_mcq
from app.quiz_engine import (
    CATEGORY_TO_ROLES,
    DB_PATH,
    TARGET_TECHNICAL_QUESTIONS,
    QuizEngine,
)


pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(),
    reason="SQLite quiz bank is required for adaptive routing tests",
)


def _start_role(engine: QuizEngine, role: str = "frontend-dev"):
    session = engine.create_session()
    session_id = session["session_id"]

    domain_question = engine.get_question(session["first_question_id"])
    domain_answer = "A"
    result = engine.submit_answer(
        session_id,
        domain_question["id"],
        domain_answer,
        domain_answer,
        evaluate_mcq(domain_question, domain_answer),
    )

    role_question = engine.get_question(result["next_question"]["id"])
    assert role in role_question["options"]
    result = engine.submit_answer(
        session_id,
        role_question["id"],
        role,
        role,
        evaluate_mcq(role_question, role),
    )
    return session_id, result


def _submit_scored_answer(
    engine: QuizEngine,
    session_id: str,
    question: dict,
    score: float,
):
    return engine.submit_answer(
        session_id,
        question["id"],
        "A structured interview answer with a concrete example and validation.",
        None,
        {
            "score": score,
            "feedback": "Test evaluation",
            "skill_scores": {},
            "category_score_deltas": {"frontend-dev": 5},
            "confidence": 0.9,
            "follow_up_question": None,
        },
    )


def test_every_role_has_beginner_intermediate_and_advanced_questions():
    engine = QuizEngine()

    for role in sorted({role for roles in CATEGORY_TO_ROLES.values() for role in roles}):
        counts = engine.get_role_difficulty_counts(role)
        assert counts["beginner"] > 0, f"{role} has no beginner questions"
        assert counts["intermediate"] > 0, f"{role} has no intermediate questions"
        assert counts["advanced"] > 0, f"{role} has no advanced questions"


def test_strong_answers_progress_to_advanced_questions():
    engine = QuizEngine()
    session_id, result = _start_role(engine)
    difficulties = []

    for _ in range(4):
        question = result["next_question"]
        difficulties.append(question["difficulty"])
        result = _submit_scored_answer(engine, session_id, question, 0.9)

    assert difficulties == [
        "beginner",
        "beginner",
        "intermediate",
        "advanced",
    ]


def test_weak_answers_remain_beginner_friendly():
    engine = QuizEngine()
    session_id, result = _start_role(engine)
    difficulties = []

    for _ in range(4):
        question = result["next_question"]
        difficulties.append(question["difficulty"])
        result = _submit_scored_answer(engine, session_id, question, 0.2)

    assert difficulties == ["beginner", "beginner", "beginner", "beginner"]


def test_quiz_stops_after_target_technical_questions_and_reports_metrics():
    engine = QuizEngine()
    session_id, result = _start_role(engine)
    technical_questions = 0

    while result["status"] == "continue":
        question = result["next_question"]
        result = _submit_scored_answer(engine, session_id, question, 0.9)
        technical_questions += 1

    profile = result["profile"]
    assert technical_questions == TARGET_TECHNICAL_QUESTIONS
    assert profile["question_count"] == TARGET_TECHNICAL_QUESTIONS + 2
    assert profile["difficulty_reached"] == "advanced"
    assert profile["difficulty_counts"]["advanced"] >= 2
    assert profile["skill_level"] == "senior"
    assert profile["confidence"] >= 80


def test_broad_role_is_capped_instead_of_using_entire_question_bank():
    engine = QuizEngine()
    session_id, result = _start_role(engine, role="tech")
    technical_questions = 0

    while result["status"] == "continue":
        question = result["next_question"]
        result = _submit_scored_answer(engine, session_id, question, 0.6)
        technical_questions += 1

    assert technical_questions == TARGET_TECHNICAL_QUESTIONS
    assert result["profile"]["question_count"] <= 12
