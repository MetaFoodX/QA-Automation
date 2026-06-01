"""Consumption verification using seeded scan data as source of truth."""
import json
from pathlib import Path

import pytest

from config.settings import settings
from data.test_constants import (
    MEAL_ALL,
    CATEGORY_ALL,
    DEFAULT_DATE_START,
    DEFAULT_DATE_END,
    NO_DATA_AVAILABLE,
)
from pages.consumption_summary_page import ConsumptionSummaryPage as Page


SCAN_DATA_PATH = (
    Path(__file__).parent.parent.parent / "data" / "test_scenarios" / "post_data.json"
)

OZ_PER_LB = 16
CONSUMPTION_TYPE = 1   # Refill — represents food that was consumed


def _to_float(s: str) -> float:
    """Strip units/commas, return float."""
    cleaned = (
        s.strip()
        .replace(",", "")
        .replace(Page.WEIGHT_UNIT, "")
        .replace(Page.COST_UNIT, "")
        .strip()
    )
    return float(cleaned) if cleaned else 0.0


def _apply_filters(page: Page):
    """Standard filter set — same as other consumption summary tests."""
    page.set_venue(settings.test_venue)
    page.set_meal(MEAL_ALL)
    page.set_category(CATEGORY_ALL)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)


def _compute_expected_consumption_lb() -> dict[str, float]:
    """Compute expected Consumption (lb) per menu item from the seeded JSON.

    Refill (Type=1) scans = food that was consumed and replenished.
    Consumption = sum of Type=1 weights, converted from oz to lb.
    """
    with SCAN_DATA_PATH.open() as f:
        scans = json.load(f)

    totals_oz: dict[str, float] = {}
    for scan in scans:
        if scan["Type"] != CONSUMPTION_TYPE:
            continue
        name = scan["MenuItemName"]
        totals_oz[name] = totals_oz.get(name, 0) + scan["Weight"]

    return {name: round(oz / OZ_PER_LB, 2) for name, oz in totals_oz.items()}


def _compute_expected_overproduction_lb() -> dict[str, float]:
    """Overproduction per menu item, in lb.

    Any scan with Type != 1 represents food that wasn't consumed — i.e.
    overproduction (empty pans, leftovers, not-served leftovers, inventory).
    """
    with SCAN_DATA_PATH.open() as f:
        scans = json.load(f)

    totals_oz: dict[str, float] = {}
    for scan in scans:
        if scan["Type"] == CONSUMPTION_TYPE:
            continue
        name = scan["MenuItemName"]
        totals_oz[name] = totals_oz.get(name, 0) + scan["Weight"]

    return {name: round(oz / OZ_PER_LB, 2) for name, oz in totals_oz.items()}


def _compute_expected_production_lb() -> dict[str, float]:
    """Production per menu item, in lb.

    Production = Consumption + Overproduction = sum of ALL scan weights
    for that item, regardless of type.
    """
    with SCAN_DATA_PATH.open() as f:
        scans = json.load(f)

    totals_oz: dict[str, float] = {}
    for scan in scans:
        name = scan["MenuItemName"]
        totals_oz[name] = totals_oz.get(name, 0) + scan["Weight"]

    return {name: round(oz / OZ_PER_LB, 2) for name, oz in totals_oz.items()}


@pytest.mark.regression
def test_consumption_matches_seeded_data(logged_in_page, seeded_basic_scans):
    """Verify Consumption column in UI matches values computed from seeded scan data.

    Flow:
      1. seeded_basic_scans fixture inserts 10 scans before this test (cleans up after)
      2. Open Consumption Summary, apply standard filters
      3. Read UI's table
      4. Compute expected Consumption per item from JSON
      5. Compare each item's UI Consumption to expected
    """
    page = Page(logged_in_page)
    print("[test] open_via_nav...")
    page.open_via_nav()
    print("[test] _apply_filters...")
    _apply_filters(page)
    print("[test] get_rows...")

    summary_rows = page.get_rows()
    print(f"[test] got {len(summary_rows)} rows")
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    expected = _compute_expected_consumption_lb()
    failures = []

    for item, expected_consumption in expected.items():
        row = next(
            (r for r in summary_rows if r[Page.COL_MENU_ITEM] == item),
            None,
        )
        if not row:
            failures.append(f"'{item}': expected in summary but not present in UI")
            continue

        actual = _to_float(row[Page.COL_CONSUMPTION])
        if abs(actual - expected_consumption) > 0.01:
            failures.append(
                f"'{item}': expected={expected_consumption} lb, UI shows={actual} lb"
            )

    assert not failures, (
        "Consumption mismatches against seeded data:\n  "
        + "\n  ".join(failures)
    )

@pytest.mark.regression
def test_overproduction_matches_seeded_data(logged_in_page, seeded_basic_scans):
    """Verify Overproduction column in UI matches values computed from seeded scan data."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    summary_rows = page.get_rows()
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    expected = _compute_expected_overproduction_lb()
    failures = []

    for item, expected_overproduction in expected.items():
        row = next(
            (r for r in summary_rows if r[Page.COL_MENU_ITEM] == item),
            None,
        )
        if not row:
            failures.append(f"'{item}': expected in summary but not present in UI")
            continue

        actual = _to_float(row[Page.COL_OVERPRODUCTION])
        if abs(actual - expected_overproduction) > 0.01:
            failures.append(
                f"'{item}': expected={expected_overproduction} lb, UI shows={actual} lb"
            )

    assert not failures, (
        "Overproduction mismatches against seeded data:\n  "
        + "\n  ".join(failures)
    )


@pytest.mark.regression
def test_production_matches_seeded_data(logged_in_page, seeded_basic_scans):
    """Verify Production column in UI matches values computed from seeded scan data.

    Production = sum of all scan weights regardless of Type
    (i.e. Production == Consumption + Overproduction).
    """
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    summary_rows = page.get_rows()
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    expected = _compute_expected_production_lb()
    failures = []

    for item, expected_production in expected.items():
        row = next(
            (r for r in summary_rows if r[Page.COL_MENU_ITEM] == item),
            None,
        )
        if not row:
            failures.append(f"'{item}': expected in summary but not present in UI")
            continue

        actual = _to_float(row[Page.COL_PRODUCTION])
        if abs(actual - expected_production) > 0.01:
            failures.append(
                f"'{item}': expected={expected_production} lb, UI shows={actual} lb"
            )

    assert not failures, (
        "Production mismatches against seeded data:\n  "
        + "\n  ".join(failures)
    )

@pytest.mark.regression
def test_no_data_for_out_of_range_dates(logged_in_page, seeded_basic_scans):
    """Negative test: filtering to a date range with no seeded data shows empty table.

    Seeded scans live in the rolling 'last 7 days' window, so May 1–7, 2026 is
    guaranteed to be outside it. Expect zero rows and the 'No data available' message.
    """
    page = Page(logged_in_page)
    page.open_via_nav()

    page.set_venue(settings.test_venue)
    page.set_meal(MEAL_ALL)
    page.set_category(CATEGORY_ALL)
    page.set_date_range("05/01/2026", "05/07/2026")

    summary_rows = page.get_rows()

    assert len(summary_rows) == 0, (
        f"Expected zero rows for out-of-range date filter (May 1-7, 2026), "
        f"but got {len(summary_rows)} rows: "
        f"{[r.get(Page.COL_MENU_ITEM) for r in summary_rows]}"
    )