"""
Inject scans via the Add Scan JS bridge — no camera, no Metron code changes.

Flow per scan:
  postAddScanCaptureAtData  → timestamp
  postAddScanSelectedMIID   → menu item
  postAddScanSelectSPID     → service period (first active one)
  postAddScanType           → 1 = consumption/service
  postAddScanWeight         → weight in oz
  addScan()                 → submits to server
"""
import json
import random
import time
from datetime import datetime, timezone

import pytest


SCAN_TYPE_SERVICE = 1
DEFAULT_WEIGHT_OZ = 32.5


def _webview_context(driver):
    return next(c for c in driver.contexts if "WEBVIEW" in c)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _get_menu_items(driver) -> list:
    raw = driver.execute_script("return window.mainJava.getAllMenuItems()")
    items = json.loads(raw)
    return [i for i in items if i.get("ID") and i.get("Name")]


def _get_service_period_id(driver) -> str | None:
    raw = driver.execute_script("return window.mainJava.getLocalServicePeriods()")
    periods = json.loads(raw)
    if not periods:
        return None
    return str(periods[0].get("ID") or periods[0].get("id") or periods[0].get("ServicePeriodID", ""))


def _create_scan(driver, menu_item_id: str, service_period_id: str | None,
                 weight: float = DEFAULT_WEIGHT_OZ) -> None:
    driver.execute_script(f"window.mainJava.postAddScanCaptureAtData('{_now_utc()}')")
    driver.execute_script(f"window.mainJava.postAddScanSelectedMIID({int(menu_item_id)})")
    if service_period_id:
        driver.execute_script(f"window.mainJava.postAddScanSelectSPID('{service_period_id}')")
    driver.execute_script(f"window.mainJava.postAddScanType({SCAN_TYPE_SERVICE})")
    driver.execute_script(f"window.mainJava.postAddScanWeight('{weight}')")
    driver.execute_script("window.mainJava.addScan()")


@pytest.fixture(autouse=True)
def webview(driver):
    driver.switch_to.context(_webview_context(driver))
    yield
    driver.switch_to.context("NATIVE_APP")


@pytest.mark.smoke
def test_list_menu_items(driver):
    """Verify the app has menu items loaded and bridge is reachable."""
    items = _get_menu_items(driver)
    assert items, "getAllMenuItems() returned empty — app may not be synced"
    print(f"\n{len(items)} menu items available")
    for item in items[:5]:
        print(f"  {item['ID']} — {item['Name']}")


@pytest.mark.smoke
def test_create_single_scan(driver):
    """Create one scan and confirm addScan() does not throw."""
    items = _get_menu_items(driver)
    assert items, "No menu items — cannot create scan"

    sp_id = _get_service_period_id(driver)
    item = items[0]

    _create_scan(driver, item["ID"], sp_id)
    time.sleep(3)
    print(f"\nScan created — menu item: {item['Name']}  service_period: {sp_id}")


def test_create_scans_varied_items(driver):
    """Create one scan per unique menu item (up to 10) with random weights."""
    items = _get_menu_items(driver)
    assert items, "No menu items — cannot create scans"

    sp_id = _get_service_period_id(driver)
    sample = random.sample(items, min(10, len(items)))

    for item in sample:
        weight = round(random.uniform(16.0, 80.0), 1)
        _create_scan(driver, item["ID"], sp_id, weight=weight)
        print(f"  ✓ {item['Name']}  {weight}oz")
        time.sleep(2)

    print(f"\n{len(sample)} scans submitted")
