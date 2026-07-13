"""Shared helpers and constants for Overproduction Summary tests."""

from shared.config.settings import settings
from shared.data.test_constants import *  # noqa: F401, F403
from dashboard.locators import common_locators as L
from dashboard.pages.overproduction_summary_page import OverproductionSummaryPage as Page


DESTINATION_ALL = "All Destinations"


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


def _assert_headers_have_unit(page: Page, unit: str):
    """Verify Total Overproduction header shows the given unit."""
    headers = page.get_headers()
    expected = f"{Page.COL_TOTAL_OVERPRODUCTION_BASE} ({unit})"
    assert any(expected in h for h in headers), (
        f"Expected header containing '{expected}'. Got: {headers}"
    )
