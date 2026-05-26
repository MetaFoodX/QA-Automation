"""Consumption Summary page — just the deltas from ExecutiveInsightsPage."""

from pages.executive_insights_page import ExecutiveInsightsPage


class ConsumptionSummaryPage(ExecutiveInsightsPage):
    SIDEBAR_ITEM = "Consumption Summary"

    # Columns specific to Consumption Summary
    COL_PRODUCTION = "Production (lb)"
    COL_CONSUMPTION = "Consumption (lb)"
    COL_OVERPRODUCTION = "Overproduction (lb)"