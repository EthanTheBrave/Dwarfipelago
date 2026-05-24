from typing import Any, ClassVar
from BaseClasses import Region, Location, Item, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld

from .options import DwarfFortressOptions, DwarfFortressGoal
from .settings import DwarfFortressSettings
from .items import (
    ItemData, ITEM_TABLE, AP_ITEM_POOL, FILLER_ITEMS, TRAP_ITEMS,
    PROGRESSION_ITEMS, USEFUL_ITEMS
)
from .locations import LocationData, LOCATION_TABLE, ALL_LOCATIONS
from . import rules

# Register the Archipelago launcher buttons (Dwarf Fortress + Dwarf Fortress Client).
# Imported here so the components are registered whenever this world is loaded,
# regardless of which AP version's discovery mechanism is in use.
# Wrapped in a bare except so a missing display / headless server never breaks
# world generation.
try:
    from . import client as _  # noqa: F401
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

    web = DwarfFortressWebWorld()

    # ── Generation lifecycle ──────────────────────────────────────────────────

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        fortress = Region("Fortress", self.player, self.multiworld)

        menu.connect(fortress)

        for loc_data in ALL_LOCATIONS:
            loc = DwarfFortressLocation(
                self.player, loc_data.name, loc_data.ap_id, fortress
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
        item_pool: list[DwarfFortressItem] = []

        trap_weight = self.options.trap_item_weight.value / 100.0

        for item_data in AP_ITEM_POOL:
            for _ in range(item_data.quantity):
                item_pool.append(self._make_item(item_data.name))

        # Pad pool to match location count with filler/traps
        location_count = len(ALL_LOCATIONS)
        while len(item_pool) < location_count:
            if self.random.random() < trap_weight and TRAP_ITEMS:
                trap = self.random.choice(TRAP_ITEMS)
                item_pool.append(self._make_item(trap.name))
            else:
                filler = self.random.choice(FILLER_ITEMS)
                item_pool.append(self._make_item(filler.name))

        # Trim if we somehow overshoot
        item_pool = item_pool[:location_count]

        self.multiworld.itempool += item_pool

    def set_rules(self) -> None:
        rules.set_rules(self)

    def generate_output(self, output_directory: str) -> None:
        # No external patch file needed — the client reads the AP server directly.
        pass

    def get_filler_item_name(self) -> str:
        return self.random.choice(FILLER_ITEMS).name

    def fill_slot_data(self) -> dict[str, Any]:
        return {
            "goal": self.options.goal.value,
            "wealth_goal_amount": self.options.wealth_goal_amount.value,
            "population_goal_amount": self.options.population_goal_amount.value,
            "deathlink_threshold": self.options.deathlink_threshold.value,
        }

    # ── Completion condition ──────────────────────────────────────────────────

    def set_completion_condition(self) -> None:
        self.multiworld.completion_condition[self.player] = (
            lambda state: state.has("Victory", self.player)
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_item(self, name: str) -> DwarfFortressItem:
        classification = ItemClassification.filler
        for item_data in AP_ITEM_POOL:
            if item_data.name == name:
                classification = item_data.classification
                break
        return DwarfFortressItem(name, classification, self.item_name_to_id[name], self.player)
