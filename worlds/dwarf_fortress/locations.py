from dataclasses import dataclass
from typing import List, Optional

BASE_ID = 37370000


@dataclass
class LocationData:
    name: str
    ap_id: int
    region: str = "Fortress"
    goal_only: bool = False  # if True, only relevant for a specific goal
    material_type: str = ""
    df_item: str = ""
    threshold: int = 0


# ── Wealth Milestones ─────────────────────────────────────────────────────────
WEALTH_LOCATIONS: list[LocationData] = [
    LocationData("Humble Beginnings (1,000)",    BASE_ID + 0,  "Fortress"),
    LocationData("Growing Stronghold (10,000)",  BASE_ID + 1,  "Fortress"),
    LocationData("Prosperous Fortress (50,000)", BASE_ID + 2,  "Fortress"),
    LocationData("Rich Citadel (100,000)",       BASE_ID + 3,  "Fortress"),
    LocationData("Legendary Vault (500,000)",    BASE_ID + 4,  "Fortress"),
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
    LocationData("First Block Cut",          BASE_ID + 107, "Fortress"),
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
    LocationData("First Anvil Made",         BASE_ID + 118, "Fortress"),
    LocationData("First Millstone Made",     BASE_ID + 119, "Fortress"),
    LocationData("First Minecart Made",      BASE_ID + 120, "Fortress"),
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


# ── Mining Milestones ─────────────────────────────────────────────────────────
# Depth = surface z-level minus the deepest z any mining job has reached.
# Tiles = cumulative count of completed dig/channel/staircase/ramp jobs.
# IDs match checks.lua (BASE_ID + 700 depth, +710 tiles).
MINING_LOCATIONS: list[LocationData] = [
    LocationData("Delved 10 Levels Deep",       BASE_ID + 700, "Fortress"),
    LocationData("Delved 25 Levels Deep",       BASE_ID + 701, "Fortress"),
    LocationData("Delved 50 Levels Deep",       BASE_ID + 702, "Fortress"),
    LocationData("Delved 75 Levels Deep",       BASE_ID + 703, "Fortress"),
    LocationData("Delved 100 Levels Deep",      BASE_ID + 704, "Fortress"),
    LocationData("Excavator I (100 tiles)",     BASE_ID + 710, "Fortress"),
    LocationData("Excavator II (500 tiles)",    BASE_ID + 711, "Fortress"),
    LocationData("Excavator III (2,000 tiles)", BASE_ID + 712, "Fortress"),
    LocationData("Excavator IV (5,000 tiles)",  BASE_ID + 713, "Fortress"),
    LocationData("Excavator V (10,000 tiles)",  BASE_ID + 714, "Fortress"),
    LocationData("First Cavern Breached",        BASE_ID + 720, "Fortress"),
    LocationData("Second Cavern Breached",       BASE_ID + 721, "Fortress"),
    LocationData("Third Cavern Breached",        BASE_ID + 722, "Fortress"),
    LocationData("Reached the Magma Sea",        BASE_ID + 723, "Fortress"),
    LocationData("Breached the Circus",          BASE_ID + 724, "Fortress"),
]

# ── Farming Milestones ────────────────────────────────────────────────────────
# Cumulative count of harvested crops (PLANT items created). IDs match checks.lua
# (BASE_ID + 730).
FARMING_LOCATIONS: list[LocationData] = [
    LocationData("Harvest 50 Crops",    BASE_ID + 730, "Fortress"),
    LocationData("Harvest 100 Crops",   BASE_ID + 731, "Fortress"),
    LocationData("Harvest 250 Crops",   BASE_ID + 732, "Fortress"),
    LocationData("Harvest 500 Crops",   BASE_ID + 733, "Fortress"),
    LocationData("Harvest 1,000 Crops", BASE_ID + 734, "Fortress"),
]

# ── Infrastructure Milestones ─────────────────────────────────────────────────
INFRASTRUCTURE_LOCATIONS: list[LocationData] = [
    LocationData("Built a Well",   BASE_ID + 740, "Fortress"),
    LocationData("Pumped Water",   BASE_ID + 741, "Fortress"),
    LocationData("Pumped Magma",   BASE_ID + 742, "Fortress"),
]

# ── Biology / Animal Milestones ───────────────────────────────────────────────
BIOLOGY_LOCATIONS: list[LocationData] = [
    LocationData("First Eggs Hatched",  BASE_ID + 750, "Fortress"),
    LocationData("Caged a Megabeast",   BASE_ID + 751, "Fortress"),
]

# ── Deep / Endgame Milestones ─────────────────────────────────────────────────
ENDGAME_LOCATIONS: list[LocationData] = [
    LocationData("Mined Adamantine",  BASE_ID + 760, "Fortress"),
    LocationData("Sold an Artifact",  BASE_ID + 761, "Fortress"),
]


# Craft locations are NOT included here. They are computed deterministically by
# craftsanity.build_craft_location_table() and merged into the World's
# location_name_to_id in __init__.py (see _FULL_LOCATION_TABLE). Keeping them out
# of this module avoids a circular import (craftsanity imports from locations).
ALL_LOCATIONS: list[LocationData] = (
    WEALTH_LOCATIONS + PRODUCTION_LOCATIONS + TRADE_LOCATIONS
    + STATUS_LOCATIONS + TITLE_LOCATIONS + MINING_LOCATIONS
    + FARMING_LOCATIONS + INFRASTRUCTURE_LOCATIONS
    + BIOLOGY_LOCATIONS + ENDGAME_LOCATIONS
)
LOCATION_TABLE: dict[str, int] = {loc.name: loc.ap_id for loc in ALL_LOCATIONS}
