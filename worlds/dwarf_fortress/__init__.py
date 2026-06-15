from typing import Any, ClassVar, List
from BaseClasses import Region, Location, Item, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from Options import OptionError
from worlds.LauncherComponents import Component, icon_paths, components, Type, launch_subprocess
from worlds.dwarf_fortress.skillsanity import Skillsanity

from .options import DwarfFortressOptions, DwarfFortressGoal, CraftingPermits, dwarf_fortress_option_groups
from .settings import DwarfFortressSettings
from .items import (
    ItemData, ITEM_TABLE, AP_ITEM_POOL, FILLER_ITEMS, TRAP_ITEMS,
    PROGRESSION_ITEMS, USEFUL_ITEMS, CRAFT_ITEMS
)
from .locations import (
    LocationData, LOCATION_TABLE, ALL_LOCATIONS, SHOP_LOCATIONS, SHOP_SLOTS,
    SHOP_PRICE_MIN, SHOP_PRICE_MAX,
)
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
    components.append(Component("Dwarf Fortress Client", func=run_client, component_type=Type.CLIENT, icon='DFAP Icon'))
    icon_paths['DFAP Icon'] = "ap:worlds.dwarf_fortress/icon.png"
except Exception as _client_err:
    import logging as _logging
    _logging.warning(f"[Dwarfipelago] Failed to register launcher components: {_client_err}")


class DwarfFortressWebWorld(WebWorld):
    theme = "dirt"
    option_groups = dwarf_fortress_option_groups
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
    active_location_names = []  # per-slot subset of location_name_to_id this slot creates
    skill_locations = []
    remove_skill_locations_names = []
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
        #populates dynamic_locations and names
        generate_location_data(self)

        # Decide which crafting-permit items this slot puts in the pool.
        # Both item_name_to_id and AP_ITEM_POOL are shared, class-level objects:
        # item_name_to_id IS the DataPackage — mutating it makes the generated
        # multidata's checksum disagree with a fresh load of the apworld, so the
        # server rejects the file ("checksum mismatch") — and AP_ITEM_POOL is
        # reused for every slot in the generation. So we never mutate either: we
        # work on a per-instance copy of the pool and always leave every craft
        # item in the DataPackage regardless of options. (Mirrors the same
        # rule already applied to location_name_to_id above.)
        self.ap_item_pool = list(AP_ITEM_POOL)
        craft_item_names = {i.name for i in CRAFT_ITEMS}

        if self.options.craftpermits == CraftingPermits.option_off or not self.options.craftsanity:
            # Permits disabled — no craft-permit items go into the pool at all.
            self.ap_item_pool = [d for d in self.ap_item_pool if d.name not in craft_item_names]
        elif self.options.craftpermits == CraftingPermits.option_on:
            # Start with a basic permit set; don't also place those in the pool.
            self.starting_inventory = ["Beds Permit", "Charcoal Permit", "Leather Permit",
                "Cloth Permit", "Alcohol Permit", "Prepared Meal Permit", "Barrel Permit"]
            self.ap_item_pool = [d for d in self.ap_item_pool
                                 if d.name not in self.starting_inventory]
        
        #Skillsanity
        skillsanity = Skillsanity(self)
        skillsanity.adjust_skill_locations()

        if self.options.craftpermits != CraftingPermits.option_off and len(CRAFT_ITEMS) > len(self.dynamic_locations) + len(self.skill_locations):
            raise OptionError(
                f"{self.player_name}: You do not have enough craftsanity or skillsanity locations enabled to use the permits feature."
                f" To increase this, add more crafting item locations, increase the maximum amount or lower the threshold."
                f" You need {len(CRAFT_ITEMS) - len(self.dynamic_locations)} more locations."
            )

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
        for skill_names in self.remove_skill_locations_names:
             active.remove(skill_names)
        # The shop is always on, so its 50 slots are always active (coffer-gated
        # in rules.py).
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
                item_data.name in {"Merchant's Coffer", "Baron's Charter",  "Count's Charter", "Duke's Charter",
                    "Monarch's Invitation", "Remains of the Great King"}:
                    required.remove(item_data)
            elif self.options.goal == DwarfFortressGoal.option_legendary_wealth and \
                item_data.name in {"Baron's Charter",  "Count's Charter", "Duke's Charter", "Monarch's Invitation",
                    "Military Training", "Artifact Weapon", "Artifact Armor", "Remains of the Great King"}:
                    required.remove(item_data)
            elif self.options.goal == DwarfFortressGoal.option_mountainhome and \
                item_data.name in {"Military Training","Artifact Armor", "Merchant's Coffer", "Remains of the Great King"}:
                    required.remove(item_data)
            elif self.options.goal == DwarfFortressGoal.option_population_boom and \
                item_data.name in {"Merchant's Coffer", "Baron's Charter",  "Count's Charter", "Duke's Charter",
                    "Monarch's Invitation", "Military Training", "Remains of the Great King"}:
                    required.remove(item_data)
            elif self.options.goal == DwarfFortressGoal.option_king_remains and \
                item_data.name in {"Merchant's Coffer", "Baron's Charter",  "Count's Charter", "Duke's Charter",
                    "Monarch's Invitation", "Military Training"}:
                    required.remove(item_data)
            elif self.options.goal == DwarfFortressGoal.option_king_remains and item_data.name == "Remains of the Great King":
                item_data.quantity = self.options.remains_great_king.value

        # The always-on shop is gated by Merchant's Coffer count, so the coffers
        # must always be in the pool -- even for goals whose loop above stripped
        # them. Re-add the (x5) coffer item if needed.
        coffer = next((d for d in self.ap_item_pool if d.name == "Merchant's Coffer"), None)
        if coffer is not None and coffer not in required:
            required.append(coffer)

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
        #    Filler is chosen by weight, so useful materials show up far more than
        #    flavor trinkets and the rare low-grade tools.
        filler_weights = [f.weight for f in FILLER_ITEMS]
        while len(item_pool) < location_count:
            if self.random.random() < trap_weight and TRAP_ITEMS:
                item_pool.append(self.create_item(self.random.choice(TRAP_ITEMS).name))
            else:
                choice = self.random.choices(FILLER_ITEMS, weights=filler_weights, k=1)[0]
                item_pool.append(self.create_item(choice.name))

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
        skill_location_data = {}
        for locations in self.skill_locations:
            skill_location_data[locations.ap_id] = {"location_name": locations.name, "threshold": locations.threshold, "skill": locations.df_item}
        # Shop slots: per-slot random coin price + coffer tier, keyed by location id
        # (as a string for JSON). The client scouts these ids to learn each slot's
        # item/recipient and writes them, with the price, for the in-game shop tab.
        shop_data = {}
        lo, hi = SHOP_PRICE_MIN, SHOP_PRICE_MAX
        for slot, loc in enumerate(SHOP_LOCATIONS, start=1):
            shop_data[str(loc.ap_id)] = {
                "slot": slot,
                "tier": (slot - 1) // 10 + 1,
                "price": self.random.randint(lo, hi),
            }
        return {
            "goal": self.options.goal.value,
            "wealth_goal_amount": self.options.wealth_goal_amount.value,
            "population_goal_amount": self.options.population_goal_amount.value,
            "remains_great_king": self.options.remains_great_king.value,
            "deathlink": self.options.deathlink.value,
            "deathlink_threshold": self.options.deathlink_threshold.value,
            "seed": self.random.randint(12212, 15245354),
            "player_name": self.player_name,
            "crafting_locations": crafting_location_data,
            "craftsanity_max_amount": self.options.craftsanity_max_amount.value,
            "craftsanity_threshold": self.options.craftsanity_threshold.value,
            "craftsanity_enabled": self.options.craftsanity.value,
            "craftsanity_materials": self.options.craftsanity_enable_materials.value,
            "crafting_permits": self.options.craftpermits.value,
            "skillsanity_enabled": self.options.skillsanity.value,
            "skillsanity_max_level": self.options.skillsanity_max_level.value,
            "skillsanity_behaviour": self.options.skillsanity_behaviour.value,
            "skillsanity_locations": skill_location_data,
            "deathlink_percentage": self.options.deathlink_percentage.value,
            "energy_link": self.options.energy_link.value,
            "shop": shop_data,
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
