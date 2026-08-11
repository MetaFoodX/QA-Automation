"""Overproduction Summary — display, math invariant, and navigation tests."""
import allure
import pytest

from dashboard.locators import common_locators as L
from dashboard.pages.overproduction_summary_page import OverproductionSummaryPage as Page
from dashboard.tests.executive_insights.overproduction_summary._helpers import (
    OZ_PER_LB,
    CURRENT_RESTAURANT_ID, CURRENT_VENUE_ID, CURRENT_VENUE_NAME,
    SECOND_VENUE_ID, SECOND_VENUE_NAME,
    LUNCH_SP_ID, DINNER_SP_ID, ALL_DAY_SP_ID,
    _to_float, _apply_filters,
    _filter_for_current_view, _filter_by_service_period,
    _compute_expected_by_item,
    _assert_column_matches, _assert_headers_have_unit,
    _is_sorted_ascending, _is_sorted_descending,
    _get_breadcrumb_links,
)
from shared.data.test_constants import *  # noqa: F401, F403


# ---------------------------------------------------------------------------
# Column Headers — Default (Weight) View
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
    key="FQL-105",
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
@allure.title("Default weight view shows (lb) unit in all destination headers")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Default weight view shows (lb) unit in all destination headers",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Verify Total Overproduction, Reuse, Donation, and Compostable headers all display '(lb)'"
    ),
    key="FQL-106",
)
@pytest.mark.smoke
@pytest.mark.regression
def test_weight_view_shows_lb_unit(logged_in_page, seeded_basic_scans):
    """Default view — verify all destination headers show (lb)."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    _assert_headers_have_unit(page, Page.WEIGHT_UNIT)


@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Cost view toggle switches all destination headers to ($) unit")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Cost view toggle switches all destination headers to ($) unit",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click the cost view toggle button\n"
        "5. Verify Total Overproduction, Reuse, Donation, Compostable headers all display '($)'"
    ),
    key="FQL-107",
)
@pytest.mark.smoke
@pytest.mark.regression
def test_cost_view_shows_dollar_unit(logged_in_page, seeded_basic_scans):
    """Click cost toggle — verify all destination headers switch to ($)."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.toggle_cost_view()

    _assert_headers_have_unit(page, Page.COST_UNIT)


@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Toggling cost view and back returns all destination headers to (lb) unit")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Toggling cost view off returns all destination headers to lb unit",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click the cost view toggle to switch to $ view\n"
        "5. Assert headers show ($) unit\n"
        "6. Click the cost view toggle again to switch back\n"
        "7. Assert all destination headers show (lb) unit"
    ),
    key="FQL-108",
)
@pytest.mark.regression
def test_toggle_cost_back_to_weight(logged_in_page, seeded_basic_scans):
    """Toggle to cost view then back — headers must return to lb unit."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.toggle_cost_view()
    _assert_headers_have_unit(page, Page.COST_UNIT)

    page.toggle_cost_view()
    _assert_headers_have_unit(page, Page.WEIGHT_UNIT)


@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Cost view contains all four expected cost columns")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Cost view shows Total Overproduction ($), Reuse ($), Donation ($), Compostable ($)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click the cost view toggle\n"
        "5. Assert all four cost columns are present in the table headers"
    ),
    key="FQL-109",
)
@pytest.mark.regression
def test_cost_view_all_columns_present(logged_in_page, seeded_basic_scans):
    """Cost view must show all four cost columns."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.toggle_cost_view()

    headers = page.get_headers()
    expected = [
        Page.COL_TOTAL_OVERPRODUCTION_COST,
        Page.COL_REUSE_COST,
        Page.COL_DONATION_COST,
        Page.COL_COMPOSTABLE_COST,
    ]
    missing = [col for col in expected if col not in headers]
    assert not missing, f"Missing cost columns: {missing}. Got: {headers}"


# ---------------------------------------------------------------------------
# Column Headers — Breakdown View
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Breakdown view shows Served and Not Served sub-columns")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Enabling breakdown view shows Served/Not Served sub-columns for each destination",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click the Breakdown toggle\n"
        "5. Assert Served Total Overproduction and Not Served Total Overproduction columns appear"
    ),
    key="FQL-110",
)
@pytest.mark.regression
def test_breakdown_view_shows_served_columns(logged_in_page, seeded_basic_scans):
    """Breakdown view must reveal Served / Not Served sub-columns."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.toggle_breakdown_view()

    rows = page.get_breakdown_rows()
    assert rows, "No rows returned in breakdown view"
    first_row = rows[0]
    assert Page.COL_SERVED_TOTAL_OP in first_row, (
        f"Expected '{Page.COL_SERVED_TOTAL_OP}' key in breakdown rows. Got keys: {list(first_row.keys())}"
    )
    assert Page.COL_NOT_SERVED_TOTAL_OP in first_row, (
        f"Expected '{Page.COL_NOT_SERVED_TOTAL_OP}' key in breakdown rows. Got keys: {list(first_row.keys())}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Toggling breakdown view off removes Served sub-columns")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Disabling breakdown view removes the Served/Not Served sub-columns",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click Breakdown toggle to enable\n"
        "5. Click Breakdown toggle again to disable\n"
        "6. Assert Served Total Overproduction column is no longer in headers"
    ),
    key="FQL-111",
)
@pytest.mark.regression
def test_breakdown_toggle_off_removes_served_columns(logged_in_page, seeded_basic_scans):
    """Toggling breakdown off must remove Served sub-columns."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.toggle_breakdown_view()
    page.toggle_breakdown_view()

    headers = page.get_headers()
    assert not any(Page.COL_SERVED_TOTAL_OP in h for h in headers), (
        f"'{Page.COL_SERVED_TOTAL_OP}' should not appear after toggling breakdown off. Got: {headers}"
    )


# ---------------------------------------------------------------------------
# Column Headers — Day View
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Day view toggle shows Date and Day columns")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Enabling day view adds Date and Day columns to the table",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click the Day toggle button\n"
        "5. Assert Date and Day columns appear in the table headers"
    ),
    key="FQL-112",
)
@pytest.mark.regression
def test_day_view_shows_date_and_day_columns(logged_in_page, seeded_basic_scans):
    """Day view must add Date and Day columns."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.toggle_day_view()

    headers = page.get_headers()
    assert Page.COL_DATE in headers, f"Expected 'Date' column in day view. Got: {headers}"
    assert Page.COL_DAY in headers, f"Expected 'Day' column in day view. Got: {headers}"


@allure.epic("Overproduction Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Toggling day view off removes Date and Day columns")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Disabling day view removes Date and Day columns",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click Day toggle to enable\n"
        "5. Click Day toggle again to disable\n"
        "6. Assert Date and Day columns are no longer in headers"
    ),
    key="FQL-113",
)
@pytest.mark.regression
def test_day_view_toggle_off_removes_date_columns(logged_in_page, seeded_basic_scans):
    """Toggling day view off must remove Date and Day columns."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.toggle_day_view()
    page.toggle_day_view()

    headers = page.get_headers()
    assert Page.COL_DATE not in headers, (
        f"'Date' column should not appear after toggling day view off. Got: {headers}"
    )
    assert Page.COL_DAY not in headers, (
        f"'Day' column should not appear after toggling day view off. Got: {headers}"
    )


# ---------------------------------------------------------------------------
# Math Invariants
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Math Invariants")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Total Overproduction equals Reuse + Donation + Compostable per row")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Math invariant: Total Overproduction = Reuse + Donation + Compostable for every row",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Read all summary rows\n"
        "5. For each row assert Total Overproduction == Reuse + Donation + Compostable (tolerance 0.01)"
    ),
    key="FQL-114",
)
@pytest.mark.smoke
@pytest.mark.regression
def test_total_equals_reuse_plus_donation_plus_compostable(logged_in_page, seeded_basic_scans):
    """Math invariant: Total == Reuse + Donation + Compostable for every row."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    rows = page.get_rows()
    if not rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in rows:
        item        = row.get(Page.COL_MENU_ITEM, "")
        total       = _to_float(row.get(Page.COL_TOTAL_OVERPRODUCTION, "0"))
        reuse       = _to_float(row.get(Page.COL_REUSE, "0"))
        donation    = _to_float(row.get(Page.COL_DONATION, "0"))
        compostable = _to_float(row.get(Page.COL_COMPOSTABLE, "0"))

        expected = reuse + donation + compostable
        if abs(total - expected) > 0.01:
            failures.append(
                f"'{item}': Total={total}, R+D+C={reuse}+{donation}+{compostable}={expected}"
            )

    assert not failures, (
        "Math invariant violations (Total != Reuse + Donation + Compostable):\n  "
        + "\n  ".join(failures)
    )


@allure.epic("Overproduction Summary")
@allure.feature("Math Invariants")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Total Overproduction equals Reuse + Donation + Compostable in cost ($) view")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Math invariant holds in cost view: Total ($) = Reuse ($) + Donation ($) + Compostable ($)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click the cost view toggle\n"
        "5. For each row assert Total Overproduction ($) == Reuse ($) + Donation ($) + Compostable ($)"
    ),
    key="FQL-116",
)
@pytest.mark.regression
def test_cost_view_total_equals_destinations(logged_in_page, seeded_basic_scans):
    """Math invariant must also hold in cost ($) view."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.toggle_cost_view()

    rows = page.get_rows()
    if not rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in rows:
        item        = row.get(Page.COL_MENU_ITEM, "")
        total       = _to_float(row.get(Page.COL_TOTAL_OVERPRODUCTION_COST, "0"))
        reuse       = _to_float(row.get(Page.COL_REUSE_COST, "0"))
        donation    = _to_float(row.get(Page.COL_DONATION_COST, "0"))
        compostable = _to_float(row.get(Page.COL_COMPOSTABLE_COST, "0"))

        expected = reuse + donation + compostable
        if abs(total - expected) > 0.01:
            failures.append(
                f"'{item}': Total=${total}, R+D+C=${reuse}+${donation}+${compostable}=${expected}"
            )

    assert not failures, (
        "Cost view math invariant violations:\n  " + "\n  ".join(failures)
    )


@allure.epic("Overproduction Summary")
@allure.feature("Math Invariants")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("All Total Overproduction values are non-negative")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction must never be negative for any row",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Read all rows across all pages\n"
        "5. Assert Total Overproduction >= 0 for every row"
    ),
    key="FQL-117",
)
@pytest.mark.regression
def test_total_overproduction_always_non_negative(logged_in_page, seeded_basic_scans):
    """Total Overproduction must be >= 0 for every row."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    all_rows = page.get_all_rows()
    failures = [
        f"'{r.get(Page.COL_MENU_ITEM, '')}': Total Overproduction={_to_float(r.get(Page.COL_TOTAL_OVERPRODUCTION, '0'))}"
        for r in all_rows
        if _to_float(r.get(Page.COL_TOTAL_OVERPRODUCTION, "0")) < 0
    ]
    assert not failures, (
        "Negative Total Overproduction found:\n  " + "\n  ".join(failures)
    )


@allure.epic("Overproduction Summary")
@allure.feature("Math Invariants")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("All destination column values (Reuse, Donation, Compostable) are non-negative")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Reuse, Donation, and Compostable values must never be negative",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Read all rows\n"
        "5. Assert Reuse, Donation, and Compostable are all >= 0 for every row"
    ),
    key="FQL-118",
)
@pytest.mark.regression
def test_destination_columns_always_non_negative(logged_in_page, seeded_basic_scans):
    """Reuse, Donation, Compostable must all be >= 0 for every row."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    all_rows = page.get_all_rows()
    failures = []
    for r in all_rows:
        item = r.get(Page.COL_MENU_ITEM, "")
        for col in [Page.COL_REUSE, Page.COL_DONATION, Page.COL_COMPOSTABLE]:
            val = _to_float(r.get(col, "0"))
            if val < 0:
                failures.append(f"'{item}' — {col}={val}")

    assert not failures, (
        "Negative destination values found:\n  " + "\n  ".join(failures)
    )


@allure.epic("Overproduction Summary")
@allure.feature("Math Invariants")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Breakdown view: Served + Not Served totals equal Total Overproduction per row")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="In breakdown view, Served Total + Not Served Total = Total Overproduction per row",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Enable breakdown view\n"
        "5. For each row assert Served Total + Not Served Total == Total Overproduction (tolerance 0.01)"
    ),
    key="FQL-119",
)
@pytest.mark.regression
def test_breakdown_served_plus_not_served_equals_total(logged_in_page, seeded_basic_scans):
    """In breakdown view, Served + Not Served must equal Total Overproduction."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    normal_rows = page.get_rows()
    if not normal_rows:
        print(NO_DATA_AVAILABLE)
        return
    totals = {r[Page.COL_MENU_ITEM]: _to_float(r.get(Page.COL_TOTAL_OVERPRODUCTION, "0"))
              for r in normal_rows}

    page.toggle_breakdown_view()
    rows = page.get_breakdown_rows()

    failures = []
    for row in rows:
        item             = row.get(Page.COL_MENU_ITEM, "")
        served_total     = _to_float(row.get(Page.COL_SERVED_TOTAL_OP, "0"))
        not_served_total = _to_float(row.get(Page.COL_NOT_SERVED_TOTAL_OP, "0"))
        expected_total   = totals.get(item, 0)

        actual_sum = round(served_total + not_served_total, 2)
        if abs(actual_sum - expected_total) > 0.01:
            failures.append(
                f"'{item}': Served({served_total}) + NotServed({not_served_total}) = {actual_sum} != Total {expected_total}"
            )

    assert not failures, (
        "Breakdown invariant violations (Total != Served + Not Served):\n  "
        + "\n  ".join(failures)
    )


# ---------------------------------------------------------------------------
# Data Accuracy
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Total Overproduction values match seeded scan data")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="UI Total Overproduction per menu item matches what was seeded via API",
    steps=(
        "1. Seed scans via API\n"
        "2. Navigate to Overproduction Summary with default filters\n"
        "3. Compute expected total overproduction from seeded payloads\n"
        "4. For each seeded menu item assert UI value matches expected (tolerance 0.01 lb)"
    ),
    key="FQL-120",
)
@pytest.mark.regression
def test_total_overproduction_matches_seeded_data(logged_in_page, seeded_basic_scans):
    """Total Overproduction per menu item must match seeded scan totals."""
    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["total"] for k, v in expected.items()},
                           Page.COL_TOTAL_OVERPRODUCTION, "Total Overproduction")


@allure.epic("Overproduction Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Reuse column values match seeded scan data")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="UI Reuse per menu item matches seeded reuse scan totals",
    steps=(
        "1. Seed scans via API\n"
        "2. Navigate to Overproduction Summary with default filters\n"
        "3. Compute expected reuse from seeded payloads (types 4 and 9)\n"
        "4. For each seeded menu item assert UI Reuse value matches expected (tolerance 0.01 lb)"
    ),
    key="FQL-121",
)
@pytest.mark.regression
def test_reuse_matches_seeded_data(logged_in_page, seeded_basic_scans):
    """Reuse column per menu item must match seeded reuse scan totals."""
    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["reuse"] for k, v in expected.items()},
                           Page.COL_REUSE, "Reuse")


@allure.epic("Overproduction Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Donation column values match seeded scan data")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="UI Donation per menu item matches seeded donation scan totals",
    steps=(
        "1. Seed scans via API\n"
        "2. Navigate to Overproduction Summary with default filters\n"
        "3. Compute expected donation from seeded payloads (types 3 and 8)\n"
        "4. For each seeded menu item assert UI Donation value matches expected (tolerance 0.01 lb)"
    ),
    key="FQL-122",
)
@pytest.mark.regression
def test_donation_matches_seeded_data(logged_in_page, seeded_basic_scans):
    """Donation column per menu item must match seeded donation scan totals."""
    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["donation"] for k, v in expected.items()},
                           Page.COL_DONATION, "Donation")


@allure.epic("Overproduction Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Compostable column values match seeded scan data")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="UI Compostable per menu item matches seeded compostable scan totals",
    steps=(
        "1. Seed scans via API\n"
        "2. Navigate to Overproduction Summary with default filters\n"
        "3. Compute expected compostable from seeded payloads (types 2 and 7)\n"
        "4. For each seeded menu item assert UI Compostable value matches expected (tolerance 0.01 lb)"
    ),
    key="FQL-123",
)
@pytest.mark.regression
def test_compostable_matches_seeded_data(logged_in_page, seeded_basic_scans):
    """Compostable column per menu item must match seeded compostable scan totals."""
    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["compostable"] for k, v in expected.items()},
                           Page.COL_COMPOSTABLE, "Compostable")


# ---------------------------------------------------------------------------
# Empty State
# ---------------------------------------------------------------------------

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
    key="FQL-124",
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



# ---------------------------------------------------------------------------
# Row Quality
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Row Quality")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("All rows have a non-empty Menu Item name")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Every row in the table must have a non-empty Menu Item cell",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Read all rows across all pages\n"
        "5. Assert no row has an empty or whitespace-only Menu Item value"
    ),
    key="FQL-125",
)
@pytest.mark.regression
def test_all_rows_have_non_empty_menu_item(logged_in_page, seeded_basic_scans):
    """Every row must have a non-empty Menu Item name."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    all_rows = page.get_all_rows()
    if not all_rows:
        print(NO_DATA_AVAILABLE)
        return

    empty = [i for i, r in enumerate(all_rows) if not r.get(Page.COL_MENU_ITEM, "").strip()]
    assert not empty, f"Rows with empty Menu Item at indices: {empty}"


@allure.epic("Overproduction Summary")
@allure.feature("Row Quality")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("All rows show only the selected venue")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="After selecting a specific venue, every row's Venue column matches that venue",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Select venue A filter\n"
        "4. Set date range\n"
        "5. Assert every row's Venue column equals venue A's name"
    ),
    key="FQL-126",
)
@pytest.mark.regression
def test_venue_filter_shows_only_selected_venue(logged_in_page, seeded_basic_scans):
    """All rows must show the selected venue name in the Venue column."""
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(CURRENT_VENUE_NAME)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    all_rows = page.get_all_rows()
    if not all_rows:
        print(NO_DATA_AVAILABLE)
        return

    wrong = [r.get(Page.COL_VENUE, "") for r in all_rows
             if r.get(Page.COL_VENUE, "") != CURRENT_VENUE_NAME]
    assert not wrong, (
        f"Rows with unexpected venue when '{CURRENT_VENUE_NAME}' selected: {wrong}"
    )


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Default sort is alphabetical by Menu Item name")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Without explicit sort, table rows are ordered alphabetically by Menu Item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Read Menu Item column values\n"
        "5. Assert they are in alphabetical (case-insensitive) ascending order"
    ),
    key="FQL-127",
)
@pytest.mark.regression
def test_default_sort_is_alphabetical_by_menu_item(logged_in_page, seeded_basic_scans):
    """Default table order must be alphabetical by Menu Item."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    rows = page.get_rows()
    if len(rows) < 2:
        pytest.skip("Need at least 2 rows to verify sort order")

    names = [r.get(Page.COL_MENU_ITEM, "").lower() for r in rows]
    assert names == sorted(names), (
        f"Menu Item names not alphabetical by default. Got: {names}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Reuse column sorts ascending on first click")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Clicking Reuse column header once produces ascending sort",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click Reuse column header\n"
        "5. Assert Reuse values are in ascending order"
    ),
    key="FQL-128",
)
@pytest.mark.regression
def test_reuse_sort_ascending(logged_in_page, seeded_basic_scans):
    """First click on Reuse column header must sort ascending."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if len(page.get_rows()) < 2:
        pytest.skip("Need at least 2 rows to test sort")

    page.click_column_sort(Page.COL_REUSE_BASE)
    rows = page.get_rows()
    assert _is_sorted_ascending(rows, Page.COL_REUSE), (
        f"Reuse not ascending after first sort click. Values: "
        f"{[_to_float(r.get(Page.COL_REUSE, '0')) for r in rows]}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Reuse column sorts descending on second click")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Clicking Reuse column header twice produces descending sort",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click Reuse column header twice\n"
        "5. Assert Reuse values are in descending order"
    ),
    key="FQL-129",
)
@pytest.mark.regression
def test_reuse_sort_descending(logged_in_page, seeded_basic_scans):
    """Second click on Reuse column header must sort descending."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if len(page.get_rows()) < 2:
        pytest.skip("Need at least 2 rows to test sort")

    page.click_column_sort(Page.COL_REUSE_BASE)
    page.click_column_sort(Page.COL_REUSE_BASE)
    rows = page.get_rows()
    assert _is_sorted_descending(rows, Page.COL_REUSE), (
        f"Reuse not descending after second sort click. Values: "
        f"{[_to_float(r.get(Page.COL_REUSE, '0')) for r in rows]}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Donation column sorts ascending on first click")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Clicking Donation column header once produces ascending sort",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click Donation column header\n"
        "5. Assert Donation values are in ascending order"
    ),
    key="FQL-130",
)
@pytest.mark.regression
def test_donation_sort_ascending(logged_in_page, seeded_basic_scans):
    """First click on Donation column header must sort ascending."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if len(page.get_rows()) < 2:
        pytest.skip("Need at least 2 rows to test sort")

    page.click_column_sort(Page.COL_DONATION_BASE)
    rows = page.get_rows()
    assert _is_sorted_ascending(rows, Page.COL_DONATION), (
        f"Donation not ascending after first sort click. Values: "
        f"{[_to_float(r.get(Page.COL_DONATION, '0')) for r in rows]}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Donation column sorts descending on second click")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Clicking Donation column header twice produces descending sort",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click Donation column header twice\n"
        "5. Assert Donation values are in descending order"
    ),
    key="FQL-131",
)
@pytest.mark.regression
def test_donation_sort_descending(logged_in_page, seeded_basic_scans):
    """Second click on Donation column header must sort descending."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if len(page.get_rows()) < 2:
        pytest.skip("Need at least 2 rows to test sort")

    page.click_column_sort(Page.COL_DONATION_BASE)
    page.click_column_sort(Page.COL_DONATION_BASE)
    rows = page.get_rows()
    assert _is_sorted_descending(rows, Page.COL_DONATION), (
        f"Donation not descending after second sort click. Values: "
        f"{[_to_float(r.get(Page.COL_DONATION, '0')) for r in rows]}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Compostable column sorts ascending on first click")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Clicking Compostable column header once produces ascending sort",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click Compostable column header\n"
        "5. Assert Compostable values are in ascending order"
    ),
    key="FQL-132",
)
@pytest.mark.regression
def test_compostable_sort_ascending(logged_in_page, seeded_basic_scans):
    """First click on Compostable column header must sort ascending."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if len(page.get_rows()) < 2:
        pytest.skip("Need at least 2 rows to test sort")

    page.click_column_sort(Page.COL_COMPOSTABLE_BASE)
    rows = page.get_rows()
    assert _is_sorted_ascending(rows, Page.COL_COMPOSTABLE), (
        f"Compostable not ascending after first sort click. Values: "
        f"{[_to_float(r.get(Page.COL_COMPOSTABLE, '0')) for r in rows]}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Compostable column sorts descending on second click")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Clicking Compostable column header twice produces descending sort",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click Compostable column header twice\n"
        "5. Assert Compostable values are in descending order"
    ),
    key="FQL-133",
)
@pytest.mark.regression
def test_compostable_sort_descending(logged_in_page, seeded_basic_scans):
    """Second click on Compostable column header must sort descending."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if len(page.get_rows()) < 2:
        pytest.skip("Need at least 2 rows to test sort")

    page.click_column_sort(Page.COL_COMPOSTABLE_BASE)
    page.click_column_sort(Page.COL_COMPOSTABLE_BASE)
    rows = page.get_rows()
    assert _is_sorted_descending(rows, Page.COL_COMPOSTABLE), (
        f"Compostable not descending after second sort click. Values: "
        f"{[_to_float(r.get(Page.COL_COMPOSTABLE, '0')) for r in rows]}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Sort order persists after changing the meal filter")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="A sort applied to Total Overproduction column persists after switching meal filter",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Sort Total Overproduction ascending\n"
        "5. Change meal filter to Lunch\n"
        "6. Assert Total Overproduction column is still in ascending order"
    ),
    key="FQL-134",
)
@pytest.mark.regression
def test_sort_persists_after_filter_change(logged_in_page, seeded_basic_scans):
    """Sort order on Total Overproduction must persist after changing the meal filter."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if len(page.get_rows()) < 2:
        pytest.skip("Need at least 2 rows to test sort persistence")

    page.click_column_sort(Page.COL_TOTAL_OVERPRODUCTION_BASE)

    page.set_meal(MEAL_LUNCH)
    rows = page.get_rows()

    if len(rows) < 2:
        pytest.skip("Lunch filter produced fewer than 2 rows — cannot verify sort")

    assert _is_sorted_ascending(rows, Page.COL_TOTAL_OVERPRODUCTION), (
        "Sort order not preserved after changing meal filter"
    )


# ---------------------------------------------------------------------------
# Breadcrumb — Extended
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Breadcrumb is unchanged after applying filters")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Applying venue, meal, and date filters does not change breadcrumb content",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Record initial breadcrumb text\n"
        "4. Apply venue, meal, category, and date filters\n"
        "5. Assert breadcrumb still shows 'Overproduction Summary'"
    ),
    key="FQL-135",
)
@pytest.mark.regression
def test_breadcrumb_unchanged_after_applying_filters(logged_in_page, seeded_basic_scans):
    """Breadcrumb must not change after filters are applied."""
    page = Page(logged_in_page)
    page.open_via_nav()

    _apply_filters(page)

    breadcrumb = page.page.locator(L.BREADCRUMB_PAGE_LINK)
    assert Page.SIDEBAR_ITEM in breadcrumb.inner_text(), (
        f"Breadcrumb changed after applying filters. Got: {breadcrumb.inner_text()}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Breadcrumb shows correct page after day view toggle")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Enabling day view toggle does not change breadcrumb content",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Toggle day view on\n"
        "5. Assert breadcrumb still shows 'Overproduction Summary'"
    ),
    key="FQL-136",
)
@pytest.mark.regression
def test_breadcrumb_unchanged_after_day_toggle(logged_in_page, seeded_basic_scans):
    """Breadcrumb must stay correct after toggling day view."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.toggle_day_view()

    breadcrumb = page.page.locator(L.BREADCRUMB_PAGE_LINK)
    assert Page.SIDEBAR_ITEM in breadcrumb.inner_text(), (
        f"Breadcrumb changed after day toggle. Got: {breadcrumb.inner_text()}"
    )
