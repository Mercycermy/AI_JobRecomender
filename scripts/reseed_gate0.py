import sqlite3
import os
import sys
import json

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.quiz_engine import QuizEngine


def _load_domain_question():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(base_dir, "data", "questions_part1.json")
    if not os.path.exists(filepath):
        return None

    with open(filepath, encoding="utf-8") as fh:
        raw = json.load(fh)

    questions = raw
    if isinstance(raw, dict):
        questions = raw.get("questions") or raw.get("data") or raw.get("items") or []

    for question in questions:
        qid = question.get("id") or question.get("question_id")
        if qid == "Q_G0_DOMAIN_001":
            return question
    return None

def main():
    db_path = "data/jobs.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    print("Connecting to database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM questions WHERE id = 'Q_G0_SUBDOMAIN_001' OR (gate=0 AND id != 'Q_G0_DOMAIN_001')")
    conn.commit()
    domain_question = _load_domain_question()
    if domain_question:
        routing = domain_question.get("routing", {})
        cursor.execute(
            """
            UPDATE questions
            SET stem = ?,
                context = ?,
                answer_mode = ?,
                options = ?,
                role_targets = ?,
                route_strong = ?,
                route_partial = ?,
                route_weak = ?
            WHERE id = ?
            """,
            (
                domain_question.get("stem") or domain_question.get("question") or "",
                domain_question.get("context"),
                domain_question.get("answer_mode", "single_choice"),
                json.dumps(domain_question.get("options")) if domain_question.get("options") else None,
                json.dumps(domain_question.get("role_targets", [])),
                routing.get("strong"),
                routing.get("partial"),
                routing.get("weak"),
                "Q_G0_DOMAIN_001",
            ),
        )
        conn.commit()
    conn.close()
    print("Old Gate 0 questions deleted successfully.")

    print("Initializing QuizEngine to re-seed SUPPORT_QUESTIONS...")
    engine = QuizEngine()
    print("Database seeding completed.")

    # Print active gate 0 questions to verify
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    g0_qs = cursor.execute("SELECT id, stem FROM questions WHERE gate=0").fetchall()
    print("\nVerification - Active Gate 0 questions in DB:")
    for qid, stem in g0_qs:
        print(f"  - {qid}: {stem}")
    conn.close()

if __name__ == "__main__":
    main()
