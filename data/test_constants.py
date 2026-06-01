"""Shared test data constants.

Test-specific values that don't fit in environment config — they describe
WHAT the test exercises, not WHERE it runs.

Tests import the constants they need:
    from data.test_constants import DEFAULT_MEAL, CATEGORY_VEGETABLES
"""
from datetime import date, timedelta

_today = date.today()

# Meal options (- All Meals - dropdown values)
MEAL_BREAKFAST = "Breakfast"
MEAL_LUNCH = "Lunch"
MEAL_DINNER = "Dinner"
MEAL_ALL= "- All Meals -"
MEAL_DAY= "All Day"

# Category options (- All Categories - dropdown values)
CATEGORY_VEGETABLES = "Vegetables"
CATEGORY_FRUITS = "Fruits"
CATEGORY_MEAT = "Meat"
CATEGORY_KITCHEN_WASTE = "Kitchen Waste"
CATEGORY_POST_CONSUMER = "Post-Consumer"
CATEGORY_ALL = "- All Categories -"


NO_DATA_AVAILABLE = (
    "No data was available for the selected filters"
    "Headers loaded correctly. Marking as pass since there's nothing to verify."
)

DEFAULT_DATE_START = (_today - timedelta(days=7)).strftime("%m/%d/%Y")
DEFAULT_DATE_END = _today.strftime("%m/%d/%Y")
