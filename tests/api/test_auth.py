"""Smoke test for API authentication."""

import pytest

from config.settings import settings
from fixtures.auth_fixtures import _load_user
from locators import login_locators as L
from pages.login_page import LoginPage
from playwright.sync_api import expect

@pytest.fixture
def login_page(browser):
    """Fresh browser context with NO stored auth — opens the login page."""
    ctx = browser.new_context(
        viewport={"width": settings.browser.viewport.width,
                  "height": settings.browser.viewport.height},
        locale=settings.browser.locale,
        timezone_id=settings.browser.timezone,
    )
    p = ctx.new_page()
    p.set_default_navigation_timeout(settings.timeouts.navigation)
    p.set_default_timeout(settings.timeouts.default)
    LoginPage(p).open()
    yield p
    ctx.close()


@pytest.mark.smoke
@pytest.mark.regression
def test_login_happy_path(login_page):
    """Valid kitchen_sapna credentials land the user past the login screen."""
    user = _load_user("kitchen_sapna")
    LoginPage(login_page).login(user["email"], user["password"])

    assert login_page.locator(L.LOGGED_IN_MARKER).is_visible(), (
        "Expected 'Current View' marker after successful login but it wasn't visible"
    )


@pytest.mark.regression
def test_login_empty_fields_shows_inline_validation(login_page):
    """Clicking Sign In with empty fields shows both inline validation errors."""
    login_page.get_by_role("button", name=L.SIGN_IN_BUTTON_TEXT).click()

    expect(login_page.get_by_text("Please enter a valid email address")).to_be_visible()
    expect(login_page.get_by_text("Required")).to_be_visible()


@pytest.mark.regression
def test_login_wrong_credentials_shows_error_popup(login_page):
    """Wrong credentials trigger the 'Incorrect username or password' popup."""
    login_page.locator(L.EMAIL_INPUT).fill("abc@gmail.com")
    login_page.locator(L.PASSWORD_INPUT).fill("wrongpassword")
    login_page.get_by_role("button", name=L.SIGN_IN_BUTTON_TEXT).click()

    expect(login_page.get_by_text("Incorrect username or password.")).to_be_visible()

@pytest.mark.smoke
@pytest.mark.regression
def test_can_acquire_access_token(access_token):
    """Verify we can authenticate against Cognito and get a non-empty access token."""
    print(f"\n[access_token] {access_token}")
    assert access_token, "Failed to acquire access token from Cognito"
    assert len(access_token) > 100, f"Access token suspiciously short: {len(access_token)} chars"