"""Validate role coverage and adaptive quiz behavior."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.answer_evaluator import evaluate_mcq
from app.quiz_engine import (
    CATEGORY_TO_ROLES,
    TARGET_TECHNICAL_QUESTIONS,
    QuizEngine,
)


def _simulate(engine: QuizEngine, role: str, score: float) -> dict:
    session = engine.create_session()
    session_id = session["session_id"]
    domain_question = engine.get_question(session["first_question_id"])
    result = engine.submit_answer(
        session_id,
        domain_question["id"],
        "A",
        "A",
        evaluate_mcq(domain_question, "A"),
    )
    role_question = engine.get_question(result["next_question"]["id"])
    if role not in role_question.get("options", {}):
        raise ValueError(f"Role {role} is not available for the selected domain")
    result = engine.submit_answer(
        session_id,
        role_question["id"],
        role,
        role,
        evaluate_mcq(role_question, role),
    )

    difficulties = []
    while result["status"] == "continue":
        question = result["next_question"]
        difficulties.append(question["difficulty"])
        result = engine.submit_answer(
            session_id,
            question["id"],
            "Validation answer with evidence, tradeoffs, and a clear outcome.",
            None,
            {
                "score": score,
                "feedback": "Validation evaluation",
                "skill_scores": {},
                "category_score_deltas": {role: 5},
                "confidence": 0.9,
                "follow_up_question": None,
            },
        )

    return {
        "technical_questions": len(difficulties),
        "difficulty_sequence": difficulties,
        "profile": result["profile"],
    }


def main() -> int:
    engine = QuizEngine()
    roles = sorted({role for roles in CATEGORY_TO_ROLES.values() for role in roles})
    coverage = {
        role: engine.get_role_difficulty_counts(role)
        for role in roles
    }
    missing = {
        role: counts
        for role, counts in coverage.items()
        if any(counts[level] == 0 for level in ("beginner", "intermediate", "advanced"))
    }

    strong = _simulate(engine, "frontend-dev", 0.9)
    weak = _simulate(engine, "frontend-dev", 0.2)
    report = {
        "roles_checked": len(roles),
        "roles_missing_difficulty_coverage": missing,
        "target_technical_questions": TARGET_TECHNICAL_QUESTIONS,
        "strong_simulation": strong,
        "weak_simulation": weak,
    }
    print(json.dumps(report, indent=2))

    strong_sequence = strong["difficulty_sequence"]
    errors = bool(
        missing
        or strong["technical_questions"] != TARGET_TECHNICAL_QUESTIONS
        or weak["technical_questions"] != TARGET_TECHNICAL_QUESTIONS
        or "advanced" not in strong_sequence
        or any(level != "beginner" for level in weak["difficulty_sequence"])
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
