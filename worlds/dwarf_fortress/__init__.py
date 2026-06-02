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
from .craftsanity import generate_location_data
from . import rules

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
    location_name_to_id = LOCATION_TABLE

    dynamic_locations = []
    dynamic_locations_names = []
    web = DwarfFortressWebWorld()

    def generate_early(self) -> None:
        # Make per-instance copies of the class-level shared containers so that
        # multiple DF players in the same multiworld don't corrupt each other's state.
        self.location_name_to_id = dict(LOCATION_TABLE)
        self.dynamic_locations = []
        self.dynamic_locations_names = []
        #populates dynamic_locations and d_l_names
        generate_location_data(self)
        ## FOR printing, uncomment below and set your yaml to the max! (enable all items, max location, lowest threshold, all materials)
        #generate_location_data_PRINT_ONLY(self)
        # CHANGED — NEEDS REVIEW:
        # Material-specific location names (e.g. "Crafting Bone Gauntlets Check 1") are
        # not pre-registered in crafting_locations.py (only the generic
        # "Crafting Gauntlets Check 1" is). Without this loop those names never enter
        # location_name_to_id, so create_regions never creates them in the multiworld,
        # and set_dynamic_rules raises a KeyError when it tries to look them up.
        # This is a workaround — ideally crafting_locations.py should be regenerated
        # to include all material-specific variants, or IDs should be assigned here.
        for loc in self.dynamic_locations:
            if loc.name not in self.location_name_to_id:
                self.location_name_to_id[loc.name] = loc.ap_id
        remove_list = []
        for location in self.location_name_to_id:
            if "Crafting" in location and location not in self.dynamic_locations_names:
                remove_list.append(location)
        for location in remove_list:
            del self.location_name_to_id[location] #remove unused locations for caculations and creations
        ## PRINT LOCATIONS
        # for locations in self.dynamic_locations:
        #     print(f'LocationData("{locations.name}", {locations.ap_id}, "Fortress", False, "{locations.material_type}", "{locations.df_item}", {locations.threshold}),')
    

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

        item_pool: list[DwarfFortressItem] = []

        # 1. Always add every progression item.
        for item_data in required:
            for _ in range(item_data.quantity):
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
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def create_item(self, name: str) -> DwarfFortressItem:
        classification = ItemClassification.filler
        for item_data in AP_ITEM_POOL:
            if item_data.name == name:
                classification = item_data.classification
                break
        return DwarfFortressItem(name, classification, self.item_name_to_id[name], self.player)
