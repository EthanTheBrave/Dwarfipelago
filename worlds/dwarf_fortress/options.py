from dataclasses import dataclass
from Options import Choice, Range, PerGameCommonOptions, DeathLink, OptionList, Toggle


class DwarfFortressGoal(Choice):
    """The win condition for the Dwarf Fortress world."""
    display_name = "Goal"
    option_slay_megabeast = 0
    option_legendary_wealth = 1
    option_population_boom = 2
    option_mountainhome = 3
    default = 2


class WealthGoalAmount(Range):
    """Target fortress wealth when goal is 'Legendary Wealth'."""
    display_name = "Wealth Goal Amount"
    range_start = 10000
    range_end = 1000000
    default = 100000


class PopulationGoalAmount(Range):
    """Target fortress population when goal is 'Population Boom'."""
    display_name = "Population Goal Amount"
    range_start = 20
    range_end = 500
    default = 300


class TrapItemWeight(Range):
    """Percentage of filler items that are traps (0 = no traps, 100 = all traps)."""
    display_name = "Trap Item Weight"
    range_start = 0
    range_end = 100
    default = 20


class DeathLinkThreshold(Range):
    """
    How many of your dwarves must die to send one DeathLink to other players.
    Incoming DeathLinks kill this many of your dwarves in return.
    Set to 1 for classic one-death-equals-one-death behaviour.
    """
    display_name = "Death Link Threshold"
    range_start = 1
    range_end = 20
    default = 5

class EnableItemCreationLocation(Choice):
    """
    Enable Craftable locations where you are required to make X of Items.
    If option_storage is selected, the X amount needs to be present in storage.
    """
    display_name = "Enable Item Creation Locations"
    option_off = 0
    option_on = 1
    option_storage = 2

class VariableItemCreationLocations(OptionList):
    """
    If Craftable locations are enabled, which items to craft X amount are checks.
    """
    display_name = "Craftable X Items locations"
    valid_keys = {
        "Beds", "Corkscrew", "Blocks", "Spike", "Ball", "Altar", "Animal Trap", "Armor Stand",
        "Barrel", "Bin", "Bookcase", "Bucket", "Buckler", "Cabinet", "Cage", "Burial Container", "Chair",
        "Container", "Crutch", "Door", "Floodgate", "Grate", "Hatch Cover", "Minecart", "Pedestal",
        "Pipe Section", "Shield", "Splint", "Stepladder", "Table", "Training Axe", "Training Spear",
        "Training Sword", "Weapon Rack", "Wheelbarrow"
    }
    default = valid_keys.copy() 

class VariableItemMaterialToggle(Toggle):
    """
    If Craftable locations are enabled, Do you need to craft certian materials of that item?
    Craft X amount of Y Item
    """
    display_name = "Enable Item Creation Item Materials"

class VariableItemTypeCreationLocations(OptionList):
    """
    Select which item types for craft X amount are required.
    """
    display_name = "Craftable X Items locations"
    valid_keys = {
        "Stone", "Wood", "Metal", "Glass", "Leather", "Cloth", "Bone", "Shells", "Ceramic"
    }
    default = valid_keys.copy() 

class VariableItemCreationMaxAmount(Range):
    """
    If Craftable locations are enabled, what is the max amount to need to make per item?
    """
    display_name = "Max Craftable location amount"
    range_start = 10
    range_end = 100
    default = 15

class VariableItemCreationThreshold(Range):
    """
    If Craftable locations are enabled, How many do you need to make per check?
    ex: 10 = every 10 crafted items is a check 
    """
    display_name = "Craftable Location Check Threshold"
    range_start = 5
    range_end = 100
    default = 5

@dataclass
class DwarfFortressOptions(PerGameCommonOptions):
    deathlink: DeathLink
    deathlink_threshold: DeathLinkThreshold
    goal: DwarfFortressGoal
    wealth_goal_amount: WealthGoalAmount
    population_goal_amount: PopulationGoalAmount
    craftable_locations: EnableItemCreationLocation
    craftable_items: VariableItemCreationLocations
    craftable_enable_materials: VariableItemMaterialToggle
    craftable_materials: VariableItemTypeCreationLocations
    craftable_max_amount: VariableItemCreationMaxAmount
    craftable_threshold: VariableItemCreationThreshold
    trap_item_weight: TrapItemWeight
