"""Tests for the Adaptive Assessment Agent (parts-only question bank)."""

import sys
import os

# Ensure the project root is on sys.path so `app.agent` resolves
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agent import AssessmentAgent, AgentState

agent = AssessmentAgent()

def score_q(state, qid):
    """Score a question using the first available option or a free-text placeholder."""
    qdata = agent.bank.get(qid)
    assert qdata is not None, f"Question {qid} not found in the QuestionBank!"
    if qdata.get("options") is not None:
        # Multiple choice
        options = list(qdata["options"].keys())
        opt = options[0]
        return agent.score_answer(state, qid, opt)
    else:
        # Free-text
        return agent.score_answer(state, qid, "strong")

# --------------------------------------------------------------------------
# 1. Start with Sector Selection (Question 1)
# --------------------------------------------------------------------------

def test_starts_with_gate0():
    """Verify first question is always Q_G0_DOMAIN_001."""
    state = agent.init_state()
    first_q = agent.get_next_question(state)
    assert first_q == "Q_G0_DOMAIN_001", (
        f"Expected 'Q_G0_DOMAIN_001', got '{first_q}'"
    )
    print("[PASS] test_starts_with_gate0 PASSED")


# --------------------------------------------------------------------------
# 2. Subdomain Selection Question (Question 2)
# --------------------------------------------------------------------------

def test_domain_answer_progresses():
    """Verify that answering Q_G0_DOMAIN_001 yields a valid next question."""
    state = agent.init_state()
    state = agent.score_answer(state, "Q_G0_DOMAIN_001", "A")
    next_q = agent.get_next_question(state)
    assert next_q is not None, "Expected a follow-up question after domain selection"
    assert agent.bank.get(next_q) is not None
    print("[PASS] test_domain_answer_progresses PASSED")


# --------------------------------------------------------------------------
# 3. Full 16-Question Sequence for SOFTWARE -> Full Stack Developer
# --------------------------------------------------------------------------

def test_flow_reaches_min_questions():
    """Verify the assessment continues until the configured minimum questions."""
    state = agent.init_state()
    while True:
        qid = agent.get_next_question(state)
        if qid is None:
            break
        state = score_q(state, qid)
        if state.question_count >= agent.MIN_QUESTIONS:
            break

    assert state.question_count >= agent.MIN_QUESTIONS
    print("[PASS] test_flow_reaches_min_questions PASSED")


# --------------------------------------------------------------------------
# 4. Full 16-Question Sequence for DATA_AI -> Data Scientist
# --------------------------------------------------------------------------

def test_flow_generates_profile():
    """Ensure we can generate a SkillProfile after progressing through the quiz."""
    state = agent.init_state()
    for _ in range(5):
        qid = agent.get_next_question(state)
        assert qid is not None
        state = score_q(state, qid)

    profile = agent.generate_skill_profile(state)
    assert profile["source"] == "adaptive_quiz"
    assert profile["question_count"] == state.question_count
    print("[PASS] test_flow_generates_profile PASSED")


# --------------------------------------------------------------------------
# 5. Agent Terminates Correctly
# --------------------------------------------------------------------------

def test_max_questions_termination():
    """Verify that get_next_question returns None after 20 questions."""
    state = agent.init_state()
    state.question_count = 20
    next_q = agent.get_next_question(state)
    assert next_q is None, f"Expected None after 20 questions, got '{next_q}'"
    print("[PASS] test_max_questions_termination PASSED")


# --------------------------------------------------------------------------
# 6. SkillProfile Output Schema Validation
# --------------------------------------------------------------------------

def test_skill_profile_keys():
    """Ensure generate_skill_profile returns every expected key."""
    required_keys = {
        "source", "experience_level", "detected_skills",
        "top_category", "category_scores", "question_count",
        "confidence", "profile_vector",
    }

    state = agent.init_state()
    for _ in range(3):
        qid = agent.get_next_question(state)
        assert qid is not None
        state = score_q(state, qid)
    profile = agent.generate_skill_profile(state)

    missing = required_keys - set(profile.keys())
    assert not missing, f"Missing keys in SkillProfile: {missing}"
    assert profile["source"] == "adaptive_quiz"
    assert profile["profile_vector"] is None
    print("[PASS] test_skill_profile_keys PASSED")


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

if __name__ == "__main__":
    test_starts_with_gate0()
    test_domain_answer_progresses()
    test_flow_reaches_min_questions()
    test_flow_generates_profile()
    test_max_questions_termination()
    test_skill_profile_keys()
    print("\n==============================")
    print("ALL TESTS PASSED [PASS]")
