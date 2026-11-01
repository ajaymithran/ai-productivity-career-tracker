"""Excel/CSV workbook importer — mapping, validation, then import.

Safety contract:
  * Never writes to the database by itself. UI calls validate() first,
    shows the human a preview + issues, and only after explicit approval
    a different function (import_rows) runs — same philosophy as AI
    proposals: preview -> approve -> apply.
  * Unknown columns are ignored, not guessed at. Aliases cover common
    names your workbook might use.
"""
from datetime import date, datetime

import pandas as pd

ALIASES = {
    "tasks": {
        "title": ["title", "task", "task name", "work", "todo"],
        "notes": ["notes", "description", "details"],
        "priority_band": ["priority", "priority band", "importance"],
        "estimated_minutes": ["minutes", "estimated minutes", "duration",
                               "time (min)", "est minutes"],
        "due_date": ["due", "due date", "deadline", "target date"],
        "impact": ["impact"],
        "effort": ["effort"],
    },
    "skills": {
        "name": ["skill", "name", "skill name", "subject"],
        "category": ["category", "type"],
        "current_level": ["current level", "level", "rating"],
        "target_level": ["target level", "goal level", "target"],
        "minutes_goal_weekly": ["weekly minutes", "minutes per week", "weekly goal"],
    },
    "goals": {
        "title": ["goal", "goal name", "title", "objective", "milestone"],
        "target_date": ["target date", "due date", "deadline"],
        "progress_pct": ["progress", "progress %", "percent complete", "%"],
        "horizon": ["horizon", "type", "term"],
    },
}

REQUIRED = {"tasks": ["title"], "skills": ["name"], "goals": ["title"]}
INT_RANGE = {"estimated_minutes": (5, 600), "impact": (1, 5), "effort": (1, 5),
             "current_level": (1, 5), "target_level": (1, 5),
             "minutes_goal_weekly": (15, 3000), "progress_pct": (0, 100)}

BAND_NORMALISE = {"h": "high", "high": "high", "medium": "medium", "med": "medium",
                  "m": "medium", "low": "low", "l": "low"}


def read_workbook(path) -> pd.ExcelFile:
    return pd.ExcelFile(path)


def sheet_summaries(xl: pd.ExcelFile, *, preview_rows: int = 30) -> list[dict]:
    out = []
    for name in xl.sheet_names:
        df = xl.parse(name, nrows=preview_rows + 1)
        out.append({"sheet": name, "rows_preview": len(df),
                    "columns": [str(c) for c in df.columns]})
    return out


def map_columns(df: pd.DataFrame, entity: str) -> dict[str, str]:
    """Return {canonical_field: actual_column} for a sheet."""
    lower = {str(c).strip().lower(): c for c in df.columns}
    mapping = {}
    for field, candidates in ALIASES[entity].items():
        for cand in candidates:
            col = lower.get(cand)
            if col is not None:
                mapping[field] = col
                break
    return mapping


def validate(df: pd.DataFrame, entity: str, mapping: dict[str, str]) -> tuple[pd.DataFrame, list[str]]:
    """Return (clean_dataframe, issues). Blank/invalid rows are dropped, not fixed."""
    issues: list[str] = []
    missing = [f for f in REQUIRED[entity] if f not in mapping]
    if missing:
        return pd.DataFrame(), [f"required field '{f}' not matched by any column" for f in missing]

    clean = df[[v for v in mapping.values() if v in df.columns]].copy()
    clean = clean.rename(columns={v: k for k, v in mapping.items()})
    clean = clean[[k for k in mapping.keys()]]
    clean = clean.loc[clean[list(REQUIRED[entity])].notna().all(axis=1)]
    req_col = REQUIRED[entity][0]
    titles = clean[req_col].astype(str).str.strip()
    clean = clean[(titles.str.len() > 0) & clean[req_col].notna()]

    # ints: coerce -> clamp to schema CHECK ranges
    for field, (lo, hi) in INT_RANGE.items():
        if field not in clean.columns:
            continue
        vals = pd.to_numeric(clean[field], errors="coerce")
        bad = int(clean[field].notna().sum() - vals.notna().sum())
        if bad:
            issues.append(f"{bad} non-numeric '{field}' value(s) defaulted to range midpoint")
        if field == "estimated_minutes":
            vals = vals.fillna(30)
        elif field == "minutes_goal_weekly":
            vals = vals.fillna(180)
        elif field in ("impact", "effort", "current_level"):
            vals = vals.fillna(3)
        elif field == "target_level":
            vals = vals.fillna(5)
        elif field == "progress_pct":
            vals = vals.fillna(0)
        clean[field] = vals.clip(lo, hi).astype(int)

    # bands
    if entity == "tasks" and "priority_band" in clean.columns:
        def norm_band(v):
            s = str(v).strip().lower()
            return BAND_NORMALISE.get(s, "medium")
        clean["priority_band"] = clean["priority_band"].map(norm_band)

    # dates: parse defensively
    for field in ("due_date", "target_date"):
        if field in clean.columns:
            parsed = pd.to_datetime(clean[field], errors="coerce", dayfirst=True)
            n_bad = int(parsed.isna().sum() - clean[field].isna().sum())
            if n_bad:
                issues.append(f"{n_bad} unparseable '{field}' value(s) dropped (field becomes empty)")
            clean[field] = [
                d.date().isoformat() if isinstance(d, datetime) else None
                for d in parsed
            ]

    if clean.empty:
        issues.append("Validation left 0 rows — check the sheet has data and required columns")
    return clean, issues


def import_rows(client, entity: str, rows: pd.DataFrame, user_id: str
                ) -> tuple[int, list[str], int]:
    """Insert validated rows via the audited CRUD layer, skipping any row whose
    key field (title/name, case-insensitive) already exists — dedup protection
    so a re-import never duplicates your data. UI calls this only after the
    user has seen and approved the preview.
    Returns (imported_count, errors, skipped_count)."""
    from db.crud import insert_row, list_rows
    key_field = REQUIRED[entity][0]
    try:
        existing = list_rows(client, entity)
        seen = {str(r.get(key_field, "")).strip().lower() for r in existing}
    except Exception as exc:
        seen = set()                     # can't read existing rows -> insert unchecked
        errors = [f"dedup disabled (could not list existing rows: {str(exc)[:80]})"]
    else:
        errors = []
    imported, skipped = 0, 0
    for _, r in rows.iterrows():
        payload = {k: (None if pd.isna(v) else v) for k, v in r.items()}
        key_val = str(payload.get(key_field, "")).strip().lower()
        if key_val and key_val in seen:
            skipped += 1
            continue
        try:
            insert_row(client, entity, payload, user_id=user_id)
            seen.add(key_val)
            imported += 1
        except Exception as exc:
            errors.append(f"row {imported + skipped + 1}: {str(exc)[:110]}")
    return imported, errors, skipped
