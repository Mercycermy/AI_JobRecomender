import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.answer_evaluator import evaluate, evaluate_mcq
from app.quiz_engine import CATEGORY_TO_ROLES, DB_PATH, ROLE_TO_CATEGORY, TARGET_QUESTIONS, QuizEngine


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


def _dynamic_role_options(engine, domain):
    session = engine.create_session()
    conn = engine._conn()
    try:
        conn.execute(
            "UPDATE quiz_sessions SET detected_domain=? WHERE id=?",
            (domain, session["session_id"]),
        )
        conn.commit()
    finally:
        conn.close()

    question = engine.get_question(f"Q_G0_ROLE_SELECT:{session['session_id']}")
    return question["stem"], set(question["options"]) - {"other"}


def test_category_to_roles_covers_active_quiz_roles_once():
    engine = QuizEngine()
    db_roles = set(engine.get_all_roles_in_db())
    categorized_roles = [
        role
        for roles in CATEGORY_TO_ROLES.values()
        for role in roles
    ]

    assert set(categorized_roles) == db_roles
    assert len(categorized_roles) == len(set(categorized_roles))
    assert ROLE_TO_CATEGORY["data-analyst"] == "DATA_AI"
    assert ROLE_TO_CATEGORY["finance"] == "ACCOUNTING"


def test_dynamic_role_selector_uses_domain_specific_roles():
    engine = QuizEngine()

    software_stem, software_roles = _dynamic_role_options(engine, "SOFTWARE")
    data_stem, data_roles = _dynamic_role_options(engine, "DATA_AI")
    creative_stem, creative_roles = _dynamic_role_options(engine, "CREATIVE")
    finance_stem, finance_roles = _dynamic_role_options(engine, "FINANCE")

    assert "Technology & Software Development" in software_stem
    assert {"frontend-dev", "backend-dev", "fullstack-dev", "mobile-dev", "devops", "tech"} <= software_roles
    assert "data-analyst" not in software_roles

    assert "Data & Artificial Intelligence" in data_stem
    assert {"data-analyst", "data-scientist", "ml-engineer"} <= data_roles
    assert not {"frontend-dev", "backend-dev"} & data_roles

    assert "Design & Creative Media" in creative_stem
    assert {"graphic-designer", "ui-ux-designer", "video-editor", "creative"} <= creative_roles
    assert not {"frontend-dev", "backend-dev", "data-analyst"} & creative_roles

    assert "Accounting, Finance & Banking" in finance_stem
    assert {"accounting", "finance"} <= finance_roles


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

    # For frontend-dev, total active questions is 3, plus 2 selection questions = 5
    expected_total = 5
    assert answered == expected_total
    assert profile["question_count"] == expected_total
    assert profile["detected_domain"] == "SOFTWARE"
    assert profile["top_category"] == "frontend-dev"
    assert profile["detected_skills"]
