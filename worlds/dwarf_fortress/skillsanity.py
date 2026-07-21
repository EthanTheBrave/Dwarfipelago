import math
import re
from typing import List, Set, Union, TYPE_CHECKING
from dataclasses import dataclass
from BaseClasses import ItemClassification, Location, LocationProgressType, CollectionState
from worlds.dwarf_fortress.craftsanity_rules import DynamicCraftingLocationRules
from worlds.generic.Rules import set_rule
from .options import CraftingPermits, SkillsanitySkillGroup, SkillsanityCombatSkillGroup
from .locations import COMBAT_SKILLS, JOB_SKILLS, LocationData

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
     "Mechanic", "Pump Operator", "Siege Engineer", "Weaver"
    ]

    SKILLSANITY_MEDIUM: List[str] = SKILLSANITY_EASY + [  
     "Engraver", "Stone Carver", "Animal Trainer", "Diagnostician", "Cheese Maker", "Dyer", "Lye Maker", "Milker",
     "Miller", "Potash Maker", "Presser", "Shearer", "Soaper", "Thresher", "Fisherdwarf", "Fish Cleaner", 
     "Armorsmith", "Metal Crafter", "Blacksmith", "Weaponsmith", "Gem Setter", "Siege Operator",
     "Appraiser", "Organizer", "Record Keeper"
    ]

    SKILLSANITY_HARD: List[str] = SKILLSANITY_MEDIUM + [
     "Trapper", "Bone Doctor", "Surgeon", "Suturer", "Wound Dresser", "Beekeeper", "Gelder", "Bookbinder",
     "Papermaker", "Strand Extractor", "Wax Worker", "Gelder", "Fish Dissector"
    ]

    SKILLSANITY_COMBAT_EASY: List[str] = [
     "Archer", "Axedwarf", "Crossbowdwarf", "Dodger", "Discipline", "Fighter", "Hammerdwarf",
     "Macedwarf", "Speardwarf", "Sworddwarf"
    ]

    SKILLSANITY_COMBAT_MEDIUM: List[str] = SKILLSANITY_COMBAT_EASY + [
     "Armordwarf", "Kicker", "Tactics", "Wrestler", "Striker", "Shielddwarf"
    ]

    SKILLSANITY_COMBAT_HARD: List[str] = SKILLSANITY_COMBAT_MEDIUM + [
     "Biter", "Blowgunner", "Bowdwarf", "Knifedwarf", "Lasher"
    ]



    def __init__(self, world: "DwarfFortressWorld") -> None:
        self.player = world.player
        self.world = world

    def adjust_skill_locations(self) -> None:
        if self.world.options.skillsanity == False:
            self.world.remove_skill_locations_names = [location.name for location in JOB_SKILLS]
            self.world.remove_skill_locations_names += [location.name for location in COMBAT_SKILLS]
            return
        else:
            remove_skills = []
            #JOB SKILLS
            skill_locations = JOB_SKILLS.copy()
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
            self.world.skill_locations = skill_locations

            #COMBAT SKILLS
            combat_skill_locations = COMBAT_SKILLS.copy()
            if self.world.options.skillsanity_enable_combat:
                if self.world.options.skillsanity_combat_skill_group == SkillsanityCombatSkillGroup.option_easy:
                    for skill in COMBAT_SKILLS:
                        compare = [s for s in self.SKILLSANITY_COMBAT_EASY if s in skill.name]
                        if len(compare) == 0:
                            remove_skills.append(skill)
                            combat_skill_locations.remove(skill)
                elif self.world.options.skillsanity_combat_skill_group == SkillsanityCombatSkillGroup.option_medium:
                    for skill in COMBAT_SKILLS:
                        compare = [s for s in self.SKILLSANITY_COMBAT_MEDIUM if s in skill.name]
                        if len(compare) == 0:
                            remove_skills.append(skill)
                            combat_skill_locations.remove(skill)
                elif self.world.options.skillsanity_combat_skill_group == SkillsanityCombatSkillGroup.option_all:
                    for skill in COMBAT_SKILLS:
                        compare = [s for s in self.SKILLSANITY_COMBAT_HARD if s in skill.name]
                        if len(compare) == 0:
                            remove_skills.append(skill)
                            combat_skill_locations.remove(skill)
                else: #Manually selected
                    for skill in COMBAT_SKILLS:
                        compare = [s for s in self.world.options.skillsanity_combat_skills.value if s in skill.name]
                        if len(compare) == 0:
                            remove_skills.append(skill)
                            combat_skill_locations.remove(skill)
                #Remove Levels
                if self.world.options.skillsanity_max_level <15: 
                    remove_levels = self.world.options.skillsanity_max_level + 1
                    for levels in range(remove_levels, 15+1):
                        for location in COMBAT_SKILLS:
                            if self.skill_levels[levels] in location.name and location in combat_skill_locations:
                                remove_skills.append(location)
                                combat_skill_locations.remove(location)
                self.world.skill_locations += combat_skill_locations
            self.world.remove_skill_locations_names = {n.name for n in remove_skills}

            
    def set_skill_rules(self) -> None:
        for location in self.world.skill_locations:
            self.world.multiworld
            loc = self.world.multiworld.get_location(location.name, self.player)
            self.df_location_rule(loc, location.name)
            

    def df_location_rule(self, loc, location_name) -> None:
        # following doesn't require rules:
        # Miner, Wood Cutter, Engraver, Mason, Stonecutter, Ambusher
        # Diagnostician, Beekeeper, Herbalist
        # Fisherdwarf, Appraiser, Axedwarf, Dodger
        # Discipline, Fighter, kicker, tactics
        # Wrestler, Striker, Blowgunner, Bowdwarf
        # Knifedwarf, Lasher
        if "Bowyer" in location_name:
            set_rule(loc, self.skill_bowyer)
        elif "Carpenter" in location_name:
            set_rule(loc, self.skill_carpentry)
        elif "Stone Carver" in location_name:
            set_rule(loc, self.skill_stonecarver)
        elif "Ambusher" in location_name:
            set_rule(loc, self.skill_ambusher)
        elif "Animal Trainer" in location_name:
            set_rule(loc, self.skill_animaltrainer)
        elif "Trapper" in location_name:
            set_rule(loc, self.skill_trapper)
        elif "Bone Doctor" in location_name:
            set_rule(loc, self.skill_bonedoctor)
        elif "Surgeon" in location_name:
            set_rule(loc, self.skill_surgeon)
        elif "Suturer" in location_name:
            set_rule(loc, self.skill_suturer)
        elif "Wound Dresser" in location_name:
            set_rule(loc, self.skill_wounddresser)
        elif "Beekeeper" in location_name:
            set_rule(loc, self.skill_beekeeper)
        elif "Brewer" in location_name:
            set_rule(loc, self.skill_brewer)
        elif "Butcher" in location_name:
            set_rule(loc, self.skill_butcher)
        elif "Cheese Maker" in location_name:
            set_rule(loc, self.skill_cheesemaker)
        elif "Cook" in location_name:
            set_rule(loc, self.skill_cook)
        elif "Dyer" in location_name:
            set_rule(loc, self.skill_dyer)
        elif "Gelder" in location_name:
            set_rule(loc, self.skill_gelder)
        elif "Planter" in location_name:
            set_rule(loc, self.skill_planter)
        elif "Lye Maker" in location_name:
            set_rule(loc, self.skill_lyemaker)
        elif "Milker" in location_name:
            set_rule(loc, self.skill_milker)
        elif "Miller" in location_name:
            set_rule(loc, self.skill_miller)
        elif "Potash Maker" in location_name:
            set_rule(loc, self.skill_potashmaker)
        elif "Presser" in location_name:
            set_rule(loc, self.skill_presser)
        elif "Shearer" in location_name:
            set_rule(loc, self.skill_shearer)
        elif "Soaper" in location_name:
            set_rule(loc, self.skill_soaper)
        elif "Spinner" in location_name:
            set_rule(loc, self.skill_spinner)
        elif "Tanner" in location_name:
            set_rule(loc, self.skill_tanner)
        elif "Thresher" in location_name:
            set_rule(loc, self.skill_thresher)
        elif "Wood Burner" in location_name:
            set_rule(loc, self.skill_woodburner)
        elif "Fish Cleaner" in location_name:
            set_rule(loc, self.skill_fishcleaner)
        elif "Fish Dissector" in location_name:
            set_rule(loc, self.skill_fishdissector)
        elif "Armorsmith" in location_name:
            set_rule(loc, self.skill_armorsmith)
        elif "Furnace Operator" in location_name:
            set_rule(loc, self.skill_furnaceoperator)
        elif "Metal Crafter" in location_name:
            set_rule(loc, self.skill_metalcrafter)
        elif "Blacksmith" in location_name:
            set_rule(loc, self.skill_blacksmith)
        elif "Weaponsmith" in location_name:
            set_rule(loc, self.skill_weaponsmith)
        elif "Gem Cutter" in location_name:
            set_rule(loc, self.skill_gemcutter)
        elif "Gem Setter" in location_name:
            set_rule(loc, self.skill_gemsetter)
        elif "Bookbinder" in location_name:
            set_rule(loc, self.skill_bookbinder)
        elif "Bone Carver" in location_name:
            set_rule(loc, self.skill_bonecarver)
        elif "Clothier" in location_name:
            set_rule(loc, self.skill_clothier)
        elif "Glassmaker" in location_name:
            set_rule(loc, self.skill_glassmaker)
        elif "Glazer" in location_name:
            set_rule(loc, self.skill_glazer)
        elif "Leatherworker" in location_name:
            set_rule(loc, self.skill_leatherworker)
        elif "Papermaker" in location_name:
            set_rule(loc, self.skill_papermaker)
        elif "Potter" in location_name:
            set_rule(loc, self.skill_potter)
        elif "Stone Crafter" in location_name:
            set_rule(loc, self.skill_stonecrafter)
        elif "Strand Extractor" in location_name:
            set_rule(loc, self.skill_strandextractor)
        elif "Wax Worker" in location_name:
            set_rule(loc, self.skill_waxworker)
        elif "Weaver" in location_name:
            set_rule(loc, self.skill_weaver)
        elif "Wood Crafter" in location_name:
            set_rule(loc, self.skill_woodcrafter)
        elif "Mechanic" in location_name:
            set_rule(loc, self.skill_mechanic)
        elif "Pump Operator" in location_name:
            set_rule(loc, self.skill_pumpoperator)
        elif "Siege Engineer" in location_name:
            set_rule(loc, self.skill_siegeengineer)
        elif "Siege Operator" in location_name:
            set_rule(loc, self.skill_siegeoperator)
        elif "Organizer" in location_name:
            set_rule(loc, self.office)
        elif "Record Keeper" in location_name:
            set_rule(loc, self.office)
        elif "Archer" in location_name:
            set_rule(loc, self.skill_ambusher) #reuse logic
        elif "Crossbowdwarf" in location_name:
            set_rule(loc, self.skill_ambusher) #reuse logic
        elif "Hammerdwarf" in location_name:
            set_rule(loc, self.skill_hammerer)
        elif "Macedwarf" in location_name:
            set_rule(loc, self.skill_macer)
        elif "Speardwarf" in location_name:
            set_rule(loc, self.skill_speardwarf)
        elif "Sworddwarf" in location_name:
            set_rule(loc, self.skill_sworddwarf)
        elif "Armordwarf" in location_name:
            set_rule(loc, self.skill_armordwarf)
        elif "Shielddwarf" in location_name:
            set_rule(loc, self.skill_shielddwarf)

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
            or dynamic_rules.wood_container(state) or dynamic_rules.wood_crutch(state) or dynamic_rules.wood_cup(state) \
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
            or dynamic_rules.wood_container(state) or dynamic_rules.wood_crutch(state) or dynamic_rules.wood_cup(state) \
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
            or dynamic_rules.stone_container(state) or dynamic_rules.stone_weaponrack(state) \
            or dynamic_rules.stone_door(state) or dynamic_rules.stone_floodgate(state) \
            or dynamic_rules.stone_grate(state) or dynamic_rules.stone_hatchcover(state) \
            or dynamic_rules.stone_slab(state) or dynamic_rules.stone_millstone(state) \
            or dynamic_rules.stone_quern(state) or dynamic_rules.stone_statue(state) \
            or dynamic_rules.stone_table(state) or dynamic_rules.craftdwarf_nestbox(state)

    def skill_ambusher(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.bowyer_workshop(state) and (dynamic_rules.craftdwarf_workshop(state) or dynamic_rules.metal(state))
        else:
            return dynamic_rules.bowyer_or_metal_crossbow(state) and dynamic_rules.woodcraft_or_bonecraft_or_metal_bolt(state)

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
            
    def skill_suturer(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic == True:
            return True
        else:
            dynamic_rules = DynamicCraftingLocationRules(self.world)
            return dynamic_rules.craftdwarf_workshop(state) or dynamic_rules.any_thread(state)

            
    def skill_wounddresser(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.soap(state) and dynamic_rules.cloth(state)
        elif self.world.options.craftpermits == CraftingPermits.option_on:
            return dynamic_rules.make_soap(state) and dynamic_rules.cloth(state)
        else:
            return dynamic_rules.make_soap(state) and dynamic_rules.process_resource(state, "cloth")
            
    def skill_beekeeper(self, state:CollectionState) -> bool:
        if self.world.options.trades_inlogic == True:
            return True
        else:
            dynamic_rules = DynamicCraftingLocationRules(self.world)
            if self.world.options.craftpermits == CraftingPermits.option_off:
                return dynamic_rules.craftdwarf_or_metal_or_glass_or_ceramic(state)
            else:
                return dynamic_rules.craftdwarf_or_metal_or_glass_or_ceramic_hive(state)
    
    def skill_brewer(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits != CraftingPermits.option_all:
            return dynamic_rules.process_resource(state, "farming") and dynamic_rules.still(state)
        else:
            return dynamic_rules.process_resource(state, "farming") and dynamic_rules.make_alcohol(state)
        
    def skill_butcher(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        return dynamic_rules.butcher_workshop(state)
    
    def skill_cheesemaker(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        return dynamic_rules.famer_workshop(state)
    
    def skill_cook(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits != CraftingPermits.option_all:
            return dynamic_rules.kitchen_and_butchershop(state)
        else:
            return dynamic_rules.make_meal(state)
    
    def skill_dyer(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.dye(state)
        else:
            return dynamic_rules.dye_dye(state)
        
    def skill_gelder(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        return dynamic_rules.famer_workshop(state)
    
    def skill_planter(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        return dynamic_rules.process_resource(state, "farming")

    def skill_lyemaker(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.ashery(state) and dynamic_rules.wood_furnace(state)
        else:
            return dynamic_rules.ash(state) and dynamic_rules.ashery(state)
        
    def skill_milker(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.famer_workshop(state)
        else:
            return dynamic_rules.famer_workshop(state) and dynamic_rules.wood_or_metal_bucket(state)
        
    def skill_miller(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return True
        else:
            return dynamic_rules.stone_quern(state) or (dynamic_rules.stone_millstone(state) and dynamic_rules.mechanic_mechanism(state))
        
    def skill_potashmaker(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.ashery_and_wood_furnace(state)
        else:
            return dynamic_rules.ashery_and_wood_furnace_potash(state)
        
    def skill_presser(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.screw_press(state) and dynamic_rules.wood_or_stone_or_metal_or_glass_or_ceramic(state) \
            and dynamic_rules.stone(state)
        else:
            return dynamic_rules.screw_press(state) and dynamic_rules.wood_or_stone_or_metal_or_glass_or_ceramic_jug(state) \
            and (dynamic_rules.stone_quern(state) or (dynamic_rules.stone_millstone(state) and dynamic_rules.mechanic_mechanism(state)))
        
    def skill_shearer(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        return dynamic_rules.famer_workshop(state)
    
    def skill_soaper(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.soap(state)
        else:
            return dynamic_rules.make_soap(state)
        
    def skill_spinner(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        return dynamic_rules.famer_workshop(state)
    
    def skill_tanner(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        return dynamic_rules.leather(state)
    
    def skill_thresher(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        return dynamic_rules.famer_workshop(state)
    
    def skill_woodburner(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.wood_furnace(state)
        else:
            return dynamic_rules.ash(state) or dynamic_rules.charcoal(state)
        
    def skill_fishcleaner(self, state:CollectionState) -> bool:
        return state.has("Fishery Blueprint", self.player)
    
    def skill_fishdissector(self, state:CollectionState) -> bool:
        return state.has("Fishery Blueprint", self.player)
    
    def skill_armorsmith(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state)
        else:
            return dynamic_rules.metal_cloth_and_armor(state)
        
    def skill_weaponsmith(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state)
        else:
            return dynamic_rules.metal_crossbow(state) or dynamic_rules.metal_spear(state) \
            or dynamic_rules.metal_battleaxe(state) or dynamic_rules.metal_sword(state) \
            or dynamic_rules.metal_pick(state) or dynamic_rules.metal_bolt(state) \
            or dynamic_rules.metal_ball(state) or dynamic_rules.metal_spike(state) \
            or dynamic_rules.metal_mace(state) \
            or dynamic_rules.adamantine_crossbow(state) or dynamic_rules.adamantine_spear(state) \
            or dynamic_rules.adamantine_battleaxe(state) or dynamic_rules.adamantine_sword(state) \
            or dynamic_rules.adamantine_pick(state) or dynamic_rules.adamantine_bolt(state) \
            or dynamic_rules.adamantine_ball(state) or dynamic_rules.adamantine_spike(state) \
            or dynamic_rules.adamantine_mace(state)
    
    def skill_furnaceoperator(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state) or dynamic_rules.ceramic(state)
        else:
            return dynamic_rules.make_metal(state) or dynamic_rules.pearlash(state) \
            or dynamic_rules.plaster(state)
        
    def skill_metalcrafter(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state)
        else:
            return dynamic_rules.metal_crafts(state) or dynamic_rules.metal_cup(state) \
            or dynamic_rules.metal_liquidcontainer(state) or dynamic_rules.metal_toy(state) \
            or dynamic_rules.metal_hive(state) or dynamic_rules.metal_jug(state) \
            or dynamic_rules.metal_minecart(state) or dynamic_rules.metal_coins(state) \
            or dynamic_rules.metal_chain(state) or dynamic_rules.metal_amulet(state) \
            or dynamic_rules.metal_bracelet(state) or dynamic_rules.metal_earring(state) \
            or dynamic_rules.metal_die(state) or dynamic_rules.metal_crown(state) \
            or dynamic_rules.metal_ring(state) or dynamic_rules.metal_scepter(state) \
            or dynamic_rules.metal_figurine(state) or dynamic_rules.metal_nestbox(state) \
            or dynamic_rules.adamantine_crafts(state) or dynamic_rules.adamantine_cup(state) \
            or dynamic_rules.adamantine_liquidcontainer(state) or dynamic_rules.adamantine_toy(state) \
            or dynamic_rules.adamantine_hive(state) or dynamic_rules.adamantine_jug(state) \
            or dynamic_rules.adamantine_minecart(state) or dynamic_rules.adamantine_coins(state) \
            or dynamic_rules.adamantine_chain(state) or dynamic_rules.adamantine_amulet(state) \
            or dynamic_rules.adamantine_bracelet(state) or dynamic_rules.adamantine_earring(state) \
            or dynamic_rules.adamantine_die(state) or dynamic_rules.adamantine_crown(state) \
            or dynamic_rules.adamantine_ring(state) or dynamic_rules.adamantine_scepter(state) \
            or dynamic_rules.adamantine_figurine(state) or dynamic_rules.adamantine_nestbox(state)
        
    def skill_blacksmith(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state)
        elif self.world.options.craftpermits == CraftingPermits.option_on:
            return dynamic_rules.metal_pedestal(state) or dynamic_rules.metal_altar(state) \
            or dynamic_rules.metal_armorstand(state) \
            or dynamic_rules.metal_bin(state) or dynamic_rules.metal_blocks(state) or dynamic_rules.metal_bookcase(state) \
            or dynamic_rules.metal_bucket(state) or dynamic_rules.metal_burial(state) \
            or dynamic_rules.metal_cabinet(state) or dynamic_rules.metal_cage(state) or dynamic_rules.metal_chair(state) \
            or dynamic_rules.metal_crutch(state) or dynamic_rules.metal_door(state) or dynamic_rules.metal_floodgate(state) \
            or dynamic_rules.metal_grate(state) or dynamic_rules.metal_hatchcover(state) or dynamic_rules.metal_weaponrack(state) \
            or dynamic_rules.metal_anvil(state) or dynamic_rules.metal_bucket(state) or dynamic_rules.metal_pot(state) \
            or dynamic_rules.adamantine_pedestal(state) or dynamic_rules.adamantine_altar(state) \
            or dynamic_rules.adamantine_armorstand(state) \
            or dynamic_rules.adamantine_bin(state) or dynamic_rules.adamantine_blocks(state) or dynamic_rules.adamantine_bookcase(state) \
            or dynamic_rules.adamantine_bucket(state) or dynamic_rules.adamantine_burial(state) \
            or dynamic_rules.adamantine_cabinet(state) or dynamic_rules.adamantine_cage(state) or dynamic_rules.adamantine_chair(state) \
            or dynamic_rules.adamantine_crutch(state) or dynamic_rules.adamantine_door(state) or dynamic_rules.adamantine_floodgate(state) \
            or dynamic_rules.adamantine_grate(state) or dynamic_rules.adamantine_hatchcover(state) or dynamic_rules.adamantine_weaponrack(state) \
            or dynamic_rules.adamantine_anvil(state) or dynamic_rules.adamantine_bucket(state) or dynamic_rules.adamantine_pot(state)
        elif self.world.options.craftpermits == CraftingPermits.option_all:
            return dynamic_rules.metal_pedestal(state) or dynamic_rules.metal_altar(state) \
            or dynamic_rules.metal_armorstand(state) \
            or dynamic_rules.metal_bin(state) or dynamic_rules.metal_blocks(state) or dynamic_rules.metal_bookcase(state) \
            or dynamic_rules.metal_bucket(state) or dynamic_rules.metal_burial(state) \
            or dynamic_rules.metal_cabinet(state) or dynamic_rules.metal_cage(state) or dynamic_rules.metal_chair(state) \
            or dynamic_rules.metal_crutch(state) or dynamic_rules.metal_door(state) or dynamic_rules.metal_floodgate(state) \
            or dynamic_rules.metal_grate(state) or dynamic_rules.metal_hatchcover(state) or dynamic_rules.metal_weaponrack(state) \
            or dynamic_rules.metal_barrel(state) or dynamic_rules.metal_bucket(state) or dynamic_rules.metal_pot(state) \
            or dynamic_rules.metal_anvil(state) \
            or dynamic_rules.adamantine_pedestal(state) or dynamic_rules.adamantine_altar(state) \
            or dynamic_rules.adamantine_armorstand(state) \
            or dynamic_rules.adamantine_bin(state) or dynamic_rules.adamantine_blocks(state) or dynamic_rules.adamantine_bookcase(state) \
            or dynamic_rules.adamantine_bucket(state) or dynamic_rules.adamantine_burial(state) \
            or dynamic_rules.adamantine_cabinet(state) or dynamic_rules.adamantine_cage(state) or dynamic_rules.adamantine_chair(state) \
            or dynamic_rules.adamantine_crutch(state) or dynamic_rules.adamantine_door(state) or dynamic_rules.adamantine_floodgate(state) \
            or dynamic_rules.adamantine_grate(state) or dynamic_rules.adamantine_hatchcover(state) or dynamic_rules.adamantine_weaponrack(state) \
            or dynamic_rules.adamantine_barrel(state) or dynamic_rules.adamantine_bucket(state) or dynamic_rules.adamantine_pot(state) \
            or dynamic_rules.adamantine_anvil(state)
        
    def skill_gemcutter(self, state:CollectionState) -> bool:
        return state.has("Jeweler's Workshop Blueprint", self.player)
    def skill_gemsetter(self, state:CollectionState) -> bool:
        return state.has("Jeweler's Workshop Blueprint", self.player)
    
    def skill_bookbinder(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.make_paper(state) and dynamic_rules.wood_or_stone_or_metal_or_glass(state)
        elif self.world.options.craftpermits == CraftingPermits.option_on:
            return (dynamic_rules.make_sheet(state) and dynamic_rules.wood_or_stone_or_metal_or_glass_scrollroller(state)) \
            or (dynamic_rules.make_sheet(state) and dynamic_rules.craftdwarf_or_metal_or_glass_bookbinding(state) \
            and dynamic_rules.any_thread(state))
        else:
            return (dynamic_rules.make_sheet(state) and dynamic_rules.wood_or_stone_or_metal_or_glass_scrollroller(state)) \
            or (dynamic_rules.make_sheet(state) and dynamic_rules.craftdwarf_or_metal_or_glass_bookbinding(state) \
            and dynamic_rules.thread(state))
        
    def skill_bonecarver(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.craftdwarf_and_butchery(state)
        else:
            return dynamic_rules.bone_products(state)

    def skill_clothier(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.clothier_workshop(state)
        else:
            return dynamic_rules.cloth_products(state)
    
    def skill_glassmaker(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        return dynamic_rules.glass(state)
    
    def skill_glazer(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.job_type(state, "Ceramics")
        else:
            return dynamic_rules.job_type(state, "Ceramics") and (dynamic_rules.stone_container(state) \
            or dynamic_rules.stone_statue(state) or dynamic_rules.stone_or_wood_crafts(state) \
            or dynamic_rules.stone_jug(state) or dynamic_rules.ceramic_jug(state) \
            or dynamic_rules.stone_pot(state) or dynamic_rules.ceramic_pot(state))
        
    def skill_leatherworker(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.leather_works(state)
        else:
            return dynamic_rules.leather_products(state)
        
    def skill_papermaker(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.famer_workshop(state) or dynamic_rules.screw_press(state)
        else:
            return (dynamic_rules.famer_workshop(state) or dynamic_rules.screw_press(state)) \
            and state.has("Sheet Permit", self.player)
        
    def skill_potter(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.ceramic(state)
        else:
            return dynamic_rules.ceramic_blocks(state) or dynamic_rules.ceramic_jug(state) \
            or dynamic_rules.ceramic_pot(state)
        
    def skill_stonecrafter(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.craftdwarf_workshop(state)
        else:
            return dynamic_rules.stone_cup(state) or dynamic_rules.stone_or_wood_crafts(state) \
            or dynamic_rules.wood_or_stone_toy(state) or dynamic_rules.stone_jug(state) \
            or dynamic_rules.stone_pot(state) or dynamic_rules.wood_or_stone_hive(state) \
            or dynamic_rules.craftdwarf_amulet(state) or dynamic_rules.craftdwarf_bracelet(state) \
            or dynamic_rules.craftdwarf_crown(state) or dynamic_rules.craftdwarf_die(state) \
            or dynamic_rules.craftdwarf_earring(state) or dynamic_rules.craftdwarf_figurine(state) \
            or dynamic_rules.craftdwarf_ring(state) or dynamic_rules.craftdwarf_scepter(state)

    def skill_strandextractor(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.mining_depth:
            return state.has("Progressive Mining Depth", self.player, 4) and dynamic_rules.craftdwarf_workshop(state)
        else:
            return dynamic_rules.craftdwarf_workshop(state)
    
    def skill_waxworker(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.craftdwarf_workshop(state) and dynamic_rules.screw_press(state)
        else:
            return dynamic_rules.stone_or_wood_crafts(state) and dynamic_rules.make_honey(state)
        
    def skill_weaver(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits != CraftingPermits.option_all:
            return state.has("Loom Blueprint", self.player) and (state.has("Farm Plot Blueprint", self.player) \
            or state.has("Farmer's Workshop Blueprint", self.player))
        else:
            return (state.has("Loom Blueprint", self.player) and (state.has("Farm Plot Blueprint", self.player) \
            or state.has("Farmer's Workshop Blueprint", self.player))) and dynamic_rules.permit(state, "Cloth")
        
    def skill_woodcrafter(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.craftdwarf_workshop(state)
        else:
            return dynamic_rules.stone_or_wood_crafts(state) or dynamic_rules.wood_bolt(state) \
            or dynamic_rules.wood_jug(state) or dynamic_rules.wood_or_stone_hive(state) \
            or dynamic_rules.bone_bolt(state)
        
    def skill_mechanic(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state) or dynamic_rules.mechanic_workshop(state)
        else:
            return dynamic_rules.mechanic_mechanism(state)
        
    def skill_pumpoperator(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state) or dynamic_rules.wood(state)
        else:
            return dynamic_rules.wood_or_metal_or_glass_corkscrew(state) \
            and dynamic_rules.wood_or_stone_or_metal_or_glass_or_ceramic_blocks(state) \
            and dynamic_rules.wood_or_metal_or_glass_pipesection(state) 
        
    def skill_siegeengineer(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.seige_workshop(state)
        else:
            return dynamic_rules.seige_ballistaparts(state) or dynamic_rules.seige_catapultparts(state) 
        
    def skill_siegeoperator(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.seige_workshop(state)
        else:
            return dynamic_rules.seige_ballistaparts(state) or dynamic_rules.seige_catapultparts(state) 
        
    def office(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.wood_or_stone_or_metal_or_glass(state)
        else:
            return dynamic_rules.wood_or_stone_or_metal_or_glass_chair(state) \
            and dynamic_rules.wood_or_stone_or_metal_or_glass_door(state)
        
    def skill_hammerer(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state)
        else:
            return dynamic_rules.metal_warhammer(state)

    def skill_macer(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state)
        else:
            return dynamic_rules.metal_mace(state)

    def skill_speardwarf(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state)
        else:
            return dynamic_rules.metal_spear(state)
        
    def skill_sworddwarf(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state)
        else:
            return dynamic_rules.metal_sword(state)
        
    def skill_armordwarf(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.metal(state)
        else:
            return dynamic_rules.armor(state)
        
    def skill_shielddwarf(self, state:CollectionState) -> bool:
        dynamic_rules = DynamicCraftingLocationRules(self.world)
        if self.world.options.craftpermits == CraftingPermits.option_off:
            return dynamic_rules.wood_or_leather_or_metal(state)
        else:
            return dynamic_rules.wood_or_leather_or_metal_buckler(state) or dynamic_rules.wood_or_leather_or_metal_shield(state)
        
    


