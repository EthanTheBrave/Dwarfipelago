from typing import Any, ClassVar, List
from BaseClasses import Region, Location, Item, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from worlds.LauncherComponents import Component, icon_paths, components, Type, launch_subprocess

from .options import DwarfFortressOptions, DwarfFortressGoal
from .settings import DwarfFortressSettings
from .items import (
    ItemData, ITEM_TABLE, AP_ITEM_POOL, FILLER_ITEMS, TRAP_ITEMS,
    PROGRESSION_ITEMS, USEFUL_ITEMS
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
    active_location_names = []  # per-slot subset of location_name_to_id this slot creates
    web = DwarfFortressWebWorld()

    def generate_early(self) -> None:
        # location_name_to_id is the static, class-level DataPackage (every
        # location any options combo could produce). It is a ClassVar — AP builds
        # the shared package from it — so we must NOT mutate it per slot. Instead
        # we build an explicit list of the location NAMES this slot actually uses;
        # create_regions / create_items work off that list and look ids up from the
        # untouched ClassVar. Craft ids are computed deterministically, so every
        # name we select is guaranteed to already exist in location_name_to_id.
        self.dynamic_locations = []
        self.dynamic_locations_names = []
        #populates dynamic_locations and d_l_names
        generate_location_data(self)

        # Active set = the static non-craft locations (LOCATION_TABLE) plus the
        # craft subset this slot generated. Goal-based filtering then drops
        # locations that don't apply to the chosen goal:
        #   - wealth tiers are coffer progression locks (legendary_wealth only)
        #   - the noble ladder is charter progression locks (mountainhome only)
        # rules.py only references these for their matching goal, so dropping them
        # leaves no dangling rule lookups. (Mirrors the item removal in create_items.)
        active = set(LOCATION_TABLE.keys()) | set(self.dynamic_locations_names)
        WEALTH_TIER_LOCATIONS = {
            "Humble Beginnings (1,000)",
            "Growing Stronghold (10,000)",
            "Prosperous Fortress (50,000)",
            "Rich Citadel (100,000)",
            "Legendary Vault (500,000)",
        }
        NOBLE_LADDER_LOCATIONS = {
            "Baron Appointed",
            "Count Appointed",
            "Duke Appointed",
            "Monarch Takes Residence",
        }
        if self.options.goal != DwarfFortressGoal.option_legendary_wealth:
            active -= WEALTH_TIER_LOCATIONS
        if self.options.goal != DwarfFortressGoal.option_mountainhome:
            active -= NOBLE_LADDER_LOCATIONS
        # Keep the registry's deterministic order for reproducible fill.
        self.active_location_names = [n for n in _FULL_LOCATION_TABLE if n in active]


    # ── Generation lifecycle ──────────────────────────────────────────────────


    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        fortress = Region("Fortress", self.player, self.multiworld)

        menu.connect(fortress)

        for name in self.active_location_names:
            loc = DwarfFortressLocation(
                self.player, name, self.location_name_to_id[name], fortress
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
        location_count = len(self.active_location_names)
        trap_weight = self.options.trap_item_weight.value / 100.0

        # Separate required (progression) items from optional ones.
        # Progression items — all blueprints plus Artifact/Legendary items — must
        # always be included because rules.py gates locations behind them.  If they
        # were trimmed to fit the location count the accessibility check would fail.
        required: list[ItemData] = [
            d for d in AP_ITEM_POOL
            if d.classification == ItemClassification.progression
        ]
        optional: list[ItemData] = [
            d for d in AP_ITEM_POOL
            if d.classification != ItemClassification.progression
        ]

        for item_data in AP_ITEM_POOL:
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
        for item_data in AP_ITEM_POOL:
            if item_data.name == name:
                classification = item_data.classification
                break
        return DwarfFortressItem(name, classification, self.item_name_to_id[name], self.player)
