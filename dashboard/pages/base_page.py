"""Base class for all page objects."""

from playwright.sync_api import Page

from dashboard.locators import common_locators as L
from shared.utils.antd_helpers import select_dropdown_option


class BasePage:
    """Universal helpers usable by every page in the app."""

    def __init__(self, page: Page):
        self.page = page

    def select_current_view(self, value: str):
        """Top-right 'Current View' dropdown.

        Works on every dashboard page. Use 'Overview Across All Restaurants'
        for the global view, or a specific restaurant name otherwise.
        """
        label = self.page.locator(L.CURRENT_VIEW_LABEL)
        label.wait_for(state="visible")
        dropdown = label.locator("..").locator(".ant-select").first
        dropdown.click()
        select_dropdown_option(self.page, value)
        self.page.wait_for_load_state("networkidle")

    def navigate_via_sidebar(self, group: str, item: str):
        """Click a leaf item under an expandable sidebar group.

        Works for any group/item combination:
          - ('Data Overview', 'Dashboard')                  global view
          - ('Executive Insights', 'Consumption Summary')   restaurant view
          - ('Kitchen Intelligence', 'Scan Log')
          - ('Menu Management', 'Menu Items')
          - etc.
        """
        item_locator = self.page.locator(L.SIDEBAR_MENU_ITEM).filter(has_text=item)
        # Only expand the group if the leaf isn't already visible
        if not item_locator.is_visible():
            self.page.locator(L.SIDEBAR_SUBMENU_TITLE).filter(has_text=group).first.click()
        item_locator.click()

    def get_rows(self) -> list[dict]:
        """Read the current Ant Table as a list of {column_header: cell_text}."""
        headers = self.page.locator("table thead th").all_inner_texts()
        rows = []
        for row in self.page.locator(L.TABLE_BODY_ROW).all():
            cells = row.locator("td").all_inner_texts()
            rows.append(dict(zip(headers, cells)))
        return rows