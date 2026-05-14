# AI Job Recommender

An intelligent, full-stack application designed to match users with job postings based on their skills, generate personalized learning paths, and provide actionable resume feedback. The application relies on machine learning (TF-IDF + Cosine Similarity) and adaptive AI to accurately evaluate skill gaps.

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
- **Machine Learning & AI:** Scikit-Learn (TF-IDF Vectorizer), Custom AI Wrapper (`ai_client.py`)

## File Structure
```text
├── app/               # Main Python application files
├── data/              # SQLite DB and raw JSON/CSV datasets
├── docs/              # Proprietary Internal system documentation (Git ignored)
├── frontend/          # React frontend (Vite source code)
├── models/            # Pickle files (.pkl) containing job vectors
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
4. Configure your `.env` file with any required API keys (e.g., Anthropic, OpenAI).
5. (Optional) Run the data/seed scripts to build your `db.sqlite3` and `.pkl` vector models if they aren't generated yet.
6. Start the development server (adjust based on your framework):
   ```bash
   python app/routes.py
   ```

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