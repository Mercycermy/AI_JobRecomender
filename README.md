# AI Job Recommender

AI Job Recommender is a full-stack career guidance application that matches users to jobs, identifies skill gaps, suggests learning resources, and generates resume coaching. It combines an adaptive quiz, manual profile entry, hybrid job matching, Telegram job ingestion, and optional AI-powered resume guidance.

For a deeper module-by-module breakdown, see [project_report.md](project_report.md).

## Key Features

1. Adaptive skill assessment that routes users through domain-specific quiz paths.
2. Manual profile entry with live skill suggestions and normalization.
3. Hybrid job matching with semantic retrieval, structured scoring, and explainable reranking.
4. Skill gap analysis that highlights the most important missing skills.
5. Learning resource recommendations mapped to those gaps.
6. Resume tips, resume upload, and resume generation support.
7. Telegram job ingestion plus an admin dashboard for review and analytics.

## Tech Stack

- Frontend: React 19, Vite 8, custom browser-history routing, vanilla CSS.
- Backend: Python 3.11+, Flask, SQLite, JSON-based service data.
- Vector search: Sentence Transformers and FAISS when installed and the generated artifacts are present.
- AI coaching: Groq-backed resume coaching with deterministic fallbacks.

## Project Layout

- [app/](app/) contains the Flask backend and all service modules.
- [frontend/](frontend/) contains the React UI.
- [data/](data/) stores the SQLite database, taxonomy, quiz bank, learning resources, and generated artifacts.
- [scripts/](scripts/) contains seeding, validation, and vector-building utilities.
- [tests/](tests/) contains the automated test suite.

## Data and Database

- [data/jobs.csv](data/jobs.csv) is the main job listing dataset.
- [data/skills_taxonomy.json](data/skills_taxonomy.json) is the canonical skill dictionary.
- [data/learning_resources.json](data/learning_resources.json) stores resource metadata.
- [data/questions_part1.json](data/questions_part1.json) through [data/questions_part5.json](data/questions_part5.json) store the adaptive quiz bank.
- [scripts/schema.sql](scripts/schema.sql) defines the quiz SQLite schema.
- The generated backend database is [data/db.sqlite3](data/db.sqlite3).
- The generated FAISS files are [data/jobs_faiss.index](data/jobs_faiss.index) and [data/jobs_id_map.json](data/jobs_id_map.json).

## Backend Setup

1. Open PowerShell in the project root.
2. Create the virtual environment:

```powershell
python -m venv .venv
```

3. Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

4. Install dependencies:

```powershell
pip install -r requirements.txt
```

5. Prepare the data and vector artifacts:

```powershell
python scripts/clean_data.py
python scripts/seed_db.py
python scripts/build_vectors.py
```

6. Start the backend from the project root:

```powershell
python -m app.routes
```

7. Verify the backend:

```text
http://127.0.0.1:5000/health
```

## Frontend Setup

1. Open a second terminal and go to the frontend folder:

```powershell
cd frontend
```

2. Install frontend dependencies:

```powershell
npm install
```

3. Set the API URL if needed:

```powershell
copy .env.example .env
```

Make sure `VITE_API_URL` points to the backend, usually `http://127.0.0.1:5000`.

4. Start the frontend:

```powershell
npm run dev
```

5. Open the app:

```text
http://localhost:5173
```

## Hosting Guide

### Local demo host

For a defense or classroom demo, run the backend and frontend in two terminals:

1. Terminal 1: `python -m app.routes`
2. Terminal 2: `cd frontend` then `npm run dev`
3. Visit `http://localhost:5173`
4. Confirm the backend health endpoint works at `http://127.0.0.1:5000/health`

### Production-style host

1. Set production environment variables such as `HOST=0.0.0.0`, `PORT`, `FLASK_SECRET_KEY`, `ADMIN_ACCESS_KEY`, and `CORS_ORIGINS`.
2. Build the frontend with `npm run build`.
3. Serve the backend behind a WSGI server such as Waitress or Gunicorn.
4. Deploy the frontend `dist` folder to a static host.
5. Point `VITE_API_URL` to the live backend URL.
6. Test `/health`, `/recommend`, and `/quiz` before presenting.

Example Windows backend host command after installing Waitress:

```powershell
waitress-serve --host=0.0.0.0 --port=5000 app.routes:app
```

## Tests

Run the Python test suite with:

```powershell
python -m pytest tests/ -v
```

## Troubleshooting

- If `python app/routes.py` fails with an import error, use `python -m app.routes` from the project root instead.
- If recommendations are missing semantic ranking, regenerate the FAISS artifacts with `python scripts/build_vectors.py`.
- If the AI resume coach is unavailable, set `GROQ_API_KEY` or rely on the built-in fallback tips.
