"""
Tests for the Adaptive Assessment Agent.

Covers: routing paths, scoring, tiebreaker logic, termination, and output schema.
"""

import sys
import os

# Ensure the project root is on sys.path so `app.agent` resolves
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agent import AssessmentAgent, AgentState


agent = AssessmentAgent()


# --------------------------------------------------------------------------
# 1. Software → Frontend path
# --------------------------------------------------------------------------

def test_software_frontend_path():
    """Simulate: Software → Frontend → React expert → mid level."""
    state = agent.init_state()

    answers = [
        ("Q0_1", "A"),       # → SOFTWARE
        ("Q0_2_SW", "A"),    # → Frontend
        ("Q1_SW_A", "C"),    # React Query (advanced)
        ("Q1_SW_A2", "A"),   # CSS Grid
        ("Q_EXP", "C"),      # mid level
        ("Q_PROJECT", "A"),  # web app with auth
    ]

    for q_id, option in answers:
        state = agent.score_answer(state, q_id, option)

    profile = agent.generate_skill_profile(state)

    assert profile["top_category"] == "frontend-dev", (
        f"Expected 'frontend-dev', got '{profile['top_category']}'"
    )
    assert profile["experience_level"] == "mid", (
        f"Expected 'mid', got '{profile['experience_level']}'"
    )
    assert "fe-react" in profile["detected_skills"]
    assert "fe-css" in profile["detected_skills"]
    print("✓ test_software_frontend_path PASSED")
    print("  category_scores:", profile["category_scores"])


# --------------------------------------------------------------------------
# 2. Data/AI → ML Engineer path
# --------------------------------------------------------------------------

def test_data_ml_path():
    """Simulate: Data/AI → ML → Docker deployment → transformer fine-tune."""
    state = agent.init_state()

    answers = [
        ("Q0_1", "B"),       # → DATA_AI
        ("Q0_2_DA", "D"),    # → ML (neural networks)
        ("Q1_ML_A", "B"),    # Docker + K8s deployment
        ("Q1_ML_B", "D"),    # HuggingFace fine-tune
        ("Q_EXP", "C"),      # mid
        ("Q_PROJECT", "B"),  # end-to-end ML model
    ]

    for q_id, option in answers:
        state = agent.score_answer(state, q_id, option)

    profile = agent.generate_skill_profile(state)

    assert profile["top_category"] == "ml-engineer", (
        f"Expected 'ml-engineer', got '{profile['top_category']}'"
    )
    assert "ml-deployment" in profile["detected_skills"]
    assert "nlp-hf" in profile["detected_skills"]
    print("✓ test_data_ml_path PASSED")
    print("  category_scores:", profile["category_scores"])


# --------------------------------------------------------------------------
# 3. Tiebreaker fires when two categories are within 15 points
# --------------------------------------------------------------------------

def test_tiebreaker_fires():
    """Engineer a state where data-scientist and data-analyst are tied,
    then verify the agent recommends the tiebreaker question."""
    state = agent.init_state()

    # Q0_1 → Data/AI.  Q0_2_DA → analyst (data-analyst +30)
    # Q1_DA_A option B → data-analyst +20, data-scientist +15
    # At this point: data-analyst=50, data-scientist=15 → gap=35 (no tie yet)
    # Q1_DA_B option C → data-analyst +15, data-scientist +10
    # data-analyst=65, data-scientist=25 → gap=40 (still no tie)

    # Let's intentionally set up a near-tie via direct state manipulation
    state.scores["data-scientist"] = 40
    state.scores["data-analyst"] = 45
    state.asked = {"Q0_1", "Q0_2_DA", "Q1_DA_A", "Q1_DA_B"}
    state.question_count = 4
    state.domain = "DATA_AI"

    next_q = agent.get_next_question(state)
    assert next_q == "Q_DIFF_DS_vs_DA", (
        f"Expected tiebreaker 'Q_DIFF_DS_vs_DA', got '{next_q}'"
    )
    print("✓ test_tiebreaker_fires PASSED")


# --------------------------------------------------------------------------
# 4. Agent terminates within 20 questions
# --------------------------------------------------------------------------

def test_max_questions_termination():
    """Verify that get_next_question returns None after 20 questions."""
    state = agent.init_state()
    state.question_count = 20
    state.asked = {"Q_EXP", "Q_PROJECT"}  # already asked the finals

    next_q = agent.get_next_question(state)
    assert next_q is None, f"Expected None after 20 questions, got '{next_q}'"
    print("✓ test_max_questions_termination PASSED")


# --------------------------------------------------------------------------
# 5. SkillProfile contains all required keys
# --------------------------------------------------------------------------

def test_skill_profile_keys():
    """Ensure generate_skill_profile returns every expected key."""
    required_keys = {
        "source", "experience_level", "detected_skills",
        "top_category", "category_scores", "question_count",
        "confidence", "profile_vector",
    }

    profile = agent.run_assessment([
        ("Q0_1", "C"),            # Creative
        ("Q1_CREATIVE_A", "A"),   # UI/UX
        ("Q1_GRAPHIC_A", "A"),    # Brand identity
        ("Q_EXP", "B"),           # Junior
        ("Q_PROJECT", "E"),       # Personal projects
    ])

    missing = required_keys - set(profile.keys())
    assert not missing, f"Missing keys in SkillProfile: {missing}"
    assert profile["source"] == "adaptive_quiz"
    assert profile["profile_vector"] is None  # populated later by NLP
    print("✓ test_skill_profile_keys PASSED")
    print("  profile:", profile)


# --------------------------------------------------------------------------
# 6. run_assessment end-to-end convenience check
# --------------------------------------------------------------------------

def test_run_assessment_end_to_end():
    """Verify that run_assessment produces a valid profile for the
    backend path."""
    profile = agent.run_assessment([
        ("Q0_1", "A"),        # Software
        ("Q0_2_SW", "B"),     # Backend
        ("Q1_SW_B", "C"),     # Pre-signed URL → advanced backend
        ("Q1_SW_B2", "A"),    # Junction table
        ("Q_EXP", "D"),       # Senior
        ("Q_PROJECT", "D"),   # Production system
    ])

    assert profile["top_category"] == "backend-dev", (
        f"Expected 'backend-dev', got '{profile['top_category']}'"
    )
    assert profile["experience_level"] == "senior"
    assert profile["question_count"] == 6
    print("✓ test_run_assessment_end_to_end PASSED")
    print("  category_scores:", profile["category_scores"])


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

if __name__ == "__main__":
    test_software_frontend_path()
    test_data_ml_path()
    test_tiebreaker_fires()
    test_max_questions_termination()
    test_skill_profile_keys()
    test_run_assessment_end_to_end()
    print("\n==============================")
    print("ALL TESTS PASSED ✓")
