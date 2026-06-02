"""Consumption verification using seeded scan data as source of truth."""
import pytest

from config.settings import settings
from data.fixtures import RESTAURANT_A
from data.test_constants import (
    MEAL_ALL,
    CATEGORY_ALL,
    DEFAULT_DATE_START,
    DEFAULT_DATE_END,
    NO_DATA_AVAILABLE,
)
from pages.consumption_summary_page import ConsumptionSummaryPage as Page


OZ_PER_LB = 16
CONSUMPTION_TYPE = 1

# Which restaurant + venue + service period the UI is currently viewing.
# Update these if you change kitchen_sapna's default view or _apply_filters.
CURRENT_RESTAURANT_ID     = RESTAURANT_A.id
CURRENT_VENUE_ID          = RESTAURANT_A.venues["v_a1"].id
CURRENT_SERVICE_PERIOD_ID = RESTAURANT_A.service_periods["all_day"].id


def _to_float(s: str) -> float:
    cleaned = (
        s.strip()
        .replace(",", "")
        .replace(Page.WEIGHT_UNIT, "")
        .replace(Page.COST_UNIT, "")
        .strip()
    )
    return float(cleaned) if cleaned else 0.0


def _apply_filters(page: Page):
    page.set_venue(settings.test_venue)
    page.set_meal(MEAL_ALL)
    page.set_category(CATEGORY_ALL)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)


def _filter_for_current_view(payloads: list[dict]) -> list[dict]:
    """Keep only scans that match the UI's restaurant + venue + service period."""
    return [
        p for p in payloads
        if p["RestaurantID"]    == CURRENT_RESTAURANT_ID
        and p["VenueID"]         == CURRENT_VENUE_ID
        and p["ServicePeriodID"] == CURRENT_SERVICE_PERIOD_ID
    ]


def _sum_weights_by_item_lb(payloads: list[dict], type_predicate) -> dict[str, float]:
    totals_oz: dict[str, float] = {}
    for p in payloads:
        if not type_predicate(p["Type"]):
            continue
        name = p["MenuItemName"]
        totals_oz[name] = totals_oz.get(name, 0) + p["Weight"]
    return {name: round(oz / OZ_PER_LB, 2) for name, oz in totals_oz.items()}


def _assert_column_matches(page, expected, column, label):
    summary_rows = page.get_rows()
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for item, expected_val in expected.items():
        row = next(
            (r for r in summary_rows if r[Page.COL_MENU_ITEM] == item),
            None,
        )
        if not row:
            failures.append(f"'{item}': expected in summary but not present in UI")
            continue
        actual = _to_float(row[column])
        if abs(actual - expected_val) > 0.01:
            failures.append(
                f"'{item}': expected={expected_val} lb, UI shows={actual} lb"
            )

    assert not failures, (
        f"{label} mismatches against seeded data:\n  " + "\n  ".join(failures)
    )


@pytest.mark.regression
def test_consumption_matches_seeded_data(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = _sum_weights_by_item_lb(relevant, lambda t: t == CONSUMPTION_TYPE)
    _assert_column_matches(page, expected, Page.COL_CONSUMPTION, "Consumption")


@pytest.mark.regression
def test_overproduction_matches_seeded_data(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = _sum_weights_by_item_lb(relevant, lambda t: t != CONSUMPTION_TYPE)
    _assert_column_matches(page, expected, Page.COL_OVERPRODUCTION, "Overproduction")


@pytest.mark.regression
def test_production_matches_seeded_data(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = _sum_weights_by_item_lb(relevant, lambda _t: True)
    _assert_column_matches(page, expected, Page.COL_PRODUCTION, "Production")


@pytest.mark.regression
def test_no_data_for_out_of_range_dates(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(settings.test_venue)
    page.set_meal(MEAL_ALL)
    page.set_category(CATEGORY_ALL)
    page.set_date_range("05/01/2026", "05/07/2026")

    summary_rows = page.get_rows()
    assert len(summary_rows) == 0, (
        f"Expected zero rows for out-of-range date filter, got {len(summary_rows)}"
    )