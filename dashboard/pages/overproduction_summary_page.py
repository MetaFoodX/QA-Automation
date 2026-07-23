"""Overproduction Summary page object."""

from dashboard.pages.executive_insights_page import ExecutiveInsightsPage
from dashboard.locators import common_locators as L
from shared.config.settings import settings


class OverproductionSummaryPage(ExecutiveInsightsPage):
    SIDEBAR_ITEM = "Overproduction Summary"

    WEIGHT_UNIT = "lb"
    COST_UNIT = "$"

    # Base column names — used for unit-agnostic header assertions
    COL_TOTAL_OVERPRODUCTION_BASE = "Total Overproduction"
    COL_REUSE_BASE = "Reuse"
    COL_DONATION_BASE = "Donation"
    COL_COMPOSTABLE_BASE = "Compostable"

    # Full column names in default (weight) view
    COL_TOTAL_OVERPRODUCTION = "Total Overproduction (lb)"
    COL_REUSE = "Reuse (lb)"
    COL_DONATION = "Donation (lb)"
    COL_COMPOSTABLE = "Compostable (lb)"

    # Full column names in cost ($) view
    COL_TOTAL_OVERPRODUCTION_COST = "Total Overproduction ($)"
    COL_REUSE_COST = "Reuse ($)"
    COL_DONATION_COST = "Donation ($)"
    COL_COMPOSTABLE_COST = "Compostable ($)"

    # Breakdown view column names (weight) — Served / Not Served sub-columns
    COL_SERVED_TOTAL_OP    = "Served Total Overproduction (lb)"
    COL_NOT_SERVED_TOTAL_OP = "Not Served Total Overproduction (lb)"
    COL_SERVED_REUSE       = "Served Reuse (lb)"
    COL_NOT_SERVED_REUSE   = "Not Served Reuse (lb)"
    COL_SERVED_DONATION    = "Served Donation (lb)"
    COL_NOT_SERVED_DONATION = "Not Served Donation (lb)"
    COL_SERVED_COMPOSTABLE  = "Served Compostable (lb)"
    COL_NOT_SERVED_COMPOSTABLE = "Not Served Compostable (lb)"

    # Day view additional columns
    COL_DATE = "Date"
    COL_DAY  = "Day"

    # Button indices — overproduction has [0]=day, [1]=breakdown, [2]=cost, [3]=export
    # Consumption has [0]=day, [1]=cost, [2]=export (no breakdown button)
    _BTN_DAY       = 0
    _BTN_BREAKDOWN = 1
    _BTN_COST      = 2
    _BTN_EXPORT    = 3

    def set_destination(self, destination: str):
        """Set the destination filter (All Destinations, Reuse, Donation, Compostable)."""
        self._select_filter_dropdown(position=3, option=destination)

    def toggle_breakdown_view(self):
        """Toggle breakdown view to show Served / Not Served sub-columns."""
        self.page.locator(L.FILTER_ACTION_BUTTONS).nth(self._BTN_BREAKDOWN).click()
        self._wait_for_table_to_settle()

    def toggle_cost_view(self):
        """Toggle between weight (lb) and cost ($) display."""
        self.page.locator(L.FILTER_ACTION_BUTTONS).nth(self._BTN_COST).click()
        self.page.wait_for_timeout(settings.timeouts.short)

    def click_export_button(self):
        """Click the CSV export button."""
        self.page.locator(L.FILTER_ACTION_BUTTONS).nth(self._BTN_EXPORT).click()

    def download_export(self):
        """Click export and return the Playwright Download object."""
        with self.page.expect_download() as dl_info:
            self.click_export_button()
        return dl_info.value

    def is_export_button_enabled(self) -> bool:
        return not self.page.locator(L.FILTER_ACTION_BUTTONS).nth(self._BTN_EXPORT).is_disabled()

    def get_breakdown_rows(self) -> list[dict]:
        """Read breakdown view rows by combining parent + sub headers from the DOM."""
        header_rows = self.page.locator("table thead tr").all()
        if len(header_rows) < 2:
            return self.get_rows()

        parent_ths = header_rows[0].locator("th").all()
        sub_ths = header_rows[1].locator("th").all()

        leaf_headers = []
        sub_idx = 0
        for th in parent_ths:
            colspan = int(th.get_attribute("colspan") or "1")
            rowspan = int(th.get_attribute("rowspan") or "1")
            name = th.inner_text().strip()
            if rowspan > 1:
                leaf_headers.append(name)
            else:
                for _ in range(colspan):
                    sub_name = sub_ths[sub_idx].inner_text().strip()
                    leaf_headers.append(f"{sub_name} {name}")
                    sub_idx += 1

        rows = []
        for row in self.page.locator("table tbody tr.ant-table-row").all():
            cells = row.locator("td").all_inner_texts()
            rows.append(dict(zip(leaf_headers, cells)))
        return rows
