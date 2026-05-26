"""
Flask API — adaptive quiz and semantic job recommendations.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request

from app.agent import AssessmentAgent, AgentState
from app.answer_evaluator import evaluate, evaluate_mcq
from app.gap_analyzer import GapAnalyzer
from app.learning_path import LearningPath
from app.quiz_engine import QuizEngine
from app.recommender import RecommendationEngine
from app.resume_tips import ResumeCoach
from app.skill_normalizer import SkillNormalizer

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

_agent: Optional[AssessmentAgent] = None
_recommender: Optional[RecommendationEngine] = None
_gap_analyzer: Optional[GapAnalyzer] = None
_learning_path: Optional[LearningPath] = None
_resume_coach: Optional[ResumeCoach] = None
_skill_normalizer: Optional[SkillNormalizer] = None
_quiz_engine: Optional[QuizEngine] = None
_quiz_sessions: Dict[str, AgentState] = {}


def _get_agent() -> AssessmentAgent:
    global _agent
    if _agent is None:
        _agent = AssessmentAgent()
    return _agent


def _get_recommender() -> RecommendationEngine:
    global _recommender
    if _recommender is None:
        _recommender = RecommendationEngine()
    return _recommender


def _get_gap_analyzer() -> GapAnalyzer:
    global _gap_analyzer
    if _gap_analyzer is None:
        _gap_analyzer = GapAnalyzer()
    return _gap_analyzer


def _get_learning_path() -> LearningPath:
    global _learning_path
    if _learning_path is None:
        _learning_path = LearningPath()
    return _learning_path


def _get_resume_coach() -> ResumeCoach:
    global _resume_coach
    if _resume_coach is None:
        _resume_coach = ResumeCoach()
    return _resume_coach


def _get_skill_normalizer() -> SkillNormalizer:
    global _skill_normalizer
    if _skill_normalizer is None:
        _skill_normalizer = SkillNormalizer()
    return _skill_normalizer


def _get_quiz_engine() -> QuizEngine:
    global _quiz_engine
    if _quiz_engine is None:
        _quiz_engine = QuizEngine()
    return _quiz_engine


def _add_cors_headers(response):
    origin = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Session-Id"
    response.headers["Access-Control-Expose-Headers"] = "X-Session-Id"
    return response


@app.after_request
def cors_after_request(response):
    return _add_cors_headers(response)


@app.route("/health", methods=["GET"])
def health():
    engine = _get_recommender()
    return jsonify({
        "status": "ok",
        "vector_index_loaded": engine.index is not None,
        "embedding_model_loaded": engine.model is not None,
        "job_count": len(engine.job_ids),
    })


_SIGNAL_LABELS = {
    "SOFTWARE": "Software Engineering",
    "DATA_AI": "Data & AI",
    "CREATIVE": "Creative & Design",
    "BUSINESS": "Business & Ops",
    "SALES_MKT": "Sales & Marketing",
    "ACCOUNTING": "Accounting & Finance",
    "ADMIN": "Administration",
    "ENGINEERING": "Engineering & Construction",
    "EDUCATION": "Education & Training",
    "LOGISTICS": "Logistics & Transport",
}


def _label_from_signals(signals: dict) -> str:
    if not signals:
        return ""
    labels = []
    for key in signals.keys():
        label = _SIGNAL_LABELS.get(key)
        if not label:
            label = key.replace("_", " ").replace("-", " ").title()
        labels.append(label)
    return ", ".join(labels)


def _label_from_skills(skills: list) -> str:
    if not skills:
        return ""
    normalizer = _get_skill_normalizer()
    labels = [normalizer.name_for(skill_id) for skill_id in skills]
    return ", ".join(labels)


def _format_question(q: dict, number: int, total: int) -> dict:
    raw_options = q.get("options")
    options = []

    if raw_options is None:
        # Open-ended / free-text question — no options to format
        pass
    elif isinstance(raw_options, dict):
        for key, meta in raw_options.items():
            label = ""
            if isinstance(meta, dict):
                label = meta.get("text") or meta.get("label") or ""
                if not label:
                    label = _label_from_skills(meta.get("skills", []))
                if not label:
                    label = _label_from_signals(meta.get("signals", {}))
            options.append({
                "value": key,
                "label": label or f"Option {key}",
            })
    elif isinstance(raw_options, list):
        for item in raw_options:
            if isinstance(item, dict):
                value = item.get("value") or item.get("id") or item.get("label")
                options.append({
                    "value": value,
                    "label": item.get("label") or item.get("text") or str(value),
                })
            else:
                options.append({"value": item, "label": str(item)})

    result = {
        "id": q["id"],
        "gate": q.get("gate"),
        "stem": q.get("stem") or q.get("text", ""),
        "options": options,
        "number": number,
        "total": total,
        "answer_mode": q.get("answer_mode"),
        "question_type": q.get("question_type"),
        "difficulty": q.get("difficulty"),
        "estimated_minutes": q.get("estimated_minutes"),
    }

    # Include context and practical_task for open-ended questions
    if q.get("context"):
        result["context"] = q["context"]
    practical = q.get("practical_task")
    if practical:
        result["practical_task"] = practical

    return result


def _session_id() -> str:
    return request.headers.get("X-Session-Id") or request.args.get("session_id") or ""


def _quiz_payload(state: AgentState, question: Optional[dict], done: bool = False,
                  profile: Optional[dict] = None) -> dict:
    payload: Dict[str, Any] = {"done": done}
    if profile is not None:
        payload["skill_profile"] = profile
    if question is not None:
        total = max(
            AssessmentAgent.MIN_QUESTIONS,
            min(AssessmentAgent.MAX_QUESTIONS, state.question_count + 3),
        )
        payload["question"] = _format_question(
            question, state.question_count + 1, total
        )
    return payload


@app.route("/quiz", methods=["GET", "OPTIONS"])
def quiz_start():
    if request.method == "OPTIONS":
        return "", 204

    try:
        engine = _get_quiz_engine()
    except Exception as exc:
        return jsonify({"error": f"Quiz unavailable: {exc}"}), 503

    session = engine.create_session()
    session_state = engine.load_session(session["session_id"])
    first_q = engine.get_question(session.get("first_question_id"))
    if not first_q:
        return jsonify({"error": "No quiz questions available."}), 500

    progress = engine._progress(session_state)
    total = progress.get("estimated_total", 12)
    resp = jsonify({
        "done": False,
        "question": _format_question(first_q, 1, total),
        "progress": progress,
    })
    resp.headers["X-Session-Id"] = session["session_id"]
    return resp


@app.route("/quiz/answer", methods=["POST", "OPTIONS"])
def quiz_answer():
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True) or {}
    question_id = body.get("questionId") or body.get("question_id")
    selected = body.get("selectedOption") or body.get("selected_option")

    if not question_id or not selected:
        return jsonify({"error": "questionId and selectedOption are required"}), 400

    sid = _session_id()
    if not sid:
        return jsonify({"error": "Invalid or expired quiz session. Start with GET /quiz."}), 400

    try:
        engine = _get_quiz_engine()
        question = engine.get_question(question_id)
        if not question:
            return jsonify({"error": f"Question not found: {question_id}"}), 404

        if question.get("answer_mode") == "single_choice":
            ai_eval = evaluate_mcq(question, selected)
            answer_key = selected
        else:
            ai_eval = evaluate(question, selected)
            answer_key = None

        result = engine.submit_answer(
            session_id=sid,
            question_id=question_id,
            answer_raw=selected,
            answer_key=answer_key,
            ai_evaluation=ai_eval,
        )

        if result.get("status") == "continue":
            next_q = result.get("next_question")
            progress = result.get("progress") or {}
            number = progress.get("questions_answered", 0) + 1
            total = progress.get("estimated_total", 12)
            return jsonify({
                "done": False,
                "question": _format_question(next_q, number, total),
                "progress": progress,
            })

        profile = result.get("profile") or {}
        skill_scores = profile.get("skill_scores", {})
        recommendations_profile = {
            **profile,
            "detected_skills": profile.get("detected_skills") or list(skill_scores.keys()),
            "top_category": profile.get("top_category") or profile.get("detected_role") or profile.get("detected_domain"),
            "experience_level": profile.get("experience_level") or "junior",
        }
        recommendations = _get_recommender().rank_jobs(recommendations_profile, top_n=10)
        return jsonify({
            "done": True,
            "skill_profile": recommendations_profile,
            "recommendations": recommendations,
            "progress": result.get("progress"),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/recommend", methods=["POST", "OPTIONS"])
def recommend():
    """Rank jobs for a skill profile using FAISS retrieval + hybrid scoring."""
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True) or {}
    profile = body.get("skill_profile") or body.get("profile") or body

    if not isinstance(profile, dict):
        return jsonify({"error": "JSON body must include a skill profile object"}), 400

    top_n = int(body.get("top_n", 10))
    top_n = max(1, min(top_n, 50))

    try:
        results = _get_recommender().rank_jobs(profile, top_n=top_n)
        return jsonify({
            "recommendations": results,
            "count": len(results),
            "engine": {
                "semantic_search": _get_recommender().index is not None,
            },
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/analysis", methods=["POST", "OPTIONS"])
def analysis():
    """Return skill gap analysis and learning resources for a profile."""
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True) or {}
    profile = body.get("skill_profile") or body.get("profile") or body.get("profile") or {}
    recommendations = body.get("recommendations") or []

    try:
        gaps = _get_gap_analyzer().analyze(profile, recommendations)
        resources = _get_learning_path().recommend_resources(
            [gap["skill_id"] for gap in gaps]
        )
        return jsonify({
            "gaps": gaps,
            "resources": resources,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/resume-tips", methods=["POST", "OPTIONS"])
def resume_tips():
    """Return personalized resume tips and study schedule for a profile and gaps."""
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True) or {}
    profile = body.get("skill_profile") or body.get("profile") or {}
    gaps = body.get("gaps") or []

    try:
        coaching = _get_resume_coach().get_coaching(profile, gaps)
        return jsonify(coaching)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
