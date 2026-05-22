"""
Tests for the Adaptive Assessment Agent.

Covers the complete 16-question dynamic routing flow, including:
1. Sector Selection (Gate 0)
2. Subdomain Selection (Gate 0)
3. Practical/Debugging Tasks (Gate 1)
4. Role-specific & Domain-specific Technical Evaluation (Gate 2)
5. Metadata Closing (Gate 3 - Q_EXP & Q_PROJECT)
6. Termination, Scoring, and SkillProfile Generation.
"""

import sys
import os

# Ensure the project root is on sys.path so `app.agent` resolves
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agent import AssessmentAgent, AgentState

agent = AssessmentAgent()

def score_q(state, qid):
    """Helper to dynamically score an answer depending on whether it's multiple choice or free response."""
    qdata = agent.bank.get(qid)
    assert qdata is not None, f"Question {qid} not found in the QuestionBank!"
    if qdata.get("options") is not None:
        # Multiple choice
        options = list(qdata["options"].keys())
        opt = "C" if "C" in options else options[0]
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

def test_subdomain_routing():
    """Verify that answering Q_G0_DOMAIN_001 routes to the correct subdomain question."""
    domain_map = {
        "A": ("SOFTWARE", "Q_G0_SUBDOMAIN_SOFTWARE"),
        "B": ("DATA_AI", "Q_G0_SUBDOMAIN_DATA_AI"),
        "C": ("CREATIVE", "Q_G0_SUBDOMAIN_CREATIVE"),
        "D": ("SALES_MKT", "Q_G0_SUBDOMAIN_SALES_MKT"),
        "E": ("ACCOUNTING", "Q_G0_SUBDOMAIN_ACCOUNTING"),
        "F": ("ADMIN", "Q_G0_SUBDOMAIN_ADMIN"),
        "G": ("ENGINEERING", "Q_G0_SUBDOMAIN_ENGINEERING")
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

    print("[PASS] test_subdomain_routing PASSED")


# --------------------------------------------------------------------------
# 3. Full 16-Question Sequence for SOFTWARE -> Full Stack Developer
# --------------------------------------------------------------------------

def test_full_16_question_flow_software():
    """Verify the entire 16-question dynamic assessment sequence for Software Full Stack Developer."""
    state = agent.init_state()

    # Q1: Sector Identification (Gate 0)
    q1 = agent.get_next_question(state)
    assert q1 == "Q_G0_DOMAIN_001"
    state = agent.score_answer(state, q1, "A")  # Select SOFTWARE
    assert state.domain == "SOFTWARE"

    # Q2: Subdomain Selection (Gate 0)
    q2 = agent.get_next_question(state)
    assert q2 == "Q_G0_SUBDOMAIN_SOFTWARE"
    state = agent.score_answer(state, q2, "C")  # Select Full Stack Developer
    assert state.specific_role == "Full Stack Developer"

    # Q3-Q4: Gate 1 Practical Tasks
    q3 = agent.get_next_question(state)
    q3_data = agent.bank.get(q3)
    assert q3_data["gate"] == 1
    assert q3_data.get("domain_scope") == "SOFTWARE"
    state = score_q(state, q3)

    q4 = agent.get_next_question(state)
    q4_data = agent.bank.get(q4)
    assert q4_data["gate"] == 1
    assert q4_data.get("domain_scope") == "SOFTWARE"
    state = score_q(state, q4)

    # Q5-Q6: Gate 2 Role-Specific Technical Questions (Full Stack Developer)
    q5 = agent.get_next_question(state)
    q5_data = agent.bank.get(q5)
    assert q5_data["gate"] == 2
    assert any("full stack developer" in t.lower() for ev in q5_data.get("job_evidence", []) for t in ev.get("job_titles", []))
    state = score_q(state, q5)

    q6 = agent.get_next_question(state)
    q6_data = agent.bank.get(q6)
    assert q6_data["gate"] == 2
    assert any("full stack developer" in t.lower() for ev in q6_data.get("job_evidence", []) for t in ev.get("job_titles", []))
    state = score_q(state, q6)

    # Q7-Q14: Gate 2 Domain-Specific Questions (TECH)
    for count in range(7, 15):
        qid = agent.get_next_question(state)
        qdata = agent.bank.get(qid)
        assert qdata["gate"] == 2
        assert qdata.get("domain_scope") in ("TECH", "GENERAL", "SOFTWARE")
        state = score_q(state, qid)

    # Q15: Metadata (Q_EXP)
    q15 = agent.get_next_question(state)
    assert q15 == "Q_EXP"
    state = agent.score_answer(state, q15, "C")  # Mid-level (3-5 years)
    assert state.experience_level == "mid"

    # Q16: Metadata (Q_PROJECT)
    q16 = agent.get_next_question(state)
    assert q16 == "Q_PROJECT"
    state = agent.score_answer(state, q16, "A")  # Full-stack project

    # Termination check (should return None now that we reached 16 questions and metadata is complete)
    next_q = agent.get_next_question(state)
    assert next_q is None, f"Expected quiz to terminate after 16 questions, but got '{next_q}'"

    # Generate Profile
    profile = agent.generate_skill_profile(state)
    assert profile["question_count"] == 16
    assert profile["experience_level"] == "mid"
    assert "fe-react" in profile["detected_skills"]
    assert "be-api" in profile["detected_skills"]

    print("[PASS] test_full_16_question_flow_software PASSED")


# --------------------------------------------------------------------------
# 4. Full 16-Question Sequence for DATA_AI -> Data Scientist
# --------------------------------------------------------------------------

def test_full_16_question_flow_data_ai():
    """Verify the entire 16-question dynamic assessment sequence for Data Scientist."""
    state = agent.init_state()

    # Q1: Sector Identification (Gate 0)
    q1 = agent.get_next_question(state)
    assert q1 == "Q_G0_DOMAIN_001"
    state = agent.score_answer(state, q1, "B")  # Select DATA_AI
    assert state.domain == "DATA_AI"

    # Q2: Subdomain Selection (Gate 0)
    q2 = agent.get_next_question(state)
    assert q2 == "Q_G0_SUBDOMAIN_DATA_AI"
    state = agent.score_answer(state, q2, "A")  # Select Data Scientist
    assert state.specific_role == "Data Scientist"

    # Q3-Q4: Gate 1 Practical Tasks (DATA_AI & Fallbacks)
    q3 = agent.get_next_question(state)
    q3_data = agent.bank.get(q3)
    assert q3_data["gate"] == 1
    assert q3_data.get("domain_scope") in ("DATA_AI", "SOFTWARE")
    state = score_q(state, q3)

    q4 = agent.get_next_question(state)
    q4_data = agent.bank.get(q4)
    assert q4_data["gate"] == 1
    assert q4_data.get("domain_scope") in ("DATA_AI", "SOFTWARE")
    state = score_q(state, q4)

    # Q5-Q6: Gate 2 Role-Specific Technical Questions (Data Scientist)
    q5 = agent.get_next_question(state)
    q5_data = agent.bank.get(q5)
    assert q5_data["gate"] == 2
    assert any("data scientist" in t.lower() for ev in q5_data.get("job_evidence", []) for t in ev.get("job_titles", []))
    state = score_q(state, q5)

    q6 = agent.get_next_question(state)
    q6_data = agent.bank.get(q6)
    assert q6_data["gate"] == 2
    assert any("data scientist" in t.lower() for ev in q6_data.get("job_evidence", []) for t in ev.get("job_titles", []))
    state = score_q(state, q6)

    # Q7-Q14: Gate 2 Domain-Specific Questions (TECH)
    for count in range(7, 15):
        qid = agent.get_next_question(state)
        qdata = agent.bank.get(qid)
        assert qdata["gate"] == 2
        assert qdata.get("domain_scope") in ("TECH", "GENERAL", "DATA_AI")
        state = score_q(state, qid)

    # Q15: Metadata (Q_EXP)
    q15 = agent.get_next_question(state)
    assert q15 == "Q_EXP"
    state = agent.score_answer(state, q15, "D")  # Senior level
    assert state.experience_level == "senior"

    # Q16: Metadata (Q_PROJECT)
    q16 = agent.get_next_question(state)
    assert q16 == "Q_PROJECT"
    state = agent.score_answer(state, q16, "C")  # Data Science / Dashboards

    # Termination check
    next_q = agent.get_next_question(state)
    assert next_q is None

    # Generate Profile
    profile = agent.generate_skill_profile(state)
    assert profile["question_count"] == 16
    assert profile["experience_level"] == "senior"

    print("[PASS] test_full_16_question_flow_data_ai PASSED")


# --------------------------------------------------------------------------
# 5. Agent Terminates Correctly
# --------------------------------------------------------------------------

def test_max_questions_termination():
    """Verify that get_next_question returns None after 20 questions."""
    state = agent.init_state()
    state.question_count = 20
    state.asked = {"Q_EXP", "Q_PROJECT"}

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
    state = agent.score_answer(state, "Q_G0_DOMAIN_001", "A")
    state = agent.score_answer(state, "Q_G0_SUBDOMAIN_SOFTWARE", "C")
    state = agent.score_answer(state, "Q_TECH_FE_REACT_001", "strong")
    state = agent.score_answer(state, "Q_EXP", "B")       # Junior
    state = agent.score_answer(state, "Q_PROJECT", "E")    # Interactive UIs
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
    test_subdomain_routing()
    test_full_16_question_flow_software()
    test_full_16_question_flow_data_ai()
    test_max_questions_termination()
    test_skill_profile_keys()
    print("\n==============================")
    print("ALL TESTS PASSED [PASS]")
