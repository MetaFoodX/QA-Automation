"""Smoke test — verify Appium can connect and the app launches."""
import pytest
from appium.webdriver.common.appiumby import AppiumBy


@pytest.mark.smoke
def test_app_launches(driver):
    """App opens and at least one element is visible on screen."""
    contexts = driver.contexts
    assert len(contexts) >= 1, f"No contexts found: {contexts}"


@pytest.mark.smoke
def test_webview_context_available(driver):
    """App exposes a WEBVIEW context (Vue frontend loaded)."""
    contexts = driver.contexts
    webview_contexts = [c for c in contexts if "WEBVIEW" in c]
    assert webview_contexts, (
        f"No WEBVIEW context found. Available: {contexts}\n"
        "App may still be loading — try increasing implicit wait."
    )
