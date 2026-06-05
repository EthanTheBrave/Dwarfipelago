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

class TradesInLogic(Toggle):
    """
    Should trading resources be considered in logic?
    EX: trades for metal bars instead of requiring a Smelter Blueprint
    """
    display_name = "Resource Trading in Logic"

class EnableCraftsanity(Choice):
    """
    Enable Craftsanity where you are required to make X amount of Items.
    If option_storage is selected, the X amount needs to be present in storage.
    """
    display_name = "Enable Item Creation Locations"
    option_off = 0
    option_on = 1
    option_storage = 2
    default = 1


class CraftsanityItemGroup(Choice):
    """
    Selects which items count as craftsanity location checks.
    Easy: 10 basic items craftable from the very start. 
    (Beds, Blocks, Alcohol, Chair, Table, Door, Barrel, Bucket, Container, Cloth)

    Medium: 25 early-game items across common workshops. 
    (Easy + Crafts, Mechanism, Cage, Leather, Prepared Meal, Bin, Cabinet, Floodgate, Animal Trap, Statue, Armor Stand, Pedestal, Weapon Rack, Corkscrew, Bookcase)

    Hard: ~45 items spanning early and late game production. 
    (Easy + Medium + Metal Bars, Glass, Ash, Charcoal, Helm, Upper Body Armor, Gauntlets, Lower Body Armor, Crossbow, Bolt, Battle Axe, Short Sword,
    War Hammer, Anvil, Rope/Chain, Coins, Goblet, Tallow, Oil, Dye, Traction Bench)
    Craftsanity: Every craftable item becomes a check.
    Choose: Pick items manually using the 'Craftsanity Items Locations' list below.
    """
    display_name = "Craftsanity Item Group"
    option_easy = 0
    option_medium = 1
    option_hard = 2
    option_craftsanity = 3
    option_choose = 4
    default = 1


class CraftsanityItems(OptionList):
    """
    Manual item selection for craftsanity checks.
    Only active when Craftsanity Item Group is set to 'Choose'.
    """
    display_name = "craftsanity Items locations"
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

class CraftsanityEnableMaterials(Toggle):
    """
    If craftsanity is enabled, Do you want seperate crafting checks based on material type?
    EX: Craft X amount of "Y" Item. Here is where "Y" matters if enabled 
    """
    display_name = "Enable Craftsanity Material Type"

class CraftsanityMaterials(OptionList):
    """
    Select which material types for crafting X amount are required.
    """
    display_name = "Craftsanity Items Materials"
    valid_keys = {
        "Stone", "Wood", "Metal", "Glass", "Leather", "Cloth", "Bone", "Ceramic"
    }
    default = valid_keys.copy() 

class CraftsanityMaxAmount(Range):
    """
    If Craftsanity is enabled, what is the max amount you need to make per item?
    """
    display_name = "Max Craftsanity Amount"
    range_start = 10
    range_end = 500
    default = 15

class CraftsanityThreshold(Range):
    """
    If Craftsanity is enabled, How many items crafted is a check?
    ex: 10 = every 10 crafted items is a check 
    """
    display_name = "Craftsanity Check Threshold"
    range_start = 5
    range_end = 500
    default = 5

class CraftingItems(Choice):
    """
    If Crafting Items is enabled, you cannot craft certian items until you got the appropriate AP item. 
    When set to "on", The following crafts you can preform that do not AP items (comes with the workshop):
    Beds, Charcoal, Leather, Cloth, Alcohol, Prepared Meal
    When set to "all", the above are included and are required to obtain them
    Craftsanity must be enabled to use this feature.
    """
    display_name = "Crafting Items"
    option_off = 0
    option_on = 1
    option_all = 2
    default = 0


class StartingDefaultDFInventory(StartInventory):
    """Starting Blueprints to make your starting game less "fun" """
    display_name = "Start Inventory"
    default = {"Carpenter's Workshop Blueprint": 1, "Stoneworker's Workshop Blueprint": 1, "Still Blueprint": 1, "Farm Plot Blueprint": 1}

@dataclass
class DwarfFortressOptions(PerGameCommonOptions):
    deathlink: DeathLink
    deathlink_threshold: DeathLinkThreshold
    deathlink_percentage: DeathLinkPercentage
    goal: DwarfFortressGoal
    wealth_goal_amount: WealthGoalAmount
    population_goal_amount: PopulationGoalAmount
    trades_inlogic: TradesInLogic
    craftsanity: EnableCraftsanity
    craftitems: CraftingItems
    craftsanity_item_group: CraftsanityItemGroup
    craftsanity_items: CraftsanityItems
    craftsanity_enable_materials: CraftsanityEnableMaterials
    craftsanity_materials: CraftsanityMaterials
    craftsanity_max_amount: CraftsanityMaxAmount
    craftsanity_threshold: CraftsanityThreshold
    trap_item_weight: TrapItemWeight
    start_inventory: StartingDefaultDFInventory
