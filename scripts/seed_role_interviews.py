"""
Generate role interview questions JSON and upsert into jobs.db.

Usage:
  python scripts/role_interview_bank.py
  python scripts/seed_role_interviews.py
"""

from __future__ import annotations

import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.role_interview_bank import (  # noqa: E402
	MIN_QUESTIONS_PER_ROLE,
	build_all_roles,
	write_bank,
)
from app.quiz_engine import CATEGORY_TO_ROLES, DB_PATH  # noqa: E402


def upsert_questions(conn: sqlite3.Connection, questions: list) -> int:
	import json

	count = 0
	for q in questions:
		routing = q.get("routing", {})
		conn.execute(
			"""
			INSERT OR REPLACE INTO questions (
				id, gate, domain_scope, question_type,
				role_targets, difficulty, experience_level_target,
				stem, context, answer_mode,
				options, practical_task, scoring,
				ai_evaluation_prompt, job_evidence,
				route_strong, route_partial, route_weak,
				estimated_minutes, is_active
			) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
			""",
			(
				q["id"],
				q.get("gate", 2),
				q.get("domain_scope", "ALL"),
				q.get("question_type", "free_response"),
				__import__("json").dumps(q.get("role_targets", [])),
				q.get("difficulty", "beginner"),
				q.get("experience_level_target", "any"),
				q["stem"],
				q.get("context"),
				q.get("answer_mode", "free_text"),
				json.dumps(q["options"]) if q.get("options") else None,
				json.dumps(q["practical_task"]) if q.get("practical_task") else None,
				json.dumps(q.get("scoring", {})),
				q.get("ai_evaluation_prompt"),
				json.dumps(q.get("job_evidence", [])),
				routing.get("strong"),
				routing.get("partial"),
				routing.get("weak"),
				q.get("estimated_minutes"),
			),
		)
		count += 1
	conn.commit()
	return count


def verify_counts(conn: sqlite3.Connection) -> None:
	roles = sorted({role for roles in CATEGORY_TO_ROLES.values() for role in roles})
	short = []
	for role in roles:
		n = conn.execute(
			"""
			SELECT COUNT(*) FROM questions q, json_each(q.role_targets)
			WHERE q.is_active = 1 AND q.id LIKE 'Q_ROLE_INT_%' AND json_each.value = ?
			""",
			(role,),
		).fetchone()[0]
		if n < MIN_QUESTIONS_PER_ROLE:
			short.append((role, n))
	if short:
		print("WARNING: roles below minimum:", short)
	else:
		print(f"All {len(roles)} roles have at least {MIN_QUESTIONS_PER_ROLE} interview questions.")


def main() -> None:
	json_path = write_bank()
	print(f"Wrote {json_path}")

	if not os.path.exists(DB_PATH):
		print(f"Database not found at {DB_PATH}; run the app once to create it.")
		return

	questions = build_all_roles()
	conn = sqlite3.connect(DB_PATH)
	try:
		upserted = upsert_questions(conn, questions)
		print(f"Upserted {upserted} questions into {DB_PATH}")
		verify_counts(conn)
	finally:
		conn.close()


if __name__ == "__main__":
	main()
