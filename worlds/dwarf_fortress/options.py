from dataclasses import dataclass
from Options import Choice, Range, PerGameCommonOptions


class DwarfFortressGoal(Choice):
    """The win condition for the Dwarf Fortress world."""
    display_name = "Goal"
    option_slay_megabeast = 0
    option_legendary_wealth = 1
    option_legendary_skill = 2
    default = 0


class WealthGoalAmount(Range):
    """Target fortress wealth when goal is 'Legendary Wealth'."""
    display_name = "Wealth Goal Amount"
    range_start = 10000
    range_end = 1000000
    default = 100000


class TrapItemWeight(Range):
    """Percentage of filler items that are traps (0 = no traps, 100 = all traps)."""
    display_name = "Trap Item Weight"
    range_start = 0
    range_end = 100
    default = 20


@dataclass
class DwarfFortressOptions(PerGameCommonOptions):
    goal: DwarfFortressGoal
    wealth_goal_amount: WealthGoalAmount
    trap_item_weight: TrapItemWeight
