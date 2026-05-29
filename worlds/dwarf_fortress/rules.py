from BaseClasses import MultiWorld
from worlds.dwarf_fortress.crafting_locations import DynamicCraftingLocationRules
from .options import DwarfFortressGoal


# Workshop blueprint → which production locations it gates.
# Locations not listed here are reachable from the start (unlocked workshops).
BLUEPRINT_RULES: dict[str, list[str]] = {
    "Craftsdwarf's Workshop Blueprint": [
        "First Crafted Item",
    ],
    "Forge Blueprint": [
        "First Weapon Forged",
        "First Armor Crafted",
    ],
    "Smelter Blueprint": [
        "First Metal Bar Smelted",
    ],
    "Kitchen Blueprint": [
        "First Prepared Meal",
    ],
    "Jeweler's Workshop Blueprint": [
        "First Gem Cut",
    ],
    "Loom Blueprint": [
        "First Cloth Woven",
    ],
    "Tanner's Blueprint": [
        "First Leather Tanned",
    ],
    "Mechanic's Workshop Blueprint": [
        "First Mechanism Made",
        "First Trap Built",
    ],
}


def set_rules(world: "DwarfFortressWorld") -> None:
    multiworld: MultiWorld = world.multiworld
    player: int = world.player
    options = world.options

    # ── Workshop blueprint gates ──────────────────────────────────────────────
    # Production locations require the matching workshop blueprint to be
    # received before they can be checked.
    for blueprint_name, location_names in BLUEPRINT_RULES.items():
        for loc_name in location_names:
            loc = multiworld.get_location(loc_name, player)
            loc.access_rule = lambda state, bp=blueprint_name: state.has(bp, player)

    # -- Dynamic location requirements -----------------------------------------
    if len(world.dynamic_locations) > 0:
        dynamic_rules = DynamicCraftingLocationRules(world)
        dynamic_rules.set_dynamic_rules()

    # ── Goal condition ────────────────────────────────────────────────────────
    goal_location = multiworld.get_location("Goal", player)

    if options.goal == DwarfFortressGoal.option_slay_megabeast:
        # Killing a megabeast requires proper dwarven armaments.
        goal_location.access_rule = lambda state: state.has("Artifact Weapon", player)

    elif options.goal == DwarfFortressGoal.option_legendary_wealth:
        # The Legendary Blueprint is the key item for a wealth run.
        goal_location.access_rule = lambda state: state.has("Legendary Blueprint", player)

    elif options.goal == DwarfFortressGoal.option_mountainhome:
        # Mountainhome requires substantial fortress development.
        goal_location.access_rule = lambda state: (
            state.has("Legendary Blueprint", player)
            and state.has("Artifact Weapon", player)
        )
    else:
        # Population Boom: population grows organically, but the fortress must
        # be established enough to sustain it — require any one progression item.
        goal_location.access_rule = lambda state: (
            state.has("Legendary Blueprint", player)
            or state.has("Artifact Weapon", player)
            or state.has("Artifact Armor", player)
        )

