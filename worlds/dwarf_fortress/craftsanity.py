import math
import re
from typing import List, Set, Union, TYPE_CHECKING
from dataclasses import dataclass
from BaseClasses import ItemClassification, Location, LocationProgressType, CollectionState
from worlds.generic.Rules import set_rule
from .options import EnableCraftsanity, CraftsanityItemGroup, CraftsanityItems
from .locations import BASE_ID, LocationData

if TYPE_CHECKING:
    from . import DwarfFortressWorld


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

def generate_location_data_PRINT_ONLY(world: "DwarfFortressWorld"):
    dynamic_locations: list[LocationData] = []
    if world.options.craftsanity != EnableCraftsanity.option_off:
        for item in world.options.craftsanity_items:
            new_location = DynamicCraftingData("", "", "", 0, 0, BASE_ID)
            new_location.item_name = item
            new_location.id = 0
            new_location.base_location_id += assign_locationid_block(new_location.item_name)
            loop_locations_PRINT_ONLY(world, new_location, dynamic_locations)

def loop_locations(world: "DwarfFortressWorld", new_location: DynamicCraftingData, dynamic_locations: list[LocationData]) -> int:
    if world.options.craftsanity_enable_materials and not non_material_items(new_location.item_name):
        for materials in world.options.craftsanity_materials: #iterate all selected Materials
            if valid_materialitem(materials, new_location.item_name) == False:
                continue
            new_location.type = materials
            new_location.max_id = calulate_check_count(world)
            for next_id in range(new_location.id, new_location.max_id):
                new_location.base_location_id += 1
                if next_id == new_location.max_id - 1: #find ID for final Check ITS IMPORTANT!
                    new_location.check_name = "Crafting "+ new_location.type + " " + new_location.item_name + " Final Check"
                    world.dynamic_locations.append(LocationData(new_location.check_name, world.location_name_to_id[new_location.check_name], "", False, new_location.type, new_location.item_name, next_id + 1))
                else:
                    new_location.check_name = "Crafting "+ new_location.type + " " + new_location.item_name + " Check "+ str(next_id + 1)
                    world.dynamic_locations.append(LocationData(new_location.check_name, new_location.base_location_id, "", False, new_location.type, new_location.item_name, next_id + 1))
                world.dynamic_locations_names.append(new_location.check_name)
    else: # Materials doesn't matter
        new_location.max_id = calulate_check_count(world)
        for next_id in range(new_location.id, new_location.max_id):
            new_location.base_location_id += 1
            if next_id == new_location.max_id - 1: #find ID for final Check ITS IMPORTANT!
                new_location.check_name = "Crafting " + new_location.item_name + " Final Check"
                world.dynamic_locations.append(LocationData(new_location.check_name, world.location_name_to_id[new_location.check_name], "", False, new_location.type, new_location.item_name, next_id + 1))
            else:
                new_location.check_name = "Crafting " + new_location.item_name + " Check "+ str(next_id + 1)
                world.dynamic_locations.append(LocationData(new_location.check_name, new_location.base_location_id, "", False, "", new_location.item_name, next_id + 1))
            world.dynamic_locations_names.append(new_location.check_name)
    return

def loop_locations_PRINT_ONLY(world: "DwarfFortressWorld", new_location: DynamicCraftingData, dynamic_locations: list[LocationData]) -> int:
    if world.options.craftsanity_enable_materials and not non_material_items(new_location.item_name):
        for materials in world.options.craftsanity_materials: #iterate all selected Materials
            if valid_materialitem(materials, new_location.item_name) == False:
                continue
            new_location.type = materials
            new_location.max_id = calulate_check_count(world)
            for next_id in range(new_location.id, new_location.max_id):
                if next_id == new_location.max_id - 1:
                    new_location.check_name = "Crafting "+ new_location.type + " " + new_location.item_name + " Final Check"
                    new_location.base_location_id += 1
                else:
                    new_location.check_name = "Crafting "+ new_location.type + " " + new_location.item_name + " Check "+ str(next_id + 1)
                    new_location.base_location_id += 1
                world.dynamic_locations.append(LocationData(new_location.check_name, new_location.base_location_id, "", False, new_location.type, new_location.item_name, next_id + 1))
                world.dynamic_locations_names.append(new_location.check_name)
        ##Also include Materials Doesn't Matter for Printing Only!
        new_location.type = ""
        new_location.max_id = calulate_check_count(world)
        for next_id in range(new_location.id, new_location.max_id):
            if next_id == new_location.max_id - 1:
                new_location.check_name = "Crafting " + new_location.item_name + " Final Check"
                new_location.base_location_id += 1
            else:
                new_location.check_name = "Crafting " + new_location.item_name + " Check "+ str(next_id + 1)
                new_location.base_location_id += 1
            world.dynamic_locations.append(LocationData(new_location.check_name, new_location.base_location_id, "", False, "", new_location.item_name, next_id + 1))
    else: # Materials doesn't matter
        new_location.max_id = calulate_check_count(world)
        for next_id in range(new_location.id, new_location.max_id):
            if next_id == new_location.max_id - 1:
                new_location.check_name = "Crafting " + new_location.item_name + " Final Check"
                new_location.base_location_id += 1
            else:
                new_location.check_name = "Crafting " + new_location.item_name + " Check "+ str(next_id + 1)
                new_location.base_location_id += 1
            world.dynamic_locations.append(LocationData(new_location.check_name, new_location.base_location_id, "", False, "", new_location.item_name, next_id + 1))
            world.dynamic_locations_names.append(new_location.check_name)
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

    def set_dynamic_rules(self) -> None:
        for location in self.world.dynamic_locations:
            self.world.multiworld
            loc = self.world.multiworld.get_location(location.name, self.player)
            match location.df_item:
                case "Beds" | "Training Axe" | "Training Spear" | "Training Sword": 
                    set_rule(loc, self.wood)
                case "Corkscrew" | "Spike" | "Ball" | "Animal Trap" | "Barrel" |\
                    "Bin" | "Bucket" | "Crutch" | "Minecart" | "Splint" |\
                    "Stepladder" | "Wheelbarrow":
                    if location.material_type == "Wood":
                        set_rule(loc, self.wood)
                    elif location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    else:
                        set_rule(loc, self.wood_or_metal)
                case "Blocks" | "Jug" | "Large Pot" | "Hive":
                    if location.material_type == "Wood":
                        set_rule(loc, self.wood)
                    elif location.material_type == "Stone":
                        set_rule(loc, self.stone)
                    elif location.material_type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.material_type == "Glass":
                        set_rule(loc, self.glass)
                    elif location.material_type == "Ceramic":
                        set_rule(loc, self.ceramic)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
                case "Altar" | "Armor Stand" | "Bookcase" | "Cabinet" | "Burial Container" |\
                    "Chair" | "Container" | "Door" | "Floodgate"| "Grate"|\
                    "Hatch Cover" | "Pedestal" | "Table" | "Weapon Rack" | "Statue" |\
                    "Book Binding" | "Scroll Roller":
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