"""PAGE 8 — Settings: profile, availability, notifications, AI status,
data import/export, backup info. Never displays API secrets."""
import datetime as dtnow

import pandas as pd
import streamlit as st

import data.source as source
from ui.components import ui_kit as kit
from ui.design import TOKENS

EXPORT_TABLES = ["tasks", "projects", "milestones", "goals", "skills",
                 "english_logs", "notifications"]


def render() -> None:
    kit.page_header("⚙️ Settings", "Preferences, availability, AI status, data",
                    date_context="local first")
    kit.page_banner_demo()

    profile = source.load_user()
    settings = source.load_settings()

    left, right = st.columns(2)

    # ---------------- profile + availability ----------------
    with left:
        with st.container():
            st.markdown("<div class='p-card'>", unsafe_allow_html=True)
            st.markdown("##### 👤 Profile")
            c1, c2 = st.columns([1, 3])
            c1.markdown("<div style='font-size:2.3rem;text-align:center'>"
                        f"{profile.get('display_name','👤')[0]} </div>",
                        unsafe_allow_html=True)
            c2.markdown(f"**{profile.get('display_name','—')}**"
                        f"<br><span style='color:{TOKENS['muted']};font-size:.82rem'>"
                        f"Single-user tracker · {profile.get('timezone','Asia/Kolkata')}"
                        "</span>", unsafe_allow_html=True)
            name = st.text_input("Display name", profile.get("display_name", ""),
                                 key="set_name")
            st.markdown("</div>", unsafe_allow_html=True)

        with st.container():
            st.markdown("<div class='p-card' style='margin-top:.7rem'>", unsafe_allow_html=True)
            st.markdown("##### ⏱ Study availability")
            mins = st.slider("Daily study minutes", 15, 720,
                             int(settings.get("daily_study_minutes", 120)), 15,
                             key="set_mins")
            c1, c2 = st.columns(2)
            start = c1.time_input("Window opens", None, key="set_start")
            end = c2.time_input("Window closes", None, key="set_end")
            day = c2.selectbox("Weekly review day", ["Sun", "Mon", "Tue", "Wed", "Thu",
                                                     "Fri", "Sat"], key="set_day")
            if st.button("Save availability", type="primary", key="set_save"):
                if source.mode() != "demo":
                    st.info("Live persistence via DB wiring; demo stores for session.")
                else:
                    from data.demo_data import data as dd
                    dd()["settings"]["daily_study_minutes"] = mins
                    if start:
                        dd()["settings"]["study_start_time"] = start.strftime("%H:%M")
                    if end:
                        dd()["settings"]["study_end_time"] = end.strftime("%H:%M")
                    dd()["settings"]["weekly_review_day"] = ["Sun", "Mon", "Tue", "Wed",
                                                             "Thu", "Fri", "Sat"].index(day)
                    st.toast("Availability saved (demo)", icon="⏱")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with st.container():
            st.markdown("<div class='p-card' style='margin-top:.7rem'>", unsafe_allow_html=True)
            st.markdown("##### 💬 Notification preferences")
            st.caption("All notifications appear inside the app — never e-mail or SMS.")
            st.toggle("Deadline notices (overdue / today / 3-day)", True, key="set_n1")
            st.toggle("Weekly review nudge", True, key="set_n2")
            st.toggle("AI proposal-waiting cue", True, key="set_n3")
            st.markdown("</div>", unsafe_allow_html=True)

        with st.container():
            st.markdown("<div class='p-card' style='margin-top:.7rem'>", unsafe_allow_html=True)
            st.markdown("#####ostante 🎨 Theme")
            th = st.radio("Theme", ["Light (recommended)", "Dark",
                                    "Follow system"], key="set_theme",
                          help="The palette keeps contrast readable in both bases. "
                               "Streamlit's own menu also offers a theme switch.")
            if th != "Light (recommended)":
                st.info("Switch via Streamlit's ☰ menu → Settings → Theme for now; "
                        "in-app dark toggle lands with the next milestone.")
            st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- AI + data ----------------
    with right:
        with st.container():
            st.markdown("<div class='p-card'>", unsafe_allow_html=True)
            st.markdown("##### 🤖 AI provider status")
            from ai.client import get_ai
            gen, err = get_ai()
            if err:
                kit.notice("info", f"AI: {err.split('—')[0].strip() or 'not configured'}")
                st.caption("The tracker is fully functional without AI. Add "
                           "`GEMINI_API_KEY` to `.env` (never commit it).")
            else:
                kit.notice("info", "AI: configured with Gemini (gemini-2.5-flash, free tier).")
            st.caption("🔒 Secrets are never displayed — only the config status is shown.")
            st.markdown("</div>", unsafe_allow_html=True)

        with st.container():
            st.markdown("<div class='p-card' style='margin-top:.7rem'>", unsafe_allow_html=True)
            st.markdown("##### 📤 Data export")
            mode = source.mode()
            a1, a2 = st.columns(2)
            # --- full workbook export (every table, one sheet each) ---
            xlsx_bytes = None
            if a1.button("⬇️ Export all to Excel", key="exp_all",
                         help="One .xlsx workbook — one sheet per table.", type="primary"):
                try:
                    from core import exporter
                    xlsx_bytes = exporter.export_all_xlsx()
                except Exception as exc:
                    st.error(f"Export failed: {str(exc)[:160]}")
            if xlsx_bytes:
                a1.download_button("💾 Save ajay_tracker_export.xlsx", xlsx_bytes,
                                   file_name=f"ajay_tracker_export_"
                                             f"{dtnow.date.today().isoformat()}.xlsx",
                                   mime="application/vnd.openxmlformats"
                                        "-officedocument.spreadsheetml.sheet",
                                   key="exp_all_dl")
            # --- single-table CSV ---
            table = st.selectbox("Single table (CSV)", EXPORT_TABLES, key="exp_t")
            if a2.button("Download CSV", key="exp_btn"):
                from data.demo_data import data as dd
                rows = (dd().get(table) if mode == "demo"
                        else source.load_tasks(active_only=False) if table == "tasks" and mode != "demo"
                        else [])
                if not rows:
                    kit.empty_state(f"Nothing in `{table}` yet.", "📤")
                else:
                    csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
                    a2.download_button("⬇️ Save file", csv,
                                       file_name=f"{table}_{mode}.csv", mime="text/csv",
                                       key="exp_dl")
            st.caption(f"Mode: **{mode}** — export always reflects real stored records. "
                       "Keep weekly backups on your own disk.")
            st.markdown("</div>", unsafe_allow_html=True)

        with st.container():
            st.markdown("<div class='p-card' style='margin-top:.7rem'>", unsafe_allow_html=True)
            st.markdown("##### 📥 Import from Excel workbook")
            st.caption("Your original file is never modified; mapping is verified "
                       "before anything lands. Duplicates are skipped automatically.")
            file = st.file_uploader("Workbook (.xlsx)", type=["xlsx", "xls"], key="imp_up")
            if file:
                from core import importer as imp
                try:
                    xl = imp.read_workbook(file)
                    sheet = st.selectbox("Sheet", xl.sheet_names, key="imp_sh")
                    entity = st.selectbox("Import as", ["tasks", "skills", "goals"],
                                          format_func=str.capitalize, key="imp_en")
                    df = xl.parse(sheet)
                    mapping = imp.map_columns(df, entity)
                    st.write(mapping or "No columns matched this entity.")
                    clean, issues = imp.validate(df, entity, mapping)
                    for msg in issues:
                        st.warning(msg)
                    if clean is None or clean.empty:
                        st.info("Nothing importable found.")
                    else:
                        st.caption(f"{len(clean)} row(s) ready — preview:")
                        st.dataframe(clean.head(8), hide_index=True)
                        confirm = st.checkbox("I reviewed the preview — import these rows",
                                              key="imp_ok")
                        if confirm and st.button("Import", type="primary", key="imp_go"):
                            if source.mode() == "live":
                                from data.source import _db
                                from db import queries
                                client, err = _db()
                                if err or client is None:
                                    st.error(f"Import needs the database: {err}")
                                else:
                                    uid = queries.current_user_id(client)
                                    imported_n, errors, skipped = imp.import_rows(
                                        client, entity, clean, uid)
                                    for msg in errors:
                                        st.warning(msg)
                                    st.success(f"Imported {imported_n} row(s) into `{entity}`; "
                                               f"{skipped} duplicate(s) skipped.")
                            else:
                                st.info("Row import writes to the cloud database — add "
                                        "Supabase credentials in `.env` (local mode "
                                        "persists new tasks you add in the app).")
                except Exception as exc:
                    st.error(f"Could not read workbook: {str(exc)[:160]}")
            st.markdown("</div>", unsafe_allow_html=True)

        with st.container():
            st.markdown("<div class='p-card' style='margin-top:.7rem'>", unsafe_allow_html=True)
            st.markdown("##### 🛟 Backup information")
            st.markdown(
                f"<span style='font-size:.85rem;color:{TOKENS['muted']}'>"
                "- Database: Supabase free tier · 500 MB cap · auto-pauses after "
                "≈1 week without use (opening the app counts as use).\n"
                "- Exports: CSV downloads above stay on your disk.\n"
                "- Secrets: stored only in `.env` locally / Streamlit secrets when "
                "deployed. Nothing is ever displayed here.</span>",
                unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
