"""Test fixture registry: Account → Restaurant → (Stations / Venues / Service Periods / Menu Items)."""
from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class Station:
    id: str
    name: str


@dataclass(frozen=True)
class Venue:
    id: str
    name: str


@dataclass(frozen=True)
class ServicePeriod:
    id: str
    name: str


@dataclass(frozen=True)
class MenuItem:
    id: int
    name: str
    category: str = ""


@dataclass(frozen=True)
class Restaurant:
    id: int
    name: str
    stations: Dict[str, Station]              = field(default_factory=dict)
    venues: Dict[str, Venue]                  = field(default_factory=dict)
    service_periods: Dict[str, ServicePeriod] = field(default_factory=dict)
    menu_items: Dict[str, MenuItem]           = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Restaurant A — Test Kitchen (ID: 241, AccountID: 105)
# ---------------------------------------------------------------------------
RESTAURANT_A = Restaurant(
    id=241,
    name="Test Kitchen",
    stations={
        "s_a1": Station(id="abe4295d3ab842f588d4f265f9966ce4", name="Test_01"),
        "s_a2": Station(id="62be647cf5184aaf82ecb9c40db04a58", name="test_02"),
    },
    venues={
        "v_a1": Venue(id="60714074-fe12-4b10-ab8e-55cfcd033916", name="Mexican Venue"),
        "v_a2": Venue(id="89070b42-42f9-4568-8eeb-21896622f5e6", name="Stuffing Venue"),
    },
    service_periods={
        "all_day": ServicePeriod(id="6e49bf41-2f2c-4c1f-9210-f4c29aeb342a", name="All Day"),
        "lunch":   ServicePeriod(id="92d56099-e75f-4984-b0c5-dd62705b06f9", name="Lunch"),
        "dinner":  ServicePeriod(id="27a36991-3ae1-41c4-a5b6-9882e6b76d93", name="Dinner"),
    },
    menu_items={
        # Fruits
        "ancient_tree_black_tea":    MenuItem(id=85458, name="Ancient Tree Black Tea",  category="Fruits"),
        "bananas":                   MenuItem(id=85475, name="Bananas",                 category="Fruits"),
        "cherries":                  MenuItem(id=85522, name="Cherries",                category="Fruits"),
        "fresas":                    MenuItem(id=85572, name="Fresas",                  category="Fruits"),
        "one_birthday_protein_bar":  MenuItem(id=85641, name="One Birthday Protein Bar",category="Fruits"),
        "strawberries":              MenuItem(id=85735, name="Strawberries",            category="Fruits"),
        "uvas":                      MenuItem(id=85756, name="Uvas",                    category="Fruits"),
        # Kitchen Waste
        "diced_ham":                 MenuItem(id=85552, name="Diced Ham",               category="Kitchen Waste"),
        "edamame":                   MenuItem(id=85561, name="Edamame",                 category="Kitchen Waste"),
        "fennel_trim":               MenuItem(id=85568, name="Fennel Trim",             category="Kitchen Waste"),
        # Post Consumer
        "turkey":                    MenuItem(id=85753, name="Turkey",                  category="Post Consumer"),
        "vanilla_yogurt":            MenuItem(id=85757, name="Vanilla Yogurt",          category="Post Consumer"),
        "zucchini":                  MenuItem(id=85775, name="Zucchini",                category="Post Consumer"),
        # Vegetables
        "hojas_de_espinaca":         MenuItem(id=85600, name="Hojas de Espinaca",       category="Vegetables"),
        "mi_fan":                    MenuItem(id=85629, name="Mi Fan",                  category="Vegetables"),
        "nuts":                      MenuItem(id=85639, name="Nuts",                    category="Vegetables"),
        "yucca_fries":               MenuItem(id=85772, name="Yucca Fries",             category="Vegetables"),
        "corn":                      MenuItem(id=85536, name="Corn",                    category="Vegetables"),
    },
)

RESTAURANTS = {
    "restaurant_a": RESTAURANT_A,
}
