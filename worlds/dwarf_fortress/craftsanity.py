import math
import re
from typing import List, Set, Union, TYPE_CHECKING
from dataclasses import dataclass
from BaseClasses import ItemClassification, Location, LocationProgressType, CollectionState
from worlds.generic.Rules import set_rule
from .options import EnableCraftsanity, CraftsanityItemGroup, CraftsanityItems, CraftsanityMaterials, CraftingItems
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
    "Upper Body Armor", "Gauntlets", "Lower Body Armor",
    "Crossbow", "Bolt", "Battle Axe", "Short Sword",
    "War Hammer", "Anvil", "Rope/Chain", "Coins", "Goblet",
    "Tallow", "Oil", "Dye", "Traction Bench"
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
    group = world.options.craftsanity_item_group
    if group == CraftsanityItemGroup.option_easy:
        return CRAFTSANITY_EASY
    elif group == CraftsanityItemGroup.option_medium:
        return CRAFTSANITY_MEDIUM
    elif group == CraftsanityItemGroup.option_hard:
        return CRAFTSANITY_HARD
    elif group == CraftsanityItemGroup.option_craftsanity:
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
    if material == "Wood" and item in {"Training Axe", "Training Spear", "Training Sword", "Cup", "Ballista Parts", "Catapult Parts"}:
        return True
    if material in {"Wood", "Metal"} and item in {"Animal Trap", "Barrel", "Bin", "Bucket", "Crutch", "Minecart", "Splint", "Stepladder", "Wheelbarrow", "Ballista Arrows", "Corkscrew"}:
        return True
    if material in {"Wood", "Metal", "Glass"} and item in {"Spike", "Cage", "Ball", "Pipe Section"}:
        return True
    if material in {"Wood", "Metal", "Leather"} and item in {"Buckler", "Shield"}:
        return True
    if material in {"Wood", "Stone", "Metal", "Glass"} and item in {"Altar", "Armor Stand", "Bookcase", "Cabinet", "Burial Container", "Chair", "Container", "Door", "Floodgate", "Grate", "Hatch Cover", "Pedestal", "Table", "Weapon Rack", "Traction Bench", "Crafts", "Toy", "Book Binding", "Scroll Roller"}:
        return True
    if material in {"Wood", "Stone", "Metal", "Glass", "Ceramic"} and item in {"Blocks", "Jug", "Large Pot", "Hive"}:
        return True
    if material in {"Wood", "Bone", "Metal"} and item in {"Crossbow", "Bolt"}:
        return True
    if material == "Stone" and item in {"Millstone", "Quern", "Slab", "Mug"}:
        return True
    if material in {"Stone", "Metal", "Glass", "Ceramic"} and item in {"Statue"}:
        return True
    if material in {"Stone", "Metal"} and item in {"Mechanism"}:
        return True
    if material in {"Leather", "Metal", "Glass"} and item in {"Liquid Container"}:
        return True
    if material in {"Metal", "Glass"} and item == "Goblet":
        return True
    if material == "Bone" and item == "Totem":
        return True
    if material in {"Bone", "Metal"} and item == "Gauntlets":
        return True
    if material in {"Leather", "Bone", "Metal"} and item == "Helm":
        return True
    if material in {"Bone", "Leather", "Metal"} and item == "Lower Body Armor":
        return True
    if material == "Glass" and item == "Window":
        return True
    if material in {"Leather", "Cloth"} and item in {"Headgear Clothing", "Upper Body Clothing", "Hand Clothing", "Lower Body Clothing", "Bag"}:
        return True
    if material in {"Leather", "Metal"} and item in {"Upper Body Armor"}:
        return True
    if material in {"Leather", "Cloth", "Leather"} and item == "Footwear":
        return True
    if material in {"Cloth", "Metal"} and item == "Rope/Chain":
        return True
    if material == "Metal" and item in {"Battle Axe", "Mace", "Pick", "Short Sword", "Spear", "War Hammer", "Anvil", "Coins"}:
        return True
    return False

def non_material_items(item: str) -> bool:
    if item in {"Beds", "Ash", "Charcoal", "Metal Bars", "Coke Bars", "Pearlash", "Gypsum Plaster", "Quicklime", "Glass", "Leather", "Sheet", "Cloth", "Alcohol", "Lye", "Potash", "Milk of Lime", "Prepared Meal", "Tallow", "Oil", "Press Cake", "Honey", "Bee Wax", "Dye", "Soap"}:
        return True
    return False
    
class DynamicCraftingLocationRules:
    world: "DwarfFortressWorld"

    def __init__(self, world: "DwarfFortressWorld") -> None:
        self.player = world.player
        self.world = world
            

    def wood(self, state:CollectionState) -> bool:
        return state.has("Carpenter's Workshop Blueprint", self.player)
    
    def metal(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return state.has("Forge Blueprint", self.player) or state.has("Magma Smelter Blueprint", self.player)
        else:
            return self.process_resource(state, "metal") and (state.has("Forge Blueprint", self.player) or \
            state.has("Magma Forge Blueprint", self.player))
        
    def process_resource(self, state:CollectionState, resource) -> bool: #glass, metal, ceramic
        if resource == "metal":
            return (state.has("Wood Furnace Blueprint", self.player) and state.has("Forge Blueprint", self.player)) or \
            state.has("Magma Smelter Blueprint", self.player)
        elif resource == "glass":
            return (state.has("Wood Furnace Blueprint", self.player) and state.has("Glass Furnace Blueprint", self.player)) or \
            state.has("Magma Glass Furnace Blueprint", self.player)
        elif resource == "ceramic":
            return (state.has("Wood Furnace Blueprint", self.player) and state.has("Kiln Blueprint", self.player)) or \
            state.has("Magma Kiln Blueprint", self.player)
        else:
            print("Missing Resource Type for process_resource function")
            return False
        
    def make_metal(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return True
        else:
            return self.process_resource(state, "metal")
        
    def needs_make_metal(self, state:CollectionState) -> bool:
        return self.process_resource(state, "metal")
        
    def ceramic(self, state:CollectionState) -> bool:
        return self.process_resource(state, "ceramic")
    
    def glass(self, state:CollectionState) -> bool:
        return self.process_resource(state, "glass")
    
    def stone(self, state:CollectionState) -> bool:
        return state.has("Stoneworker's Workshop Blueprint", self.player)
    
    def leather(self, state:CollectionState) -> bool:
        return state.has("Tanner's Blueprint", self.player)

    def leather_works(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return state.has("Leather Works Blueprint", self.player)
        else:
            return self.leather(state) and state.has("Leather Works Blueprint", self.player)
    
    def cloth(self, state:CollectionState) -> bool:
        return state.has("Loom Blueprint", self.player)
    
    def clothier_workshop(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return state.has("Clothier's Shop Blueprint", self.player)
        else:
            return self.cloth(state) and state.has("Clothier's Shop Blueprint", self.player)
        
    def wood_or_metal(self, state:CollectionState) -> bool:
        return self.wood(state) or self.metal(state)
    
    def wood_or_metal_or_glass(self, state:CollectionState) -> bool:
        return self.wood(state) or self.metal(state) or self.glass(state)
    
    def wood_or_stone_or_metal_or_glass(self, state:CollectionState) -> bool:
        return self.wood(state) or self.stone(state) or self.metal(state) or self.glass(state)
    
    def wood_or_stone_or_metal_or_glass_or_ceramic(self, state:CollectionState) -> bool:
        return self.wood(state) or self.stone(state) or self.metal(state) or self.glass(state) or self.ceramic(state)
    
    def wood_or_leather_or_metal(self, state:CollectionState) -> bool:
        return self.wood(state) or self.leather_works(state) or self.metal(state) 
    
    def bowyer_workshop(self, state:CollectionState) -> bool:
        return state.has("Bowyer's Workshop Blueprint", self.player)
    
    def craftdwarf_workshop(self, state:CollectionState) -> bool:
        return state.has("Craftsdwarf's Workshop Blueprint", self.player)
    
    def mechanic_workshop(self, state:CollectionState) -> bool:
        return state.has("Mechanic's Workshop Blueprint", self.player)
    
    def butcher_workshop(self, state:CollectionState) -> bool:
        return state.has("Butcher's Shop Blueprint", self.player)
    
    def famer_workshop(self, state:CollectionState) -> bool:
        return state.has("Farmer's Workshop Blueprint", self.player)
    
    def seige_workshop(self, state:CollectionState) -> bool:
        return state.has("Siege Workshop Blueprint", self.player)
    
    def wood_furnace(self, state:CollectionState) -> bool:
        return state.has("Wood Furnace Blueprint", self.player)
    
    def screw_press(self, state:CollectionState) -> bool:
        return state.has("Screw Press Blueprint", self.player)
    
    def still(self, state:CollectionState) -> bool:
        return state.has("Still Blueprint", self.player)
    
    def ashery(self, state:CollectionState) -> bool:
        return state.has("Ashery Blueprint", self.player)
    
    def kitchen(self, state:CollectionState) -> bool:
        return state.has("Kitchen Blueprint", self.player)
    
    def kitchen_and_butchershop(self, state:CollectionState) -> bool:
        return self.kitchen(state) and self.butcher_workshop(state)
    
    def seige_and_metal(self, state:CollectionState) -> bool:
        return self.seige_workshop(state) and self.metal(state)

    def bowyer_or_metal(self, state:CollectionState) -> bool:
        return self.metal(state) or self.bowyer_workshop(state) 
    
    def craftdwarf_or_metal(self, state:CollectionState) -> bool:
        return self.metal(state) or self.craftdwarf_workshop(state) 
    
    def craftdwarf_and_butchery(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and self.butcher_workshop(state)
    
    def wooden_traction_bench(self, state:CollectionState) -> bool:
        return self.wood(state) and self.mechanic_workshop(state) and \
        (self.metal(state) or self.clothier_workshop(state))
    
    def stone_traction_bench(self, state:CollectionState) -> bool:
        return self.stone(state) and self.mechanic_workshop(state) and \
        (self.metal(state) or self.clothier_workshop(state))
    
    def metal_traction_bench(self, state:CollectionState) -> bool:
        return self.metal(state) and self.mechanic_workshop(state)
    
    def glass_traction_bench(self, state:CollectionState) -> bool:
        return self.glass(state) and self.mechanic_workshop(state) and \
        (self.metal(state) or self.clothier_workshop(state))
    
    def any_traction_bench(self, state:CollectionState) -> bool:
        return (self.glass(state) or self.metal(state) or self.wood(state) or self.stone(state)) \
        and self.mechanic_workshop(state) and (self.metal(state) or self.clothier_workshop(state))
    
    def metal_or_glass_or_leather(self, state:CollectionState) -> bool:
        return self.metal(state) or self.glass(state) or self.leather_works(state)
    
    def metal_or_glass(self, state:CollectionState) -> bool:
        return self.metal(state) or self.glass(state)
    
    def metal_or_leather(self, state:CollectionState) -> bool:
        return self.metal(state) or self.leather_works(state)
    
    def metal_or_bone(self, state:CollectionState) -> bool:
        return self.metal(state) or self.craftdwarf_workshop(state)
    
    def metal_or_cloth(self, state:CollectionState) -> bool:
        return self.metal(state) or self.clothier_workshop(state)

    def metal_or_bone_or_leather(self, state:CollectionState) -> bool:
        return self.metal(state) or self.leather_works(state) or self.craftdwarf_workshop(state)
    
    def metal_or_cloth_or_leather(self, state:CollectionState) -> bool:
        return self.metal(state) or self.leather_works(state) or self.clothier_workshop(state)
    
    def make_paper(self, state:CollectionState) -> bool:
        return self.famer_workshop(state) or self.screw_press(state) or self.leather(state)
    
    def ashery_and_wood_furnace(self, state:CollectionState) -> bool:
        return self.ashery(state) and self.wood_furnace(state)
    
    def ashery_and_kiln(self, state:CollectionState) -> bool:
        return self.ashery(state) and self.ceramic(state)
    
    def leather_or_cloth(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) or self.leather_works(state)
    
    def dye(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return state.has("Dyer's Workshop Blueprint", self.player)
        else:
            return self.cloth(state) and state.has("Dyer's Workshop Blueprint", self.player)
        
    def soap(self, state:CollectionState) -> bool:
        return self.ashery(state) and self.wood_furnace(state) \
            and state.has("Soap Maker's Workshop Blueprint", self.player) \
            and (self.kitchen(state) and self.butcher_workshop(state) or self.screw_press(state))
    
    def bed(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Beds", self.player)
    
    def training_axe(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Training Axe", self.player)
    def training_spear(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Training Spear", self.player)
    def training_sword(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Training Sword", self.player)
    
    def wood_corkscrew(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Corkscrew", self.player)
    def metal_corkscrew(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Corkscrew", self.player)
    def wood_or_metal_corkscrew(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Corkscrew", self.player)

    def wood_spike(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Spike", self.player)
    def metal_spike(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Spike", self.player)
    def wood_or_metal_spike(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Spike", self.player)

    def wood_ball(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Ball", self.player)
    def metal_ball(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Ball", self.player)
    def wood_or_metal_ball(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Ball", self.player)

    def wood_animal_trap(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Animal Trap", self.player)
    def metal_animal_trap(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Animal Trap", self.player)
    def wood_or_metal_animal_trap(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Animal Trap", self.player)
    
    def wood_barrel(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Barrel", self.player)
    def metal_barrel(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Barrel", self.player)
    def wood_or_metal_barrel(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Barrel", self.player)
    
    def wood_bin(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Bin", self.player)
    def metal_bin(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Bin", self.player)
    def wood_or_metal_bin(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Bin", self.player)

    def wood_bucket(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Bucket", self.player)
    def metal_bucket(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Bucket", self.player)
    def wood_or_metal_bucket(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Bucket", self.player)

    def wood_crutch(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Crutch", self.player)
    def metal_crutch(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Crutch", self.player)
    def wood_or_metal_crutch(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Crutch", self.player)

    def wood_minecart(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Minecart", self.player)
    def metal_minecart(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Minecart", self.player)
    def wood_or_metal_minecart(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Minecart", self.player)

    def wood_splint(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Splint", self.player)
    def metal_splint(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Splint", self.player)
    def wood_or_metal_splint(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Splint", self.player)
    
    def wood_stepladder(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Stepladder", self.player)
    def metal_stepladder(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Stepladder", self.player)
    def wood_or_metal_stepladder(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Stepladder", self.player)
    
    def wood_wheelbarrow(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Wheelbarrow", self.player)
    def metal_wheelbarrow(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Wheelbarrow", self.player)
    def wood_or_metal_wheelbarrow(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crafting Wheelbarrow", self.player)
    
    def wood_blocks(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Blocks", self.player)
    def stone_blocks(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Blocks", self.player)
    def metal_blocks(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Blocks", self.player)
    def glass_blocks(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Blocks", self.player)
    def ceramic_blocks(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Crafting Blocks", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_blocks(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Crafting Blocks", self.player)
    
    def wood_jug(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Jug", self.player)
    def stone_jug(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Jug", self.player)
    def metal_jug(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Jug", self.player)
    def glass_jug(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Jug", self.player)
    def ceramic_jug(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Crafting Jug", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_jug(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Crafting Jug", self.player)
    
    def wood_pot(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Large Pot", self.player)
    def stone_pot(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Large Pot", self.player)
    def metal_pot(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Large Pot", self.player)
    def glass_pot(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Large Pot", self.player)
    def ceramic_pot(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Crafting Large Pot", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_pot(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Crafting Large Pot", self.player)
    
    def wood_hive(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Hive", self.player)
    def stone_hive(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Hive", self.player)
    def metal_hive(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Hive", self.player)
    def glass_hive(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Hive", self.player)
    def ceramic_hive(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Crafting Hive", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_hive(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Crafting Hive", self.player)
    
    def wood_altar(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Altar", self.player)
    def stone_altar(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Altar", self.player)
    def metal_altar(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Altar", self.player)
    def glass_altar(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Altar", self.player)
    def wood_or_stone_or_metal_or_glass_altar(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Altar", self.player)
    
    def wood_armorstand(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Armor Stand", self.player)
    def stone_armorstand(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Armor Stand", self.player)
    def metal_armorstand(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Armor Stand", self.player)
    def glass_armorstand(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Armor Stand", self.player)
    def wood_or_stone_or_metal_or_glass_armorstand(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Armor Stand", self.player)
    
    def wood_bookcase(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Bookcase", self.player)
    def stone_bookcase(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Bookcase", self.player)
    def metal_bookcase(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Bookcase", self.player)
    def glass_bookcase(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Bookcase", self.player)
    def wood_or_stone_or_metal_or_glass_bookcase(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Bookcase", self.player)
    
    def wood_cabinet(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Cabinet", self.player)
    def stone_cabinet(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Cabinet", self.player)
    def metal_cabinet(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Cabinet", self.player)
    def glass_cabinet(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Cabinet", self.player)
    def wood_or_stone_or_metal_or_glass_cabinet(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Cabinet", self.player)
    
    def wood_burial(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Burial Container", self.player)
    def stone_burial(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Burial Container", self.player)
    def metal_burial(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Burial Container", self.player)
    def glass_burial(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Burial Container", self.player)
    def wood_or_stone_or_metal_or_glass_burial(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Burial Container", self.player)
    
    def wood_chair(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Chair", self.player)
    def stone_chair(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Chair", self.player)
    def metal_chair(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Chair", self.player)
    def glass_chair(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Chair", self.player)
    def wood_or_stone_or_metal_or_glass_chair(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Chair", self.player)
    
    def wood_container(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Container", self.player)
    def stone_container(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Container", self.player)
    def metal_container(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Container", self.player)
    def glass_container(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Container", self.player)
    def wood_or_stone_or_metal_or_glass_container(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Container", self.player)
    
    def wood_door(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Door", self.player)
    def stone_door(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Door", self.player)
    def metal_door(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Door", self.player)
    def glass_door(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Door", self.player)
    def wood_or_stone_or_metal_or_glass_door(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Door", self.player)
    
    def wood_floodgate(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Floodgate", self.player)
    def stone_floodgate(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Floodgate", self.player)
    def metal_floodgate(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Floodgate", self.player)
    def glass_floodgate(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Floodgate", self.player)
    def wood_or_stone_or_metal_or_glass_floodgate(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Floodgate", self.player)
    
    def wood_grate(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Grate", self.player)
    def stone_grate(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Grate", self.player)
    def metal_grate(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Grate", self.player)
    def glass_grate(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Grate", self.player)
    def wood_or_stone_or_metal_or_glass_grate(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Grate", self.player)
    
    def wood_hatchcover(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Hatch Cover", self.player)
    def stone_hatchcover(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Hatch Cover", self.player)
    def metal_hatchcover(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Hatch Cover", self.player)
    def glass_hatchcover(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Hatch Cover", self.player)
    def wood_or_stone_or_metal_or_glass_hatchcover(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Hatch Cover", self.player)

    def wood_pedestal(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Pedestal", self.player)
    def stone_pedestal(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Pedestal", self.player)
    def metal_pedestal(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Pedestal", self.player)
    def glass_pedestal(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Pedestal", self.player)
    def wood_or_stone_or_metal_or_glass_pedestal(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Pedestal", self.player)
    
    def wood_table(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Table", self.player)
    def stone_table(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Table", self.player)
    def metal_table(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Table", self.player)
    def glass_table(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Table", self.player)
    def wood_or_stone_or_metal_or_glass_table(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Table", self.player)

    def wood_weaponrack(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Weapon Rack", self.player)
    def stone_weaponrack(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Weapon Rack", self.player)
    def metal_weaponrack(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Weapon Rack", self.player)
    def glass_weaponrack(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Weapon Rack", self.player)
    def wood_or_stone_or_metal_or_glass_weaponrack(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Weapon Rack", self.player)
    
    def wood_statue(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crafting Statue", self.player)
    def stone_statue(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Crafting Statue", self.player)
    def metal_statue(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crafting Statue", self.player)
    def glass_statue(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Crafting Statue", self.player)
    def wood_or_stone_or_metal_or_glass_statue(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Crafting Statue", self.player)

    def set_dynamic_rules(self) -> None:
        for location in self.world.dynamic_locations:
            self.world.multiworld
            loc = self.world.multiworld.get_location(location.name, self.player)
            match location.df_item:
                case "Beds": 
                    if self.world.options.craftsanity_items == CraftingItems.option_all:
                        set_rule(loc, self.bed)
                    else:
                        set_rule(loc, self.wood)
                case "Training Axe":
                    if self.world.options.craftsanity_items != CraftingItems.option_off:
                        set_rule(loc, self.training_axe)
                    else:
                        set_rule(loc, self.wood)
                case "Training Spear":
                    if self.world.options.craftsanity_items != CraftingItems.option_off:
                        set_rule(loc, self.training_spear)
                    else:
                        set_rule(loc, self.wood)
                case  "Training Sword":
                    if self.world.options.craftsanity_items != CraftingItems.option_off:
                        set_rule(loc, self.training_sword)
                    else:
                        set_rule(loc, self.wood)
                case "Corkscrew":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_corkscrew)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_corkscrew)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_corkscrew)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Spike":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_spike)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_spike)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_spike)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Ball":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_ball)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_ball)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_ball)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Animal Trap":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_animal_trap)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_animal_trap)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_animal_trap)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Barrel":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_barrel)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_barrel)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_barrel)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Bin":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_bin)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_bin)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_bin)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Bucket":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_bucket)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_bucket)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_bucket)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Crutch":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_crutch)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_crutch)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_crutch)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Minecart":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_minecart)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_minecart)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_minecart)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Splint":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_splint)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_splint)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_splint)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Stepladder":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_stepladder)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_stepladder)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_stepladder)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Wheelbarrow":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_wheelbarrow)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_wheelbarrow)
                        else:
                            set_rule(loc, self.metal)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_metal_wheelbarrow)
                        else:
                            set_rule(loc, self.wood_or_metal)
                case "Blocks":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_blocks)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_blocks)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_blocks)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_blocks)
                        else:
                            set_rule(loc, self.glass)
                    elif location.material_type == "Ceramic":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.ceramic_blocks)
                        else:
                            set_rule(loc, self.ceramic)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic_blocks)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
                case "Jug":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_jug)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_jug)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_jug)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_jug)
                        else:
                            set_rule(loc, self.glass)
                    elif location.material_type == "Ceramic":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.ceramic_jug)
                        else:
                            set_rule(loc, self.ceramic)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic_jug)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
                case "Large Pot":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_pot)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_pot)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_pot)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_pot)
                        else:
                            set_rule(loc, self.glass)
                    elif location.material_type == "Ceramic":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.ceramic_pot)
                        else:
                            set_rule(loc, self.ceramic)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic_pot)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
                case "Hive":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_hive)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_hive)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_hive)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_hive)
                        else:
                            set_rule(loc, self.glass)
                    elif location.material_type == "Ceramic":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.ceramic_hive)
                        else:
                            set_rule(loc, self.ceramic)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic_hive)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
                case "Altar":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_altar)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_altar)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_altar)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_altar)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_altar)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Armor Stand":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_armorstand)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_armorstand)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_armorstand)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_armorstand)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_armorstand)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Bookcase":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_bookcase)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_bookcase)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_bookcase)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_bookcase)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_bookcase)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Cabinet":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_cabinet)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_cabinet)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_cabinet)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_cabinet)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_cabinet)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Burial Container":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_burial)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_burial)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_burial)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_burial)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_burial)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Chair":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_chair)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_chair)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_chair)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_chair)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_chair)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Container":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_container)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_container)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_container)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_container)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_container)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Door":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_door)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_door)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_door)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_door)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_door)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Floodgate":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_floodgate)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_floodgate)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_floodgate)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_floodgate)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_floodgate)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Grate":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_grate)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_grate)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_grate)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_grate)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_grate)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Hatch Cover":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_hatchcover)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_hatchcover)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_hatchcover)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_hatchcover)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_hatchcover)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Pedestal":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_pedestal)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_pedestal)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_pedestal)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_pedestal)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_pedestal)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Table":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_table)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_table)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_table)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_table)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_table)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Weapon Rack":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_weaponrack)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_weaponrack)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_weaponrack)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_weaponrack)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_weaponrack)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Statue":
                    if location.material_type == "Wood":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_statue)
                        else:
                            set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.stone_statue)
                        else:
                            set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.metal_statue)
                        else:
                            set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.glass_statue)
                        else:
                            set_rule(loc, self.glass)
                    else:
                        if self.world.options.craftsanity_items != CraftingItems.option_off:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass_statue)
                        else:
                            set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Book Binding" | "Scroll Roller":
                    if location.material_type == "Wood":
                        set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        set_rule(loc, self.glass)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)



                case "Buckler" | "Shield":
                    if location.material_type == "Wood":
                        set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.material_type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.wood_or_leather_or_metal)
                case "Cage" | "Pipe Section":
                    if location.material_type == "Wood":
                        set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        set_rule(loc, self.glass)
                    else:
                        set_rule(loc, self.wood_or_metal_or_glass)
                case "Crossbow":
                    if type in {"Wood", "Bone"}:
                        set_rule(loc, self.bowyer_workshop)
                    elif location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    else:
                        set_rule(loc, self.bowyer_or_metal)
                case "Bolt":
                    if type in {"Wood", "Bone"}:
                        set_rule(loc, self.craftdwarf_workshop)
                    elif location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
                case "Millstone" | "Quern" | "Slab" | "Crafts":
                    set_rule(loc, self.stone)
                case "Mechanism":
                    set_rule(loc, self.mechanic_workshop)
                case "Traction Bench":
                    if location.material_type == "Wood":
                        set_rule(loc, self.wooden_traction_bench)
                    elif location.material_type == "Stone":
                        set_rule(loc, self.stone_traction_bench)
                    elif location.material_type == "Metal":
                        set_rule(loc, self.metal_traction_bench)
                    elif location.material_type == "Glass":
                        set_rule(loc, self.glass_traction_bench)
                    else:
                        set_rule(loc, self.any_traction_bench)
                case "Liquid Container":
                    if location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        set_rule(loc, self.glass)
                    elif location.material_type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.metal_or_glass_or_leather)
                case "Goblet":
                    set_rule(loc, self.metal_or_glass)
                case "Mug" | "Cup" | "Toy":
                    set_rule(loc, self.craftdwarf_workshop)
                case "Totem":
                    set_rule(loc, self.craftdwarf_and_butchery)
                case "Helm" | "Lower Body Armor":
                    if location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.material_type == "Bone":
                        set_rule(loc, self.craftdwarf_workshop)
                    elif location.material_type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.metal_or_bone_or_leather)
                case "Ballista Parts" | "Catapult Parts":
                    set_rule(loc, self.seige_workshop)
                case "Ballista Arrows":
                    if location.material_type == "Wood":
                        set_rule(loc, self.seige_workshop)
                    elif location.material_type == "Metal":
                        set_rule(loc, self.seige_and_metal)
                    else:
                        set_rule(loc, self.seige_workshop)
                case "Ash" | "Charcoal":
                    set_rule(loc, self.wood_furnace)
                case "Metal Bars" | "Coke Bars":
                    set_rule(loc, self.make_metal)
                case "Pearlash" | "Gypsum Plaster" | "Quicklime":
                    set_rule(loc, self.ceramic)
                case "Glass" | "Window" :
                    set_rule(loc, self.glass)
                case "Leather":
                    set_rule(loc, self.leather)
                case "Sheet":
                    set_rule(loc, self.make_paper)
                case "Cloth":
                    set_rule(loc, self.cloth)
                case "Alcohol":
                    set_rule(loc, self.still)
                case "Lye" | "Potash":
                    set_rule(loc, self.ashery_and_wood_furnace)
                case "Milk of Lime":
                    set_rule(loc, self.ashery_and_kiln)
                case "Prepared Meal":
                    set_rule(loc, self.kitchen)
                case "Tallow":
                    set_rule(loc, self.kitchen_and_butchershop)
                case "Oil" | "Press Cake" | "Honey" | "Bee Wax":
                    set_rule(loc, self.screw_press)
                case "Headgear Clothing" | "Upper Body Clothing" | "Hand Clothing"|\
                    "Lower Body Clothing":
                    if location.material_type == "Cloth":
                        set_rule(loc, self.clothier_workshop)
                    elif location.material_type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.leather_or_cloth)
                case "Upper Body Armor":
                    if location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.material_type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.metal_or_leather)
                case "Gauntlets":
                    if location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.material_type == "Bone":
                        set_rule(loc, self.craftdwarf_workshop)
                    else:
                        set_rule(loc, self.metal_or_bone)  
                case "Footwear":
                    if location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.material_type == "Cloth":
                        set_rule(loc, self.clothier_workshop)
                    elif location.material_type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.metal_or_cloth_or_leather)
                case "Dye":
                    set_rule(loc, self.dye)
                case "Bag":
                    if location.material_type == "Cloth":
                        set_rule(loc, self.clothier_workshop)
                    elif location.material_type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.leather_or_cloth)
                case "Rope/Chain":
                    if location.material_type == "Cloth":
                        set_rule(loc, self.clothier_workshop)
                    elif location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    else:
                        set_rule(loc, self.metal_or_cloth)
                case "Battle Axe" | "Mace" | "Pick" | "Short Sword" | "War Hammer" |\
                    "Anvil" | "Coins":
                    set_rule(loc, self.metal)
                case "Soap":
                    set_rule(loc, self.soap)

def assign_locationid_block(item: str) -> int:
    match item:
        case "Beds": return 100000  #20 Checks Max
        case "Corkscrew": return 102000 #60
        case "Blocks": return  104000 #100
        case "Spike": return 106000 #60
        case "Ball": return 108000 #60 
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
        case "Headgear Clothing": return 264000
        case "Upper Body Clothing": return 266000
        case "Upper Body Armor": return 268000
        case "Hand Clothing": return 270000
        case "Lower Body Clothing": return 272000
        case "Lower Body Armor": return 274000
        case "Footwear": return 276000
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
    print("Missing entry: "+item)
    return 0