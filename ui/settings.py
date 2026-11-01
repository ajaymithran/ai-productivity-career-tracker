"""Settings — study availability, preferences, AI settings, backup/export."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from db import crud


@st.cache_resource
def _sup():
    from db.client import get_supabase
    return get_supabase()


EXPORT_TABLES = ["tasks", "projects", "milestones", "goals", "skills",
                 "daily_plans", "daily_plan_items", "english_logs",
                 "weekly_reviews", "job_readiness", "activity_logs", "ai_proposals"]


def _ensure_settings(client, uid: str) -> dict:
    rows = crud.list_rows(client, "user_settings")
    if rows:
        return rows[0]
    return crud.insert_row(client, "user_settings",
                           {"daily_study_minutes": 120,
                            "study_start_time": "06:30",
                            "study_end_time": "22:00",
                            "weekly_review_day": 0,
                            "theme": "light",
                            "ai_enabled": True,
                            "ai_tone": "mentor"}, user_id=uid)


def render() -> None:
    st.header("⚙️ Settings")
    st.caption("Preferences live in the database; backups live on YOUR disk.")

    client, err = _sup()
    if err:
        st.warning(err)
        return
    from db import queries
    uid = queries.current_user_id(client)
    s = _ensure_settings(client, uid)

    left, right = st.columns([3, 2])

    # ----- study availability -----
    with left:
        st.subheader("⏰ Study availability")
        with st.form("availability", border=True):
            c1, c2 = st.columns(2)
            mins = c1.number_input("Daily study minutes", 15, 720,
                                   s.get("daily_study_minutes", 120), 15)
            start = c2.time_input("Study window opens", value=None)
            c3, c4 = st.columns(2)
            end = c3.time_input("Study window closes", value=None)
            day = c4.selectbox("Weekly review day",
                               ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                               index=s.get("weekly_review_day", 0))
            # index list: Sun=0..Sat=6 (form value)
            if st.form_submit_button("Save availability", type="primary"):
                crud.update_row(client, "user_settings", uid,
                                {"daily_study_minutes": int(mins),
                                 "study_start_time": start.strftime("%H:%M"),
                                 "study_end_time": end.strftime("%H:%M"),
                                 "weekly_review_day": ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].index(day)},
                                user_id=uid)
                st.success("Saved — the planner and AI coach will respect this.")
                st.rerun()

        st.subheader("🤖 AI preferences")
        with st.form("ai_pref", border=True):
            ai_on = st.checkbox("Enable AI features (Gemini)", s.get("ai_enabled", True))
            tone = st.select_slider("Coach tone", ["mentor", "concise", "drill_sergeant"],
                                    s.get("ai_tone", "mentor"))
            if st.form_submit_button("Save AI settings"):
                crud.update_row(client, "user_settings", uid,
                                {"ai_enabled": bool(ai_on), "ai_tone": tone}, user_id=uid)
                st.rerun()
        st.caption("Note: the theme switch lives in Streamlit's own menu (☰ → Settings → Theme). "
                   "Your choice is remembered browser-side by Streamlit, and the colour palette "
                   "already keeps text readable in both.")

    # ----- backup / export -----
    with right:
        st.subheader("💾 Backup — export CSV")
        st.caption("Downloads a CSV snapshot of each table. Keep copies outside this folder.")
        pick = st.selectbox("Table", EXPORT_TABLES)
        if st.button("Download CSV"):
            try:
                rows = crud.list_rows(client, pick)
                if not rows:
                    st.warning("That table is empty — nothing to export yet.")
                else:
                    csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
                    fname = f"{pick}_{date.today().isoformat()}.csv"
                    st.download_button("⬇️ Save file", csv, file_name=fname,
                                       mime="text/csv", key=f"dl_{pick}")
            except Exception as exc:
                st.error(f"Export failed: {str(exc)[:160]}")

        st.divider()
        st.subheader("📗 Excel workbook import")
        st.caption("Preview → map → validate → **you approve** → import. The original "
                   "workbook is never modified.")
        file = st.file_uploader("Upload your workbook (.xlsx)", type=["xlsx", "xls"],
                                key="wbupload")
        if file:
            from core import importer
            try:
                xl = importer.read_workbook(file)
                sheet = st.selectbox("Sheet", xl.sheet_names,
                                     format_func=lambda s: str(s))
                entity = st.selectbox("Import as", ["tasks", "skills", "goals"],
                                      format_func=str.capitalize)
                df = xl.parse(sheet)
                mapping = importer.map_columns(df, entity)
                st.caption("Column mapping:")
                st.write({f: c for f, c in mapping.items()} or "No columns matched this entity.")
                clean, issues = importer.validate(df, entity, mapping)
                for msg in issues:
                    st.warning(msg)
                if clean.empty:
                    st.info("Nothing to import from this sheet as it stands.")
                else:
                    st.caption(f"{len(clean)} row(s) ready:")
                    st.dataframe(clean.head(8), hide_index=True)
                    confirm = st.checkbox("I reviewed the preview — import these rows")
                    if confirm and st.button("Import to database", type="primary",
                                             key="wbimport"):
                        imported, errs = importer.import_rows(client, entity, clean, uid)
                        st.success(f"Imported {imported} row(s) — each is in activity_logs.")
                        for e in errs:
                            st.error(e)
            except Exception as exc:
                st.error(f"Could not read workbook: {str(exc)[:200]}")

        st.divider()
        st.caption("Free-tier reminder: Supabase pauses projects after ~1 week without "
                   "activity — opening this app counts as activity.")
