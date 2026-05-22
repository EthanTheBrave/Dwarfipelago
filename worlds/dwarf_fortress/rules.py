from BaseClasses import MultiWorld
from .options import DwarfFortressGoal


def set_rules(world: "DwarfFortressWorld") -> None:
    multiworld: MultiWorld = world.multiworld
    player: int = world.player
    options = world.options

    # All production and trade locations are reachable from the start —
    # the player can work toward them in any order.

    # The goal location requires the player to have received progression items
    # (the legendary blueprint signals readiness for the final push).
    goal_location = multiworld.get_location("Goal", player)
    goal_location.access_rule = lambda state: state.has("Legendary Blueprint", player)
