import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.answer_evaluator import evaluate, evaluate_mcq
from app.quiz_engine import DB_PATH, TARGET_QUESTIONS, QuizEngine


pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(),
    reason="SQLite quiz bank is required for the adaptive flow regression test",
)


def _answer_question(engine, session_id, question_id):
    question = engine.get_question(question_id)
    assert question is not None

    if question.get("answer_mode") == "single_choice" and question.get("options"):
        if question_id == "Q_G0_CATEGORY":
            answer = "A"
        elif question_id == "Q_G0_ROLE_TECH":
            answer = "frontend-dev"
        else:
            answer = next(iter(question["options"].keys()))
        return engine.submit_answer(
            session_id,
            question_id,
            answer,
            answer,
            evaluate_mcq(question, answer),
        )

    answer = (
        "I would diagnose the issue, describe the tradeoffs, implement a clean "
        "solution, validate it, and communicate the outcome clearly."
    )
    eval_res = evaluate(question, answer)
    # Ensure frontend-dev accumulates category scores to remain the top category
    eval_res["category_score_deltas"] = {"frontend-dev": 5}
    return engine.submit_answer(
        session_id,
        question_id,
        answer,
        None,
        eval_res,
    )


def test_quiz_engine_reaches_target_questions_and_builds_profile(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("AI_JOB_RECOMMENDER_SKIP_DOTENV", "1")

    engine = QuizEngine()
    session = engine.create_session()
    question_id = session["first_question_id"]
    answered = 0

    while question_id:
        result = _answer_question(engine, session["session_id"], question_id)
        answered += 1

        if result["status"] == "done":
            profile = result["profile"]
            break

        question_id = result["next_question"]["id"]
    else:
        pytest.fail("Quiz ended without returning a completed profile")

    assert answered == TARGET_QUESTIONS
    assert profile["question_count"] == TARGET_QUESTIONS
    assert profile["detected_domain"] == "SOFTWARE"
    assert profile["top_category"] == "frontend-dev"
    assert profile["detected_skills"]
