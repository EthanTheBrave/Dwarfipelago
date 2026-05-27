import math
import re
from typing import List, Set, Union, TYPE_CHECKING
from dataclasses import dataclass
from BaseClasses import ItemClassification, Location, LocationProgressType, CollectionState
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
                dynamic_locations.append(LocationData(new_location.check_name, new_location.base_location_id, ""))
    else: # Materials doesn't matter
        new_location.max_id = calulate_check_count(world)
        for next_id in range(new_location.id, new_location.max_id):
            if next_id == new_location.max_id - 1:
                new_location.check_name = "Crafting " + new_location.item_name + " Final Check"
                new_location.base_location_id += 1
            else:
                new_location.check_name = "Crafting " + new_location.item_name + " Check "+ str(next_id + 1)
                new_location.base_location_id += 1
            dynamic_locations.append(LocationData(new_location.check_name, new_location.base_location_id, ""))
    return dynamic_locations

def calulate_check_count(world: "DwarfFortressWorld"):
    if world.options.craftable_threshold >= world.options.craftable_max_amount:
        return 1
    else:
        checks = math.floor(world.options.craftable_max_amount / world.options.craftable_threshold)
        return checks
    
def valid_materialitem(material: str, item: str) -> bool:
    if material == "Wood" and item in {"Bed", "Training Axe", "Training Spear", "Training Sword", "Cup", "Ballista Parts", "Catapult Parts"}:
        return True
    if material in {"Wood", "Metal"} and item in {"Animal Trap", "Barrel", "Bin", "Bucket", "Crutch", "Minecart", "Splint", "Stepladder", "Wheelbarrow", "Ballista Arrows"}:
        return True
    if material in {"Wood", "Metal", "Glass"} and item in {"Corkscrew", "Spike", "Cage", "Ball", "Pipe Section"}:
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
    if material == "Bone" and item in {"Totem", "Leggings", "Greaves", }:
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
        case "Leggings": return 20000
        case "Greaves": return 20200
        case "Helm": return 20400
        case "Ballista Parts": return 20600
        case "Catapult Parts": return 20800
        case "Ballista Arrows": return 21000
        case "Ash": return 21200
        case "Charcoal": return 21400
        case "Metal Bars": return 21600
        case "Coke Bars": return 21800
        case "Pearlash": return 22000
        case "Gypsum Plaster": return 22200
        case "Jug": return 22400
        case "Large Pot": return 22600
        case "Hive": return 22800
        case "Quicklime": return 23000
        case "Glass": return 23200
        case "Window": return 23400
        case "Book Binding": return 23600
        case "Scroll Roller": return 23800
        case "Leather": return 24000
        case "Sheet": return 24200
        case "Cloth": return 24400
        case "Alcohol": return 24600
        case "Lye": return 24800
        case "Potash": return 25000
        case "Milk of Lime": return 25200
        case "Prepared Meal": return 25400
        case "Tallow": return 25600
        case "Oil": return 25800
        case "Press Cake": return 26000
        case "Honey": return 26200
        case "Bee Wax": return 26400
        case "Headgear Clothing": return 26600
        case "Upper Body Clothing": return 26800
        case "Upper Body Armor": return 27000
        case "Hand Clothing": return 27200
        case "Lower Body Clothing": return 27400
        case "Lower Body Armor": return 27600
        case "Footwear": return 27800
        case "Dye": return 28000
        case "Bag": return 28200
        case "Rope/Chain": return 28400
        case "Battle Axe": return 28600
        case "Mace": return 28800
        case "Pick": return 29000
        case "Short Sword": return 29200
        case "Spear": return 29400
        case "War Hammer": return 29600
        case "Anvil": return 29800
        case "Coins": return 30000
        case "Soap": return 30200
    print("Missing entry: "+item)
    return 0
