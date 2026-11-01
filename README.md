# AI Productivity & Career Tracker

A personal, single-user web app that centralizes daily tasks, projects, skills, career goals, study analytics, and AI-generated coaching — built to be run on a laptop and (optionally) deployed for free.

## Stack & principles

- **Python / Streamlit** — UI + all application logic
- **Supabase PostgreSQL** — 15-table schema, Row Level Security, FKs, constraints, indexes
- **Pandas / Plotly** — data handling & interactive charts
- **Gemini (free tier)** — suggestions & explanations ONLY; the tracker is fully functional without AI
- **GitHub Actions** — daily deadline notices & weekly-review nudges, delivered **in-app only**

Design rules enforced by the code and the database:
1. **Python decides, AI explains** — priority scoring, capacity math, deadline warnings are deterministic (`core/`); Gemini never computes.
2. **Nothing silent changes your data** — AI output is stored as a *pending proposal*; only your ✅/❌ decision is final, and both are permanently logged in `ai_proposals` + `activity_logs`.
3. **Fail softly** — missing config shows guidance, never a crash.
4. **One door for secrets** — env vars are read only in `config/settings.py`; `.env` is git-ignored, `.env.example` is always blank in the repo.

## Features

| Module | Highlights |
|---|---|
| Dashboard | KPI cards, top priorities, live deadline notices, skill-gap bars, goal progress |
| Daily Planner | Task CRUD (priority band, impact/effort, due dates), **time allocation validated against availability** |
| Projects | Milestones with blockers, GitHub links, progress bars |
| Skills | Level targets per skill, Plotly gap analysis, English practice logs |
| Career Roadmap | Goals, weekly reviews, job-readiness score (deterministic formula) |
| AI Coach | Shows the exact context JSON, generates plans/reviews, pending→approve/reject audit trail |
| Analytics | Study minutes, completion streaks, status split, English weekly split |
| Settings | Study availability, AI prefs, CSV export of every table, **Excel workbook import with preview & approval** |

## Local setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env    # then fill in values
streamlit run app.py
```

Required `.env` values: `SUPABASE_URL`, `SUPABASE_ANON_KEY` (publishable), `SUPABASE_USER_EMAIL`, `SUPABASE_USER_PASSWORD` (your one app user), optional `GEMINI_API_KEY`.

## Verify

```powershell
.\.venv\Scripts\python.exe scripts\check_auth.py     # sign-in diagnostic
.\.venv\Scripts\python.exe scripts\verify_db.py      # 15 tables + RLS check
.\.venv\Scripts\python.exe -m pytest tests\ -v       # 26 tests
```

## Automation (optional)

Add repo secrets `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_USER_EMAIL`, `SUPABASE_USER_PASSWORD`, then let `.github/workflows/daily-assistant.yml` run daily (cron 16:15 UTC) — it writes deadline & weekly-review notices into the `notifications` table, shown only inside the app.

## Deployment (free): Streamlit Community Cloud

1. Push this repo (done), fork nothing needed.
2. share.streamlit.io → New app → pick repo → `app.py`.
3. In the app's **Settings → Secrets**, paste the same key/value pairs as `.env` (TOML format).
4. Notes: the app sleeps when idle (first load after sleep is slow); your `.env` is never needed in the repo.

## Free-tier limits (honest)

- **Supabase:** 500 MB, 2 projects, pauses after ~1 week inactivity (opening the app counts).
- **Gemini free:** limited daily requests; AI Coach is one call per click — fine.
- **Actions:** seconds per run/monthly 2,000 free minutes — effectively unlimited here.
- **Streamlit Cloud:** sleep-on-idle; public URL; keep real secrets in the Secrets UI, never in code.

## Status

- [x] Task 1 — skeleton, config layer, themed shell
- [x] Task 2 — Git/GitHub, pytest, README
- [x] Task 3 — 15-table schema (RLS, indexes, triggers)
- [x] Task 4 — Supabase live, RLS verified
- [x] Tasks 5–8 — Planner, Projects, Skills, Roadmap
- [x] Tasks 9–10 — AI Coach (approval flow), Analytics, Settings
- [x] Workbook importer (preview → approve → apply)
- [x] Daily/weekly automation via GitHub Actions
- [ ] Your one-time setup: fix the app-user sign-in (run `scripts\check_auth.py`), add repo secrets, optional cloud deploy
