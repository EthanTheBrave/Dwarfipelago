"""Client-side AP-logic evaluator.

Runs the real rules.py against a stub state built from the items a player has
received, so the in-game panel can show which checks are logically reachable now
(e.g. no Smelter means the metal-craft checks stay locked), with no query to the
AP server or a separate tracker.

set_rules(world) only ever calls multiworld.get_location(name, player) and
assigns loc.access_rule, so a mock multiworld can record every (name,
access_rule) it touches; each rule is then evaluated against the stub state.
"""
from collections import Counter
from typing import Iterable, Optional

from .rules import set_rules
from .locations import LOCATION_TABLE
from .craftsanity_rules import DynamicCraftingLocationRules

PLAYER = 1


class StubState:
    """Stand-in for AP's CollectionState, backed by a Counter of received items.

    Counts matter: stackable items like "Immigration Wave" gate on count >= N.
    """

    def __init__(self, received: Counter):
        self.received = received

    def has(self, name, player, count=1):
        return self.received.get(name, 0) >= count

    def has_all(self, names, player):
        return all(self.received.get(name, 0) >= 1 for name in names)

    def has_any(self, names, player):
        return any(self.received.get(name, 0) >= 1 for name in names)

    def count(self, name, player):
        return self.received.get(name, 0)

    def can_reach_location(self, name, player):
        # No region graph here; the location's own access_rule is what we test.
        return True


class MockOption:
    """A single option value, supporting the comparisons rules.py performs on
    options: equality with a constant, truthiness, int(), and membership.
    """

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        other_value = other.value if isinstance(other, MockOption) else other
        return self.value == other_value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __bool__(self):
        return bool(self.value)

    def __int__(self):
        return int(self.value)

    def __hash__(self):
        if isinstance(self.value, list):
            return hash(tuple(self.value))
        return hash(self.value)

    def __iter__(self):
        if hasattr(self.value, "__iter__") and not isinstance(self.value, str):
            return iter(self.value)
        return iter([])

    def __contains__(self, item):
        if hasattr(self.value, "__contains__"):
            return item in self.value
        return False


class MockOptions:
    """Options bag where any option not supplied reads as 0 (unset / off)."""

    def __init__(self, values):
        object.__setattr__(self, "_values", values)

    def __getattr__(self, name):
        return MockOption(self._values.get(name, 0))


class MockLocation:
    """A location whose access_rule set_rules will overwrite."""

    def __init__(self, name):
        self.name = name
        self.player = PLAYER
        self.access_rule = lambda state: True


class MockMultiworld:
    """Records every location set_rules touches, keyed by name."""

    def __init__(self):
        self.locations = {}
        self.completion_condition = {}

    def get_location(self, name, player):
        self.locations.setdefault(name, MockLocation(name))
        return self.locations[name]


class MockWorld:
    def __init__(self, options, multiworld):
        self.player = PLAYER
        self.options = options
        self.multiworld = multiworld
        self.dynamic_locations = []
        self.skill_locations = []


# slot_data key -> option attribute that rules.py reads. The exclude_* options
# are left out on purpose: they only remove locations, they never change the
# access rule of a location that remains, so defaulting them to 0 stays exact.
SLOT_DATA_TO_OPTION = {
    "goal": "goal",
    "crafting_permits": "craftpermits",
    "craftsanity_enabled": "craftsanity",
    "craftsanity_materials": "craftsanity_materials",
    "skillsanity_enabled": "skillsanity",
}


def _options_from_slot_data(slot_data: Optional[dict]) -> MockOptions:
    values = {}
    if slot_data:
        for slot_key, option_name in SLOT_DATA_TO_OPTION.items():
            if slot_key in slot_data:
                values[option_name] = slot_data[slot_key]
    return MockOptions(values)


def _harvest_milestone_rules(slot_data: Optional[dict]) -> dict:
    """Return {location_name: access_rule} for every static location set_rules gates."""
    multiworld = MockMultiworld()
    world = MockWorld(_options_from_slot_data(slot_data), multiworld)
    set_rules(world)
    return {name: loc.access_rule for name, loc in multiworld.locations.items()}


def accessible_location_ids(
    received_item_names: Iterable[str],
    slot_data: Optional[dict] = None,
    restrict_ids: Optional[set] = None,
    dynamic_locations=None,
) -> dict:
    """Evaluate real AP logic for the current inventory.

    received_item_names: names of items the player has received.
    slot_data:           this slot's fill_slot_data, for option values.
    restrict_ids:        if set, report only ids in it (the seed's real locations).
    dynamic_locations:   craftsanity locations (with .name / .df_item /
                         .material_type / .ap_id) to gate alongside the milestones.

    Returns {"accessible": [ids], "locked": [ids], "errors": [messages]}. A rule
    that raises is reported under errors and treated as locked.
    """
    state = StubState(Counter(received_item_names))  # duplicates count for stackables
    craft_locations = list(dynamic_locations or [])

    accessible = set()
    locked = set()
    errors = []

    # Milestone (static) rules. Harvested with no craft locations, so a bad craft
    # rule can never break this pass.
    for name, access_rule in _harvest_milestone_rules(slot_data).items():
        location_id = LOCATION_TABLE.get(name)
        if location_id is None:
            continue
        try:
            reachable = access_rule(state)
        except Exception as error:
            locked.add(location_id)
            errors.append(f"{name}: {error!r}")
            continue
        (accessible if reachable else locked).add(location_id)

    # Craftsanity (dynamic) rules. Each craft is evaluated on its own so one bad
    # item/material only locks that craft rather than sinking the whole batch.
    if craft_locations:
        rules = DynamicCraftingLocationRules(
            MockWorld(_options_from_slot_data(slot_data), MockMultiworld())
        )
        for craft in craft_locations:
            location = MockLocation(craft.name)
            try:
                rules.df_location_rule(location, craft.df_item, craft.material_type)
                reachable = location.access_rule(state)
            except Exception as error:
                locked.add(craft.ap_id)
                errors.append(f"{craft.name}: {error!r}")
                continue
            (accessible if reachable else locked).add(craft.ap_id)

    if restrict_ids is not None:
        restrict_ids = set(restrict_ids)
        # Ids the seed has that no rule gated are unconditionally reachable.
        ungated = restrict_ids - accessible - locked
        accessible = (accessible | ungated) & restrict_ids
        locked = locked & restrict_ids

    return {
        "accessible": sorted(accessible),
        "locked": sorted(locked),
        "errors": errors,
    }
