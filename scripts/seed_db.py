import sqlite3
import json
import csv
import os
import re

# Resolve paths relative to the project root (assuming script runs from c:\Users\zuko\Documents\a\AI_JobRecomender)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "db.sqlite3")
TAXONOMY_PATH = os.path.join(BASE_DIR, "data", "skills_taxonomy.json")
JOBS_PATH = os.path.join(BASE_DIR, "data", "jobs.csv")
RESOURCES_PATH = os.path.join(BASE_DIR, "data", "learning_resources.json")

def main():
    print("Connecting to SQLite database...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Creating tables...")
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        job_title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        source TEXT,
        exp_level TEXT,
        job_type TEXT,
        location TEXT,
        date_added TEXT,
        tfidf_vector BLOB
    );
    CREATE TABLE IF NOT EXISTS skill_taxonomy (
        skill_id TEXT PRIMARY KEY,
        canonical_name TEXT NOT NULL,
        aliases TEXT,
        domain TEXT,
        category TEXT,
        weight REAL DEFAULT 1.0,
        diff_tags TEXT
    );
    CREATE TABLE IF NOT EXISTS job_skills (
        job_id TEXT,
        skill_id TEXT,
        is_required INTEGER DEFAULT 1,
        PRIMARY KEY (job_id, skill_id),
        FOREIGN KEY (job_id) REFERENCES jobs(job_id),
        FOREIGN KEY (skill_id) REFERENCES skill_taxonomy(skill_id)
    );
    CREATE TABLE IF NOT EXISTS learning_resources (
        resource_id TEXT PRIMARY KEY,
        skill_id TEXT,
        title TEXT NOT NULL,
        platform TEXT,
        url TEXT,
        resource_type TEXT,
        difficulty TEXT,
        is_free INTEGER DEFAULT 1,
        FOREIGN KEY (skill_id) REFERENCES skill_taxonomy(skill_id)
    );
    CREATE TABLE IF NOT EXISTS admins (
        admin_id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)

    # Memory structure to map an exact alias string to its canonical skill_id
    alias_to_skill = {}

    print("Loading skills_taxonomy.json...")
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        for s in data["skills"]:
            cur.execute(
                "INSERT OR REPLACE INTO skill_taxonomy VALUES (?,?,?,?,?,?,?)",
                (s["skill_id"], s["canonical_name"],
                 json.dumps(s.get("aliases", [])),
                 s.get("domain"), s.get("category"),
                 s.get("weight", 1.0),
                 json.dumps(s.get("differentiation_tags", [])))
            )
            # Add mappings for auto-extraction
            # Add canonical name
            alias_to_skill[s["canonical_name"].lower()] = s["skill_id"]
            # Add all aliases
            for alias in s.get("aliases", []):
                alias_to_skill[alias.lower()] = s["skill_id"]

    # Precompile Regex for word-boundary matching on skills to avoid partial word matches
    # Since some aliases contain special chars like C++ or React.js, we escape them.
    # Note: re.escape might escape spaces, so we replace escaped spaces back.
    print("Precompiling skill alias regex matcher for job descriptions...")
    # Sort by length descending to match longest phrases first
    sorted_aliases = sorted(alias_to_skill.keys(), key=lambda x: len(x), reverse=True)
    # Build regex patterns
    compiled_patterns = []
    for alias in sorted_aliases:
        escaped = re.escape(alias)
        # Handle word boundaries nicely for things like C++
        # If it ends in a word char, require word boundary. Same for start.
        prefix = r'\b' if alias[0].isalnum() else r''
        suffix = r'\b' if alias[-1].isalnum() else r''
        pattern = re.compile(f"{prefix}{escaped}{suffix}", re.IGNORECASE)
        compiled_patterns.append((pattern, alias_to_skill[alias]))

    print("Loading jobs.csv and extracting skills...")
    jobs_inserted = 0
    skills_extracted = 0
    with open(JOBS_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Insert Job
            cur.execute(
                "INSERT OR REPLACE INTO jobs (job_id, job_title, description, category, source, exp_level, job_type, location, date_added) VALUES (?,?,?,?,?,?,?,?,?)",
                (row["job_id"], row["job_title"], row["description"],
                 row["category"], row.get("source"), row.get("exp_level"),
                 row.get("job_type"), row.get("location"), row.get("date_added"))
            )
            jobs_inserted += 1
            
            # Extract Skills
            desc_text = f"{row['job_title']} {row['description']}"
            matched_skills = set()
            for pattern, skill_id in compiled_patterns:
                if pattern.search(desc_text):
                    matched_skills.add(skill_id)
            
            for sk_id in matched_skills:
                # We can't perfectly distinguish required vs preferred easily without NLP, 
                # but we default to 1 (Required) for now as requested by spec.
                cur.execute(
                    "INSERT OR IGNORE INTO job_skills (job_id, skill_id, is_required) VALUES (?, ?, 1)",
                    (row["job_id"], sk_id)
                )
                skills_extracted += 1

    print(f"Loading learning_resources.json...")
    resources_inserted = 0
    with open(RESOURCES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        for r in data["resources"]:
            cur.execute(
                "INSERT OR REPLACE INTO learning_resources VALUES (?,?,?,?,?,?,?,?)",
                (r["resource_id"], r["skill_id"], r["title"], r.get("platform"),
                 r.get("url"), r.get("resource_type"), r.get("difficulty"),
                 r.get("is_free", 1))
            )
            resources_inserted += 1

    # Insert a default Admin for testing
    cur.execute("INSERT OR IGNORE INTO admins (admin_id, username, password_hash) VALUES (?, ?, ?)", ("admin_1", "admin", "pbkdf2:sha256:260000$xxxx$yyyy"))

    conn.commit()
    conn.close()
    
    print("\n--- Seeding Summary ---")
    print(f"Jobs Table: {jobs_inserted} rows inserted.")
    print(f"Job Skills Table: {skills_extracted} distinct skill extractions mapped.")
    print(f"Learning Resources Table: {resources_inserted} rows inserted.")
    print("Database seeded successfully.")

if __name__ == "__main__":
    main()
