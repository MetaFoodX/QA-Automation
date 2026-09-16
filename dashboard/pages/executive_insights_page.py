"""Base class for Executive Insights pages."""

import re
import time

from playwright.sync_api import expect

from shared.config.settings import settings
from dashboard.locators import common_locators as L
from dashboard.pages.base_page import BasePage
from shared.utils.antd_helpers import select_dropdown_option


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
        # The by-day column headers (and their 'View' buttons) render before the
        # real per-day rows replace the stale summary rows underneath them —
        # confirmed live: row count/pagination visibly changes shortly after
        # _wait_for_rows_to_match_item already passes. Wait for that to settle
        # too before returning, so callers never act on a still-transitioning table.
        self._wait_for_table_to_settle()

    def get_breadcrumb_texts(self) -> list[str]:
        """Non-empty breadcrumb crumb texts, in DOM order (hidden home crumb excluded)."""
        items = self.page.locator(L.BREADCRUMB_ITEM_LINK).all_inner_texts()
        return [t.strip() for t in items if t.strip()]

    def is_breadcrumb_parent_clickable(self) -> bool:
        """True if the page-name crumb (e.g. 'Consumption Summary') is a real link —
        only the case while drilled into a menu item."""
        return self.page.locator(L.BREADCRUMB_PAGE_LINK).locator("a").count() > 0

    def is_breadcrumb_venue_clickable(self) -> bool:
        """True if the venue crumb contains a link. Expected to always be False —
        breadCrumbParent2 is rendered as plain text, never a Link."""
        return self.page.locator(L.BREADCRUMB_VENUE_ITEM).locator("a").count() > 0

    def is_breadcrumb_item_clickable(self) -> bool:
        """True if the menu-item-name crumb contains a link. Expected to always be
        False — breadCrumbActive is rendered as plain text, never a Link."""
        return self.page.locator(L.BREADCRUMB_ITEM_CRUMB).locator("a").count() > 0

    def click_breadcrumb_parent(self):
        """Click the page-name breadcrumb crumb to return to the parent view.

        Unlike navigate_back_to_summary(), this does NOT toggle day view off first —
        closeMenuItemDrillDown() in the app restores whatever day-view state
        (parentWasDailyView) was active before the drill-down on its own.
        """
        self.page.locator(L.BREADCRUMB_RESET_LINK).click()
        self._wait_for_table_to_settle()

    def has_scan_images_column(self) -> bool:
        """True if the 'Scan Images' column header is present — only rendered
        inside a standard menu-item drill-down while in the by-day view."""
        return any("Scan Images" in h for h in self.get_headers())

    def click_view_scans_in_row(self, row_index: int):
        """Click the 'View' button in the given data-by-dates row to expand its
        scan gallery. Waits for the gallery to mount before returning."""
        rows = self.page.locator(L.TABLE_BODY_ROW).all()
        if row_index >= len(rows):
            raise IndexError(f"Row {row_index} out of range ({len(rows)} rows)")
        rows[row_index].locator(L.SCAN_GALLERY_VIEW_BUTTON).click()
        self.page.locator(L.SCAN_GALLERY).first.wait_for(state="visible")
        self._wait_for_gallery_to_settle()

    def click_view_scans_button(self, row_locator):
        """Click the 'View' button inside an already-located row (for rows read
        via get_rows()/get_all_rows() rather than by index)."""
        row_locator.locator(L.SCAN_GALLERY_VIEW_BUTTON).click()

    def is_scan_gallery_expanded(self) -> bool:
        """True if a scan gallery is currently expanded. At most one is ever
        mounted — expandedRowKeys holds a single key."""
        return self.page.locator(L.SCAN_GALLERY).count() > 0

    def get_scan_gallery_toggle_label(self) -> str:
        """Currently-selected Service/Leftover label — Consumption mode only."""
        return self.page.locator(L.SCAN_GALLERY_TOGGLE).inner_text().strip()

    def select_scan_gallery_option(self, label: str):
        """Switch the expanded gallery's Service/Leftover toggle (Consumption
        mode only). Waits out the resulting scan refetch before returning."""
        self.page.locator(L.SCAN_GALLERY_TOGGLE).click()
        select_dropdown_option(self.page, label, exact=True)
        self._wait_for_gallery_to_settle()

    def _wait_for_gallery_to_settle(self):
        """Poll until the expanded gallery shows scan cards or its own 'No
        data' message — i.e. the async scan fetch triggered by expanding or
        switching Service/Leftover has actually finished. A fixed sleep here
        previously masked this: short seed days finished within the sleep and
        passed by luck, while a slower fetch left the gallery mid-load with
        neither cards nor the empty message rendered yet.

        Once content appears, also wait out AntD's row-expand height
        animation before returning — clicking something inside the row (e.g.
        the Service/Leftover select) while it's still animating can silently
        fail to open. Confirmed live: content can render before that
        animation finishes, so "content appeared" alone isn't "settled".
        """
        deadline = time.time() + (settings.timeouts.default / 1000)
        while time.time() < deadline:
            if self.page.locator(L.SCAN_GALLERY_CARD).count() > 0 or self.is_scan_gallery_empty():
                self.page.wait_for_timeout(settings.timeouts.medium)
                return
            self.page.wait_for_timeout(settings.timeouts.short)
        raise TimeoutError(
            f"Scan gallery didn't settle (no cards, no 'No data' message) within {settings.timeouts.default}ms"
        )

    def has_scan_gallery_toggle(self) -> bool:
        """True only in Consumption mode — every other mode shows a static title instead."""
        return self.page.locator(L.SCAN_GALLERY_TOGGLE).count() > 0

    def get_scan_gallery_static_title(self) -> str:
        """Static gallery title text — every mode other than Consumption."""
        return self.page.locator(L.SCAN_GALLERY_STATIC_TITLE).inner_text().strip()

    def is_scan_gallery_empty(self) -> bool:
        """True if the expanded gallery shows its own 'No data' message."""
        return self.page.locator(L.SCAN_GALLERY_EMPTY).count() > 0

    def get_scan_cards(self) -> list[dict]:
        """Read each visible scan card's name/weight/time/temperature text in
        the currently expanded gallery."""
        cards = self.page.locator(L.SCAN_GALLERY_CARD).all()
        result = []
        for card in cards:
            def _text(selector):
                loc = card.locator(selector)
                return loc.first.inner_text().strip() if loc.count() else ""

            result.append({
                "name": _text(L.SCAN_CARD_NAME),
                "weight": _text(L.SCAN_CARD_WEIGHT),
                "time": _text(L.SCAN_CARD_TIME),
                "temperature": _text(L.SCAN_CARD_TEMPERATURE),
            })
        return result

    def open_scan_preview(self, card_index: int = 0):
        """Click the image of the given scan card (by position in the
        currently expanded gallery) to open the enlarged preview modal."""
        cards = self.page.locator(L.SCAN_GALLERY_CARD).all()
        if card_index >= len(cards):
            raise IndexError(f"Card {card_index} out of range ({len(cards)} cards)")
        cards[card_index].locator("img").first.click()
        self.page.locator(L.SCAN_PREVIEW_MODAL).first.wait_for(state="visible")

    def close_scan_preview(self):
        """Close the open scan preview modal."""
        self.page.locator(L.SCAN_PREVIEW_CLOSE).click()
        self.page.locator(L.SCAN_PREVIEW_MODAL).wait_for(state="hidden")

    def is_scan_preview_open(self) -> bool:
        modal = self.page.locator(L.SCAN_PREVIEW_MODAL)
        return modal.count() > 0 and modal.first.is_visible()

    def get_scan_preview_fields(self) -> dict[str, str]:
        """Read label -> first value text for every field in the open preview
        modal. A field with multiple value divs (e.g. Pan Size & Depth) only
        contributes its first value here — see get_scan_preview_pan_size_and_depth."""
        result = {}
        for label_el in self.page.locator(L.SCAN_PREVIEW_FIELD_LABEL).all():
            label_text = label_el.inner_text().strip()
            values = label_el.locator("xpath=following-sibling::div[contains(@class,'preview-label')]")
            result[label_text] = values.first.inner_text().strip() if values.count() else ""
        return result

    def get_scan_preview_pan_size_and_depth(self) -> tuple[str, str]:
        """Both value divs under the 'Pan Size & Depth' label: (size, depth)."""
        label = self.page.locator(L.SCAN_PREVIEW_FIELD_LABEL).filter(has_text="Pan Size & Depth")
        texts = label.locator("xpath=following-sibling::div[contains(@class,'preview-label')]").all_inner_texts()
        return (
            texts[0].strip() if len(texts) > 0 else "",
            texts[1].strip() if len(texts) > 1 else "",
        )

    def click_scan_preview_prev(self):
        self.page.locator(L.SCAN_PREVIEW_PREV_BUTTON).click()

    def click_scan_preview_next(self):
        self.page.locator(L.SCAN_PREVIEW_NEXT_BUTTON).click()

    def is_scan_preview_prev_visible(self) -> bool:
        return self.page.locator(L.SCAN_PREVIEW_PREV_BUTTON).count() > 0

    def is_scan_preview_next_visible(self) -> bool:
        return self.page.locator(L.SCAN_PREVIEW_NEXT_BUTTON).count() > 0

    def navigate_back_to_summary(self):
        """Two-step navigate back. Wait for the table to fully settle after each click,
        same way we wait when first opening the page.
        """
        self.page.locator(L.DAY_TOGGLE_BUTTON).click()
        self._wait_for_table_to_settle()

        self.page.locator(L.BREADCRUMB_RESET_LINK).click()
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
        select = self.page.locator(L.MENU_ITEM_SEARCH_SELECT)
        for name in item_names:
            select.click()
            search_input = select.locator("input")
            search_input.fill("")
            search_input.type(name)
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