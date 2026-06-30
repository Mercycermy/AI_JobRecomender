"""
Flask API — adaptive quiz and semantic job recommendations.
"""

from __future__ import annotations

from typing import Optional

from flask import Flask, jsonify, request

from app.ai_tips import GroqResumeCoach
from app.answer_evaluator import evaluate, evaluate_mcq
from app.config import settings
from app.gap_analyzer import GapAnalyzer, format_gaps_for_ui
from app.learning_path import LearningPath
from app.profile_service import ProfileService, ProfileValidationError
from app.quiz_engine import QuizEngine
from app.recommender import RecommendationEngine
from app.resource_recommender import ResourceRecommender
from app.resume_generator import ResumeGeneratorError, ResumeGeneratorService
from app.resume_tips import ResumeCoach
from app.resume_upload import ResumeUploadError, ResumeUploadService, loads_json_field
from app.skill_normalizer import SkillNormalizer
from app.telegram_jobs import TelegramJobIngestionError, TelegramJobIngestionService

app = Flask(__name__)
app.config["SECRET_KEY"] = settings.secret_key

_recommender: Optional[RecommendationEngine] = None
_skill_normalizer: Optional[SkillNormalizer] = None
_profile_service: Optional[ProfileService] = None
_gap_analyzer: Optional[GapAnalyzer] = None
_learning_path: Optional[LearningPath] = None
_resume_coach: Optional[ResumeCoach] = None
_resume_upload_service: Optional[ResumeUploadService] = None
_resume_generator_service: Optional[ResumeGeneratorService] = None
_quiz_engine: Optional[QuizEngine] = None
_resource_recommender: Optional[ResourceRecommender] = None
_ai_resume_coach: Optional[GroqResumeCoach] = None
_telegram_job_service: Optional[TelegramJobIngestionService] = None


def _get_recommender() -> RecommendationEngine:
    global _recommender
    if _recommender is None:
        _recommender = RecommendationEngine()
    return _recommender


def _get_skill_normalizer() -> SkillNormalizer:
    global _skill_normalizer
    if _skill_normalizer is None:
        _skill_normalizer = SkillNormalizer()
    return _skill_normalizer


def _get_profile_service() -> ProfileService:
    global _profile_service
    if _profile_service is None:
        _profile_service = ProfileService(_get_skill_normalizer())
    return _profile_service


def _get_gap_analyzer() -> GapAnalyzer:
    global _gap_analyzer
    if _gap_analyzer is None:
        _gap_analyzer = GapAnalyzer(_get_skill_normalizer())
    return _gap_analyzer


def _get_learning_path() -> LearningPath:
    global _learning_path
    if _learning_path is None:
        _learning_path = LearningPath(normalizer=_get_skill_normalizer())
    return _learning_path


def _get_resume_coach() -> ResumeCoach:
    global _resume_coach
    if _resume_coach is None:
        _resume_coach = ResumeCoach()
    return _resume_coach


def _get_resume_upload_service() -> ResumeUploadService:
    global _resume_upload_service
    if _resume_upload_service is None:
        _resume_upload_service = ResumeUploadService(
            normalizer=_get_skill_normalizer(),
            ai_coach=_get_ai_resume_coach(),
        )
    return _resume_upload_service


def _get_resume_generator_service() -> ResumeGeneratorService:
    global _resume_generator_service
    if _resume_generator_service is None:
        _resume_generator_service = ResumeGeneratorService()
    return _resume_generator_service


def _get_quiz_engine() -> QuizEngine:
    global _quiz_engine
    if _quiz_engine is None:
        _quiz_engine = QuizEngine()
    return _quiz_engine


def _get_resource_recommender() -> ResourceRecommender:
    global _resource_recommender
    if _resource_recommender is None:
        _resource_recommender = ResourceRecommender()
    return _resource_recommender


def _get_ai_resume_coach() -> GroqResumeCoach:
    global _ai_resume_coach
    if _ai_resume_coach is None:
        _ai_resume_coach = GroqResumeCoach()
    return _ai_resume_coach


def _get_telegram_job_service() -> TelegramJobIngestionService:
    global _telegram_job_service
    if _telegram_job_service is None:
        _telegram_job_service = TelegramJobIngestionService(
            normalizer=_get_skill_normalizer(),
            ai_extractor=_get_ai_resume_coach(),
        )
    return _telegram_job_service


def _add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin and origin in settings.cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
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

        profile = _get_profile_service().from_payload(
            result.get("profile") or {},
            source_hint="quiz",
        )
        recommendations_profile = _get_profile_service().to_recommender_input(profile)
        recommendations = _get_recommender().rank_jobs(
            recommendations_profile, top_n=10
        )
        return jsonify({
            "done": True,
            "skill_profile": _get_profile_service().serialize(profile),
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

    try:
        body = request.get_json(silent=True) or {}
        profile_payload = body.get("skill_profile") or body.get("profile") or body
        profile = _get_profile_service().from_payload(profile_payload)
        top_n = int(body.get("top_n", 10))
        top_n = max(1, min(top_n, 50))
        recommender_input = _get_profile_service().to_recommender_input(profile)
        engine = _get_recommender()
        results = engine.rank_jobs(recommender_input, top_n=top_n)
        return jsonify({
            "skill_profile": _get_profile_service().serialize(profile),
            "recommendations": results,
            "count": len(results),
            "engine": engine.info(),
        })
    except (ProfileValidationError, TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/profile/normalize", methods=["POST", "OPTIONS"])
def normalize_profile():
    """Convert manual or quiz-shaped input to the shared canonical profile."""
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True) or {}
    profile_payload = body.get("skill_profile") or body.get("profile") or body
    try:
        profile = _get_profile_service().from_payload(profile_payload)
        return jsonify({"skill_profile": _get_profile_service().serialize(profile)})
    except ProfileValidationError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/skills/normalize", methods=["POST", "OPTIONS"])
def normalize_skills():
    """Normalize skill labels or skill-containing phrases for UI feedback."""
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True) or {}
    try:
        return jsonify(_get_profile_service().normalize_skills(body.get("skills")))
    except ProfileValidationError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/skills/suggest", methods=["GET", "OPTIONS"])
def suggest_skills():
    """Return taxonomy-backed autocomplete suggestions."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        limit = int(request.args.get("limit", 8))
    except ValueError:
        limit = 8
    return jsonify(
        _get_profile_service().suggest_skills(
            request.args.get("q", ""),
            limit=max(1, min(limit, 25)),
        )
    )


@app.route("/analysis", methods=["POST", "OPTIONS"])
def analysis():
    """Return skill gap analysis and learning resources for a profile or session."""
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")

    try:
        if session_id:
            session = _get_quiz_engine().load_session(session_id)
            gaps = format_gaps_for_ui(session)
            resources = _get_resource_recommender().recommend_grouped(session)
            ai_payload = _get_ai_resume_coach().generate_analysis(
                session, gaps, resources
            )
        else:
            profile = _get_profile_service().from_payload(
                body.get("skill_profile") or body.get("profile") or {}
            )
            recommendations = body.get("recommendations") or []
            profile_data = _get_profile_service().serialize(profile)
            gaps = _get_gap_analyzer().analyze(profile_data, recommendations)
            resources = _get_learning_path().recommend_resources(
                gaps
            )
            ai_payload = _get_ai_resume_coach().generate_analysis(
                profile_data, gaps, resources
            )
        return jsonify({
            "gaps": gaps,
            "resources": resources,
            "summary": ai_payload.get("summary"),
            "is_ai": ai_payload.get("is_ai", False),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/resume-tips", methods=["POST", "OPTIONS"])
def resume_tips():
    """Return personalized resume tips and study schedule for a profile or session."""
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")

    try:
        if session_id:
            session = _get_quiz_engine().load_session(session_id)
            gaps = format_gaps_for_ui(session)
            resource_groups = _get_resource_recommender().recommend_grouped(session)
            recs = _get_resource_recommender().recommend(session)
            ai_payload = _get_ai_resume_coach().generate_coaching(
                session,
                gaps,
                recommendations=recs,
                resource_groups=resource_groups,
            )
        else:
            profile = _get_profile_service().from_payload(
                body.get("skill_profile") or body.get("profile") or {}
            )
            recommendations = body.get("recommendations") or []
            profile_data = _get_profile_service().serialize(profile)
            gaps = _get_gap_analyzer().analyze(profile_data, recommendations)
            coaching = _get_resume_coach().get_coaching(profile_data, gaps)
            ai_payload = _get_ai_resume_coach().generate_coaching(
                profile_data,
                gaps,
                resource_groups=_get_learning_path().recommend_resources(gaps),
            )
            if not ai_payload.get("tips"):
                ai_payload = {
                "summary": "Use these recommendations to align your resume with your target role.",
                "tips": coaching.get("tips", []),
                "schedule": coaching.get("schedule", []),
                "resume_tips": [],
                "resource_explanations": {},
                "is_ai": coaching.get("is_ai", False),
                }
        return jsonify({
            "summary": ai_payload.get("summary"),
            "tips": ai_payload.get("tips", []),
            "schedule": ai_payload.get("schedule", []),
            "resume_tips": ai_payload.get("resume_tips", []),
            "resource_explanations": ai_payload.get("resource_explanations", {}),
            "is_ai": ai_payload.get("is_ai", False),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/resume/upload", methods=["POST", "OPTIONS"])
def resume_upload():
    """Extract an uploaded resume and return ATS-focused improvement tips."""
    if request.method == "OPTIONS":
        return "", 204

    upload = request.files.get("resume") or request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "Upload a resume file named resume or file."}), 400

    profile_payload = loads_json_field(request.form.get("profile"), {})
    recommendations = loads_json_field(request.form.get("recommendations"), [])
    target_role = request.form.get("target_role") or request.form.get("targetRole")

    try:
        profile = _get_profile_service().from_payload(profile_payload)
        profile_data = _get_profile_service().serialize(profile)
        result = _get_resume_upload_service().process_upload(
            filename=upload.filename,
            content=upload.read(),
            profile=profile_data,
            recommendations=recommendations,
            target_role=target_role,
        )
        return jsonify(result)
    except (ProfileValidationError, ResumeUploadError, TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/resume/generate", methods=["POST", "OPTIONS"])
def resume_generate():
    """Generate resume preview markup and downloadable assets."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        payload = request.get_json(silent=True) or {}
        return jsonify(_get_resume_generator_service().generate(payload))
    except ResumeGeneratorError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/telegram/jobs", methods=["GET", "OPTIONS"])
def telegram_jobs():
    """Return normalized Telegram jobs from the local feed."""
    if request.method == "OPTIONS":
        return "", 204

    query = request.args.get("q", "")
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    return jsonify(_get_telegram_job_service().list_jobs(query=query, limit=limit))


@app.route("/telegram/jobs/ingest", methods=["POST", "OPTIONS"])
def telegram_jobs_ingest():
    """Extract, validate, dedupe, and store raw Telegram job posts."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        payload = request.get_json(silent=True) or {}
        posts = payload.get("posts")
        if posts is None and any(key in payload for key in ("raw_text", "text", "message")):
            posts = [payload]
        result = _get_telegram_job_service().ingest_posts(posts or [])
        return jsonify(result)
    except TelegramJobIngestionError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/telegram/jobs/refresh", methods=["POST", "OPTIONS"])
def telegram_jobs_refresh():
    """Fetch configured public Telegram channels and ingest active jobs."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        payload = request.get_json(silent=True) or {}
        channels = payload.get("channels")
        per_channel_limit = int(payload.get("per_channel_limit", 12))
        return jsonify(
            _get_telegram_job_service().refresh_channels(
                channels=channels,
                per_channel_limit=per_channel_limit,
            )
        )
    except TelegramJobIngestionError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/recommendations", methods=["POST", "OPTIONS"])
def recommendations():
    """Return Groq AI analysis + FAISS learning resources for a completed quiz."""
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    try:
        session = _get_quiz_engine().load_session(session_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    if session.get("status") != "completed":
        return jsonify({"error": "Quiz not yet completed"}), 400

    try:
        gaps = format_gaps_for_ui(session)
        recs = _get_resource_recommender().recommend(session)
        ai_payload = _get_ai_resume_coach().generate(session, recs, gaps=gaps)

        resources_out = []
        for rec in recs:
            resource = rec.get("resource", {})
            gap = rec.get("gap", {})
            title = resource.get("title")
            resources_out.append(
                {
                    "resource_id": resource.get("resource_id"),
                    "title": title,
                    "platform": resource.get("platform"),
                    "url": resource.get("url"),
                    "difficulty": resource.get("difficulty"),
                    "is_free": resource.get("is_free"),
                    "estimated_hours": resource.get("estimated_hours"),
                    "covers": resource.get("covers"),
                    "skill_gap": gap.get("skill_id"),
                    "gap_score": gap.get("score"),
                    "ai_explanation": ai_payload.get("resource_explanations", {}).get(title, ""),
                }
            )

        return jsonify({
            "summary": ai_payload.get("summary"),
            "resources": resources_out,
            "resume_tips": ai_payload.get("resume_tips"),
            "detected_domain": session.get("detected_domain"),
            "is_ai": ai_payload.get("is_ai", False),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
