from dataclasses import dataclass
from BaseClasses import ItemClassification
from typing import Optional


BASE_ID = 37370000


@dataclass
class ItemData:
    name: str
    ap_id: int
    classification: ItemClassification
    quantity: int = 1  # how many copies go into the item pool


# ── Items DF sends to other players ──────────────────────────────────────────

PROGRESSION_ITEMS: list[ItemData] = [
    ItemData("Artifact Weapon",        BASE_ID + 500, ItemClassification.progression),
    ItemData("Artifact Armor",         BASE_ID + 501, ItemClassification.progression),
    ItemData("Legendary Blueprint",    BASE_ID + 502, ItemClassification.progression),
]

USEFUL_ITEMS: list[ItemData] = [
    ItemData("Masterwork Crafts",      BASE_ID + 510, ItemClassification.useful, quantity=3),
    ItemData("Dwarven Steel Sword",    BASE_ID + 511, ItemClassification.useful, quantity=2),
    ItemData("Fine Cloth",             BASE_ID + 512, ItemClassification.useful, quantity=2),
    ItemData("Adamantine Fiber",       BASE_ID + 513, ItemClassification.useful),
]

FILLER_ITEMS: list[ItemData] = [
    ItemData("Dwarven Ale",            BASE_ID + 520, ItemClassification.filler, quantity=5),
    ItemData("Stone Trinket",          BASE_ID + 521, ItemClassification.filler, quantity=5),
    ItemData("Bone Crafts",            BASE_ID + 522, ItemClassification.filler, quantity=4),
    ItemData("Raw Ore",                BASE_ID + 523, ItemClassification.filler, quantity=3),
    ItemData("Wooden Cup",             BASE_ID + 524, ItemClassification.filler, quantity=3),
]

TRAP_ITEMS: list[ItemData] = [
    ItemData("Cave Fisher Silk",       BASE_ID + 530, ItemClassification.trap, quantity=2),
    ItemData("Dwarf Bones",            BASE_ID + 531, ItemClassification.trap, quantity=2),
    ItemData("Goblin Trophy",          BASE_ID + 532, ItemClassification.trap, quantity=2),
]

# ── Items DF receives from other players ─────────────────────────────────────
# (These are delivered in-game; they don't go into the AP item pool,
#  but we define them here for name→ID mapping used by the client.)

RECEIVED_TRADE_GOODS: list[ItemData] = [
    ItemData("Cut Sapphire",           BASE_ID + 600, ItemClassification.useful),
    ItemData("Cut Ruby",               BASE_ID + 601, ItemClassification.useful),
    ItemData("Cut Diamond",            BASE_ID + 602, ItemClassification.useful),
    ItemData("Gold Bar",               BASE_ID + 603, ItemClassification.useful),
    ItemData("Silver Bar",             BASE_ID + 604, ItemClassification.useful),
    ItemData("Steel Bar",              BASE_ID + 605, ItemClassification.useful),
    ItemData("Masterwork Craft",       BASE_ID + 606, ItemClassification.useful),
]

RECEIVED_RESOURCES: list[ItemData] = [
    ItemData("Food Bundle",            BASE_ID + 610, ItemClassification.filler),
    ItemData("Wood Bundle",            BASE_ID + 611, ItemClassification.filler),
    ItemData("Iron Ore Bundle",        BASE_ID + 612, ItemClassification.filler),
    ItemData("Coal Bundle",            BASE_ID + 613, ItemClassification.filler),
]

RECEIVED_TRAPS: list[ItemData] = [
    ItemData("Goblin Ambush",          BASE_ID + 620, ItemClassification.trap),
    ItemData("Cave Bear Incursion",    BASE_ID + 621, ItemClassification.trap),
    ItemData("Vermin Infestation",     BASE_ID + 622, ItemClassification.trap),
    ItemData("Tantrum Trigger",        BASE_ID + 623, ItemClassification.trap),
    ItemData("Lost Caravan",           BASE_ID + 624, ItemClassification.trap),
]

# Pool that goes into the AP multiworld (what DF sends to others)
AP_ITEM_POOL: list[ItemData] = (
    PROGRESSION_ITEMS + USEFUL_ITEMS + FILLER_ITEMS + TRAP_ITEMS
)

# All items (for name→ID mapping, including received items)
ALL_ITEMS: list[ItemData] = (
    AP_ITEM_POOL
    + RECEIVED_TRADE_GOODS
    + RECEIVED_RESOURCES
    + RECEIVED_TRAPS
)

ITEM_TABLE: dict[str, int] = {item.name: item.ap_id for item in ALL_ITEMS}
