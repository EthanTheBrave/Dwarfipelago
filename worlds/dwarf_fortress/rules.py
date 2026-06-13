from BaseClasses import MultiWorld
from worlds.dwarf_fortress.craftsanity_rules import DynamicCraftingLocationRules
from .options import DwarfFortressGoal, CraftingPermits


# Wealth tier → how many Merchant's Coffers needed to unlock it.
WEALTH_COFFER_RULES: list[tuple[str, int]] = [
    ("Humble Beginnings (1,000)",    1),
    ("Growing Stronghold (10,000)",  2),
    ("Prosperous Fortress (50,000)", 3),
    ("Rich Citadel (100,000)",       4),
    ("Legendary Vault (500,000)",    5),
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
    dynamic_rules = DynamicCraftingLocationRules(world)

    # ── Workshop blueprint gates ──────────────────────────────────────────────
    loc = multiworld.get_location("First Minecart Made", player)
    dynamic_rules.df_location_rule(loc, "Minecart", "")

    loc = multiworld.get_location("First Prepared Meal", player)
    dynamic_rules.df_location_rule(loc, "Prepared Meal", "")

    loc = multiworld.get_location("First Cloth Woven", player)
    dynamic_rules.df_location_rule(loc, "Cloth", "")

    loc = multiworld.get_location("First Crafted Item", player)
    dynamic_rules.df_location_rule(loc, "Crafts", "")

    loc = multiworld.get_location("First Gem Cut", player)
    loc.access_rule = lambda state: state.has("Jeweler's Workshop Blueprint", player)

    loc = multiworld.get_location("First Leather Tanned", player)
    dynamic_rules.df_location_rule(loc, "Leather", "")

    loc = multiworld.get_location("First Mechanism Made", player)
    dynamic_rules.df_location_rule(loc, "Mechanism", "")

    loc = multiworld.get_location("First Trap Built", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: state.has("Mechanic's Workshop Blueprint", player)
    else:
        loc.access_rule = lambda state: state.has("Mechanic's Workshop Blueprint", player) and \
            state.has_any(["Spike Permit", "Ball Permit"], player)
    
    loc = multiworld.get_location("First Millstone Made", player)
    dynamic_rules.df_location_rule(loc, "Millstone", "")

    loc = multiworld.get_location("First Block Cut", player)
    dynamic_rules.df_location_rule(loc, "Blocks", "")

    loc = multiworld.get_location("First Cage Constructed", player)
    dynamic_rules.df_location_rule(loc, "Cage", "")

    loc = multiworld.get_location("First Furniture Made", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: dynamic_rules.metal(state) or dynamic_rules.wood(state) \
            or dynamic_rules.stone(state) or dynamic_rules.glass(state)
    else:
        loc.access_rule = lambda state: dynamic_rules.wood_or_stone_or_metal_or_glass_chair(state) \
            or dynamic_rules.wood_or_stone_or_metal_or_glass_cabinet(state) or dynamic_rules.wood_or_metal_bucket(state) \
            or dynamic_rules.wood_or_stone_or_metal_or_glass_floodgate(state) or dynamic_rules.wood_or_stone_or_metal_or_glass_door(state)
    
    loc = multiworld.get_location("First Brew Complete", player)
    dynamic_rules.df_location_rule(loc, "Alcohol", "")

    loc = multiworld.get_location("First Barrel Made", player)
    dynamic_rules.df_location_rule(loc, "Barrel", "")

    loc = multiworld.get_location("First Chest Made", player)
    dynamic_rules.df_location_rule(loc, "Container", "")

    loc = multiworld.get_location("First Table Made", player)
    dynamic_rules.df_location_rule(loc, "Table", "")

    loc = multiworld.get_location("First Bed Made", player)
    dynamic_rules.df_location_rule(loc, "Bed", "")

    loc = multiworld.get_location("First Weapon Forged", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: dynamic_rules.metal(state) or dynamic_rules.wood(state)
    else:
        loc.access_rule = lambda state: dynamic_rules.training_axe(state) \
            or dynamic_rules.training_spear(state) or dynamic_rules.training_sword(state) \
            or dynamic_rules.make_battleaxe(state) or dynamic_rules.make_sword(state) or dynamic_rules.make_spear(state) \
            or dynamic_rules.make_warhammer(state) or dynamic_rules.wood_or_bone_bolt(state)
    
    loc = multiworld.get_location("First Armor Crafted", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: dynamic_rules.metal(state) or dynamic_rules.leather_works(state)
    else:
        loc.access_rule = lambda state: dynamic_rules.metal_or_bone_or_leather_helm(state) \
            or dynamic_rules.metal_or_bone_gauntlets(state) or dynamic_rules.metal_or_leather_ubodyarmor(state) \
            or dynamic_rules.metal_or_bone_or_leather_lbodyarmor(state)
    
    loc = multiworld.get_location("First Anvil Made", player)
    dynamic_rules.df_location_rule(loc, "Anvil", "")

    loc = multiworld.get_location("First Metal Bar Smelted", player)
    dynamic_rules.df_location_rule(loc, "Metal Bars", "")

    # -- Harvesting Gates ------------------------------------------------------
    loc = multiworld.get_location("Harvest 50 Crops", player)
    loc.access_rule = lambda state: dynamic_rules.process_resource(state, "farming")

    loc = multiworld.get_location("Harvest 100 Crops", player)
    loc.access_rule = lambda state: dynamic_rules.process_resource(state, "farming")

    loc = multiworld.get_location("Harvest 250 Crops", player)
    loc.access_rule = lambda state: dynamic_rules.process_resource(state, "farming")

    loc = multiworld.get_location("Harvest 500 Crops", player)
    loc.access_rule = lambda state: dynamic_rules.process_resource(state, "farming")

    loc = multiworld.get_location("Harvest 1,000 Crops", player)
    loc.access_rule = lambda state: dynamic_rules.process_resource(state, "farming")

    # -- Infrastructure ---------------------------------------------------------
    loc = multiworld.get_location("Built a Well", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: (dynamic_rules.metal(state) or dynamic_rules.wood(state))  \
              and dynamic_rules.mechanic_workshop(state)
    else:
        loc.access_rule = lambda state: dynamic_rules.metal_or_cloth_ropechain(state) \
        and dynamic_rules.wood_or_stone_or_metal_or_glass_or_ceramic_blocks(state) and dynamic_rules.mechanic_mechanism(state) \
        and dynamic_rules.wood_or_metal_bucket(state)
    
    loc = multiworld.get_location("Pumped Water", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: (dynamic_rules.metal(state) or dynamic_rules.wood(state))
    else:
        loc.access_rule = lambda state: dynamic_rules.wood_or_metal_or_glass_corkscrew(state) \
        and dynamic_rules.wood_or_stone_or_metal_or_glass_or_ceramic_blocks(state) and dynamic_rules.wood_or_metal_or_glass_pipesection(state) 

    loc = multiworld.get_location("Pumped Magma", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: (dynamic_rules.metal(state) or dynamic_rules.glass(state)) # magma safe materials
    else:
        loc.access_rule = lambda state: (dynamic_rules.metal_corkscrew(state) or dynamic_rules.glass_corkscrew(state)) \
        and (dynamic_rules.stone_blocks(state) or dynamic_rules.glass_blocks(state) or dynamic_rules.metal_blocks(state)) \
        and (dynamic_rules.glass_pipesection(state) or dynamic_rules.metal_pipesection(state))
    
    # ── Biology / Animal Milestones ───────────────────────────────────────────────
    # Eggs hatch in a nest box, which is built only at the Craftsdwarf's Workshop.
    loc = multiworld.get_location("First Eggs Hatched", player)
    loc.access_rule = lambda state: dynamic_rules.craftdwarf_workshop(state)

    # Catching a hostile beast needs a cage trap = a cage plus a mechanism (built
    # at the Mechanic's Workshop), so require both.
    loc = multiworld.get_location("Caged a Hostile Beast", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: dynamic_rules.wood_or_metal_or_glass(state) \
            and dynamic_rules.mechanic_workshop(state)
    else:
        loc.access_rule = lambda state: dynamic_rules.wood_or_metal_or_glass_cage(state) \
            and dynamic_rules.mechanic_mechanism(state)


    # ── Progressive Coffer gates (wealth tier locations) ──────────────────────
    if options.goal == DwarfFortressGoal.option_legendary_wealth:
        for loc_name, coffers_needed in WEALTH_COFFER_RULES:
            loc = multiworld.get_location(loc_name, player)
            loc.access_rule = lambda state, n=coffers_needed: state.count("Merchant's Coffer", player) >= n

    # ── Immigration Wave gates (population / title tier locations) ────────────
    for loc_name, waves_needed in TITLE_WAVE_RULES:
        loc = multiworld.get_location(loc_name, player)
        loc.access_rule = lambda state, n=waves_needed: state.count("Immigration Wave", player) >= n

    # ── Noble Ladder gates (noble rank locations) ─────────────────────────────
    if options.goal == DwarfFortressGoal.option_mountainhome :
        for loc_name, charter_name in NOBLE_CHARTER_RULES:
            loc = multiworld.get_location(loc_name, player)
            loc.access_rule = lambda state, charter=charter_name: state.has(charter, player)

    # -- Dynamic location requirements -----------------------------------------
    if len(world.dynamic_locations) > 0:
        dynamic_rules.set_dynamic_rules()


    # ── Goal condition ────────────────────────────────────────────────────────
    goal_location = multiworld.get_location("Goal", player)

    if options.goal == DwarfFortressGoal.option_slay_megabeast:
        # Megabeast requires armaments, a battle-ready military, and a populated fortress.
        goal_location.access_rule = lambda state: (
            state.has("Artifact Weapon", player)
            and state.count("Military Training", player) >= 4
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

    elif options.goal == DwarfFortressGoal.option_king_remains:
        # required to find all remains
        goal_location.access_rule = lambda state: (
            state.has("Remains of the Great King", player, options.remains_great_king.value)
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
