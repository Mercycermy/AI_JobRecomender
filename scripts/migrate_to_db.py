import glob
import json
import os
import sqlite3

DB_PATH = os.path.join("data", "jobs.db")
SCHEMA_PATH = os.path.join("scripts", "schema.sql")

DOMAIN_LABELS = {
    "SOFTWARE": "Software Development",
    "DATA_AI": "Data & AI",
    "CREATIVE": "Design & Creative",
    "SALES_MKT": "Sales & Marketing",
    "ACCOUNTING": "Accounting & Finance",
    "ADMIN": "Administration",
    "ENGINEERING": "Architecture & Engineering",
    "ALL": "All Domains",
}

ROLE_DOMAIN_MAP = {
    "frontend-dev": "SOFTWARE",
    "backend-dev": "SOFTWARE",
    "fullstack-dev": "SOFTWARE",
    "mobile-dev": "SOFTWARE",
    "data-analyst": "DATA_AI",
    "data-scientist": "DATA_AI",
    "ml-engineer": "DATA_AI",
    "data-engineer": "DATA_AI",
    "graphic-designer": "CREATIVE",
    "ui-designer": "CREATIVE",
    "ux-researcher": "CREATIVE",
    "sales": "SALES_MKT",
    "marketing": "SALES_MKT",
    "accounting": "ACCOUNTING",
    "finance": "ACCOUNTING",
    "admin": "ADMIN",
    "hr": "ADMIN",
    "architect": "ENGINEERING",
    "civil-engineer": "ENGINEERING",
}


def apply_schema(conn):
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        conn.executescript(fh.read())
    print("✓ Schema applied")


def seed_taxonomy(conn):
    for slug, label in DOMAIN_LABELS.items():
        conn.execute(
            "INSERT OR IGNORE INTO domains (slug, label) VALUES (?,?)",
            (slug, label),
        )
    for role_slug, domain_slug in ROLE_DOMAIN_MAP.items():
        domain_id = conn.execute(
            "SELECT id FROM domains WHERE slug=?", (domain_slug,)
        ).fetchone()
        if domain_id:
            conn.execute(
                """
                INSERT OR IGNORE INTO roles (slug, domain_id, label)
                VALUES (?, ?, ?)
                """,
                (role_slug, domain_id[0], role_slug.replace("-", " ").title()),
            )
    conn.commit()
    print("✓ Taxonomy seeded")


def _normalize_questions(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("questions", "data", "items"):
            if key in raw:
                return raw[key]
        return list(raw.values())[0]
    return []


def migrate_questions(conn):
    files = sorted(glob.glob(os.path.join("data", "questions_part*.json")))
    if not files:
        print("⚠ No questions_part*.json files found in data/")
        return

    total_inserted = 0
    total_skipped = 0

    for filepath in files:
        print(f"\nProcessing {filepath} ...")
        with open(filepath, encoding="utf-8") as fh:
            raw = json.load(fh)

        questions = _normalize_questions(raw)
        file_inserted = 0

        for q in questions:
            try:
                qid = q.get("id") or q.get("question_id")
                if not qid:
                    total_skipped += 1
                    continue

                stem = q.get("stem") or q.get("question") or q.get("question_text")
                if not stem:
                    total_skipped += 1
                    continue

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
                        estimated_minutes
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        qid,
                        q.get("gate", 0),
                        q.get("domain_scope", "ALL"),
                        q.get("question_type", "multiple_choice"),
                        json.dumps(q.get("role_targets", [])),
                        q.get("difficulty", "beginner"),
                        q.get("experience_level_target", "any"),
                        stem,
                        q.get("context"),
                        q.get("answer_mode", "single_choice"),
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
                file_inserted += 1
            except Exception as exc:
                print(f"  ⚠ Skipped {q.get('id','?')}: {exc}")
                total_skipped += 1

        conn.commit()
        total_inserted += file_inserted
        print(f"  ✓ {file_inserted} questions inserted")

    print("\n" + "=" * 50)
    print(f"TOTAL: {total_inserted} inserted, {total_skipped} skipped")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    apply_schema(conn)
    seed_taxonomy(conn)
    migrate_questions(conn)
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
