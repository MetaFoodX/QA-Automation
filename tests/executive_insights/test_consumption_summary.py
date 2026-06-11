"""Consumption Summary drill-down consistency tests."""
import allure
import pytest

from config.settings import settings
from data.fixtures import RESTAURANT_A
from data.test_constants import (
    MEAL_ALL,
    CATEGORY_ALL,
    DEFAULT_DATE_START,
    DEFAULT_DATE_END,
    NO_DATA_AVAILABLE,
    SCAN_TYPE_REFILL,
    SERVED_LEFTOVER_TYPES,
    NOT_SERVED_LEFTOVER_TYPES,
)
from locators import common_locators as L
from pages.consumption_summary_page import ConsumptionSummaryPage as Page


OZ_PER_LB = 16

CURRENT_RESTAURANT_ID = RESTAURANT_A.id
CURRENT_VENUE_ID      = RESTAURANT_A.venues["v_a1"].id

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
    """Keep only scans that match the UI's restaurant + venue (all service periods shown)."""
    return [
        p for p in payloads
        if p["RestaurantID"] == CURRENT_RESTAURANT_ID
        and p["VenueID"]      == CURRENT_VENUE_ID
    ]


def _compute_expected_by_item(payloads: list[dict]) -> dict[str, dict]:
    """
    Mirror the server formula (grouped per day per item, matching UI's calculateTotal):
      Per day: consumption_day    = max(Refill - ServedLeftover, 0)
               overproduction_day = ServedLeftover + NotServedLeftover
    Then sum across days per item. All values returned in lb.
    """
    by_item_date: dict[tuple, dict] = {}

    for p in payloads:
        name = p["MenuItemName"]
        date = p["CapturedAt"][:10]
        t    = p["Type"]
        w    = p["Weight"]
        key  = (name, date)
        if key not in by_item_date:
            by_item_date[key] = {"refill": 0, "served_lo": 0, "not_served_lo": 0}
        if t == SCAN_TYPE_REFILL:
            by_item_date[key]["refill"] += w
        elif t in SERVED_LEFTOVER_TYPES:
            by_item_date[key]["served_lo"] += w
        elif t in NOT_SERVED_LEFTOVER_TYPES:
            by_item_date[key]["not_served_lo"] += w

    totals: dict[str, dict] = {}
    for (name, _), vals in by_item_date.items():
        if name not in totals:
            totals[name] = {"consumption": 0, "overproduction": 0}
        totals[name]["consumption"]    += max(vals["refill"] - vals["served_lo"], 0)
        totals[name]["overproduction"] += vals["served_lo"] + vals["not_served_lo"]

    return {
        name: {
            "consumption":    round(v["consumption"]    / OZ_PER_LB, 2),
            "overproduction": round(v["overproduction"] / OZ_PER_LB, 2),
            "production":     round((v["consumption"] + v["overproduction"]) / OZ_PER_LB, 2),
        }
        for name, v in totals.items()
    }


def _assert_column_matches(page, expected: dict[str, float], column, label):
    summary_rows = page.get_rows()
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in summary_rows:
        item = row[Page.COL_MENU_ITEM]
        if item not in expected:
            continue
        actual = _to_float(row[column])
        expected_val = expected[item]
        if round(abs(actual - expected_val), 2) > 0.01:
            failures.append(
                f"'{item}': expected={expected_val} lb, UI shows={actual} lb"
            )

    assert not failures, (
        f"{label} mismatches against seeded data:\n  " + "\n  ".join(failures)
    )


def _check_column_sum_matches(page: Page, column: str) -> list[str]:
    summary_rows = page.get_rows()

    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return []

    failures = []
    for i, summary in enumerate(summary_rows):
        item = summary[Page.COL_MENU_ITEM]
        s_val = _to_float(summary[column])

        page.click_menu_item_in_row(i)

        detail_rows = page.get_all_rows()
        d_val = sum(_to_float(r[column]) for r in detail_rows)

        if abs(d_val - s_val) > 0.01:
            failures.append(f"'{item}': summary={s_val}, detail sum={d_val}")

        page.navigate_back_to_summary()

    return failures


def _is_sorted_ascending(rows: list[dict], column: str) -> bool:
    values = [_to_float(r[column]) for r in rows]
    return values == sorted(values)


def _is_sorted_descending(rows: list[dict], column: str) -> bool:
    values = [_to_float(r[column]) for r in rows]
    return values == sorted(values, reverse=True)


def _assert_headers_have_unit(page: Page, unit: str):
    """Verify Production/Consumption/Overproduction headers all show the given unit."""
    headers = page.get_headers()
    expected = [
        f"{Page.COL_PRODUCTION_BASE} ({unit})",
        f"{Page.COL_CONSUMPTION_BASE} ({unit})",
        f"{Page.COL_OVERPRODUCTION_BASE} ({unit})",
    ]
    missing = [col for col in expected if not any(col in h for h in headers)]
    assert not missing, (
        f"Expected headers with '{unit}' unit missing: {missing}. "
        f"Got headers: {headers}"
    )


# ---------------------------------------------------------------------------
# Column Headers
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("All expected columns are present in default weight view")
@pytest.mark.testcase(
    component="consumption_summary",
    type="smoke, regression",
    description="All expected columns are present in the default weight view",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary via top nav\n"
        "3. Read the table headers\n"
        "4. Assert Menu Item, Venue, Production (lb), Consumption (lb), Overproduction (lb), and Days Served columns are all present\n"
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
        Page.COL_PRODUCTION,
        Page.COL_CONSUMPTION,
        Page.COL_OVERPRODUCTION,
        Page.COL_DAYS_SERVED,
    ]
    missing = [col for col in expected if col not in headers]
    assert not missing, f"Missing columns: {missing}. Got: {headers}"


@allure.epic("Consumption Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Default weight view shows (lb) unit in headers")
@pytest.mark.testcase(
    component="consumption_summary",
    type="smoke, regression",
    description="Default weight view shows (lb) unit in headers",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Verify Production, Consumption, and Overproduction headers all display '(lb)'"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_weight_view_shows_lb_unit(logged_in_page, seeded_basic_scans):
    """Default view; verify headers show (lb)."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    _assert_headers_have_unit(page, Page.WEIGHT_UNIT)


@allure.epic("Consumption Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Cost view toggle switches table headers to ($) unit")
@pytest.mark.testcase(
    component="consumption_summary",
    type="smoke, regression",
    description="Cost view toggle switches table headers to ($) unit",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the cost view toggle button\n"
        "5. Verify Production, Consumption, and Overproduction headers all display '($)'"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_cost_view_shows_dollar_unit(logged_in_page, seeded_basic_scans):
    """Click cost toggle; verify headers switch to ($)."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.toggle_cost_view()

    _assert_headers_have_unit(page, Page.COST_UNIT)


@allure.epic("Consumption Summary")
@allure.feature("Column Headers")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Toggling cost view and back returns headers to (lb) unit")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Toggling cost view off returns headers to lb unit",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the cost view toggle to switch to $ view\n"
        "5. Assert headers show ($) unit\n"
        "6. Click the cost view toggle again to switch back\n"
        "7. Assert Production, Consumption, and Overproduction headers all show (lb) unit"
    ),
)
@pytest.mark.regression
def test_toggle_cost_back_to_weight(logged_in_page):
    """Toggle to cost view then back — headers must return to lb unit."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.toggle_cost_view()
    _assert_headers_have_unit(page, Page.COST_UNIT)

    page.toggle_cost_view()
    _assert_headers_have_unit(page, Page.WEIGHT_UNIT)


# ---------------------------------------------------------------------------
# Math Invariants
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Math Invariants")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Production equals Consumption + Overproduction per row (weight view)")
@pytest.mark.testcase(
    component="consumption_summary",
    type="smoke, regression",
    description="Math invariant: Production equals Consumption + Overproduction per row",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Read all summary rows\n"
        "5. For each row, assert Production == Consumption + Overproduction (tolerance 0.01)"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_production_equals_consumption_plus_overproduction(logged_in_page, seeded_basic_scans):
    """Math invariant: Production == Consumption + Overproduction for every menu item."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    summary_rows = page.get_rows()

    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in summary_rows:
        item = row[Page.COL_MENU_ITEM]
        production = _to_float(row[Page.COL_PRODUCTION])
        consumption = _to_float(row[Page.COL_CONSUMPTION])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION])

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


@allure.epic("Consumption Summary")
@allure.feature("Math Invariants")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Production equals Consumption + Overproduction per row (cost view)")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Cost view math invariant: Production equals Consumption + Overproduction in $ view",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the cost view toggle to switch to $ view\n"
        "5. Read all summary rows\n"
        "6. For each row, assert Production ($) == Consumption ($) + Overproduction ($) (tolerance 0.01)\n"
        "7. Report all violations"
    ),
)
@pytest.mark.regression
def test_cost_view_production_equals_consumption_plus_overproduction(logged_in_page, seeded_basic_scans):
    """Math invariant must hold in cost ($) view too."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.toggle_cost_view()

    summary_rows = page.get_rows()
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in summary_rows:
        item = row[Page.COL_MENU_ITEM]
        production     = _to_float(row[Page.COL_PRODUCTION_COST])
        consumption    = _to_float(row[Page.COL_CONSUMPTION_COST])
        overproduction = _to_float(row[Page.COL_OVERPRODUCTION_COST])

        expected = consumption + overproduction
        if abs(production - expected) > 0.01:
            failures.append(
                f"'{item}': Production=${production}, "
                f"Consumption + Overproduction = ${consumption} + ${overproduction} = ${expected}"
            )

    assert not failures, (
        "Cost view math invariant violations:\n  " + "\n  ".join(failures)
    )


@allure.epic("Consumption Summary")
@allure.feature("Math Invariants")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Production is always >= Consumption for every row")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production is always >= Consumption for every row",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters (venue, meal=All, category=All, default date range)\n"
        "4. Read all rows across all pages\n"
        "5. For each row, assert Production >= Consumption (tolerance 0.01)\n"
        "6. Report all violations"
    ),
)
@pytest.mark.regression
def test_production_always_gte_consumption(logged_in_page, seeded_basic_scans):
    """Production must be >= Consumption for every row — business logic invariant."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    all_rows = page.get_all_rows()
    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' venue='{r[Page.COL_VENUE]}': production={_to_float(r[Page.COL_PRODUCTION])}, consumption={_to_float(r[Page.COL_CONSUMPTION])}"
        for r in all_rows
        if _to_float(r[Page.COL_PRODUCTION]) < _to_float(r[Page.COL_CONSUMPTION]) - 0.01
    ]
    assert not failures, (
        "Production should never be less than Consumption:\n  " + "\n  ".join(failures)
    )


@allure.epic("Consumption Summary")
@allure.feature("Math Invariants")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Production is always >= Overproduction for every row")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Production is always >= Overproduction for every row",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Read all rows across all pages\n"
        "5. For each row, assert Production >= Overproduction (tolerance 0.01)\n"
        "6. Report all violations"
    ),
)
@pytest.mark.regression
def test_production_always_gte_overproduction(logged_in_page, seeded_basic_scans):
    """Production must be >= Overproduction for every row — business logic invariant."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    all_rows = page.get_all_rows()
    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' venue='{r[Page.COL_VENUE]}': production={_to_float(r[Page.COL_PRODUCTION])}, overproduction={_to_float(r[Page.COL_OVERPRODUCTION])}"
        for r in all_rows
        if _to_float(r[Page.COL_PRODUCTION]) < _to_float(r[Page.COL_OVERPRODUCTION]) - 0.01
    ]
    assert not failures, (
        "Production should never be less than Overproduction:\n  " + "\n  ".join(failures)
    )


# ---------------------------------------------------------------------------
# Data Accuracy
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Production summary equals sum of detail rows per menu item")
@pytest.mark.testcase(
    component="consumption_summary",
    type="smoke, regression",
    description="Production summary equals sum of detail rows per menu item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary via top nav\n"
        "3. Apply default filters (venue, meal=All, category=All, default date range)\n"
        "4. For each summary row, click the menu item to drill down\n"
        "5. Read all pages of detail rows and sum the Production column\n"
        "6. Assert the sum equals the summary row's Production value (tolerance 0.01)\n"
        "7. Navigate back to summary and repeat for next item"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_production_sums_match_summary(logged_in_page, seeded_basic_scans):
    """Verify Production summary == sum of daily detail Production for every menu item."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    failures = _check_column_sum_matches(page, Page.COL_PRODUCTION)
    assert not failures, "Production mismatches:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Consumption summary equals sum of detail rows per menu item")
@pytest.mark.testcase(
    component="consumption_summary",
    type="smoke, regression",
    description="Consumption summary equals sum of detail rows per menu item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. For each summary row, click the menu item to drill down\n"
        "5. Sum the Consumption column across all detail pages\n"
        "6. Assert the sum equals the summary Consumption value (tolerance 0.01)\n"
        "7. Navigate back to summary and repeat"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_consumption_sums_match_summary(logged_in_page, seeded_basic_scans):
    """Verify Consumption summary == sum of daily detail Consumption for every menu item."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    failures = _check_column_sum_matches(page, Page.COL_CONSUMPTION)
    assert not failures, "Consumption mismatches:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Overproduction summary equals sum of detail rows per menu item")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Overproduction summary equals sum of daily detail rows per menu item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. For each summary row, click the menu item to drill down\n"
        "5. Read all pages of detail rows and sum the Overproduction column\n"
        "6. Assert the sum equals the summary row's Overproduction value (tolerance 0.01)\n"
        "7. Navigate back to summary and repeat for next item"
    ),
)
@pytest.mark.regression
def test_overproduction_sums_match_summary(logged_in_page, seeded_basic_scans):
    """Verify Overproduction summary == sum of daily detail Overproduction for every menu item."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    failures = _check_column_sum_matches(page, Page.COL_OVERPRODUCTION)
    assert not failures, "Overproduction mismatches:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Seeded data: UI Consumption matches formula max(Refill - ServedLeftover, 0)")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Seeded data: UI Consumption matches sum of Type=1 weights from JSON",
    steps=(
        "1. Insert seeded scans via API (session fixture)\n"
        "2. Log in as kitchen_sapna and navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. From seed JSON, sum weights where Type=1 per menu item; convert oz to lb (divide by 16)\n"
        "5. Read UI rows and assert the Consumption column matches computed value per item (tolerance 0.01)\n"
        "6. Session fixture cleans up inserted scans at end"
    ),
)
@pytest.mark.regression
def test_consumption_matches_seeded_data(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = {name: vals["consumption"] for name, vals in _compute_expected_by_item(relevant).items()}
    _assert_column_matches(page, expected, Page.COL_CONSUMPTION, "Consumption")


@allure.epic("Consumption Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Seeded data: UI Overproduction matches formula ServedLeftover + NotServedLeftover")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Seeded data: UI Overproduction matches sum of non-Type=1 weights from JSON",
    steps=(
        "1. Insert seeded scans via API\n"
        "2. Log in and navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. From seed JSON, sum weights where Type != 1 per menu item; convert oz to lb\n"
        "5. Read UI rows and assert the Overproduction column matches computed value per item (tolerance 0.01)"
    ),
)
@pytest.mark.regression
def test_overproduction_matches_seeded_data(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = {name: vals["overproduction"] for name, vals in _compute_expected_by_item(relevant).items()}
    _assert_column_matches(page, expected, Page.COL_OVERPRODUCTION, "Overproduction")


@allure.epic("Consumption Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Seeded data: UI Production matches formula Consumption + Overproduction")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Seeded data: UI Production matches sum of all weights from JSON",
    steps=(
        "1. Insert seeded scans via API\n"
        "2. Log in and navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. From seed JSON, sum all weights per menu item regardless of Type; convert oz to lb\n"
        "5. Read UI rows and assert the Production column matches computed value per item (tolerance 0.01)"
    ),
)
@pytest.mark.regression
def test_production_matches_seeded_data(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    relevant = _filter_for_current_view(seeded_basic_scans)
    expected = {name: vals["production"] for name, vals in _compute_expected_by_item(relevant).items()}
    _assert_column_matches(page, expected, Page.COL_PRODUCTION, "Production")


@allure.epic("Consumption Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("All rows have a non-empty Menu Item name")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="All rows have a non-empty Menu Item name",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Read all rows across all pages\n"
        "5. For each row, assert the Menu Item column is non-empty and non-whitespace\n"
        "6. Report any blank Menu Item rows"
    ),
)
@pytest.mark.regression
def test_all_rows_have_non_empty_menu_item(logged_in_page, seeded_basic_scans):
    """Every row must have a non-empty Menu Item name."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    all_rows = page.get_all_rows()
    failures = [
        f"Row {i+1} has empty Menu Item"
        for i, r in enumerate(all_rows)
        if not r.get(Page.COL_MENU_ITEM, "").strip()
    ]
    assert not failures, (
        "Rows with empty Menu Item found:\n  " + "\n  ".join(failures)
    )


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Venue filter shows only rows belonging to the selected venue")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Venue filter shows only rows belonging to the selected venue",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Select a specific venue in the venue filter\n"
        "4. Apply remaining default filters\n"
        "5. Read all rows across all pages\n"
        "6. Assert every row's Venue column matches the selected venue\n"
        "7. Report any rows from unexpected venues"
    ),
)
@pytest.mark.regression
def test_venue_filter_shows_only_selected_venue(logged_in_page, seeded_basic_scans):
    """When a venue is selected, every row must belong to that venue only."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    all_rows = page.get_all_rows()
    failures = [
        f"'{r[Page.COL_MENU_ITEM]}': venue='{r[Page.COL_VENUE]}' expected='{settings.test_venue}'"
        for r in all_rows
        if r.get(Page.COL_VENUE, "").strip() != settings.test_venue
    ]
    assert not failures, (
        "Rows from unexpected venues found:\n  " + "\n  ".join(failures)
    )


@allure.epic("Consumption Summary")
@allure.feature("Filters")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Out-of-range date filter shows empty table")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Out-of-range date filter shows empty table",
    steps=(
        "1. Log in and navigate to Consumption Summary\n"
        "2. Apply venue / meal / category filters\n"
        "3. Set date range to May 1-7, 2026 (outside the seed window)\n"
        "4. Assert get_rows() returns 0 rows\n"
        "5. (Optional) Verify 'No data available' message is visible"
    ),
)
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


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Breadcrumb shows the correct page name after navigation")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Breadcrumb shows correct page name after navigation",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Locate the breadcrumb element\n"
        "4. Assert the breadcrumb text contains 'Consumption Summary'\n"
        "5. Assert no error or unexpected page is shown"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_breadcrumb_shows_correct_text(logged_in_page):
    """Breadcrumb must show the page name after navigation."""
    page = Page(logged_in_page)
    page.open_via_nav()

    breadcrumb = page.page.locator(L.BREADCRUMB_PAGE_LINK)
    assert Page.SIDEBAR_ITEM in breadcrumb.inner_text(), (
        f"Expected '{Page.SIDEBAR_ITEM}' in breadcrumb, got: {breadcrumb.inner_text()}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Breadcrumb click returns to summary with filters and day toggle intact")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Breadcrumb click returns to summary with filters and day toggle preserved",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the menu item in row 0 to drill down\n"
        "5. Click the breadcrumb to return to summary\n"
        "6. Wait for the table to settle\n"
        "7. Assert Date and Day columns are still visible (day toggle preserved)\n"
        "8. Assert the venue filter still shows the selected venue"
    ),
)
@pytest.mark.regression
def test_breadcrumb_preserves_filters_and_day_toggle(logged_in_page, seeded_basic_scans):
    """Clicking breadcrumb returns to summary with filters and day toggle state intact."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_menu_item_in_row(0)

    page.page.locator(L.BREADCRUMB_PAGE_LINK).click()
    page._wait_for_table_to_settle()

    headers = page.get_headers()
    assert Page.COL_DATE in headers, "Date column should still be visible after breadcrumb click"
    assert Page.COL_DAY in headers, "Day column should still be visible after breadcrumb click"
    assert page.is_venue_selected(settings.test_venue), (
        f"Venue filter changed after breadcrumb. Expected '{settings.test_venue}' to still be selected."
    )


@allure.epic("Consumption Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking a menu item auto-enables day toggle showing Date and Day columns")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Clicking a menu item auto-enables day toggle (Date and Day columns appear)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the menu item link in the first row to drill down\n"
        "5. Read the table headers in the detail view\n"
        "6. Assert 'Date' column is present\n"
        "7. Assert 'Day' column is present"
    ),
)
@pytest.mark.regression
def test_clicking_menu_item_enables_day_toggle(logged_in_page, seeded_basic_scans):
    """Clicking a menu item must auto-enable day toggle — Date and Day columns appear in detail view."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_menu_item_in_row(0)

    headers = page.get_headers()
    assert Page.COL_DATE in headers, f"Expected Date column after clicking menu item, got: {headers}"
    assert Page.COL_DAY in headers, f"Expected Day column after clicking menu item, got: {headers}"


@allure.epic("Consumption Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Day toggle shows Date and Day columns")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Day toggle shows Date and Day columns",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the day view toggle\n"
        "5. Read the table headers\n"
        "6. Assert 'Date' column is present\n"
        "7. Assert 'Day' column is present"
    ),
)
@pytest.mark.regression
def test_day_toggle_shows_date_and_day_columns(logged_in_page, seeded_basic_scans):
    """Switching to day view must show Date and Day columns."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.toggle_day_view()

    headers = page.get_headers()
    assert Page.COL_DATE in headers, f"Expected 'Date' column in day view, got: {headers}"
    assert Page.COL_DAY in headers, f"Expected 'Day' column in day view, got: {headers}"


@allure.epic("Consumption Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Toggling day view off hides Date and Day columns")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Toggling day view off hides Date and Day columns",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the day view toggle to enable it\n"
        "5. Click the day view toggle again to disable it\n"
        "6. Read the table headers\n"
        "7. Assert 'Date' column is NOT present\n"
        "8. Assert 'Day' column is NOT present"
    ),
)
@pytest.mark.regression
def test_day_toggle_back_hides_date_and_day_columns(logged_in_page, seeded_basic_scans):
    """Toggling back from day view must hide Date and Day columns."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)
    page.toggle_day_view()
    page.toggle_day_view()

    headers = page.get_headers()
    assert Page.COL_DATE not in headers, f"Date column should be hidden in range view, got: {headers}"
    assert Page.COL_DAY not in headers, f"Day column should be hidden in range view, got: {headers}"


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Default sort is alphabetical A-Z by Menu Item")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Default sort is alphabetical A-Z by Menu Item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Read the first page of rows\n"
        "5. Extract the Menu Item column values\n"
        "6. Assert the list is sorted A-Z (case-insensitive)\n"
        "7. Report the actual vs expected order if not sorted"
    ),
)
@pytest.mark.regression
def test_default_sort_is_alphabetical_by_menu_item(logged_in_page, seeded_basic_scans):
    """Table must load sorted A-Z by Menu Item by default."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    rows = page.get_rows()
    if not rows:
        print(NO_DATA_AVAILABLE)
        return

    names = [r[Page.COL_MENU_ITEM] for r in rows]
    expected = sorted(names, key=lambda s: s.lower())
    assert names == expected, (
        f"Default sort is not alphabetical A-Z.\n"
        f"Got:      {names}\n"
        f"Expected: {expected}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking Production column once sorts values low to high")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Clicking Production column header once sorts values ascending (low to high)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the Production column header once\n"
        "5. Read the visible rows\n"
        "6. Extract Production values\n"
        "7. Assert values are sorted in ascending order"
    ),
)
@pytest.mark.regression
def test_production_sort_ascending(logged_in_page, seeded_basic_scans):
    """Clicking Production column once sorts values low to high."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_column_sort(Page.COL_PRODUCTION)
    rows = page.get_rows()

    assert _is_sorted_ascending(rows, Page.COL_PRODUCTION), (
        f"Production not sorted ascending. Values: {[_to_float(r[Page.COL_PRODUCTION]) for r in rows]}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking Production column twice sorts values high to low")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Clicking Production column header twice sorts values descending (high to low)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the Production column header twice\n"
        "5. Read the visible rows\n"
        "6. Extract Production values\n"
        "7. Assert values are sorted in descending order"
    ),
)
@pytest.mark.regression
def test_production_sort_descending(logged_in_page, seeded_basic_scans):
    """Clicking Production column twice sorts values high to low."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_column_sort(Page.COL_PRODUCTION)
    page.click_column_sort(Page.COL_PRODUCTION)
    rows = page.get_rows()

    assert _is_sorted_descending(rows, Page.COL_PRODUCTION), (
        f"Production not sorted descending. Values: {[_to_float(r[Page.COL_PRODUCTION]) for r in rows]}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking Consumption column once sorts values low to high")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Clicking Consumption column header once sorts values ascending (low to high)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the Consumption column header once\n"
        "5. Read the visible rows\n"
        "6. Extract Consumption values\n"
        "7. Assert values are sorted in ascending order"
    ),
)
@pytest.mark.regression
def test_consumption_sort_ascending(logged_in_page, seeded_basic_scans):
    """Clicking Consumption column once sorts values low to high."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_column_sort(Page.COL_CONSUMPTION)
    rows = page.get_rows()

    assert _is_sorted_ascending(rows, Page.COL_CONSUMPTION), (
        f"Consumption not sorted ascending. Values: {[_to_float(r[Page.COL_CONSUMPTION]) for r in rows]}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking Consumption column twice sorts values high to low")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Clicking Consumption column header twice sorts values descending (high to low)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the Consumption column header twice\n"
        "5. Read the visible rows\n"
        "6. Extract Consumption values\n"
        "7. Assert values are sorted in descending order"
    ),
)
@pytest.mark.regression
def test_consumption_sort_descending(logged_in_page, seeded_basic_scans):
    """Clicking Consumption column twice sorts values high to low."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_column_sort(Page.COL_CONSUMPTION)
    page.click_column_sort(Page.COL_CONSUMPTION)
    rows = page.get_rows()

    assert _is_sorted_descending(rows, Page.COL_CONSUMPTION), (
        f"Consumption not sorted descending. Values: {[_to_float(r[Page.COL_CONSUMPTION]) for r in rows]}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking Overproduction column once sorts values low to high")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Clicking Overproduction column header once sorts values ascending (low to high)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the Overproduction column header once\n"
        "5. Read the visible rows\n"
        "6. Extract Overproduction values\n"
        "7. Assert values are sorted in ascending order"
    ),
)
@pytest.mark.regression
def test_overproduction_sort_ascending(logged_in_page, seeded_basic_scans):
    """Clicking Overproduction column once sorts values low to high."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_column_sort(Page.COL_OVERPRODUCTION)
    rows = page.get_rows()

    assert _is_sorted_ascending(rows, Page.COL_OVERPRODUCTION), (
        f"Overproduction not sorted ascending. Values: {[_to_float(r[Page.COL_OVERPRODUCTION]) for r in rows]}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking Overproduction column twice sorts values high to low")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Clicking Overproduction column header twice sorts values descending (high to low)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the Overproduction column header twice\n"
        "5. Read the visible rows\n"
        "6. Extract Overproduction values\n"
        "7. Assert values are sorted in descending order"
    ),
)
@pytest.mark.regression
def test_overproduction_sort_descending(logged_in_page, seeded_basic_scans):
    """Clicking Overproduction column twice sorts values high to low."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_column_sort(Page.COL_OVERPRODUCTION)
    page.click_column_sort(Page.COL_OVERPRODUCTION)
    rows = page.get_rows()

    assert _is_sorted_descending(rows, Page.COL_OVERPRODUCTION), (
        f"Overproduction not sorted descending. Values: {[_to_float(r[Page.COL_OVERPRODUCTION]) for r in rows]}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking Days Served column once sorts values low to high")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Clicking Days Served column header once sorts values ascending (low to high)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the Days Served column header once\n"
        "5. Read the visible rows\n"
        "6. Extract Days Served values\n"
        "7. Assert values are sorted in ascending order"
    ),
)
@pytest.mark.regression
def test_days_served_sort_ascending(logged_in_page, seeded_basic_scans):
    """Clicking Days Served column once sorts values low to high."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_column_sort(Page.COL_DAYS_SERVED)
    rows = page.get_rows()

    values = [_to_float(r[Page.COL_DAYS_SERVED]) for r in rows]
    assert values == sorted(values), (
        f"Days Served not sorted ascending. Values: {values}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking Days Served column twice sorts values high to low")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Clicking Days Served column header twice sorts values descending (high to low)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the Days Served column header twice\n"
        "5. Read the visible rows\n"
        "6. Extract Days Served values\n"
        "7. Assert values are sorted in descending order"
    ),
)
@pytest.mark.regression
def test_days_served_sort_descending(logged_in_page, seeded_basic_scans):
    """Clicking Days Served column twice sorts values high to low."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_column_sort(Page.COL_DAYS_SERVED)
    page.click_column_sort(Page.COL_DAYS_SERVED)
    rows = page.get_rows()

    values = [_to_float(r[Page.COL_DAYS_SERVED]) for r in rows]
    assert values == sorted(values, reverse=True), (
        f"Days Served not sorted descending. Values: {values}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Sorting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Active sort persists after changing the date filter")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Active sort order persists after changing a filter",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Click the Production column header twice to sort descending\n"
        "5. Change the date range filter\n"
        "6. Wait for the table to reload\n"
        "7. Read the visible rows\n"
        "8. Assert Production values are still sorted descending"
    ),
)
@pytest.mark.regression
def test_sort_persists_after_filter_change(logged_in_page, seeded_basic_scans):
    """Active sort must persist when a filter changes — AntD re-applies sort on reloaded data."""
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    page.click_column_sort(Page.COL_PRODUCTION)
    page.click_column_sort(Page.COL_PRODUCTION)

    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)

    rows_after = page.get_rows()
    if not rows_after:
        print(NO_DATA_AVAILABLE)
        return

    values_after = [_to_float(r[Page.COL_PRODUCTION]) for r in rows_after]
    assert values_after == sorted(values_after, reverse=True), (
        f"Production descending sort did not persist after filter change.\n"
        f"Values after filter: {values_after}"
    )
