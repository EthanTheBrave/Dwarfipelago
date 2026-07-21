from BaseClasses import MultiWorld
from worlds.dwarf_fortress.craftsanity_rules import DynamicCraftingLocationRules
from worlds.dwarf_fortress.items import BLUEPRINT_ITEMS, CRAFT_ITEMS
from worlds.dwarf_fortress.skillsanity import Skillsanity
from .options import DwarfFortressGoal, CraftingPermits
from .locations import SHOP_SLOTS


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

# Workshops a strange mood can claim. A moody dwarf uses the workshop of their
# highest moodable skill, so an artifact mood needs that specific workshop.
# https://dwarffortresswiki.org/index.php/Strange_mood#Skills_and_Workshops
MOODABLE_WORKSHOP_BLUEPRINTS: list[str] = [
    "Craftsdwarf's Workshop Blueprint",
    "Stoneworker's Workshop Blueprint",
    "Carpenter's Workshop Blueprint",
    "Jeweler's Workshop Blueprint",
    "Forge Blueprint",
    "Magma Forge Blueprint",
    "Mechanic's Workshop Blueprint",
    "Bowyer's Workshop Blueprint",
    "Clothier's Shop Blueprint",
    "Leather Works Blueprint",
    "Glass Furnace Blueprint",
    "Magma Glass Furnace Blueprint",
]


def set_rules(world: "DwarfFortressWorld") -> None:
    multiworld: MultiWorld = world.multiworld
    player: int = world.player
    options = world.options
    dynamic_rules = DynamicCraftingLocationRules(world)
    skillsanity_rules = Skillsanity(world)

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
        # if you can make mechanisms, just make a stonefall trap and your done
        loc.access_rule = lambda state: dynamic_rules.mechanic_mechanism(state) \
        or dynamic_rules.metal_spear(state) or dynamic_rules.training_spear(state)
    
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
    dynamic_rules.df_location_rule(loc, "Beds", "")

    loc = multiworld.get_location("First Weapon Forged", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: dynamic_rules.metal(state) or dynamic_rules.wood(state)
    else:
        loc.access_rule = lambda state: dynamic_rules.training_axe(state) \
            or dynamic_rules.training_spear(state) or dynamic_rules.training_sword(state) \
            or dynamic_rules.metal_battleaxe(state) or dynamic_rules.metal_sword(state) or dynamic_rules.metal_spear(state) \
            or dynamic_rules.metal_warhammer(state) or dynamic_rules.woodcraft_or_bonecraft_or_metal_bolt(state) \
            or dynamic_rules.metal_mace(state)
    
    loc = multiworld.get_location("First Armor Crafted", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: dynamic_rules.metal(state) or dynamic_rules.leather_works(state)
    else:
        loc.access_rule = lambda state: dynamic_rules.metal_or_bone_or_leather_helm(state) \
            or dynamic_rules.metal_or_bone_gauntlets(state) or dynamic_rules.metal_cap(state) \
            or dynamic_rules.leather_cap(state) or dynamic_rules.metal_mailshirt(state) \
            or dynamic_rules.metal_lboots(state) or dynamic_rules.metal_or_bone_greaves(state) \
            or dynamic_rules.metal_buckler(state) or dynamic_rules.metal_or_bone_or_leather_leggings(state) \
            or dynamic_rules.metal_hboots(state) or dynamic_rules.metal_breastplate(state) 
    
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

    # -- Iterative milestone ladders --------------------------------------------
    # These tiers are monotonic in play (you cannot reach a higher one without
    # passing the lower ones), so each later tier additionally requires the
    # previous tier to be reachable. Each tier keeps whatever base gate it already
    # has (farming -> Farm Plot Blueprint; mining depth/tiles -> none), and the
    # chain bottoms out at an always-reachable first tier, so no new unreachable
    # locations are introduced.
    def require_previous(names: list[str]) -> None:
        for i in range(1, len(names)):
            tier = multiworld.get_location(names[i], player)
            tier.access_rule = (lambda state, base=tier.access_rule, prev=names[i - 1]:
                                 base(state) and state.can_reach_location(prev, player))

    require_previous([
        "Excavator I (100 tiles)", "Excavator II (500 tiles)",
        "Excavator III (2,000 tiles)", "Excavator IV (5,000 tiles)",
        "Excavator V (10,000 tiles)",
    ])
    require_previous([
        "Harvest 50 Crops", "Harvest 100 Crops", "Harvest 250 Crops",
        "Harvest 500 Crops", "Harvest 1,000 Crops",
    ])
    # Cavern progress + breaches are one monotonic ladder (25% C1 -> 50% C1 ->
    # breach C1 -> ... -> magma sea -> Circus). Off: each step requires the
    # previous. On: gated by item count instead (breach Cn needs n; the progress
    # checks for Cn+1 need n, since you must dig past Cn to reach them).
    if options.mining_depth == False:
        require_previous([
            "25% to the First Cavern", "50% to the First Cavern", "First Cavern Breached",
            "25% to the Second Cavern", "50% to the Second Cavern", "Second Cavern Breached",
            "50% to the Third Cavern", "Third Cavern Breached",
            "Reached the Magma Sea", "Welcome to the Circus",
        ])
    else:
        def needs_depth(name: str, count: int) -> None:
            loc = multiworld.get_location(name, player)
            loc.access_rule = lambda state, c=count: state.has("Progressive Mining Depth", player, c)

        # 25%/50% to Cavern 1 need no unlock: you may always dig to just above it.
        needs_depth("First Cavern Breached", 1)
        needs_depth("25% to the Second Cavern", 1)
        needs_depth("50% to the Second Cavern", 1)
        needs_depth("Second Cavern Breached", 2)
        needs_depth("50% to the Third Cavern", 2)
        needs_depth("Third Cavern Breached", 3)
        needs_depth("Reached the Magma Sea", 4)
        needs_depth("Welcome to the Circus", 4)

        loc = multiworld.get_location("Mined Adamantine", player)
        loc.access_rule = lambda state: state.has("Progressive Mining Depth", player, 4)

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
    # "First Eggs Hatched" disabled: hatch detection unreliable on DF v50. Re-enable
    # together with the location in locations.py and the check in checks.lua.
    # loc = multiworld.get_location("First Eggs Hatched", player)
    # loc.access_rule = lambda state: dynamic_rules.craftdwarf_workshop(state)

    # Catching a hostile beast needs a cage trap = a cage plus a mechanism (built
    # at the Mechanic's Workshop), so require both.
    loc = multiworld.get_location("Caged a Hostile Beast", player)
    if options.craftpermits == CraftingPermits.option_off:
        loc.access_rule = lambda state: dynamic_rules.wood_or_metal_or_glass(state) \
            and dynamic_rules.mechanic_workshop(state)
    else:
        loc.access_rule = lambda state: dynamic_rules.wood_or_metal_or_glass_cage(state) \
            and dynamic_rules.mechanic_mechanism(state)


    # ── Merchant's Shop gates ─────────────────────────────────────────────────
    # Shop slots require:
    #   1. Enough Merchant's Coffers for the tier (10 slots per coffer).
    #   2. The ability to mint coins - needs metal smelting; with craft permits
    #      also requires a Coins Permit so the player can actually produce currency.
    # Only set when the shop is enabled; otherwise these locations don't exist.
    if options.merchant_shop:
        for slot in range(1, SHOP_SLOTS + 1):
            tier = (slot - 1) // 10 + 1
            loc = multiworld.get_location(f"Shop Slot {slot}", player)
            if options.craftpermits == CraftingPermits.option_off:
                loc.access_rule = lambda state, n=tier: (
                    state.count("Merchant's Coffer", player) >= n
                    and dynamic_rules.metal(state)
                )
            else:
                loc.access_rule = lambda state, n=tier: (
                    state.count("Merchant's Coffer", player) >= n
                    and dynamic_rules.metal_coins(state)
                )

    # ── Sold an Artifact (endgame) ────────────────────────────────────────────
    # You can only sell an artifact you first obtained. Two in-logic paths:
    #   * Master Builder's Codex delivers a genuine, tradeable artifact door to the
    #     depot (items.lua: spawn_artifact_door), so it's a deterministic gate.
    #   * A strange mood needs population ~20 (proxied by >= 2 immigration waves)
    #     and the workshop matching the moody dwarf's highest moodable skill.
    # The skill isn't predictable, so the fully-sound mood gate would be EVERY
    # moodable workshop. We require only one: enough to raise the bar above
    # ungated, but not a guarantee the mood can be satisfied. The Codex is reliable.
    loc = multiworld.get_location("Sold an Artifact", player)
    loc.access_rule = lambda state: (
        state.has("Master Builder's Codex", player)
        or (
            state.count("Immigration Wave", player) >= 2
            and state.has_any(MOODABLE_WORKSHOP_BLUEPRINTS, player)
        )
    )

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

    # -- Skillsanity location requirements -------------------------------------
    if len(world.skill_locations) > 0:
        skillsanity_rules.set_skill_rules()

    # ── Goal condition ────────────────────────────────────────────────────────
    goal_location = multiworld.get_location("Goal", player)

    if options.goal == DwarfFortressGoal.option_slay_megabeast:
        # Megabeast requires armaments, a battle-ready military, and a populated fortress.
        goal_location.access_rule = lambda state: (
            state.has("Artifact Weapon", player)
            and state.count("Military Training", player) >= 10
            and state.count("Immigration Wave", player) >= 2
        )

        # War-effort checks need a barracks, which needs a metal armor stand AND
        # weapon rack - so require the ability to make metal (smelt ore + a forge).
        # "Training Completed" follows the same barracks-training path.
        multiworld.get_location("Barracks Established", player).access_rule = \
            lambda state: dynamic_rules.metal(state)
        multiworld.get_location("Training Completed", player).access_rule = \
            lambda state: dynamic_rules.metal(state)

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
    elif options.goal == DwarfFortressGoal.option_dwarfsanity:
        # requires all blueprints and Permits
        required_item_list = []
        for items in BLUEPRINT_ITEMS:
            required_item_list.append(items.name)
        for items in CRAFT_ITEMS:
            if items.name in {"Beds Permit", "Charcoal Permit", "Leather Permit", "Cloth Permit",
                "Alcohol Permit", "Prepared Meal Permit", "Barrel Permit", "Burial Container Permit"} and options.craftpermits == CraftingPermits.option_on:
                continue
            required_item_list.append(items.name)
        goal_location.access_rule = lambda state: state.has_all(required_item_list, player)
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
