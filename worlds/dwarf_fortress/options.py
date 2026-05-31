from dataclasses import dataclass
from Options import Choice, Range, PerGameCommonOptions, DeathLink, OptionList, Toggle, StartInventory


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
    When Death Link Percentage is enabled, this value is treated as a percentage of your current population.
    """
    display_name = "Death Link Threshold"
    range_start = 1
    range_end = 50
    default = 5


class DeathLinkPercentage(Toggle):
    """
    When enabled, the Death Link Threshold is treated as a percentage of your current population
    rather than a flat dwarf count.
    Example: threshold=10 with 80 dwarves kills/requires 8 dwarves per DeathLink.
    """
    display_name = "Death Link Percentage"

class EnableItemCreationLocation(Choice):
    """
    Enable Craftable locations where you are required to make X of Items.
    If option_storage is selected, the X amount needs to be present in storage.
    """
    display_name = "Enable Item Creation Locations"
    option_off = 0
    option_on = 1
    option_storage = 2

class TradesInLogic(Toggle):
    """
    Should resource trading be considered in logic?
    EX: trade for Metal Bars instead of requiring a Smelter Blueprint
    """
    display_name = "Resource Trading in Logic"

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
        "Training Sword", "Weapon Rack", "Wheelbarrow", "Crossbow", "Bolt", "Millstone", "Quern",
        "Slab", "Statue", "Mechanism", "Traction Bench", "Crafts", "Liquid Container", "Goblet",
        "Mug", "Cup", "Toy", "Totem", "Helm", "Ballista Parts", "Catapult Parts", "Ballista Arrows",
        "Ash", "Charcoal", "Metal Bars", "Coke Bars", "Pearlash", "Gypsum Plaster", "Jug", "Large Pot",
        "Hive", "Quicklime", "Glass", "Window", "Book Binding",
        "Scroll Roller", "Leather", "Sheet", "Cloth", "Alcohol", "Lye", "Potash", "Milk of Lime",
        "Prepared Meal", "Tallow", "Oil", "Press Cake", "Honey", "Bee Wax", "Headgear Clothing",
        "Upper Body Clothing", "Upper Body Armor", "Hand Clothing", "Gauntlets", "Lower Body Clothing",
        "Lower Body Armor", "Footwear", "Dye", "Bag", "Rope/Chain", "Battle Axe", "Mace",
        "Pick", "Short Sword", "Spear", "War Hammer", "Anvil", "Coins", "Soap"
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
    display_name = "Craftable X Items Materials"
    valid_keys = {
        "Stone", "Wood", "Metal", "Glass", "Leather", "Cloth", "Bone", "Ceramic"
    }
    default = valid_keys.copy() 

class VariableItemCreationMaxAmount(Range):
    """
    If Craftable locations are enabled, what is the max amount to need to make per item?
    """
    display_name = "Max Craftable location amount"
    range_start = 10
    range_end = 500
    default = 15

class VariableItemCreationThreshold(Range):
    """
    If Craftable locations are enabled, How many do you need to make per check?
    ex: 10 = every 10 crafted items is a check 
    """
    display_name = "Craftable Location Check Threshold"
    range_start = 5
    range_end = 500
    default = 5

class StartingDefaultDFInventory(StartInventory):
    """Starting Blueprints to make your starting game less "fun" """
    display_name = "Start Inventory"
    default = {"Carpenter's Workshop Blueprint": 1, "Stoneworker's Workshop Blueprint": 1, "Still Blueprint": 1}

@dataclass
class DwarfFortressOptions(PerGameCommonOptions):
    deathlink: DeathLink
    deathlink_threshold: DeathLinkThreshold
    deathlink_percentage: DeathLinkPercentage
    goal: DwarfFortressGoal
    wealth_goal_amount: WealthGoalAmount
    population_goal_amount: PopulationGoalAmount
    craftable_locations: EnableItemCreationLocation
    trades_inlogic: TradesInLogic
    craftable_items: VariableItemCreationLocations
    craftable_enable_materials: VariableItemMaterialToggle
    craftable_materials: VariableItemTypeCreationLocations
    craftable_max_amount: VariableItemCreationMaxAmount
    craftable_threshold: VariableItemCreationThreshold
    trap_item_weight: TrapItemWeight
    start_inventory: StartingDefaultDFInventory
