"""Playwright browser/context/page fixtures."""
import pytest
from playwright.sync_api import sync_playwright

from config.settings import settings


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(playwright_instance):
    launcher = getattr(playwright_instance, settings.browser.engine)
    launch_kwargs = {
        "headless": settings.browser.headless,
        "slow_mo": settings.browser.slow_mo,
    }
    if settings.browser.engine == "chromium" and settings.browser.channel:
        launch_kwargs["channel"] = settings.browser.channel
    browser = launcher.launch(**launch_kwargs)
    yield browser
    browser.close()


@pytest.fixture
def context(browser):
    ctx = browser.new_context(
        viewport={"width": settings.browser.viewport.width,
                  "height": settings.browser.viewport.height},
        locale=settings.browser.locale,
        timezone_id=settings.browser.timezone,
        ignore_https_errors=settings.browser.ignore_https_errors,
    )
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    p = context.new_page()
    p.set_default_navigation_timeout(settings.timeouts.navigation)
    p.set_default_timeout(settings.timeouts.default)
    yield p
    p.close()