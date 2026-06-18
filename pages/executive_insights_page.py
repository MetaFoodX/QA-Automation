"""Base class for Executive Insights pages."""

import re
import time

from playwright.sync_api import expect

from config.settings import settings
from locators import common_locators as L
from pages.base_page import BasePage
from utils.antd_helpers import select_dropdown_option


class ExecutiveInsightsPage(BasePage):
    SIDEBAR_GROUP = "Executive Insights"
    SIDEBAR_ITEM: str = None

    COL_MENU_ITEM = "Menu Item"
    COL_VENUE = "Venue"
    COL_DATE = "Date"
    COL_DAY = "Day"
    COL_DAYS_SERVED = "Days Served"
    COL_NUMBER_OF_PAN = "Number of Pan"

    def __init__(self, page):
        super().__init__(page)
        self._summary_row_count = None

    def open_via_nav(self, restaurant: str = "Test Kitchen"):
        """Pick restaurant → navigate via sidebar → cache summary row count."""
        self.select_current_view(restaurant)
        self.navigate_via_sidebar(self.SIDEBAR_GROUP, self.SIDEBAR_ITEM)
        self.page.wait_for_selector(L.TABLE_LOADED_MARKER)
        self.page.wait_for_load_state("networkidle")
        self._wait_for_table_to_settle()

        self._summary_row_count = self.page.locator(L.TABLE_BODY_ROW).count()

    def set_venue(self, venue_name: str):
        self._select_filter_dropdown(position=0, option=venue_name)
    
    def set_meal(self, meal_name: str):
        """Set the meal filter."""
        self._select_filter_dropdown(position=1, option=meal_name)


    def set_category(self, category_name: str):
        """Set the category filter."""
        self._select_filter_dropdown(position=2, option=category_name)


    def _select_filter_dropdown(self, position: int, option: str):
        """0=Venue, 1=Meals, 2=Categories — verified against Header.jsx render order
        for non-catering, non-ingredient, non-ratings pages."""
        select = self.page.locator("form.ant-form").locator(".ant-select").nth(position)
        select.click()
        select_dropdown_option(self.page, option)
        self._wait_for_table_to_settle()



    def click_menu_item_in_row(self, row_index: int):
        """Drill in. Wait until the specific row index exists before reading."""
        self.page.locator("th", has_text=self.COL_DAYS_SERVED).wait_for(state="visible")

        # Wait for the requested row to be present
        self.page.locator(L.TABLE_BODY_ROW).nth(row_index).wait_for(state="visible")

        rows = self.page.locator(L.TABLE_BODY_ROW).all()
        if row_index >= len(rows):
            raise IndexError(f"Row {row_index} out of range ({len(rows)} rows)")

        target_item = rows[row_index].locator("a").first.inner_text().strip()
        rows[row_index].locator("a").first.click()

        self.page.locator("th", has_text=self.COL_DATE).wait_for(state="visible")
        self.page.wait_for_load_state("networkidle")
        self.page.locator(L.TABLE_BODY_ROW, has_text=target_item).first.wait_for(state="visible")
        self._wait_for_rows_to_match_item(target_item)

    def navigate_back_to_summary(self):
        """Two-step navigate back. Wait for the table to fully settle after each click,
        same way we wait when first opening the page.
        """
        self.page.locator(L.DAY_TOGGLE_BUTTON).click()
        self._wait_for_table_to_settle()

        self.page.locator(L.BREADCRUMB_PAGE_LINK).click()
        self._wait_for_table_to_settle()


    def _wait_for_table_to_settle(self, interval_ms=200, stable_checks=5):
        """Poll until table is in a stable state — either has rows, or shows 'No data'.

        Distinguishes between:
        - Loading state ("Loading data" text shown) → keep waiting
        - Stable with data (rows present, count not changing) → return
        - Stable empty (no rows, but "No data" text shown) → return
        """
        deadline = time.time() + (settings.timeouts.default / 1000)
        previous_count = -1
        stable = 0
        while time.time() < deadline:
            current = self.page.locator(L.TABLE_BODY_ROW).count()
            no_data_visible = self.page.locator("text=No data").count() > 0

            # "Settled" means either has rows, or empty with confirmed "No data" message
            is_settled = current > 0 or no_data_visible

            if current == previous_count and is_settled:
                stable += 1
                if stable >= stable_checks:
                    return
            else:
                previous_count = current
                stable = 0

            self.page.wait_for_timeout(interval_ms)

        raise TimeoutError(
            f"Table didn't settle within {settings.timeouts.default}ms"
    )

    def _wait_for_rows_to_match_item(self, expected_item: str):
        """Poll until every visible row's Menu Item cell contains expected_item."""
        deadline = time.time() + (settings.timeouts.default / 1000)
        while time.time() < deadline:
            rows = self.get_rows()
            if rows and all(
                expected_item in row.get(self.COL_MENU_ITEM, "")
                for row in rows
            ):
                return
            self.page.wait_for_timeout(settings.timeouts.short)

        raise TimeoutError(
            f"Detail rows didn't stabilize to show only '{expected_item}' within "
            f"{settings.timeouts.default}ms"
        )
    def set_date_range(self, start_date: str, end_date: str):
        """Set the date range filter.

        Args:
            start_date: Start date in MM/DD/YYYY format (e.g. "05/15/2026")
            end_date: End date in MM/DD/YYYY format (e.g. "05/22/2026")
        """
        # Open the picker
        self.page.locator(L.DATE_RANGE_PICKER).click()

        # The picker has two input fields (start, end). Target by position
        # because they don't have unique placeholders when values are already set.
        inputs = self.page.locator(L.DATE_RANGE_PICKER).locator("input")

        # Fill start date
        inputs.first.fill(start_date)
        inputs.first.press("Enter")

        # Fill end date
        inputs.nth(1).fill(end_date)
        inputs.nth(1).press("Enter")

        # Filter change triggers a refetch — wait for the table to settle
        self._wait_for_table_to_settle()
    
    def is_venue_selected(self, venue_name: str) -> bool:
        """Check if the given venue name is currently selected in the venue dropdown."""
        return self.is_filter_selected(venue_name)

    def is_filter_selected(self, value: str) -> bool:
        """Check if any filter dropdown in the header form currently shows the given value."""
        return (
            self.page.locator(f"{L.FILTER_SELECTION_ITEM}:has-text('{value}')")
            .is_visible()
        )

    def click_search_toggle(self):
        """Toggle the menu-item search select visible/hidden."""
        opening = not self.page.locator(L.SEARCH_MINIMIZE_BUTTON).is_visible()
        self.page.locator(
            f"{L.SEARCH_BUTTON}, {L.SEARCH_MINIMIZE_BUTTON}"
        ).first.click()
        expected_state = "visible" if opening else "hidden"
        self.page.locator(L.MENU_ITEM_SEARCH_SELECT).wait_for(state=expected_state)

    def is_search_active(self) -> bool:
        """True if the menu-item search select is currently shown (arrow icon visible)."""
        return self.page.locator(L.SEARCH_MINIMIZE_BUTTON).is_visible()

    def select_menu_items_in_search(self, *item_names: str):
        """Open the Menu Items multi-select and pick items by display name."""
        self.page.locator(L.MENU_ITEM_SEARCH_SELECT).click()
        for name in item_names:
            select_dropdown_option(self.page, name, exact=True)
        self.page.keyboard.press("Escape")
        self._wait_for_table_to_settle()

    def clear_menu_item_search(self):
        """Clear all selected items in the Menu Items search multi-select."""
        select = self.page.locator(L.MENU_ITEM_SEARCH_SELECT)
        select.hover()
        select.locator(".ant-select-clear").click()
        self._wait_for_table_to_settle()

    def click_column_sort(self, column_name: str):
        """Click a column header to cycle sort state (none → asc → desc → none)."""
        self.page.get_by_role("columnheader", name=re.compile(rf"^{re.escape(column_name)}")).click()
        self._wait_for_table_to_settle()

    def toggle_day_view(self):
        """Click the day-range toggle button — switches between by-date and combined view."""
        self.page.locator(L.FILTER_ACTION_BUTTONS).nth(0).click()
        self._wait_for_table_to_settle()

    def click_export_button(self):
        """Click the export (download) button — 3rd action button after the date picker."""
        self.page.locator(L.FILTER_ACTION_BUTTONS).nth(2).click()

    def download_export(self):
        """Click export and return the resulting Playwright Download object."""
        with self.page.expect_download() as dl_info:
            self.click_export_button()
        return dl_info.value

    def is_export_button_enabled(self) -> bool:
        """Return True if the export button is not disabled."""
        return not self.page.locator(L.FILTER_ACTION_BUTTONS).nth(2).is_disabled()

    def toggle_cost_view(self):
        """Click the cost/weight toggle button (next to day-toggle).

        Switches the table between $ (cost) display and lb (weight) display.
        Client-side only — no API call, just a quick re-render.
        """
        self.page.locator(L.FILTER_ACTION_BUTTONS).nth(1).click()
        # Brief wait for React to re-render headers + cells with new unit
        self.page.wait_for_timeout(settings.timeouts.short)


    def get_headers(self) -> list[str]:
        """Return the current table column header texts."""
        return self.page.locator("table thead th").all_inner_texts()

    def get_all_rows(self) -> list[dict]:
        """Read rows across all pagination pages, then reset pagination to page 1.

        Resetting at the end prevents the page-2-or-later state from leaking
        into subsequent operations (e.g., the summary view re-rendering still
        on page 2 after navigate_back).
        """
        all_rows = list(self.get_rows())

        while self._click_next_page():
            all_rows.extend(self.get_rows())

        self._reset_to_first_page()
        return all_rows


    def _reset_to_first_page(self):
        """Click the pagination 'page 1' button if not already there."""
        active = self.page.locator(".ant-pagination-item-active").first

        if not active.is_visible():
            return  # no pagination (single page, fewer rows than pageSize)

        current = int(active.inner_text().strip())
        if current == 1:
            return  # already on page 1

        self.page.locator(".ant-pagination-item-1").click()
        self.page.locator(
            ".ant-pagination-item-1.ant-pagination-item-active"
        ).wait_for(state="visible")


    def _click_next_page(self) -> bool:
        """Click the pagination 'Next' button. Returns True if clicked, False if disabled."""
        next_button = self.page.locator("li.ant-pagination-next")

        if not next_button.is_visible():
            return False

        classes = next_button.get_attribute("class") or ""
        if "ant-pagination-disabled" in classes:
            return False

        # Capture current active page so we can wait for it to advance
        current_active = self.page.locator(".ant-pagination-item-active").first
        current_page = int(current_active.inner_text().strip())

        next_button.click()

        # Wait for the next page indicator to become active.
        # Works for client-side (instant DOM swap) and server-side (after API).
        self.page.locator(
            f".ant-pagination-item-{current_page + 1}.ant-pagination-item-active"
        ).wait_for(state="visible")

        return True