from dataclasses import dataclass
from typing import List, Optional


BASE_ID = 37370000


@dataclass
class LocationData:
    name: str
    ap_id: int
    region: str = "Fortress"
    goal_only: bool = False  # if True, only relevant for a specific goal
    item_requirements: str = ""


# ── Wealth Milestones ─────────────────────────────────────────────────────────
WEALTH_LOCATIONS: list[LocationData] = [
    LocationData("Humble Beginnings",    BASE_ID + 0,  "Fortress"),
    LocationData("Growing Stronghold",   BASE_ID + 1,  "Fortress"),
    LocationData("Prosperous Fortress",  BASE_ID + 2,  "Fortress"),
    LocationData("Rich Citadel",         BASE_ID + 3,  "Fortress"),
    LocationData("Legendary Vault",      BASE_ID + 4,  "Fortress"),
]

# ── First Production Milestones ───────────────────────────────────────────────
PRODUCTION_LOCATIONS: list[LocationData] = [
    LocationData("First Crafted Item",       BASE_ID + 100, "Fortress"),
    LocationData("First Weapon Forged",      BASE_ID + 101, "Fortress"),
    LocationData("First Armor Crafted",      BASE_ID + 102, "Fortress"),
    LocationData("First Furniture Made",     BASE_ID + 103, "Fortress"),
    LocationData("First Prepared Meal",      BASE_ID + 104, "Fortress"),
    LocationData("First Brew Complete",      BASE_ID + 105, "Fortress"),
    LocationData("First Metal Bar Smelted",  BASE_ID + 106, "Fortress"),
    LocationData("First Stone Block Cut",    BASE_ID + 107, "Fortress"),
    LocationData("First Cloth Woven",        BASE_ID + 108, "Fortress"),
    LocationData("First Leather Tanned",     BASE_ID + 109, "Fortress"),
    LocationData("First Gem Cut",            BASE_ID + 110, "Fortress"),
    LocationData("First Mechanism Made",     BASE_ID + 111, "Fortress"),
    LocationData("First Trap Built",         BASE_ID + 112, "Fortress"),
    LocationData("First Cage Constructed",   BASE_ID + 113, "Fortress"),
    LocationData("First Barrel Made",        BASE_ID + 114, "Fortress"),
    LocationData("First Chest Made",         BASE_ID + 115, "Fortress"),
    LocationData("First Table Made",         BASE_ID + 116, "Fortress"),
    LocationData("First Bed Made",           BASE_ID + 117, "Fortress"),
]

# ── Trade / Export Milestones ─────────────────────────────────────────────────
TRADE_LOCATIONS: list[LocationData] = [
    LocationData("First Trade Completed",          BASE_ID + 200, "Fortress"),
    LocationData("First Export",                   BASE_ID + 201, "Fortress"),
    LocationData("Dwarven Caravan Visit",          BASE_ID + 202, "Fortress"),
    LocationData("Elven Caravan Visit",            BASE_ID + 203, "Fortress"),
    LocationData("Human Caravan Visit",            BASE_ID + 204, "Fortress"),
    LocationData("Outpost Liaison Meeting",        BASE_ID + 205, "Fortress"),
]

# ── Fortress Status / Noble Appointments ──────────────────────────────────────
# IDs match checks.lua (BASE_ID + 300+).
# These track the civilisation's recognition of the fortress, from a mayor-run
# settlement up to a capital with a resident monarch.
STATUS_LOCATIONS: list[LocationData] = [
    LocationData("Mayor Elected",           BASE_ID + 300, "Fortress"),
    LocationData("Baron Appointed",         BASE_ID + 301, "Fortress"),
    LocationData("Count Appointed",         BASE_ID + 302, "Fortress"),
    LocationData("Duke Appointed",          BASE_ID + 303, "Fortress"),
    LocationData("Monarch Takes Residence", BASE_ID + 304, "Fortress"),
]

# ── Fortress Title Milestones ─────────────────────────────────────────────────
# Each title requires population AND either created-wealth OR exported-wealth.
# See https://dwarffortresswiki.org/index.php/Fortress
TITLE_LOCATIONS: list[LocationData] = [
    LocationData("Hamlet Established",      BASE_ID + 400, "Fortress"),
    LocationData("Village Established",     BASE_ID + 401, "Fortress"),
    LocationData("Town Established",        BASE_ID + 402, "Fortress"),
    LocationData("City Established",        BASE_ID + 403, "Fortress"),
    LocationData("Metropolis Established",  BASE_ID + 404, "Fortress"),
]

ALL_LOCATIONS: list[LocationData] = (
    WEALTH_LOCATIONS + PRODUCTION_LOCATIONS + TRADE_LOCATIONS
    + STATUS_LOCATIONS + TITLE_LOCATIONS
)

LOCATION_TABLE: dict[str, int] = {loc.name: loc.ap_id for loc in ALL_LOCATIONS}
