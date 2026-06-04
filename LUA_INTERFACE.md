# Dwarfipelago — Lua ↔ Python Interface Reference

This document describes how the Python AP client (`DwarfFortressClient.py`) communicates
with the Lua mod running inside DFHack. It is intended as a quick reference for Python-side
development — you should not need to read through the Lua source to use this.

---

## How it works

The Lua mod runs inside DFHack and has no direct network access. All communication
happens through **DFHack's world-level persistent storage** — a key/value store that
survives save/reload cycles.

- **Lua writes** event queues and state flags as JSON strings.
- **Python reads** them via `DFHackConnection.run_command("lua", ...)` RPC calls.
- Queues follow a **pop pattern**: read the value, then immediately write `"[]"` back to clear it.
- State flags follow a **peek pattern**: read without clearing.

The Python client polls DFHack every `_poll_interval` seconds (default 5s). All
persistent storage operations require an active loaded world — the client already
guards against this with the `_world_loaded` flag.

---

## Persistent Storage Keys

All keys are namespaced under `dwarfipelago/`.

### Event Queues (pop to consume)

| Key | Format | Written by | Description |
|-----|--------|------------|-------------|
| `dwarfipelago/pending_checks` | JSON `int[]` | Lua | AP location IDs ready to send to the server |
| `dwarfipelago/pending_item_created` | JSON `ItemEvent[]` | Lua | Items created since last poll (see schema below) |
| `dwarfipelago/pending_item_stockpiled` | JSON `ItemEvent[]` | Lua | Items placed into a stockpile since last poll |

### State Flags (peek, do not clear)

| Key | Format | Written by | Description |
|-----|--------|------------|-------------|
| `dwarfipelago/checked_locations` | JSON `{id: true}` | Lua | Location IDs already checked (dedup set) |
| `dwarfipelago/goal_complete` | `"1"` or `""` | Lua | Set when the fortress has met its win condition |
| `dwarfipelago/death_count` | Integer string | Lua | Cumulative citizen deaths |
| `dwarfipelago/deathlinks_sent` | Integer string | Lua | DeathLink bounces Python has already sent |
| `dwarfipelago/pending_recv` | Integer string | Lua | Incoming DeathLinks not yet applied in-game |
| `dwarfipelago/prod/<flag>` | `"1"` or absent | Lua | Set when a first-production milestone fires |
| `dwarfipelago/trade/<flag>` | `"1"` or absent | Lua | Set when a trade/caravan milestone fires |
| `dwarfipelago/craft_count/<flag>` | Integer string | Lua | Cumulative crafts completed for that flag |
| `dwarfipelago/blueprint/<name>` | `"1"` or absent | Lua | Set when a blueprint item has been received |
| `dwarfipelago/unlock/wealth_coffers` | Integer string | Lua | How many Merchant's Coffers received (0–5); gates wealth tier checks |
| `dwarfipelago/unlock/immigration_waves` | Integer string | Lua | How many Immigration Waves received (0–5); gates title/population checks |
| `dwarfipelago/unlock/baron_charter` | `"1"` or absent | Lua | Set when Baron's Charter received; gates Baron Appointed check |
| `dwarfipelago/unlock/count_charter` | `"1"` or absent | Lua | Set when Count's Charter received; gates Count Appointed check |
| `dwarfipelago/unlock/duke_charter` | `"1"` or absent | Lua | Set when Duke's Charter received; gates Duke Appointed check |
| `dwarfipelago/unlock/monarch_invitation` | `"1"` or absent | Lua | Set when Monarch's Invitation received; gates Monarch Takes Residence check |
| `dwarfipelago/unlock/military_training` | Integer string | Lua | How many Military Training items received (0–3); used by slay_megabeast goal |
| `dwarfipelago/unlock/artifact_weapon` | `"1"` or absent | Lua | Set when Artifact Weapon received; gates slay_megabeast and mountainhome goals |
| `dwarfipelago/unlock/artifact_armor` | `"1"` or absent | Lua | Set when Artifact Armor received; gates population_boom prestige requirement |
| `dwarfipelago/unlock/master_builders_codex` | `"1"` or absent | Lua | Set when Master Builder's Codex received; gates legendary_wealth, mountainhome, and population_boom goals |
| `dwarfipelago/depot_built` | `"1"` or absent | Lua | Set once the starting trade depot has been placed or adopted |
| `dwarfipelago/megabeast/target_id` | Integer string | Lua | Unit ID of the AP-summoned megabeast; prevents natural megabeast kills counting as goal completion |

### Config (written by Python, read by Lua)

| Key | Format | Written by | Description |
|-----|--------|------------|-------------|
| `dwarfipelago/goal` | `"0"`–`"3"` | Python | Goal type from slot data |
| `dwarfipelago/wealth_goal` | Integer string | Python | Wealth target for legendary_wealth goal |
| `dwarfipelago/pop_goal` | Integer string | Python | Population target for population_boom goal |
| `dwarfipelago/deathlink_threshold` | Integer string | Python | Dwarves (or % of pop) per DeathLink send/receive; option max is 50 |
| `dwarfipelago/deathlink_percentage` | `"0"` or `"1"` | Python | When `"1"`, threshold is treated as % of current population instead of a flat count |
| `dwarfipelago/seed` | Integer string | Python | World identity — used to scope AP storage keys and detect wrong-world loads |
| `dwarfipelago/received_index` | Integer string | Python | Count of received AP items already applied in-game; restored on reconnect so items aren't re-delivered (and counter-based progression items aren't double-counted) |
| `dwarfipelago/version` | Version string | Lua | Mod version recorded on `start()` |
| `dwarfipelago/craftsanity_enabled` | `"0"`, `"1"`, or `"2"` | Python | Craftsanity mode: 0=off, 1=on (crafted), 2=storage |
| `dwarfipelago/craftsanity_materials` | `"0"` or `"1"` | Python | When `"1"`, craft counts are split by material type (e.g. `Barrel_Wood` vs `Barrel_Metal`) |

---

## Data Schemas

### ItemEvent
Produced by the `onItemCreated` eventful hook and by `StoreItemInStockpile` job detection inside `onJobCompleted`.

```json
{
  "id":       12345,
  "type":     "WEAPON",
  "material": "inorganic/IRON",
  "quality":  3,
  "artifact": false,

  // stockpile events only:
  "stockpile_name":   "Weapon Pile",
  "stockpile_number": 2
}
```

`quality` values: `0`=normal, `1`=well-crafted, `2`=finely, `3`=superior, `4`=exceptional, `5`=masterwork

`type` is the `df.item_type` enum name: `WEAPON`, `ARMOR`, `FOOD`, `DRINK`, `FURNITURE`, `TOOL`, `GEM`, `CLOTH`, `CRAFTS`, etc.

`material` is the `matinfo:toString()` format: `"inorganic/IRON"`, `"plant/OAK"`, `"creature/DWARF/SKIN"`, etc.

Skipped types (never queued): `CORPSE`, `CORPSEPIECE`, `REMAINS`, `VERMIN`, `PLANT`, `PLANT_GROWTH`, `FISH_RAW`, `BODY_PARTS`

Queue is capped at 500 entries — if Python falls behind, oldest events are dropped.

### Craft Counts
Lua increments a counter in `dwarfipelago/craft_count/<flag>` each time a matching
job completes. Python polls these counters and is responsible for deciding when a
threshold is met and sending the location check to the AP server.

Read a count with `dfhack.persistent.getWorldDataString("dwarfipelago/craft_count/<flag>")` —
returns an integer string.

Initialized by Python to create the persistent storage for Lua to count the crafts to.
Example:

| Key | Description |
|-----|-------------|
| `dwarfipelago/craft_count/Barrel_Metal` | Total Metal Barrels crafted/stored (when `craftsanity_materials` is `"1"`) |
| `dwarfipelago/craft_count/Barrel_Wood` | Total Wooden Barrels crafted/stored (when `craftsanity_materials` is `"1"`) |
| `dwarfipelago/craft_count/Barrel` | Total Barrels of any material (when `craftsanity_materials` is `"0"`) |
| `dwarfipelago/craft_count/Glass` | Total Glass items (Glass has only one material type, so always stored without suffix) |


#### How a completed job becomes a flag

`checks.job_to_craft_flag(job)` (in `checks.lua`) maps a finished job to the
craft-count flag it should increment. The authoritative mapping lives in
`checks.lua` and is built from these tables — refer to the source rather than
duplicating the full list here, as it spans ~100 item types:

- **`JOB_TO_CRAFT_FLAG`** (`cmap` calls) — maps a `df.job_type` directly to a
  flag, e.g. `ConstructDoor → "door"`, `MakeCage → "cage"`,
  `ConstructBlocks → "blocks"`, `MakeCrafts → "crafts"`,
  `SmeltOre → "metal_bars"`, `MakeRawGlass → "glass"`.
- **Subtype dispatch** — some jobs resolve to a flag via the item's
  `item_subtype` using the `TOOL_SUBTYPE_FLAG`, `TRAP_SUBTYPE_FLAG`,
  `SHIELD_SUBTYPE_FLAG`, `WEAPON_SUBTYPE_FLAG`, `HELM_SUBTYPE_FLAG`,
  `GOBLET_SUBTYPE_FLAG`, `REACTION_SUBTYPE_FLAG`, `UARMOR_SUBTYPE_FLAG`,
  `GARMOR_SUBTYPE_FLAG`, and `LARMOR_SUBTYPE_FLAG` tables. For example a
  `MakeWeapon` job resolves to `"battle_axe"`, `"short_sword"`, etc. by subtype.
- **Material dispatch** — for `MakeCrafts`, `CarveBone`, `CarveStatue`, and
  `CarveFurniture` (the `NEEDS_MAT_CHECK` set), the flag comes from the job's
  primary material: inorganic-metal → `metal`, other inorganic → `stone`,
  plant → `wood`, creature → `bone`.

> **Note:** the flag strings produced here must match the storage-key suffixes
> the Python client initializes in `init_crafting_locations` (derived from each
> AP location's `item`/`material`, lowercased with spaces → underscores). If a
> craft count never increments, a flag/key-name mismatch between `checks.lua`
> and the AP location data is the first thing to check.

---

## Python Patterns

### Pop a queue (read + clear atomically)

The existing `pop_pending_checks` in `DwarfFortressClient.py` is the reference
implementation — follow its exact pattern for `pending_item_created` and
`pending_item_stockpiled`. The inline Lua must read and clear in a single call
so no events fall through between poll cycles.

Keys to implement methods for:
- `dwarfipelago/pending_item_created` → `pop_item_created_events() -> list[dict]`
- `dwarfipelago/pending_item_stockpiled` → `pop_stockpile_events() -> list[dict]`

Call both inside the poll loop alongside `_process_new_checks()`.

### Peek at any key (read without clearing)

Use `run_command("lua", ...)` with `dfhack.persistent.getWorldDataString` and
`print()` to read a key without touching it. Useful for debugging — return the
stripped output string.

### Write config to Lua

JSON sent through the inline Lua string must have its double-quotes escaped
before embedding. Look at how `_sync_slot_data` writes the goal/wealth/pop
values — any JSON config follows the same approach.

---

## Lua Module Reference

Modules live under `mods/dwarfipelago/scripts_modinstalled/internal/dwarfipelago/`.
Load them from Python via `reqscript("internal/dwarfipelago/<module>")`.

### `checks`

| Symbol | Type | Description |
|--------|------|-------------|
| `checks` | table | List of all static AP location check definitions |
| `production_flag(flag)` | fn → bool | True if a first-production flag has fired |
| `set_production_flag(flag)` | fn | Mark a first-production flag |
| `trade_flag(flag)` | fn → bool | True if a trade/caravan flag has fired |
| `set_trade_flag(flag)` | fn | Mark a trade flag |
| `job_to_production_flag(job)` | fn → string\|nil | Maps a completed job to its first-production flag |
| `job_to_craft_flag(job)` | fn → string\|nil | Maps a completed job to its craft-count flag |
| `increment_craft_count(flag)` | fn → int | Increment and persist a craft count, returns new total |
| `get_craft_count(flag)` | fn → int | Read current craft count for a flag |
| `fortress_wealth()` | fn → int | Current total fortress wealth (items + buildings + stocks) |
| `treasury_wealth()` | fn → int | Combined value of minted coins + cut gems in stocks (used by the legendary_wealth goal and wealth-tier checks) |

### `state`

| Symbol | Type | Description |
|--------|------|-------------|
| `is_enabled()` | fn → bool | Whether the mod is active |
| `mark_location_checked(id)` | fn → bool | Mark a location as checked; returns true if newly checked |
| `is_location_checked(id)` | fn → bool | Check if a location ID has already been checked |
| `increment_death_count()` | fn → int | Increment citizen death counter |
| `get_death_count()` | fn → int | Read citizen death counter |
| `get_deathlinks_sent()` | fn → int | Read DeathLinks-sent counter |
| `get_pending_recv()` | fn → int | Read pending incoming DeathLinks |
| `is_goal_complete()` | fn → bool | True if fortress has won |
| `mark_goal_complete()` | fn → bool | Set goal complete; returns true if first time |
| `dump()` | fn | Print full state summary to DFHack console |
| `reset()` | fn | Wipe all persistent state (use with care) |

### `log`

Levelled logging that writes to a file **and** mirrors to the DFHack console.
The log file lives next to the DF executable: `<Dwarf Fortress>/dwarfipelago.log`
(auto-rotated at 1 MB, keeping one `.old` backup). The exact path is printed to
the console when the mod starts.

| Symbol | Type | Description |
|--------|------|-------------|
| `info(msg)` | fn | Log at INFO; mirrors to console via `print` |
| `warn(msg)` | fn | Log at WARN; mirrors to console via `printerr` |
| `error(msg)` | fn | Log at ERROR; mirrors to console via `printerr` |
| `path()` | fn → string | Absolute path to the active log file |

---

## In-Game Panel (`dwarfipelago-panel.lua`)

The in-game status and control panel lives in:
```
mods/dwarfipelago/scripts_modinstalled/dwarfipelago-panel.lua
```

It is a DFHack overlay widget + ZScreen popup. Open it three ways:
- Click the `[AP]` button in the top-left corner of the fortress screen
- Run `dwarfipelago panel` from the DFHack console
- Run `dwarfipelago-panel` directly from the DFHack console

### Adding a status field

Status fields are `widgets.Label` views inside `DwarfipelagoPanel:init()`. Each one has a `frame = {t=N, l=0}` where `t` is the row offset inside the window (0-indexed from the top of the window's content area).

Read plain persistent keys with the local `ps()` helper:
```lua
local my_value = ps("some/key", "default")
```

Read the enabled flag specifically via `state.is_enabled()` (not `ps()`) because it is stored as a JSON object, not a plain string.

Example — adding a new status row at `t=3` (shift existing rows down by 1 to make room):
```lua
widgets.Label{
    frame = {t=3, l=0},
    text  = {"My label: ", ps("my/key", "unknown")},
},
```

Color a value with the `yn()` helper (for boolean YES/no display) or inline pen:
```lua
{text="some text", pen=COLOR_GREEN}   -- always green
yn(some_bool)                          -- YES (green) / no (dark gray)
yn(some_bool, COLOR_CYAN, COLOR_RED)  -- custom colors
```

After adding a row, update the separator and all rows below it — increment each `t=` value by 1, and also update `local W, H = 44, 32` if the window needs to grow taller.

### Adding a control button

Buttons are `widgets.HotkeyLabel` views in the Controls section. Pick an unused key binding and add the view:
```lua
widgets.HotkeyLabel{
    frame = {t=20, l=2},          -- t= row, l=2 indents it under "Controls:"
    key   = "CUSTOM_SHIFT_X",     -- DFHack key binding name
    label = "My action",
    on_activate = function()
        dfhack.run_command("dwarfipelago", "some-subcommand")
        self:dismiss()            -- close the panel after acting
    end,
},
```

Available `CUSTOM_SHIFT_*` keys: A–Z. Avoid S (Restart/Start) and R (Reset) which are already taken.

### Moving the `[AP]` hotspot button

The corner button position is set in `DwarfipelagoHotspot.ATTRS`:
```lua
default_pos = {x=8, y=2},   -- x= column from left, y= row from top (1-indexed)
```

Negative values count from the bottom-right edge (e.g. `{x=-5, y=-2}`).
The position only takes effect on first load — if DFHack has already saved a position for this widget, edit `dfhack-config/overlay.json` in your DF install and remove the `dwarfipelago-panel.hotspot` entry to reset it.

---

## DFHack Console Debug Commands

Run these from the DFHack console while a world is loaded:

```
# Full state dump
dwarfipelago status

# Manually start/stop/restart the mod
dwarfipelago start
dwarfipelago stop

# Open the in-game status panel
dwarfipelago panel

# Reset all persistent state
dwarfipelago reset

# Manually deliver an item (for testing)
dwarfipelago receive "Gold Bar"

# Peek at any storage key
lua print(dfhack.persistent.getWorldDataString("dwarfipelago/pending_item_created"))
lua print(dfhack.persistent.getWorldDataString("dwarfipelago/pending_checks"))

# Read a single craft count (use single quotes to avoid the console eating the string)
lua print(dfhack.persistent.getWorldDataString('dwarfipelago/craft_count/door'))

# Craft counts are included in the full status dump
dwarfipelago status

# Show where the mod log file is written
lua print(reqscript("internal/dwarfipelago/log").path())
```

> The mod log file (`<Dwarf Fortress>/dwarfipelago.log`) captures spawn failures,
> depot placement, and other in-game errors. The AP client window captures
> client/RPC/network errors with full tracebacks.
