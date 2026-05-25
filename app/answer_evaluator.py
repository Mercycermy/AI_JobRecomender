"""
Answer evaluation helpers.
Falls back to heuristic scoring if no AI key is configured.
"""

from __future__ import annotations

import json
import os
from typing import Dict


def _api_key() -> str:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if api_key or os.environ.get("AI_JOB_RECOMMENDER_SKIP_DOTENV") == "1":
        return api_key

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        return api_key

    return os.environ.get("GROQ_API_KEY", "")


def _heuristic_score(question: dict, answer: str) -> Dict[str, object]:
    scoring = question.get("scoring") or {}
    skill_weights = scoring.get("skill_weights") or {}
    cat_weights = scoring.get("category_weights") or {}

    score = 0.6 if answer else 0.2

    return {
        "score": score,
        "feedback": "Thanks for the response. We'll refine this with AI scoring when enabled.",
        "skill_scores": {k: score for k in skill_weights},
        "category_score_deltas": {k: int(score * 10) for k in cat_weights},
        "confidence": 0.5,
        "follow_up_question": None,
    }


def evaluate(question: dict, user_answer: str) -> Dict[str, object]:
    api_key = _api_key()
    if not api_key:
        return _heuristic_score(question, user_answer)

    try:
        from groq import Groq
    except Exception:
        return _heuristic_score(question, user_answer)

    client = Groq(api_key=api_key)
    model = "llama3-70b-8192"

    scoring = question.get("scoring") or {}
    rubric = scoring.get("rubric", [])
    red_flags = scoring.get("red_flags", [])
    skill_weights = scoring.get("skill_weights", {})
    cat_weights = scoring.get("category_weights", {})

    if question.get("ai_evaluation_prompt"):
        prompt = f"""
{question['ai_evaluation_prompt']}

## Question
{question['stem']}

## Context
{question.get('context') or 'None'}

## Candidate Answer
{user_answer}

## Rubric
{json.dumps(rubric, indent=2)}

## Red Flags
{json.dumps(red_flags)}

## Skill Weights
{json.dumps(skill_weights)}

## Category Weights
{json.dumps(cat_weights)}

Return ONLY this JSON structure:
{{
  "score": 0.75,
  "feedback": "...",
  "skill_scores": {json.dumps({k: 0.0 for k in skill_weights})},
  "category_score_deltas": {json.dumps({k: 0 for k in cat_weights})},
  "confidence": 0.9,
  "follow_up_question": "..."
}}
"""
    else:
        prompt = f"""
Evaluate this interview answer for the role implied by these skill weights: {list(skill_weights.keys())}.

## Question
{question['stem']}

## Context
{question.get('context') or 'None'}

## Candidate Answer
{user_answer}

## Rubric Criteria
{json.dumps(rubric, indent=2)}

Return ONLY this JSON:
{{
  "score": 0.0,
  "feedback": "...",
  "skill_scores": {json.dumps({k: 0.0 for k in skill_weights})},
  "category_score_deltas": {json.dumps({k: 0 for k in cat_weights})},
  "confidence": 0.8,
  "follow_up_question": "..."
}}
"""

    system = "You are a senior technical interviewer. Return ONLY valid JSON."

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return _heuristic_score(question, user_answer)


def evaluate_mcq(question: dict, answer_key: str) -> Dict[str, object]:
    options = question.get("options") or {}
    chosen = {}

    if isinstance(options, dict):
        chosen = options.get(answer_key, {})
    elif isinstance(options, list):
        for option in options:
            if not isinstance(option, dict):
                continue
            key = option.get("value") or option.get("id") or option.get("label")
            if key == answer_key:
                chosen = option
                break
    quality = chosen.get("quality_level", "partial")
    score_map = {"strong": 1.0, "partial": 0.6, "weak": 0.2}
    score = score_map.get(quality, 0.5)
    return {
        "score": score,
        "feedback": f"You selected: {chosen.get('text','')}",
        "skill_scores": {skill: score for skill in chosen.get("skills", [])},
        "category_score_deltas": chosen.get("signals", {}),
        "confidence": 1.0,
        "follow_up_question": None,
    }
