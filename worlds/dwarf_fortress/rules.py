from BaseClasses import MultiWorld
from .options import DwarfFortressGoal


def set_rules(world: "DwarfFortressWorld") -> None:
    multiworld: MultiWorld = world.multiworld
    player: int = world.player
    options = world.options

    # All production and trade locations are reachable from the start —
    # the player can work toward them in any order.

    goal_location = multiworld.get_location("Goal", player)

    if options.goal == DwarfFortressGoal.option_slay_megabeast:
        # Killing a megabeast requires proper dwarven armaments.
        goal_location.access_rule = lambda state: state.has("Artifact Weapon", player)

    elif options.goal == DwarfFortressGoal.option_legendary_wealth:
        # The Legendary Blueprint is the key item for a wealth run.
        goal_location.access_rule = lambda state: state.has("Legendary Blueprint", player)

    else:
        # Population Boom: population grows organically, but the fortress must
        # be established enough to sustain it — require any one progression item.
        goal_location.access_rule = lambda state: (
            state.has("Legendary Blueprint", player)
            or state.has("Artifact Weapon", player)
            or state.has("Artifact Armor", player)
        )
