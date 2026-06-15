import math
import re
from typing import List, Set, Union, TYPE_CHECKING
from dataclasses import dataclass
from BaseClasses import ItemClassification, Location, LocationProgressType, CollectionState
from worlds.dwarf_fortress.craftsanity_rules import DynamicCraftingLocationRules
from worlds.generic.Rules import set_rule
from .options import CraftingPermits, SkillsanitySkillGroup
from .locations import JOB_SKILLS, LocationData

if TYPE_CHECKING:
    from . import DwarfFortressWorld


class Skillsanity:
    world: "DwarfFortressWorld"
    skill_levels: List[str] = [
        "Dabbling",
        "Novice",
        "Adequate",
        "Competent",
        "Skilled",
        "Proficient",
        "Talented",
        "Adept",
        "Expert",
        "Professional",
        "Accomplished",
        "Great",
        "Master",
        "High Master",
        "Grand Master",
        "Legendary"
    ]

    SKILLSANITY_EASY: List[str] = [
     "Miner", "Carpenter", "Wood Cutter", "Bowyer", "Mason", "Stonecutter", "Stone Carver", "Ambusher", "Brewer", 
     "Cook", "Planter", "Herbalist", "Spinner", "Tanner", "Wood Burner", "Butcher", "Furnace Operator", "Gem Cutter",
     "Bone Carver", "Clothier", "Glassmaker", "Leatherworker", "Potter", "Glazer", "Stone Crafter", "Wood Crafter",
     "Mechanic", "Pump Operator", "Siege Engineer"
    ]

    SKILLSANITY_MEDIUM: List[str] = SKILLSANITY_EASY + [  
     "Engraver", "Stone Carver", "Animal Trainer", "Diagnostician", "Cheese Maker", "Dyer", "Lye Maker", "Milker",
     "Miller", "Potash Maker", "Presser", "Shearer", "Soaper", "Thresher", "Fisherdwarf", "Fish Cleaner", 
     "Fish Dissector", "Armorsmith", "Metal Crafter", "Blacksmith", "Weaponsmith", "Gem Setter", "Siege Operator",
     "Appraiser", "Organizer", "Record Keeper"
    ]

    SKILLSANITY_HARD: List[str] = SKILLSANITY_MEDIUM + [
     "Trapper", "Bone Doctor", "Surgeon", "Suturer", "Wound Dresser", "Beekeeper", "Gelder", "Bookbinder",
     "Papermaker", "Strand Extractor", "Wax Worker", "Gelder"
    ]



    def __init__(self, world: "DwarfFortressWorld") -> None:
        self.player = world.player
        self.world = world

    def adjust_skill_locations(self) -> None:
        if self.world.options.skillsanity == False:
            self.world.remove_skill_locations_names = [location.name for location in JOB_SKILLS]
            return
        else:
            skill_locations = JOB_SKILLS.copy()
            remove_skills = []

            if self.world.options.skillsanity_skill_group == SkillsanitySkillGroup.option_easy:
                for skill in JOB_SKILLS:
                    compare = [s for s in self.SKILLSANITY_EASY if s in skill.name]
                    if len(compare) == 0:
                        remove_skills.append(skill)
                        skill_locations.remove(skill)
            elif self.world.options.skillsanity_skill_group == SkillsanitySkillGroup.option_medium:
                for skill in JOB_SKILLS:
                    compare = [s for s in self.SKILLSANITY_MEDIUM if s in skill.name]
                    if len(compare) == 0:
                        remove_skills.append(skill)
                        skill_locations.remove(skill)
            elif self.world.options.skillsanity_skill_group == SkillsanitySkillGroup.option_all:
                for skill in JOB_SKILLS:
                    compare = [s for s in self.SKILLSANITY_HARD if s in skill.name]
                    if len(compare) == 0:
                        remove_skills.append(skill)
                        skill_locations.remove(skill)
            else: #Manually selected
                for skill in JOB_SKILLS:
                    compare = [s for s in self.world.options.skillsanity_skills.value if s in skill.name]
                    if len(compare) == 0:
                        remove_skills.append(skill)
                        skill_locations.remove(skill)
            #Remove Levels
            if self.world.options.skillsanity_max_level <15: 
                remove_levels = self.world.options.skillsanity_max_level + 1
                for levels in range(remove_levels, 15+1):
                    for location in JOB_SKILLS:
                        if self.skill_levels[levels] in location.name and location in skill_locations:
                            remove_skills.append(location)
                            skill_locations.remove(location)
            self.world.remove_skill_locations_names = {n.name for n in remove_skills}
            self.world.skill_locations = skill_locations
            
    def set_skill_rules(self) -> None:
        for location in self.world.skill_locations:
            self.world.multiworld
            loc = self.world.multiworld.get_location(location.name, self.player)
            self.df_location_rule(loc, location.name)
            

    def df_location_rule(self, loc, location_name) -> None:
        # following doesn't require rules:
        # Miner, Wood Cutter, Engraver, Mason, Stonecutter, Ambusher
        # Diagnostician, Suturer (adamantine), 
        if "Bowyer" in location_name:
            set_rule(loc, self.skill_bowyer)
        elif "Carpenter" in location_name:
            set_rule(loc, self.skill_carpentry)
        elif "Stone Carver" in location_name:
            set_rule(loc, self.skill_stonecarver)
        elif "Animal Trainer" in location_name:
            set_rule(loc, self.skill_animaltrainer)
        elif "Trapper" in location_name:
            set_rule(loc, self.skill_animaltrainer)
        elif "Bone Doctor" in location_name:
            set_rule(loc, self.skill_bonedoctor)
        elif "Surgeon" in location_name:
            set_rule(loc, self.skill_surgeon)
        elif "Wound Dresser" in location_name:
            set_rule(loc, self.skill_wounddresser)

    def skill_bowyer(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.bowyer_workshop(state)
        else:
            return dynamic_rules.bowyer_or_metal_crossbow(state)
        
    def skill_carpentry(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.wood(state)
        elif self.world.options.craftpermits == CraftingPermits.option_on:
            return dynamic_rules.wood_pedestal(state) or dynamic_rules.wood_altar(state) \
            or dynamic_rules.wood_animal_trap(state) or dynamic_rules.wood_armorstand(state) \
            or dynamic_rules.wood_bin(state) or dynamic_rules.wood_blocks(state) or dynamic_rules.wood_bookcase(state) \
            or dynamic_rules.wood_bucket(state) or dynamic_rules.wood_buckler(state) or dynamic_rules.wood_burial(state) \
            or dynamic_rules.wood_cabinet(state) or dynamic_rules.wood_cage(state) or dynamic_rules.wood_chair(state) \
            or dynamic_rules.wood_container or dynamic_rules.wood_crutch(state) or dynamic_rules.wood_cup(state) \
            or dynamic_rules.wood_door(state) or dynamic_rules.wood_floodgate(state) or dynamic_rules.wood_grate(state) \
            or dynamic_rules.wood_hatchcover(state) or dynamic_rules.wood_minecart(state) or dynamic_rules.training_axe(state) \
            or dynamic_rules.training_spear(state) or dynamic_rules.training_sword(state) or dynamic_rules.wood_table(state) \
            or dynamic_rules.wood_weaponrack(state)
        elif self.world.options.craftpermits == CraftingPermits.option_all:
            return dynamic_rules.wood_pedestal(state) or dynamic_rules.wood_altar(state) \
            or dynamic_rules.wood_animal_trap(state) or dynamic_rules.wood_armorstand(state) or dynamic_rules.wood_barrel(state) \
            or dynamic_rules.wood_bin(state) or dynamic_rules.wood_blocks(state) or dynamic_rules.wood_bookcase(state) \
            or dynamic_rules.wood_bucket(state) or dynamic_rules.wood_buckler(state) or dynamic_rules.wood_burial(state) \
            or dynamic_rules.wood_cabinet(state) or dynamic_rules.wood_cage(state) or dynamic_rules.wood_chair(state) \
            or dynamic_rules.wood_container or dynamic_rules.wood_crutch(state) or dynamic_rules.wood_cup(state) \
            or dynamic_rules.wood_door(state) or dynamic_rules.wood_floodgate(state) or dynamic_rules.wood_grate(state) \
            or dynamic_rules.wood_hatchcover(state) or dynamic_rules.wood_minecart(state) or dynamic_rules.training_axe(state) \
            or dynamic_rules.training_spear(state) or dynamic_rules.training_sword(state) or dynamic_rules.wood_table(state) \
            or dynamic_rules.wood_weaponrack(state) or dynamic_rules.bed(state) or dynamic_rules.wood_barrel(state)
        
    def skill_stonecarver(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.stone(state)
        else:
            return dynamic_rules.stone_pedestal(state) or dynamic_rules.stone_altar(state) \
            or dynamic_rules.stone_armorstand(state) or dynamic_rules.stone_blocks(state) \
            or dynamic_rules.stone_bookcase(state) or dynamic_rules.stone_burial(state) \
            or dynamic_rules.stone_cabinet(state) or dynamic_rules.stone_chair(state) \
            or dynamic_rules.stone_container or dynamic_rules.stone_cup(state) \
            or dynamic_rules.stone_door(state) or dynamic_rules.stone_floodgate(state) \
            or dynamic_rules.stone_grate(state) or dynamic_rules.stone_hatchcover(state) \
            or dynamic_rules.stone_slab(state) or dynamic_rules.stone_millstone(state) \
            or dynamic_rules.stone_quern(state) or dynamic_rules.stone_statue(state) \
            or dynamic_rules.stone_table(state) or dynamic_rules.stone_weaponrack(state)

    def skill_animaltrainer(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic == True:
            return True
        else:
            dynamic_rules = DynamicCraftingLocationRules(self.world)
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return dynamic_rules.wood_or_metal_or_glass(state)
            else:
                return dynamic_rules.wood_or_metal_or_glass_cage(state)
        
    def skill_trapper(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic == True:
            return True
        else:
            dynamic_rules = DynamicCraftingLocationRules(self.world)
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return dynamic_rules.wood_or_metal(state)
            else:
                return dynamic_rules.wood_or_metal_animal_trap(state)
        
    def skill_bonedoctor(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic == True:
            return True
        else:
            dynamic_rules = DynamicCraftingLocationRules(self.world)
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return dynamic_rules.wood_or_metal(state) or dynamic_rules.ceramic(state)
            else:
                return dynamic_rules.wood_or_metal_splint(state) or dynamic_rules.plaster(state)
        
    def skill_surgeon(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic == True:
            return True
        else:
            dynamic_rules = DynamicCraftingLocationRules(self.world)
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return dynamic_rules.wood_or_stone_or_metal_or_glass(state)
            elif self.world.options.craftpermits == CraftingPermits.option_on:
                return dynamic_rules.wood_or_stone_or_metal_or_glass_table(state) \
                or dynamic_rules.any_traction_bench(state) or dynamic_rules.wood(state)
            else:
                return dynamic_rules.wood_or_stone_or_metal_or_glass_table(state) \
                or dynamic_rules.any_traction_bench(state) or dynamic_rules.bed(state)
            
    def skill_wounddresser(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic == True:
            return True
        else:
            dynamic_rules = DynamicCraftingLocationRules(self.world)
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return dynamic_rules.soap(state) and dynamic_rules.cloth(state)
            elif self.world.options.craftpermits == CraftingPermits.option_on:
                return dynamic_rules.make_soap(state) and dynamic_rules.cloth(state)
            else:
                return dynamic_rules.make_soap(state) and dynamic_rules.make_cloth(state)
        