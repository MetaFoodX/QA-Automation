"""Shared helpers and constants for Overproduction Summary tests."""
import csv

from shared.config.settings import settings
from shared.data.fixtures import RESTAURANT_A
from shared.data.test_constants import *  # noqa: F401, F403
from dashboard.locators import common_locators as L
from dashboard.pages.overproduction_summary_page import OverproductionSummaryPage as Page


OZ_PER_LB = 16

VENUE_ALL_OP           = "- All Venues -"

DESTINATION_ALL        = "All Destinations"
DESTINATION_REUSE      = "Reuse"
DESTINATION_DONATION   = "Donation"
DESTINATION_COMPOSTABLE = "Compostable"

CURRENT_RESTAURANT_ID = RESTAURANT_A.id
CURRENT_VENUE_ID      = RESTAURANT_A.venues["v_a1"].id
CURRENT_VENUE_NAME    = RESTAURANT_A.venues["v_a1"].name
SECOND_VENUE_ID       = RESTAURANT_A.venues["v_a2"].id
SECOND_VENUE_NAME     = RESTAURANT_A.venues["v_a2"].name
LUNCH_SP_ID           = RESTAURANT_A.service_periods["lunch"].id
DINNER_SP_ID          = RESTAURANT_A.service_periods["dinner"].id
ALL_DAY_SP_ID         = RESTAURANT_A.service_periods["all_day"].id

# Scan types that contribute to each overproduction destination
REUSE_TYPES        = {SCAN_TYPE_LEFTOVER_REUSE, SCAN_TYPE_NOT_SERVED_LEFTOVER_REUSE}
DONATION_TYPES     = {SCAN_TYPE_LEFTOVER_DONATION, SCAN_TYPE_NOT_SERVED_LEFTOVER_DONATION}
COMPOSTABLE_TYPES  = {SCAN_TYPE_LEFTOVER_COMPOSTABLE, SCAN_TYPE_NOT_SERVED_LEFTOVER_COMPOSTABLE}
ALL_OP_TYPES       = REUSE_TYPES | DONATION_TYPES | COMPOSTABLE_TYPES


def _to_float(s: str) -> float:
    cleaned = (
        s.strip()
        .replace(",", "")
        .replace(Page.WEIGHT_UNIT, "")
        .replace(Page.COST_UNIT, "")
        .strip()
    )
    return float(cleaned) if cleaned and cleaned != "N/A" else 0.0


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
    """Keep scans matching the restaurant. venue_id=None means All Venues."""
    return [
        p for p in payloads
        if p["RestaurantID"] == CURRENT_RESTAURANT_ID
        and (venue_id is None or p["VenueID"] == venue_id)
        and p["Type"] in ALL_OP_TYPES
    ]


def _compute_expected_by_item(payloads: list[dict]) -> dict[str, dict]:
    """
    Compute expected overproduction totals per menu item from seeded scan payloads.

    Formula (weights in oz, converted to lb at return):
      reuse       = sum of type 4 (served reuse) + type 9 (not served reuse)
      donation    = sum of type 3 (served donation) + type 8 (not served donation)
      compostable = sum of type 2 (served compostable) + type 7 (not served compostable)
      total       = reuse + donation + compostable
    """
    totals: dict[str, dict] = {}

    for p in payloads:
        name = p["MenuItemName"]
        t    = p["Type"]
        w    = p["Weight"]

        if t not in ALL_OP_TYPES:
            continue

        if name not in totals:
            totals[name] = {"reuse": 0, "donation": 0, "compostable": 0}

        if t in REUSE_TYPES:
            totals[name]["reuse"] += w
        elif t in DONATION_TYPES:
            totals[name]["donation"] += w
        elif t in COMPOSTABLE_TYPES:
            totals[name]["compostable"] += w

    return {
        name: {
            "reuse":        round(v["reuse"]        / OZ_PER_LB, 2),
            "donation":     round(v["donation"]      / OZ_PER_LB, 2),
            "compostable":  round(v["compostable"]   / OZ_PER_LB, 2),
            "total":        round((v["reuse"] + v["donation"] + v["compostable"]) / OZ_PER_LB, 2),
        }
        for name, v in totals.items()
    }


def _assert_column_matches(page: Page, expected: dict[str, float], column: str, label: str):
    summary_rows = page.get_rows()
    if not summary_rows:
        print(NO_DATA_AVAILABLE)
        return

    failures = []
    for row in summary_rows:
        item = row.get(Page.COL_MENU_ITEM, "")
        if item not in expected:
            continue
        actual = _to_float(row.get(column, "0"))
        expected_val = expected[item]
        if round(abs(actual - expected_val), 2) > 0.01:
            failures.append(
                f"'{item}': expected={expected_val} lb, UI shows={actual} lb"
            )

    assert not failures, (
        f"{label} mismatches against seeded data:\n  " + "\n  ".join(failures)
    )


def _assert_headers_have_unit(page: Page, unit: str):
    """Verify Total Overproduction, Reuse, Donation, Compostable headers all show the given unit."""
    headers = page.get_headers()
    expected = [
        f"{Page.COL_TOTAL_OVERPRODUCTION_BASE} ({unit})",
        f"{Page.COL_REUSE_BASE} ({unit})",
        f"{Page.COL_DONATION_BASE} ({unit})",
        f"{Page.COL_COMPOSTABLE_BASE} ({unit})",
    ]
    missing = [col for col in expected if not any(col in h for h in headers)]
    assert not missing, (
        f"Expected headers with '{unit}' unit missing: {missing}. Got: {headers}"
    )


def _get_breadcrumb_links(page: Page) -> list[str]:
    """Return non-empty breadcrumb item texts."""
    items = page.page.locator(L.BREADCRUMB_ITEM_LINK).all_inner_texts()
    return [t.strip() for t in items if t.strip()]


def _is_sorted_ascending(rows: list[dict], column: str) -> bool:
    values = [_to_float(r.get(column, "0")) for r in rows]
    return values == sorted(values)


def _is_sorted_descending(rows: list[dict], column: str) -> bool:
    values = [_to_float(r.get(column, "0")) for r in rows]
    return values == sorted(values, reverse=True)


def _filter_items_for_service_period(payloads: list[dict], sp_id: str) -> set[str]:
    """Return set of menu item names that have overproduction scans in given service period."""
    return {p["MenuItemName"] for p in payloads
            if p["ServicePeriodID"] == sp_id and p["Type"] in ALL_OP_TYPES}


def _parse_export_csv(download) -> dict:
    """Parse a Playwright Download object as a CSV export.

    Returns:
        {
            "title":   str,
            "headers": list[str],
            "rows":    list[dict],
        }
    """
    path = download.path()
    with open(path, newline="", encoding="utf-8-sig") as f:
        all_rows = list(csv.reader(f))

    if not all_rows:
        return {"title": "", "headers": [], "rows": []}

    title = all_rows[0][0].strip() if all_rows[0] else ""
    headers = all_rows[2] if len(all_rows) > 2 else []
    data_rows = [
        dict(zip(headers, row))
        for row in all_rows[3:]
        if any(c.strip() for c in row)
    ]
    return {"title": title, "headers": headers, "rows": data_rows}
