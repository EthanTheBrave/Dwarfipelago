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

# Workshop blueprint items — progression gates that other players find and send
# to unlock workshops in your fortress. These are the core AP mechanic.
# Workshop / furnace / building blueprint items — progression gates that other
# players find and send to unlock structures in your fortress.
BLUEPRINT_ITEMS: list[ItemData] = [
    # Workshops
    ItemData("Craftsdwarf's Workshop Blueprint", BASE_ID + 540, ItemClassification.progression),
    ItemData("Forge Blueprint",                  BASE_ID + 541, ItemClassification.progression),
    ItemData("Kitchen Blueprint",                BASE_ID + 543, ItemClassification.progression),
    ItemData("Jeweler's Workshop Blueprint",     BASE_ID + 544, ItemClassification.progression),
    ItemData("Clothier's Shop Blueprint",        BASE_ID + 545, ItemClassification.progression),
    ItemData("Tanner's Blueprint",               BASE_ID + 546, ItemClassification.progression),
    ItemData("Mechanic's Workshop Blueprint",    BASE_ID + 547, ItemClassification.progression),
    ItemData("Magma Forge Blueprint",            BASE_ID + 548, ItemClassification.progression),
    ItemData("Siege Workshop Blueprint",         BASE_ID + 549, ItemClassification.progression),
    ItemData("Soap Maker's Workshop Blueprint",  BASE_ID + 550, ItemClassification.progression),
    ItemData("Ashery Blueprint",                 BASE_ID + 551, ItemClassification.progression),
    ItemData("Bowyer's Workshop Blueprint",      BASE_ID + 552, ItemClassification.progression),
    ItemData("Screw Press Blueprint",            BASE_ID + 553, ItemClassification.progression),
    ItemData("Fishery Blueprint",                BASE_ID + 554, ItemClassification.progression),
    ItemData("Loom Blueprint",                   BASE_ID + 555, ItemClassification.progression),
    ItemData("Dyer's Workshop Blueprint",        BASE_ID + 556, ItemClassification.progression),
    ItemData("Butcher's Shop Blueprint",         BASE_ID + 557, ItemClassification.progression),
    ItemData("Farmer's Workshop Blueprint",      BASE_ID + 558, ItemClassification.progression),
    # Furnaces
    ItemData("Smelter Blueprint",                BASE_ID + 542, ItemClassification.progression),
    ItemData("Magma Smelter Blueprint",          BASE_ID + 559, ItemClassification.progression),
    ItemData("Wood Furnace Blueprint",           BASE_ID + 560, ItemClassification.progression),
    ItemData("Glass Furnace Blueprint",          BASE_ID + 561, ItemClassification.progression),
    ItemData("Kiln Blueprint",                   BASE_ID + 562, ItemClassification.progression),
    ItemData("Magma Kiln Blueprint",             BASE_ID + 563, ItemClassification.progression),
    ItemData("Magma Glass Furnace Blueprint",    BASE_ID + 564, ItemClassification.progression),
    # Buildings
    ItemData("Farm Plot Blueprint",              BASE_ID + 565, ItemClassification.progression),
]

PROGRESSION_ITEMS: list[ItemData] = [
    ItemData("Artifact Weapon",        BASE_ID + 500, ItemClassification.progression),
    ItemData("Artifact Armor",         BASE_ID + 501, ItemClassification.progression),
    ItemData("Legendary Blueprint",    BASE_ID + 502, ItemClassification.progression),
]

USEFUL_ITEMS: list[ItemData] = [
    ItemData("Masterwork Crafts",      BASE_ID + 510, ItemClassification.useful),
    ItemData("Dwarven Steel Sword",    BASE_ID + 511, ItemClassification.useful),
    ItemData("Fine Cloth",             BASE_ID + 512, ItemClassification.useful),
    ItemData("Adamantine Fiber",       BASE_ID + 513, ItemClassification.useful),
]

FILLER_ITEMS: list[ItemData] = [
    ItemData("Dwarven Ale",            BASE_ID + 520, ItemClassification.filler),
    ItemData("Stone Trinket",          BASE_ID + 521, ItemClassification.filler),
    ItemData("Bone Crafts",            BASE_ID + 522, ItemClassification.filler),
    ItemData("Raw Ore",                BASE_ID + 523, ItemClassification.filler),
    ItemData("Wooden Cup",             BASE_ID + 524, ItemClassification.filler),
]

TRAP_ITEMS: list[ItemData] = [
    ItemData("Cave Fisher Silk",       BASE_ID + 530, ItemClassification.trap),
    ItemData("Dwarf Bones",            BASE_ID + 531, ItemClassification.trap),
    ItemData("Goblin Trophy",          BASE_ID + 532, ItemClassification.trap),
]

# ── Items the DF player receives from the multiworld ─────────────────────────
# These ARE part of the AP item pool — they must be placed at locations so the
# AP server can route them back to the DF player when those locations are checked.
# The client's deliver_item() call hands them off to items.lua for in-game effect.

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

# Pool that goes into the AP multiworld.
#
# BLUEPRINT_ITEMS are progression-gated items the DF player must receive to
# unlock workshops. They must ALL be in the pool — create_items() guarantees
# they are never trimmed, regardless of location count.
#
# PROGRESSION_ITEMS / USEFUL_ITEMS / FILLER_ITEMS / TRAP_ITEMS are outbound
# items DF contributes that other players may find.
#
# RECEIVED_* are items routed back to the DF player (trade goods, resources,
# traps) — they live in the pool so the AP server can place them at locations.
AP_ITEM_POOL: list[ItemData] = \
    BLUEPRINT_ITEMS \
    + PROGRESSION_ITEMS \
    + USEFUL_ITEMS \
    + FILLER_ITEMS \
    + TRAP_ITEMS \
    + RECEIVED_TRADE_GOODS \
    + RECEIVED_RESOURCES \
    + RECEIVED_TRAPS \


# All items (for name→ID mapping used by item_name_to_id).
# AP_ITEM_POOL already covers every item the world deals with.
ALL_ITEMS: list[ItemData] = AP_ITEM_POOL
ITEM_TABLE: dict[str, int] = {}
for data in ALL_ITEMS:
    ITEM_TABLE.update({data.name: data.ap_id})
