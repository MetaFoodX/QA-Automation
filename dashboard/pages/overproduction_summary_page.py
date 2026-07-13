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
