"""Auth fixtures: log in once per session, replay storage state per test."""
import os
import re
from pathlib import Path

import pytest
import yaml

from shared.config.settings import settings
from dashboard.pages.login_page import LoginPage

AUTH_STATE_DIR = Path(__file__).parent.parent / ".auth-state"
USERS_FILE = Path(__file__).parent.parent.parent / "shared" / "data" / "users.yaml"
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _resolve(value: str) -> str:
    return ENV_VAR_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), value)


def _load_user(role: str) -> dict:
    with USERS_FILE.open() as f:
        users = yaml.safe_load(f)
    return {"email": _resolve(users[role]["email"]),
            "password": _resolve(users[role]["password"])}


@pytest.fixture(scope="session")
def kitchen_sapna_storage_state(browser):
    """Log in once per session, save storage state, clean up at session end."""
    AUTH_STATE_DIR.mkdir(exist_ok=True)
    state_file = AUTH_STATE_DIR / "kitchen_sapna.json"

    user = _load_user("kitchen_sapna")

    ctx = browser.new_context()
    page = ctx.new_page()
    LoginPage(page).open()
    LoginPage(page).login(user["email"], user["password"])
    ctx.storage_state(path=str(state_file))
    ctx.close()

    yield str(state_file)

    if state_file.exists():
        state_file.unlink()


@pytest.fixture
def logged_in_page(browser, kitchen_sapna_storage_state):
    """Per-test fresh context, pre-loaded with kitchen_sapna's session, on the dashboard."""
    ctx = browser.new_context(
        storage_state=kitchen_sapna_storage_state,
        viewport={"width": settings.browser.viewport.width,
                  "height": settings.browser.viewport.height},
        locale=settings.browser.locale,
        timezone_id=settings.browser.timezone,
    )
    p = ctx.new_page()
    p.set_default_navigation_timeout(settings.timeouts.navigation)
    p.set_default_timeout(settings.timeouts.default)
    p.goto(settings.base_url)
    yield p
    ctx.close()