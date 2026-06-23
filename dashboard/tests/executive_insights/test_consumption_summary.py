"""Consumption Summary drill-down consistency tests."""
import allure
import pytest

from shared.config.settings import settings
from shared.data.fixtures import RESTAURANT_A
from shared.data.test_constants import *  # noqa: F401, F403
from dashboard.locators import common_locators as L
from dashboard.pages.consumption_summary_page import ConsumptionSummaryPage as Page


OZ_PER_LB = 16

CURRENT_RESTAURANT_ID = RESTAURANT_A.id
CURRENT_VENUE_ID      = RESTAURANT_A.venues["v_a1"].id
CURRENT_VENUE_NAME    = RESTAURANT_A.venues["v_a1"].name
SECOND_VENUE_ID       = RESTAURANT_A.venues["v_a2"].id
SECOND_VENUE_NAME     = RESTAURANT_A.venues["v_a2"].name
LUNCH_SP_ID           = RESTAURANT_A.service_periods["lunch"].id
DINNER_SP_ID          = RESTAURANT_A.service_periods["dinner"].id
ALL_DAY_SP_ID         = RESTAURANT_A.service_periods["all_day"].id

def _to_float(s: str) -> float:
    cleaned = (
        s.strip()
        .replace(",", "")
        .replace(Page.WEIGHT_UNIT, "")
        .replace(Page.COST_UNIT, "")
        .strip()
    )
    return float(cleaned) if cleaned else 0.0


def _apply_filters(
    page: Page,
    venue: str = settings.test_venue,
    meal: str = MEAL_ALL,
    category: str = CATEGORY_ALL,
):
    page.set_venue(venue)
    page.set_meal(meal)
    page.set_category(category)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)


def _filter_by_service_period(payloads: list[dict], sp_id: str) -> list[dict]:
    return [p for p in payloads if p["ServicePeriodID"] == sp_id]


def _filter_by_category(payloads: list[dict], category: str) -> list[dict]:
    category_items = {mi.name for mi in RESTAURANT_A.menu_items.values() if mi.category == category}
    return [p for p in payloads if p["MenuItemName"] in category_items]


def _filter_for_current_view(payloads: list[dict], venue_id: str | None = CURRENT_VENUE_ID) -> list[dict]:
    """Keep scans matching the restaurant. venue_id=None means All Venues (no venue filter)."""
    return [
        p for p in payloads
        if p["RestaurantID"] == CURRENT_RESTAURANT_ID
        and (venue_id is None or p["VenueID"] == venue_id)
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
# Breadcrumb
# ---------------------------------------------------------------------------

def _get_breadcrumb_links(page: Page) -> list[str]:
    """Return non-empty breadcrumb item texts."""
    items = page.page.locator(L.BREADCRUMB_ITEM_LINK).all_inner_texts()
    return [t.strip() for t in items if t.strip()]


@allure.epic("Consumption Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Breadcrumb shows only 'Consumption Summary' on initial page load")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="On summary page load the breadcrumb contains exactly 'Consumption Summary' with no item name appended",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Read all span.ant-breadcrumb-link texts inside .custom-breadcrumb\n"
        "4. Assert 'Consumption Summary' is present\n"
        "5. Assert no menu item name appears alongside it"
    ),
)
@pytest.mark.regression
def test_breadcrumb_has_consumption_summary_on_load(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()

    links = _get_breadcrumb_links(page)
    assert any(Page.SIDEBAR_ITEM in t for t in links), (
        f"'{Page.SIDEBAR_ITEM}' not found in breadcrumb. Got: {links}"
    )
    # Only 1 meaningful entry — no item name yet
    cs_idx = next(i for i, t in enumerate(links) if Page.SIDEBAR_ITEM in t)
    assert len(links) == cs_idx + 1, (
        f"Expected only '{Page.SIDEBAR_ITEM}' in breadcrumb on load, got: {links}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Breadcrumb stays as 'Consumption Summary' after applying all-type filters")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Applying All Venues, All Meals, All Categories filters does not add any extra level to the breadcrumb",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Select '- All Venues -', '- All Meals -', '- All Categories -' and apply date range\n"
        "4. Read breadcrumb texts\n"
        "5. Assert 'Consumption Summary' is still the last meaningful item — no item name appended"
    ),
)
@pytest.mark.regression
def test_breadcrumb_unchanged_after_applying_filters(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, venue=VENUE_ALL, meal=MEAL_ALL, category=CATEGORY_ALL)

    links = _get_breadcrumb_links(page)
    assert any(Page.SIDEBAR_ITEM in t for t in links), (
        f"'{Page.SIDEBAR_ITEM}' not found in breadcrumb after filters. Got: {links}"
    )
    last_meaningful = links[-1]
    assert Page.SIDEBAR_ITEM in last_meaningful, (
        f"Breadcrumb gained an extra level after applying filters. Got: {links}"
    )


@allure.epic("Consumption Summary")
@allure.feature("Navigation")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Clicking a menu item adds the item name as a second breadcrumb level")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="After clicking a menu item the breadcrumb shows 'Consumption Summary / <item name>'",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Record the menu item name from the first row\n"
        "4. Click the menu item to drill down\n"
        "5. Read breadcrumb texts\n"
        "6. Assert 'Consumption Summary' is still present\n"
        "7. Assert the clicked item's name appears as the last breadcrumb level"
    ),
)
@pytest.mark.regression
def test_breadcrumb_adds_item_name_after_drill_down(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    rows = page.get_rows()
    if not rows:
        print(NO_DATA_AVAILABLE)
        return

    item_name = rows[0][Page.COL_MENU_ITEM]
    page.click_menu_item_in_row(0)

    links = _get_breadcrumb_links(page)
    assert any(Page.SIDEBAR_ITEM in t for t in links), (
        f"'{Page.SIDEBAR_ITEM}' missing from breadcrumb in detail view. Got: {links}"
    )
    assert any(item_name in t for t in links), (
        f"Item name '{item_name}' not found in breadcrumb after drill-down. Got: {links}"
    )
    cs_idx   = next(i for i, t in enumerate(links) if Page.SIDEBAR_ITEM in t)
    item_idx = next(i for i, t in enumerate(links) if item_name in t)
    assert item_idx > cs_idx, (
        f"Item name '{item_name}' should appear after '{Page.SIDEBAR_ITEM}' in breadcrumb. Got: {links}"
    )


# ---------------------------------------------------------------------------
# Date and Day Columns
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Date and Day Columns")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("All dates in detail view fall within the selected date range")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Every Date value in the daily detail view is within the filter's start and end date",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Click the first menu item to drill into the daily detail view\n"
        "4. Read all detail rows across all pages\n"
        "5. Parse each Date value and assert it falls within [DEFAULT_DATE_START, DEFAULT_DATE_END]"
    ),
)
@pytest.mark.regression
def test_detail_view_dates_within_selected_range(logged_in_page, seeded_basic_scans):
    from datetime import datetime as dt
    _ = seeded_basic_scans

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)

    range_start = dt.strptime(DEFAULT_DATE_START, "%m/%d/%Y").date()
    range_end   = dt.strptime(DEFAULT_DATE_END,   "%m/%d/%Y").date()

    failures = []
    for row in page.get_all_rows():
        date_str = row.get(Page.COL_DATE, "").strip()
        if not date_str:
            failures.append("Row has empty Date")
            continue
        try:
            row_date = dt.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            failures.append(f"Cannot parse date '{date_str}'")
            continue
        if not (range_start <= row_date <= range_end):
            failures.append(
                f"'{date_str}' is outside range [{DEFAULT_DATE_START}, {DEFAULT_DATE_END}]"
            )

    assert not failures, "Dates outside selected range:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Date and Day Columns")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Day column shows the correct weekday name for each date row")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="For each row in the daily detail view, the Day column must match the weekday of the Date column",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Click the first menu item to drill into the daily detail view\n"
        "4. For each row, parse the Date value and derive the expected weekday (e.g. Monday)\n"
        "5. Assert the Day column value matches the expected weekday"
    ),
)
@pytest.mark.regression
def test_detail_view_day_column_matches_date(logged_in_page, seeded_basic_scans):
    from datetime import datetime as dt
    _ = seeded_basic_scans

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)

    failures = []
    for row in page.get_all_rows():
        date_str = row.get(Page.COL_DATE, "").strip()
        day_str  = row.get(Page.COL_DAY,  "").strip()
        if not date_str or not day_str:
            continue
        try:
            expected_day = dt.strptime(date_str, "%Y-%m-%d").strftime("%A")
        except ValueError:
            failures.append(f"Cannot parse date '{date_str}'")
            continue
        if day_str != expected_day:
            failures.append(f"Date '{date_str}': expected Day='{expected_day}', got '{day_str}'")

    assert not failures, "Day/Date mismatches:\n  " + "\n  ".join(failures)


@allure.epic("Consumption Summary")
@allure.feature("Date and Day Columns")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("No duplicate dates appear for a single menu item in detail view")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Each date appears at most once in the daily detail view — data is aggregated per day per item",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Click the first menu item to drill into the daily detail view\n"
        "4. Collect all Date values across all pages\n"
        "5. Assert no date appears more than once"
    ),
)
@pytest.mark.regression
def test_detail_view_no_duplicate_dates(logged_in_page, seeded_basic_scans):
    _ = seeded_basic_scans

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)

    dates = [
        r.get(Page.COL_DATE, "").strip()
        for r in page.get_all_rows()
        if r.get(Page.COL_DATE, "").strip()
    ]
    seen, duplicates = set(), []
    for d in dates:
        if d in seen:
            duplicates.append(d)
        seen.add(d)

    assert not duplicates, f"Duplicate dates in detail view: {duplicates}"


@allure.epic("Consumption Summary")
@allure.feature("Date and Day Columns")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Narrowing the date range reduces the dates visible in detail view")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="After narrowing the date range filter, detail view shows fewer dates and all are within the new range",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default (7-day) date range\n"
        "3. Click the first menu item and record all visible dates\n"
        "4. Navigate back to summary and apply a narrower date range (last 3 days)\n"
        "5. Click the first menu item again and assert visible dates <= original count\n"
        "6. Assert all visible dates fall within the narrower range"
    ),
)
@pytest.mark.regression
def test_narrowing_date_range_reduces_detail_dates(logged_in_page, seeded_basic_scans):
    from datetime import datetime as dt, timedelta
    _ = seeded_basic_scans

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    wide_dates = {r.get(Page.COL_DATE, "").strip() for r in page.get_all_rows() if r.get(Page.COL_DATE, "").strip()}
    page.navigate_back_to_summary()

    from datetime import date as date_cls
    narrow_end   = date_cls.today()
    narrow_start = narrow_end - timedelta(days=3)
    page.set_date_range(narrow_start.strftime("%m/%d/%Y"), narrow_end.strftime("%m/%d/%Y"))

    if not page.get_rows():
        return  # narrower range has no data — acceptable

    page.click_menu_item_in_row(0)
    narrow_dates = {r.get(Page.COL_DATE, "").strip() for r in page.get_all_rows() if r.get(Page.COL_DATE, "").strip()}

    assert len(narrow_dates) <= len(wide_dates), (
        f"Narrower range shows more dates than wider range. Wide: {len(wide_dates)}, Narrow: {len(narrow_dates)}"
    )

    failures = [
        d for d in narrow_dates
        if not (narrow_start <= dt.strptime(d, "%Y-%m-%d").date() <= narrow_end)
    ]
    assert not failures, f"Dates outside narrow range [{narrow_start}, {narrow_end}]: {failures}"


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
)
@pytest.mark.regression
def test_category_kitchen_waste_filter_shows_only_kitchen_waste_items(logged_in_page, seeded_basic_scans):
    kw_items = {mi.name for mi in RESTAURANT_A.menu_items.values() if mi.category == CATEGORY_KITCHEN_WASTE}

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_KITCHEN_WASTE)

    all_rows = page.get_all_rows()
    if not all_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' is not a Kitchen Waste item"
        for r in all_rows
        if r[Page.COL_MENU_ITEM] not in kw_items
    ]
    assert not failures, "Non-Kitchen-Waste items visible with Kitchen Waste filter:\n  " + "\n  ".join(failures)


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
)
@pytest.mark.regression
def test_category_kitchen_waste_production_equals_overproduction(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_KITCHEN_WASTE)

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
        if abs(production - overproduction) > 0.01:
            failures.append(f"'{item}': Production={production}, Overproduction={overproduction}")
        if consumption != 0:
            failures.append(f"'{item}': expected Consumption=0, got {consumption}")

    assert not failures, "Kitchen Waste invariant violations:\n  " + "\n  ".join(failures)


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
)
@pytest.mark.regression
def test_category_post_consumer_filter_shows_only_post_consumer_items(logged_in_page, seeded_basic_scans):
    pc_items = {mi.name for mi in RESTAURANT_A.menu_items.values() if mi.category == CATEGORY_POST_CONSUMER}

    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_POST_CONSUMER)

    all_rows = page.get_all_rows()
    if not all_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = [
        f"'{r[Page.COL_MENU_ITEM]}' is not a Post-Consumer item"
        for r in all_rows
        if r[Page.COL_MENU_ITEM] not in pc_items
    ]
    assert not failures, "Non-Post-Consumer items visible with Post-Consumer filter:\n  " + "\n  ".join(failures)


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
)
@pytest.mark.regression
def test_category_post_consumer_production_equals_overproduction(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page, category=CATEGORY_POST_CONSUMER)

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
        if abs(production - overproduction) > 0.01:
            failures.append(f"'{item}': Production={production}, Overproduction={overproduction}")
        if consumption != 0:
            failures.append(f"'{item}': expected Consumption=0, got {consumption}")

    assert not failures, "Post-Consumer invariant violations:\n  " + "\n  ".join(failures)


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
# Data Accuracy — additional (skeletons)
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
)
@pytest.mark.regression
def test_days_served_equals_unique_dates_in_seeded_data(logged_in_page, seeded_basic_scans):
    pass


@allure.epic("Consumption Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("All numeric values (Production, Consumption, Overproduction) are non-negative")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="No negative values appear in Production, Consumption, or Overproduction columns",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Read all rows across all pages\n"
        "4. Assert Production >= 0, Consumption >= 0, Overproduction >= 0 for every row"
    ),
)
@pytest.mark.regression
def test_all_numeric_values_are_non_negative(logged_in_page, seeded_basic_scans):
    pass


@allure.epic("Consumption Summary")
@allure.feature("Data Accuracy")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Days Served value is always >= 1 for all visible rows")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Days Served column never shows 0 or negative — every visible row was served at least once",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary, apply default filters\n"
        "3. Read all rows across all pages\n"
        "4. Assert Days Served >= 1 for every row"
    ),
)
@pytest.mark.regression
def test_days_served_always_gte_one(logged_in_page, seeded_basic_scans):
    pass


# ---------------------------------------------------------------------------
# Export (skeletons)
# ---------------------------------------------------------------------------

@allure.epic("Consumption Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Export button is present and enabled on the Consumption Summary page")
@pytest.mark.testcase(
    component="consumption_summary",
    type="smoke, regression",
    description="Export button is visible and clickable on the summary page",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply default filters\n"
        "4. Locate the export (download) button\n"
        "5. Assert the button is visible and not disabled"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_export_button_is_present_and_enabled(logged_in_page, seeded_basic_scans):
    pass


@allure.epic("Consumption Summary")
@allure.feature("Export")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Export button is disabled when table has no data")
@pytest.mark.testcase(
    component="consumption_summary",
    type="regression",
    description="Export button is disabled or hidden when the table is empty (no data for selected filters)",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Consumption Summary\n"
        "3. Apply out-of-range date filter to produce empty table\n"
        "4. Locate the export button\n"
        "5. Assert the button is disabled or not visible"
    ),
)
@pytest.mark.regression
def test_export_button_disabled_when_no_data(logged_in_page, seeded_basic_scans):
    pass
