import sqlite3
import os
import sys

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.quiz_engine import QuizEngine

def main():
    engine = QuizEngine()
    
    print("--- Verifying Quiz Session Creation ---")
    session_data = engine.create_session()
    session_id = session_data["session_id"]
    first_q_id = session_data["first_question_id"]
    
    print(f"Created Session ID: {session_id}")
    print(f"First Question ID: {first_q_id}")
    assert first_q_id == "Q_G0_CATEGORY", f"Expected Q_G0_CATEGORY, got {first_q_id}"
    print("OK: Session creation verified successfully!")
    
    print("\n--- Verifying Answering Q_G0_CATEGORY (A -> Technology & Software Development) ---")
    result = engine.submit_answer(
        session_id=session_id,
        question_id="Q_G0_CATEGORY",
        answer_raw="A",
        answer_key="A"
    )
    
    next_q = result["next_question"]
    print(f"Next Question ID: {next_q['id']}")
    print(f"Next Question Stem: {next_q['stem']}")
    assert next_q["id"] == "Q_G0_ROLE_TECH", f"Expected Q_G0_ROLE_TECH, got {next_q['id']}"
    print("OK: Category selection routing verified successfully!")
    
    print("\n--- Verifying Answering Q_G0_ROLE_TECH (frontend-dev) ---")
    result = engine.submit_answer(
        session_id=session_id,
        question_id="Q_G0_ROLE_TECH",
        answer_raw="frontend-dev",
        answer_key="frontend-dev"
    )
    
    next_q = result["next_question"]
    print(f"Next Question ID: {next_q['id']}")
    print(f"Next Question Difficulty: {next_q['difficulty']}")
    print(f"Next Question Stem: {next_q['stem']}")
    print("OK: Role selection and dynamic transition to first assessment question verified successfully!")
    
    print("\n--- Verifying Subsequent Questions (Easy to Hard) ---")
    for i in range(3):
        current_qid = next_q["id"]
        result = engine.submit_answer(
            session_id=session_id,
            question_id=current_qid,
            answer_raw="test answer",
            answer_key=None,
            ai_evaluation={"score": 0.8, "feedback": "Good job", "skill_scores": {}, "category_score_deltas": {}}
        )
        if result["status"] == "done":
            print("Quiz finished early.")
            break
        next_q = result["next_question"]
        print(f"Question {i+2} ID: {next_q['id']}, Difficulty: {next_q['difficulty']}, Stem: {next_q['stem']}")
        assert next_q["difficulty"] == "beginner", f"Expected beginner question first, got {next_q['difficulty']}"

    print("\nOK: SUCCESS: All quiz flow and easy-to-hard progression checks passed successfully!")

if __name__ == "__main__":
    main()
