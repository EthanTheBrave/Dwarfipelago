import math
import re
from typing import List, Set, Union, TYPE_CHECKING
from dataclasses import dataclass
from BaseClasses import ItemClassification, Location, LocationProgressType, CollectionState
from worlds.generic.Rules import set_rule
from .options import SkillsanitySkillGroup
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
     "Trapper", "Bone Doctor", "Sugeon", "Suturer", "Wound Dresser", "Bee Keeper", "Gelder", "Book Binder",
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
            elif self.world.options.skillsanity_skill_group == SkillsanitySkillGroup.option_hard:
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
                    for location in skill_locations:
                        if self.skill_levels[levels] in location.name:
                            remove_skills.append(location)
            self.world.remove_skill_locations_names = {n.name for n in remove_skills}
            self.world.skill_locations = skill_locations
            

                
