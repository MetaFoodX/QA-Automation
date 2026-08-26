"""HTTP client for the Menu Items API — lookups plus CostPerLb updates."""

import allure
import requests
from requests.adapters import HTTPAdapter

from shared.config.settings import settings

_POOL_SIZE = 55


class MenuItemClient:
    """Wraps GET /menuitems with auth."""

    def __init__(self, access_token: str):
        self.base_url = f"{settings.base_url}/api/v1"
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=_POOL_SIZE, pool_maxsize=_POOL_SIZE)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        })

    def get_by_name(self, name: str, restaurant_id: int) -> dict:
        """Look up a single menu item by exact name. Raises if not found."""
        url = f"{self.base_url}/menuitems"
        params = {"current": 1, "pageSize": 10, "RestaurantID": restaurant_id, "Name": name}
        with allure.step(f"GET /menuitems?Name={name}"):
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            match = next((item for item in data if item.get("Name") == name), None)
            if match is None:
                raise ValueError(f"Menu item '{name}' not found for RestaurantID={restaurant_id}")
            return match

    def get_cost_per_lb(self, name: str, restaurant_id: int) -> float:
        """Current CostPerLb ($/lb) for a menu item, read live (not cached/hardcoded)."""
        item = self.get_by_name(name, restaurant_id)
        return float(item["CostPerLb"])

    def update_cost_per_lb(self, menu_item_id: int, cost_per_lb: float) -> dict:
        """Update a menu item's CostPerLb by ID. Only CostPerLb is sent —
        Name/Status are left untouched. Callers are responsible for
        restoring the original value afterward (this mutates real,
        persistent dashboard data, not per-test scan rows)."""
        url = f"{self.base_url}/menuitems/{menu_item_id}"
        with allure.step(f"PATCH /menuitems/{menu_item_id} CostPerLb={cost_per_lb}"):
            resp = self.session.patch(url, json={"CostPerLb": cost_per_lb}, timeout=30)
            resp.raise_for_status()
            return resp.json()
