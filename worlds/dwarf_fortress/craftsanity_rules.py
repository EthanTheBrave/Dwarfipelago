from typing import List, Set, Union, TYPE_CHECKING
from dataclasses import dataclass
from BaseClasses import ItemClassification, Location, LocationProgressType, CollectionState
from worlds.generic.Rules import set_rule
from .options import CraftingPermits

if TYPE_CHECKING:
    from . import DwarfFortressWorld

class DynamicCraftingLocationRules:
    world: "DwarfFortressWorld"

    def __init__(self, world: "DwarfFortressWorld") -> None:
        self.player = world.player
        self.world = world
            

    def wood(self, state:CollectionState) -> bool:
        return state.has("Carpenter's Workshop Blueprint", self.player)
    
    def metal(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")
        else:
            return self.process_resource(state, "metal") and (state.has("Forge Blueprint", self.player) or \
            self.magma_processing(state, "forge"))
        
    def bone(self, state:CollectionState) -> bool:
        return self.process_resource(state, "bone")
    
    def bonecraft(self, state:CollectionState) -> bool:
        return self.process_resource(state, "bone") and self.craftdwarf_workshop(state)
    
    def leathercraft(self, state:CollectionState) -> bool:
        return self.leather(state) and self.craftdwarf_workshop(state)
    
    def forge_only(self, state:CollectionState) -> bool:
         return self.magma_processing(state, "forge") or state.has("Forge Blueprint", self.player)
        
    def process_resource(self, state:CollectionState, resource) -> bool: #glass, metal, ceramic
        if resource == "metal":
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return (state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player)) or \
                self.magma_processing(state, "metal")
            elif self.world.options.craftpermits == CraftingPermits.option_on:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player)) or \
                self.magma_processing(state, "metal")) and state.has("Metal Bars Permit", self.player)
            else:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player) and \
                state.has("Charcoal Permit", self.player)) or self.magma_processing(state, "metal")) and \
                state.has("Metal Bars Permit", self.player)
        if resource == "adamantine_metal":
            if self.world.options.craftpermits == CraftingPermits.option_off:
                if self.world.options.mining_depth: # need to dig deep
                    if self.world.options.trades_inlogic: # don't need fuel
                        return (state.has("Smelter Blueprint", self.player) or self.magma_processing(state, "metal")) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) \
                        and (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) \
                        and state.has("Progressive Mining Depth", self.player, 4)
                    else:
                        return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player)) \
                        or self.magma_processing(state, "metal")) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) \
                        and (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) \
                        and state.has("Progressive Mining Depth", self.player, 4)
                else:
                    if self.world.options.trades_inlogic: # don't need fuel
                        return (state.has("Smelter Blueprint", self.player) or self.magma_processing(state, "metal")) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) \
                        and (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge"))
                    else:
                        return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player)) \
                        or self.magma_processing(state, "metal")) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) \
                        and (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) 
            elif self.world.options.craftpermits == CraftingPermits.option_on:
                if self.world.options.mining_depth: # need to dig deep
                    if self.world.options.trades_inlogic: # don't need fuel
                        return (state.has("Smelter Blueprint", self.player) or self.magma_processing(state, "metal")) \
                        and (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) \
                        and state.has("Metal Bars Permit", self.player) and state.has("Craftsdwarf's Workshop Blueprint", self.player) \
                        and state.has("Progressive Mining Depth", self.player, 4)
                    else:
                        return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player)) or \
                        self.magma_processing(state, "metal")) and state.has("Metal Bars Permit", self.player) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) and (state.has("Forge Blueprint", self.player) or \
                        self.magma_processing(state, "forge")) and state.has("Progressive Mining Depth", self.player, 4)
                else:
                    if self.world.options.trades_inlogic: # don't need fuel
                        return (state.has("Smelter Blueprint", self.player) or self.magma_processing(state, "metal")) \
                        and (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) \
                        and state.has("Metal Bars Permit", self.player) and state.has("Craftsdwarf's Workshop Blueprint", self.player)
                    else:
                        return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player)) or \
                        self.magma_processing(state, "metal")) and state.has("Metal Bars Permit", self.player) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) and (state.has("Forge Blueprint", self.player) or \
                        self.magma_processing(state, "forge"))
            else:
                if self.world.options.mining_depth: # need to dig deep
                    if self.world.options.trades_inlogic: # don't need fuel
                        return (state.has("Smelter Blueprint", self.player) or self.magma_processing(state, "metal")) \
                        and state.has("Metal Bars Permit", self.player) and state.has("Craftsdwarf's Workshop Blueprint", self.player) \
                        and (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) \
                        and state.has("Progressive Mining Depth", self.player, 4)
                    else:
                        return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player) \
                        and state.has("Charcoal Permit", self.player)) or (self.magma_processing(state, "metal") \
                        and state.has("Coke Bars Permit", self.player))) and state.has("Metal Bars Permit", self.player) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) \
                        and (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) \
                        and state.has("Progressive Mining Depth", self.player, 4)
                else:
                    if self.world.options.trades_inlogic: # don't need fuel
                        return (state.has("Smelter Blueprint", self.player) or self.magma_processing(state, "metal")) \
                        and state.has("Metal Bars Permit", self.player) and state.has("Craftsdwarf's Workshop Blueprint", self.player) \
                        and (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge"))
                    else:
                        return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player) \
                        and state.has("Charcoal Permit", self.player)) or (self.magma_processing(state, "metal") \
                        and state.has("Coke Bars Permit", self.player))) and state.has("Metal Bars Permit", self.player) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) \
                        and (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge"))
        if resource == "adamantine_cloth":
            if self.world.options.craftpermits != CraftingPermits.option_all:
                if self.world.options.mining_depth:  # can't mine adamantine without depth  
                    if self.world.options.trades_inlogic: # obtain fuel
                        return (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) \
                            and state.has("Craftsdwarf's Workshop Blueprint", self.player) and state.has("Loom Blueprint", self.player) \
                            and state.has("Progressive Mining Depth", self.player, 4)
                    else:
                        return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Charcoal Permit", self.player) \
                            and state.has("Forge Blueprint", self.player)) or self.magma_processing(state, "forge")) \
                            and state.has("Craftsdwarf's Workshop Blueprint", self.player) and state.has("Loom Blueprint", self.player) \
                            and state.has("Progressive Mining Depth", self.player, 4)
                else: # no depth item
                    if self.world.options.trades_inlogic: # obtain fuel
                        return (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) \
                            and state.has("Craftsdwarf's Workshop Blueprint", self.player) and state.has("Loom Blueprint", self.player)
                    else:
                        return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Charcoal Permit", self.player) \
                            and state.has("Forge Blueprint", self.player)) or self.magma_processing(state, "forge")) \
                            and state.has("Craftsdwarf's Workshop Blueprint", self.player) and state.has("Loom Blueprint", self.player) \
                            and state.has("Cloth Permit", self.player)
            else:
                if self.world.options.mining_depth:  # can't mine adamantine without depth 
                    if self.world.options.trades_inlogic: #obtain fuel
                        return (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) and state.has("Loom Blueprint", self.player) \
                        and state.has("Cloth Permit", self.player) and state.has("Progressive Mining Depth", self.player, 4)
                    else:
                        return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Charcoal Permit", self.player) \
                        and state.has("Forge Blueprint", self.player)) or self.magma_processing(state, "forge")) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) and state.has("Loom Blueprint", self.player) \
                        and state.has("Cloth Permit", self.player) and state.has("Progressive Mining Depth", self.player, 4)
                else: #no depth
                    if self.world.options.trades_inlogic: #obtain fuel
                        return (state.has("Forge Blueprint", self.player) or self.magma_processing(state, "forge")) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) and state.has("Loom Blueprint", self.player) \
                        and state.has("Cloth Permit", self.player)
                    else:
                        return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Charcoal Permit", self.player) \
                        and state.has("Forge Blueprint", self.player)) or self.magma_processing(state, "forge")) \
                        and state.has("Craftsdwarf's Workshop Blueprint", self.player) and state.has("Loom Blueprint", self.player) \
                        and state.has("Cloth Permit", self.player)
        if resource == "coke":
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return (state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player)) or \
                self.magma_processing(state, "coke")
            elif self.world.options.craftpermits == CraftingPermits.option_on:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Forge Blueprint", self.player)) or \
                self.magma_processing(state, "coke")) and state.has("Coke Bars Permit", self.player)
            else:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Forge Blueprint", self.player) and \
                state.has("Charcoal Permit", self.player)) or self.magma_processing(state, "coke")) and \
                state.has("Coke Bars Permit", self.player)
        elif resource == "glass":
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return (state.has("Wood Furnace Blueprint", self.player) and state.has("Glass Furnace Blueprint", self.player)) or \
                self.magma_processing(state, "glass")
            elif self.world.options.craftpermits == CraftingPermits.option_on:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Glass Furnace Blueprint", self.player)) or \
                self.magma_processing(state, "glass")) and state.has("Glass Permit", self.player)
            else:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Glass Furnace Blueprint", self.player) and \
                state.has("Charcoal Permit", self.player)) or self.magma_processing(state, "glass")) and \
                state.has("Glass Permit", self.player) 
        elif resource == "ceramic":
            if self.world.options.craftpermits != CraftingPermits.option_all:
                return (state.has("Wood Furnace Blueprint", self.player) and state.has("Kiln Blueprint", self.player)) or \
                self.magma_processing(state, "ceramic")
            else:
                return (state.has("Wood Furnace Blueprint", self.player) and state.has("Kiln Blueprint", self.player) and \
                state.has("Charcoal Permit", self.player)) or self.magma_processing(state, "ceramic")
        elif resource == "bone":
             return state.has("Butcher's Shop Blueprint", self.player)
        elif resource == "farming":
                return state.has("Farm Plot Blueprint", self.player)
        else:
            print("Missing Resource Type for process_resource function")
            return False
        
    def magma_processing(self, state:CollectionState, resource) -> bool: #glass, metal, ceramic
        if resource in {"metal", "coke"}:
            if self.world.options.mining_depth:
                return state.has("Magma Smelter Blueprint", self.player) and state.has("Progressive Mining Depth", self.player, 4)
            else:
                return state.has("Magma Smelter Blueprint", self.player)
        elif resource == "glass":
            if self.world.options.mining_depth:
                return state.has("Magma Glass Furnace Blueprint", self.player) and state.has("Progressive Mining Depth", self.player, 4)
            else:
                return state.has("Magma Glass Furnace Blueprint", self.player)
        elif resource == "ceramic":
            if self.world.options.mining_depth:
                return state.has("Magma Kiln Blueprint", self.player) and state.has("Progressive Mining Depth", self.player, 4)
            else:
                return state.has("Magma Kiln Blueprint", self.player)
        elif resource == "forge":
            if self.world.options.mining_depth:
                return state.has("Magma Forge Blueprint", self.player) and state.has("Progressive Mining Depth", self.player, 4)
            else:
                return state.has("Magma Forge Blueprint", self.player)
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
    
    def adamantine_metal(self, state:CollectionState) -> bool:
        return self.process_resource(state, "adamantine_metal")
        
    def ceramic(self, state:CollectionState) -> bool:
        return self.process_resource(state, "ceramic")
    
    def glass(self, state:CollectionState) -> bool:
        return self.process_resource(state, "glass")
    
    def stone(self, state:CollectionState) -> bool:
        return state.has("Stoneworker's Workshop Blueprint", self.player)
    
    def leather(self, state:CollectionState) -> bool:
        return state.has("Tanner's Blueprint", self.player) and self.butcher_workshop(state)

    def leather_works(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return state.has("Leather Works Blueprint", self.player)
        else:
            if self.world.options.craftpermits != CraftingPermits.option_all:
                return self.leather(state) and state.has("Leather Works Blueprint", self.player)
            else:
                return self.leather(state) and state.has("Leather Works Blueprint", self.player) and \
                state.has("Leather Permit", self.player)

    def adamantine_cloth(self, state:CollectionState) -> bool:
        return self.process_resource(state, "adamantine_cloth")
    
    def adamantine_or_cloth(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) or self.adamantine_cloth(state)

    def adamantinecloth_or_leather(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) or self.leather_works(state) 
    
    def cloth(self, state:CollectionState) -> bool:
        return state.has("Loom Blueprint", self.player)
    
    def thread(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
             return True
        else:
            return state.has("Farmer's Workshop Blueprint", self.player) or state.has("Loom Blueprint", self.player)
    
    def clothier_workshop(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return state.has("Clothier's Shop Blueprint", self.player)
        else:
            if self.world.options.craftpermits != CraftingPermits.option_all:
                return self.cloth(state) and state.has("Clothier's Shop Blueprint", self.player)
            else:
                return self.make_cloth(state) and state.has("Clothier's Shop Blueprint", self.player)
        
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
    
    def bone_bowyer_workshop(self, state:CollectionState) -> bool:
        return state.has("Bowyer's Workshop Blueprint", self.player) and self.bone(state)
    
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
        if self.world.options.trades_inlogic == True or self.world.options.craftpermits == CraftingPermits.option_off:
            return state.has("Screw Press Blueprint", self.player)
        else:
            return state.has("Screw Press Blueprint", self.player) and self.mechanic_mechanism(state)
    
    def still(self, state:CollectionState) -> bool:
        return state.has("Still Blueprint", self.player)
    
    def ashery(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic == True \
        or self.world.options.craftpermits == CraftingPermits.option_off:
            return state.has("Ashery Blueprint", self.player)
        elif self.world.options.craftpermits == CraftingPermits.option_on:
            return state.has("Ashery Blueprint", self.player) and self.wood_or_metal_bucket(state)
        else:
            return state.has("Ashery Blueprint", self.player) and self.wood_or_metal_bucket(state) \
            and self.wood_or_metal_barrel(state)

    
    def kitchen(self, state:CollectionState) -> bool:
        return state.has("Kitchen Blueprint", self.player)
    
    def kitchen_and_butchershop(self, state:CollectionState) -> bool:
        return self.kitchen(state) and self.butcher_workshop(state)
    
    def seige_and_metal(self, state:CollectionState) -> bool:
        return self.seige_workshop(state) and self.metal(state)

    def bowyer_or_metal(self, state:CollectionState) -> bool:
        return self.metal(state) or self.bowyer_workshop(state) 
    
    def woodcraft_or_bonecraft_or_metal(self, state:CollectionState) -> bool:
        return self.metal(state) or self.craftdwarf_workshop(state) or self.bonecraft(state)

    def craftdwarf_or_metal(self, state:CollectionState) -> bool:
        return self.metal(state) or self.craftdwarf_workshop(state) 
    
    def craftdwarf_and_butchery(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and self.butcher_workshop(state)
    
    def craftdwarf_or_metal_or_glass(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) or self.metal(state) or self.glass(state)
    
    def craftdwarf_or_metal_or_glass_or_ceramic(self, state:CollectionState) -> bool:
         return self.craftdwarf_workshop(state) or self.metal(state) or self.glass(state) or self.ceramic(state)
    
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
        return self.metal(state) or self.bonecraft(state)
    
    def metal_or_cloth(self, state:CollectionState) -> bool:
        return self.metal(state) or self.clothier_workshop(state)

    def metal_or_bone_or_leather(self, state:CollectionState) -> bool:
        return self.metal(state) or self.leather_works(state) or self.bonecraft(state)
    
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
    
    def leather_or_cloth_or_adamantinecloth(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) or self.leather_works(state) or self.adamantine_cloth(state)
    
    def dye(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return state.has("Dyer's Workshop Blueprint", self.player)
        else:
            return self.cloth(state) and state.has("Dyer's Workshop Blueprint", self.player)
        
    def soap(self, state:CollectionState) -> bool:
        return self.ashery(state) and self.wood_furnace(state) \
            and state.has("Soap Maker's Workshop Blueprint", self.player) \
            and (self.kitchen(state) and self.butcher_workshop(state) or self.screw_press(state))
    
    def displaycase(self, state:CollectionState) -> bool:
        return self.wood(state) and self.glass(state) \

    def bed(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Beds Permit", self.player)
    
    def training_axe(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Training Axe Permit", self.player)
    def training_spear(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Training Spear Permit", self.player)
    def training_sword(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Training Sword Permit", self.player)
    
    def wood_corkscrew(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Corkscrew Permit", self.player)
    def metal_corkscrew(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Corkscrew Permit", self.player)
    def adamantine_corkscrew(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Corkscrew Permit", self.player)
    def glass_corkscrew(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Corkscrew Permit", self.player)
    def wood_or_metal_or_glass_corkscrew(self, state:CollectionState) -> bool:
            return self.wood_or_metal_or_glass(state) and state.has("Corkscrew Permit", self.player)

    def wood_spike(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Menacing Spike Permit", self.player)
    def metal_spike(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Menacing Spike Permit", self.player)
    def adamantine_spike(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Menacing Spike Permit", self.player)
    def wood_or_metal_spike(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Menacing Spike Permit", self.player)

    def wood_ball(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Spiked Ball Permit", self.player)
    def metal_ball(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Spiked Ball Permit", self.player)
    def adamantine_ball(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Spiked Ball Permit", self.player)
    def glass_ball(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Spiked Ball Permit", self.player)
    def wood_or_metal_ball(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Spiked Ball Permit", self.player)

    def wood_animal_trap(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Animal Trap Permit", self.player)
    def metal_animal_trap(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Animal Trap Permit", self.player)
    def adamantine_animal_trap(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Animal Trap Permit", self.player)
    def wood_or_metal_animal_trap(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Animal Trap Permit", self.player)
    
    def wood_barrel(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Barrel Permit", self.player)
    def metal_barrel(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Barrel Permit", self.player)
    def adamantine_barrel(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Barrel Permit", self.player)
    def wood_or_metal_barrel(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Barrel Permit", self.player)
    
    def wood_bin(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Bin Permit", self.player)
    def metal_bin(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Bin Permit", self.player)
    def adamantine_bin(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Bin Permit", self.player)
    def wood_or_metal_bin(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Bin Permit", self.player)

    def wood_bucket(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Bucket Permit", self.player)
    def metal_bucket(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Bucket Permit", self.player)
    def adamantine_bucket(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Bucket Permit", self.player)
    def wood_or_metal_bucket(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Bucket Permit", self.player)

    def wood_crutch(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crutch Permit", self.player)
    def metal_crutch(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crutch Permit", self.player)
    def adamantine_crutch(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Crutch Permit", self.player)
    def wood_or_metal_crutch(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crutch Permit", self.player)

    def wood_minecart(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Minecart Permit", self.player)
    def metal_minecart(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Minecart Permit", self.player)
    def adamantine_minecart(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Minecart Permit", self.player)
    def wood_or_metal_minecart(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Minecart Permit", self.player)

    def wood_splint(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Splint Permit", self.player)
    def metal_splint(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Splint Permit", self.player)
    def adamantine_splint(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Splint Permit", self.player)
    def wood_or_metal_splint(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Splint Permit", self.player)
    
    def wood_stepladder(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Stepladder Permit", self.player)
    def metal_stepladder(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Stepladder Permit", self.player)
    def adamantine_stepladder(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Stepladder Permit", self.player)
    def wood_or_metal_stepladder(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Stepladder Permit", self.player)
    
    def wood_wheelbarrow(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Wheelbarrow Permit", self.player)
    def metal_wheelbarrow(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Wheelbarrow Permit", self.player)
    def adamantine_wheelbarrow(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Wheelbarrow Permit", self.player)
    def wood_or_metal_wheelbarrow(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Wheelbarrow Permit", self.player)
    
    def wood_blocks(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Blocks Permit", self.player)
    def stone_blocks(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Blocks Permit", self.player)
    def metal_blocks(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Blocks Permit", self.player)
    def adamantine_blocks(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Blocks Permit", self.player)
    def glass_blocks(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Blocks Permit", self.player)
    def ceramic_blocks(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Blocks Permit", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_blocks(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Blocks Permit", self.player)
    
    def wood_jug(self, state:CollectionState) -> bool:
            return self.craftdwarf_workshop(state) and state.has("Jug Permit", self.player)
    def stone_jug(self, state:CollectionState) -> bool:
            return self.craftdwarf_workshop(state) and state.has("Jug Permit", self.player)
    def metal_jug(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Jug Permit", self.player)
    def adamantine_jug(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Jug Permit", self.player)
    def glass_jug(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Jug Permit", self.player)
    def ceramic_jug(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Jug Permit", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_jug(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Jug Permit", self.player)
    
    def wood_pot(self, state:CollectionState) -> bool:
            return self.craftdwarf_workshop(state) and state.has("Large Pot Permit", self.player)
    def stone_pot(self, state:CollectionState) -> bool:
            return self.craftdwarf_workshop(state) and state.has("Large Pot Permit", self.player)
    def metal_pot(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Large Pot Permit", self.player)
    def adamantine_pot(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Large Pot Permit", self.player)
    def glass_pot(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Large Pot Permit", self.player)
    def ceramic_pot(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Large Pot Permit", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_pot(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Large Pot Permit", self.player)
    
    def wood_or_stone_hive(self, state:CollectionState) -> bool:
            return self.craftdwarf_workshop(state) and state.has("Hive Permit", self.player)
    def metal_hive(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Hive Permit", self.player)
    def adamantine_hive(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Hive Permit", self.player)
    def glass_hive(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Hive Permit", self.player)
    def ceramic_hive(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Hive Permit", self.player)
    def craftdwarf_or_metal_or_glass_or_ceramic_hive(self, state:CollectionState) -> bool:
            return self.craftdwarf_or_metal_or_glass_or_ceramic(state) and state.has("Hive Permit", self.player)
    
    def wood_altar(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Altar Permit", self.player)
    def stone_altar(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Altar Permit", self.player)
    def metal_altar(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Altar Permit", self.player)
    def adamantine_altar(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Altar Permit", self.player)
    def glass_altar(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Altar Permit", self.player)
    def wood_or_stone_or_metal_or_glass_altar(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Altar Permit", self.player)
    
    def wood_armorstand(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Armor Stand Permit", self.player)
    def stone_armorstand(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Armor Stand Permit", self.player)
    def metal_armorstand(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Armor Stand Permit", self.player)
    def adamantine_armorstand(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Armor Stand Permit", self.player)
    def glass_armorstand(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Armor Stand Permit", self.player)
    def wood_or_stone_or_metal_or_glass_armorstand(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Armor Stand Permit", self.player)
    
    def wood_bookcase(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Bookcase Permit", self.player)
    def stone_bookcase(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Bookcase Permit", self.player)
    def metal_bookcase(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Bookcase Permit", self.player)
    def adamantine_bookcase(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Bookcase Permit", self.player)
    def glass_bookcase(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Bookcase Permit", self.player)
    def wood_or_stone_or_metal_or_glass_bookcase(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Bookcase Permit", self.player)
    
    def wood_cabinet(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Cabinet Permit", self.player)
    def stone_cabinet(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Cabinet Permit", self.player)
    def metal_cabinet(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Cabinet Permit", self.player)
    def adamantine_cabinet(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Cabinet Permit", self.player)
    def glass_cabinet(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Cabinet Permit", self.player)
    def wood_or_stone_or_metal_or_glass_cabinet(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Cabinet Permit", self.player)
    
    def wood_burial(self, state:CollectionState) -> bool:
        return self.wood(state) and state.has("Burial Container Permit", self.player)
    def stone_burial(self, state:CollectionState) -> bool:
        return self.stone(state) and state.has("Burial Container Permit", self.player)
    def metal_burial(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Burial Container Permit", self.player)
    def adamantine_burial(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Burial Container Permit", self.player)
    def glass_burial(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Burial Container Permit", self.player)
    def wood_or_stone_or_metal_or_glass_burial(self, state:CollectionState) -> bool:
        return self.wood_or_stone_or_metal_or_glass(state) and state.has("Burial Container Permit", self.player)
    
    def wood_chair(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Chair Permit", self.player)
    def stone_chair(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Chair Permit", self.player)
    def metal_chair(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Chair Permit", self.player)
    def adamantine_chair(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Chair Permit", self.player)
    def glass_chair(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Chair Permit", self.player)
    def wood_or_stone_or_metal_or_glass_chair(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Chair Permit", self.player)
    
    def wood_container(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Container Permit", self.player)
    def stone_container(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Container Permit", self.player)
    def metal_container(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Container Permit", self.player)
    def adamantine_container(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Container Permit", self.player)
    def glass_container(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Container Permit", self.player)
    def wood_or_stone_or_metal_or_glass_container(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Container Permit", self.player)
    
    def wood_door(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Door Permit", self.player)
    def stone_door(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Door Permit", self.player)
    def metal_door(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Door Permit", self.player)
    def adamantine_door(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Door Permit", self.player)
    def glass_door(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Door Permit", self.player)
    def wood_or_stone_or_metal_or_glass_door(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Door Permit", self.player)
    
    def wood_floodgate(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Floodgate Permit", self.player)
    def stone_floodgate(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Floodgate Permit", self.player)
    def metal_floodgate(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Floodgate Permit", self.player)
    def adamantine_floodgate(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Floodgate Permit", self.player)
    def glass_floodgate(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Floodgate Permit", self.player)
    def wood_or_stone_or_metal_or_glass_floodgate(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Floodgate Permit", self.player)
    
    def wood_grate(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Grate Permit", self.player)
    def stone_grate(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Grate Permit", self.player)
    def metal_grate(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Grate Permit", self.player)
    def adamantine_grate(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Grate Permit", self.player)
    def glass_grate(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Grate Permit", self.player)
    def wood_or_stone_or_metal_or_glass_grate(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Grate Permit", self.player)
    
    def wood_hatchcover(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Hatch Cover Permit", self.player)
    def stone_hatchcover(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Hatch Cover Permit", self.player)
    def metal_hatchcover(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Hatch Cover Permit", self.player)
    def adamantine_hatchcover(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Hatch Cover Permit", self.player)
    def glass_hatchcover(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Hatch Cover Permit", self.player)
    def wood_or_stone_or_metal_or_glass_hatchcover(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Hatch Cover Permit", self.player)

    def wood_pedestal(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Pedestal Permit", self.player)
    def stone_pedestal(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Pedestal Permit", self.player)
    def metal_pedestal(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Pedestal Permit", self.player)
    def adamantine_pedestal(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Pedestal Permit", self.player)
    def glass_pedestal(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Pedestal Permit", self.player)
    def wood_or_stone_or_metal_or_glass_pedestal(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Pedestal Permit", self.player)
    
    def wood_table(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Table Permit", self.player)
    def stone_table(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Table Permit", self.player)
    def metal_table(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Table Permit", self.player)
    def adamantine_table(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Table Permit", self.player)
    def glass_table(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Table Permit", self.player)
    def wood_or_stone_or_metal_or_glass_table(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Table Permit", self.player)

    def wood_weaponrack(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Weapon Rack Permit", self.player)
    def stone_weaponrack(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Weapon Rack Permit", self.player)
    def metal_weaponrack(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Weapon Rack Permit", self.player)
    def adamantine_weaponrack(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Weapon Rack Permit", self.player)
    def glass_weaponrack(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Weapon Rack Permit", self.player)
    def wood_or_stone_or_metal_or_glass_weaponrack(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Weapon Rack Permit", self.player)
    
    def wood_statue(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Statue Permit", self.player)
    def stone_statue(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Statue Permit", self.player)
    def metal_statue(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Statue Permit", self.player)
    def adamantine_statue(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Statue Permit", self.player)
    def glass_statue(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Statue Permit", self.player)
    def ceramic_statue(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Statue Permit", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_statue(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Statue Permit", self.player)
    
    def wood_or_stone_bookbinding(self, state:CollectionState) -> bool:
            return self.craftdwarf_workshop(state) and state.has("Book Binding Permit", self.player)
    def metal_bookbinding(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Book Binding Permit", self.player)
    def adamantine_bookbinding(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Book Binding Permit", self.player)
    def glass_bookbinding(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Book Binding Permit", self.player)
    def craftdwarf_or_metal_or_glass_bookbinding(self, state:CollectionState) -> bool:
            return self.craftdwarf_or_metal_or_glass(state) and state.has("Book Binding Permit", self.player)
    
    def wood_scrollroller(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Scroll Roller Permit", self.player)
    def stone_scrollroller(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Scroll Roller Permit", self.player)
    def metal_scrollroller(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Scroll Roller Permit", self.player)
    def adamantine_scrollroller(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Scroll Roller Permit", self.player)
    def glass_scrollroller(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Scroll Roller Permit", self.player)
    def wood_or_stone_or_metal_or_glass_scrollroller(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Scroll Roller Permit", self.player)
    
    def wood_buckler(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Buckler Permit", self.player)
    def metal_buckler(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Buckler Permit", self.player)
    def adamantine_buckler(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Buckler Permit", self.player)
    def leather_buckler(self, state:CollectionState) -> bool:
            return self.leather_works(state) and state.has("Buckler Permit", self.player)
    def wood_or_leather_or_metal_buckler(self, state:CollectionState) -> bool:
            return self.wood_or_leather_or_metal(state) and state.has("Buckler Permit", self.player)
    
    def wood_shield(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Shield Permit", self.player)
    def metal_shield(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Shield Permit", self.player)
    def adamantine_shield(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Shield Permit", self.player)
    def leather_shield(self, state:CollectionState) -> bool:
            return self.leather_works(state) and state.has("Shield Permit", self.player)
    def wood_or_leather_or_metal_shield(self, state:CollectionState) -> bool:
            return self.wood_or_leather_or_metal(state) and state.has("Shield Permit", self.player)
    
    def wood_cage(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Cage Permit", self.player)
    def metal_cage(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Cage Permit", self.player)
    def adamantine_cage(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Cage Permit", self.player)
    def glass_cage(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Cage Permit", self.player)
    def wood_or_metal_or_glass_cage(self, state:CollectionState) -> bool:
            return self.wood_or_metal_or_glass(state) and state.has("Cage Permit", self.player)
    
    def wood_pipesection(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Pipe Section Permit", self.player)
    def metal_pipesection(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Pipe Section Permit", self.player)
    def adamantine_pipesection(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Pipe Section Permit", self.player)
    def glass_pipesection(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Pipe Section Permit", self.player)
    def wood_or_metal_or_glass_pipesection(self, state:CollectionState) -> bool:
            return self.wood_or_metal_or_glass(state) and state.has("Pipe Section Permit", self.player)
    
    def wood_crossbow(self, state:CollectionState) -> bool:
            return self.bowyer_workshop(state) and state.has("Crossbow Permit", self.player)
    def bone_crossbow(self, state:CollectionState) -> bool:
            return self.bowyer_workshop(state) and self.bone(state) and state.has("Crossbow Permit", self.player)
    def metal_crossbow(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crossbow Permit", self.player)
    def adamantine_crossbow(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Crossbow Permit", self.player)
    def bowyer_or_metal_crossbow(self, state:CollectionState) -> bool:
        return self.bowyer_or_metal(state) and state.has("Crossbow Permit", self.player)
    
    def wood_bolt(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Bolt Permit", self.player)
    def bone_bolt(self, state:CollectionState) -> bool:
        return self. bonecraft(state) and state.has("Bolt Permit", self.player)
    def metal_bolt(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Bolt Permit", self.player)
    def adamantine_bolt(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Bolt Permit", self.player)
    def woodcraft_or_bonecraft_or_metal_bolt(self, state:CollectionState) -> bool:
        return self.woodcraft_or_bonecraft_or_metal(state) and state.has("Bolt Permit", self.player)
    
    def stone_millstone(self, state:CollectionState) -> bool:
        return self.stone(state) and state.has("Millstone Permit", self.player)
    
    def stone_quern(self, state:CollectionState) -> bool:
        return self.stone(state) and state.has("Quern Permit", self.player)
    
    def stone_slab(self, state:CollectionState) -> bool:
        return self.stone(state) and state.has("Slab Permit", self.player)
    
    def stone_or_wood_crafts(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Crafts Permit", self.player)
    def bone_crafts(self, state:CollectionState) -> bool:
        return self.bonecraft(state) \
        and state.has("Crafts Permit", self.player)
    def metal_crafts(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Crafts Permit", self.player)
    def adamantine_crafts(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Crafts Permit", self.player)
    def glass_crafts(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Crafts Permit", self.player)
    def ceramic_crafts(self, state:CollectionState) -> bool:
        return self.ceramic(state) and state.has("Crafts Permit", self.player)
    def cloth_crafts(self, state:CollectionState) -> bool:
        if self.world.options.craftpermits == CraftingPermits.option_all:
            return self.make_cloth(state) and self.craftdwarf_workshop(state) \
            and state.has("Crafts Permit", self.player)
        else:
            return self.cloth(state) and self.craftdwarf_workshop(state) \
            and state.has("Crafts Permit", self.player)
    def leather_crafts(self, state:CollectionState) -> bool:
            return self.leather(state) and self.craftdwarf_workshop(state) \
            and state.has("Crafts Permit", self.player)
    def clothcraftdwarf(self, state:CollectionState) -> bool:
            if self.world.options.craftpermits == CraftingPermits.option_all:
                return self.make_cloth(state) and self.craftdwarf_workshop(state)
            else:
                return self.cloth(state) and self.craftdwarf_workshop(state)
    def craftdwarf_or_metal_or_glass_crafts(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal_or_glass(state) and state.has("Crafts Permit", self.player)
    
    def mechanic_mechanism(self, state:CollectionState) -> bool:
        return self.mechanic_workshop(state) and state.has("Mechanism Permit", self.player)
    def adamantine_mechanism(self, state:CollectionState) -> bool:
        return self.adamantine_mechanic_workshop(state) and state.has("Mechanism Permit", self.player)
    def adamantine_mechanic_workshop(self, state:CollectionState) -> bool:
        return self.mechanic_workshop(state) and self.adamantine_metal(state)
    
    def wood_crafting_tractionbench(self, state:CollectionState) -> bool:
        return self.wood_table(state) and self.metal_or_cloth_ropechain(state) \
            and self.mechanic_mechanism(state) and state.has("Traction Bench Permit", self.player)
    def stone_crafting_tractionbench(self, state:CollectionState) -> bool:
        return self.stone_table(state) and self.metal_or_cloth_ropechain(state) \
            and self.mechanic_mechanism(state) and state.has("Traction Bench Permit", self.player)
    def metal_crafting_tractionbench(self, state:CollectionState) -> bool:
        return self.metal_table(state) and self.metal_or_cloth_ropechain(state) \
            and self.mechanic_mechanism(state) and state.has("Traction Bench Permit", self.player)
    def adamantine_crafting_tractionbench(self, state:CollectionState) -> bool:
        return self.adamantine_table(state) and self.metal_or_cloth_ropechain(state) \
            and self.mechanic_mechanism(state) and state.has("Traction Bench Permit", self.player)
    def glass_crafting_tractionbench(self, state:CollectionState) -> bool:
        return self.glass_table(state) and self.metal_or_cloth_ropechain(state) \
            and self.mechanic_mechanism(state) and state.has("Traction Bench Permit", self.player)
    def any_crafting_tractionbench(self, state:CollectionState) -> bool:
        return (self.wood_table(state) or self.stone_table(state) or self.metal_table(state) \
            or self.glass_table(state)) and self.metal_or_cloth_ropechain(state) \
            and self.mechanic_mechanism(state) and state.has("Traction Bench Permit", self.player)
    
    def glass_liquidcontainer(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Liquid Container Permit", self.player)
    def metal_liquidcontainer(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Liquid Container Permit", self.player)
    def adamantine_liquidcontainer(self, state:CollectionState) -> bool:
            return self.adamantine_metal(state) and state.has("Liquid Container Permit", self.player)
    def leather_liquidcontainer(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Liquid Container Permit", self.player)
    def metal_or_glass_or_leather_liquidcontainer(self, state:CollectionState) -> bool:
        return self.metal_or_glass_or_leather(state) and state.has("Liquid Container Permit", self.player)
    
    def metal_or_glass_cup(self, state:CollectionState) -> bool:
        return self.metal_or_glass(state) and state.has("Cup Permit", self.player)
    def metal_cup(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Cup Permit", self.player)
    def glass_cup(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Cup Permit", self.player)
    def adamantine_cup(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Cup Permit", self.player)
    def stone_cup(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Cup Permit", self.player)
    def wood_cup(self, state:CollectionState) -> bool:
        return self.wood(state) and state.has("Cup Permit", self.player)
    
    def wood_or_stone_toy(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Toy Permit", self.player)
    def metal_toy(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Toy Permit", self.player)
    def adamantine_toy(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Toy Permit", self.player)
    def glass_toy(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Toy Permit", self.player)
    def craftdwarf_or_metal_or_glass_toy(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal_or_glass(state) and state.has("Toy Permit", self.player)
    
    def craftdwarf_and_butchery_totem(self, state:CollectionState) -> bool:
        return self.craftdwarf_and_butchery(state) and state.has("Totem Permit", self.player)
    
    def bone_helm(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Helm Permit", self.player)
    def metal_helm(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Helm Permit", self.player)
    def adamantine_helm(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Helm Permit", self.player)
    def leather_helm(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Helm Permit", self.player)
    def metal_or_bone_or_leather_helm(self, state:CollectionState) -> bool:
        return self.metal_or_bone_or_leather(state) and state.has("Helm Permit", self.player)
    
    def seige_ballistaparts(self, state:CollectionState) -> bool:
        return self.seige_workshop(state) and state.has("Ballista Parts Permit", self.player)
    
    def seige_catapultparts(self, state:CollectionState) -> bool:
        return self.seige_workshop(state) and state.has("Catapult Parts Permit", self.player)
    
    def seige_boltthrowerparts(self, state:CollectionState) -> bool:
        return self.seige_workshop(state) and state.has("Bolt Thrower Parts Permit", self.player)
    
    def seige_arrows(self, state:CollectionState) -> bool:
        return self.seige_workshop(state) and state.has("Ballista Arrows Permit", self.player)
    def seige_metal_arrows(self, state:CollectionState) -> bool:
        return self.seige_and_metal(state) and state.has("Ballista Arrows Permit", self.player)
    def seige_adamantine_arrows(self, state:CollectionState) -> bool:
        return self.seige_workshop(state) and self.adamantine_metal(state) and state.has("Ballista Arrows Permit", self.player)
    
    def ash(self, state:CollectionState) -> bool:
        return self.wood_furnace(state) and state.has("Ash Permit", self.player)
    def charcoal(self, state:CollectionState) -> bool:
        return self.wood_furnace(state) and state.has("Charcoal Permit", self.player)
    
    def metal_bars(self, state:CollectionState) -> bool:
        return self.process_resource(state, "metal")
    def coke_bars(self, state:CollectionState) -> bool:
        return self.process_resource(state, "coke")
    
    def pearlash(self, state:CollectionState) -> bool:
        return self.ceramic(state) and state.has("Pearlash Permit", self.player)
    def plaster(self, state:CollectionState) -> bool:
        return self.ceramic(state) and state.has("Gypsum Plaster Permit", self.player)
    def quicklime(self, state:CollectionState) -> bool:
        return self.ceramic(state) and state.has("Quicklime Permit", self.player)
    
    def make_glass(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Glass Permit", self.player)
    def glass_window(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Window Permit", self.player)
    
    def make_leather(self, state:CollectionState) -> bool:
        return self.leather(state) and state.has("Leather Permit", self.player)
    
    def make_sheet(self, state:CollectionState) -> bool:
        return self.make_paper(state) and state.has("Sheet Permit", self.player)
    
    def make_cloth(self, state:CollectionState) -> bool:
        return self.cloth(state) and state.has("Cloth Permit", self.player)
    
    def make_alcohol(self, state:CollectionState) -> bool:
        return self.still(state) and state.has("Alcohol Permit", self.player)
    
    def ashery_and_wood_furnace_lye(self, state:CollectionState) -> bool:
        return self.ash(state) and state.has("Lye Permit", self.player)
    def ashery_and_wood_furnace_potash(self, state:CollectionState) -> bool:
        return (self.ash(state) or self.ashery_and_wood_furnace_lye(state)) and state.has("Potash Permit", self.player)
    def ashery_and_kiln_milklime(self, state:CollectionState) -> bool:
        return self.ashery_and_kiln(state) and state.has("Milk of Lime Permit", self.player)
    
    def make_meal(self, state:CollectionState) -> bool:
        return self.kitchen(state) and state.has("Prepared Meal Permit", self.player)
    
    def make_tallow(self, state:CollectionState) -> bool:
        return self.kitchen_and_butchershop(state) and state.has("Tallow Permit", self.player)
    
    def make_oil(self, state:CollectionState) -> bool:
        return self.screw_press(state) and state.has("Oil Permit", self.player)
    
    def make_honey(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic == True:
             return self.screw_press(state) and state.has("Honey Permit", self.player) 
        else:
            return self.screw_press(state) and self.wood_or_stone_or_metal_or_glass_or_ceramic_jug(state) \
            and state.has("Honey Permit", self.player) 
    
    def metal_gauntlets(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Gauntlets Permit", self.player)
    def adamantine_gauntlets(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Gauntlets Permit", self.player)
    def bone_gauntlets(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Gauntlets Permit", self.player)
    def metal_or_bone_gauntlets(self, state:CollectionState) -> bool:
        return self.metal_or_bone(state) and state.has("Gauntlets Permit", self.player)
    
    def dye_dye(self, state:CollectionState) -> bool:
        return self.dye(state) and state.has("Dye Permit", self.player) and self.wood_or_metal_bucket(state)
    
    def cloth_bag(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Bag Permit", self.player)
    def leather_bag(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Bag Permit", self.player)
    def leather_or_cloth_bag(self, state:CollectionState) -> bool:
        return self.leather_or_cloth(state) and state.has("Bag Permit", self.player)
    
    def metal_chain(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Rope/Chain Permit", self.player)
    def adamantine_chain(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Rope/Chain Permit", self.player)
    def make_rope(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Rope/Chain Permit", self.player)
    def metal_or_cloth_ropechain(self, state:CollectionState) -> bool:
        return self.metal_or_cloth(state) and state.has("Rope/Chain Permit", self.player)

    def metal_battleaxe(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Battle Axe Permit", self.player)
    def adamantine_battleaxe(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Battle Axe Permit", self.player)
    
    def metal_mace(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Mace Permit", self.player)
    def adamantine_mace(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Mace Permit", self.player)
    
    def metal_pick(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Pick Permit", self.player)
    def adamantine_pick(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Pick Permit", self.player)
    
    def metal_sword(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Short Sword Permit", self.player)
    def adamantine_sword(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Short Sword Permit", self.player)
    
    def metal_spear(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Spear Permit", self.player)
    def adamantine_spear(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Spear Permit", self.player)
    
    def metal_warhammer(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("War Hammer Permit", self.player)
    def adamantine_warhammer(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("War Hammer Permit", self.player)
    
    def metal_anvil(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Anvil Permit", self.player)
    def adamantine_anvil(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Anvil Permit", self.player)
    
    def metal_coins(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Coins Permit", self.player)
    def adamantine_coins(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Coins Permit", self.player)
    
    def make_soap(self, state:CollectionState) -> bool:
        return self.ashery_and_wood_furnace_lye(state) and (self.make_tallow(state) or self.make_oil(state)) \
        and state.has("Soap Permit", self.player) and (state.has("Soap Maker's Workshop Blueprint", self.player) \
        and self.wood_or_metal_bucket(state))
    
    def make_displaycase(self, state:CollectionState) -> bool:
        return self.make_glass(state) and self.wood(state) and state.has("Display Case Permit", self.player) 
    
    def adamantine_backpack(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Backpack Permit", self.player) 
    def leather_backpack(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Backpack Permit", self.player) 
    def adamantinecloth_or_leather_backpack(self, state:CollectionState) -> bool:
        return self.adamantine_backpack(state) or self.leather_backpack(state) 
    
    def adamantine_quiver(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Quiver Permit", self.player) 
    def leather_quiver(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Quiver Permit", self.player) 
    def adamantinecloth_or_leather_quiver(self, state:CollectionState) -> bool:
        return self.adamantine_quiver(state) or self.leather_quiver(state)
    
    def craftdwarf_amulet(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Amulet Permit", self.player)
    def bonecraftdwarf_amulet(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Amulet Permit", self.player)
    def leather_amulet(self, state:CollectionState) -> bool:
        return self.leathercraft(state) and state.has("Amulet Permit", self.player)
    def metal_amulet(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Amulet Permit", self.player)
    def adamantine_amulet(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Amulet Permit", self.player)
    def craftdwarf_or_metal_amulet(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal(state) and state.has("Amulet Permit", self.player)
    
    def craftdwarf_bracelet(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Bracelet Permit", self.player)
    def bonecraftdwarf_bracelet(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Bracelet Permit", self.player)
    def leather_bracelet(self, state:CollectionState) -> bool:
        return self.leathercraft(state) and state.has("Bracelet Permit", self.player)
    def metal_bracelet(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Bracelet Permit", self.player)
    def adamantine_bracelet(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Bracelet Permit", self.player)
    def craftdwarf_or_metal_bracelet(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal(state) and state.has("Bracelet Permit", self.player)
    
    def craftdwarf_earring(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Earring Permit", self.player)
    def bonecraftdwarf_earring(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Earring Permit", self.player)
    def clothcraftdwarf_earring(self, state:CollectionState) -> bool:
        return self.clothcraftdwarf(state) and state.has("Earring Permit", self.player)
    def leather_earring(self, state:CollectionState) -> bool:
        return self.leathercraft(state) and state.has("Earring Permit", self.player)
    def metal_earring(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Earring Permit", self.player)
    def adamantine_earring(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Earring Permit", self.player)
    def craftdwarf_or_metal_earring(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal(state) and state.has("Earring Permit", self.player)
    
    def craftdwarf_crown(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Crown Permit", self.player)
    def bonecraftdwarf_crown(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Crown Permit", self.player)
    def metal_crown(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Crown Permit", self.player)
    def adamantine_crown(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Crown Permit", self.player)
    def craftdwarf_or_metal_crown(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal(state) and state.has("Crown Permit", self.player)
    
    def craftdwarf_die(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Die Permit", self.player)
    def bonecraftdwarf_die(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Die Permit", self.player)
    def metal_die(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Die Permit", self.player)
    def adamantine_die(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Die Permit", self.player)
    def glass_die(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Die Permit", self.player)
    def craftdwarf_or_metal_or_glass_die(self, state:CollectionState) -> bool:
        return (self.craftdwarf_or_metal(state) or self.glass(state)) and state.has("Die Permit", self.player)


    def craftdwarf_figurine(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Figurine Permit", self.player)
    def bonecraftdwarf_figurine(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Figurine Permit", self.player)
    def metal_figurine(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Figurine Permit", self.player)
    def adamantine_figurine(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Figurine Permit", self.player)
    def craftdwarf_or_metal_figurine(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal(state) and state.has("Figurine Permit", self.player)
    
    def craftdwarf_nestbox(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Nest Box Permit", self.player)
    def bonecraftdwarf_nestbox(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Nest Box Permit", self.player)
    def metal_nestbox(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Nest Box Permit", self.player)
    def adamantine_nestbox(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Nest Box Permit", self.player)
    def glass_nestbox(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Nest Box Permit", self.player)
    def craftdwarf_or_metal_or_glass_nestbox(self, state:CollectionState) -> bool:
        return (self.craftdwarf_or_metal(state) or self.glass(state)) and state.has("Nest Box Permit", self.player)
    
    def craftdwarf_ring(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Ring Permit", self.player)
    def bonecraftdwarf_ring(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Ring Permit", self.player)
    def metal_ring(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Ring Permit", self.player)
    def adamantine_ring(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Ring Permit", self.player)
    def craftdwarf_or_metal_ring(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal(state) and state.has("Ring Permit", self.player)
    
    def craftdwarf_scepter(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Scepter Permit", self.player)
    def bonecraftdwarf_scepter(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Scepter Permit", self.player)
    def metal_scepter(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Scepter Permit", self.player)
    def adamantine_scepter(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Scepter Permit", self.player)
    def craftdwarf_or_metal_scepter(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal(state) and state.has("Scepter Permit", self.player)
    
    def make_quire(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Quire Permit", self.player) \
        and self.make_sheet(state)
    def quire(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and self.make_paper(state)
    
    def make_scroll(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Quire Permit", self.player) \
        and self.make_sheet(state) and self.wood_or_stone_or_metal_or_glass_scrollroller(state)
    def scroll(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and self.make_paper(state)
    
    def metal_mailshirt(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Mail Shirt Permit", self.player)
    def adamantine_mailshirt(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Mail Shirt Permit", self.player)
    
    def metal_breastplate(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Breastplate Permit", self.player)
    def adamantine_breastplate(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Breastplate Permit", self.player)
    
    def cloth_gloves(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Gloves Permit", self.player)
    def adamantine_gloves(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Gloves Permit", self.player)
    def leather_gloves(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Gloves Permit", self.player)
    def leather_or_cloth_or_adamantine_gloves(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Gloves Permit", self.player)
    
    def cloth_mittens(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Mittens Permit", self.player)
    def adamantine_mittens(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Mittens Permit", self.player)
    def leather_mittens(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Mittens Permit", self.player)
    def leather_or_cloth_or_adamantine_mittens(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Mittens Permit", self.player)
    
    def cloth_loincloth(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Loincloth Permit", self.player)
    def adamantine_loincloth(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Loincloth Permit", self.player)
    def leather_loincloth(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Loincloth Permit", self.player)
    def leather_or_cloth_or_adamantine_loincloth(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Loincloth Permit", self.player)
    
    def cloth_trousers(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Trousers Permit", self.player)
    def adamantine_trousers(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Trousers Permit", self.player)
    def leather_trousers(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Trousers Permit", self.player)
    def leather_or_cloth_or_adamantine_trousers(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Trousers Permit", self.player)
    
    def bone_leggings(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Leggings Permit", self.player)
    def metal_leggings(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Leggings Permit", self.player)
    def adamantine_leggings(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Leggings Permit", self.player)
    def leather_leggings(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Leggings Permit", self.player)
    def metal_or_bone_or_leather_leggings(self, state:CollectionState) -> bool:
        return self.metal_or_bone_or_leather(state) and state.has("Leggings Permit", self.player)
    
    def metal_greaves(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Greaves Permit", self.player)
    def adamantine_greaves(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Greaves Permit", self.player)
    def bone_greaves(self, state:CollectionState) -> bool:
        return self.bonecraft(state) and state.has("Greaves Permit", self.player)
    def metal_or_bone_greaves(self, state:CollectionState) -> bool:
        return self.metal_or_bone(state) and state.has("Greaves Permit", self.player)
    
    def cloth_socks(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Socks Permit", self.player)
    def adamantine_socks(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Socks Permit", self.player)
    def cloth_or_adamantine_socks(self, state:CollectionState) -> bool:
        return self.cloth_socks(state) or self.adamantine_socks(state)

    def cloth_shoes(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Shoes Permit", self.player)
    def adamantine_shoes(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Shoes Permit", self.player)
    def leather_shoes(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Shoes Permit", self.player)
    def leather_or_cloth_or_adamantine_shoes(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Shoes Permit", self.player)

    def metal_lboots(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Low Boots Permit", self.player)
    def adamantine_lboots(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Low Boots Permit", self.player)
    def leather_lboots(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Low Boots Permit", self.player)
    def metal_or_leather_lboots(self, state:CollectionState) -> bool:
        return self.metal_or_leather(state) and state.has("Low Boots Permit", self.player)
    
    def metal_hboots(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("High Boots Permit", self.player)
    def adamantine_hboots(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("High Boots Permit", self.player)
    def leather_hboots(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("High Boots Permit", self.player)
    def metal_or_leather_hboots(self, state:CollectionState) -> bool:
        return self.metal_or_bone_or_leather(state) and state.has("High Boots Permit", self.player)
    
    def make_codex(self, state:CollectionState) -> bool:
        return self.make_quire(state) and state.has("Codex Permit", self.player) \
        and self.craftdwarf_or_metal_or_glass_bookbinding(state)
    def codex(self, state:CollectionState) -> bool:
        return self.quire(state) and self.craftdwarf_or_metal_or_glass(state)
    
    def metal_axeblade(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Giant Axe Blade Permit", self.player)
    def adamantine_axeblade(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Giant Axe Blade Permit", self.player)
    def glass_axeblade(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Giant Axe Blade Permit", self.player)
    def metal_or_glass_axeblade(self, state:CollectionState) -> bool:
        return self.metal_or_glass(state) and state.has("Giant Axe Blade Permit", self.player)

    def metal_disc(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Serrated Disc Permit", self.player)
    def adamantine_disc(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Serrated Disc Permit", self.player)
    def glass_disc(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Serrated Disc Permit", self.player)
    def metal_or_glass_disc(self, state:CollectionState) -> bool:
        return self.metal_or_glass(state) and state.has("Serrated Disc Permit", self.player)
    
    def cloth_cap(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Cap Permit", self.player)
    def leather_cap(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Cap Permit", self.player)
    def metal_cap(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Cap Permit", self.player)
    def adamantine_cap(self, state:CollectionState) -> bool:
        return self.adamantine_metal(state) and state.has("Cap Permit", self.player)
    def metal_or_cloth_or_leather_cap(self, state:CollectionState) -> bool:
        return self.metal_or_cloth_or_leather(state) and state.has("Cap Permit", self.player)
    
    def cloth_hood(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Hood Permit", self.player)
    def adamantine_hood(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Hood Permit", self.player)
    def leather_hood(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Hood Permit", self.player)
    def leather_or_cloth_or_adamantine_hood(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Hood Permit", self.player)
    
    def cloth_shirt(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Shirt Permit", self.player)
    def adamantine_shirt(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Shirt Permit", self.player)
    def leather_shirt(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Shirt Permit", self.player)
    def leather_or_cloth_or_adamantine_shirt(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Shirt Permit", self.player)
    
    def cloth_vest(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Vest Permit", self.player)
    def adamantine_vest(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Vest Permit", self.player)
    def leather_vest(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Vest Permit", self.player)
    def leather_or_cloth_or_adamantine_vest(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Vest Permit", self.player)
    
    def cloth_coat(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Coat Permit", self.player)
    def adamantine_coat(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Coat Permit", self.player)
    def leather_coat(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Coat Permit", self.player)
    def leather_or_cloth_or_adamantine_coat(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Coat Permit", self.player)
    
    def cloth_cloak(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Cloak Permit", self.player)
    def adamantine_cloak(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Cloak Permit", self.player)
    def leather_cloak(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Cloak Permit", self.player)
    def leather_or_cloth_or_adamantine_cloak(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Cloak Permit", self.player)
    
    def leather_leatherarmor(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Leather Armor Permit", self.player)
    
    def cloth_tunic(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Tunic Permit", self.player)
    def adamantine_tunic(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Tunic Permit", self.player)
    def leather_tunic(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Tunic Permit", self.player)
    def leather_or_cloth_or_adamantine_tunic(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Tunic Permit", self.player)
    
    def cloth_dress(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Dress Permit", self.player)
    def adamantine_dress(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Dress Permit", self.player)
    def leather_dress(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Dress Permit", self.player)
    def leather_or_cloth_or_adamantine_dress(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Dress Permit", self.player)
    
    def cloth_toga(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Toga Permit", self.player)
    def adamantine_toga(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Toga Permit", self.player)
    def leather_toga(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Toga Permit", self.player)
    def leather_or_cloth_or_adamantine_toga(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Toga Permit", self.player)
    
    def cloth_robe(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Robe Permit", self.player)
    def adamantine_robe(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Robe Permit", self.player)
    def leather_robe(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Robe Permit", self.player)
    def leather_or_cloth_or_adamantine_robe(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Robe Permit", self.player)
    
    def cloth_braies(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Braies Permit", self.player)
    def adamantine_braies(self, state:CollectionState) -> bool:
        return self.adamantine_cloth(state) and state.has("Braies Permit", self.player)
    def leather_braies(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Braies Permit", self.player)
    def leather_or_cloth_or_adamantine_braies(self, state:CollectionState) -> bool:
        return self.leather_or_cloth_or_adamantinecloth(state) and state.has("Braies Permit", self.player)
    
    def leather_products(self, state:CollectionState) -> bool:
        return self.leather_cap(state) or self.leather_hood(state) \
        or self.leather_shirt(state) or self.leather_vest(state) \
        or self.leather_coat(state) or self.leather_leatherarmor(state) \
        or self.leather_cloak(state) or self.leather_bag(state) \
        or self.make_leather_backpack(state) or self.make_leather_quiver(state) \
        or self.leather_gloves(state) or self.leather_mittens(state) \
        or self.leather_loincloth(state) or self.leather_trousers(state) \
        or self.leather_leggings(state) or self.leather_shoes(state) \
        or self.leather_lboots(state) or self.leather_hboots(state) \
        or self.leather_buckler(state) or self.leather_shield(state) \
        or self.leather_crafts(state) or self.leather_amulet(state) \
        or self.leather_bracelet(state) or self.leather_earring(state) \
        or self.leather_tunic(state) or self.leather_dress(state) \
        or self.leather_toga(state) or self.leather_robe(state) \
        or self.leather_braies(state)
    
    def metal_cloth_and_armor(self, state:CollectionState) -> bool:
        return self.metal_cap(state) or self.metal_helm(state) \
        or self.metal_mailshirt(state) or self.metal_breastplate(state) \
        or self.metal_gauntlets(state) or self.metal_leggings(state) \
        or self.metal_greaves(state) or self.metal_lboots(state) \
        or self.metal_hboots(state) or self.metal_buckler(state) \
        or self.metal_shield(state) or self.adamantine_mailshirt(state) \
        or self.adamantine_breastplate(state) or self.adamantine_socks(state) \
        or self.adamantine_hood(state) or self.adamantine_cap(state) \
        or self.adamantine_tunic(state) or self.adamantine_shirt(state) \
        or self.adamantine_dress(state) or self.adamantine_vest(state) \
        or self.adamantine_toga(state) or self.adamantine_coat(state) \
        or self.adamantine_robe(state) or self.adamantine_cloak(state) \
        or self.adamantine_gloves(state) or self.adamantine_mittens(state) \
        or self.adamantine_gauntlets(state) or self.adamantine_loincloth(state) \
        or self.adamantine_braies(state) or self.adamantine_trousers(state) \
        or self.adamantine_leggings(state) or self.adamantine_greaves(state) \
        or self.adamantine_shoes(state) or self.adamantine_lboots(state) \
        or self.adamantine_hboots(state) or self.adamantine_shield(state) \
        or self.adamantine_buckler(state)
    
    def bone_products(self, state:CollectionState) -> bool:
        return self.bone_bolt(state) or self.bone_crossbow(state) \
        or self.bone_crafts(state) or self.bone_gauntlets(state) \
        or self.bone_greaves(state) or self.bone_helm(state) \
        or self.bone_leggings(state) or self.bonecraftdwarf_amulet(state) \
        or self.bonecraftdwarf_bracelet(state) or self.bonecraftdwarf_crown(state) \
        or self.bonecraftdwarf_die(state) or self.bonecraftdwarf_earring(state) \
        or self.bonecraftdwarf_figurine(state) or self.bonecraftdwarf_nestbox(state) \
        or self.bonecraftdwarf_ring(state) or self.bonecraftdwarf_scepter(state) 
    
    def cloth_products(self, state:CollectionState) -> bool:
        return self.cloth_bag(state) or self.cloth_cap(state) \
        or self.cloth_crafts(state) or self.cloth_hood(state) \
        or self.cloth_shirt(state) or self.cloth_vest(state) \
        or self.cloth_coat(state) or self.cloth_cloak(state) \
        or self.cloth_gloves(state) or self.cloth_mittens(state) \
        or self.cloth_loincloth(state) or self.cloth_trousers(state) \
        or self.cloth_socks(state) or self.cloth_shoes(state) \
        or self.cloth_tunic(state) or self.cloth_dress(state) \
        or self.cloth_toga(state) or self.cloth_robe(state) \
        or self.cloth_braies(state)
    
    def armor(self, state:CollectionState) -> bool:
        return (self.metal_mailshirt(state) or self.metal_breastplate(state) \
        or self.leather_leatherarmor(state) or self.adamantine_mailshirt(state) or self.adamantine_breastplate(state)) \
        and (self.metal_or_bone_or_leather_leggings(state) or self.metal_or_bone_greaves(state))
        
    
    def set_dynamic_rules(self) -> None:
        for location in self.world.dynamic_locations:
            self.world.multiworld
            loc = self.world.multiworld.get_location(location.name, self.player)
            self.df_location_rule(loc, location.df_item, location.material_type)        

    def df_location_rule(self, loc, item_name, material_type) -> None:
        match item_name:
            case "Beds": 
                if self.world.options.craftpermits == CraftingPermits.option_all:
                    set_rule(loc, self.bed)
                else:
                    set_rule(loc, self.wood)
            case "Training Axe":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.training_axe)
                else:
                    set_rule(loc, self.wood)
            case "Training Spear":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.training_spear)
                else:
                    set_rule(loc, self.wood)
            case  "Training Sword":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.training_sword)
                else:
                    set_rule(loc, self.wood)
            case "Corkscrew":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_corkscrew)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_corkscrew)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_corkscrew)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_corkscrew)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_or_glass_corkscrew)
                    else:
                        set_rule(loc, self.wood_or_metal_or_glass)
            case "Menacing Spike":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_spike)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_spike)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_spike)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_spike)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Spiked Ball":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_ball)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_ball)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_ball)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_ball)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_ball)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Animal Trap":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_animal_trap)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_animal_trap)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_animal_trap)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_animal_trap)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Barrel":
                if material_type == "Wood":
                    if self.world.options.craftpermits == CraftingPermits.option_all:
                        set_rule(loc, self.wood_barrel)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits == CraftingPermits.option_all:
                        set_rule(loc, self.metal_barrel)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits == CraftingPermits.option_all:
                        set_rule(loc, self.adamantine_barrel)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits == CraftingPermits.option_all:
                        set_rule(loc, self.wood_or_metal_barrel)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Bin":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_bin)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_bin)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_bin)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_bin)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Bucket":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_bucket)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_bucket)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_bucket)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_bucket)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Crutch":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_crutch)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_crutch)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_crutch)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_crutch)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Minecart":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_minecart)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_minecart)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_minecart)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_minecart)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Splint":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_splint)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_splint)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_splint)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_splint)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Stepladder":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_stepladder)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_stepladder)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_stepladder)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_stepladder)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Wheelbarrow":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_wheelbarrow)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_wheelbarrow)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_wheelbarrow)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_wheelbarrow)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Blocks":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_blocks)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_blocks)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_blocks)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_blocks)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_blocks)
                    else:
                        set_rule(loc, self.glass)
                elif material_type == "Ceramic":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.ceramic_blocks)
                    else:
                        set_rule(loc, self.ceramic)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic_blocks)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
            case "Jug":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_jug)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_jug)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_jug)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_jug)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_jug)
                    else:
                        set_rule(loc, self.glass)
                elif material_type == "Ceramic":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.ceramic_jug)
                    else:
                        set_rule(loc, self.ceramic)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic_jug)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
            case "Large Pot":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_pot)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_pot)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_pot)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_pot)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_pot)
                    else:
                        set_rule(loc, self.glass)
                elif material_type == "Ceramic":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.ceramic_pot)
                    else:
                        set_rule(loc, self.ceramic)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic_pot)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
            case "Hive":
                if material_type in {"Wood", "Stone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_hive)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_hive)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_hive)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_hive)
                    else:
                        set_rule(loc, self.glass)
                elif material_type == "Ceramic":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.ceramic_hive)
                    else:
                        set_rule(loc, self.ceramic)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass_or_ceramic_hive)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass_or_ceramic)
            case "Altar":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_altar)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_altar)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_altar)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_altar)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_altar)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_altar)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Armor Stand":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_armorstand)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_armorstand)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_armorstand)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_armorstand)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_armorstand)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_armorstand)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Bookcase":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_bookcase)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_bookcase)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_bookcase)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_bookcase)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_bookcase)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_bookcase)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Cabinet":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_cabinet)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_cabinet)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_cabinet)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_cabinet)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_cabinet)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_cabinet)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Burial Container":
                if material_type == "Wood":
                    if self.world.options.craftpermits == CraftingPermits.option_all:
                        set_rule(loc, self.wood_burial)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits == CraftingPermits.option_all:
                        set_rule(loc, self.stone_burial)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits == CraftingPermits.option_all:
                        set_rule(loc, self.metal_burial)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits == CraftingPermits.option_all:
                        set_rule(loc, self.adamantine_burial)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits == CraftingPermits.option_all:
                        set_rule(loc, self.glass_burial)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits == CraftingPermits.option_all:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_burial)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Chair":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_chair)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_chair)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_chair)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_chair)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_chair)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_chair)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Container":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_container)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_container)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_container)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_container)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_container)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_container)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Door":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_door)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_door)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_door)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_door)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_door)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_door)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Floodgate":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_floodgate)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_floodgate)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_floodgate)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_floodgate)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_floodgate)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_floodgate)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Grate":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_grate)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_grate)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_grate)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_grate)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_grate)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_grate)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Hatch Cover":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_hatchcover)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_hatchcover)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_hatchcover)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_hatchcover)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_hatchcover)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_hatchcover)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Pedestal":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_pedestal)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_pedestal)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_pedestal)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_pedestal)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_pedestal)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_pedestal)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Table":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_table)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_table)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_table)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_table)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_table)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_table)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Weapon Rack":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_weaponrack)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_weaponrack)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_weaponrack)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_weaponrack)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_weaponrack)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_weaponrack)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Statue":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_statue)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_statue)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_statue)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_statue)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_statue)
                    else:
                        set_rule(loc, self.glass)
                elif material_type == "Ceramic":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.ceramic_statue)
                    else:
                        set_rule(loc, self.ceramic)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic_statue)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
            case "Book Binding":
                if material_type in {"Wood", "Stone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_bookbinding)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_bookbinding)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_bookbinding)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_bookbinding)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass_bookbinding)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass)
            case "Scroll Roller":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_scrollroller)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_scrollroller)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_scrollroller)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_scrollroller)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_scrollroller)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_scrollroller)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Buckler":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_buckler)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_buckler)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_buckler)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_buckler)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_leather_or_metal_buckler)
                    else:
                        set_rule(loc, self.wood_or_leather_or_metal)
            case "Shield":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_shield)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_shield)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_shield)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_shield)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_leather_or_metal_shield)
                    else:
                        set_rule(loc, self.wood_or_leather_or_metal)
            case "Cage":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_cage)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_cage)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_cage)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_cage)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_or_glass_cage)
                    else:
                        set_rule(loc, self.wood_or_metal_or_glass)
            case "Pipe Section":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_pipesection)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_pipesection)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_pipesection)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_pipesection)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_or_glass_pipesection)
                    else:
                        set_rule(loc, self.wood_or_metal_or_glass)
            case "Crossbow":
                if type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_crossbow)
                    else:
                        set_rule(loc, self.bowyer_workshop)
                elif type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bone_crossbow)
                    else:
                        set_rule(loc, self.bone_bowyer_workshop)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_crossbow)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_crossbow)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bowyer_or_metal_crossbow)
                    else:
                        set_rule(loc, self.bowyer_or_metal)
            case "Bolt":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_bolt)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bone_bolt)
                    else:
                        set_rule(loc, self.bonecraft)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_bolt)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_bolt)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.woodcraft_or_bonecraft_or_metal_bolt)
                    else:
                        set_rule(loc, self.woodcraft_or_bonecraft_or_metal)
            case "Millstone":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.stone_millstone)
                else:
                    set_rule(loc, self.stone)
            case "Quern":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.stone_quern)
                else:
                    set_rule(loc, self.stone)
            case "Slab":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.stone_slab)
                else:
                    set_rule(loc, self.stone)
            case "Crafts":
                if material_type in {"Wood", "Stone", "Bone"} :
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_or_wood_crafts)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Glass":  
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_crafts)
                    else:
                        set_rule(loc, self.glass)
                elif material_type == "Ceramic":  
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.ceramic_crafts)
                    else:
                        set_rule(loc, self.ceramic)
                elif material_type == "Cloth":  
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_crafts)
                    else:
                        set_rule(loc, self.clothcraftdwarf)
                elif material_type == "Leather":  
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_crafts)
                    else:
                        set_rule(loc, self.leathercraft)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_crafts)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_crafts)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass_crafts)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass)
            case "Mechanism": #done in job manager, only needs Mechanic Shop
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_mechanism)
                    else:
                        set_rule(loc, self.adamantine_mechanic_workshop)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.mechanic_mechanism)
                    else:
                        set_rule(loc, self.mechanic_workshop)
            case "Traction Bench":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_crafting_tractionbench)
                    else:
                        set_rule(loc, self.wooden_traction_bench)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_crafting_tractionbench)
                    else:
                        set_rule(loc, self.stone_traction_bench)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_crafting_tractionbench)
                    else:
                        set_rule(loc, self.metal_traction_bench)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_crafting_tractionbench)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_crafting_tractionbench)
                    else:
                        set_rule(loc, self.glass_traction_bench)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.any_crafting_tractionbench)
                    else:
                        set_rule(loc, self.any_traction_bench)
            case "Liquid Container":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                            set_rule(loc, self.metal_liquidcontainer)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_liquidcontainer)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                            set_rule(loc, self.metal_liquidcontainer)
                    else:
                        set_rule(loc, self.glass)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                            set_rule(loc, self.leather_liquidcontainer)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                            set_rule(loc, self.metal_or_glass_or_leather_liquidcontainer)
                    else:
                        set_rule(loc, self.metal_or_glass_or_leather)
            case "Goblet":
                if material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_cup)
                    else:
                        set_rule(loc, self.glass)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_cup)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_cup)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                            set_rule(loc, self.metal_or_glass_cup)
                    else:
                        set_rule(loc, self.metal_or_glass)
            case "Mug":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.stone_cup)
                else:
                    set_rule(loc, self.craftdwarf_workshop)
            case "Cup":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.wood_cup)
                else:
                    set_rule(loc, self.wood)  
            case "Toy":
                if material_type in {"Wood", "Stone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_toy)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_toy)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_toy)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_toy)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass_toy)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Totem":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.craftdwarf_and_butchery_totem)
                else:
                    set_rule(loc, self.craftdwarf_and_butchery)
            case "Helm":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                            set_rule(loc, self.metal_helm)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_helm)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bone_helm)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_helm)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_bone_or_leather_helm)
                    else:
                        set_rule(loc, self.metal_or_bone_or_leather)
            case "Ballista Parts":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.seige_ballistaparts)
                else:
                    set_rule(loc, self.seige_workshop)
            case "Catapult Parts":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.seige_catapultparts)
                else:
                    set_rule(loc, self.seige_workshop)
            case "Ballista Arrows":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.seige_arrows)
                    else:
                        set_rule(loc, self.seige_workshop)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.seige_metal_arrows)
                    else:
                        set_rule(loc, self.seige_and_metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.seige_adamantine_arrows)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.seige_arrows)
                    else:
                        set_rule(loc, self.seige_workshop)
            case "Ash":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.ash)
                else:
                    set_rule(loc, self.wood_furnace)
            case "Charcoal":
                if self.world.options.craftpermits == CraftingPermits.option_all:
                    set_rule(loc, self.charcoal)
                else:
                    set_rule(loc, self.wood_furnace)
            case "Metal Bars":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.metal_bars)
                else:
                    set_rule(loc, self.make_metal)
            case "Coke Bars":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.coke_bars)
                else:
                    set_rule(loc, self.make_metal)
            case "Pearlash":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.pearlash)
                else:
                    set_rule(loc, self.ceramic)
            case "Gypsum Plaster":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.plaster)
                else:
                    set_rule(loc, self.ceramic)
            case "Quicklime":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.quicklime)
                else:
                    set_rule(loc, self.ceramic)
            case "Glass":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_glass)
                else:
                    set_rule(loc, self.glass)
            case "Window":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.glass_window)
                else:
                    set_rule(loc, self.glass)
            case "Leather":
                if self.world.options.craftpermits == CraftingPermits.option_all:
                    set_rule(loc, self.make_leather)
                else:
                    set_rule(loc, self.leather)
            case "Sheet":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_sheet)
                else:
                    set_rule(loc, self.make_paper)
            case "Cloth":
                if self.world.options.craftpermits == CraftingPermits.option_all:
                    set_rule(loc, self.make_cloth)
                else:
                    set_rule(loc, self.cloth)
            case "Alcohol":
                if self.world.options.craftpermits == CraftingPermits.option_all:
                    set_rule(loc, self.make_alcohol)
                else:
                    set_rule(loc, self.still)
            case "Lye":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.ashery_and_wood_furnace_lye)
                else:
                    set_rule(loc, self.ashery_and_wood_furnace)
            case "Potash":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.ashery_and_wood_furnace_potash)
                else:
                    set_rule(loc, self.ashery_and_wood_furnace)
            case "Milk of Lime":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.ashery_and_kiln_milklime)
                else:
                    set_rule(loc, self.ashery_and_kiln)
            case "Prepared Meal":
                if self.world.options.craftpermits == CraftingPermits.option_all:
                    set_rule(loc, self.make_meal)
                else:
                    set_rule(loc, self.kitchen)
            case "Tallow":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_tallow)
                else:
                    set_rule(loc, self.kitchen_and_butchershop)
            case "Oil" | "Press Cake":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_oil)
                else:
                    set_rule(loc, self.screw_press)
            case "Honey" | "Bee Wax":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_honey)
                else:
                    set_rule(loc, self.screw_press)
            case "Gauntlets":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_gauntlets)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_gauntlets)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bone_gauntlets)
                    else:
                        set_rule(loc, self.bonecraft)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_bone_gauntlets)
                    else:
                        set_rule(loc, self.metal_or_bone)  
            case "Dye":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.dye_dye)
                else:
                    set_rule(loc, self.dye)
            case "Bag":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_bag)
                    else:   
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_bag)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_bag)
                    else:
                        set_rule(loc, self.leather_or_cloth)
            case "Rope/Chain":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.make_rope)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_chain)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_chain)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_cloth_ropechain)
                    else:
                        set_rule(loc, self.metal_or_cloth)
            case "Battle Axe":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_battleaxe)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_battleaxe)
                    else:
                        set_rule(loc, self.metal)
            case "Mace":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_mace)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_mace)
                    else:
                        set_rule(loc, self.metal)
            case "Spear":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_spear)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_spear)
                    else:
                        set_rule(loc, self.metal)
            case "Pick":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_pick)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_pick)
                    else:
                        set_rule(loc, self.metal)
            case "Short Sword":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_sword)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_sword)
                    else:
                        set_rule(loc, self.metal)
            case "War Hammer":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_warhammer)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_warhammer)
                    else:
                        set_rule(loc, self.metal)
            case "Anvil":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_anvil)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_anvil)
                    else:
                        set_rule(loc, self.metal)
            case "Coins":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_coins)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_coins)
                    else:
                        set_rule(loc, self.metal)
            case "Soap":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_soap)
                else:
                    set_rule(loc, self.soap)
            case "Display Case":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_displaycase)
                else:
                    set_rule(loc, self.displaycase)
            case "Backpack":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_backpack)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_backpack)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantinecloth_or_leather_backpack)
                    else:
                        set_rule(loc, self.adamantinecloth_or_leather)
            case "Quiver":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_quiver)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_quiver)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantinecloth_or_leather_quiver)
                    else:
                        set_rule(loc, self.adamantinecloth_or_leather)
            case "Bolt Thrower Parts":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.seige_boltthrowerparts)
                else:
                    set_rule(loc, self.seige_workshop)
            case "Amulet":
                if material_type in {"Wood", "Stone", "Cloth"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_amulet)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bonecraftdwarf_amulet)
                    else:
                        set_rule(loc, self.bonecraft)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_amulet)
                    else:
                        set_rule(loc, self.leathercraft)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_amulet)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_amulet)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_amulet)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
            case "Bracelet":
                if material_type in {"Wood", "Stone", "Cloth"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_bracelet)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bonecraftdwarf_bracelet)
                    else:
                        set_rule(loc, self.bonecraft)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_bracelet)
                    else:
                        set_rule(loc, self.leathercraft)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_bracelet)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_bracelet)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_bracelet)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
            case "Crown":
                if material_type in {"Wood", "Stone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_crown)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bonecraftdwarf_crown)
                    else:
                        set_rule(loc, self.bonecraft)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_crown)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_bracelet)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_crown)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
            case "Die":
                if material_type in {"Wood", "Stone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_die)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bonecraftdwarf_die)
                    else:
                        set_rule(loc, self.bonecraft)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_die)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_die)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_die)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass_die)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
            case "Earring":
                if material_type in {"Wood", "Stone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_earring)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bonecraftdwarf_earring)
                    else:
                        set_rule(loc, self.bonecraft)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_earring)
                    else:
                        set_rule(loc, self.leathercraft)
                elif material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.clothcraftdwarf_earring)
                    else:
                        set_rule(loc, self.clothcraftdwarf)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_earring)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_earring)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_earring)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
            case "Figurine":
                if material_type in {"Wood", "Stone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_figurine)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bonecraftdwarf_figurine)
                    else:
                        set_rule(loc, self.bonecraft)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_figurine)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_figurine)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_figurine)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
            case "Nest Box":
                if material_type in {"Wood", "Stone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_nestbox)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bonecraftdwarf_nestbox)
                    else:
                        set_rule(loc, self.bonecraft)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_nestbox)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_nestbox)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_nestbox)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass_nestbox)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
            case "Ring":
                if material_type in {"Wood", "Stone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_ring)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bonecraftdwarf_ring)
                    else:
                        set_rule(loc, self.bonecraft)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_ring)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_ring)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_ring)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
            case "Scepter":
                if material_type in {"Wood", "Stone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_scepter)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bonecraftdwarf_scepter)
                    else:
                        set_rule(loc, self.bonecraft)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_scepter)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_scepter)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_scepter)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
            case "Quire":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_quire)
                else:
                    set_rule(loc, self.quire)
            case "Scroll":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_scroll)
                else:
                    set_rule(loc, self.scroll)
            case "Cap":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_cap)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_cap)
                    else:
                        set_rule(loc, self.leather_works)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_cap)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_cap)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_cloth_or_leather_cap)
                    else:
                        set_rule(loc, self.metal_or_cloth_or_leather) 
            case "Hood":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_hood)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_hood)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_hood)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_hood)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Shirt":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_shirt)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_shirt)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_shirt)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_shirt)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Vest": 
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_vest)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_vest)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_vest)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_vest)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Coat": 
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_coat)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_coat)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_coat)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_coat)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Cloak":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_cloak)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_cloak)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_cloak)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_cloak)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Leather Armor":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.leather_leatherarmor)
                else:
                    set_rule(loc, self.leather_works)
            case "Mail Shirt":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_mailshirt)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else: #both  the Metal type and easiest of the two types
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_mailshirt) 
                    else:
                        set_rule(loc, self.metal)
            case "Breastplate":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_breastplate)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else: #both Metal and easiest of the two types
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_breastplate) 
                    else:
                        set_rule(loc, self.metal)
            case "Gloves":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_gloves)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_gloves)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_gloves)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_gloves)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Mittens":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_mittens)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_mittens)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_mittens)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_mittens)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Loincloth":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_loincloth)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_loincloth)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_loincloth)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_loincloth)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Trousers":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_trousers)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_trousers)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_trousers)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_trousers)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Leggings":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                            set_rule(loc, self.metal_leggings)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_leggings)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bone_leggings)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_leggings)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_bone_or_leather_leggings)
                    else:
                        set_rule(loc, self.metal_or_bone_or_leather)
            case "Greaves":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_greaves)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_greaves)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bone_greaves)
                    else:
                        set_rule(loc, self.bonecraft)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_bone_greaves)
                    else:
                        set_rule(loc, self.metal_or_bone)
            case "Socks":
                if material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_socks)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_socks) 
                    else:
                        set_rule(loc, self.clothier_workshop)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_or_adamantine_socks)
                    else:
                        set_rule(loc, self.adamantine_or_cloth)
            case "Shoes":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_shoes)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_shoes)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_shoes)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_shoes)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Low Boots":
                if material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_lboots)
                    else:
                        set_rule(loc, self.leather_works)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_lboots)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_lboots)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_leather_lboots)
                    else:
                        set_rule(loc, self.metal_or_leather)
            case "High Boots":
                if material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_hboots)
                    else:
                        set_rule(loc, self.leather_works)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_hboots)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_hboots)
                    else:
                        set_rule(loc, self.adamantine_metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_leather_hboots)
                    else:
                        set_rule(loc, self.metal_or_leather)
            case "Giant Axe Blade":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_axeblade)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_axeblade)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_axeblade)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_glass_axeblade)
                    else:
                        set_rule(loc, self.metal_or_glass)
            case "Serrated Disc":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_disc)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_disc)
                    else:
                        set_rule(loc, self.adamantine_metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_disc)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_glass_disc)
                    else:
                        set_rule(loc, self.metal_or_glass)
            case "Codex":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_codex)
                else:
                    set_rule(loc, self.codex)
            case "Tunic": 
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_tunic)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_tunic)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_tunic)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_tunic)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Dress": 
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_dress)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_dress)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_dress)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_dress)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Toga": 
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_toga)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_toga)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_toga)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_toga)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Robe": 
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_robe)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_robe)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_robe)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_robe)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
            case "Braies": 
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_braies)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Adamantine":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.adamantine_braies)
                    else:
                        set_rule(loc, self.adamantine_cloth)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_braies)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_or_adamantine_braies)
                    else:
                        set_rule(loc, self.leather_or_cloth_or_adamantinecloth)
