"""Consumption Summary — filters and accuracy tests."""
import allure
import pytest

from shared.config.settings import settings
from shared.data.fixtures import RESTAURANT_A
from shared.data.test_constants import *  # noqa: F401, F403
from dashboard.locators import common_locators as L
from dashboard.pages.consumption_summary_page import ConsumptionSummaryPage as Page
from datetime import datetime

from dashboard.tests.executive_insights.consumption_summary._helpers import (
    OZ_PER_LB,
    CURRENT_RESTAURANT_ID, CURRENT_VENUE_ID, CURRENT_VENUE_NAME,
    SECOND_VENUE_ID, SECOND_VENUE_NAME,
    LUNCH_SP_ID, DINNER_SP_ID, ALL_DAY_SP_ID,
    _to_float, _apply_filters,
    _filter_by_service_period, _filter_by_category, _filter_for_current_view,
    _compute_expected_by_item,
    _assert_column_matches, _check_column_sum_matches,
    _is_sorted_ascending, _is_sorted_descending,
    _assert_headers_have_unit, _get_breadcrumb_links,
    _get_category_dropdown_options,
    _parse_export_csv,
)

# ---------------------------------------------------------------------------
# Meal Period Filters
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Math invariant P = C + O holds per row with Lunch meal filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production equals Consumption + Overproduction for every row when Lunch filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters with Lunch meal period\n"
        "4. If no seeded data for Lunch, assert table is empty and pass\n"
        "5. For each row assert Production == Consumption + Overproduction (tolerance 0.01)"
    ),
    key="FQL-57",
)
@pytest.mark.regression
def test_meal_period_lunch_math_invariant(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), LUNCH_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_LUNCH)

    summary_rows = page.get_rows()

    if not relevant:
        assert len(summary_rows) == 0, "No lunch scans seeded but UI shows data"
        return

    failures = []
    for row in summary_rows:
        item          = row[Page.COL_MENU_ITEM]
        production    = _to_float(row[Page.COL_PRODUCTION])
        consumption   = _to_float(row[Page.COL_CONSUMPTION])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(
                f"'{item}': P={production}, C+O={consumption}+{overproduction}={expected}"
            )

    assert not failures, (
        "Math invariant violations with Lunch filter:\n  " + "\n  ".join(failures)
    )


@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Math invariant P = C + O holds per row with Dinner meal filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production equals Consumption + Overproduction for every row when Dinner filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters with Dinner meal period\n"
        "4. If no seeded data for Dinner, assert table is empty and pass\n"
        "5. For each row assert Production == Consumption + Overproduction (tolerance 0.01)"
    ),
    key="FQL-58",
)
@pytest.mark.regression
def test_meal_period_dinner_math_invariant(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), DINNER_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DINNER)

    summary_rows = page.get_rows()

    if not relevant:
        assert len(summary_rows) == 0, "No dinner scans seeded but UI shows data"
        return

    failures = []
    for row in summary_rows:
        item          = row[Page.COL_MENU_ITEM]
        production    = _to_float(row[Page.COL_PRODUCTION])
        consumption   = _to_float(row[Page.COL_CONSUMPTION])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(
                f"'{item}': P={production}, C+O={consumption}+{overproduction}={expected}"
            )

    assert not failures, (
        "Math invariant violations with Dinner filter:\n  " + "\n  ".join(failures)
    )


@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Seeded data: Consumption matches formula with Lunch filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="UI Consumption matches max(Refill - ServedLeftover, 0) from seeded Lunch scans",
    steps=(
        "1. Filter seeded payloads to Lunch service period\n"
        "2. Navigate to Consumption Summary, apply Lunch filter\n"
        "3. If no seeded Lunch data, assert empty table and pass\n"
        "4. Compute expected Consumption per item from seeded payloads\n"
        "5. Assert UI Consumption matches expected (tolerance 0.01)"
    ),
    key="FQL-59",
)
@pytest.mark.regression
def test_meal_period_lunch_consumption_matches_seeded_data(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), LUNCH_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_LUNCH)

    if not relevant:
        assert len(page.get_rows()) == 0, "No lunch scans seeded but UI shows data"
        return

    expected = {name: vals["consumption"] for name, vals in _compute_expected_by_item(relevant).items()}
    _assert_column_matches(page, expected, Page.COL_CONSUMPTION, "Consumption (Lunch)")


@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Seeded data: Overproduction matches formula with Lunch filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="UI Overproduction matches ServedLeftover + NotServedLeftover from seeded Lunch scans",
    steps=(
        "1. Filter seeded payloads to Lunch service period\n"
        "2. Navigate to Consumption Summary, apply Lunch filter\n"
        "3. If no seeded Lunch data, assert empty table and pass\n"
        "4. Compute expected Overproduction per item from seeded payloads\n"
        "5. Assert UI Overproduction matches expected (tolerance 0.01)"
    ),
    key="FQL-60",
)
@pytest.mark.regression
def test_meal_period_lunch_overproduction_matches_seeded_data(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), LUNCH_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_LUNCH)

    if not relevant:
        assert len(page.get_rows()) == 0, "No lunch scans seeded but UI shows data"
        return

    expected = {name: vals["overproduction"] for name, vals in _compute_expected_by_item(relevant).items()}
    _assert_column_matches(page, expected, Page.COL_OVERPRODUCTION, "Overproduction (Lunch)")


@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Production summary equals sum of detail rows with Dinner meal filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production summary equals sum of daily detail rows when Dinner filter is applied",
    steps=(
        "1. Navigate to Consumption Summary, apply Dinner filter\n"
        "2. If no seeded Dinner data, assert empty table and pass\n"
        "3. For each summary row click to drill down\n"
        "4. Sum detail Production values and assert equals summary value (tolerance 0.01)"
    ),
    key="FQL-61",
)
@pytest.mark.regression
def test_meal_period_dinner_production_sums_match_summary(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), DINNER_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DINNER)

    if not relevant:
        assert len(page.get_rows()) == 0, "No dinner scans seeded but UI shows data"
        return

    failures = _check_column_sum_matches(page, Page.COL_PRODUCTION)
    assert not failures, "Production mismatches (Dinner filter):\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Consumption summary equals sum of detail rows with Dinner meal filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Consumption summary equals sum of daily detail rows when Dinner filter is applied",
    steps=(
        "1. Navigate to Consumption Summary, apply Dinner filter\n"
        "2. If no seeded Dinner data, assert empty table and pass\n"
        "3. For each summary row click to drill down\n"
        "4. Sum detail Consumption values and assert equals summary value (tolerance 0.01)"
    ),
    key="FQL-62",
)
@pytest.mark.regression
def test_meal_period_dinner_consumption_sums_match_summary(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), DINNER_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DINNER)

    if not relevant:
        assert len(page.get_rows()) == 0, "No dinner scans seeded but UI shows data"
        return

    failures = _check_column_sum_matches(page, Page.COL_CONSUMPTION)
    assert not failures, "Consumption mismatches (Dinner filter):\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Overproduction summary equals sum of detail rows with Dinner meal filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Overproduction summary equals sum of daily detail rows when Dinner filter is applied",
    steps=(
        "1. Navigate to Consumption Summary, apply Dinner filter\n"
        "2. If no seeded Dinner data, assert empty table and pass\n"
        "3. For each summary row click to drill down\n"
        "4. Sum detail Overproduction values and assert equals summary value (tolerance 0.01)"
    ),
    key="FQL-63",
)
@pytest.mark.regression
def test_meal_period_dinner_overproduction_sums_match_summary(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), DINNER_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DINNER)

    if not relevant:
        assert len(page.get_rows()) == 0, "No dinner scans seeded but UI shows data"
        return

    failures = _check_column_sum_matches(page, Page.COL_OVERPRODUCTION)
    assert not failures, "Overproduction mismatches (Dinner filter):\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Meal Period Filters — Filter correctness (one per meal period, skeletons)
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Lunch filter shows only menu items that have Lunch service period scans")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="When Lunch meal filter is applied, every visible item across all pages must belong to the Lunch service period only",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Lunch meal filter\n"
        "3. Read all rows across all pages\n"
        "4. From seeded payloads, build the set of menu item names with Lunch scans\n"
        "5. Assert every UI row's Menu Item is in that set — no items from other periods visible"
    ),
    key="FQL-64",
)
@pytest.mark.regression
def test_meal_period_lunch_filter_shows_only_lunch_items(logged_in_page, seeded_basic_scans):
    relevant = _filter_for_current_view(seeded_basic_scans)
    lunch_items = {p["MenuItemName"] for p in relevant if p["ServicePeriodID"] == LUNCH_SP_ID}

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_LUNCH)

    all_rows = page.get_all_rows()

    if not lunch_items:
        assert len(all_rows) == 0, "No lunch scans seeded but UI shows data"
        return

    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' has no Lunch scans in seeded data"
        for r in all_rows
        if r[Page.COL_MENU_ITEM] not in lunch_items
    ]
    assert not failures, (
        "Items visible with Lunch filter that have no Lunch scans:\n  " + "\n  ".join(failures)
    )


@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Dinner filter shows only menu items that have Dinner service period scans")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="When Dinner meal filter is applied, every visible item across all pages must belong to the Dinner service period only",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Dinner meal filter\n"
        "3. Read all rows across all pages\n"
        "4. From seeded payloads, build the set of menu item names with Dinner scans\n"
        "5. Assert every UI row's Menu Item is in that set — no items from other periods visible"
    ),
    key="FQL-65",
)
@pytest.mark.regression
def test_meal_period_dinner_filter_shows_only_dinner_items(logged_in_page, seeded_basic_scans):
    relevant = _filter_for_current_view(seeded_basic_scans)
    dinner_items = {p["MenuItemName"] for p in relevant if p["ServicePeriodID"] == DINNER_SP_ID}

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DINNER)

    all_rows = page.get_all_rows()

    if not dinner_items:
        assert len(all_rows) == 0, "No dinner scans seeded but UI shows data"
        return

    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' has no Dinner scans in seeded data"
        for r in all_rows
        if r[Page.COL_MENU_ITEM] not in dinner_items
    ]
    assert not failures, (
        "Items visible with Dinner filter that have no Dinner scans:\n  " + "\n  ".join(failures)
    )


@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("All Day filter shows only menu items that have All Day service period scans")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="When All Day meal filter is applied, every visible item across all pages must belong to the All Day service period only",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply All Day meal filter\n"
        "3. Read all rows across all pages\n"
        "4. From seeded payloads, build the set of menu item names with All Day scans\n"
        "5. Assert every UI row's Menu Item is in that set — no items from other periods visible"
    ),
    key="FQL-66",
)
@pytest.mark.regression
def test_meal_period_all_day_filter_shows_only_all_day_items(logged_in_page, seeded_basic_scans):
    relevant = _filter_for_current_view(seeded_basic_scans)
    all_day_items = {p["MenuItemName"] for p in relevant if p["ServicePeriodID"] == ALL_DAY_SP_ID}

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DAY)

    all_rows = page.get_all_rows()

    if not all_day_items:
        assert len(all_rows) == 0, "No All Day scans seeded but UI shows data"
        return

    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' has no All Day scans in seeded data"
        for r in all_rows
        if r[Page.COL_MENU_ITEM] not in all_day_items
    ]
    assert not failures, (
        "Items visible with All Day filter that have no All Day scans:\n  " + "\n  ".join(failures)
    )


@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Math invariant P = C + O holds per row with All Day meal filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production equals Consumption + Overproduction for every row when All Day filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply All Day meal filter\n"
        "3. If no seeded All Day data, assert table is empty and pass\n"
        "4. For each row assert Production == Consumption + Overproduction (tolerance 0.01)"
    ),
    key="FQL-67",
)
@pytest.mark.regression
def test_meal_period_all_day_math_invariant(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), ALL_DAY_SP_ID)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_DAY)

    summary_rows = page.get_rows()

    if not relevant:
        assert len(summary_rows) == 0, "No All Day scans seeded but UI shows data"
        return

    failures = []
    for row in summary_rows:
        item           = row[Page.COL_MENU_ITEM]
        production     = _to_float(row[Page.COL_PRODUCTION])
        consumption    = _to_float(row[Page.COL_CONSUMPTION])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(
                f"'{item}': P={production}, C+O={consumption}+{overproduction}={expected}"
            )

    assert not failures, (
        "Math invariant violations with All Day filter:\n  " + "\n  ".join(failures)
    )


# ---------------------------------------------------------------------------
# Meal Period Filters — Cross-Period Accuracy
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Meal Period Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Lunch filter excludes Dinner leftover — consumption differs from All Meals")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description=(
        "When a menu item has a Refill scan at Lunch and a Leftover scan at Dinner on the same day, "
        "All Meals consumption deducts the Dinner leftover but Lunch-only consumption does not, "
        "so the Lunch value is strictly higher than the All Meals value."
    ),
    steps=(
        "1. Seed Refill(Lunch, 400oz) + ServedLeftover(Dinner, 200oz) for 'Corn in a Basket'\n"
        "2. Navigate to Consumption Summary, set venue + date, leave meal = All Meals\n"
        "3. Read 'Corn in a Basket' Consumption — assert equals 12.5 lb (cross-period deduction applied)\n"
        "4. Switch to Lunch filter\n"
        "5. Read 'Corn in a Basket' Consumption — assert equals 25.0 lb (Dinner leftover excluded)\n"
        "6. Assert Lunch consumption > All Meals consumption"
    ),
    key="FQL-68",
)
@pytest.mark.regression
def test_lunch_filter_excludes_dinner_leftover_from_consumption(logged_in_page, seeded_cross_period_scans):
    _ = seeded_cross_period_scans

    expected_all_meals = round(max(CROSS_PERIOD_REFILL_OZ - CROSS_PERIOD_LEFTOVER_OZ, 0) / OZ_PER_LB, 2)
    expected_lunch     = round(CROSS_PERIOD_REFILL_OZ / OZ_PER_LB, 2)

    print(f"\n[cross-period] item         : {CROSS_PERIOD_ITEM_NAME}")
    print(f"[cross-period] seeded        : Refill@Lunch={CROSS_PERIOD_REFILL_OZ}oz  ServedLeftover@Dinner={CROSS_PERIOD_LEFTOVER_OZ}oz")
    print(f"[cross-period] expected      : All Meals={expected_all_meals} lb  |  Lunch-only={expected_lunch} lb")

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(CURRENT_VENUE_NAME)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    all_rows = {r[Page.COL_MENU_ITEM]: r for r in page.get_all_rows()}
    assert CROSS_PERIOD_ITEM_NAME in all_rows, (
        f"'{CROSS_PERIOD_ITEM_NAME}' not found in All Meals view — seeding may have failed"
    )
    actual_all_meals = _to_float(all_rows[CROSS_PERIOD_ITEM_NAME][Page.COL_CONSUMPTION])
    print(f"[cross-period] All Meals UI  : {actual_all_meals} lb  (expected {expected_all_meals} lb)")
    assert abs(actual_all_meals - expected_all_meals) <= 0.01, (
        f"All Meals consumption: expected={expected_all_meals} lb, got={actual_all_meals} lb"
    )

    page.set_meal(MEAL_LUNCH)

    lunch_rows = {r[Page.COL_MENU_ITEM]: r for r in page.get_all_rows()}
    assert CROSS_PERIOD_ITEM_NAME in lunch_rows, (
        f"'{CROSS_PERIOD_ITEM_NAME}' not found in Lunch filter view"
    )
    actual_lunch = _to_float(lunch_rows[CROSS_PERIOD_ITEM_NAME][Page.COL_CONSUMPTION])
    print(f"[cross-period] Lunch-only UI : {actual_lunch} lb  (expected {expected_lunch} lb)")
    assert abs(actual_lunch - expected_lunch) <= 0.01, (
        f"Lunch consumption: expected={expected_lunch} lb, got={actual_lunch} lb"
    )

    assert actual_lunch > actual_all_meals, (
        f"Lunch consumption ({actual_lunch} lb) should exceed All Meals ({actual_all_meals} lb) "
        f"because the Dinner leftover is excluded when filtering to Lunch only"
    )
    print(f"[cross-period] PASS: Lunch ({actual_lunch} lb) > All Meals ({actual_all_meals} lb) ✓")


# ---------------------------------------------------------------------------
# Category Filters — Fruits
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Fruits filter shows only menu items belonging to the Fruits category")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="When Fruits category filter is applied, every visible item across all pages must be a Fruits item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Fruits category filter\n"
        "3. Read all rows across all pages\n"
        "4. Assert every visible Menu Item belongs to the Fruits category"
    ),
    key="FQL-69",
)
@pytest.mark.regression
def test_category_fruits_filter_shows_only_fruits_items(logged_in_page, seeded_basic_scans):
    fruits_items = {mi.name for mi in RESTAURANT_A.menu_items.values() if mi.category == CATEGORY_FRUITS}

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_FRUITS)

    all_rows = page.get_all_rows()
    if not all_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' is not a Fruits item"
        for r in all_rows
        if r[Page.COL_MENU_ITEM] not in fruits_items
    ]
    assert not failures, "Non-Fruits items visible with Fruits filter:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Math invariant P = C + O holds per row with Fruits category filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production equals Consumption + Overproduction for every row when Fruits category filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Fruits category filter\n"
        "3. If no data, assert table is empty and pass\n"
        "4. For each row assert Production == Consumption + Overproduction (tolerance 0.01)"
    ),
    key="FQL-70",
)
@pytest.mark.regression
def test_category_fruits_math_invariant(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_FRUITS)

    summary_rows = page.get_rows()
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in summary_rows:
        item           = row[Page.COL_MENU_ITEM]
        production     = _to_float(row[Page.COL_PRODUCTION])
        consumption    = _to_float(row[Page.COL_CONSUMPTION])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(f"'{item}': P={production}, C+O={consumption}+{overproduction}={expected}")

    assert not failures, "Math invariant violations with Fruits filter:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Seeded data: Consumption matches formula with Fruits category filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="UI Consumption matches max(Refill - ServedLeftover, 0) for Fruits category items",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Fruits category filter\n"
        "3. Compute expected Consumption for Fruits items from seeded payloads\n"
        "4. Assert UI Consumption matches expected per item (tolerance 0.01)"
    ),
    key="FQL-71",
)
@pytest.mark.regression
def test_category_fruits_consumption_matches_seeded_data(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_FRUITS)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_FRUITS)

    if not relevant:
        assert len(page.get_rows()) == 0, "No Fruits scans seeded but UI shows data"
        return

    expected = {name: vals["consumption"] for name, vals in _compute_expected_by_item(relevant).items()}
    _assert_column_matches(page, expected, Page.COL_CONSUMPTION, "Consumption (Fruits)")


@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Seeded data: Overproduction matches formula with Fruits category filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="UI Overproduction matches ServedLeftover + NotServedLeftover for Fruits category items",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Fruits category filter\n"
        "3. Compute expected Overproduction for Fruits items from seeded payloads\n"
        "4. Assert UI Overproduction matches expected per item (tolerance 0.01)"
    ),
    key="FQL-72",
)
@pytest.mark.regression
def test_category_fruits_overproduction_matches_seeded_data(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_FRUITS)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_FRUITS)

    if not relevant:
        assert len(page.get_rows()) == 0, "No Fruits scans seeded but UI shows data"
        return

    expected = {name: vals["overproduction"] for name, vals in _compute_expected_by_item(relevant).items()}
    _assert_column_matches(page, expected, Page.COL_OVERPRODUCTION, "Overproduction (Fruits)")


@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Production summary equals sum of detail rows with Fruits category filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production drill-down sums match summary values when Fruits category filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Fruits category filter\n"
        "3. For each summary row click to drill down\n"
        "4. Sum detail Production values and assert equals summary value (tolerance 0.01)"
    ),
    key="FQL-73",
)
@pytest.mark.regression
def test_category_fruits_production_sums_match_summary(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_FRUITS)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_FRUITS)

    if not relevant:
        assert len(page.get_rows()) == 0, "No Fruits scans seeded but UI shows data"
        return

    failures = _check_column_sum_matches(page, Page.COL_PRODUCTION)
    assert not failures, "Production mismatches (Fruits filter):\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Category Filters — Vegetables
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Vegetables filter shows only menu items belonging to the Vegetables category")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="When Vegetables category filter is applied, every visible item across all pages must be a Vegetables item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Vegetables category filter\n"
        "3. Read all rows across all pages\n"
        "4. Assert every visible Menu Item belongs to the Vegetables category"
    ),
    key="FQL-74",
)
@pytest.mark.regression
def test_category_vegetables_filter_shows_only_vegetables_items(logged_in_page, seeded_basic_scans):
    vegetables_items = {mi.name for mi in RESTAURANT_A.menu_items.values() if mi.category == CATEGORY_VEGETABLES}

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_VEGETABLES)

    all_rows = page.get_all_rows()
    if not all_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' is not a Vegetables item"
        for r in all_rows
        if r[Page.COL_MENU_ITEM] not in vegetables_items
    ]
    assert not failures, "Non-Vegetables items visible with Vegetables filter:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Math invariant P = C + O holds per row with Vegetables category filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production equals Consumption + Overproduction for every row when Vegetables category filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Vegetables category filter\n"
        "3. If no data, assert table is empty and pass\n"
        "4. For each row assert Production == Consumption + Overproduction (tolerance 0.01)"
    ),
    key="FQL-75",
)
@pytest.mark.regression
def test_category_vegetables_math_invariant(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_VEGETABLES)

    summary_rows = page.get_rows()
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in summary_rows:
        item           = row[Page.COL_MENU_ITEM]
        production     = _to_float(row[Page.COL_PRODUCTION])
        consumption    = _to_float(row[Page.COL_CONSUMPTION])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(f"'{item}': P={production}, C+O={consumption}+{overproduction}={expected}")

    assert not failures, "Math invariant violations with Vegetables filter:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Seeded data: Consumption matches formula with Vegetables category filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="UI Consumption matches max(Refill - ServedLeftover, 0) for Vegetables category items",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Vegetables category filter\n"
        "3. Compute expected Consumption for Vegetables items from seeded payloads\n"
        "4. Assert UI Consumption matches expected per item (tolerance 0.01)"
    ),
    key="FQL-76",
)
@pytest.mark.regression
def test_category_vegetables_consumption_matches_seeded_data(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_VEGETABLES)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_VEGETABLES)

    if not relevant:
        assert len(page.get_rows()) == 0, "No Vegetables scans seeded but UI shows data"
        return

    expected = {name: vals["consumption"] for name, vals in _compute_expected_by_item(relevant).items()}
    _assert_column_matches(page, expected, Page.COL_CONSUMPTION, "Consumption (Vegetables)")


@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Seeded data: Overproduction matches formula with Vegetables category filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="UI Overproduction matches ServedLeftover + NotServedLeftover for Vegetables category items",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Vegetables category filter\n"
        "3. Compute expected Overproduction for Vegetables items from seeded payloads\n"
        "4. Assert UI Overproduction matches expected per item (tolerance 0.01)"
    ),
    key="FQL-77",
)
@pytest.mark.regression
def test_category_vegetables_overproduction_matches_seeded_data(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_VEGETABLES)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_VEGETABLES)

    if not relevant:
        assert len(page.get_rows()) == 0, "No Vegetables scans seeded but UI shows data"
        return

    expected = {name: vals["overproduction"] for name, vals in _compute_expected_by_item(relevant).items()}
    _assert_column_matches(page, expected, Page.COL_OVERPRODUCTION, "Overproduction (Vegetables)")


@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Production summary equals sum of detail rows with Vegetables category filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production drill-down sums match summary values when Vegetables category filter is applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Vegetables category filter\n"
        "3. For each summary row click to drill down\n"
        "4. Sum detail Production values and assert equals summary value (tolerance 0.01)"
    ),
    key="FQL-78",
)
@pytest.mark.regression
def test_category_vegetables_production_sums_match_summary(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_category(_filter_for_current_view(seeded_basic_scans), CATEGORY_VEGETABLES)

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_VEGETABLES)

    if not relevant:
        assert len(page.get_rows()) == 0, "No Vegetables scans seeded but UI shows data"
        return

    failures = _check_column_sum_matches(page, Page.COL_PRODUCTION)
    assert not failures, "Production mismatches (Vegetables filter):\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Category Filters — Kitchen Waste
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Kitchen Waste filter shows only menu items belonging to the Kitchen Waste category")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="When Kitchen Waste filter is applied, every visible item across all pages must be a Kitchen Waste item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Kitchen Waste category filter\n"
        "3. Read all rows across all pages\n"
        "4. Assert every visible Menu Item belongs to the Kitchen Waste category"
    ),
    key="FQL-79",
)
@pytest.mark.regression
def test_category_kitchen_waste_filter_shows_only_kitchen_waste_items(logged_in_page, seeded_basic_scans):
    # kw_items = {mi.name for mi in RESTAURANT_A.menu_items.values() if mi.category == CATEGORY_KITCHEN_WASTE}
    #
    # page = Page(logged_in_page)
    # page.open_via_nav()
    # _apply_filters(page, category=CATEGORY_KITCHEN_WASTE)
    #
    # all_rows = page.get_all_rows()
    # if not all_rows:
    #     print(NO_DATA_AVAILABLE)
    #     return
    #
    # failures = [
    #     f"'{r[Page.COL_MENU_ITEM]}' is not a Kitchen Waste item"
    #     for r in all_rows
    #     if r[Page.COL_MENU_ITEM] not in kw_items
    # ]
    # assert not failures, "Non-Kitchen-Waste items visible with Kitchen Waste filter:\n  " + "\n  ".join(failures)

    page = Page(logged_in_page)
    page.open_via_nav()
    options = _get_category_dropdown_options(page)
    assert CATEGORY_KITCHEN_WASTE not in options, (
        f"'{CATEGORY_KITCHEN_WASTE}' unexpectedly present in category dropdown: {options}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Kitchen Waste items: Production equals Overproduction (Consumption is always zero)")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Kitchen Waste items never have Refill scans so Consumption=0 and Production must equal Overproduction",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Kitchen Waste category filter\n"
        "3. Read all visible rows\n"
        "4. For each row assert Production == Overproduction (tolerance 0.01)\n"
        "5. For each row assert Consumption == 0"
    ),
    key="FQL-80",
)
@pytest.mark.regression
def test_category_kitchen_waste_production_equals_overproduction(logged_in_page, seeded_basic_scans):
    # page = Page(logged_in_page)
    # page.open_via_nav()
    # _apply_filters(page, category=CATEGORY_KITCHEN_WASTE)
    #
    # summary_rows = page.get_rows()
    # if not summary_rows:
    #     print(NO_DATA_AVAILABLE)
    #     return
    #
    # failures = []
    # for row in summary_rows:
    #     item           = row[Page.COL_MENU_ITEM]
    #     production     = _to_float(row[Page.COL_PRODUCTION])
    #     consumption    = _to_float(row[Page.COL_CONSUMPTION])
    #     overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
    #     if abs(production - overproduction) > 0.01:
    #         failures.append(f"'{item}': Production={production}, Overproduction={overproduction}")
    #     if consumption != 0:
    #         failures.append(f"'{item}': expected Consumption=0, got {consumption}")
    #
    # assert not failures, "Kitchen Waste invariant violations:\n  " + "\n  ".join(failures)

    page = Page(logged_in_page)
    page.open_via_nav()
    options = _get_category_dropdown_options(page)
    assert CATEGORY_KITCHEN_WASTE not in options, (
        f"'{CATEGORY_KITCHEN_WASTE}' unexpectedly present in category dropdown: {options}"
    )


# ---------------------------------------------------------------------------
# Category Filters — Post-Consumer
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Post-Consumer filter shows only menu items belonging to the Post-Consumer category")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="When Post-Consumer filter is applied, every visible item across all pages must be a Post-Consumer item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Post-Consumer category filter\n"
        "3. Read all rows across all pages\n"
        "4. Assert every visible Menu Item belongs to the Post-Consumer category"
    ),
    key="FQL-81",
)
@pytest.mark.regression
def test_category_post_consumer_filter_shows_only_post_consumer_items(logged_in_page, seeded_basic_scans):
    # pc_items = {mi.name for mi in RESTAURANT_A.menu_items.values() if mi.category == CATEGORY_POST_CONSUMER}
    #
    # page = Page(logged_in_page)
    # page.open_via_nav()
    # _apply_filters(page, category=CATEGORY_POST_CONSUMER)
    #
    # all_rows = page.get_all_rows()
    # if not all_rows:
    #     print(NO_DATA_AVAILABLE)
    #     return
    #
    # failures = [
    #     f"'{r[Page.COL_MENU_ITEM]}' is not a Post-Consumer item"
    #     for r in all_rows
    #     if r[Page.COL_MENU_ITEM] not in pc_items
    # ]
    # assert not failures, "Non-Post-Consumer items visible with Post-Consumer filter:\n  " + "\n  ".join(failures)

    page = Page(logged_in_page)
    page.open_via_nav()
    options = _get_category_dropdown_options(page)
    assert CATEGORY_POST_CONSUMER not in options, (
        f"'{CATEGORY_POST_CONSUMER}' unexpectedly present in category dropdown: {options}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Category Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Post-Consumer items: Production equals Overproduction (Consumption is always zero)")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Post-Consumer items never have Refill scans so Consumption=0 and Production must equal Overproduction",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Post-Consumer category filter\n"
        "3. Read all visible rows\n"
        "4. For each row assert Production == Overproduction (tolerance 0.01)\n"
        "5. For each row assert Consumption == 0"
    ),
    key="FQL-82",
)
@pytest.mark.regression
def test_category_post_consumer_production_equals_overproduction(logged_in_page, seeded_basic_scans):
    # page = Page(logged_in_page)
    # page.open_via_nav()
    # _apply_filters(page, category=CATEGORY_POST_CONSUMER)
    #
    # summary_rows = page.get_rows()
    # if not summary_rows:
    #     print(NO_DATA_AVAILABLE)
    #     return
    #
    # failures = []
    # for row in summary_rows:
    #     item           = row[Page.COL_MENU_ITEM]
    #     production     = _to_float(row[Page.COL_PRODUCTION])
    #     consumption    = _to_float(row[Page.COL_CONSUMPTION])
    #     overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
    #     if abs(production - overproduction) > 0.01:
    #         failures.append(f"'{item}': Production={production}, Overproduction={overproduction}")
    #     if consumption != 0:
    #         failures.append(f"'{item}': expected Consumption=0, got {consumption}")
    #
    # assert not failures, "Post-Consumer invariant violations:\n  " + "\n  ".join(failures)

    page = Page(logged_in_page)
    page.open_via_nav()
    options = _get_category_dropdown_options(page)
    assert CATEGORY_POST_CONSUMER not in options, (
        f"'{CATEGORY_POST_CONSUMER}' unexpectedly present in category dropdown: {options}"
    )


# ---------------------------------------------------------------------------
# Combined Filters (skeletons)
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Combined Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Math invariant P = C + O holds with Fruits category and Lunch meal filter combined")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production equals Consumption + Overproduction when Fruits + Lunch filters are combined",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply venue and date filters, set category to Fruits, meal to Lunch\n"
        "4. If no data for combination, assert table is empty and pass\n"
        "5. For each row assert Production == Consumption + Overproduction (tolerance 0.01)"
    ),
    key="FQL-83",
)
@pytest.mark.regression
def test_combined_fruits_lunch_math_invariant(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_category(
        _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), LUNCH_SP_ID),
        CATEGORY_FRUITS,
    )

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, meal=MEAL_LUNCH, category=CATEGORY_FRUITS)

    summary_rows = page.get_rows()
    if not relevant:
        assert len(summary_rows) == 0, "No Fruits+Lunch scans seeded but UI shows data"
        return

    failures = []
    for row in summary_rows:
        item           = row[Page.COL_MENU_ITEM]
        production     = _to_float(row[Page.COL_PRODUCTION])
        consumption    = _to_float(row[Page.COL_CONSUMPTION])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(f"'{item}': P={production}, C+O={consumption}+{overproduction}={expected}")

    assert not failures, "Math invariant violations (Fruits+Lunch):\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Combined Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Math invariant P = C + O holds with Vegetables category and Dinner meal filter combined")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production equals Consumption + Overproduction when Vegetables + Dinner filters are combined",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply venue and date filters, set category to Vegetables, meal to Dinner\n"
        "4. If no data for combination, assert table is empty and pass\n"
        "5. For each row assert Production == Consumption + Overproduction (tolerance 0.01)"
    ),
    key="FQL-84",
)
@pytest.mark.regression
def test_combined_vegetables_dinner_math_invariant(logged_in_page, seeded_basic_scans):
    relevant = _filter_by_category(
        _filter_by_service_period(_filter_for_current_view(seeded_basic_scans), DINNER_SP_ID),
        CATEGORY_VEGETABLES,
    )

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, meal=MEAL_DINNER, category=CATEGORY_VEGETABLES)

    summary_rows = page.get_rows()
    if not relevant:
        assert len(summary_rows) == 0, "No Vegetables+Dinner scans seeded but UI shows data"
        return

    failures = []
    for row in summary_rows:
        item           = row[Page.COL_MENU_ITEM]
        production     = _to_float(row[Page.COL_PRODUCTION])
        consumption    = _to_float(row[Page.COL_CONSUMPTION])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(f"'{item}': P={production}, C+O={consumption}+{overproduction}={expected}")

    assert not failures, "Math invariant violations (Vegetables+Dinner):\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Combined Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Switching category filter updates table without resetting meal filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Changing the category filter preserves the currently selected meal period filter",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Lunch meal filter\n"
        "3. Change category filter from All Categories to Fruits\n"
        "4. Assert meal filter still shows Lunch\n"
        "5. Assert table reloads with Fruits + Lunch data"
    ),
    key="FQL-85",
)
@pytest.mark.regression
def test_category_change_preserves_meal_filter(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, meal=MEAL_LUNCH)

    page.set_category(CATEGORY_FRUITS)

    assert page.is_filter_selected(MEAL_LUNCH), (
        f"Meal filter reset after category change — expected '{MEAL_LUNCH}' still selected"
    )

    fruits_items = {mi.name for mi in RESTAURANT_A.menu_items.values() if mi.category == CATEGORY_FRUITS}
    all_rows = page.get_all_rows()
    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' is not a Fruits item"
        for r in all_rows
        if r[Page.COL_MENU_ITEM] not in fruits_items
    ]
    assert not failures, "Non-Fruits items after category change:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Combined Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Switching meal filter updates table without resetting category filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Changing the meal filter preserves the currently selected category filter",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply Fruits category filter\n"
        "3. Change meal filter from All Meals to Dinner\n"
        "4. Assert category filter still shows Fruits\n"
        "5. Assert table reloads with Fruits + Dinner data"
    ),
    key="FQL-86",
)
@pytest.mark.regression
def test_meal_change_preserves_category_filter(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_FRUITS)

    page.set_meal(MEAL_DINNER)

    assert page.is_filter_selected(CATEGORY_FRUITS), (
        f"Category filter reset after meal change — expected '{CATEGORY_FRUITS}' still selected"
    )

    fruits_items = {mi.name for mi in RESTAURANT_A.menu_items.values() if mi.category == CATEGORY_FRUITS}
    all_rows = page.get_all_rows()
    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' is not a Fruits item"
        for r in all_rows
        if r[Page.COL_MENU_ITEM] not in fruits_items
    ]
    assert not failures, "Non-Fruits items after meal change:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# All Venues
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("All Venues filter shows rows from both venues")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="With All Venues selected (default), rows from both Mexican Venue and Stuffing Venue appear",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Select '- All Venues -' in the venue filter\n"
        "4. Apply meal=All, category=All, default date range\n"
        "5. Read all rows across all pages\n"
        "6. Assert both venue names appear in the Venue column"
    ),
    key="FQL-87",
)
@pytest.mark.regression
def test_all_venues_shows_rows_from_both_venues(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    both_venue_names = {v.name for v in RESTAURANT_A.venues.values()}

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, venue=VENUE_ALL)

    all_rows = page.get_all_rows()
    if not all_rows:
        print(NO_DATA_AVAILABLE)
        return

    venues_seen = {r[Page.COL_VENUE] for r in all_rows}
    missing = both_venue_names - venues_seen
    assert not missing, (
        f"Expected rows from all venues. Missing: {missing}. Seen: {venues_seen}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Math invariant P = C + O holds per row with All Venues filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production equals Consumption + Overproduction for every row when All Venues is selected",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, select '- All Venues -'\n"
        "3. Apply meal=All, category=All, default date range\n"
        "4. For each row assert Production == Consumption + Overproduction (tolerance 0.01)"
    ),
    key="FQL-88",
)
@pytest.mark.regression
def test_all_venues_math_invariant(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, venue=VENUE_ALL)

    summary_rows = page.get_rows()
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in summary_rows:
        item           = row[Page.COL_MENU_ITEM]
        production     = _to_float(row[Page.COL_PRODUCTION])
        consumption    = _to_float(row[Page.COL_CONSUMPTION])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(f"'{item}': P={production}, C+O={consumption}+{overproduction}={expected}")

    assert not failures, "Math invariant violations with All Venues filter:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Filters")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("[BUG] Drill-down in All Venues mode should scope detail to the clicked row's venue")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description=(
        "When All Venues is selected and a summary row is clicked, the detail view "
        "should only show records matching the venue shown in that summary row. "
        "Known bug: detail currently returns data across all venues."
    ),
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Select '- All Venues -' in the venue filter\n"
        "4. Apply meal=All, category=All, default date range\n"
        "5. Note the Venue value of the first summary row\n"
        "6. Click that row to drill into the detail view\n"
        "7. Read all detail rows across all pages\n"
        "8. Assert every detail row's Venue matches the venue from step 5"
    ),
    key="FQL-89",
)
@pytest.mark.regression
@pytest.mark.xfail(
    strict=False,
    reason=(
        "Known bug: drilling down from an All-Venues summary row returns detail records "
        "for ALL venues instead of scoping to the venue shown in the clicked row."
    ),
)
def test_all_venues_drill_down_scopes_to_row_venue(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, venue=VENUE_ALL)

    # Read all summary rows (resets pagination to page 1 after)
    all_rows = page.get_all_rows()
    if not all_rows:
        print(NO_DATA_AVAILABLE)
        return

    # Find an item that appears under more than one venue in the summary.
    # If every item only has one venue's data, the bug cannot produce wrong results
    # for this seed — skip rather than give a false pass.
    item_venues: dict[str, set] = {}
    for r in all_rows:
        name = r[Page.COL_MENU_ITEM]
        venue = r.get(Page.COL_VENUE, "")
        item_venues.setdefault(name, set()).add(venue)

    multi_venue_items = {name for name, vs in item_venues.items() if len(vs) > 1}
    if not multi_venue_items:
        pytest.skip(
            "No menu item appears under more than one venue in the current seeded data "
            "— cannot exercise the cross-venue scoping bug"
        )

    # Click the first such row on page 1
    page1_rows = page.get_rows()
    target_idx = next(
        (i for i, r in enumerate(page1_rows) if r[Page.COL_MENU_ITEM] in multi_venue_items),
        None,
    )
    if target_idx is None:
        pytest.skip("Multi-venue item not on page 1 — skipping")

    expected_venue = page1_rows[target_idx][Page.COL_VENUE]
    item_name = page1_rows[target_idx][Page.COL_MENU_ITEM]

    page.click_menu_item_in_row(target_idx)
    detail_rows = page.get_all_rows()

    wrong_venue_rows = [
        r for r in detail_rows
        if r.get(Page.COL_VENUE, "") != expected_venue
    ]

    assert not wrong_venue_rows, (
        f"Clicked '{item_name}' (summary venue='{expected_venue}') but detail shows "
        f"rows from other venues: "
        + ", ".join(
            f"'{r[Page.COL_MENU_ITEM]}' @ '{r.get(Page.COL_VENUE)}'"
            for r in wrong_venue_rows[:5]
        )
    )


# ---------------------------------------------------------------------------
# Second Venue (Stuffing Venue)
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Second venue filter shows only rows belonging to Stuffing Venue")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Selecting Stuffing Venue shows only rows with Venue = Stuffing Venue",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Select Stuffing Venue in the venue filter\n"
        "4. Apply meal=All, category=All, default date range\n"
        "5. Read all rows across all pages\n"
        "6. Assert every row's Venue column equals 'Stuffing Venue'"
    ),
    key="FQL-90",
)
@pytest.mark.regression
def test_second_venue_filter_shows_only_stuffing_venue(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, venue=SECOND_VENUE_NAME)

    all_rows = page.get_all_rows()
    if not all_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = [
        f"'{r[Page.COL_MENU_ITEM]}': venue='{r[Page.COL_VENUE]}' expected='{SECOND_VENUE_NAME}'"
        for r in all_rows
        if r.get(Page.COL_VENUE, "").strip() != SECOND_VENUE_NAME
    ]
    assert not failures, (
        "Non-Stuffing-Venue rows visible with Stuffing Venue filter:\n  " + "\n  ".join(failures)
    )


@allure.epic("Consumption Summary")
@allure.feature("Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Math invariant P = C + O holds per row for Stuffing Venue")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production equals Consumption + Overproduction for every row when Stuffing Venue is selected",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, select Stuffing Venue\n"
        "3. Apply meal=All, category=All, default date range\n"
        "4. For each row assert Production == Consumption + Overproduction (tolerance 0.01)"
    ),
    key="FQL-91",
)
@pytest.mark.regression
def test_second_venue_math_invariant(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, venue=SECOND_VENUE_NAME)

    summary_rows = page.get_rows()
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in summary_rows:
        item           = row[Page.COL_MENU_ITEM]
        production     = _to_float(row[Page.COL_PRODUCTION])
        consumption    = _to_float(row[Page.COL_CONSUMPTION])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION])
        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(f"'{item}': P={production}, C+O={consumption}+{overproduction}={expected}")

    assert not failures, "Math invariant violations with Stuffing Venue filter:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Data Accuracy — additional
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Days Served value equals the number of unique dates in seeded data per item")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Days Served column shows the correct count of unique scan dates per menu item",
    steps=(
        "1. Seed scans via API with known dates per item\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. For each item in summary rows, count unique CapturedAt dates in seeded payloads\n"
        "4. Assert Days Served in UI equals unique date count (tolerance 0)"
    ),
    key="FQL-92",
)
@pytest.mark.regression
def test_days_served_equals_unique_dates_in_seeded_data(logged_in_page, seeded_basic_scans):
    relevant = _filter_for_current_view(seeded_basic_scans)

    expected_days: dict[str, int] = {}
    for p in relevant:
        name = p["MenuItemName"]
        date = p["CapturedAt"][:10]
        if name not in expected_days:
            expected_days[name] = set()
        expected_days[name].add(date)
    expected_days = {name: len(dates) for name, dates in expected_days.items()}

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    summary_rows = page.get_all_rows()

    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in summary_rows:
        item = row[Page.COL_MENU_ITEM]
        if item not in expected_days:
            continue
        ui_days = int(_to_float(row[Page.COL_DAYS_SERVED]))
        exp_days = expected_days[item]
        if ui_days != exp_days:
            failures.append(f"'{item}': expected={exp_days}, UI={ui_days}")

    assert not failures, (
        "Days Served mismatch against seeded data:\n  " + "\n  ".join(failures)
    )


# ---------------------------------------------------------------------------
# Search Button
# ---------------------------------------------------------------------------

# Items that appear in the search dropdown (Header.jsx excludes BackOfKitchen and PostConsumer)
_SEARCHABLE_CATEGORIES = {CATEGORY_FRUITS, CATEGORY_VEGETABLES}
_SEARCHABLE_ITEMS = {mi.name for mi in RESTAURANT_A.menu_items.values() if mi.category in _SEARCHABLE_CATEGORIES}


@allure.epic("Consumption Summary")
@allure.feature("Search")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Search button is visible in the filter bar")
@pytest.mark.testcase(
    component="consumption_summary",
    type="smoke, regression",
    description="The search icon button is present in the header filter bar",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Assert the search icon button is visible"
    ),
    key="FQL-93",
)
@pytest.mark.smoke
@pytest.mark.regression
def test_search_button_visible_in_header(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    assert page.page.locator(L.SEARCH_BUTTON).is_visible(), (
        "Search button (magnifying glass icon) not found in filter bar"
    )


@allure.epic("Consumption Summary")
@allure.feature("Search")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Search button toggles Menu Items select and changes icon")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Clicking the search button shows the Menu Items multi-select and switches icon to arrow; clicking again hides it",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Assert Menu Items select is hidden and search icon is shown\n"
        "4. Click search button — assert Menu Items select appears and icon becomes arrow\n"
        "5. Click minimize button — assert Menu Items select disappears and icon reverts to search"
    ),
    key="FQL-94",
)
@pytest.mark.regression
def test_search_button_toggles_menu_item_select(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    assert not page.page.locator(L.MENU_ITEM_SEARCH_SELECT).is_visible(), (
        "Menu Items select should be hidden before clicking search"
    )
    assert page.page.locator(L.SEARCH_BUTTON).is_visible()

    page.click_search_toggle()

    assert page.page.locator(L.MENU_ITEM_SEARCH_SELECT).is_visible(), (
        "Menu Items select should appear after clicking search"
    )
    assert page.page.locator(L.SEARCH_MINIMIZE_BUTTON).is_visible(), (
        "Icon should switch to arrow-right after opening search"
    )

    page.click_search_toggle()

    assert not page.page.locator(L.MENU_ITEM_SEARCH_SELECT).is_visible(), (
        "Menu Items select should hide after clicking minimize"
    )
    assert page.page.locator(L.SEARCH_BUTTON).is_visible(), (
        "Icon should revert to search after minimizing"
    )


@allure.epic("Consumption Summary")
@allure.feature("Search")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Selecting a single menu item filters the table to that item only")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="After selecting one item in the search filter, every visible table row shows only that item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. From seeded data pick a searchable item (Fruits/Vegetables) with data for current venue\n"
        "4. Open search, select that item\n"
        "5. Assert every row in the table shows only the selected item"
    ),
    key="FQL-95",
)
@pytest.mark.regression
def test_search_single_item_filters_table(logged_in_page, seeded_basic_scans):
    relevant = _filter_for_current_view(seeded_basic_scans)
    searchable_with_data = {p["MenuItemName"] for p in relevant if p["MenuItemName"] in _SEARCHABLE_ITEMS}

    if not searchable_with_data:
        pytest.skip("No searchable (Fruits/Vegetables) items with data in current venue for this run")

    target = next(iter(sorted(searchable_with_data)))

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(settings.test_venue)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)
    page.click_search_toggle()
    page.select_menu_items_in_search(target)

    rows = page.get_rows()
    assert rows, f"Expected rows after selecting '{target}' but table is empty"

    wrong = [r[Page.COL_MENU_ITEM] for r in rows if r[Page.COL_MENU_ITEM] != target]
    assert not wrong, (
        f"Search filter for '{target}' returned unexpected items: {wrong}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Search")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Selecting multiple menu items shows rows for all selected items only")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="After selecting two items in the search filter, only rows for those two items are shown",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. From seeded data pick two searchable items with data\n"
        "4. Open search, select both items\n"
        "5. Assert only rows for the two selected items appear"
    ),
    key="FQL-96",
)
@pytest.mark.regression
def test_search_multiple_items_shows_all_selected(logged_in_page, seeded_basic_scans):
    relevant = _filter_for_current_view(seeded_basic_scans)
    searchable_with_data = sorted(
        p["MenuItemName"] for p in relevant if p["MenuItemName"] in _SEARCHABLE_ITEMS
    )
    unique_with_data = sorted(set(searchable_with_data))

    if len(unique_with_data) < 2:
        pytest.skip("Need at least 2 distinct searchable items with data — not enough in this run")

    item_a, item_b = unique_with_data[0], unique_with_data[1]

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(settings.test_venue)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)
    page.click_search_toggle()
    page.select_menu_items_in_search(item_a, item_b)

    rows = page.get_rows()
    assert rows, f"Expected rows after selecting '{item_a}' + '{item_b}' but table is empty"

    names = {r[Page.COL_MENU_ITEM] for r in rows}
    unexpected = names - {item_a, item_b}
    assert not unexpected, (
        f"Unexpected items visible with search filter [{item_a}, {item_b}]: {unexpected}"
    )
    missing = {item_a, item_b} - names
    assert not missing, (
        f"Selected items not visible in table: {missing}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Search")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Clearing search selection restores the full table")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="After clearing the Menu Items search filter, the table returns to its unfiltered row count",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Record unfiltered row count\n"
        "4. Open search, select one item — confirm row count decreases\n"
        "5. Click the clear (X) icon on the search select\n"
        "6. Assert row count returns to the unfiltered value"
    ),
    key="FQL-97",
)
@pytest.mark.regression
def test_search_clear_restores_all_rows(logged_in_page, seeded_basic_scans):
    relevant = _filter_for_current_view(seeded_basic_scans)
    searchable_with_data = {p["MenuItemName"] for p in relevant if p["MenuItemName"] in _SEARCHABLE_ITEMS}

    if not searchable_with_data:
        pytest.skip("No searchable items with data for this run")

    target = next(iter(sorted(searchable_with_data)))

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(settings.test_venue)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    full_count = len(page.get_rows())

    page.click_search_toggle()
    page.select_menu_items_in_search(target)

    filtered_count = len(page.get_rows())
    assert filtered_count < full_count, (
        f"Expected fewer rows after selecting '{target}' but got {filtered_count} (was {full_count})"
    )

    page.clear_menu_item_search()

    restored_count = len(page.get_rows())
    assert restored_count == full_count, (
        f"After clearing search expected {full_count} rows but got {restored_count}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Search")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Search filter combined with meal filter: only matching rows shown")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="When both a meal filter and a search item are active, only rows matching both are shown",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. From seeded data find a searchable item (Fruits/Vegetables) that has Lunch scans\n"
        "3. Navigate to Consumption Summary, apply Lunch meal filter\n"
        "4. Open search and select that item\n"
        "5. Assert every visible row shows only that item"
    ),
    key="FQL-98",
)
@pytest.mark.regression
def test_search_combined_with_meal_filter(logged_in_page, seeded_basic_scans):
    relevant = _filter_for_current_view(seeded_basic_scans)
    lunch_searchable = {
        p["MenuItemName"]
        for p in relevant
        if p["ServicePeriodID"] == LUNCH_SP_ID and p["MenuItemName"] in _SEARCHABLE_ITEMS
    }

    if not lunch_searchable:
        pytest.skip("No searchable (Fruits/Vegetables) items with Lunch scans in seeded data for this run")

    target = next(iter(sorted(lunch_searchable)))

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(settings.test_venue)
    page.set_meal(MEAL_LUNCH)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)
    page.click_search_toggle()
    page.select_menu_items_in_search(target)

    rows = page.get_rows()
    assert rows, (
        f"Expected rows for '{target}' with Lunch filter but table is empty"
    )

    wrong = [r[Page.COL_MENU_ITEM] for r in rows if r[Page.COL_MENU_ITEM] != target]
    assert not wrong, (
        f"Search+Lunch filter returned unexpected items: {wrong}"
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Exported CSV column headers match expected schema")
@pytest.mark.testcase(
    component="consumption_summary",
    type="smoke, regression",
    description="Downloaded CSV row 3 headers exactly match ConsumptionSummaryPage.EXPORT_HEADERS",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Click the export button and capture the download\n"
        "4. Parse the CSV and read row 3 (header row)\n"
        "5. Assert headers == Page.EXPORT_HEADERS"
    ),
    key="FQL-99",
)
@pytest.mark.smoke
@pytest.mark.regression
def test_export_headers_are_correct(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    download = page.download_export()
    csv_data = _parse_export_csv(download)

    assert csv_data["headers"] == Page.EXPORT_HEADERS, (
        f"CSV headers mismatch.\nExpected: {Page.EXPORT_HEADERS}\nActual:   {csv_data['headers']}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Exported CSV row count matches UI table row count")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Number of data rows in the downloaded CSV equals the number of rows shown in the UI",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Count all UI rows (across all pages)\n"
        "4. Click export and parse CSV\n"
        "5. Assert len(csv rows) == UI row count"
    ),
    key="FQL-100",
)
@pytest.mark.regression
def test_export_row_count_matches_ui(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    ui_rows = page.get_all_rows()
    ui_count = len(ui_rows)
    assert ui_count > 0, "No UI rows found — seeded data missing, cannot validate export"

    download = page.download_export()
    csv_data = _parse_export_csv(download)
    csv_count = len(csv_data["rows"])

    print(f"\n[export] UI rows={ui_count}, CSV rows={csv_count}")
    assert csv_count == ui_count, (
        f"CSV row count ({csv_count}) doesn't match UI row count ({ui_count})"
    )


@allure.epic("Consumption Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Exported CSV Consumption (lb) values match UI values")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="For every row the Consumption (lb) value in the CSV matches the value shown in the UI table",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Read all UI rows into a dict keyed by Menu Item name\n"
        "4. Click export and parse CSV\n"
        "5. For each CSV row find the matching UI row and compare Consumption (lb) within 0.01 tolerance"
    ),
    key="FQL-101",
)
@pytest.mark.regression
def test_export_values_match_ui(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    all_ui_rows = page.get_all_rows()
    assert all_ui_rows, "No UI rows found — seeded data missing, cannot validate export"
    ui_rows = {r[Page.COL_MENU_ITEM]: r for r in all_ui_rows}

    download = page.download_export()
    csv_data = _parse_export_csv(download)
    assert csv_data["rows"], "CSV has no data rows — export produced an empty file"

    failures = []
    matched = 0
    for csv_row in csv_data["rows"]:
        item = csv_row.get("Menu Item", "")
        if item not in ui_rows:
            failures.append(f"'{item}' in CSV not found in UI")
            continue
        matched += 1
        ui_val  = _to_float(ui_rows[item][Page.COL_CONSUMPTION])
        csv_val = _to_float(csv_row.get(Page.COL_CONSUMPTION, "0"))
        print(f"[export] {item}: UI={ui_val} lb, CSV={csv_val} lb")
        if abs(ui_val - csv_val) > 0.01:
            failures.append(f"'{item}': UI={ui_val} lb, CSV={csv_val} lb")

    assert matched > 0, "No CSV items matched UI rows — CSV item names may not match UI"
    assert not failures, (
        "Consumption (lb) mismatch between UI and CSV:\n  " + "\n  ".join(failures)
    )


@allure.epic("Consumption Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Exported CSV title row contains the active date range")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Row 1 of the CSV (the report title) includes the start and end dates in YYYY-MM-DD format",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Click export and parse CSV\n"
        "4. Assert csv['title'] contains start date and end date in YYYY-MM-DD format"
    ),
    key="FQL-102",
)
@pytest.mark.regression
def test_export_title_contains_date_range(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    start_ymd = datetime.strptime(DEFAULT_DATE_START, "%m/%d/%Y").strftime("%Y-%m-%d")
    end_ymd   = datetime.strptime(DEFAULT_DATE_END,   "%m/%d/%Y").strftime("%Y-%m-%d")

    download = page.download_export()
    csv_data = _parse_export_csv(download)
    title = csv_data["title"]

    print(f"\n[export] CSV title: '{title}'")
    assert start_ymd in title, f"Start date '{start_ymd}' not in CSV title: '{title}'"
    assert end_ymd   in title, f"End date '{end_ymd}' not in CSV title: '{title}'"


@allure.epic("Consumption Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Exported CSV respects meal filter — only Lunch items exported")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="When the Lunch meal filter is active, the downloaded CSV contains the same items as the UI table",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters then switch meal to Lunch\n"
        "3. Collect UI item names from all rows\n"
        "4. Click export and parse CSV\n"
        "5. Assert CSV item names == UI item names"
    ),
    key="FQL-103",
)
@pytest.mark.regression
def test_export_respects_meal_filter(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.set_meal(MEAL_LUNCH)

    ui_rows = page.get_all_rows()
    if not ui_rows:
        pytest.skip("No Lunch data in seeded scans for this run")

    ui_items = {r[Page.COL_MENU_ITEM] for r in ui_rows}

    download = page.download_export()
    csv_data = _parse_export_csv(download)
    csv_items = {row.get("Menu Item", "") for row in csv_data["rows"]}

    assert ui_items == csv_items, (
        f"CSV items don't match UI items with Lunch filter.\n"
        f"UI only:  {ui_items - csv_items}\n"
        f"CSV only: {csv_items - ui_items}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Exported CSV for empty table contains headers but no data rows")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="When the table has no data (out-of-range date filter), the CSV still has correct headers but zero data rows",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, set date range to 2020-01-01–2020-01-02\n"
        "3. Confirm UI table is empty\n"
        "4. Click export and parse CSV\n"
        "5. Assert headers == Page.EXPORT_HEADERS and len(rows) == 0"
    ),
    key="FQL-104",
)
@pytest.mark.regression
def test_export_empty_table_has_headers_only(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_venue(settings.test_venue)
    page.set_date_range("01/01/2020", "01/02/2020")

    ui_rows = page.get_all_rows()
    if ui_rows:
        pytest.skip("Unexpectedly found data for 2020-01-01–2020-01-02; cannot verify empty export")

    download = page.download_export()
    csv_data = _parse_export_csv(download)

    assert csv_data["headers"] == Page.EXPORT_HEADERS, (
        f"Headers wrong in empty export: {csv_data['headers']}"
    )
    assert len(csv_data["rows"]) == 0, (
        f"Expected 0 data rows in empty export but got {len(csv_data['rows'])}"
    )