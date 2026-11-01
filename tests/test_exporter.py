"""Excel exporter: honest multi-sheet workbook built in every mode
(tested in demo mode with monkeypatched source.mode)."""
import io

import pandas as pd


def test_export_all_xlsx_builds_workbook(monkeypatch):
    import data.source as source
    monkeypatch.setattr(source, "mode", lambda: "demo")

    from core.exporter import export_all_xlsx
    data = export_all_xlsx()

    assert isinstance(data, bytes) and len(data) > 1000
    xl = pd.ExcelFile(io.BytesIO(data))
    expected_sheets = ["_meta", "tasks", "projects", "milestones", "skills",
                       "goals", "career_milestones", "english_logs", "notifications"]
    for sheet in expected_sheets:
        assert sheet in xl.sheet_names, f"missing sheet {sheet}"

    meta = pd.read_excel(io.BytesIO(data), sheet_name="_meta")
    assert meta.loc[0, "data_mode"] == "demo"
    assert "generated_at" in meta.columns
