from typing import Any, ClassVar, List
from BaseClasses import Region, Location, Item, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from Options import OptionError
from worlds.LauncherComponents import Component, icon_paths, components, Type, launch_subprocess

from .options import DwarfFortressOptions, DwarfFortressGoal, CraftingItems
from .settings import DwarfFortressSettings
from .items import (
    ItemData, ITEM_TABLE, AP_ITEM_POOL, FILLER_ITEMS, TRAP_ITEMS,
    PROGRESSION_ITEMS, USEFUL_ITEMS, CRAFT_ITEMS
)
from .locations import LocationData, LOCATION_TABLE, ALL_LOCATIONS
from .craftsanity import (
    generate_location_data,
    build_craft_location_table,
)
from . import rules

# The complete AP DataPackage: the static (non-craft) locations plus every
# possible craft check, computed deterministically. This is the single source of
# truth for location ids — the per-slot generation in craftsanity.loop_locations
# derives the same ids from the same formula, so they can never drift.
_FULL_LOCATION_TABLE: dict[str, int] = {**LOCATION_TABLE, **build_craft_location_table()}

# Register the Archipelago launcher buttons (Dwarf Fortress + Dwarf Fortress Client).
# Imported here so the components are registered whenever this world is loaded,
# regardless of which AP version's discovery mechanism is in use.
# Wrapped in a bare except so a missing display / headless server never breaks
# world generation.
try:
    def run_client():
        from .DwarfFortressClient import main  # lazy import
        launch_subprocess(main)
    components.append(Component("Dwarf Fortress Client", func=run_client, component_type=Type.CLIENT,))
except Exception as _client_err:
    import logging as _logging
    _logging.warning(f"[Dwarfipelago] Failed to register launcher components: {_client_err}")


class DwarfFortressWebWorld(WebWorld):
    theme = "dirt"
    tutorials = [
        Tutorial(
            tutorial_name="Setup Guide",
            description="How to install and run Dwarfipelago",
            language="English",
            file_name="setup_en.md",
            link="setup/en",
            authors=["Dwarfipelago Contributors"],
        )
    ]


class DwarfFortressItem(Item):
    game = "Dwarf Fortress"


class DwarfFortressLocation(Location):
    game = "Dwarf Fortress"


class DwarfFortressWorld(World):
    """
    Dwarf Fortress — build a fortress, fulfill economic milestones, and
    send items to your fellow Archipelago players. Beware the traps they
    send in return.
    """

    game = "Dwarf Fortress"
    options_dataclass = DwarfFortressOptions
    options: DwarfFortressOptions

    settings_key = "dwarf_fortress_options"
    settings: ClassVar[DwarfFortressSettings]

    item_name_to_id = ITEM_TABLE
    location_name_to_id = _FULL_LOCATION_TABLE

    dynamic_locations = []
    dynamic_locations_names = []
    ap_item_pool = AP_ITEM_POOL
    starting_inventory = []
    web = DwarfFortressWebWorld()

    def generate_early(self) -> None:
        # Make per-instance copies of the class-level shared containers so that
        # multiple DF players in the same multiworld don't corrupt each other's state.
        self.location_name_to_id = dict(_FULL_LOCATION_TABLE)
        self.ap_item_pool = AP_ITEM_POOL
        self.dynamic_locations = []
        self.dynamic_locations_names = []
        #populates dynamic_locations and names
        generate_location_data(self)

        # Craft ids are now computed deterministically (craftsanity.craft_location_id),
        # so the per-slot generation and the DataPackage registry always agree —
        # no override needed. We only need to PRUNE the craft locations this slot
        # didn't generate (the registry contains every possible check), otherwise
        # create_regions would create checks the player can never reach.
        generated = set(self.dynamic_locations_names)
        remove_list = [
            name for name in self.location_name_to_id
            if "Crafting" in name and name not in generated
        ]
        for location in remove_list:
            del self.location_name_to_id[location] #remove unused locations for caculations and creations

        # remove the crafting items from the pool depending on the options
        if self.options.craftitems == CraftingItems.option_off or not self.options.craftsanity:
            remove_list = []
            remove_ap_pool = []
            for item in self.item_name_to_id:
                match = [i for i in CRAFT_ITEMS if i.name == item]
                if len(match) > 0:
                    remove_list.append(item)
                    remove_ap_pool.append(match[0])
            for item in remove_list:
                del self.item_name_to_id[item]
            for item in remove_ap_pool:
                self.ap_item_pool.remove(item)
        elif self.options.craftitems == CraftingItems.option_on:
            self.starting_inventory = ["Crafting Beds", "Crafting Charcoal", "Crafting Leather",
                "Crafting Cloth", "Crafting Alcohol", "Crafting Prepared Meal"
            ]
            remove_ap_pool = []
            for item in self.item_name_to_id:
                if item in self.starting_inventory:
                    match = [i for i in CRAFT_ITEMS if i.name == item]
                    remove_ap_pool.append(match[0])
            for item in remove_ap_pool:
                self.ap_item_pool.remove(item)
        
        if len(CRAFT_ITEMS) > len(self.dynamic_locations):
            raise OptionError(
                f"{self.player_name}: You do not have enough crafting locations enabled to use the crafting items feature."
                f" To increase this, add more crafting item locations, increase the maximum amount or lower the threshold."
                f" You need {len(CRAFT_ITEMS) - len(self.dynamic_locations)} more locations."
            )
        # Goal-based location filtering — mirror of the item removal in
        # create_items(). The wealth-tier checks are coffer progression locks:
        # they are only gated (and the Merchant's Coffer items only exist) when
        # the goal is legendary_wealth. For every other goal, remove these
        # locations entirely so they don't appear as ungated bonus checks.
        # rules.py only applies WEALTH_COFFER_RULES for the wealth goal, so it
        # never looks these up after they're removed here.
        WEALTH_TIER_LOCATIONS = [
            "Humble Beginnings (1,000)",
            "Growing Stronghold (10,000)",
            "Prosperous Fortress (50,000)",
            "Rich Citadel (100,000)",
            "Legendary Vault (500,000)",
        ]
        if self.options.goal != DwarfFortressGoal.option_legendary_wealth:
            for loc_name in WEALTH_TIER_LOCATIONS:
                self.location_name_to_id.pop(loc_name, None)

        # The noble-ladder checks are charter progression locks: each is gated in
        # checks.lua behind its charter item, and those charters only exist in the
        # pool for the mountainhome goal. For every other goal they'd be dead,
        # uncompletable locations, so remove them. Mayor Elected stays (no charter,
        # happens in any fortress) and the fortress titles stay (gated by
        # Immigration Waves, which are in every goal's pool).
        NOBLE_LADDER_LOCATIONS = [
            "Baron Appointed",
            "Count Appointed",
            "Duke Appointed",
            "Monarch Takes Residence",
        ]
        if self.options.goal != DwarfFortressGoal.option_mountainhome:
            for loc_name in NOBLE_LADDER_LOCATIONS:
                self.location_name_to_id.pop(loc_name, None)


    # ── Generation lifecycle ──────────────────────────────────────────────────


    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        fortress = Region("Fortress", self.player, self.multiworld)

        menu.connect(fortress)

        for loc_data in self.location_name_to_id:
            loc = DwarfFortressLocation(
                self.player, loc_data, self.location_name_to_id[loc_data], fortress
            )
            fortress.locations.append(loc)

        # Goal location (no AP ID — event location)
        goal_loc = DwarfFortressLocation(self.player, "Goal", None, fortress)
        goal_loc.place_locked_item(
            DwarfFortressItem("Victory", ItemClassification.progression, None, self.player)
        )
        fortress.locations.append(goal_loc)

        self.multiworld.regions += [menu, fortress]

    def create_items(self) -> None:
        location_count = len(self.location_name_to_id)
        trap_weight = self.options.trap_item_weight.value / 100.0

        #precollect starting items
        for item_name in self.starting_inventory:
            self.multiworld.push_precollected(self.create_item(item_name))

        # Separate required (progression) items from optional ones.
        # Progression items — all blueprints plus Artifact/Legendary items — must
        # always be included because rules.py gates locations behind them.  If they
        # were trimmed to fit the location count the accessibility check would fail.
        required: list[ItemData] = [
            d for d in self.ap_item_pool
            if d.classification == ItemClassification.progression
        ]
        optional: list[ItemData] = [
            d for d in self.ap_item_pool
            if d.classification != ItemClassification.progression
        ]

        for item_data in self.ap_item_pool:
            if self.options.goal == DwarfFortressGoal.option_slay_megabeast and \
                item_data.name in {"Merchant's Coffer", "Baron's Charter",  "Count's Charter", "Duke's Charter", "Monarch's Invitation"}:
                    required.remove(item_data)
            elif self.options.goal == DwarfFortressGoal.option_legendary_wealth and \
                item_data.name in {"Baron's Charter",  "Count's Charter", "Duke's Charter", "Monarch's Invitation", "Military Training", "Artifact Weapon", "Artifact Armor"}:
                    required.remove(item_data)
            elif self.options.goal == DwarfFortressGoal.option_mountainhome and \
                item_data.name in {"Military Training","Artifact Armor", "Merchant's Coffer"}:
                    required.remove(item_data)
            elif self.options.goal == DwarfFortressGoal.option_population_boom and \
                item_data.name in {"Merchant's Coffer", "Baron's Charter",  "Count's Charter", "Duke's Charter", "Monarch's Invitation", "Military Training"}:
                    required.remove(item_data)

        item_pool: list[DwarfFortressItem] = []

        # Items granted via start_inventory are auto-precollected by AP core.
        # We must NOT also place them in the pool, or a duplicate ends up at a
        # location and gets sent when that location is checked (e.g. starting
        # with the Stoneworker's blueprint but still receiving it later).
        start_inv = dict(self.options.start_inventory.value)

        # 1. Add every progression item, minus copies already in start_inventory.
        for item_data in required:
            qty = item_data.quantity
            granted = start_inv.get(item_data.name, 0)
            if granted > 0:
                skip = min(granted, qty)
                qty -= skip
                start_inv[item_data.name] = granted - skip
            for _ in range(qty):
                item_pool.append(self.create_item(item_data.name))

        # 2. Fill remaining slots from optional items (shuffled for variety).
        remaining = location_count - len(item_pool)
        shuffled_optional = list(optional)
        self.random.shuffle(shuffled_optional)
        for item_data in shuffled_optional[:max(remaining, 0)]:
            item_pool.append(self.create_item(item_data.name))

        # 3. Pad with filler/traps if still under location count
        #    (happens when progression items alone outnumber locations).
        while len(item_pool) < location_count:
            if self.random.random() < trap_weight and TRAP_ITEMS:
                item_pool.append(self.create_item(self.random.choice(TRAP_ITEMS).name))
            else:
                item_pool.append(self.create_item(self.random.choice(FILLER_ITEMS).name))

        self.multiworld.itempool += item_pool

    def set_rules(self) -> None:
        rules.set_rules(self)

    def generate_output(self, output_directory: str) -> None:
        # No external patch file needed — the client reads the AP server directly.
        pass

    def get_filler_item_name(self) -> str:
        return self.random.choice(FILLER_ITEMS).name

    def fill_slot_data(self) -> dict[str, Any]:
        crafting_location_data = {}
        for locations in self.dynamic_locations:
            crafting_location_data[locations.ap_id] = {"item": locations.df_item, "material": locations.material_type, "threshold": locations.threshold, "location_name": locations.name}
        return {
            "goal": self.options.goal.value,
            "wealth_goal_amount": self.options.wealth_goal_amount.value,
            "population_goal_amount": self.options.population_goal_amount.value,
            "deathlink_threshold": self.options.deathlink_threshold.value,
            "seed": self.random.randint(12212, 15245354),
            "player_name": self.player_name,
            "crafting_locations": crafting_location_data,
            "craftsanity_max_amount": self.options.craftsanity_max_amount.value,
            "craftsanity_threshold": self.options.craftsanity_threshold.value,
            "craftsanity_enabled": self.options.craftsanity.value,
            "craftsanity_materials": self.options.craftsanity_enable_materials.value,
            "deathlink_percentage": self.options.deathlink_percentage.value,
            "version": f"{self.world_version.as_simple_string()}",
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def create_item(self, name: str) -> DwarfFortressItem:
        classification = ItemClassification.filler
        for item_data in self.ap_item_pool:
            if item_data.name == name:
                classification = item_data.classification
                break
        return DwarfFortressItem(name, classification, self.item_name_to_id[name], self.player)
