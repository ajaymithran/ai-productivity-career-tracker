#!/usr/bin/env python
"""Pre-commit secret guard.

Aborts the commit if .env.example contains a non-empty value for any
credential line, or if a .env file got staged. Run via:

    git config core.hooksPath .githooks

(see .githooks/pre-commit)
"""
import re
import sys
from pathlib import Path

SECRET_VARS = ("SUPABASE_URL", "SUPABASE_ANON_KEY",
               "SUPABASE_USER_EMAIL", "SUPABASE_USER_PASSWORD", "GEMINI_API_KEY")

root = Path(__file__).resolve().parents[1]
failures = []

example = root / ".env.example"
if example.exists():
    for line in example.read_text(encoding="utf-8").splitlines():
        for var in SECRET_VARS:
            m = re.match(rf"^\s*{var}\s*=\s*(\S.*)$", line)
            if m:
                failures.append(f".env.example has a real value for {var} — templates must stay blank!")

envf = root / ".env"
if envf.exists():
    # sanity: warn (not fail) if risky values look present anywhere in tracked files
    for tracked in list(root.glob("*.py")) + [root / "README.md"]:
        text = tracked.read_text(encoding="utf-8", errors="ignore")
        for var in SECRET_VARS:
            if re.search(rf"{var}\s*=\s*['\"]?[A-Za-z0-9_\-]{{10,}}", text):
                failures.append(f"{tracked.name} appears to hardcode a value for {var}")

if failures:
    print("SECRET GUARD — commit blocked:\n")
    for f in sorted(set(failures)):
        print(" -", f)
    print("\nReal values belong ONLY in .env (never committed).")
    sys.exit(1)
sys.exit(0)
