import math
import re
from typing import List, Set, Union, TYPE_CHECKING
from dataclasses import dataclass
from BaseClasses import ItemClassification, Location, LocationProgressType, CollectionState
from .options import EnableItemCreationLocation, VariableItemCreationLocations, VariableItemMateriaToggle, VariableItemTypeCreationLocations, VariableItemCreationMaxAmount, VariableItemCreationThreshold
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
    if world.options.craftable_locations:
        print("REACHED")
        for item in world.options.craftable_items:
            new_location = DynamicCraftingData("", "", "", 0, 0, BASE_ID)
            new_location.item_name = item
            new_location.id = 1
            if item == "Door":
                new_location.base_location_id += 10000 
                dynamic_locations = loop_locations(world, new_location, dynamic_locations)
            if item == "Cage":
                new_location.base_location_id += 10200 
                dynamic_locations = loop_locations(world, new_location, dynamic_locations)

    return dynamic_locations

def loop_locations(world: "DwarfFortressWorld", new_location: DynamicCraftingData, dynamic_locations: list[LocationData]) -> list[LocationData]:
    if world.options.craftable_enable_materials:
        for materials in world.options.craftable_materials: #iterate all selected Materials
            if valid_materialitem(materials, new_location.item_name) == False:
                continue
            new_location.type = materials
            new_location.max_id = calulate_check_count(world)
            new_location.base_location_id += 20 #max checks per craftables
            for next_id in range(new_location.id, new_location.max_id + 1):
                if next_id == new_location.max_id:
                    new_location.check_name = "Crafting "+ new_location.type + " " + new_location.item_name + " Final Check"
                    new_location.base_location_id += 1
                else:
                    new_location.check_name = "Crafting "+ new_location.type + " " + new_location.item_name + " Check "+ str(next_id)
                    new_location.base_location_id += 1
                dynamic_locations.append(LocationData(new_location.check_name, new_location.base_location_id, ""))
    else: # Materials doesn't matter
        new_location.max_id = calulate_check_count(world)
        for next_id in range(new_location.id, new_location.max_id + 1):
            if next_id == new_location.max_id:
                new_location.check_name = "Crafting " + new_location.item_name + " Final Check"
                new_location.base_location_id += 1
            else:
                new_location.check_name = "Crafting " + new_location.item_name + " Check "+ str(next_id)
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
    if material in {"Stone", "Metal", "Wood"} and item == "Door":
        return True
    if material in {"Wood", "Metal", "Glass"} and item == "Cage":
        return True
    return False