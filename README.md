# AI Productivity & Career Tracker

A personal, single-user web app that centralizes daily tasks, projects, skills, career goals, study analytics, and AI-generated coaching — built to be run on a laptop and (optionally) deployed for free.

Current version: **v3.0** (persistence hardening, approval workflow, automation package, real exports/imports).

## Stack & principles

- **Python / Streamlit** — UI + all application logic
- **Supabase PostgreSQL** — 15-table schema + `approval_history`, Row Level Security, FKs, constraints, indexes
- **SQLite (stdlib)** — local persistence mode: zero-credential, survives restarts (`tracker_local.db`)
- **Pandas / OpenPyXL / Plotly** — Excel import/export & interactive charts
- **Gemini (free tier)** — suggestions & explanations ONLY; the tracker is fully functional without AI
- **GitHub Actions** — daily deadline notices & weekly-review nudges, delivered **in-app only**
- **Pytest** — 52 tests, no paid API required (AI calls are mocked)

Design rules enforced by the code and the database:
1. **Python decides, AI explains** — priority scoring, capacity math, deadline warnings are deterministic (`core/`); Gemini never computes.
2. **Nothing silent changes your data** — AI output is stored as *pending*; only your ✅/✏️/❌ decision finalizes it, and every decision is permanently logged in `approval_history` (append-only in the database) + `activity_logs`.
3. **Fail softly** — missing config shows guidance, never a crash.
4. **One door for secrets** — env vars are read only in `config/settings.py`; `.env` is git-ignored, `.env.example` is always blank in the repo (a pre-commit hook enforces this).

## Architecture (what lives where)

```
app.py                  navy sidebar shell + page router
ui/                     8 pages (dashboard, planner, projects, skills, roadmap, ai_coach, analytics, settings)
ui/components/ui_kit.py reusable cards/forms/notifications (pages never copy-paste)
core/                   deterministic logic: priority scoring, scheduler, importer, exporter
ai/                     Gemini client (configurable model) + prompts
db/                     Supabase client + queries + generic audited CRUD
src/database/           local_store.py — SQLite persistence adapter
src/services/           approvals.py — the approval-enforcement service
automation/             workflows.py — idempotent daily/weekly jobs
data/                   data source abstraction (live/local/demo) + sample data
database/schema.sql     15-table schema + RLS
database/migrations/    incremental SQL (001_approval_history.sql)
scripts/                daily_job.py (GH Actions), check_auth.py, verify_db.py, check_secrets.py
tests/                  pytest suite (mocked AI, temp SQLite — never your real data)
```

Key decision — **three data modes** (`data/source.py` is the single router):
- `live` → Supabase, authenticated; RLS scopes every row to you
- `local` → SQLite at `tracker_local.db`; persistent without any cloud credentials
- `demo` → session-memory sample data, clearly labelled; resets on refresh

Pages never touch a store directly — all loads and mutations go through `data/source.py`, and task changes fire an event hook that refreshes deadline notifications.

## Local setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env    # then fill values (template stays blank in git)
streamlit run app.py
```

Required `.env` values for **live** mode: `SUPABASE_URL`, `SUPABASE_ANON_KEY` (publishable), `SUPABASE_USER_EMAIL`, `SUPABASE_USER_PASSWORD` (your one app user), optional `GEMINI_API_KEY`, optional `GEMINI_MODEL` (default `gemini-2.5-flash` — name it explicitly because "3.5-flash" is not a real Gemini model ID).
**Without** credentials the app runs in **local mode** automatically: same UI, persistent SQLite on your machine.

## What's verified vs. not (honest ledger)

**Implemented and tested locally (pytest, no network):**
- 8 pages boot and navigate (headless Streamlit HTTP 200 check)
- Task create/update/complete/delete with priority scoring; deadline validation
- Approval workflow: reject leaves plan unchanged; unapproved activation raises `PermissionError`; latest decision wins; decision history persists
- Local SQLite persistence across restarts; notification idempotency (retries add nothing)
- Excel export (9-sheet workbook) and importer mapping/validation with duplicate-skipping
- AI degradation without a key (honest fallback, never a crash); mocked provider path
- 52 automated tests green

**Requires YOUR actions (not yet verified):**
- Run `database/migrations/001_approval_history.sql` in Supabase SQL Editor (creates the append-only decision ledger; safe to re-run)
- Rotate the leaked Supabase app-user password (Authentication → Users), rotate `GEMINI_API_KEY` at aistudio.google.com, and keep both in `.env` only
- Add GitHub repo secrets (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_USER_EMAIL`, `SUPABASE_USER_PASSWORD`) for the Actions job
- Drop `ajay_career_tracking.xlsx` into `backups/` so the importer can be verified against your real workbook (it does **not** exist in the repo yet — importer stays generic until then)

**Tested against the real cloud earlier, re-verify after rotation:** Supabase sign-in + RLS isolation (`scripts\check_auth.py`, `scripts\verify_db.py`).

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -q
.\.venv\Scripts\python.exe scripts\check_auth.py     # sign-in diagnostic (needs .env creds)
.\.venv\Scripts\python.exe scripts\verify_db.py      # tables + RLS check (needs creds)
.\.venv\Scripts\python.exe -m pytest tests\ ; streamlit run app.py   # full smoke
```

## Automation (optional)

`scripts/daily_job.py` calls the same `automation.workflows.run_all()` used by the app: deadline notices (overdue/today/3-day) + a weekly-review nudge on your configured day. Idempotent — same type+title+day is never duplicated, so retries are safe. Add the four repo secrets, then `.github/workflows/daily-assistant.yml` (cron 16:15 UTC) writes notices into the `notifications` table, shown only inside the app. **No e-mail/SMS/Telegram/WhatsApp — by design.**

## Excel migration

Put your workbook (e.g. `ajay_career_tracking.xlsx`) anywhere; in Settings → Import, upload it, pick the sheet and target (tasks/skills/goals). The importer shows the column mapping and a preview; nothing lands until you tick "I reviewed the preview" and press Import. Duplicates are skipped automatically and the run reports imported/skipped/errors. Export: "Export all to Excel" writes a dated multi-sheet `.xlsx` of every table.

## Deployment (free): Streamlit Community Cloud

1. Push this repo.
2. share.streamlit.io → New app → pick repo → `app.py`.
3. In the app's **Settings → Secrets**, paste the same key/value pairs as `.env` (TOML format).
4. Notes: the app sleeps when idle (first load after sleep is slow); secrets live only in the Secrets UI.

## Free-tier limits (honest)

- **Supabase:** 500 MB, 2 projects, pauses after ~1 week inactivity (opening the app counts).
- **Gemini free:** limited daily requests; the Coach is one call per click — fine. When the key/quota fails, the app says so and uses the deterministic fallback.
- **Actions:** seconds per run / 2,000 free minutes monthly — effectively unlimited here.
- **Streamlit Cloud:** sleep-on-idle; public URL; keep real secrets in the Secrets UI, never in code.

## Troubleshooting

- **"SECRET GUARD — commit blocked"** — you pasted a real value into `.env.example`. Move it to `.env` and blank the template; the hook is doing its job.
- **AI Coach shows "not configured"** — `GEMINI_API_KEY` missing/invalid in `.env`; the page still works via the deterministic fallback.
- **Sign-in errors** — run `scripts\check_auth.py`; the usual cause is the leaked password that hasn't been rotated yet.
- **Data gone after refresh?** — you were in demo mode (labelled 🧪). Use local or live mode for persistence.
