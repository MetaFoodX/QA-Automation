"""Overproduction Summary — filter and export tests."""
import allure
import pytest

from dashboard.locators import common_locators as L
from dashboard.pages.overproduction_summary_page import OverproductionSummaryPage as Page
from dashboard.tests.executive_insights.overproduction_summary._helpers import (
    OZ_PER_LB,
    VENUE_ALL_OP,
    DESTINATION_ALL, DESTINATION_REUSE, DESTINATION_DONATION, DESTINATION_COMPOSTABLE,
    CURRENT_RESTAURANT_ID, CURRENT_VENUE_ID, CURRENT_VENUE_NAME,
    SECOND_VENUE_ID, SECOND_VENUE_NAME,
    LUNCH_SP_ID, DINNER_SP_ID, ALL_DAY_SP_ID,
    REUSE_TYPES, DONATION_TYPES, COMPOSTABLE_TYPES,
    _to_float, _apply_filters,
    _filter_for_current_view, _filter_by_service_period, _filter_by_category,
    _compute_expected_by_item,
    _assert_column_matches, _assert_headers_have_unit,
    _parse_export_csv,
)
from shared.data.test_constants import *  # noqa: F401, F403


# ---------------------------------------------------------------------------
# Destination Filter
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Destination Filter")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("'All Destinations' filter shows Reuse, Donation, and Compostable columns")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Default All Destinations filter renders all three destination columns",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters with All Destinations\n"
        "4. Assert Reuse, Donation, and Compostable columns are all present"
    ),
    key="FQL-137",
)
@pytest.mark.smoke
@pytest.mark.regression
def test_destination_all_shows_all_columns(logged_in_page, seeded_basic_scans):
    """All Destinations must render all three destination columns."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_destination(DESTINATION_ALL)

    headers = page.get_headers()
    for col in [Page.COL_REUSE, Page.COL_DONATION, Page.COL_COMPOSTABLE]:
        assert col in headers, f"Expected '{col}' in All Destinations view. Got: {headers}"


@allure.epic("Overproduction Summary")
@allure.feature("Destination Filter")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Reuse destination filter shows only Reuse column")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Selecting Reuse destination hides Donation and Compostable columns",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Set destination filter to 'Reuse'\n"
        "5. Assert Reuse (lb) column is present\n"
        "6. Assert Donation and Compostable columns are absent"
    ),
    key="FQL-138",
)
@pytest.mark.regression
def test_destination_reuse_shows_only_reuse_column(logged_in_page, seeded_basic_scans):
    """Reuse destination filter must show Reuse column and hide others."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_destination(DESTINATION_REUSE)

    headers = page.get_headers()
    assert Page.COL_REUSE in headers, f"Expected '{Page.COL_REUSE}'. Got: {headers}"
    assert Page.COL_DONATION not in headers, (
        f"'{Page.COL_DONATION}' should not appear with Reuse filter. Got: {headers}"
    )
    assert Page.COL_COMPOSTABLE not in headers, (
        f"'{Page.COL_COMPOSTABLE}' should not appear with Reuse filter. Got: {headers}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Destination Filter")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Donation destination filter shows only Donation column")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Selecting Donation destination hides Reuse and Compostable columns",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Set destination filter to 'Donation'\n"
        "5. Assert Donation (lb) column is present\n"
        "6. Assert Reuse and Compostable columns are absent"
    ),
    key="FQL-139",
)
@pytest.mark.regression
def test_destination_donation_shows_only_donation_column(logged_in_page, seeded_basic_scans):
    """Donation destination filter must show Donation column and hide others."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_destination(DESTINATION_DONATION)

    headers = page.get_headers()
    assert Page.COL_DONATION in headers, f"Expected '{Page.COL_DONATION}'. Got: {headers}"
    assert Page.COL_REUSE not in headers, (
        f"'{Page.COL_REUSE}' should not appear with Donation filter. Got: {headers}"
    )
    assert Page.COL_COMPOSTABLE not in headers, (
        f"'{Page.COL_COMPOSTABLE}' should not appear with Donation filter. Got: {headers}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Destination Filter")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Compostable destination filter shows only Compostable column")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Selecting Compostable destination hides Reuse and Donation columns",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Set destination filter to 'Compostable'\n"
        "5. Assert Compostable (lb) column is present\n"
        "6. Assert Reuse and Donation columns are absent"
    ),
    key="FQL-140",
)
@pytest.mark.regression
def test_destination_compostable_shows_only_compostable_column(logged_in_page, seeded_basic_scans):
    """Compostable destination filter must show Compostable column and hide others."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_destination(DESTINATION_COMPOSTABLE)

    headers = page.get_headers()
    assert Page.COL_COMPOSTABLE in headers, f"Expected '{Page.COL_COMPOSTABLE}'. Got: {headers}"
    assert Page.COL_REUSE not in headers, (
        f"'{Page.COL_REUSE}' should not appear with Compostable filter. Got: {headers}"
    )
    assert Page.COL_DONATION not in headers, (
        f"'{Page.COL_DONATION}' should not appear with Compostable filter. Got: {headers}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Destination Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Reuse filter: all visible rows have non-zero Reuse value")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="When Reuse destination is selected, all rows shown must have Reuse > 0",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Set destination to 'Reuse'\n"
        "5. Assert every row has Reuse (lb) > 0"
    ),
    key="FQL-141",
)
@pytest.mark.regression
def test_destination_reuse_rows_have_nonzero_reuse(logged_in_page, seeded_basic_scans):
    """With Reuse destination filter, only items with Reuse > 0 should appear."""
    relevant = _filter_for_current_view(seeded_basic_scans)
    has_reuse = any(p["Type"] in REUSE_TYPES for p in relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_destination(DESTINATION_REUSE)

    rows = page.get_rows()
    if not has_reuse:
        assert len(rows) == 0, "No reuse scans seeded but rows shown with Reuse filter"
        return

    failures = [
        f"'{r.get(Page.COL_MENU_ITEM, '')}': Reuse={_to_float(r.get(Page.COL_REUSE, '0'))}"
        for r in rows
        if _to_float(r.get(Page.COL_REUSE, "0")) <= 0
    ]
    assert not failures, (
        "Rows with zero Reuse shown under Reuse filter:\n  " + "\n  ".join(failures)
    )


@allure.epic("Overproduction Summary")
@allure.feature("Destination Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Donation filter: all visible rows have non-zero Donation value")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="When Donation destination is selected, all rows shown must have Donation > 0",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Set destination to 'Donation'\n"
        "5. Assert every row has Donation (lb) > 0"
    ),
    key="FQL-142",
)
@pytest.mark.regression
def test_destination_donation_rows_have_nonzero_donation(logged_in_page, seeded_basic_scans):
    """With Donation destination filter, only items with Donation > 0 should appear."""
    relevant = _filter_for_current_view(seeded_basic_scans)
    has_donation = any(p["Type"] in DONATION_TYPES for p in relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_destination(DESTINATION_DONATION)

    rows = page.get_rows()
    if not has_donation:
        assert len(rows) == 0, "No donation scans seeded but rows shown with Donation filter"
        return

    failures = [
        f"'{r.get(Page.COL_MENU_ITEM, '')}': Donation={_to_float(r.get(Page.COL_DONATION, '0'))}"
        for r in rows
        if _to_float(r.get(Page.COL_DONATION, "0")) <= 0
    ]
    assert not failures, (
        "Rows with zero Donation shown under Donation filter:\n  " + "\n  ".join(failures)
    )


@allure.epic("Overproduction Summary")
@allure.feature("Destination Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Compostable filter: all visible rows have non-zero Compostable value")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="When Compostable destination is selected, all rows shown must have Compostable > 0",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Set destination to 'Compostable'\n"
        "5. Assert every row has Compostable (lb) > 0"
    ),
    key="FQL-143",
)
@pytest.mark.regression
def test_destination_compostable_rows_have_nonzero_compostable(logged_in_page, seeded_basic_scans):
    """With Compostable destination filter, only items with Compostable > 0 should appear."""
    relevant = _filter_for_current_view(seeded_basic_scans)
    has_compostable = any(p["Type"] in COMPOSTABLE_TYPES for p in relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_destination(DESTINATION_COMPOSTABLE)

    rows = page.get_rows()
    if not has_compostable:
        assert len(rows) == 0, "No compostable scans seeded but rows shown with Compostable filter"
        return

    failures = [
        f"'{r.get(Page.COL_MENU_ITEM, '')}': Compostable={_to_float(r.get(Page.COL_COMPOSTABLE, '0'))}"
        for r in rows
        if _to_float(r.get(Page.COL_COMPOSTABLE, "0")) <= 0
    ]
    assert not failures, (
        "Rows with zero Compostable shown under Compostable filter:\n  " + "\n  ".join(failures)
    )


@allure.epic("Overproduction Summary")
@allure.feature("Destination Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Switching back to All Destinations restores all three columns")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="After filtering by Reuse then back to All Destinations, all columns return",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Set destination to 'Reuse'\n"
        "5. Set destination back to 'All Destinations'\n"
        "6. Assert Reuse, Donation, and Compostable columns all present"
    ),
    key="FQL-144",
)
@pytest.mark.regression
def test_destination_back_to_all_restores_columns(logged_in_page, seeded_basic_scans):
    """Switching back to All Destinations must restore all three destination columns."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.set_destination(DESTINATION_REUSE)
    page.set_destination(DESTINATION_ALL)

    headers = page.get_headers()
    for col in [Page.COL_REUSE, Page.COL_DONATION, Page.COL_COMPOSTABLE]:
        assert col in headers, (
            f"Expected '{col}' after switching back to All Destinations. Got: {headers}"
        )


# ---------------------------------------------------------------------------
# Venue Filter
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Venue Filter")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Venue filter changes data shown in the table")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Switching venue filter loads data for that venue only",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply filters with venue A and record Total Overproduction values\n"
        "4. Switch to venue B\n"
        "5. Assert table data changes (different set of items or different values)"
    ),
    key="FQL-145",
)
@pytest.mark.regression
def test_venue_filter_changes_data(logged_in_page, seeded_basic_scans):
    """Switching venue must change the table data."""
    v1_relevant = _filter_for_current_view(seeded_basic_scans, CURRENT_VENUE_ID)
    v2_relevant = _filter_for_current_view(seeded_basic_scans, SECOND_VENUE_ID)

    page = Page(logged_in_page)
    page.open_via_nav()

    page.set_venue(CURRENT_VENUE_NAME)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)
    rows_v1 = page.get_rows()

    page.set_venue(SECOND_VENUE_NAME)
    rows_v2 = page.get_rows()

    totals_v1 = {r.get(Page.COL_MENU_ITEM, ""): _to_float(r.get(Page.COL_TOTAL_OVERPRODUCTION, "0"))
                 for r in rows_v1}
    totals_v2 = {r.get(Page.COL_MENU_ITEM, ""): _to_float(r.get(Page.COL_TOTAL_OVERPRODUCTION, "0"))
                 for r in rows_v2}

    if not v1_relevant or not v2_relevant:
        return

    assert totals_v1 != totals_v2, (
        "Table data did not change when switching between venues"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Venue Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Venue A data matches seeded overproduction for that venue")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction values for venue A match seeded scan totals for that venue",
    steps=(
        "1. Seed scans for multiple venues\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Filter by venue A\n"
        "4. Compute expected totals from seeded payloads for venue A only\n"
        "5. Assert UI values match expected (tolerance 0.01 lb)"
    ),
    key="FQL-146",
)
@pytest.mark.regression
def test_venue_a_data_matches_seeded(logged_in_page, seeded_basic_scans):
    """Total Overproduction for venue A must match seeded totals for that venue."""
    relevant = _filter_for_current_view(seeded_basic_scans, CURRENT_VENUE_ID)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(CURRENT_VENUE_NAME)
    page.set_meal(MEAL_ALL)
    page.set_category(CATEGORY_ALL)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["total"] for k, v in expected.items()},
                           Page.COL_TOTAL_OVERPRODUCTION, "Total Overproduction (Venue A)")


@allure.epic("Overproduction Summary")
@allure.feature("Venue Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Venue B data matches seeded overproduction for that venue")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction values for venue B match seeded scan totals for that venue",
    steps=(
        "1. Seed scans for multiple venues\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Filter by venue B\n"
        "4. Compute expected totals from seeded payloads for venue B only\n"
        "5. Assert UI values match expected (tolerance 0.01 lb)"
    ),
    key="FQL-147",
)
@pytest.mark.regression
def test_venue_b_data_matches_seeded(logged_in_page, seeded_basic_scans):
    """Total Overproduction for venue B must match seeded totals for that venue."""
    relevant = _filter_for_current_view(seeded_basic_scans, SECOND_VENUE_ID)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(SECOND_VENUE_NAME)
    page.set_meal(MEAL_ALL)
    page.set_category(CATEGORY_ALL)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["total"] for k, v in expected.items()},
                           Page.COL_TOTAL_OVERPRODUCTION, "Total Overproduction (Venue B)")


# ---------------------------------------------------------------------------
# Meal Period Filters
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Math invariant Total = R + D + C holds per row with Lunch meal filter")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction = Reuse + Donation + Compostable for every row when Lunch filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters with Lunch meal period\n"
        "4. If no seeded data for Lunch, assert table is empty and pass\n"
        "5. For each row assert Total == Reuse + Donation + Compostable (tolerance 0.01)"
    ),
    key="FQL-148",
)
@pytest.mark.regression
def test_meal_lunch_math_invariant(logged_in_page, seeded_basic_scans):
    """Math invariant must hold when Lunch meal filter is applied."""
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), LUNCH_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_LUNCH)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0, "No lunch scans seeded but UI shows data"
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
            failures.append(f"'{item}': Total={total}, R+D+C={expected}")

    assert not failures, (
        "Math invariant violations with Lunch filter:\n  " + "\n  ".join(failures)
    )


@allure.epic("Overproduction Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Math invariant Total = R + D + C holds per row with Dinner meal filter")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction = Reuse + Donation + Compostable for every row when Dinner filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters with Dinner meal period\n"
        "4. If no seeded data for Dinner, assert table is empty and pass\n"
        "5. For each row assert Total == Reuse + Donation + Compostable (tolerance 0.01)"
    ),
    key="FQL-149",
)
@pytest.mark.regression
def test_meal_dinner_math_invariant(logged_in_page, seeded_basic_scans):
    """Math invariant must hold when Dinner meal filter is applied."""
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), DINNER_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DINNER)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0, "No dinner scans seeded but UI shows data"
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
            failures.append(f"'{item}': Total={total}, R+D+C={expected}")

    assert not failures, (
        "Math invariant violations with Dinner filter:\n  " + "\n  ".join(failures)
    )


@allure.epic("Overproduction Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Lunch overproduction data matches seeded Lunch scans")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction with Lunch filter matches seeded scan totals for Lunch service period",
    steps=(
        "1. Seed scans with Lunch service period\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Lunch meal filter\n"
        "4. Compute expected totals from seeded Lunch payloads\n"
        "5. Assert UI values match expected (tolerance 0.01 lb)"
    ),
    key="FQL-150",
)
@pytest.mark.regression
def test_meal_lunch_data_accuracy(logged_in_page, seeded_basic_scans):
    """Total Overproduction with Lunch filter must match seeded Lunch totals."""
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), LUNCH_SP_ID)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_LUNCH)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["total"] for k, v in expected.items()},
                           Page.COL_TOTAL_OVERPRODUCTION, "Total Overproduction (Lunch)")


@allure.epic("Overproduction Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Dinner overproduction data matches seeded Dinner scans")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction with Dinner filter matches seeded scan totals for Dinner service period",
    steps=(
        "1. Seed scans with Dinner service period\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Dinner meal filter\n"
        "4. Compute expected totals from seeded Dinner payloads\n"
        "5. Assert UI values match expected (tolerance 0.01 lb)"
    ),
    key="FQL-151",
)
@pytest.mark.regression
def test_meal_dinner_data_accuracy(logged_in_page, seeded_basic_scans):
    """Total Overproduction with Dinner filter must match seeded Dinner totals."""
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), DINNER_SP_ID)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DINNER)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["total"] for k, v in expected.items()},
                           Page.COL_TOTAL_OVERPRODUCTION, "Total Overproduction (Dinner)")


# ---------------------------------------------------------------------------
# Category Filter
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Category Filter")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Vegetables category filter shows only Vegetables menu items")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Selecting Vegetables category shows only menu items in that category",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters with Vegetables category\n"
        "4. Assert all visible rows contain only Vegetables menu items"
    ),
    key="FQL-152",
)
@pytest.mark.regression
def test_category_vegetables_shows_only_vegetables(logged_in_page, seeded_basic_scans):
    """Vegetables category filter must show only Vegetables menu items."""
    from shared.data.fixtures import RESTAURANT_A
    vegetable_items = {mi.name for mi in RESTAURANT_A.menu_items.values()
                       if mi.category == CATEGORY_VEGETABLES}

    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_VEGETABLES)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_category(CATEGORY_VEGETABLES)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0, "No Vegetables scans seeded but rows shown"
        return

    unexpected = [
        r.get(Page.COL_MENU_ITEM, "")
        for r in rows
        if r.get(Page.COL_MENU_ITEM, "") not in vegetable_items
    ]
    assert not unexpected, (
        f"Non-Vegetable items shown with Vegetables filter: {unexpected}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Category Filter")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Fruits category filter shows only Fruits menu items")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Selecting Fruits category shows only menu items in that category",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters with Fruits category\n"
        "4. Assert all visible rows contain only Fruits menu items"
    ),
    key="FQL-153",
)
@pytest.mark.regression
def test_category_fruits_shows_only_fruits(logged_in_page, seeded_basic_scans):
    """Fruits category filter must show only Fruits menu items."""
    from shared.data.fixtures import RESTAURANT_A
    fruit_items = {mi.name for mi in RESTAURANT_A.menu_items.values()
                   if mi.category == CATEGORY_FRUITS}

    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_FRUITS)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_category(CATEGORY_FRUITS)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0, "No Fruits scans seeded but rows shown"
        return

    unexpected = [
        r.get(Page.COL_MENU_ITEM, "")
        for r in rows
        if r.get(Page.COL_MENU_ITEM, "") not in fruit_items
    ]
    assert not unexpected, (
        f"Non-Fruit items shown with Fruits filter: {unexpected}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Category Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Vegetables category data accuracy matches seeded scan totals")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction with Vegetables filter matches seeded totals for Vegetables items",
    steps=(
        "1. Seed scans for Vegetables category items\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Vegetables category filter\n"
        "4. Compute expected totals from seeded Vegetables payloads\n"
        "5. Assert UI values match expected (tolerance 0.01 lb)"
    ),
    key="FQL-154",
)
@pytest.mark.regression
def test_category_vegetables_data_accuracy(logged_in_page, seeded_basic_scans):
    """Total Overproduction with Vegetables filter must match seeded Vegetables totals."""
    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_VEGETABLES)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_category(CATEGORY_VEGETABLES)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["total"] for k, v in expected.items()},
                           Page.COL_TOTAL_OVERPRODUCTION, "Total Overproduction (Vegetables)")


@allure.epic("Overproduction Summary")
@allure.feature("Category Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Fruits category data accuracy matches seeded scan totals")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction with Fruits filter matches seeded totals for Fruits items",
    steps=(
        "1. Seed scans for Fruits category items\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Fruits category filter\n"
        "4. Compute expected totals from seeded Fruits payloads\n"
        "5. Assert UI values match expected (tolerance 0.01 lb)"
    ),
    key="FQL-155",
)
@pytest.mark.regression
def test_category_fruits_data_accuracy(logged_in_page, seeded_basic_scans):
    """Total Overproduction with Fruits filter must match seeded Fruits totals."""
    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_FRUITS)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_category(CATEGORY_FRUITS)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["total"] for k, v in expected.items()},
                           Page.COL_TOTAL_OVERPRODUCTION, "Total Overproduction (Fruits)")


# ---------------------------------------------------------------------------
# Menu Item Search Filter
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Search")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Menu item search filters table to show only the selected item")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Searching for a specific menu item shows only that item in the table",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Open menu item search and select the first seeded item with overproduction\n"
        "5. Assert table shows only that menu item"
    ),
    key="FQL-156",
)
@pytest.mark.regression
def test_menu_item_search_filters_to_single_item(logged_in_page, seeded_basic_scans):
    """Searching for a specific menu item must show only that item."""
    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = _compute_expected_by_item(relevant)

    if not expected:
        pytest.skip("No overproduction seeded data for this venue")

    target_item = "Corn"

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(CURRENT_VENUE_NAME)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    page.click_search_toggle()
    page.select_menu_items_in_search(target_item)

    rows = page.get_rows()
    assert len(rows) >= 1, f"Expected at least 1 row for '{target_item}', got 0"
    items_in_table = {r.get(Page.COL_MENU_ITEM, "") for r in rows}
    assert items_in_table == {target_item}, (
        f"Expected only '{target_item}' after search filter. Got: {items_in_table}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Search")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clearing menu item search restores all rows")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Clearing the menu item search filter brings back all overproduction items",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters and record row count\n"
        "4. Open menu item search and select one item\n"
        "5. Clear the search\n"
        "6. Assert table returns to original row count"
    ),
    key="FQL-157",
)
@pytest.mark.regression
def test_clearing_menu_item_search_restores_all_rows(logged_in_page, seeded_basic_scans):
    """Clearing the menu item search must restore all overproduction rows."""
    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = _compute_expected_by_item(relevant)

    if not expected:
        pytest.skip("No overproduction seeded data for this venue")

    target_item = "Corn"
    if target_item not in expected:
        pytest.skip(f"'{target_item}' has no overproduction data in the seeded date range")

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(CURRENT_VENUE_NAME)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    initial_count = len(page.get_rows())

    page.click_search_toggle()
    page.select_menu_items_in_search(target_item)
    filtered_count = len(page.get_rows())

    page.clear_menu_item_search()
    restored_count = len(page.get_rows())

    assert restored_count == initial_count, (
        f"Row count after clearing search: {restored_count}, expected {initial_count}"
    )
    if len(expected) > 1:
        assert filtered_count < initial_count, (
            "Filtered count should be less than initial when more than 1 item exists"
        )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Export button is enabled when data is loaded")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Export button must be enabled when the table has data",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters with seeded data\n"
        "4. Assert export button is enabled"
    ),
    key="FQL-158",
)
@pytest.mark.smoke
@pytest.mark.regression
def test_export_button_enabled_with_data(logged_in_page, seeded_basic_scans):
    """Export button must be enabled when the table has data."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    rows = page.get_rows()
    if not rows:
        pytest.skip("No data in table — cannot test export enabled state")

    assert page.is_export_button_enabled(), "Export button should be enabled when data is present"


@allure.epic("Overproduction Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Export downloads a CSV file")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Clicking the export button triggers a CSV file download",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click the export button\n"
        "5. Assert a file download starts and the file is non-empty"
    ),
    key="FQL-159",
)
@pytest.mark.regression
def test_export_downloads_csv_file(logged_in_page, seeded_basic_scans):
    """Export button must trigger a file download."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    rows = page.get_rows()
    if not rows:
        pytest.skip("No data in table — cannot test export download")

    download = page.download_export()
    assert download is not None, "No download triggered after clicking export"
    assert download.path() is not None, "Downloaded file has no local path"


@allure.epic("Overproduction Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Exported CSV has expected column headers")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="CSV export file contains expected column headers for overproduction data",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Export CSV\n"
        "5. Parse downloaded file and assert 'Menu Item' and 'Venue' columns are present"
    ),
    key="FQL-160",
)
@pytest.mark.regression
def test_export_csv_has_expected_headers(logged_in_page, seeded_basic_scans):
    """Exported CSV must contain core column headers."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    rows = page.get_rows()
    if not rows:
        pytest.skip("No data in table — cannot test export headers")

    download = page.download_export()
    parsed = _parse_export_csv(download)

    assert parsed["headers"], "CSV has no headers"
    assert any("Menu Item" in h for h in parsed["headers"]), (
        f"'Menu Item' column not found in CSV headers: {parsed['headers']}"
    )
    assert any("Venue" in h for h in parsed["headers"]), (
        f"'Venue' column not found in CSV headers: {parsed['headers']}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Exported CSV contains at least one data row")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="CSV export file contains at least one data row when table has data",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Export CSV\n"
        "5. Parse downloaded file and assert it has >= 1 data rows"
    ),
    key="FQL-161",
)
@pytest.mark.regression
def test_export_csv_has_data_rows(logged_in_page, seeded_basic_scans):
    """Exported CSV must contain data rows when the table has data."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    rows = page.get_rows()
    if not rows:
        pytest.skip("No data in table — cannot test export data rows")

    download = page.download_export()
    parsed = _parse_export_csv(download)

    assert len(parsed["rows"]) >= 1, (
        f"CSV has no data rows even though table showed {len(rows)} rows"
    )


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking Total Overproduction header sorts column in ascending then descending order")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Two clicks on Total Overproduction header produce ascending then descending sort",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Click Total Overproduction column header once\n"
        "5. Assert values are in ascending order\n"
        "6. Click again\n"
        "7. Assert values are in descending order"
    ),
    key="FQL-162",
)
@pytest.mark.regression
def test_sort_total_overproduction_ascending_then_descending(logged_in_page, seeded_basic_scans):
    """Total Overproduction column header must cycle sort asc → desc."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    rows = page.get_rows()
    if len(rows) < 2:
        pytest.skip("Need at least 2 rows to test sort order")

    page.click_column_sort(Page.COL_TOTAL_OVERPRODUCTION_BASE)
    asc_rows = page.get_rows()
    asc_values = [_to_float(r.get(Page.COL_TOTAL_OVERPRODUCTION, "0")) for r in asc_rows]
    assert asc_values == sorted(asc_values), (
        f"Expected ascending order after first sort click. Got: {asc_values}"
    )

    page.click_column_sort(Page.COL_TOTAL_OVERPRODUCTION_BASE)
    desc_rows = page.get_rows()
    desc_values = [_to_float(r.get(Page.COL_TOTAL_OVERPRODUCTION, "0")) for r in desc_rows]
    assert desc_values == sorted(desc_values, reverse=True), (
        f"Expected descending order after second sort click. Got: {desc_values}"
    )


# ---------------------------------------------------------------------------
# Day View with Filters
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Day View")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Day view with Reuse destination shows Date column and Reuse values")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Day view combined with Reuse destination filter shows per-date rows with Reuse column",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Enable Day view toggle\n"
        "5. Set destination to Reuse\n"
        "6. Assert Date column is present and Reuse column is present"
    ),
    key="FQL-163",
)
@pytest.mark.regression
def test_day_view_with_reuse_destination(logged_in_page, seeded_basic_scans):
    """Day view + Reuse destination filter must show Date column and Reuse values."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.toggle_day_view()
    page.set_destination(DESTINATION_REUSE)

    headers = page.get_headers()
    assert Page.COL_DATE in headers, f"Expected 'Date' column in day view. Got: {headers}"
    assert Page.COL_REUSE in headers, f"Expected '{Page.COL_REUSE}' column. Got: {headers}"


@allure.epic("Overproduction Summary")
@allure.feature("Day View")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Day view shows multiple rows per menu item when data spans multiple dates")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="In day view, a menu item with data on multiple dates produces one row per date",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Enable Day view\n"
        "5. Assert total row count >= non-day view row count (day view splits by date)"
    ),
    key="FQL-164",
)
@pytest.mark.regression
def test_day_view_shows_more_rows_than_combined_view(logged_in_page, seeded_basic_scans):
    """Day view should produce >= as many rows as combined view (same or more due to date split)."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    combined_count = len(page.get_rows())
    if combined_count == 0:
        pytest.skip("No data to verify day view row expansion")

    page.toggle_day_view()
    day_count = len(page.get_rows())

    assert day_count >= combined_count, (
        f"Day view ({day_count} rows) should have >= rows than combined view ({combined_count} rows)"
    )


# ---------------------------------------------------------------------------
# Meal Period — Completions
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Lunch filter shows only items with Lunch overproduction scans")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Lunch filter hides all items that have no overproduction scans in the Lunch service period",
    steps=(
        "1. Seed overproduction scans for Lunch and Dinner service periods\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Lunch meal filter\n"
        "4. Assert only items with Lunch overproduction scans appear"
    ),
    key="FQL-165",
)
@pytest.mark.regression
def test_meal_lunch_shows_only_lunch_items(logged_in_page, seeded_basic_scans):
    """Lunch filter must show only items that have Lunch overproduction scans."""
    from dashboard.tests.executive_insights.overproduction_summary._helpers import _filter_items_for_service_period
    all_relevant = _filter_for_current_view(seeded_basic_scans)
    lunch_items = _filter_items_for_service_period(all_relevant, LUNCH_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_LUNCH)

    rows = page.get_rows()
    if not lunch_items:
        assert len(rows) == 0, "No Lunch OP scans seeded but rows appear"
        return

    unexpected = [r.get(Page.COL_MENU_ITEM, "") for r in rows
                  if r.get(Page.COL_MENU_ITEM, "") not in lunch_items]
    assert not unexpected, f"Items not from Lunch shown with Lunch filter: {unexpected}"


@allure.epic("Overproduction Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Dinner filter shows only items with Dinner overproduction scans")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Dinner filter hides all items that have no overproduction scans in the Dinner service period",
    steps=(
        "1. Seed overproduction scans for Lunch and Dinner service periods\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Dinner meal filter\n"
        "4. Assert only items with Dinner overproduction scans appear"
    ),
    key="FQL-166",
)
@pytest.mark.regression
def test_meal_dinner_shows_only_dinner_items(logged_in_page, seeded_basic_scans):
    """Dinner filter must show only items that have Dinner overproduction scans."""
    from dashboard.tests.executive_insights.overproduction_summary._helpers import _filter_items_for_service_period
    all_relevant = _filter_for_current_view(seeded_basic_scans)
    dinner_items = _filter_items_for_service_period(all_relevant, DINNER_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DINNER)

    rows = page.get_rows()
    if not dinner_items:
        assert len(rows) == 0, "No Dinner OP scans seeded but rows appear"
        return

    unexpected = [r.get(Page.COL_MENU_ITEM, "") for r in rows
                  if r.get(Page.COL_MENU_ITEM, "") not in dinner_items]
    assert not unexpected, f"Items not from Dinner shown with Dinner filter: {unexpected}"


@allure.epic("Overproduction Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("All Day filter shows only items with All Day overproduction scans")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="All Day filter shows only items seeded under All Day service period",
    steps=(
        "1. Seed overproduction scans for All Day service period\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply All Day meal filter\n"
        "4. Assert only items with All Day overproduction scans appear"
    ),
    key="FQL-167",
)
@pytest.mark.regression
def test_meal_all_day_shows_only_all_day_items(logged_in_page, seeded_basic_scans):
    """All Day filter must show only items that have All Day overproduction scans."""
    from dashboard.tests.executive_insights.overproduction_summary._helpers import _filter_items_for_service_period
    all_relevant = _filter_for_current_view(seeded_basic_scans)
    all_day_items = _filter_items_for_service_period(all_relevant, ALL_DAY_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DAY)

    rows = page.get_rows()
    if not all_day_items:
        assert len(rows) == 0, "No All Day OP scans seeded but rows appear"
        return

    unexpected = [r.get(Page.COL_MENU_ITEM, "") for r in rows
                  if r.get(Page.COL_MENU_ITEM, "") not in all_day_items]
    assert not unexpected, f"Items not from All Day shown with All Day filter: {unexpected}"


@allure.epic("Overproduction Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Math invariant Total = R + D + C holds per row with All Day meal filter")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction = Reuse + Donation + Compostable for every row when All Day filter applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply All Day meal filter\n"
        "4. For each row assert Total == Reuse + Donation + Compostable (tolerance 0.01)"
    ),
    key="FQL-168",
)
@pytest.mark.regression
def test_meal_all_day_math_invariant(logged_in_page, seeded_basic_scans):
    """Math invariant must hold when All Day meal filter is applied."""
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), ALL_DAY_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DAY)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0, "No All Day scans seeded but UI shows data"
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
            failures.append(f"'{item}': Total={total}, R+D+C={expected}")

    assert not failures, "Math invariant violations with All Day filter:\n  " + "\n  ".join(failures)


@allure.epic("Overproduction Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("All Day overproduction data matches seeded All Day scans")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total Overproduction with All Day filter matches seeded scan totals for All Day service period",
    steps=(
        "1. Seed All Day overproduction scans\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply All Day meal filter\n"
        "4. Assert UI values match expected (tolerance 0.01 lb)"
    ),
    key="FQL-169",
)
@pytest.mark.regression
def test_meal_all_day_data_accuracy(logged_in_page, seeded_basic_scans):
    """Total Overproduction with All Day filter must match seeded All Day totals."""
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), ALL_DAY_SP_ID)
    expected = _compute_expected_by_item(relevant)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DAY)

    if not expected:
        print(NO_DATA_AVAILABLE)
        return

    _assert_column_matches(page, {k: v["total"] for k, v in expected.items()},
                           Page.COL_TOTAL_OVERPRODUCTION, "Total Overproduction (All Day)")


# ---------------------------------------------------------------------------
# Category Filter — Completions
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Category Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Fruits category: math invariant Total = R + D + C holds per row")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Math invariant holds for all rows when Fruits category filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Fruits category filter\n"
        "4. For each row assert Total == Reuse + Donation + Compostable (tolerance 0.01)"
    ),
    key="FQL-170",
)
@pytest.mark.regression
def test_category_fruits_math_invariant(logged_in_page, seeded_basic_scans):
    """Math invariant must hold when Fruits category filter is applied."""
    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_FRUITS)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_category(CATEGORY_FRUITS)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0
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
            failures.append(f"'{item}': Total={total}, R+D+C={expected}")

    assert not failures, "Math invariant violations with Fruits filter:\n  " + "\n  ".join(failures)


@allure.epic("Overproduction Summary")
@allure.feature("Category Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Vegetables category: math invariant Total = R + D + C holds per row")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Math invariant holds for all rows when Vegetables category filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Vegetables category filter\n"
        "4. For each row assert Total == Reuse + Donation + Compostable (tolerance 0.01)"
    ),
    key="FQL-171",
)
@pytest.mark.regression
def test_category_vegetables_math_invariant(logged_in_page, seeded_basic_scans):
    """Math invariant must hold when Vegetables category filter is applied."""
    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_VEGETABLES)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_category(CATEGORY_VEGETABLES)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0
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
            failures.append(f"'{item}': Total={total}, R+D+C={expected}")

    assert not failures, "Math invariant violations with Vegetables filter:\n  " + "\n  ".join(failures)


@allure.epic("Overproduction Summary")
@allure.feature("Category Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Kitchen Waste category filter shows only Kitchen Waste items")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Selecting Kitchen Waste category shows only kitchen waste items in the table",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Kitchen Waste category filter\n"
        "4. Assert all rows contain only Kitchen Waste menu items"
    ),
    key="FQL-172",
)
@pytest.mark.regression
def test_category_kitchen_waste_shows_only_kw_items(logged_in_page, seeded_basic_scans):
    """Kitchen Waste filter must show only Kitchen Waste items."""
    from shared.data.fixtures import RESTAURANT_A
    kw_items = {mi.name for mi in RESTAURANT_A.menu_items.values()
                if mi.category == CATEGORY_KITCHEN_WASTE}

    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_KITCHEN_WASTE)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_category(CATEGORY_KITCHEN_WASTE)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0, "No Kitchen Waste OP scans seeded but rows appear"
        return

    unexpected = [r.get(Page.COL_MENU_ITEM, "") for r in rows
                  if r.get(Page.COL_MENU_ITEM, "") not in kw_items]
    assert not unexpected, f"Non-KW items shown with Kitchen Waste filter: {unexpected}"


@allure.epic("Overproduction Summary")
@allure.feature("Category Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Post Consumer category filter shows only Post Consumer items")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Selecting Post Consumer category shows only post consumer items in the table",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Post Consumer category filter\n"
        "4. Assert all rows contain only Post Consumer menu items"
    ),
    key="FQL-173",
)
@pytest.mark.regression
def test_category_post_consumer_shows_only_pc_items(logged_in_page, seeded_basic_scans):
    """Post Consumer filter must show only Post Consumer items."""
    from shared.data.fixtures import RESTAURANT_A
    pc_items = {mi.name for mi in RESTAURANT_A.menu_items.values()
                if mi.category == CATEGORY_POST_CONSUMER}

    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_POST_CONSUMER)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_category(CATEGORY_POST_CONSUMER)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0, "No Post Consumer OP scans seeded but rows appear"
        return

    unexpected = [r.get(Page.COL_MENU_ITEM, "") for r in rows
                  if r.get(Page.COL_MENU_ITEM, "") not in pc_items]
    assert not unexpected, f"Non-PC items shown with Post Consumer filter: {unexpected}"


# ---------------------------------------------------------------------------
# Combined Filters
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Combined Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Fruits + Lunch combined filter: math invariant holds")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total = Reuse + Donation + Compostable for all rows when Fruits category and Lunch meal are both applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Fruits category filter and Lunch meal filter\n"
        "4. For each row assert Total == Reuse + Donation + Compostable"
    ),
    key="FQL-174",
)
@pytest.mark.regression
def test_combined_fruits_lunch_math_invariant(logged_in_page, seeded_basic_scans):
    """Math invariant must hold with combined Fruits + Lunch filter."""
    relevant = _filter_by_service_period(
        _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_FRUITS),
        LUNCH_SP_ID,
    )

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_category(CATEGORY_FRUITS)
    page.set_meal(MEAL_LUNCH)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0
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
            failures.append(f"'{item}': Total={total}, R+D+C={expected}")

    assert not failures, "Math violations with Fruits+Lunch:\n  " + "\n  ".join(failures)


@allure.epic("Overproduction Summary")
@allure.feature("Combined Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Vegetables + Dinner combined filter: math invariant holds")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Total = Reuse + Donation + Compostable for all rows when Vegetables category and Dinner meal are both applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Vegetables category filter and Dinner meal filter\n"
        "4. For each row assert Total == Reuse + Donation + Compostable"
    ),
    key="FQL-175",
)
@pytest.mark.regression
def test_combined_vegetables_dinner_math_invariant(logged_in_page, seeded_basic_scans):
    """Math invariant must hold with combined Vegetables + Dinner filter."""
    relevant = _filter_by_service_period(
        _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_VEGETABLES),
        DINNER_SP_ID,
    )

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_category(CATEGORY_VEGETABLES)
    page.set_meal(MEAL_DINNER)

    rows = page.get_rows()
    if not relevant:
        assert len(rows) == 0
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
            failures.append(f"'{item}': Total={total}, R+D+C={expected}")

    assert not failures, "Math violations with Vegetables+Dinner:\n  " + "\n  ".join(failures)


@allure.epic("Overproduction Summary")
@allure.feature("Combined Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Changing category preserves the current meal filter")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="After applying Lunch meal filter, switching category should keep Lunch still selected",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Lunch meal filter\n"
        "4. Change category to Fruits\n"
        "5. Assert meal filter still shows Lunch as selected"
    ),
    key="FQL-176",
)
@pytest.mark.regression
def test_category_change_preserves_meal_filter(logged_in_page, seeded_basic_scans):
    """Changing category must not reset the meal filter."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.set_meal(MEAL_LUNCH)
    page.set_category(CATEGORY_FRUITS)

    assert page.is_filter_selected(MEAL_LUNCH), (
        f"Meal filter '{MEAL_LUNCH}' was reset when category changed"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Combined Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Changing meal preserves the current category filter")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="After applying Fruits category filter, switching meal should keep Fruits still selected",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Fruits category filter\n"
        "4. Change meal to Dinner\n"
        "5. Assert category filter still shows Fruits as selected"
    ),
    key="FQL-177",
)
@pytest.mark.regression
def test_meal_change_preserves_category_filter(logged_in_page, seeded_basic_scans):
    """Changing meal must not reset the category filter."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.set_category(CATEGORY_FRUITS)
    page.set_meal(MEAL_DINNER)

    assert page.is_filter_selected(CATEGORY_FRUITS), (
        f"Category filter '{CATEGORY_FRUITS}' was reset when meal changed"
    )


# ---------------------------------------------------------------------------
# All Venues
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Venue Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("All Venues shows rows from both venues")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Selecting All Venues displays overproduction data from every venue",
    steps=(
        "1. Seed overproduction scans for two venues\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Select All Venues filter\n"
        "4. Assert Venue column contains entries from both venue A and venue B"
    ),
    key="FQL-178",
)
@pytest.mark.regression
def test_all_venues_shows_rows_from_both_venues(logged_in_page, seeded_basic_scans):
    """All Venues must show rows from both seeded venues."""
    v1_relevant = _filter_for_current_view(seeded_basic_scans, CURRENT_VENUE_ID)
    v2_relevant = _filter_for_current_view(seeded_basic_scans, SECOND_VENUE_ID)

    if not v1_relevant or not v2_relevant:
        pytest.skip("Need overproduction scans for both venues")

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(VENUE_ALL_OP)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    all_rows = page.get_all_rows()
    venues_seen = {r.get(Page.COL_VENUE, "") for r in all_rows}

    assert CURRENT_VENUE_NAME in venues_seen, (
        f"'{CURRENT_VENUE_NAME}' not found in All Venues view. Seen: {venues_seen}"
    )
    assert SECOND_VENUE_NAME in venues_seen, (
        f"'{SECOND_VENUE_NAME}' not found in All Venues view. Seen: {venues_seen}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Venue Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("All Venues: math invariant Total = R + D + C holds for all rows")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Math invariant holds for all rows when All Venues is selected",
    steps=(
        "1. Navigate to Overproduction Summary\n"
        "2. Select All Venues\n"
        "3. For each row assert Total == Reuse + Donation + Compostable"
    ),
    key="FQL-179",
)
@pytest.mark.regression
def test_all_venues_math_invariant(logged_in_page, seeded_basic_scans):
    """Math invariant must hold across all venues."""
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(VENUE_ALL_OP)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

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
            failures.append(f"'{item}': Total={total}, R+D+C={expected}")

    assert not failures, "Math invariant violations with All Venues:\n  " + "\n  ".join(failures)


@allure.epic("Overproduction Summary")
@allure.feature("Venue Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Venue B filter shows only Venue B rows")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="After selecting venue B, every row's Venue column must show venue B's name",
    steps=(
        "1. Navigate to Overproduction Summary\n"
        "2. Select venue B filter\n"
        "3. Assert every row's Venue column equals venue B's name"
    ),
    key="FQL-180",
)
@pytest.mark.regression
def test_second_venue_shows_only_that_venue(logged_in_page, seeded_basic_scans):
    """All rows must show venue B's name when venue B is selected."""
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(SECOND_VENUE_NAME)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    all_rows = page.get_all_rows()
    if not all_rows:
        print(NO_DATA_AVAILABLE)
        return

    wrong = [r.get(Page.COL_VENUE, "") for r in all_rows
             if r.get(Page.COL_VENUE, "") != SECOND_VENUE_NAME]
    assert not wrong, (
        f"Rows with unexpected venue when '{SECOND_VENUE_NAME}' selected: {wrong}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Venue Filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Venue B: math invariant Total = R + D + C holds for all rows")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Math invariant holds for all rows when venue B is selected",
    steps=(
        "1. Navigate to Overproduction Summary\n"
        "2. Select venue B\n"
        "3. For each row assert Total == Reuse + Donation + Compostable"
    ),
    key="FQL-181",
)
@pytest.mark.regression
def test_second_venue_math_invariant(logged_in_page, seeded_basic_scans):
    """Math invariant must hold when venue B is selected."""
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(SECOND_VENUE_NAME)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

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
            failures.append(f"'{item}': Total={total}, R+D+C={expected}")

    assert not failures, "Math invariant violations with venue B:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Menu Item Search — Completions
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Search")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Search button is visible in the header")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="The menu item search toggle button is visible in the filter header",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Assert the search/filter icon button is visible in the header"
    ),
    key="FQL-182",
)
@pytest.mark.regression
def test_search_button_visible_in_header(logged_in_page):
    """Search button must be visible in the Overproduction Summary header."""
    page = Page(logged_in_page)
    page.open_via_nav()

    assert not page.is_search_active(), "Search select should be hidden before toggling"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Search")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Search button toggles the menu item multi-select visible and hidden")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Clicking the search button shows the menu item select; clicking again hides it",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Click the search button\n"
        "4. Assert menu item select appears\n"
        "5. Click the minimize button\n"
        "6. Assert menu item select disappears"
    ),
    key="FQL-183",
)
@pytest.mark.regression
def test_search_button_toggles_menu_item_select(logged_in_page):
    """Search button must show/hide the menu item multi-select."""
    page = Page(logged_in_page)
    page.open_via_nav()

    page.click_search_toggle()
    assert page.is_search_active(), "Menu item select should be visible after first toggle"

    page.click_search_toggle()
    assert not page.is_search_active(), "Menu item select should be hidden after second toggle"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Search")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Selecting multiple menu items shows all selected items")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Selecting two items in the menu item search shows rows for both items",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Open menu item search and select two items\n"
        "5. Assert table shows exactly those two items"
    ),
    key="FQL-184",
)
@pytest.mark.regression
def test_search_multiple_items_shows_all_selected(logged_in_page, seeded_basic_scans):
    """Selecting two items via search must show both in the table."""
    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = _compute_expected_by_item(relevant)

    items = ["Bananas", "Corn"]
    missing = [i for i in items if i not in expected]
    if missing:
        pytest.skip(f"{missing} have no overproduction data in the seeded date range")

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(CURRENT_VENUE_NAME)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    page.click_search_toggle()
    page.select_menu_items_in_search(*items)

    rows = page.get_rows()
    items_in_table = {r.get(Page.COL_MENU_ITEM, "") for r in rows}
    assert items_in_table == set(items), (
        f"Expected items {set(items)} after multi-select. Got: {items_in_table}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Search")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Menu item search combined with meal filter scopes results correctly")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Searching for an item while Lunch meal filter is active shows only that item's Lunch data",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply Lunch meal filter\n"
        "4. Open menu item search and select one item\n"
        "5. Assert table shows only that item"
    ),
    key="FQL-185",
)
@pytest.mark.regression
def test_search_combined_with_meal_filter(logged_in_page, seeded_basic_scans):
    """Search combined with meal filter must scope to that item + meal only."""
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), LUNCH_SP_ID)
    expected = _compute_expected_by_item(relevant)

    if not expected:
        pytest.skip("No Lunch overproduction scans seeded")

    target_item = "Corn"
    if target_item not in expected:
        pytest.skip(f"'{target_item}' has no overproduction data in the Lunch seeded date range")

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(CURRENT_VENUE_NAME)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)
    page.set_meal(MEAL_LUNCH)

    page.click_search_toggle()
    page.select_menu_items_in_search(target_item)

    rows = page.get_rows()
    items_in_table = {r.get(Page.COL_MENU_ITEM, "") for r in rows}
    assert items_in_table <= {target_item}, (
        f"Expected only '{target_item}' with Lunch+search. Got: {items_in_table}"
    )


# ---------------------------------------------------------------------------
# Export — Completions
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Exported CSV row count matches number of visible table rows")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="The number of data rows in the CSV export matches the number of rows in the UI table",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Count table rows\n"
        "5. Export CSV\n"
        "6. Assert CSV data rows count matches table rows count"
    ),
    key="FQL-186",
)
@pytest.mark.regression
def test_export_row_count_matches_ui(logged_in_page, seeded_basic_scans):
    """CSV row count must match the number of rows visible in the table."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    ui_rows = page.get_all_rows()
    if not ui_rows:
        pytest.skip("No data to compare export row count")

    download = page.download_export()
    parsed = _parse_export_csv(download)

    assert len(parsed["rows"]) == len(ui_rows), (
        f"CSV has {len(parsed['rows'])} data rows but UI shows {len(ui_rows)} rows"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Exported CSV Menu Item values match the UI table")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Menu Item names in the CSV export match those shown in the UI table",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Record Menu Item names from the UI table\n"
        "5. Export CSV and assert Menu Item names match"
    ),
    key="FQL-187",
)
@pytest.mark.regression
def test_export_menu_items_match_ui(logged_in_page, seeded_basic_scans):
    """Menu Item names in the CSV must match those in the UI table."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    ui_rows = page.get_all_rows()
    if not ui_rows:
        pytest.skip("No data to compare export values")

    ui_items = {r.get(Page.COL_MENU_ITEM, "") for r in ui_rows}

    download = page.download_export()
    parsed = _parse_export_csv(download)

    menu_item_col = next((h for h in parsed["headers"] if "Menu Item" in h), None)
    assert menu_item_col, f"No 'Menu Item' column in CSV headers: {parsed['headers']}"

    csv_items = {row.get(menu_item_col, "").strip() for row in parsed["rows"]}
    assert csv_items == ui_items, (
        f"CSV Menu Items {csv_items} do not match UI items {ui_items}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Export CSV title contains the selected date range")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="The first row of the CSV export file contains the date range used for filtering",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters\n"
        "4. Export CSV\n"
        "5. Assert CSV first row (title) contains the start and end dates"
    ),
    key="FQL-188",
)
@pytest.mark.regression
def test_export_title_contains_date_range(logged_in_page, seeded_basic_scans):
    """CSV title row must reference the selected date range."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    ui_rows = page.get_rows()
    if not ui_rows:
        pytest.skip("No data to test export title")

    download = page.download_export()
    parsed = _parse_export_csv(download)

    from datetime import datetime
    start_iso = datetime.strptime(DEFAULT_DATE_START, "%m/%d/%Y").strftime("%Y-%m-%d")
    end_iso   = datetime.strptime(DEFAULT_DATE_END,   "%m/%d/%Y").strftime("%Y-%m-%d")
    assert start_iso in parsed["title"] and end_iso in parsed["title"], (
        f"Date range '{start_iso} — {end_iso}' not found in CSV title: '{parsed['title']}'"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Export respects the Lunch meal filter")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Exporting with Lunch meal filter produces a CSV containing only Lunch items",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary\n"
        "3. Apply default filters then set meal to Lunch\n"
        "4. Export CSV\n"
        "5. Assert CSV data rows are fewer than or equal to unfiltered export"
    ),
    key="FQL-189",
)
@pytest.mark.regression
def test_export_respects_meal_filter(logged_in_page, seeded_basic_scans):
    """Export must respect the active meal filter (Lunch produces <= unfiltered rows)."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    all_rows = page.get_rows()
    if not all_rows:
        pytest.skip("No data to test export meal filter")

    unfiltered_dl = page.download_export()
    unfiltered = _parse_export_csv(unfiltered_dl)

    page.set_meal(MEAL_LUNCH)
    lunch_rows = page.get_rows()

    if not lunch_rows:
        pytest.skip("No Lunch data — cannot compare export sizes")

    lunch_dl = page.download_export()
    lunch_csv = _parse_export_csv(lunch_dl)

    assert len(lunch_csv["rows"]) <= len(unfiltered["rows"]), (
        f"Lunch export ({len(lunch_csv['rows'])} rows) should be <= "
        f"unfiltered export ({len(unfiltered['rows'])} rows)"
    )
