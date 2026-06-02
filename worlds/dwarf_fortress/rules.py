from BaseClasses import MultiWorld
from worlds.dwarf_fortress.craftsanity import DynamicCraftingLocationRules
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

# Wealth tier → how many Merchant's Coffers needed to unlock it.
WEALTH_COFFER_RULES: list[tuple[str, int]] = [
    ("Humble Beginnings (1,000☼)",    1),
    ("Growing Stronghold (10,000☼)",  2),
    ("Prosperous Fortress (50,000☼)", 3),
    ("Rich Citadel (100,000☼)",       4),
    ("Legendary Vault (500,000☼)",    5),
]

# Population/title tier → how many Immigration Waves needed to unlock it.
TITLE_WAVE_RULES: list[tuple[str, int]] = [
    ("Hamlet Established",     1),
    ("Village Established",    2),
    ("Town Established",       3),
    ("City Established",       4),
    ("Metropolis Established", 5),
]

# Noble rank → charter item required to check that location.
NOBLE_CHARTER_RULES: list[tuple[str, str]] = [
    ("Baron Appointed",         "Baron's Charter"),
    ("Count Appointed",         "Count's Charter"),
    ("Duke Appointed",          "Duke's Charter"),
    ("Monarch Takes Residence", "Monarch's Invitation"),
]


def set_rules(world: "DwarfFortressWorld") -> None:
    multiworld: MultiWorld = world.multiworld
    player: int = world.player
    options = world.options

    # ── Workshop blueprint gates ──────────────────────────────────────────────
    for blueprint_name, location_names in BLUEPRINT_RULES.items():
        for loc_name in location_names:
            loc = multiworld.get_location(loc_name, player)
            loc.access_rule = lambda state, bp=blueprint_name: state.has(bp, player)

    # ── Progressive Coffer gates (wealth tier locations) ──────────────────────
    for loc_name, coffers_needed in WEALTH_COFFER_RULES:
        loc = multiworld.get_location(loc_name, player)
        loc.access_rule = lambda state, n=coffers_needed: state.count("Merchant's Coffer", player) >= n

    # ── Immigration Wave gates (population / title tier locations) ────────────
    for loc_name, waves_needed in TITLE_WAVE_RULES:
        loc = multiworld.get_location(loc_name, player)
        loc.access_rule = lambda state, n=waves_needed: state.count("Immigration Wave", player) >= n

    # ── Noble Ladder gates (noble rank locations) ─────────────────────────────
    for loc_name, charter_name in NOBLE_CHARTER_RULES:
        loc = multiworld.get_location(loc_name, player)
        loc.access_rule = lambda state, charter=charter_name: state.has(charter, player)

    # -- Dynamic location requirements -----------------------------------------
    if len(world.dynamic_locations) > 0:
        dynamic_rules = DynamicCraftingLocationRules(world)
        dynamic_rules.set_dynamic_rules()

    # ── Goal condition ────────────────────────────────────────────────────────
    goal_location = multiworld.get_location("Goal", player)

    if options.goal == DwarfFortressGoal.option_slay_megabeast:
        # Megabeast requires armaments, a battle-ready military, and a populated fortress.
        goal_location.access_rule = lambda state: (
            state.has("Artifact Weapon", player)
            and state.count("Military Training", player) >= 3
            and state.count("Immigration Wave", player) >= 2
        )

    elif options.goal == DwarfFortressGoal.option_legendary_wealth:
        # Legendary Wealth requires the Blueprint, all five coffers, and a workforce.
        goal_location.access_rule = lambda state: (
            state.has("Master Builder's Codex", player)
            and state.count("Merchant's Coffer", player) >= 5
            and state.count("Immigration Wave", player) >= 3
        )

    elif options.goal == DwarfFortressGoal.option_mountainhome:
        # Mountainhome requires fortress prestige, armaments, a monarch, and a full city.
        goal_location.access_rule = lambda state: (
            state.has("Master Builder's Codex", player)
            and state.has("Artifact Weapon", player)
            and state.has("Monarch's Invitation", player)
            and state.count("Immigration Wave", player) >= 5
        )

    else:
        # Population Boom: all immigration waves must have arrived plus fortress established.
        goal_location.access_rule = lambda state: (
            state.count("Immigration Wave", player) >= 5
            and (
                state.has("Master Builder's Codex", player)
                or state.has("Artifact Weapon", player)
                or state.has("Artifact Armor", player)
            )
        )
    multiworld.completion_condition[player] = goal_location.access_rule

