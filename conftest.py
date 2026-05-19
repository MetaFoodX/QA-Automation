"""Root pytest configuration for QA-Automation.

pytest auto-discovers this file (no import needed). Code here runs once
before any test in this project. Use it for:

  - Loading environment variables from .env
  - Making fixtures from `fixtures/` discoverable
  - Registering hooks (e.g. screenshot on failure)

Tests do NOT import from this file directly.
"""

from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root before pytest collects any tests.
# This must happen at module import time so os.getenv(...) works everywhere.
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")


# -----------------------------------------------------------------------------
# Fixture re-exports — added later as we build out fixtures/
# -----------------------------------------------------------------------------
# from fixtures.browser_fixtures import *  # noqa: F401, F403
# from fixtures.auth_fixtures import *     # noqa: F401, F403