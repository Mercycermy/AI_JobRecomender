-- Quiz engine schema (derived from quizimplement.txt)

CREATE TABLE IF NOT EXISTS domains (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    slug  TEXT UNIQUE NOT NULL,
    label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    slug      TEXT UNIQUE NOT NULL,
    domain_id INTEGER REFERENCES domains(id),
    label     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id                      TEXT PRIMARY KEY,
    gate                    INTEGER NOT NULL,
    domain_scope            TEXT NOT NULL,
    question_type           TEXT NOT NULL,
    role_targets            TEXT NOT NULL,
    difficulty              TEXT NOT NULL,
    experience_level_target TEXT,
    stem                    TEXT NOT NULL,
    context                 TEXT,
    answer_mode             TEXT NOT NULL,
    options                 TEXT,
    practical_task          TEXT,
    scoring                 TEXT NOT NULL,
    ai_evaluation_prompt    TEXT,
    job_evidence            TEXT,
    route_strong            TEXT,
    route_partial           TEXT,
    route_weak              TEXT,
    estimated_minutes       INTEGER,
    is_active               INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_q_gate ON questions(gate);
CREATE INDEX IF NOT EXISTS idx_q_domain_gate ON questions(domain_scope, gate);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT,
    status          TEXT DEFAULT 'active',
    domain_scores   TEXT DEFAULT '{}',
    detected_domain TEXT,
    detected_role   TEXT,
    current_question_id  TEXT REFERENCES questions(id),
    questions_asked      TEXT DEFAULT '[]',
    skill_scores    TEXT DEFAULT '{}',
    category_scores TEXT DEFAULT '{}',
    overall_score   REAL DEFAULT 0,
    started_at      TEXT DEFAULT (datetime('now')),
    completed_at    TEXT
);

CREATE TABLE IF NOT EXISTS quiz_responses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES quiz_sessions(id),
    question_id     TEXT NOT NULL REFERENCES questions(id),
    answer_raw      TEXT,
    answer_key      TEXT,
    performance     TEXT,
    ai_score        REAL,
    ai_feedback     TEXT,
    ai_skill_scores TEXT,
    ai_category_deltas TEXT,
    ai_follow_up    TEXT,
    ai_confidence   REAL,
    evaluated       INTEGER DEFAULT 0,
    answered_at     TEXT DEFAULT (datetime('now'))
);
