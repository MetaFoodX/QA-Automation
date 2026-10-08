"""Menu Item Drill Down — Section 1: Navigation & Breadcrumb.

Same drill-down entry point as Consumption Summary (NAV-005 in the PRD test
matrix): clicking a menu item opens an in-place daily breakdown (no page
navigation), and the breadcrumb grows to
'Overproduction Summary / [Venue] / [Item]' where only the first crumb is a
real link.
"""
import allure
import pytest

from shared.data.test_constants import *  # noqa: F401, F403
from dashboard.locators import common_locators as L
from dashboard.pages.overproduction_summary_page import OverproductionSummaryPage as Page
from dashboard.tests.executive_insights.overproduction_summary._helpers import (
    CURRENT_VENUE_NAME, _get_breadcrumb_links,
)


def _apply_filters(page: Page, venue: str = CURRENT_VENUE_NAME, meal: str = MEAL_ALL):
    """Venue/meal/date only — deliberately skips the Category filter.

    Selecting '- All Categories -' has a known bug (table fails to reload after
    returning from a drill-down); leaving the category filter at whatever it
    defaults to on page load avoids it. Tracked separately, out of scope here.
    """
    page.set_venue(venue)
    page.set_meal(meal)
    page.set_date_range(DEFAULT_DATE_START, DEFAULT_DATE_END)


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Navigation")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Clicking a menu item row drills down in place, without a page navigation")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Clicking a menu item row opens the daily drill-down in place (SPA state change), not a full page navigation",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply default filters\n"
        "3. Record the current page URL\n"
        "4. Click the menu item link in row 0\n"
        "5. Assert the URL is unchanged after the click\n"
        "6. Assert Date and Day columns are now present (drill-down confirmed)"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_row_click_drills_down_without_page_navigation(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    url_before = page.page.url
    page.click_menu_item_in_row(0)
    url_after = page.page.url

    assert url_after == url_before, (
        f"Drill-down should not navigate. Before: {url_before}, after: {url_after}"
    )
    headers = page.get_headers()
    assert Page.COL_DATE in headers, f"Expected Date column after drill-down, got: {headers}"
    assert Page.COL_DAY in headers, f"Expected Day column after drill-down, got: {headers}"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Navigation")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Breadcrumb reads 'Overproduction Summary / [Venue] / [Item]' after drill-down")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="After drilling into a menu item, the breadcrumb shows exactly page name, venue, then item name",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply default filters\n"
        "3. Record the menu item name from row 0\n"
        "4. Click the menu item to drill down\n"
        "5. Read breadcrumb crumb texts\n"
        "6. Assert crumbs are exactly ['Overproduction Summary', <venue>, <item>] in that order"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_breadcrumb_format_shows_summary_venue_item(logged_in_page, seeded_basic_scans):
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
    assert links == [Page.SIDEBAR_ITEM, CURRENT_VENUE_NAME, item_name], (
        f"Expected breadcrumb ['{Page.SIDEBAR_ITEM}', '{CURRENT_VENUE_NAME}', '{item_name}'], got: {links}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Navigation")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Breadcrumb parent is clickable and returns to summary with filters preserved")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="The 'Overproduction Summary' breadcrumb crumb is a real link while drilled down; clicking it returns to the summary with the venue filter still applied",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply default filters\n"
        "3. Click a menu item to drill down\n"
        "4. Assert the 'Overproduction Summary' crumb is a real link\n"
        "5. Click it\n"
        "6. Assert the table is back at summary level (no Date/Day columns)\n"
        "7. Assert the venue filter still shows the previously selected venue"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_breadcrumb_parent_clickable_returns_with_filters_preserved(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    assert page.is_breadcrumb_parent_clickable(), (
        "'Overproduction Summary' breadcrumb crumb should be a real link while drilled down"
    )

    page.click_breadcrumb_parent()

    headers = page.get_headers()
    assert Page.COL_DATE not in headers, f"Expected summary-level columns after returning, got: {headers}"
    assert page.is_venue_selected(CURRENT_VENUE_NAME), (
        f"Venue filter changed after returning via breadcrumb. Expected '{CURRENT_VENUE_NAME}' still selected."
    )


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Navigation")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Breadcrumb venue and item crumbs are plain text, not clickable")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="The venue and menu-item-name breadcrumb crumbs are non-clickable labels while drilled down",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply default filters\n"
        "3. Click a menu item to drill down\n"
        "4. Assert the venue crumb contains no link\n"
        "5. Assert the item-name crumb contains no link"
    ),
)
@pytest.mark.regression
def test_breadcrumb_venue_and_item_are_not_clickable(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)

    assert not page.is_breadcrumb_venue_clickable(), "Venue breadcrumb crumb should be plain text, not a link"
    assert not page.is_breadcrumb_item_clickable(), "Menu item breadcrumb crumb should be plain text, not a link"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Navigation")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Returning via breadcrumb restores the pre-drill-down day-view state")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Drill-down forces the daily (by-date) view; returning via the breadcrumb auto-restores whatever day-view state (combined vs. by-date) was active beforehand",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply default filters (combined view, no day toggle)\n"
        "3. Assert Date/Day columns are absent (combined view)\n"
        "4. Click a menu item to drill down\n"
        "5. Assert Date/Day columns are now present (forced day view)\n"
        "6. Click the 'Overproduction Summary' breadcrumb crumb to return\n"
        "7. Assert Date/Day columns are absent again — day-view state restored automatically"
    ),
)
@pytest.mark.regression
def test_returning_via_breadcrumb_restores_day_view_state(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    headers_before = page.get_headers()
    assert Page.COL_DATE not in headers_before, f"Expected combined view before drill-down, got: {headers_before}"

    page.click_menu_item_in_row(0)
    headers_during = page.get_headers()
    assert Page.COL_DATE in headers_during, f"Expected day view during drill-down, got: {headers_during}"

    page.click_breadcrumb_parent()
    headers_after = page.get_headers()
    assert Page.COL_DATE not in headers_after, (
        f"Day-view state should auto-restore to combined view after returning, got: {headers_after}"
    )
    assert Page.COL_DAY not in headers_after, (
        f"Day-view state should auto-restore to combined view after returning, got: {headers_after}"
    )


# ---------------------------------------------------------------------------
# Section 2: Drill-Down View & Scan Expansion
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Scan Expansion")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Drilling into a menu item renders a per-day breakdown")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Drilling into a menu item shows one row per day the item was produced, each with a valid Date",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply filters (venue/meal/date only)\n"
        "3. Click a menu item to drill down\n"
        "4. Read all detail rows\n"
        "5. Assert at least one row is present and every row has a non-empty Date"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_daily_breakdown_renders_per_day_rows(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)

    rows = page.get_rows()
    assert rows, "Expected at least one daily row after drill-down"
    assert all(r.get(Page.COL_DATE, "").strip() for r in rows), (
        f"Every daily row should have a non-empty Date. Got: {rows}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Scan Expansion")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("'Scan Images' column and its View button are present in the daily drill-down")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Each data-by-dates row in a menu-item drill-down shows a 'Scan Images' column with a View button",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply filters, drill into a menu item\n"
        "3. Assert the 'Scan Images' column header is present\n"
        "4. Assert the first row has a visible 'View' button"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_scan_images_column_and_view_button_present(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)

    assert page.has_scan_images_column(), f"Expected 'Scan Images' column, got headers: {page.get_headers()}"
    view_button = page.page.locator(L.TABLE_BODY_ROW).first.locator(L.SCAN_GALLERY_VIEW_BUTTON)
    assert view_button.is_visible(), "Expected a visible 'View' button in the first daily row"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Scan Expansion")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("'Scan Images' column and View button are hidden in combined view")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="While drilled into a menu item, switching back to combined (non-day) view hides the Scan Images column — scans are only available in the by-day view",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply filters, drill into a menu item\n"
        "3. Assert the 'Scan Images' column is present in the by-day view\n"
        "4. Toggle day view off (combined view) while still drilled into the item\n"
        "5. Assert the 'Scan Images' column is no longer present"
    ),
)
@pytest.mark.regression
def test_view_button_hidden_in_combined_view(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    assert page.has_scan_images_column(), "Expected 'Scan Images' column in the by-day view"

    page.toggle_day_view()

    assert not page.has_scan_images_column(), (
        f"'Scan Images' column should be hidden in combined view, got headers: {page.get_headers()}"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Scan Expansion")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Clicking View expands the scan gallery for that date")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Clicking the View button in a daily row expands the scan gallery below it",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply filters, drill into a menu item\n"
        "3. Assert no gallery is expanded yet\n"
        "4. Click View in the first daily row\n"
        "5. Assert a scan gallery is now expanded"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_clicking_view_expands_scan_gallery(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    assert not page.is_scan_gallery_expanded(), "No gallery should be expanded before clicking View"

    page.click_view_scans_in_row(0)

    assert page.is_scan_gallery_expanded(), "Expected the scan gallery to expand after clicking View"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Scan Expansion")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Clicking View again collapses the scan gallery")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Re-clicking the View button on an already-expanded row collapses its scan gallery",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply filters, drill into a menu item\n"
        "3. Click View in the first daily row — gallery expands\n"
        "4. Click View again on the same row\n"
        "5. Assert the gallery is no longer expanded"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_clicking_view_again_collapses_scan_gallery(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    page.click_view_scans_in_row(0)
    assert page.is_scan_gallery_expanded(), "Gallery should be expanded before re-clicking View"

    page.page.locator(L.TABLE_BODY_ROW).first.locator(L.SCAN_GALLERY_VIEW_BUTTON).click()
    page.page.locator(L.SCAN_GALLERY).first.wait_for(state="hidden")

    assert not page.is_scan_gallery_expanded(), "Gallery should collapse after clicking View again"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Scan Expansion")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Expanding a new row's gallery collapses the previously expanded one")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Only one date's scan gallery can be expanded at a time — expanding a new row auto-collapses the previous one",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply filters, drill into a menu item with 2+ daily rows\n"
        "3. Click View on row 0 — gallery expands\n"
        "4. Click View on row 1\n"
        "5. Assert exactly one gallery is mounted (row 0's collapsed automatically)"
    ),
)
@pytest.mark.regression
def test_expanding_new_row_collapses_previous_gallery(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    if len(page.get_rows()) < 2:
        print(NO_DATA_AVAILABLE)
        return

    page.click_view_scans_in_row(0)
    assert page.is_scan_gallery_expanded()

    page.click_view_scans_in_row(1)

    assert page.page.locator(L.SCAN_GALLERY).count() == 1, (
        "Expanding a new row's gallery should collapse the previous one — only one should be mounted at a time"
    )


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Scan Expansion")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Scan gallery shows Leftover only, with no Service/Leftover toggle")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="On Overproduction Summary, the expanded scan gallery has no Service/Leftover toggle — it's a static 'Scan For Leftover' view",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply filters, drill into a menu item\n"
        "3. Click View to expand the gallery\n"
        "4. Assert no Service/Leftover toggle is present\n"
        "5. Assert the static title reads 'Scan For Leftover'"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_scan_gallery_shows_leftover_only_no_toggle(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    page.click_view_scans_in_row(0)

    assert not page.has_scan_gallery_toggle(), "Overproduction gallery should have no Service/Leftover toggle"
    title = page.get_scan_gallery_static_title()
    assert "Leftover" in title, f"Expected static 'Scan For Leftover' title, got: '{title}'"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Scan Expansion")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Each scan card shows a menu item name, weight, and captured time")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Every scan card in the expanded gallery shows a non-empty menu item name, weight, and captured time",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, apply filters, drill into a menu item\n"
        "3. Click View to expand the gallery\n"
        "4. Read every scan card's name/weight/time\n"
        "5. Assert none are empty"
    ),
)
@pytest.mark.regression
def test_scan_card_shows_weight_time_and_name(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    page.click_view_scans_in_row(0)

    if page.is_scan_gallery_empty():
        print(NO_DATA_AVAILABLE)
        return

    cards = page.get_scan_cards()
    assert cards, "Expected at least one scan card in the gallery"
    failures = [
        f"Card {i}: {card}"
        for i, card in enumerate(cards)
        if not card["weight"] or not card["time"] or not card["name"]
    ]
    assert not failures, "Every scan card should show name, weight, and time:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# DD-009 / DD-010 — Manual only. Both are visual/layout checks (image wrap
# arrangement, absence of an independent scroll container) that a DOM/CSS
# query can't meaningfully assert — a computed-style check would be too
# brittle to catch the real regression. Documented per the same convention
# as the manual/skip cases in test_weekly_service_line_report.py, rather
# than silently having no record of them at all.
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Scan Expansion")
@allure.severity(allure.severity_level.MINOR)
@allure.title("Scan images wrap vertically, matching Scan Log's layout")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Scan cards in the expanded gallery wrap vertically (multiple rows of thumbnails) the same way the Scan Log page's gallery does",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, drill into a menu item with enough scans to wrap\n"
        "3. Click View to expand the gallery\n"
        "4. Visually compare the wrap layout against the Scan Log page's gallery\n"
        "5. Confirm they match"
    ),
)
@pytest.mark.skip(
    reason="Visual layout check (thumbnail wrap arrangement) — not meaningfully assertable via DOM/CSS "
    "queries, requires visual comparison against the Scan Log page"
)
def test_scan_gallery_layout_matches_scan_log():
    pass


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Scan Expansion")
@allure.severity(allure.severity_level.MINOR)
@allure.title("Expanded scan gallery has no independent scroll container")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="The expanded scan gallery scrolls with the page as a whole — it does not have its own internal scrollbar/scroll container",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, drill into a menu item with enough scans to overflow a fixed-height box\n"
        "3. Click View to expand the gallery\n"
        "4. Scroll the page and visually confirm the gallery scrolls with it, with no separate inner scrollbar"
    ),
)
@pytest.mark.skip(
    reason="Visual/manual check — a computed-style (overflow) assertion would be too brittle to catch the "
    "real regression (e.g. a max-height/overflow added later); requires visual confirmation of scroll behavior"
)
def test_scan_gallery_has_no_independent_scroll():
    pass


# ---------------------------------------------------------------------------
# Section 4: Enlarged View & Scan Interactions
# ---------------------------------------------------------------------------

@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Enlarged View")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Clicking a scan image opens the enlarged preview")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Clicking a scan card's image in the gallery opens the enlarged preview modal",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, drill into a menu item, expand a gallery\n"
        "3. Assert no preview is open yet\n"
        "4. Click the first scan card's image\n"
        "5. Assert the enlarged preview modal is now open"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_clicking_scan_image_opens_preview(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    page.click_view_scans_in_row(0)
    if page.is_scan_gallery_empty():
        print(NO_DATA_AVAILABLE)
        return

    assert not page.is_scan_preview_open(), "No preview should be open yet"
    page.open_scan_preview(0)
    assert page.is_scan_preview_open(), "Expected the enlarged preview to open"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Enlarged View")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Enlarged preview shows all expected detail fields")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="The enlarged preview shows Scan Date, Scan Time, Temperature, Menu Item Weight, Menu Item Price, Pan Size & Depth, Pan Weight, and Overproduction Type — Overproduction Summary's gallery is leftover-only, so every scan qualifies",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, drill into a menu item, expand a gallery\n"
        "3. Open the first scan's preview\n"
        "4. Assert every expected field label is present"
    ),
)
@pytest.mark.regression
def test_preview_shows_all_detail_fields(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    page.click_view_scans_in_row(0)
    if page.is_scan_gallery_empty():
        print(NO_DATA_AVAILABLE)
        return

    page.open_scan_preview(0)
    fields = page.get_scan_preview_fields()

    expected_labels = [
        "Scan Date", "Scan Time", "Temperature", "Menu Item Weight",
        "Menu Item Price", "Pan Size & Depth", "Pan Weight", "Overproduction Type",
    ]
    missing = [label for label in expected_labels if label not in fields]
    assert not missing, f"Missing preview fields: {missing}. Got: {list(fields.keys())}"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Enlarged View")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Prev/Next navigation cycles between scans in the current gallery")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="smoke, regression",
    description="Next moves to a different scan and shows Prev; Prev returns to the original scan",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, drill into a menu item, expand a gallery with 2+ scans\n"
        "3. Open the first scan's preview — assert no Prev button, Next button present\n"
        "4. Click Next — assert the Menu Item Weight value changed and Prev is now visible\n"
        "5. Click Prev — assert the Menu Item Weight value returns to the original"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_preview_prev_next_navigation_cycles_scans(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    page.click_view_scans_in_row(0)
    if page.is_scan_gallery_empty():
        print(NO_DATA_AVAILABLE)
        return

    if len(page.get_scan_cards()) < 2:
        print(NO_DATA_AVAILABLE)
        return

    page.open_scan_preview(0)
    assert not page.is_scan_preview_prev_visible(), "First scan should have no Prev button"
    assert page.is_scan_preview_next_visible(), "Expected a Next button with more scans available"
    weight_1 = page.get_scan_preview_fields().get("Menu Item Weight")

    page.click_scan_preview_next()
    weight_2 = page.get_scan_preview_fields().get("Menu Item Weight")
    assert weight_2 != weight_1, "Next should move to a different scan (different weight)"
    assert page.is_scan_preview_prev_visible(), "Prev should be visible after moving forward"

    page.click_scan_preview_prev()
    weight_back = page.get_scan_preview_fields().get("Menu Item Weight")
    assert weight_back == weight_1, "Prev should return to the original scan"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Enlarged View")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Closing the preview preserves the drill-down's expanded state")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="Closing the enlarged preview returns to the drill-down with the same date's gallery still expanded",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, drill into a menu item, expand a gallery\n"
        "3. Open a scan's preview\n"
        "4. Close the preview\n"
        "5. Assert the preview is closed and the gallery is still expanded"
    ),
)
@pytest.mark.regression
def test_closing_preview_preserves_drill_down_state(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    page.click_view_scans_in_row(0)
    if page.is_scan_gallery_empty():
        print(NO_DATA_AVAILABLE)
        return

    page.open_scan_preview(0)
    page.close_scan_preview()

    assert not page.is_scan_preview_open(), "Preview should be closed"
    assert page.is_scan_gallery_expanded(), "Gallery should remain expanded after closing the preview"


@allure.epic("Overproduction Summary")
@allure.feature("Menu Item Drill Down — Enlarged View")
@allure.severity(allure.severity_level.MINOR)
@allure.title("Clicking the menu item name below a scan card does nothing")
@pytest.mark.testcase(
    component="overproduction_summary",
    type="regression",
    description="The menu item name label under a scan card has no click behavior — it neither opens the preview nor navigates",
    steps=(
        "1. Log in as kitchen_sapna\n"
        "2. Navigate to Overproduction Summary, drill into a menu item, expand a gallery\n"
        "3. Click the menu item name text under the first scan card\n"
        "4. Assert no preview opened, the gallery is still expanded, and the URL is unchanged"
    ),
)
@pytest.mark.regression
def test_clicking_scan_card_name_does_nothing(logged_in_page, seeded_basic_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    _apply_filters(page)

    if not page.get_rows():
        print(NO_DATA_AVAILABLE)
        return

    page.click_menu_item_in_row(0)
    page.click_view_scans_in_row(0)
    if page.is_scan_gallery_empty():
        print(NO_DATA_AVAILABLE)
        return

    url_before = page.page.url
    page.page.locator(L.SCAN_CARD_NAME).first.click()

    assert not page.is_scan_preview_open(), "Clicking the menu item name should not open the preview"
    assert page.is_scan_gallery_expanded(), "Clicking the menu item name should not affect the gallery"
    assert page.page.url == url_before, "Clicking the menu item name should not navigate"
