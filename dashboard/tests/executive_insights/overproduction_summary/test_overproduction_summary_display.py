"""Overproduction Summary — display and navigation tests."""
import allure
import pytest

from dashboard.locators import common_locators as L
from dashboard.pages.overproduction_summary_page import OverproductionSummaryPage as Page
from dashboard.tests.executive_insights.overproduction_summary._helpers import (
    _apply_filters,
    _assert_headers_have_unit,
)
from shared.data.test_constants import *  # noqa: F401, F403


# ---------------------------------------------------------------------------
# Column Headers
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("All expected columns are present in default weight view")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="All expected columns are present in the default weight view",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary via top nav\n"
        "3. Read the table headers\n"
        "4. Assert Menu Item, Venue, Total Overproduction (lb), Reuse (lb), "
        "Donation (lb), and Compostable (lb) columns are all present\n"
        "5. Assert no expected column is missing"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_all_expected_columns_present(logged_in_page):
    """All expected columns must be present in default weight view."""
    page = Page(logged_in_page)
    page.open_via_nav()

    headers = page.get_headers()
    expected = [
        Page.COL_MENU_ITEM,
        Page.COL_VENUE,
        Page.COL_TOTAL_OVERPRODUCTION,
        Page.COL_REUSE,
        Page.COL_DONATION,
        Page.COL_COMPOSTABLE,
    ]
    missing = [col for col in expected if col not in headers]
    assert not missing, f"Missing columns: {missing}. Got: {headers}"


@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Default weight view shows (lb) unit in Total Overproduction header")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Default weight view shows (lb) unit in Total Overproduction header",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Verify Total Overproduction header displays '(lb)'"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_weight_view_shows_lb_unit(logged_in_page, seeded_basic_scans):
    """Default view — verify Total Overproduction header shows (lb)."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    _assert_headers_have_unit(page, Page.WEIGHT_UNIT)


@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Cost view toggle switches Total Overproduction header to ($) unit")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Cost view toggle switches Total Overproduction header to ($) unit",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click the cost view toggle button\n"
        "5. Verify Total Overproduction header displays '($)'"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_cost_view_shows_dollar_unit(logged_in_page, seeded_basic_scans):
    """Click cost toggle — verify Total Overproduction header switches to ($)."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.toggle_cost_view()

    _assert_headers_have_unit(page, Page.COST_UNIT)


@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Toggling cost view and back returns Total Overproduction header to (lb) unit")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Toggling cost view off returns Total Overproduction header to lb unit",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click the cost view toggle to switch to $ view\n"
        "5. Assert header shows ($) unit\n"
        "6. Click the cost view toggle again to switch back\n"
        "7. Assert Total Overproduction header shows (lb) unit"
    ),
)
@pytest.mark.regression
def test_toggle_cost_back_to_weight(logged_in_page, seeded_basic_scans):
    """Toggle to cost view then back — header must return to lb unit."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.toggle_cost_view()
    _assert_headers_have_unit(page, Page.COST_UNIT)

    page.toggle_cost_view()
    _assert_headers_have_unit(page, Page.WEIGHT_UNIT)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Breadcrumb shows 'Overproduction Summary' after navigation")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Breadcrumb shows correct page name after navigation",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Locate the breadcrumb element\n"
        "4. Assert the breadcrumb text contains 'Overproduction Summary'"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_breadcrumb_shows_correct_text(logged_in_page):
    """Breadcrumb must show 'Overproduction Summary' after navigation."""
    page = Page(logged_in_page)
    page.open_via_nav()

    breadcrumb = page.page.locator(L.BREADCRUMB_PAGE_LINK)
    assert Page.SIDEBAR_ITEM in breadcrumb.inner_text(), (
        f"Expected '{Page.SIDEBAR_ITEM}' in breadcrumb, got: {breadcrumb.inner_text()}"
    )
