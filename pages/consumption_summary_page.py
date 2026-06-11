"""Consumption Summary page — just the deltas from ExecutiveInsightsPage."""

from pages.executive_insights_page import ExecutiveInsightsPage


class ConsumptionSummaryPage(ExecutiveInsightsPage):
    SIDEBAR_ITEM = "Consumption Summary"

    # Unit options shown in column headers (toggled via cost/weight button)
    WEIGHT_UNIT = "lb"
    COST_UNIT = "$"

    # Base column names — used for dynamic header construction
    COL_PRODUCTION_BASE = "Production"
    COL_CONSUMPTION_BASE = "Consumption"
    COL_OVERPRODUCTION_BASE = "Overproduction"

    # Full column names in default (weight) view — used to read row data
    COL_PRODUCTION = "Production (lb)"
    COL_CONSUMPTION = "Consumption (lb)"
    COL_OVERPRODUCTION = "Overproduction (lb)"

    # Full column names in cost ($) view
    COL_PRODUCTION_COST = "Production ($)"
    COL_CONSUMPTION_COST = "Consumption ($)"
    COL_OVERPRODUCTION_COST = "Overproduction ($)"