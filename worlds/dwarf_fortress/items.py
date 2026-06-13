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
    weight: int = 10   # relative frequency when padding the pool with filler
                       # (higher = more common; only used for FILLER_ITEMS)


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
    ItemData("Merchant's Coffer",           BASE_ID + 630, ItemClassification.progression, quantity=5),
    # Population Boom: 5 waves → unlock title/population tiers 1–5
    ItemData("Immigration Wave",            BASE_ID + 631, ItemClassification.progression, quantity=5),
    # Mountainhome: one charter per noble rank
    ItemData("Baron's Charter",             BASE_ID + 632, ItemClassification.progression),
    ItemData("Count's Charter",             BASE_ID + 633, ItemClassification.progression),
    ItemData("Duke's Charter",              BASE_ID + 634, ItemClassification.progression),
    ItemData("Monarch's Invitation",        BASE_ID + 635, ItemClassification.progression),
    # Slay Megabeast: 3 training items gate megabeast goal
    ItemData("Military Training",           BASE_ID + 636, ItemClassification.progression, quantity=4),
    # Remains of the Great King goal
    ItemData("Remains of the Great King",   BASE_ID + 637, ItemClassification.progression, quantity=5),
]

USEFUL_ITEMS: list[ItemData] = [
    ItemData("Masterwork Crafts",      BASE_ID + 510, ItemClassification.useful),
    ItemData("Dwarven Steel Sword",    BASE_ID + 511, ItemClassification.useful),
    ItemData("Fine Cloth",             BASE_ID + 512, ItemClassification.useful),
    ItemData("Adamantine Fiber",       BASE_ID + 513, ItemClassification.useful),
    ItemData("Sunlight Tonic",         BASE_ID + 514, ItemClassification.useful),
    ItemData("Breeding Pigs",          BASE_ID + 515, ItemClassification.useful),
    ItemData("Breeding Chickens",      BASE_ID + 516, ItemClassification.useful),
    ItemData("Breeding Alpacas",       BASE_ID + 517, ItemClassification.useful),
    ItemData("Breeding Cows",          BASE_ID + 518, ItemClassification.useful),
    ItemData("Breeding Sheep",         BASE_ID + 519, ItemClassification.useful),
    ItemData("Breeding Yaks",          BASE_ID + 538, ItemClassification.useful),
]

FILLER_ITEMS: list[ItemData] = [
    # Flavor filler — kept but down-weighted so they no longer dominate the pool.
    ItemData("Dwarven Ale",            BASE_ID + 520, ItemClassification.filler, weight=10),
    ItemData("Stone Trinket",          BASE_ID + 521, ItemClassification.filler, weight=3),
    ItemData("Bone Crafts",            BASE_ID + 522, ItemClassification.filler, weight=6),
    ItemData("Raw Ore",                BASE_ID + 523, ItemClassification.filler, weight=10),
    ItemData("Wooden Cup",             BASE_ID + 524, ItemClassification.filler, weight=3),
    # Useful industry materials — the bulk of what a DF player should receive.
    ItemData("Flux Stone",             BASE_ID + 525, ItemClassification.filler, weight=12),
    ItemData("Pig Iron Bar",           BASE_ID + 526, ItemClassification.filler, weight=10),
    ItemData("Charcoal",               BASE_ID + 527, ItemClassification.filler, weight=12),
    ItemData("Cloth Bolt",             BASE_ID + 528, ItemClassification.filler, weight=10),
    ItemData("Tanned Leather",         BASE_ID + 529, ItemClassification.filler, weight=10),
    ItemData("Bag of Sand",            BASE_ID + 536, ItemClassification.filler, weight=10),
    ItemData("Raw Clay",               BASE_ID + 537, ItemClassification.filler, weight=10),
    # Low-grade (copper) tools/gear — genuinely useful recovery items, kept rare.
    ItemData("Copper Pick",            BASE_ID + 533, ItemClassification.filler, weight=3),
    ItemData("Copper Axe",             BASE_ID + 534, ItemClassification.filler, weight=3),
    ItemData("Copper Short Sword",     BASE_ID + 535, ItemClassification.filler, weight=2),
]

TRAP_ITEMS: list[ItemData] = [
    ItemData("Cave Fisher Silk",       BASE_ID + 530, ItemClassification.trap),
    ItemData("Dwarf Bones",            BASE_ID + 531, ItemClassification.trap),
    ItemData("Goblin Trophy",          BASE_ID + 532, ItemClassification.trap),
]

CRAFT_ITEMS: list[ItemData] = [ #commented items people should get when getting the blueprints
    ItemData("Beds Permit", BASE_ID + 1000, ItemClassification.progression),
    ItemData("Corkscrew Permit", BASE_ID + 1001, ItemClassification.progression),
    ItemData("Blocks Permit", BASE_ID + 1002, ItemClassification.progression),
    ItemData("Spike Permit", BASE_ID + 1003, ItemClassification.progression),
    ItemData("Ball Permit", BASE_ID + 1004, ItemClassification.progression),
    ItemData("Altar Permit", BASE_ID + 1005, ItemClassification.progression),
    ItemData("Animal Trap Permit", BASE_ID + 1006, ItemClassification.progression),
    ItemData("Armor Stand Permit", BASE_ID + 1007, ItemClassification.progression),
    ItemData("Barrel Permit", BASE_ID + 1008, ItemClassification.progression),
    ItemData("Bin Permit", BASE_ID + 1009, ItemClassification.progression),
    ItemData("Bookcase Permit", BASE_ID + 1010, ItemClassification.progression),
    ItemData("Bucket Permit", BASE_ID + 1011, ItemClassification.progression),
    ItemData("Buckler Permit", BASE_ID + 1012, ItemClassification.progression),
    ItemData("Cabinet Permit", BASE_ID + 1013, ItemClassification.progression),
    ItemData("Cage Permit", BASE_ID + 1014, ItemClassification.progression),
    ItemData("Burial Container Permit", BASE_ID + 1015, ItemClassification.progression),
    ItemData("Chair Permit", BASE_ID + 1016, ItemClassification.progression),
    ItemData("Container Permit", BASE_ID + 1017, ItemClassification.progression),
    ItemData("Crutch Permit", BASE_ID + 1018, ItemClassification.progression),
    ItemData("Door Permit", BASE_ID + 1019, ItemClassification.progression),
    ItemData("Floodgate Permit", BASE_ID + 1020, ItemClassification.progression),
    ItemData("Grate Permit", BASE_ID + 1021, ItemClassification.progression),
    ItemData("Hatch Cover Permit", BASE_ID + 1022, ItemClassification.progression),
    ItemData("Minecart Permit", BASE_ID + 1023, ItemClassification.progression),
    ItemData("Pedestal Permit", BASE_ID + 1024, ItemClassification.progression),
    ItemData("Pipe Section Permit", BASE_ID + 1025, ItemClassification.progression),
    ItemData("Shield Permit", BASE_ID + 1026, ItemClassification.progression),
    ItemData("Splint Permit", BASE_ID + 1027, ItemClassification.progression),
    ItemData("Stepladder Permit", BASE_ID + 1028, ItemClassification.progression),
    ItemData("Table Permit", BASE_ID + 1029, ItemClassification.progression),
    ItemData("Training Axe Permit", BASE_ID + 1030, ItemClassification.progression),
    ItemData("Training Spear Permit", BASE_ID + 1031, ItemClassification.progression),
    ItemData("Training Sword Permit", BASE_ID + 1032, ItemClassification.progression),
    ItemData("Weapon Rack Permit", BASE_ID + 1033, ItemClassification.progression),
    ItemData("Wheelbarrow Permit", BASE_ID + 1034, ItemClassification.progression),
    ItemData("Crossbow Permit", BASE_ID + 1035, ItemClassification.progression),
    ItemData("Bolt Permit", BASE_ID + 1036, ItemClassification.progression),
    ItemData("Millstone Permit", BASE_ID + 1037, ItemClassification.progression),
    ItemData("Quern Permit", BASE_ID + 1038, ItemClassification.progression),
    ItemData("Slab Permit", BASE_ID + 1039, ItemClassification.progression),
    ItemData("Statue Permit", BASE_ID + 1040, ItemClassification.progression),
    ItemData("Mechanism Permit", BASE_ID + 1041, ItemClassification.progression),
    ItemData("Traction Bench Permit", BASE_ID + 1042, ItemClassification.progression),
    ItemData("Crafts Permit", BASE_ID + 1043, ItemClassification.progression),
    ItemData("Liquid Container Permit", BASE_ID + 1044, ItemClassification.progression),
    ItemData("Cup Permit", BASE_ID + 1045, ItemClassification.progression),
    ItemData("Toy Permit", BASE_ID + 1046, ItemClassification.progression),
    ItemData("Totem Permit", BASE_ID + 1047, ItemClassification.progression),
    ItemData("Helm Permit", BASE_ID + 1048, ItemClassification.progression),
    ItemData("Ballista Parts Permit", BASE_ID + 1049, ItemClassification.progression),
    ItemData("Catapult Parts Permit", BASE_ID + 1050, ItemClassification.progression),
    ItemData("Ballista Arrows Permit", BASE_ID + 1051, ItemClassification.progression),
    ItemData("Ash Permit", BASE_ID + 1052, ItemClassification.progression),
    ItemData("Charcoal Permit", BASE_ID + 1053, ItemClassification.progression),
    ItemData("Metal Bars Permit", BASE_ID + 1054, ItemClassification.progression),
    ItemData("Coke Bars Permit", BASE_ID + 1055, ItemClassification.progression),
    ItemData("Pearlash Permit", BASE_ID + 1056, ItemClassification.progression),
    ItemData("Gypsum Plaster Permit", BASE_ID + 1057, ItemClassification.progression),
    ItemData("Jug Permit", BASE_ID + 1058, ItemClassification.progression),
    ItemData("Large Pot Permit", BASE_ID + 1059, ItemClassification.progression),
    ItemData("Hive Permit", BASE_ID + 1060, ItemClassification.progression),
    ItemData("Quicklime Permit", BASE_ID + 1061, ItemClassification.progression),
    ItemData("Glass Permit", BASE_ID + 1062, ItemClassification.progression),
    ItemData("Window Permit", BASE_ID + 1063, ItemClassification.progression),
    ItemData("Book Binding Permit", BASE_ID + 1064, ItemClassification.progression),
    ItemData("Scroll Roller Permit", BASE_ID + 1065, ItemClassification.progression),
    ItemData("Leather Permit", BASE_ID + 1066, ItemClassification.progression),
    ItemData("Sheet Permit", BASE_ID + 1067, ItemClassification.progression),
    ItemData("Cloth Permit", BASE_ID + 1068, ItemClassification.progression),
    ItemData("Alcohol Permit", BASE_ID + 1069, ItemClassification.progression),
    ItemData("Lye Permit", BASE_ID + 1070, ItemClassification.progression),
    ItemData("Potash Permit", BASE_ID + 1071, ItemClassification.progression),
    ItemData("Milk of Lime Permit", BASE_ID + 1072, ItemClassification.progression),
    ItemData("Prepared Meal Permit", BASE_ID + 1073, ItemClassification.progression),
    ItemData("Tallow Permit", BASE_ID + 1074, ItemClassification.progression),
    ItemData("Oil Permit", BASE_ID + 1075, ItemClassification.progression),
    ItemData("Honey Permit", BASE_ID + 1076, ItemClassification.progression),
    ItemData("Headgear Clothing Permit", BASE_ID + 1077, ItemClassification.progression),
    ItemData("Upper Body Clothing Permit", BASE_ID + 1078, ItemClassification.progression),
    ItemData("Upper Body Armor Permit", BASE_ID + 1079, ItemClassification.progression),
    ItemData("Hand Clothing Permit", BASE_ID + 1080, ItemClassification.progression),
    ItemData("Gauntlets Permit", BASE_ID + 1081, ItemClassification.progression),
    ItemData("Lower Body Clothing Permit", BASE_ID + 1082, ItemClassification.progression),
    ItemData("Lower Body Armor Permit", BASE_ID + 1083, ItemClassification.progression),
    ItemData("Footwear Permit", BASE_ID + 1084, ItemClassification.progression),
    ItemData("Dye Permit", BASE_ID + 1085, ItemClassification.progression),
    ItemData("Bag Permit", BASE_ID + 1086, ItemClassification.progression),
    ItemData("Rope/Chain Permit", BASE_ID + 1087, ItemClassification.progression),
    ItemData("Battle Axe Permit", BASE_ID + 1088, ItemClassification.progression),
    ItemData("Mace Permit", BASE_ID + 1089, ItemClassification.progression),
    ItemData("Pick Permit", BASE_ID + 1090, ItemClassification.progression),
    ItemData("Short Sword Permit", BASE_ID + 1091, ItemClassification.progression),
    ItemData("Spear Permit", BASE_ID + 1092, ItemClassification.progression),
    ItemData("War Hammer Permit", BASE_ID + 1093, ItemClassification.progression),
    ItemData("Anvil Permit", BASE_ID + 1094, ItemClassification.progression),
    ItemData("Coins Permit", BASE_ID + 1095, ItemClassification.progression),
    ItemData("Soap Permit", BASE_ID + 1096, ItemClassification.progression),
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
    ItemData("Catsplosion",            BASE_ID + 625, ItemClassification.trap),
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
