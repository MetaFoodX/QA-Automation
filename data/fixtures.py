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


@dataclass(frozen=True)
class Restaurant:
    id: int
    name: str
    stations: Dict[str, Station]              = field(default_factory=dict)
    venues: Dict[str, Venue]                  = field(default_factory=dict)
    service_periods: Dict[str, ServicePeriod] = field(default_factory=dict)
    menu_items: Dict[str, MenuItem]           = field(default_factory=dict)


RESTAURANT_A = Restaurant(
    id=200,
    name="Raj Restaurant",
    stations={
        "a1": Station(id="5051cb17c6df4e028e266b63b12b3895", name="Raj Station 1"),
        
    },
    venues={
        "v_a1": Venue(id="e7df55b7-400c-4322-a13b-95936076b9e0", name="Delicious Without"),
    
    },
    service_periods={
        "all_day": ServicePeriod(id="6fa96823-f1d4-4681-a284-4f59acb5588b", name="All Day"),
    },
    menu_items={
        "item_a1":  MenuItem(id=61817, name="Strawberries"),
        "item_a2":  MenuItem(id=61818, name="Corn on the cob"),
        "item_a3":  MenuItem(id=61805, name="Strawberry")
    },
)





RESTAURANTS: Dict[str, Restaurant] = {
    "a": RESTAURANT_A,
    
}