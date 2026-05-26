"""Consumption Summary drill-down consistency tests."""
import pytest

from config.settings import settings
from data.test_constants import *
from pages.consumption_summary_page import ConsumptionSummaryPage


def _to_float(s: str) -> float:
    cleaned = s.strip().replace(",", "").replace("lb", "").strip()
    return float(cleaned) if cleaned else 0.0


def _check_column_sum_matches(page: ConsumptionSummaryPage, column: str) -> list[str]:
    summary_rows = page.get_rows()

    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return []  # no failures → test passes

    failures = []
    for i, summary in enumerate(summary_rows):
        item = summary["Menu Item"]
        s_val = _to_float(summary[column])

        page.click_menu_item_in_row(i)

        detail_rows = page.get_rows()
        d_val = sum(_to_float(r[column]) for r in detail_rows)

        if abs(d_val - s_val) > 0.01:
            failures.append(f"'{item}': summary={s_val}, detail sum={d_val}")

        page.navigate_back_to_summary()

    return failures


def _apply_filters(page: ConsumptionSummaryPage):
    """Apply the standard filter set used by Consumption Summary tests."""
    page.set_venue(settings.test_venue)
    page.set_meal(MEAL_ALL)
    page.set_category(CATEGORY_ALL)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

def _assert_headers_have_unit(page: ConsumptionSummaryPage, unit: str):
    """Verify Production/Consumption/Overproduction headers all show the given unit."""
    headers = page.get_headers()
    expected = [
        f"Production ({unit})",
        f"Consumption ({unit})",
        f"Overproduction ({unit})",
    ]
    missing = [col for col in expected if not any(col in h for h in headers)]
    assert not missing, (
        f"Expected headers with '{unit}' unit missing: {missing}. "
        f"Got headers: {headers}"
    )


@pytest.mark.smoke
def test_production_sums_match_summary(logged_in_page):
    """Verify Production summary == sum of daily detail Production for every menu item."""
    page = ConsumptionSummaryPage(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    failures = _check_column_sum_matches(page, "Production (lb)")
    assert not failures, "Production mismatches:\n  " + "\n  ".join(failures)


@pytest.mark.smoke
def test_consumption_sums_match_summary(logged_in_page):
    """Verify Consumption summary == sum of daily detail Consumption for every menu item."""
    page = ConsumptionSummaryPage(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    failures = _check_column_sum_matches(page, "Consumption (lb)")
    assert not failures, "Consumption mismatches:\n  " + "\n  ".join(failures)




@pytest.mark.smoke
def test_cost_view_shows_dollar_unit(logged_in_page):
    """Click cost toggle; verify headers switch to ($)."""
    page = ConsumptionSummaryPage(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.toggle_cost_view()

    _assert_headers_have_unit(page, "$")


@pytest.mark.smoke
def test_weight_view_shows_lb_unit(logged_in_page):
    """Default view; verify headers show (lb)."""
    page = ConsumptionSummaryPage(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    _assert_headers_have_unit(page, "lb")


@pytest.mark.smoke
def test_production_equals_consumption_plus_overproduction(logged_in_page):
    """Math invariant: Production == Consumption + Overproduction for every menu item.

    Pure summary-page check — no drill-in, no pagination handling.
    """
    page = ConsumptionSummaryPage(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    summary_rows = page.get_rows()

    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in summary_rows:
        item = row["Menu Item"]
        production = _to_float(row["Production (lb)"])
        consumption = _to_float(row["Consumption (lb)"])
        overproduction = _to_float(row["Overproduction (lb)"])

        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(
                f"'{item}': Production={production}, "
                f"Consumption + Overproduction = {consumption} + {overproduction} = {expected}"
            )

    assert not failures, (
        "Math invariant violations (Production != Consumption + Overproduction):\n  "
        + "\n  ".join(failures)
    )