"""AppTest smoke: render every page's render() under a real Streamlit runner
and report exceptions — the browser-level check that HTTP 200 can't do."""
import pathlib
import sys
import traceback

from streamlit.testing.v1 import AppTest

REPO = str(pathlib.Path(__file__).resolve().parents[1])

PAGES = ["dashboard", "planner", "projects", "skills", "roadmap",
         "ai_coach", "analytics", "settings"]

failures = []
for name in PAGES:
    script = (
        f"import sys; sys.path.insert(0, {REPO!r})\n"
        f"from ui import {name}\n"
        f"{name}.render()\n"
    )
    at = AppTest.from_string(script, default_timeout=60)
    try:
        at.run()
        excs = list(at.exception)
        if excs:
            failures.append((name, excs[0].value, excs[0].stack_trace))
            print(f"PAGE {name}: EXCEPTION -> {excs[0].value}")
        else:
            print(f"PAGE {name}: OK "
                  f"(errors_on_page={len(at.error)})")
    except Exception:
        failures.append((name, "AppTest crash", traceback.format_exc()))
        print(f"PAGE {name}: APPTEST CRASH")

print("\n==== SUMMARY ====")
if failures:
    for name, value, stack in failures:
        print(f"\n--- {name} ---\n{value}\n{stack}")
    sys.exit(1)
print(f"ALL {len(PAGES)} PAGES RENDER CLEAN")
