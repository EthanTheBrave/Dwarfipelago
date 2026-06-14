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
            return state.has("Forge Blueprint", self.player) or state.has("Magma Forge Blueprint", self.player)
        else:
            return self.process_resource(state, "metal") and (state.has("Forge Blueprint", self.player) or \
            state.has("Magma Forge Blueprint", self.player))
        
    def process_resource(self, state:CollectionState, resource) -> bool: #glass, metal, ceramic
        if resource == "metal":
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return (state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player)) or \
                state.has("Magma Smelter Blueprint", self.player)
            elif self.world.options.craftpermits == CraftingPermits.option_on:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player)) or \
                state.has("Magma Smelter Blueprint", self.player)) and state.has("Metal Bars Permit", self.player)
            else:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player) and \
                state.has("Charcoal Permit", self.player)) or state.has("Magma Smelter Blueprint", self.player)) and \
                state.has("Metal Bars Permit", self.player)
        if resource == "coke":
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return (state.has("Wood Furnace Blueprint", self.player) and state.has("Smelter Blueprint", self.player)) or \
                state.has("Magma Smelter Blueprint", self.player)
            elif self.world.options.craftpermits == CraftingPermits.option_on:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Forge Blueprint", self.player)) or \
                state.has("Magma Smelter Blueprint", self.player)) and state.has("Coke Bars Permit", self.player)
            else:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Forge Blueprint", self.player) and \
                state.has("Charcoal Permit", self.player)) or state.has("Magma Smelter Blueprint", self.player)) and \
                state.has("Coke Bars Permit", self.player)
        elif resource == "glass":
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return (state.has("Wood Furnace Blueprint", self.player) and state.has("Glass Furnace Blueprint", self.player)) or \
                state.has("Magma Glass Furnace Blueprint", self.player)
            elif self.world.options.craftpermits == CraftingPermits.option_on:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Glass Furnace Blueprint", self.player)) or \
                state.has("Magma Glass Furnace Blueprint", self.player)) and state.has("Glass Permit", self.player)
            else:
                return ((state.has("Wood Furnace Blueprint", self.player) and state.has("Glass Furnace Blueprint", self.player) and \
                state.has("Charcoal Permit", self.player)) or state.has("Magma Glass Furnace Blueprint", self.player)) and \
                state.has("Glass Permit", self.player) 
        elif resource == "ceramic":
            if self.world.options.craftpermits != CraftingPermits.option_all:
                return (state.has("Wood Furnace Blueprint", self.player) and state.has("Kiln Blueprint", self.player)) or \
                state.has("Magma Kiln Blueprint", self.player)
            else:
                return (state.has("Wood Furnace Blueprint", self.player) and state.has("Kiln Blueprint", self.player) and \
                state.has("Charcoal Permit", self.player)) or state.has("Magma Kiln Blueprint", self.player)
        elif resource == "farming":
                return state.has("Farm Plot Blueprint", self.player)
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
            if self.world.options.craftpermits != CraftingPermits.option_all:
                return self.leather(state) and state.has("Leather Works Blueprint", self.player)
            else:
                return self.leather(state) and state.has("Leather Works Blueprint", self.player) and \
                state.has("Leather Permit", self.player)
    
    def cloth(self, state:CollectionState) -> bool:
        return state.has("Loom Blueprint", self.player)
    
    def clothier_workshop(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic:
            return state.has("Clothier's Shop Blueprint", self.player)
        else:
            if self.world.options.craftpermits != CraftingPermits.option_all:
                return self.cloth(state) and state.has("Clothier's Shop Blueprint", self.player)
            else:
                return self.leather(state) and state.has("Leather Works Blueprint", self.player) and \
                state.has("Cloth Permit", self.player)
        
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
    
    def craftdwarf_or_metal_or_glass(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) or self.metal(state) or self.glass(state)
    
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
    def glass_corkscrew(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Corkscrew Permit", self.player)
    def wood_or_metal_or_glass_corkscrew(self, state:CollectionState) -> bool:
            return self.wood_or_metal_or_glass(state) and state.has("Corkscrew Permit", self.player)

    def wood_spike(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Spike Permit", self.player)
    def metal_spike(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Spike Permit", self.player)
    def wood_or_metal_spike(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Spike Permit", self.player)

    def wood_ball(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Ball Permit", self.player)
    def metal_ball(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Ball Permit", self.player)
    def wood_or_metal_ball(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Ball Permit", self.player)

    def wood_animal_trap(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Animal Trap Permit", self.player)
    def metal_animal_trap(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Animal Trap Permit", self.player)
    def wood_or_metal_animal_trap(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Animal Trap Permit", self.player)
    
    def wood_barrel(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Barrel Permit", self.player)
    def metal_barrel(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Barrel Permit", self.player)
    def wood_or_metal_barrel(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Barrel Permit", self.player)
    
    def wood_bin(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Bin Permit", self.player)
    def metal_bin(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Bin Permit", self.player)
    def wood_or_metal_bin(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Bin Permit", self.player)

    def wood_bucket(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Bucket Permit", self.player)
    def metal_bucket(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Bucket Permit", self.player)
    def wood_or_metal_bucket(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Bucket Permit", self.player)

    def wood_crutch(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Crutch Permit", self.player)
    def metal_crutch(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crutch Permit", self.player)
    def wood_or_metal_crutch(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Crutch Permit", self.player)

    def wood_minecart(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Minecart Permit", self.player)
    def metal_minecart(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Minecart Permit", self.player)
    def wood_or_metal_minecart(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Minecart Permit", self.player)

    def wood_splint(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Splint Permit", self.player)
    def metal_splint(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Splint Permit", self.player)
    def wood_or_metal_splint(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Splint Permit", self.player)
    
    def wood_stepladder(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Stepladder Permit", self.player)
    def metal_stepladder(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Stepladder Permit", self.player)
    def wood_or_metal_stepladder(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Stepladder Permit", self.player)
    
    def wood_wheelbarrow(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Wheelbarrow Permit", self.player)
    def metal_wheelbarrow(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Wheelbarrow Permit", self.player)
    def wood_or_metal_wheelbarrow(self, state:CollectionState) -> bool:
            return self.wood_or_metal(state) and state.has("Wheelbarrow Permit", self.player)
    
    def wood_blocks(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Blocks Permit", self.player)
    def stone_blocks(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Blocks Permit", self.player)
    def metal_blocks(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Blocks Permit", self.player)
    def glass_blocks(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Blocks Permit", self.player)
    def ceramic_blocks(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Blocks Permit", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_blocks(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Blocks Permit", self.player)
    
    def wood_jug(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Jug Permit", self.player)
    def stone_jug(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Jug Permit", self.player)
    def metal_jug(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Jug Permit", self.player)
    def glass_jug(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Jug Permit", self.player)
    def ceramic_jug(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Jug Permit", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_jug(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Jug Permit", self.player)
    
    def wood_pot(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Large Pot Permit", self.player)
    def stone_pot(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Large Pot Permit", self.player)
    def metal_pot(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Large Pot Permit", self.player)
    def glass_pot(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Large Pot Permit", self.player)
    def ceramic_pot(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Large Pot Permit", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_pot(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Large Pot Permit", self.player)
    
    def wood_hive(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Hive Permit", self.player)
    def stone_hive(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Hive Permit", self.player)
    def metal_hive(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Hive Permit", self.player)
    def glass_hive(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Hive Permit", self.player)
    def ceramic_hive(self, state:CollectionState) -> bool:
            return self.ceramic(state) and state.has("Hive Permit", self.player)
    def wood_or_stone_or_metal_or_glass_or_ceramic_hive(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass_or_ceramic(state) and state.has("Hive Permit", self.player)
    
    def wood_altar(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Altar Permit", self.player)
    def stone_altar(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Altar Permit", self.player)
    def metal_altar(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Altar Permit", self.player)
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
    def glass_statue(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Statue Permit", self.player)
    def wood_or_stone_or_metal_or_glass_statue(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Statue Permit", self.player)
    
    def wood_bookbinding(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Book Binding Permit", self.player)
    def stone_bookbinding(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Book Binding Permit", self.player)
    def metal_bookbinding(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Book Binding Permit", self.player)
    def glass_bookbinding(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Book Binding Permit", self.player)
    def wood_or_stone_or_metal_or_glass_bookbinding(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Book Binding Permit", self.player)
    
    def wood_scrollroller(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Scroll Roller Permit", self.player)
    def stone_scrollroller(self, state:CollectionState) -> bool:
            return self.stone(state) and state.has("Scroll Roller Permit", self.player)
    def metal_scrollroller(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Scroll Roller Permit", self.player)
    def glass_scrollroller(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Scroll Roller Permit", self.player)
    def wood_or_stone_or_metal_or_glass_scrollroller(self, state:CollectionState) -> bool:
            return self.wood_or_stone_or_metal_or_glass(state) and state.has("Scroll Roller Permit", self.player)
    
    def wood_buckler(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Buckler Permit", self.player)
    def metal_buckler(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Buckler Permit", self.player)
    def leather_buckler(self, state:CollectionState) -> bool:
            return self.leather_works(state) and state.has("Buckler Permit", self.player)
    def wood_or_leather_or_metal_buckler(self, state:CollectionState) -> bool:
            return self.wood_or_leather_or_metal(state) and state.has("Buckler Permit", self.player)
    
    def wood_shield(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Shield Permit", self.player)
    def metal_shield(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Shield Permit", self.player)
    def leather_shield(self, state:CollectionState) -> bool:
            return self.leather_works(state) and state.has("Shield Permit", self.player)
    def wood_or_leather_or_metal_shield(self, state:CollectionState) -> bool:
            return self.wood_or_leather_or_metal(state) and state.has("Shield Permit", self.player)
    
    def wood_cage(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Cage Permit", self.player)
    def metal_cage(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Cage Permit", self.player)
    def glass_cage(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Cage Permit", self.player)
    def wood_or_metal_or_glass_cage(self, state:CollectionState) -> bool:
            return self.wood_or_metal_or_glass(state) and state.has("Cage Permit", self.player)
    
    def wood_pipesection(self, state:CollectionState) -> bool:
            return self.wood(state) and state.has("Pipe Section Permit", self.player)
    def metal_pipesection(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Pipe Section Permit", self.player)
    def glass_pipesection(self, state:CollectionState) -> bool:
            return self.glass(state) and state.has("Pipe Section Permit", self.player)
    def wood_or_metal_or_glass_pipesection(self, state:CollectionState) -> bool:
            return self.wood_or_metal_or_glass(state) and state.has("Pipe Section Permit", self.player)
    
    def wood_or_bone_crossbow(self, state:CollectionState) -> bool:
            return self.bowyer_workshop(state) and state.has("Crossbow Permit", self.player)
    def metal_crossbow(self, state:CollectionState) -> bool:
            return self.metal(state) and state.has("Crossbow Permit", self.player)
    def bowyer_or_metal_crossbow(self, state:CollectionState) -> bool:
        return self.bowyer_or_metal(state) and state.has("Crossbow Permit", self.player)
    
    def wood_or_bone_bolt(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Bolt Permit", self.player)
    def metal_bolt(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Bolt Permit", self.player)
    def craftdwarf_or_metal_bolt(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal(state) and state.has("Bolt Permit", self.player)
    
    def stone_millstone(self, state:CollectionState) -> bool:
        return self.stone(state) and state.has("Millstone Permit", self.player)
    
    def stone_quern(self, state:CollectionState) -> bool:
        return self.stone(state) and state.has("Quern Permit", self.player)
    
    def stone_slab(self, state:CollectionState) -> bool:
        return self.stone(state) and state.has("Slab Permit", self.player)
    
    def stone_or_wood_crafts(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Crafts Permit", self.player)
    def metal_crafts(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Crafts Permit", self.player)
    def glass_crafts(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Crafts Permit", self.player)
    def craftdwarf_or_metal_or_glass_crafts(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal_or_glass(state) and state.has("Crafts Permit", self.player)
    
    def mechanic_mechanism(self, state:CollectionState) -> bool:
        return self.mechanic_workshop(state) and state.has("Mechanism Permit", self.player)
    
    def wood_crafting_tractionbench(self, state:CollectionState) -> bool:
        return self.wood_table(state) and self.metal_or_cloth_ropechain(state) \
            and self.mechanic_mechanism(state) and state.has("Traction Bench Permit", self.player)
    def stone_crafting_tractionbench(self, state:CollectionState) -> bool:
        return self.stone_table(state) and self.metal_or_cloth_ropechain(state) \
            and self.mechanic_mechanism(state) and state.has("Traction Bench Permit", self.player)
    def metal_crafting_tractionbench(self, state:CollectionState) -> bool:
        return self.metal_table(state) and self.metal_or_cloth_ropechain(state) \
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
    def leather_liquidcontainer(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Liquid Container Permit", self.player)
    def metal_or_glass_or_leather_liquidcontainer(self, state:CollectionState) -> bool:
        return self.metal_or_glass_or_leather(state) and state.has("Liquid Container Permit", self.player)
    
    def metal_or_glass_cup(self, state:CollectionState) -> bool:
        return self.metal_or_glass(state) and state.has("Cup Permit", self.player)
    def stone_cup(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Cup Permit", self.player)
    def wood_cup(self, state:CollectionState) -> bool:
        return self.wood(state) and state.has("Cup Permit", self.player)
    
    def wood_or_stone_toy(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Toy Permit", self.player)
    def metal_toy(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Toy Permit", self.player)
    def glass_toy(self, state:CollectionState) -> bool:
        return self.glass(state) and state.has("Toy Permit", self.player)
    def craftdwarf_or_metal_or_glass_toy(self, state:CollectionState) -> bool:
        return self.craftdwarf_or_metal_or_glass(state) and state.has("Toy Permit", self.player)
    
    def craftdwarf_and_butchery_totem(self, state:CollectionState) -> bool:
        return self.craftdwarf_and_butchery(state) and state.has("Totem Permit", self.player)
    
    def bone_helm(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Helm Permit", self.player)
    def metal_helm(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Helm Permit", self.player)
    def leather_helm(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Helm Permit", self.player)
    def metal_or_bone_or_leather_helm(self, state:CollectionState) -> bool:
        return self.metal_or_bone_or_leather(state) and state.has("Helm Permit", self.player)
    
    def bone_lbodyarmor(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Lower Body Armor Permit", self.player)
    def metal_lbodyarmor(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Lower Body Armor Permit", self.player)
    def leather_lbodyarmor(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Lower Body Armor Permit", self.player)
    def metal_or_bone_or_leather_lbodyarmor(self, state:CollectionState) -> bool:
        return self.metal_or_bone_or_leather(state) and state.has("Lower Body Armor Permit", self.player)
    
    def seige_ballistaparts(self, state:CollectionState) -> bool:
        return self.seige_workshop(state) and state.has("Ballista Parts Permit", self.player)
    
    def seige_catapultparts(self, state:CollectionState) -> bool:
        return self.seige_workshop(state) and state.has("Catapult Parts Permit", self.player)
    
    def seige_arrows(self, state:CollectionState) -> bool:
        return self.seige_workshop(state) and state.has("Catapult Parts Permit", self.player)
    def seige_metal_arrows(self, state:CollectionState) -> bool:
        return self.seige_and_metal(state) and state.has("Catapult Parts Permit", self.player)
    
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
        return self.screw_press(state) and state.has("Honey Permit", self.player)
    
    def cloth_headgear(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Headgear Clothing Permit", self.player)
    def leather_headgear(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Headgear Clothing Permit", self.player)
    def leather_or_cloth_headgear(self, state:CollectionState) -> bool:
        return self.leather_or_cloth(state) and state.has("Headgear Clothing Permit", self.player)
    
    def cloth_upperbodycloth(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Upper Body Clothing Permit", self.player)
    def leather_upperbodycloth(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Upper Body Clothing Permit", self.player)
    def leather_or_cloth_upperbodycloth(self, state:CollectionState) -> bool:
        return self.leather_or_cloth(state) and state.has("Upper Body Clothing Permit", self.player)
    
    def cloth_hands(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Hand Clothing Permit", self.player)
    def leather_hands(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Hand Clothing Permit", self.player)
    def leather_or_cloth_hands(self, state:CollectionState) -> bool:
        return self.leather_or_cloth(state) and state.has("Hand Clothing Permit", self.player)
    
    def cloth_lbodyclothing(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Lower Body Clothing Permit", self.player)
    def leather_lbodyclothing(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Lower Body Clothing Permit", self.player)
    def leather_or_cloth_lbodyclothing(self, state:CollectionState) -> bool:
        return self.leather_or_cloth(state) and state.has("Lower Body Clothing Permit", self.player)
    
    def metal_ubodyarmor(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Upper Body Armor Permit", self.player)
    def leather_ubodyarmor(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Upper Body Armor Permit", self.player)
    def metal_or_leather_ubodyarmor(self, state:CollectionState) -> bool:
        return self.metal_or_leather(state) and state.has("Upper Body Armor Permit", self.player)
    
    def metal_gauntlets(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Gauntlets Permit", self.player)
    def bone_gauntlets(self, state:CollectionState) -> bool:
        return self.craftdwarf_workshop(state) and state.has("Gauntlets Permit", self.player)
    def metal_or_bone_gauntlets(self, state:CollectionState) -> bool:
        return self.metal_or_bone(state) and state.has("Gauntlets Permit", self.player)
    
    def metal_shoes(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Footwear Permit", self.player)
    def cloth_shoes(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Footwear Permit", self.player)
    def leather_shoes(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Footwear Permit", self.player)
    def metal_or_cloth_or_leather_shoes(self, state:CollectionState) -> bool:
        return self.metal_or_cloth_or_leather(state) and state.has("Footwear Permit", self.player)
    
    def dye_dye(self, state:CollectionState) -> bool:
        return self.dye(state) and state.has("Dye Permit", self.player)
    
    def cloth_bag(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Bag Permit", self.player)
    def leather_bag(self, state:CollectionState) -> bool:
        return self.leather_works(state) and state.has("Bag Permit", self.player)
    def leather_or_cloth_bag(self, state:CollectionState) -> bool:
        return self.leather_or_cloth(state) and state.has("Bag Permit", self.player)
    
    def make_chain(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Rope/Chain Permit", self.player)
    def make_rope(self, state:CollectionState) -> bool:
        return self.clothier_workshop(state) and state.has("Rope/Chain Permit", self.player)
    def metal_or_cloth_ropechain(self, state:CollectionState) -> bool:
        return self.metal_or_cloth(state) and state.has("Rope/Chain Permit", self.player)

    def make_battleaxe(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Battle Axe Permit", self.player)
    def make_mace(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Mace Permit", self.player)
    def make_pick(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Pick Permit", self.player)
    def make_sword(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Short Sword Permit", self.player)
    def make_spear(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Spear Permit", self.player)
    def make_warhammer(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("War Hammer Permit", self.player)
    
    def make_anvil(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Anvil Permit", self.player)
    
    def make_coins(self, state:CollectionState) -> bool:
        return self.metal(state) and state.has("Coins Permit", self.player)
    
    def make_soap(self, state:CollectionState) -> bool:
        return self.ashery_and_wood_furnace_lye(state) and (self.make_tallow(state) or self.make_oil(state)) \
        and state.has("Soap Permit", self.player)
    
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
            case "Spike":
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
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_metal_spike)
                    else:
                        set_rule(loc, self.wood_or_metal)
            case "Ball":
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
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_hive)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_hive)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_hive)
                    else:
                        set_rule(loc, self.metal)
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
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic_hive)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_or_ceramic)
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
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_burial)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_burial)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_burial)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_burial)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
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
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_statue)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_statue)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
            case "Book Binding":
                if material_type == "Wood":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_bookbinding)
                    else:
                        set_rule(loc, self.wood)
                elif material_type == "Stone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_bookbinding)
                    else:
                        set_rule(loc, self.stone)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_bookbinding)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Glass":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_bookbinding)
                    else:
                        set_rule(loc, self.glass)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass_bookbinding)
                    else:
                        set_rule(loc, self.wood_or_stone_or_metal_or_glass)
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
                if type in {"Wood", "Bone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_bone_crossbow)
                    else:
                        set_rule(loc, self.bowyer_workshop)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_crossbow)
                    else:
                        set_rule(loc, self.metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bowyer_or_metal_crossbow)
                    else:
                        set_rule(loc, self.bowyer_or_metal)
            case "Bolt":
                if material_type in {"Wood", "Bone"}:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.wood_or_bone_bolt)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_bolt)
                    else:
                        set_rule(loc, self.metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_bolt)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal)
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
                if material_type in {"Wood", "Stone"} :
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.stone_or_wood_crafts)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Glass":  
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.glass_crafts)
                    else:
                        set_rule(loc, self.glass)
                elif material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_crafts)
                    else:
                        set_rule(loc, self.metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass_crafts)
                    else:
                        set_rule(loc, self.craftdwarf_or_metal_or_glass)
            case "Mechanism":
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
            case "Lower Body Armor":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                            set_rule(loc, self.metal_lbodyarmor)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bone_lbodyarmor)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_lbodyarmor)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_bone_or_leather_lbodyarmor)
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
            case "Headgear Clothing":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_headgear)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_headgear)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_headgear)
                    else:
                        set_rule(loc, self.leather_or_cloth)
            case "Upper Body Clothing":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_upperbodycloth)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_upperbodycloth)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_upperbodycloth)
                    else:
                        set_rule(loc, self.leather_or_cloth)
            case "Hand Clothing":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_hands)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_hands)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_hands)
                    else:
                        set_rule(loc, self.leather_or_cloth)
            case "Lower Body Clothing":
                if material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_lbodyclothing)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_lbodyclothing)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_or_cloth_lbodyclothing)
                    else:
                        set_rule(loc, self.leather_or_cloth)
            case "Upper Body Armor":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_ubodyarmor)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_ubodyarmor)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_leather_ubodyarmor)
                    else:
                        set_rule(loc, self.metal_or_leather)
            case "Gauntlets":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_gauntlets)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Bone":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.bone_gauntlets)
                    else:
                        set_rule(loc, self.craftdwarf_workshop)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_bone_gauntlets)
                    else:
                        set_rule(loc, self.metal_or_bone)  
            case "Footwear":
                if material_type == "Metal":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_shoes)
                    else:
                        set_rule(loc, self.metal)
                elif material_type == "Cloth":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.cloth_shoes)
                    else:
                        set_rule(loc, self.clothier_workshop)
                elif material_type == "Leather":
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.leather_shoes)
                    else:
                        set_rule(loc, self.leather_works)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_cloth_or_leather_shoes)
                    else:
                        set_rule(loc, self.metal_or_cloth_or_leather)
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
                        set_rule(loc, self.make_chain)
                    else:
                        set_rule(loc, self.metal)
                else:
                    if self.world.options.craftpermits != CraftingPermits.option_off:
                        set_rule(loc, self.metal_or_cloth_ropechain)
                    else:
                        set_rule(loc, self.metal_or_cloth)
            case "Battle Axe":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_battleaxe)
                else:
                    set_rule(loc, self.metal)
            case "Mace":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_mace)
                else:
                    set_rule(loc, self.metal)
            case "Pick":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_pick)
                else:
                    set_rule(loc, self.metal)
            case "Short Sword":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_sword)
                else:
                    set_rule(loc, self.metal)
            case "War Hammer":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_warhammer)
                else:
                    set_rule(loc, self.metal)
            case "Anvil":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_anvil)
                else:
                    set_rule(loc, self.metal)
            case "Coins":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_coins)
                else:
                    set_rule(loc, self.metal)
            case "Soap":
                if self.world.options.craftpermits != CraftingPermits.option_off:
                    set_rule(loc, self.make_soap)
                else:
                    set_rule(loc, self.soap)
