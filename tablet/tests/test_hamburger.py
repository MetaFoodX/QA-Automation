"""Hamburger menu — opens bottom panel."""
import pytest
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


@pytest.fixture(autouse=True)
def switch_to_webview(driver):
    contexts = driver.contexts
    webview = next(c for c in contexts if "WEBVIEW" in c)
    driver.switch_to.context(webview)
    yield
    driver.switch_to.context("NATIVE_APP")


@pytest.mark.smoke
def test_hamburger_opens_bottom_panel(driver):
    """Tapping the hamburger icon must reveal the bottom menu panel."""
    wait = WebDriverWait(driver, 10)

    # click the inner div that holds the @click handler, not the outer wrapper
    hamburger = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, ".icon-div > div")
    ))
    # use JS click to bypass any overlay issues
    driver.execute_script("arguments[0].click();", hamburger)

    time.sleep(2)

    source = driver.page_source
    for keyword in ["van-popup", "menu-view", "bottom", "panel", "slide"]:
        idx = source.find(keyword)
        if idx != -1:
            print(f"\n=== found '{keyword}' at {idx} ===")
            print(source[max(0, idx-100):idx+300])

    panel = wait.until(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, ".menu-view, .van-popup--bottom, .van-popup")
    ))
    assert panel.is_displayed(), "Bottom panel did not appear after tapping hamburger"
