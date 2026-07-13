import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options


def pytest_addoption(parser):
    parser.addoption("--device-ip", default=None, help="Tablet IP for ADB wireless connection")


@pytest.fixture(scope="session")
def driver(request):
    device_ip = request.config.getoption("--device-ip")

    options = UiAutomator2Options()
    options.platform_name        = "Android"
    options.app_package          = "com.foodfx"
    options.app_activity         = ".presentation.view.MainActivity"
    options.no_reset             = True
    options.auto_grant_permissions   = True
    options.chromedriver_autodownload = True

    if device_ip:
        options.udid = device_ip if ":" in device_ip else f"{device_ip}:5555"

    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
    driver.implicitly_wait(10)

    yield driver

    driver.quit()
