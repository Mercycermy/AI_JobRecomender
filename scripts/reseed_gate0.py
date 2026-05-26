import sqlite3
import os
import sys

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.quiz_engine import QuizEngine

def main():
    db_path = "data/jobs.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    print("Connecting to database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Cleaning up old Gate 0 questions...")
    # Delete old domain and subdomain questions
    cursor.execute("DELETE FROM questions WHERE id IN ('Q_G0_DOMAIN_001', 'Q_G0_SUBDOMAIN_001') OR gate=0")
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
