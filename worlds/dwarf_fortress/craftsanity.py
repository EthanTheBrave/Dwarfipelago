import math
import re
from typing import List, Set, Union, TYPE_CHECKING
from dataclasses import dataclass
from BaseClasses import ItemClassification, Location, LocationProgressType, CollectionState
from worlds.generic.Rules import set_rule
from .options import EnableCraftsanity, CraftsanityDifficulty, CraftsanityItems, CraftsanityMaterials
from .locations import BASE_ID, LocationData

if TYPE_CHECKING:
    from . import DwarfFortressWorld


# ── Deterministic craft-location id scheme ────────────────────────────────────
# Every craft check id is computed directly from (item, material, tier), so the
# id is STABLE regardless of the yaml material order or Python set-iteration
# order. This replaces the old static crafting_locations.py table, which drifted
# out of sync with the per-slot generation and caused id collisions (a wooden
# table check could land on a stone table's id).
#
#   id = BASE_ID + assign_locationid_block(item) + MATERIAL_SLOT * STRIDE + tier
#
# tier 0 is reserved for the "Final Check"; numbered "Check N" use tier N.
# Item blocks are spaced 2000 apart; the worst case is slot 8 (Ceramic) at
# 8*100 + 99 = 899, so every variant fits inside its item's block.
CRAFT_TIER_STRIDE = 100
CRAFT_MAX_NUMBERED = 99  # Check 1..99 (must stay < CRAFT_TIER_STRIDE)

# Fixed, canonical slot per material. The no-material variant is slot 0. These
# indices must never be reordered once seeds exist, or ids would shift.
MATERIAL_SLOTS: dict[str, int] = {
    "":        0,
    "Stone":   1,
    "Wood":    2,
    "Metal":   3,
    "Glass":   4,
    "Leather": 5,
    "Cloth":   6,
    "Bone":    7,
    "Ceramic": 8,
    "Adamantine": 9
}


def craft_check_name(item: str, material: str, tier: int, is_final: bool) -> str:
    prefix = "Crafting " + (material + " " if material else "") + item
    return prefix + (" Final Check" if is_final else " Check " + str(tier))


def craft_location_id(item: str, material: str, tier: int) -> int:
    return BASE_ID + assign_locationid_block(item) + MATERIAL_SLOTS[material] * CRAFT_TIER_STRIDE + tier


def build_craft_location_table() -> dict:
    """Full name->id registry for every possible craft check.

    The single source of truth for craft-location ids: the World's
    location_name_to_id (the AP DataPackage) and the per-slot generation in
    loop_locations both derive ids from craft_location_id(), so they can never
    drift apart. Includes the no-material variant for every item (used when
    materials are disabled) plus each valid material variant.
    """
    table: dict = {}

    def add_variant(item: str, material: str) -> None:
        table[craft_check_name(item, material, 0, True)] = craft_location_id(item, material, 0)
        for n in range(1, CRAFT_MAX_NUMBERED + 1):
            table[craft_check_name(item, material, n, False)] = craft_location_id(item, material, n)

    for item in CraftsanityItems.valid_keys:
        add_variant(item, "")
        if not non_material_items(item):
            for material in CraftsanityMaterials.valid_keys:
                if material in MATERIAL_SLOTS and valid_materialitem(material, item):
                    add_variant(item, material)
    return table


CRAFTSANITY_EASY: set = {
    "Beds", "Blocks", "Alcohol", "Chair", "Table", "Door",
    "Barrel", "Bucket", "Container", "Cloth",
}

CRAFTSANITY_MEDIUM: set = CRAFTSANITY_EASY | {
    "Crafts", "Mechanism", "Cage", "Leather", "Prepared Meal",
    "Bin", "Cabinet", "Floodgate", "Animal Trap", "Statue",
    "Armor Stand", "Pedestal", "Weapon Rack", "Corkscrew", "Bookcase",
}

CRAFTSANITY_HARD: set = CRAFTSANITY_MEDIUM | {
    "Metal Bars", "Glass", "Ash", "Charcoal", "Helm",
    "Cap", "Mail Shirt", "Breastplate", "Leather Armor",
    "Gauntlets", "Leggings", "Greaves", "Low Boots", "High Boots",
    "Crossbow", "Bolt", "Battle Axe", "Short Sword",
    "War Hammer", "Anvil", "Rope/Chain", "Coins", "Goblet",
    "Tallow", "Oil", "Dye", "Traction Bench", "Shield", "Buckler"
}


@dataclass
class DynamicCraftingData:
    check_name: str  # Name of the Check
    item_name: str
    type: str # Item Material
    id: int # Next number of check
    max_id: int # Max number of checks
    base_location_id: int = BASE_ID

def _craftsanity_items_for_group(world: "DwarfFortressWorld") -> set:
    group = world.options.craftsanity_difficulty
    if group == CraftsanityDifficulty.option_easy:
        return CRAFTSANITY_EASY
    elif group == CraftsanityDifficulty.option_medium:
        return CRAFTSANITY_MEDIUM
    elif group == CraftsanityDifficulty.option_hard:
        return CRAFTSANITY_HARD
    elif group == CraftsanityDifficulty.option_craftsanity:
        return CraftsanityItems.valid_keys
    else:  # option_choose
        return set(world.options.craftsanity_items)


def generate_location_data(world: "DwarfFortressWorld"):
    dynamic_locations: list[LocationData] = []
    if world.options.craftsanity != EnableCraftsanity.option_off:
        for item in _craftsanity_items_for_group(world):
            new_location = DynamicCraftingData("", "", "", 0, 0, BASE_ID)
            new_location.item_name = item
            new_location.id = 0
            new_location.base_location_id += assign_locationid_block(new_location.item_name)
            loop_locations(world, new_location, dynamic_locations)

def loop_locations(world: "DwarfFortressWorld", new_location: DynamicCraftingData, dynamic_locations: list[LocationData]) -> int:
    item = new_location.item_name
    max_id = calulate_check_count(world)

    def emit(material: str) -> None:
        # next_id runs 0..max_id-1; the last one is the Final Check (tier 0),
        # the rest are numbered "Check N" (tier N). Ids come straight from the
        # deterministic formula, so iteration order no longer affects them.
        for next_id in range(0, max_id):
            is_final = (next_id == max_id - 1)
            tier = 0 if is_final else next_id + 1
            name = craft_check_name(item, material, tier, is_final)
            loc_id = craft_location_id(item, material, tier)
            world.dynamic_locations.append(
                LocationData(name, loc_id, "", False, material, item, next_id + 1))
            world.dynamic_locations_names.append(name)

    if world.options.craftsanity_enable_materials and not non_material_items(item):
        for material in world.options.craftsanity_materials:  # player-selected materials
            if material in MATERIAL_SLOTS and valid_materialitem(material, item):
                emit(material)
    else:  # material doesn't matter
        emit("")
    return

def calulate_check_count(world: "DwarfFortressWorld"):
    if world.options.craftsanity_threshold >= world.options.craftsanity_max_amount:
        return 1
    else:
        checks = math.ceil(world.options.craftsanity_max_amount / world.options.craftsanity_threshold)
        return checks
    
def valid_materialitem(material: str, item: str) -> bool:
    if material in {"Wood", "Metal", "Adamantine"} and item in {"Animal Trap", "Barrel", "Bin", "Bucket", "Crutch", "Minecart", "Splint", "Stepladder", "Wheelbarrow", "Ballista Arrows"}:
        return True
    if material in {"Wood", "Metal", "Glass", "Adamantine"} and item in {"Menacing Spike", "Cage", "Spiked Ball", "Pipe Section", "Corkscrew"}:
        return True
    if material in {"Wood", "Metal", "Leather", "Adamantine"} and item in {"Buckler", "Shield"}:
        return True
    if material in {"Wood", "Stone", "Metal", "Glass", "Adamantine"} and item in {"Altar", "Armor Stand", "Bookcase", "Cabinet", "Burial Container", "Chair", "Container", "Door", "Floodgate", "Grate", "Hatch Cover", "Pedestal", "Table", "Weapon Rack", "Traction Bench", "Toy", "Book Binding", "Scroll Roller"}:
        return True
    if material in {"Wood", "Stone", "Metal", "Glass", "Ceramic", "Adamantine"} and item in {"Blocks", "Jug", "Large Pot", "Hive"}:
        return True
    if material in {"Wood", "Stone", "Bone", "Cloth", "Leather", "Metal", "Adamantine"} and item in {"Amulet", "Bracelet", "Earring"}:
        return True
    if material in {"Wood", "Stone", "Bone", "Metal", "Adamantine"} and item in {"Crown", "Figurine", "Ring", "Scepter"}:
        return True
    if material in {"Wood", "Stone", "Bone", "Metal", "Glass", "Adamantine"} and item in {"Die", "Nest Box"}:
        return True
    if material in {"Wood", "Stone", "Metal", "Glass", "Bone", "Cloth", "Ceramic", "Leather", "Adamantine"} and item in {"Crafts"}:
        return True
    if material in {"Wood", "Bone", "Metal", "Adamantine"} and item in {"Crossbow", "Bolt"}:
        return True
    if material in {"Stone", "Metal", "Glass", "Ceramic", "Adamantine"} and item in {"Statue"}:
        return True
    if material in {"Stone", "Metal", "Adamantine"} and item in {"Mechanism"}:
        return True
    if material in {"Leather", "Metal", "Glass", "Adamantine"} and item in {"Liquid Container"}:
        return True
    if material in {"Metal", "Glass", "Adamantine"} and item in {"Goblet", "Giant Axe Blade", "Serrated Disc"}:
        return True
    if material in {"Bone", "Metal", "Adamantine"} and item in {"Gauntlets", "Greaves"}:
        return True
    if material in {"Leather", "Bone", "Metal", "Adamantine"} and item in {"Helm", "Leggings"}:
        return True
    if material in {"Leather", "Cloth", "Adamantine"} and item in {"Bag", "Hood", "Shirt", "Gloves", "Mittens", "Loincloth", "Trousers", "Shoes", "Tunic", "Dress", "Toga", "Robe", "Braies", "Cloak", "Coat", "Vest"}:
        return True
    if material in {"Leather", "Cloth", "Adamantine"} and item in {"Backpack", "Quiver"}:
        return True
    if material in {"Leather", "Metal", "Adamantine"} and item in {"Low Boots", "High Boots"}:
        return True
    if material in {"Leather", "Cloth", "Metal", "Adamantine"} and item in {"Cap"}:
        return True
    if material in {"Cloth", "Metal", "Adamantine"} and item == "Rope/Chain":
        return True
    if material in {"Metal", "Adamantine"} and item in {"Mail Shirt", "Breastplate", "Battle Axe", "Mace", "Pick", "Short Sword", "Spear", "War Hammer", "Anvil", "Coins",}:
        return True
    if material in {"Cloth", "Adamantine"} and item in {"Socks", "Breastplate"}:
        return True
    return False

def non_material_items(item: str) -> bool:
    if item in {"Beds", "Ash", "Charcoal", "Metal Bars", "Coke Bars", "Pearlash", "Gypsum Plaster", "Quicklime",
        "Glass", "Leather", "Sheet", "Cloth", "Alcohol", "Lye", "Potash", "Milk of Lime", "Prepared Meal", "Tallow",
        "Oil", "Press Cake", "Honey", "Bee Wax", "Dye", "Soap", "Training Axe", "Training Spear", "Training Sword",
        "Cup", "Ballista Parts", "Catapult Parts", "Millstone", "Quern", "Slab", "Mug", "Totem", "Window", 
         "Display Case", "Bolt Thrower Parts", "Codex", "Quire", "Scroll", "Leather Armor"}:
        return True
    return False

def assign_locationid_block(item: str) -> int:
    match item:
        case "Beds": return 100000  #20 Checks Max
        case "Corkscrew": return 102000 #60
        case "Blocks": return  104000 #100
        case "Menacing Spike": return 106000 #60
        case "Spiked Ball": return 108000 #60 
        case "Altar": return 110000
        case "Animal Trap": return 112000
        case "Armor Stand": return 114000
        case "Barrel": return 116000
        case "Bin": return 118000
        case "Bookcase": return 120000
        case "Bucket": return 122000
        case "Buckler": return 124000
        case "Cabinet": return 126000
        case "Cage": return 128000
        case "Burial Container": return 130000
        case "Chair": return 132000
        case "Container": return 134000
        case "Crutch": return 136000
        case "Door": return 138000
        case "Floodgate": return 140000
        case "Grate": return 142000
        case "Hatch Cover": return 144000
        case "Minecart": return 146000
        case "Pedestal": return 148000
        case "Pipe Section": return 150000
        case "Shield": return 152000
        case "Splint": return 154000
        case "Stepladder": return 156000
        case "Table": return 158000
        case "Training Axe": return 160000
        case "Training Spear": return 162000
        case "Training Sword": return 164000
        case "Weapon Rack": return 166000
        case "Wheelbarrow": return 168000
        case "Crossbow": return 170000
        case "Bolt": return 172000
        case "Millstone": return 174000
        case "Quern": return 176000
        case "Slab": return 178000
        case "Statue": return 180000
        case "Mechanism": return 182000
        case "Traction Bench": return 184000
        case "Crafts": return 186000
        case "Liquid Container": return 188000
        case "Goblet": return 190000
        case "Mug": return 192000
        case "Cup": return 194000
        case "Toy": return 196000
        case "Totem": return 198000
        case "Gauntlets": return 200000
        case "Helm": return 202000
        case "Ballista Parts": return 204000
        case "Catapult Parts": return 206000
        case "Ballista Arrows": return 208000
        case "Ash": return 210000
        case "Charcoal": return 212000
        case "Metal Bars": return 214000
        case "Coke Bars": return 216000
        case "Pearlash": return 218000
        case "Gypsum Plaster": return 220000
        case "Jug": return 222000
        case "Large Pot": return 224000
        case "Hive": return 226000
        case "Quicklime": return 228000
        case "Glass": return 230000
        case "Window": return 232000
        case "Book Binding": return 234000
        case "Scroll Roller": return 236000
        case "Leather": return 238000
        case "Sheet": return 240000
        case "Cloth": return 242000
        case "Alcohol": return 244000
        case "Lye": return 246000
        case "Potash": return 248000
        case "Milk of Lime": return 250000
        case "Prepared Meal": return 252000
        case "Tallow": return 254000
        case "Oil": return 256000
        case "Press Cake": return 258000
        case "Honey": return 260000
        case "Bee Wax": return 262000
        case "Cap": return 264000
        case "Hood": return 266000
        case "Shirt": return 268000
        case "Vest": return 270000
        case "Coat": return 272000
        case "Cloak": return 274000
        case "Leather Armor": return 276000
        case "Dye": return 278000
        case "Bag": return 280000
        case "Rope/Chain": return 282000
        case "Battle Axe": return 284000
        case "Mace": return 286000
        case "Pick": return 288000
        case "Short Sword": return 290000
        case "Spear": return 292000
        case "War Hammer": return 294000
        case "Anvil": return 296000
        case "Coins": return 298000
        case "Soap": return 300000
        case "Display Case": return 302000
        case "Backpack": return 304000
        case "Quiver": return 308000
        case "Bolt Thrower Parts": return 310000
        case "Amulet": return 312000
        case "Bracelet": return 314000
        case "Crown": return 316000
        case "Die": return 318000
        case "Earring": return 320000
        case "Figurine": return 322000
        case "Nest Box": return 324000
        case "Ring": return 326000
        case "Scepter": return 328000
        case "Quire": return 330000
        case "Scroll": return 332000
        case "Mail Shirt": return 334000
        case "Breastplate": return 336000
        case "Gloves": return 338000
        case "Mittens": return 340000
        case "Loincloth": return 342000
        case "Trousers": return 344000
        case "Leggings": return 346000
        case "Greaves": return 348000
        case "Socks": return 350000
        case "Shoes": return 352000
        case "Low Boots": return 354000
        case "High Boots": return 356000
        case "Giant Axe Blade": return 358000
        case "Serrated Disc": return 360000
        case "Codex": return 362000
        case "Tunic": return 364000
        case "Dress": return 366000
        case "Toga": return 368000
        case "Robe": return 370000
        case "Braies": return 372000
    print("Missing entry: "+item)
    return 0
