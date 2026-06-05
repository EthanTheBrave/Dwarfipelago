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
    # Normally Start with
    ItemData("Carpenter's Workshop Blueprint",   BASE_ID + 566, ItemClassification.progression),
    ItemData("Stoneworker's Workshop Blueprint", BASE_ID + 567, ItemClassification.progression),
    ItemData("Still Blueprint",                  BASE_ID + 568, ItemClassification.progression),
    
    ItemData("Leather Works Blueprint",          BASE_ID + 569, ItemClassification.progression),

]

PROGRESSION_ITEMS: list[ItemData] = [
    ItemData("Artifact Weapon",        BASE_ID + 500, ItemClassification.progression),
    ItemData("Artifact Armor",         BASE_ID + 501, ItemClassification.progression),
    ItemData("Master Builder's Codex", BASE_ID + 502, ItemClassification.progression),
]

# Progressive lock items — gate milestone checks behind received items.
# quantity > 1 means that many copies enter the pool; Lua counts how many
# the DF player has received and uses the count as the unlock tier.
PROGRESSION_LOCK_ITEMS: list[ItemData] = [
    # Legendary Wealth: 5 coffers → unlock wealth tiers 1–5
    ItemData("Merchant's Coffer",    BASE_ID + 630, ItemClassification.progression, quantity=5),
    # Population Boom: 5 waves → unlock title/population tiers 1–5
    ItemData("Immigration Wave",     BASE_ID + 631, ItemClassification.progression, quantity=5),
    # Mountainhome: one charter per noble rank
    ItemData("Baron's Charter",      BASE_ID + 632, ItemClassification.progression),
    ItemData("Count's Charter",      BASE_ID + 633, ItemClassification.progression),
    ItemData("Duke's Charter",       BASE_ID + 634, ItemClassification.progression),
    ItemData("Monarch's Invitation", BASE_ID + 635, ItemClassification.progression),
    # Slay Megabeast: 3 training items gate megabeast goal
    ItemData("Military Training",    BASE_ID + 636, ItemClassification.progression, quantity=4),
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

CRAFT_ITEMS: list[ItemData] = [ #commented items people should get when getting the blueprints
    ItemData("Crafting Beds", BASE_ID + 1000, ItemClassification.progression),
    ItemData("Crafting Corkscrew", BASE_ID + 1001, ItemClassification.progression),
    ItemData("Crafting Blocks", BASE_ID + 1002, ItemClassification.progression),
    ItemData("Crafting Spike", BASE_ID + 1003, ItemClassification.progression),
    ItemData("Crafting Ball", BASE_ID + 1004, ItemClassification.progression),
    ItemData("Crafting Altar", BASE_ID + 1005, ItemClassification.progression),
    ItemData("Crafting Animal Trap", BASE_ID + 1006, ItemClassification.progression),
    ItemData("Crafting Armor Stand", BASE_ID + 1007, ItemClassification.progression),
    ItemData("Crafting Barrel", BASE_ID + 1008, ItemClassification.progression),
    ItemData("Crafting Bin", BASE_ID + 1009, ItemClassification.progression),
    ItemData("Crafting Bookcase", BASE_ID + 1010, ItemClassification.progression),
    ItemData("Crafting Bucket", BASE_ID + 1011, ItemClassification.progression),
    ItemData("Crafting Buckler", BASE_ID + 1012, ItemClassification.progression),
    ItemData("Crafting Cabinet", BASE_ID + 1013, ItemClassification.progression),
    ItemData("Crafting Cage", BASE_ID + 1014, ItemClassification.progression),
    ItemData("Crafting Burial Container", BASE_ID + 1015, ItemClassification.progression),
    ItemData("Crafting Chair", BASE_ID + 1016, ItemClassification.progression),
    ItemData("Crafting Container", BASE_ID + 1017, ItemClassification.progression),
    ItemData("Crafting Crutch", BASE_ID + 1018, ItemClassification.progression),
    ItemData("Crafting Door", BASE_ID + 1019, ItemClassification.progression),
    ItemData("Crafting Floodgate", BASE_ID + 1020, ItemClassification.progression),
    ItemData("Crafting Grate", BASE_ID + 1021, ItemClassification.progression),
    ItemData("Crafting Hatch Cover", BASE_ID + 1022, ItemClassification.progression),
    ItemData("Crafting Minecart", BASE_ID + 1023, ItemClassification.progression),
    ItemData("Crafting Pedestal", BASE_ID + 1024, ItemClassification.progression),
    ItemData("Crafting Pipe Section", BASE_ID + 1025, ItemClassification.progression),
    ItemData("Crafting Shield", BASE_ID + 1026, ItemClassification.progression),
    ItemData("Crafting Splint", BASE_ID + 1027, ItemClassification.progression),
    ItemData("Crafting Stepladder", BASE_ID + 1028, ItemClassification.progression),
    ItemData("Crafting Table", BASE_ID + 1029, ItemClassification.progression),
    ItemData("Crafting Training Axe", BASE_ID + 1030, ItemClassification.progression),
    ItemData("Crafting Training Spear", BASE_ID + 1031, ItemClassification.progression),
    ItemData("Crafting Training Sword", BASE_ID + 1032, ItemClassification.progression),
    ItemData("Crafting Weapon Rack", BASE_ID + 1033, ItemClassification.progression),
    ItemData("Crafting Wheelbarrow", BASE_ID + 1034, ItemClassification.progression),
    ItemData("Crafting Crossbow", BASE_ID + 1035, ItemClassification.progression),
    ItemData("Crafting Bolt", BASE_ID + 1036, ItemClassification.progression),
    ItemData("Crafting Millstone", BASE_ID + 1037, ItemClassification.progression),
    ItemData("Crafting Quern", BASE_ID + 1038, ItemClassification.progression),
    ItemData("Crafting Slab", BASE_ID + 1039, ItemClassification.progression),
    ItemData("Crafting Statue", BASE_ID + 1040, ItemClassification.progression),
    ItemData("Crafting Mechanism", BASE_ID + 1041, ItemClassification.progression),
    ItemData("Crafting Traction Bench", BASE_ID + 1042, ItemClassification.progression),
    ItemData("Crafting Crafts", BASE_ID + 1043, ItemClassification.progression),
    ItemData("Crafting Liquid Container", BASE_ID + 1044, ItemClassification.progression),
    ItemData("Crafting Cup", BASE_ID + 1045, ItemClassification.progression),
    ItemData("Crafting Toy", BASE_ID + 1046, ItemClassification.progression),
    ItemData("Crafting Totem", BASE_ID + 1047, ItemClassification.progression),
    ItemData("Crafting Helm", BASE_ID + 1048, ItemClassification.progression),
    ItemData("Crafting Ballista Parts", BASE_ID + 1049, ItemClassification.progression),
    ItemData("Crafting Catapult Parts", BASE_ID + 1050, ItemClassification.progression),
    ItemData("Crafting Ballista Arrows", BASE_ID + 1051, ItemClassification.progression),
    ItemData("Crafting Ash", BASE_ID + 1052, ItemClassification.progression),
    ItemData("Crafting Charcoal", BASE_ID + 1053, ItemClassification.progression),
    ItemData("Crafting Metal Bars", BASE_ID + 1054, ItemClassification.progression),
    ItemData("Crafting Coke Bars", BASE_ID + 1055, ItemClassification.progression),
    ItemData("Crafting Pearlash", BASE_ID + 1056, ItemClassification.progression),
    ItemData("Crafting Gypsum Plaster", BASE_ID + 1057, ItemClassification.progression),
    ItemData("Crafting Jug", BASE_ID + 1058, ItemClassification.progression),
    ItemData("Crafting Large Pot", BASE_ID + 1059, ItemClassification.progression),
    ItemData("Crafting Hive", BASE_ID + 1060, ItemClassification.progression),
    ItemData("Crafting Quicklime", BASE_ID + 1061, ItemClassification.progression),
    ItemData("Crafting Glass", BASE_ID + 1062, ItemClassification.progression),
    ItemData("Crafting Window", BASE_ID + 1063, ItemClassification.progression),
    ItemData("Crafting Book Binding", BASE_ID + 1064, ItemClassification.progression),
    ItemData("Crafting Scroll Roller", BASE_ID + 1065, ItemClassification.progression),
    ItemData("Crafting Leather", BASE_ID + 1066, ItemClassification.progression),
    ItemData("Crafting Sheet", BASE_ID + 1067, ItemClassification.progression),
    ItemData("Crafting Cloth", BASE_ID + 1068, ItemClassification.progression),
    ItemData("Crafting Alcohol", BASE_ID + 1069, ItemClassification.progression),
    ItemData("Crafting Lye", BASE_ID + 1070, ItemClassification.progression),
    ItemData("Crafting Potash", BASE_ID + 1071, ItemClassification.progression),
    ItemData("Crafting Milk of Lime", BASE_ID + 1072, ItemClassification.progression),
    ItemData("Crafting Prepared Meal", BASE_ID + 1073, ItemClassification.progression),
    ItemData("Crafting Tallow", BASE_ID + 1074, ItemClassification.progression),
    ItemData("Crafting Oil", BASE_ID + 1075, ItemClassification.progression),
    ItemData("Crafting Honey", BASE_ID + 1076, ItemClassification.progression),
    ItemData("Crafting Headgear Clothing", BASE_ID + 1077, ItemClassification.progression),
    ItemData("Crafting Upper Body Clothing", BASE_ID + 1078, ItemClassification.progression),
    ItemData("Crafting Upper Body Armor", BASE_ID + 1079, ItemClassification.progression),
    ItemData("Crafting Hand Clothing", BASE_ID + 1080, ItemClassification.progression),
    ItemData("Crafting Gauntlets", BASE_ID + 1081, ItemClassification.progression),
    ItemData("Crafting Lower Body Clothing", BASE_ID + 1082, ItemClassification.progression),
    ItemData("Crafting Lower Body Armor", BASE_ID + 1083, ItemClassification.progression),
    ItemData("Crafting Footwear", BASE_ID + 1084, ItemClassification.progression),
    ItemData("Crafting Dye", BASE_ID + 1085, ItemClassification.progression),
    ItemData("Crafting Bag", BASE_ID + 1086, ItemClassification.progression),
    ItemData("Crafting Rope/Chain", BASE_ID + 1087, ItemClassification.progression),
    ItemData("Crafting Battle Axe", BASE_ID + 1088, ItemClassification.progression),
    ItemData("Crafting Mace", BASE_ID + 1089, ItemClassification.progression),
    ItemData("Crafting Pick", BASE_ID + 1090, ItemClassification.progression),
    ItemData("Crafting Short Sword", BASE_ID + 1091, ItemClassification.progression),
    ItemData("Crafting Spear", BASE_ID + 1092, ItemClassification.progression),
    ItemData("Crafting War Hammer", BASE_ID + 1093, ItemClassification.progression),
    ItemData("Crafting Anvil", BASE_ID + 1094, ItemClassification.progression),
    ItemData("Crafting Coins", BASE_ID + 1095, ItemClassification.progression),
    ItemData("Crafting Soap", BASE_ID + 1096, ItemClassification.progression),
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
    + PROGRESSION_LOCK_ITEMS \
    + CRAFT_ITEMS \
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
