import math
import re
from typing import List, Set, Union, TYPE_CHECKING
from dataclasses import dataclass
from BaseClasses import ItemClassification, Location, LocationProgressType, CollectionState
from worlds.generic.Rules import set_rule
from .options import EnableItemCreationLocation
from .locations import BASE_ID, LocationData

if TYPE_CHECKING:
    from . import DwarfFortressWorld


@dataclass
class DynamicCraftingData:
    check_name: str  # Name of the Check
    item_name: str
    type: str # Item Material
    id: int # Next number of check
    max_id: int # Max number of checks
    base_location_id: int = BASE_ID

def generate_location_data(world: "DwarfFortressWorld"):
    dynamic_locations: list[LocationData] = []
    if world.options.craftable_locations != EnableItemCreationLocation.option_off:
        for item in world.options.craftable_items:
            new_location = DynamicCraftingData("", "", "", 0, 0, BASE_ID)
            new_location.item_name = item
            new_location.id = 0
            new_location.base_location_id += assign_locationid_block(new_location.item_name)
            dynamic_locations = loop_locations(world, new_location, dynamic_locations)
    return dynamic_locations

def loop_locations(world: "DwarfFortressWorld", new_location: DynamicCraftingData, dynamic_locations: list[LocationData]) -> list[LocationData]:
    if world.options.craftable_enable_materials and not non_material_items(new_location.item_name):
        i = 0
        for materials in world.options.craftable_materials: #iterate all selected Materials
            if valid_materialitem(materials, new_location.item_name) == False:
                continue
            i += 1
            new_location.type = materials
            new_location.max_id = calulate_check_count(world)
            if i > 1:
                new_location.base_location_id += 20 #max checks per craftables
            for next_id in range(new_location.id, new_location.max_id):
                if next_id == new_location.max_id - 1:
                    new_location.check_name = "Crafting "+ new_location.type + " " + new_location.item_name + " Final Check"
                    new_location.base_location_id += 1
                else:
                    new_location.check_name = "Crafting "+ new_location.type + " " + new_location.item_name + " Check "+ str(next_id + 1)
                    new_location.base_location_id += 1
                dynamic_locations.append(LocationData(new_location.check_name, new_location.base_location_id, "", False, new_location.type, new_location.item_name, next_id + 1))
    else: # Materials doesn't matter
        new_location.max_id = calulate_check_count(world)
        for next_id in range(new_location.id, new_location.max_id):
            if next_id == new_location.max_id - 1:
                new_location.check_name = "Crafting " + new_location.item_name + " Final Check"
                new_location.base_location_id += 1
            else:
                new_location.check_name = "Crafting " + new_location.item_name + " Check "+ str(next_id + 1)
                new_location.base_location_id += 1
            dynamic_locations.append(LocationData(new_location.check_name, new_location.base_location_id, "", False, "", new_location.item_name, next_id + 1))
    return dynamic_locations

def calulate_check_count(world: "DwarfFortressWorld"):
    if world.options.craftable_threshold >= world.options.craftable_max_amount:
        return 1
    else:
        checks = math.ceil(world.options.craftable_max_amount / world.options.craftable_threshold)
        return checks
    
def valid_materialitem(material: str, item: str) -> bool:
    if material == "Wood" and item in {"Bed", "Training Axe", "Training Spear", "Training Sword", "Cup", "Ballista Parts", "Catapult Parts"}:
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
    if item in {"Ash", "Charcoal", "Metal Bars", "Coke Bars", "Pearlash", "Gypsum Plaster", "Quicklime", "Glass", "Leather", "Sheet", "Cloth", "Alcohol", "Lye", "Potash", "Milk of Lime", "Prepared Meal", "Tallow", "Oil", "Press Cake", "Honey", "Bee Wax", "Dye", "Soap"}:
        return True
    return False
    

def assign_locationid_block(item: str) -> int:
    match item:
        case "Beds": return 10000  #20 Checks Max
        case "Corkscrew": return 10200 #60
        case "Blocks": return  10400 #100
        case "Spike": return 10600 #60
        case "Ball": return 10800 #60 
        case "Altar": return 11000
        case "Animal Trap": return 11200
        case "Armor Stand": return 11400
        case "Barrel": return 11600
        case "Bin": return 11800
        case "Bookcase": return 12000
        case "Bucket": return 12200
        case "Buckler": return 12400
        case "Cabinet": return 12600
        case "Cage": return 12800
        case "Burial Container": return 13000
        case "Chair": return 13200
        case "Container": return 13400
        case "Crutch": return 13600
        case "Door": return 13800
        case "Floodgate": return 14000
        case "Grate": return 14200
        case "Hatch Cover": return 14400
        case "Minecart": return 14600
        case "Pedestal": return 14800
        case "Pipe Section": return 15000
        case "Shield": return 15200
        case "Splint": return 15400
        case "Stepladder": return 15600
        case "Table": return 15800
        case "Training Axe": return 16000
        case "Training Spear": return 16200
        case "Training Sword": return 16400
        case "Weapon Rack": return 16600
        case "Wheelbarrow": return 16800
        case "Crossbow": return 17000
        case "Bolt": return 17200
        case "Millstone": return 17400
        case "Quern": return 17600
        case "Slab": return 17800
        case "Statue": return 18000
        case "Mechanism": return 18200
        case "Traction Bench": return 18400
        case "Crafts": return 18600
        case "Liquid Container": return 18800
        case "Goblet": return 19000
        case "Mug": return 19200
        case "Cup": return 19400
        case "Toy": return 19600
        case "Totem": return 19800
        case "Gauntlets": return 20000
        case "Helm": return 20200
        case "Ballista Parts": return 20400
        case "Catapult Parts": return 20600
        case "Ballista Arrows": return 20800
        case "Ash": return 21000
        case "Charcoal": return 21200
        case "Metal Bars": return 21400
        case "Coke Bars": return 21600
        case "Pearlash": return 21800
        case "Gypsum Plaster": return 22000
        case "Jug": return 22200
        case "Large Pot": return 22400
        case "Hive": return 22600
        case "Quicklime": return 22800
        case "Glass": return 23000
        case "Window": return 23200
        case "Book Binding": return 23400
        case "Scroll Roller": return 23600
        case "Leather": return 23800
        case "Sheet": return 24000
        case "Cloth": return 24200
        case "Alcohol": return 24400
        case "Lye": return 24600
        case "Potash": return 24800
        case "Milk of Lime": return 25000
        case "Prepared Meal": return 25200
        case "Tallow": return 25400
        case "Oil": return 25600
        case "Press Cake": return 25800
        case "Honey": return 26000
        case "Bee Wax": return 26200
        case "Headgear Clothing": return 26400
        case "Upper Body Clothing": return 26600
        case "Upper Body Armor": return 26800
        case "Hand Clothing": return 27000
        case "Lower Body Clothing": return 27200
        case "Lower Body Armor": return 27400
        case "Footwear": return 27600
        case "Dye": return 27800
        case "Bag": return 28000
        case "Rope/Chain": return 28200
        case "Battle Axe": return 28400
        case "Mace": return 28600
        case "Pick": return 28800
        case "Short Sword": return 29000
        case "Spear": return 29200
        case "War Hammer": return 29400
        case "Anvil": return 29600
        case "Coins": return 29800
        case "Soap": return 30000
    print("Missing entry: "+item)
    return 0

class DynamicCraftingLocationRules:
    world: "DwarfFortressWorld"
    metal_working_list: List[str] = [
        "Forge Blueprint",
        "Magma Forge Blueprint"
    ]
    smelter_list: List[str] = [
        "Smelter Blueprint",
        "Magma Smelter Blueprint"
    ]
    glass_working_list: List[str] = [
        "Glass Furnace Blueprint",
        "Magma Glass Furnace Blueprint"
    ]
    ceramic_working_list: List[str] = [
        "Magma Kiln Blueprint",
        "Kiln Blueprint"
    ]

    def __init__(self, world: "DwarfFortressWorld") -> None:
        self.player = world.player
        self.world = world
            

    def wood(self, state:CollectionState) -> bool:
        return state.has("Carpenter's Workshop Blueprint", self.player)
    
    def metal(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return state.has_any(self.metal_working_list, self.player)
        else:
            return state.has_any(self.smelter_list, self.player) and state.has_any(self.metal_working_list, self.player)
        
    def make_metal(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return True
        else:
            return state.has_any(self.smelter_list, self.player)
        
    def ceramic(self, state:CollectionState) -> bool:
        return state.has_any(self.ceramic_working_list, self.player)
    
    def glass(self, state:CollectionState) -> bool:
        return state.has_any(self.glass_working_list, self.player)
    
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
                    if location.type == "Wood":
                        set_rule(loc, self.wood)
                    elif location.type == "Metal":
                        set_rule(loc, self.metal)
                    else:
                        set_rule(loc, self.wood_or_metal)
                case "Blocks" | "Jug" | "Large Pot" | "Hive":
                    if location.type == "Wood":
                        set_rule(loc, self.wood)
                    elif location.type == "Stone":
                        set_rule(loc, self.stone)
                    elif location.type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.type == "Glass":
                        set_rule(loc, self.glass)
                    elif location.type == "Ceramic":
                        set_rule(loc, self.ceramic)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
                case "Altar" | "Armor Stand" | "Bookcase" | "Cabinet" | "Burial Container" |\
                    "Chair" | "Container" | "Door" | "Floodgate"| "Grate"|\
                    "Hatch Cover" | "Pedestal" | "Table" | "Weapon Rack" | "Statue" |\
                    "Book Binding" | "Scroll Roller":
                    if location.type == "Wood":
                        set_rule(loc, self.wood)
                    elif location.type == "Stone":
                        set_rule(loc, self.stone)
                    elif location.type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.type == "Glass":
                        set_rule(loc, self.glass)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
                case "Buckler" | "Shield":
                    if location.type == "Wood":
                        set_rule(loc, self.wood)
                    elif location.type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.wood_or_leather_or_metal)
                case "Cage" | "Pipe Section":
                    if location.type == "Wood":
                        set_rule(loc, self.wood)
                    elif location.type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.type == "Glass":
                        set_rule(loc, self.glass)
                    else:
                        set_rule(loc, self.wood_or_metal_or_glass)
                case "Crossbow":
                    if type in {"Wood", "Bone"}:
                        set_rule(loc, self.bowyer_workshop)
                    elif location.type == "Metal":
                        set_rule(loc, self.metal)
                    else:
                        set_rule(loc, self.bowyer_or_metal)
                case "Bolt":
                    if type in {"Wood", "Bone"}:
                        set_rule(loc, self.craftdwarf_workshop)
                    elif location.type == "Metal":
                        set_rule(loc, self.metal)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
                case "Millstone" | "Quern" | "Slab" | "Crafts":
                    set_rule(loc, self.stone)
                case "Mechanism":
                    set_rule(loc, self.mechanic_workshop)
                case "Traction Bench":
                    if location.type == "Wood":
                        set_rule(loc, self.wooden_traction_bench)
                    elif location.type == "Stone":
                        set_rule(loc, self.stone_traction_bench)
                    elif location.type == "Metal":
                        set_rule(loc, self.metal_traction_bench)
                    elif location.type == "Glass":
                        set_rule(loc, self.glass_traction_bench)
                    else:
                        set_rule(loc, self.any_traction_bench)
                case "Liquid Container":
                    if location.type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.type == "Glass":
                        set_rule(loc, self.glass)
                    elif location.type == "Leather":
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
                    if location.type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.type == "Bone":
                        set_rule(loc, self.craftdwarf_workshop)
                    elif location.type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.metal_or_bone_or_leather)
                case "Ballista Parts" | "Catapult Parts":
                    set_rule(loc, self.seige_workshop)
                case "Ballista Arrows":
                    if location.type == "Wood":
                        set_rule(loc, self.seige_workshop)
                    elif location.type == "Metal":
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
                    if location.type == "Cloth":
                        set_rule(loc, self.clothier_workshop)
                    elif location.type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.leather_or_cloth)
                case "Upper Body Armor":
                    if location.type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.metal_or_leather)
                case "Gauntlets":
                    if location.type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.type == "Bone":
                        set_rule(loc, self.craftdwarf_workshop)
                    else:
                        set_rule(loc, self.metal_or_bone)  
                case "Footwear":
                    if location.type == "Metal":
                        set_rule(loc, self.metal)
                    elif location.type == "Cloth":
                        set_rule(loc, self.clothier_workshop)
                    elif location.type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.metal_or_cloth_or_leather)
                case "Dye":
                    set_rule(loc, self.dye)
                case "Bag":
                    if location.type == "Cloth":
                        set_rule(loc, self.clothier_workshop)
                    elif location.type == "Leather":
                        set_rule(loc, self.leather_works)
                    else:
                        set_rule(loc, self.leather_or_cloth)
                case "Rope/Chain":
                    if location.type == "Cloth":
                        set_rule(loc, self.clothier_workshop)
                    elif location.type == "Metal":
                        set_rule(loc, self.metal)
                    else:
                        set_rule(loc, self.metal_or_cloth)
                case "Battle Axe" | "Mace" | "Pick" | "Short Sword" | "War Hammer" |\
                    "Anvil" | "Coins":
                    set_rule(loc, self.metal)
                case "Soap":
                    set_rule(loc, self.soap)