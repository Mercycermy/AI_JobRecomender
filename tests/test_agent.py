"""
Tests for the Adaptive Assessment Agent.

Covers: routing paths, scoring, tiebreaker logic, termination, and output schema.
Uses REAL question IDs from the partitioned data files (questions_part*.json).
"""

import sys
import os

# Ensure the project root is on sys.path so `app.agent` resolves
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agent import AssessmentAgent, AgentState


agent = AssessmentAgent()


# --------------------------------------------------------------------------
# 1. Software → Frontend path  (real IDs from partitioned data)
# --------------------------------------------------------------------------

def test_software_frontend_path():
    """Simulate: Domain → Software → free-text React + CSS questions → Q_EXP → Q_PROJECT."""
    state = agent.init_state()

    # Step 1: Gate 0 — choose SOFTWARE domain
    state = agent.score_answer(state, "Q_G0_DOMAIN_001", "A")

    # Step 2-3: Gate 1 free-text questions (options=null → answer is free text)
    state = agent.score_answer(state, "Q_TECH_FE_REACT_001", "strong")
    state = agent.score_answer(state, "Q_TECH_FE_CSS_001", "strong")

    # Step 4-5: Standard close-out questions
    state = agent.score_answer(state, "Q_EXP", "C")       # mid-level
    state = agent.score_answer(state, "Q_PROJECT", "A")    # web app

    profile = agent.generate_skill_profile(state)

    assert profile["top_category"] == "frontend-dev", (
        f"Expected 'frontend-dev', got '{profile['top_category']}'"
    )
    assert profile["experience_level"] == "mid", (
        f"Expected 'mid', got '{profile['experience_level']}'"
    )
    assert "fe-react" in profile["detected_skills"]
    assert "fe-css" in profile["detected_skills"]
    print("[PASS] test_software_frontend_path PASSED")
    print("  category_scores:", profile["category_scores"])


# --------------------------------------------------------------------------
# 2. Agent starts with Q_G0_DOMAIN_001
# --------------------------------------------------------------------------

def test_starts_with_gate0():
    """Verify first question is Q_G0_DOMAIN_001."""
    state = agent.init_state()
    first_q = agent.get_next_question(state)
    assert first_q == "Q_G0_DOMAIN_001", (
        f"Expected 'Q_G0_DOMAIN_001', got '{first_q}'"
    )
    print("[PASS] test_starts_with_gate0 PASSED")


# --------------------------------------------------------------------------
# 3. Free-text scoring accumulates category_weights and skill_weights
# --------------------------------------------------------------------------

def test_freetext_scoring():
    """Verify that answering a free-text question accumulates scores
    from category_weights and detects skills from skill_weights."""
    state = agent.init_state()

    # Answer the gate-0 question first
    state = agent.score_answer(state, "Q_G0_DOMAIN_001", "A")  # SOFTWARE

    # Answer a free-text question
    state = agent.score_answer(state, "Q_TECH_FE_REACT_001", "strong")

    # The question has category_weights: {"frontend-dev": 30}
    assert state.scores["frontend-dev"] >= 30, (
        f"Expected frontend-dev >= 30, got {state.scores['frontend-dev']}"
    )
    # The question has skill_weights: {"fe-react": 25, "lang-js": 10}
    assert "fe-react" in state.detected_skills
    assert "lang-js" in state.detected_skills
    print("[PASS] test_freetext_scoring PASSED")
    print("  scores:", dict(state.scores))
    print("  skills:", state.detected_skills)


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
    print("[PASS] test_max_questions_termination PASSED")


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

    state = agent.init_state()
    state = agent.score_answer(state, "Q_G0_DOMAIN_001", "A")
    state = agent.score_answer(state, "Q_TECH_FE_REACT_001", "strong")
    state = agent.score_answer(state, "Q_EXP", "B")       # Junior
    state = agent.score_answer(state, "Q_PROJECT", "E")    # Interactive UIs
    profile = agent.generate_skill_profile(state)

    missing = required_keys - set(profile.keys())
    assert not missing, f"Missing keys in SkillProfile: {missing}"
    assert profile["source"] == "adaptive_quiz"
    assert profile["profile_vector"] is None  # populated later by NLP
    print("[PASS] test_skill_profile_keys PASSED")
    print("  profile:", profile)


# --------------------------------------------------------------------------
# 6. Domain routing from Q_G0_DOMAIN_001 sets correct domain
# --------------------------------------------------------------------------

def test_domain_routing():
    """Verify that answering Q_G0_DOMAIN_001 sets the correct domain
    and routes to the correct first Gate-1 question."""
    domain_map = {
        "A": ("SOFTWARE", "Q_TECH_FE_REACT_001"),
        "B": ("DATA_AI", "Q_TECH_DS_MODEL_001"),
    }

    for option, (expected_domain, expected_next) in domain_map.items():
        state = agent.init_state()
        state = agent.score_answer(state, "Q_G0_DOMAIN_001", option)
        assert state.domain == expected_domain, (
            f"Option {option}: Expected domain '{expected_domain}', got '{state.domain}'"
        )
        next_q = agent.get_next_question(state)
        assert next_q == expected_next, (
            f"Option {option}: Expected next '{expected_next}', got '{next_q}'"
        )

    print("[PASS] test_domain_routing PASSED")


# --------------------------------------------------------------------------
# 7. Q_EXP and Q_PROJECT are always asked before termination
# --------------------------------------------------------------------------

def test_experience_always_asked():
    """Verify Q_EXP and Q_PROJECT are served before termination
    even after confidence is reached."""
    state = agent.init_state()
    state.question_count = 12
    state.scores["frontend-dev"] = 100  # high confidence
    state.asked = {"Q_G0_DOMAIN_001", "Q_TECH_FE_REACT_001"}

    next_q = agent.get_next_question(state)
    assert next_q == "Q_EXP", f"Expected 'Q_EXP', got '{next_q}'"

    state.asked.add("Q_EXP")
    state.experience_level = "mid"
    next_q = agent.get_next_question(state)
    assert next_q == "Q_PROJECT", f"Expected 'Q_PROJECT', got '{next_q}'"

    state.asked.add("Q_PROJECT")
    next_q = agent.get_next_question(state)
    assert next_q is None, f"Expected None (done), got '{next_q}'"
    print("[PASS] test_experience_always_asked PASSED")


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

if __name__ == "__main__":
    test_software_frontend_path()
    test_starts_with_gate0()
    test_freetext_scoring()
    test_max_questions_termination()
    test_skill_profile_keys()
    test_domain_routing()
    test_experience_always_asked()
    print("\n==============================")
    print("ALL TESTS PASSED [PASS]")
