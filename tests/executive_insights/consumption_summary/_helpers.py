"""Shared helpers and constants for Consumption Summary tests."""
import allure
import csv
import pytest


from config.settings import settings
from data.fixtures import RESTAURANT_A
from data.test_constants import *  # noqa: F401, F403
from locators import common_locators as L
from pages.consumption_summary_page import ConsumptionSummaryPage as Page


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


def _get_breadcrumb_links(page: Page) -> list[str]:
    """Return non-empty breadcrumb item texts."""
    items = page.page.locator(L.BREADCRUMB_ITEM_LINK).all_inner_texts()
    return [t.strip() for t in items if t.strip()]


def _parse_export_csv(download) -> dict:
    """Parse a Playwright Download object as a CSV export.

    CSV layout (from handleExport in consumptionsummary/index.jsx):
      row 0 = report title (filename without .csv extension)
      row 1 = empty
      row 2 = column headers
      row 3+ = data rows (string cells are double-quoted by the exporter)

    Returns:
        {
            "title":   str,         # row 0, first cell
            "headers": list[str],   # row 2
            "rows":    list[dict],  # row 3+, keyed by header name
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
