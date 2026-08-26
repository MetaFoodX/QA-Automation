"""Shared helpers for Weekly Service Line Report tests.

Started with just the AI Ranking tie-break helpers that don't belong
crowding the main test file. The rest of that file's helper code (seeding,
PDF extraction, settle-checks, etc.) is a planned follow-up migration here.
"""
from shared.data.fixtures import RESTAURANT_A


def _find_two_items_with_same_cost(menu_item_client, items):
    """First pair (by list order) of items in `items` that currently share
    the exact same live CostPerLb, plus that shared cost. Returns None if no
    two items in the pool happen to match right now. Predates
    MenuItemClient.update_cost_per_lb (see C-02) — D-04 checks for an
    existing coincidental match rather than forcing one via that API, to
    keep this test independent of that mutation path.
    """
    costs = {
        item.name: menu_item_client.get_cost_per_lb(item.name, restaurant_id=RESTAURANT_A.id)
        for item in items
    }
    for i, item_a in enumerate(items):
        for item_b in items[i + 1:]:
            if costs[item_a.name] == costs[item_b.name]:
                return item_a, item_b, costs[item_a.name]
    return None
