# AI Job Recommender

An intelligent, full-stack application designed to match users with job postings based on their skills, generate personalized learning paths, and provide actionable resume feedback. Job matching uses **Sentence Transformers** (`all-MiniLM-L6-v2`) with **FAISS** dense retrieval and a multi-factor hybrid ranker; an adaptive quiz agent builds the skill profile.

## Features
- **Smart Recommendations:** Uses precomputed job vectors to find the best job matches based on your unique skill set.
- **Skill Gap Analyzer:** Employs an AI-powered agent to calculate skill gaps and prioritize what you need to learn.
- **Adaptive Questioning:** An AI agent system actively queries and evaluates user inputs.
- **Modern User Interface:** Built with React and Vite for blazing-fast performance.
- **Scalable Backend:** Python-based REST API serving recommendations, tracking user context, and interacting with LLMs.

## Tech Stack
- **Frontend:** React, Vite
- **Backend:** Python (Flask/FastAPI)
- **Database:** SQLite
- **Machine Learning:** Sentence Transformers, FAISS (`faiss-cpu`), hybrid scoring (`app/recommender.py`)
- **Assessment:** Adaptive quiz agent (`app/agent.py`)

## File Structure
```text
├── app/               # Main Python application files
├── data/              # SQLite DB and raw JSON/CSV datasets
├── docs/              # Proprietary Internal system documentation (Git ignored)
├── frontend/          # React frontend (Vite source code)
├── models/            # Legacy pickle vectors (optional; superseded by FAISS index)
├── scripts/           # Python scripts for data seeding and model-building
├── tests/             # Unit and integration tests
└── README.md          # You are here
```

## Getting Started

### 1. Backend Setup
1. Open a terminal and navigate to the project directory.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your `.env` file with any required API keys (e.g., Groq, Anthropic, OpenAI).
5. Seed the database, quiz bank, and FAISS index:
   ```bash
   python scripts/seed_db.py
   python scripts/build_quiz_bank.py
   python scripts/build_vectors.py
   python scripts/build_faiss_index.py
   ```
   See `skills.md` for architecture details and `recommendation_phases.md` for the roadmap.
6. Start the Flask API:
   ```bash
   python app/routes.py
   ```
7. Run tests:
   ```bash
   python -m pytest tests/ -q
   ```

### Learning resources + resume tips (Groq + FAISS)
Set `GROQ_API_KEY` in your environment to enable AI resume tips and summaries. Build the learning-resource FAISS index once with `scripts/build_faiss_index.py`. After a user completes the adaptive quiz, call:

```bash
curl -X POST http://127.0.0.1:5000/recommendations \
   -H "Content-Type: application/json" \
   -d '{"session_id": "<quiz-session-id>"}'
```

The API returns a summary, resource list (FAISS ranked), and resume tips powered by Groq.

### 2. Frontend Setup
1. Open a new terminal instance and change into the frontend directory:
   ```bash
   cd frontend
   ```
2. Install NodeJS dependencies:
   ```bash
   npm install
   ```
3. Update `frontend/.env` to point to your local Python server (e.g., `VITE_API_URL=http://127.0.0.1:5000`).
4. Start the frontend development server:
   ```bash
   npm run dev
   ```
5. Open your browser to the URL provided (usually `http://localhost:5173`).

## Hosting
Detailed deployment constraints and cloud deployment instructions are tracked internally in `hosting_guide.md`. Recommended stacks include PythonAnywhere (Free) or Vercel + Render.