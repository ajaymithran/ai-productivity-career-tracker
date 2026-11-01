"""Pytest configuration.

Adds the project root to sys.path so tests can `import config`, `import core`,
etc. regardless of where pytest is launched from. Without this, pytest only
puts the tests/ folder on the path and `config.settings` wouldn't be found.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
