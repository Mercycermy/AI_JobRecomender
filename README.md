# AI Job Recommender

AI Job Recommender is a full-stack career guidance system. It collects a user profile through an adaptive quiz or manual technical-skill input, matches that profile to jobs, explains the highest-fit roles, identifies technical skill gaps, recommends learning resources, reviews uploaded resumes, and builds a ready-to-use resume for matched jobs.

For the full defense document, module-by-module function reference, database details, dataset inventory, and deployment checklist, see [project_report.md](project_report.md).


## Current Product Flow

1. User starts from the main website.
2. User completes the adaptive quiz or manual skill input.
3. The frontend stores only the active session output in `sessionStorage`.
4. Backend normalizes the profile with the skill taxonomy.
5. Backend ranks jobs with hybrid matching.
6. Results page shows the highest-match job first, then compact other matches.
7. Gap analysis uses technical skills only; languages and soft skills are excluded from gap measurement.
8. Learning resources are generated from real detected gaps.
9. Resume tips and upload review use profile, matched jobs, and gap data.
10. Resume builder generates a downloadable improved resume.
11. Admin dashboard records quiz/manual intake, matched roles, matched skills, gaps, watched jobs, resources, resumes, and quiz question management.

## Main Features

- Adaptive quiz with role and skill routing.
- Manual profile input with taxonomy-backed skill suggestions.
- Hybrid job recommendation using structured scoring and optional semantic retrieval.
- Technical skill gap analysis based on matched jobs.
- Learning resource recommendations tied to the gap list.
- AI or fallback resume coaching.
- Resume upload review for improvement recommendations.
- Resume builder with HTML preview and PDF/image export payloads.
- Telegram job feed ingestion, active-deadline filtering, role/skill search, and profile-based matching.
- Admin dashboard for analytics and content management.

## Tech Stack

- Frontend: React 19, Vite 8, custom browser-history routing, CSS variables for light/dark themes.
- Backend: Python, Flask, SQLite, JSON service data.
- Matching: SQLite jobs, taxonomy normalization, weighted scoring, optional FAISS and sentence-transformers.
- AI: Groq API when `GROQ_API_KEY` is set, deterministic local fallbacks otherwise.
- Tests: Pytest for backend, ESLint and Vite build for frontend.

## Repository Layout

```text
app/                         Flask backend services and routes
data/                        Taxonomy, jobs, quiz banks, learning resources, runtime data
frontend/                    React/Vite frontend
scripts/                     Data seeding, validation, and artifact builders
tests/                       Backend automated tests
README.md                    Quick setup and hosting guide
requirements.txt             Python dependencies
requirements-render.txt      Lightweight backend dependencies for Render Free
jobtittle.csv                Job-title frequency/source support file
```

## Important Backend Files

| File | Purpose |
| --- | --- |
| `app/routes.py` | Flask app, REST endpoints, CORS, admin checks, lazy service creation |
| `app/config.py` | Environment variables, paths, startup validation |
| `app/canonical.py` | Canonical data models and loaders |
| `app/skill_normalizer.py` | Skill alias resolution, taxonomy lookup, hard-skill filtering |
| `app/profile_service.py` | Converts quiz/manual payloads into canonical profiles |
| `app/quiz_engine.py` | SQLite-backed adaptive quiz sessions and admin quiz CRUD |
| `app/recommender.py` | Hybrid job ranking and Telegram job scoring |
| `app/gap_analyzer.py` | Technical gap analysis and UI gap formatting |
| `app/learning_path.py` | Resource selection for gaps |
| `app/resource_recommender.py` | Learning resource search and grouping |
| `app/resume_upload.py` | Resume text extraction and improvement analysis |
| `app/resume_generator.py` | Resume preview and downloadable artifact generation |
| `app/telegram_jobs.py` | Telegram post extraction, validation, active-feed filtering |
| `app/analytics.py` | Anonymous event recording and admin rollups |
| `app/migrations.py` | Runtime SQLite migrations |
| `app/reliability.py` | Request IDs, JSON errors, rate limiting |

## Important Frontend Files

| File | Purpose |
| --- | --- |
| `frontend/src/App.jsx` | Custom route selection |
| `frontend/src/components/Layout.jsx` | Header, theme toggle, admin sign out |
| `frontend/src/components/FlowProgress.jsx` | End-to-end flow progress |
| `frontend/src/api/recommend.js` | API calls and session storage helpers |
| `frontend/src/pages/Quiz.jsx` | Adaptive quiz UI |
| `frontend/src/pages/ManualInput.jsx` | Manual technical skill input |
| `frontend/src/pages/Results.jsx` | Match dashboard, high match, gaps, current jobs |
| `frontend/src/pages/SkillGap.jsx` | Gap list view |
| `frontend/src/pages/LearningResources.jsx` | Learning resource groups |
| `frontend/src/pages/ResumeTips.jsx` | Resume coaching display |
| `frontend/src/pages/ResumeBuilder.jsx` | Improved resume builder |
| `frontend/src/pages/TelegramJobs.jsx` | Live job feed with role/skill filter |
| `frontend/src/pages/Admin.jsx` | Admin analytics and content management |
| `frontend/src/utils/roleFilters.js` | Quiz/manual role to live-feed role filter |

## Data and Database

Current local data inventory:

- `data/jobs.csv`: 64,523 job rows with `job_id`, `job_title`, `description`, `category`, `source`, `exp_level`, `job_type`, `location`, `date_added`.
- `jobtittle.csv`: 33,753 job-title frequency rows.
- `data/skills_taxonomy.json`: 246 canonical skills with aliases, domain, category, weight, and tags.
- `data/skill_alias_overrides.json`: manual alias and ignored-term overrides.
- `data/learning_resources.json`: 32 resource entries plus learning-path metadata.
- `data/questions_part1.json` to `data/questions_part5.json`: 67,533 adaptive quiz questions.
- `data/questions_role_interviews.json`: 324 role interview questions.
- `data/telegram_jobs.json`: local Telegram feed snapshot.
- `data/db.sqlite3`: local recommender/admin runtime database.
- `data/jobs.db`: local quiz-session database.

Generated SQLite tables include:

- `jobs`, `job_skills`, `skill_taxonomy`, `learning_resources`
- `quiz_sessions`, `quiz_responses`, `questions`, `domains`, `roles`
- `telegram_posts`
- `user_flow_events`
- `schema_migrations`

Runtime database files and Telegram feed snapshots are ignored by Git. For hosting, either regenerate them during deployment or upload/copy them to the host.

## Local Backend Setup

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Prepare data:

```powershell
python scripts\clean_data.py
python scripts\seed_db.py
```

Optional semantic vector artifacts:

```powershell
python scripts\build_vectors.py
```

Start backend:

```powershell
python -m app.routes
```

Health check:

```text
http://127.0.0.1:5000/health
```

## Local Frontend Setup

In a second terminal:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open:

```text
http://localhost:5173
```

`frontend/.env` should contain:

```text
VITE_API_URL=http://127.0.0.1:5000
```

## Environment Variables

Backend variables are defined in `.env.example`.

Minimum local values:

```text
APP_ENV=development
HOST=127.0.0.1
PORT=5000
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
RUN_MIGRATIONS_ON_STARTUP=1
```

Minimum production values:

```text
APP_ENV=production
HOST=0.0.0.0
PORT=<platform-port>
FLASK_SECRET_KEY=<strong-random-secret>
ADMIN_ACCESS_KEY=<private-admin-key>
CORS_ORIGINS=https://<frontend-domain>
RUN_MIGRATIONS_ON_STARTUP=1
```

Optional:

```text
GROQ_API_KEY=<optional-ai-key>
API_KEY=<optional-api-key>
REQUIRE_API_KEY=0
RATE_LIMIT_ENABLED=1
```

## Tests and Verification

Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

Latest verified result in this workspace:

- Backend: `92 passed, 2 skipped`
- Targeted backend matching/feed tests: `26 passed, 2 skipped`
- Frontend lint: passed
- Frontend build: passed

## Render Free Backend Fix

If Render logs show this pattern:

```text
No open ports detected
Out of memory (used over 512Mi)
Running 'python -m app.routes'
```

the free instance is running out of memory before Flask can bind to the port. The usual cause is installing/importing the full local ML stack (`sentence-transformers`, `torch`, CUDA wheels, and FAISS). The project now avoids importing those packages during startup, and Render should use `requirements-render.txt` instead of the full local development `requirements.txt`.

Use this Render backend build command:

```bash
pip install -r requirements-render.txt && python scripts/seed_db.py
```

Use this Render backend start command:

```bash
python -m app.routes
```

Set these Render environment variables:

```text
APP_ENV=production
HOST=0.0.0.0
PORT=10000
FLASK_SECRET_KEY=<strong-random-secret>
ADMIN_ACCESS_KEY=<private-admin-key>
CORS_ORIGINS=https://<frontend-domain>
RUN_MIGRATIONS_ON_STARTUP=1
RATE_LIMIT_ENABLED=1
```

Optional:

```text
GROQ_API_KEY=<optional-groq-key>
```

Do not run `scripts/build_vectors.py` on Render Free. The deployed backend will use database/lexical fallback matching. That is the correct free-tier mode.

## Free Online Hosting Guide

Recommended free deployment:

- Backend: Render Free Web Service.
- Frontend: Vercel Hobby or Render Static Site.

### Backend on Render

1. Push the project to GitHub.
2. Create a Render Web Service.
3. Select the repository.
4. Set build command:

```bash
pip install -r requirements-render.txt && python scripts/seed_db.py
```

5. Set start command:

```bash
python -m app.routes
```

6. Add the environment variables listed above.
7. Deploy.
8. Test:

```text
https://<backend-name>.onrender.com/health
```

Expected result:

```json
{"status": "ok"}
```

Render Free limitations:

- Cold start after idle spin-down.
- 512 MiB memory limit.
- Ephemeral filesystem, so SQLite writes may not persist after redeploy/restart.
- Use a managed persistent database for a production system.

### Frontend on Vercel

1. Import the GitHub repository into Vercel.
2. Set root directory:

```text
frontend
```

3. Set framework preset:

```text
Vite
```

4. Set build command:

```bash
npm run build
```

5. Set output directory:

```text
dist
```

6. Add frontend environment variable:

```text
VITE_API_URL=https://<backend-name>.onrender.com
```

7. Deploy frontend.
8. Copy the Vercel frontend URL.
9. Update Render backend `CORS_ORIGINS` to that exact frontend URL.
10. Redeploy backend.

### Frontend on Render Static Site

The repository includes `render.yaml` for a two-service Render Blueprint:

- `ai-job-recommender-api`: Flask backend.
- `ai-job-recommender-frontend`: Vite static frontend.

For the frontend service, set:

```text
VITE_API_URL=https://<backend-name>.onrender.com
```

For the backend service, set:

```text
CORS_ORIGINS=https://<frontend-name>.onrender.com
```

If you create the Render Static Site manually instead of using `render.yaml`, add this Redirect/Rewrites rule:

```text
Action: Rewrite
Source: /*
Destination: /index.html
```

Without this rewrite, direct hosted visits to `/results/gap`, `/results/resources`, and other frontend routes can return a Render 404 instead of loading the React app.

### Deployment Smoke Test

Backend:

```bash
curl https://<backend-domain>/health
```

Recommendation:

```bash
curl -X POST https://<backend-domain>/recommend \
  -H "Content-Type: application/json" \
  -d "{\"skills\":[\"Python\",\"SQL\",\"Docker\"],\"experience\":\"mid\",\"category\":\"backend-dev\",\"location\":\"remote\",\"top_n\":3}"
```

Frontend:

1. Open hosted frontend.
2. Complete manual input or quiz.
3. Confirm matched jobs appear.
4. Open gaps/resources.
5. Build resume.
6. Open `/admin` and sign in with `ADMIN_ACCESS_KEY`.

