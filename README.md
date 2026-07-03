# AI Job Recommender

An intelligent, full-stack application designed to match users with job postings based on their skills, generate personalized learning paths, and provide actionable resume feedback. 

This project features an **Adaptive Skill Assessment Quiz** that builds a user profile, a **Hybrid Recommendation Engine** using **Sentence Transformers** (`all-MiniLM-L6-v2`) with a **FAISS** dense retrieval index for semantic similarity and multi-factor reranking, and an AI-powered resume review agent.

---

## Key Features

1. **Adaptive Skill Quiz:** An intelligent questioning engine that routes users through different paths (software, data/AI, business, creative) based on their answers, dynamically adjusting question difficulty and stopping once a high confidence score is reached.
2. **Manual Profile Entry:** An alternative profile builder allowing users to manually select and rate their skills, with live taxonomy suggestions.
3. **Smart Job Matching:** Hybrid scoring that combines vector search similarity, exact skill overlaps, experience level mapping, category matching, and location parameters.
4. **Skill Gap Analysis:** Computes current vs. required proficiency levels across top job matches, ranking gaps by priority.
5. **Personalized Learning Paths:** Maps curated online courses, documentation, and tutorials to the user's biggest skill gaps.
6. **Resume Coaching:** Uses LLMs (or static fallbacks) to suggest resume section edits and a 4-week study roadmap to prepare for the target roles.

---

## Tech Stack

*   **Frontend:** React 19, Vite 8, Vanilla CSS (with responsive grid and custom design tokens for light/dark themes).
*   **Backend:** Python 3.11+, Flask (REST API endpoints with CORS support).
*   **Database:** SQLite (local database for job listings, taxonomy, and sessions).
*   **Vector Engine & ML:** Sentence Transformers, FAISS (`faiss-cpu`) for dense embeddings and indexing.
*   **AI Integration:** Anthropic Claude API for personalized resume reviews.

---

## Project Structure

```text
├── app/                      # Main Python Flask application
│   ├── agent.py              # Adaptive quiz logic & state machine
│   ├── ai_client.py          # Anthropic Claude API client
│   ├── gap_analyzer.py       # Skill gap calculator
│   ├── learning_path.py      # Learning resources matching
│   ├── recommender.py        # FAISS & SQL recommendation engine
│   ├── resume_tips.py        # Resume tips & fallback generator
│   ├── routes.py             # Flask API blueprints & routing
│   └── skill_normalizer.py   # Skill canonical name mapping
├── data/                     # Data folder (contains SQLite DB and datasets)
│   ├── db.sqlite3            # Seeding target SQLite database (Git ignored)
│   ├── jobs.csv              # Main job listings dataset
│   ├── learning_resources.json # Course catalog mapped to skills
│   ├── questions_part1-5.json # Segmented quiz questions database
│   └── skills_taxonomy.json  # 246 canonical skills and aliases
├── frontend/                 # React frontend (Vite source code)
│   ├── public/               # Favicons and sprite SVGs
│   └── src/
│       ├── api/              # API communications client
│       ├── components/       # Layout page wrap components
│       ├── data/             # Mock data for offline execution
│       ├── pages/            # View pages (Home, Quiz, Results, Admin, etc.)
│       ├── App.jsx           # Routing mapping & root component
│       ├── index.css         # Styling colors and global resets
│       └── App.css           # UI layout and styling properties
├── scripts/                  # Seeding, vector construction, & validation scripts
│   ├── build_quiz_bank.py    # Generates quiz JSON data for testing
│   ├── build_vectors.py      # Creates FAISS semantic vector index
│   ├── clean_data.py         # Performs data validation checks
│   ├── seed_db.py            # Sets up and seeds the database
│   └── ...                   # Other processing scripts
├── tests/                    # Unit and integration test suites
│   ├── test_agent.py         # Validates quiz logic
│   ├── test_recommender.py   # Validates recommendation weights
│   └── ...                   # Other unit tests
├── requirements.txt          # Python dependencies
├── project_roadmap.txt       # Master build roadmap document
├── step1_scope.txt to step6_manual_profile.txt # Architecture planning logs
└── README.md                 # You are here
```

---

## Getting Started

### 1. Backend Setup & Data Seeding

1. Open your terminal and navigate to the project directory.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   
   # Windows:
   .venv\Scripts\activate
   
   # Mac/Linux:
   source .venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template and insert your API keys:
   ```bash
   copy .env.example .env
   # Edit .env and enter: ANTHROPIC_API_KEY=your-api-key
   ```
5. Initialize and seed the database, quiz banks, and FAISS vectors:
   ```bash
   # 1. Clean and validate data files
   python scripts/clean_data.py
   
   # 2. Seed SQLite database
   python scripts/seed_db.py
   
   # 3. Build FAISS vector index
   python scripts/build_vectors.py
   ```
6. Launch the Flask API server:
   ```bash
   python app/routes.py
   ```
   *The server will start on `http://127.0.0.1:5000`.*

### 2. Frontend Setup

1. Open a new terminal window and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Copy environment settings and specify your local API URL:
   ```bash
   copy .env.example .env
   # Ensure VITE_API_URL is set to http://127.0.0.1:5000
   ```
4. Start the frontend developer server:
   ```bash
   npm run dev
   ```
   *The application will open on `http://localhost:5173`.*

---

## Running Tests

To run the Python test suite, execute:
```bash
python -m pytest tests/ -v
```
This runs checks verifying the adaptive assessment engine, skill mapping calculations, and fallback mechanisms.