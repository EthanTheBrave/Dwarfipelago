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

Skipped types (never queued): `CORPSE`, `CORPSEPIECE`, `VERMIN`, `PLANT`, `PLANT_GROWTH`

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


#### Craft item flags (items crafted at a workshop)
| Flag | Job type(s) |
|------|-------------|
| `altar` | MakeTotem |
| `door` | MakeDoor |
| `cage` | MakeCage |
| `bin` | MakeBox |
| `blocks` | CutBlock |
| `wheelbarrow` | MakeWheelbarrow |
| `grate` | MakeGrate |
| `corkscrew` | MakeCorkscrew |
| `animal_trap` | MakeAnimalTrap |
| `ball` | MakeBall |
| `armor_stand` | MakeArmorStand |
| `pedestal` | MakePedestal |
| `bucket` | MakeBucket |
| `spike` | MakeSpike |

#### Craft material flags (determined by job + primary material)
| Flag | How it's triggered |
|------|--------------------|
| `cloth` | WeaveCloth, ProcessPlants |
| `leather` | TanHide |
| `metal` | SmeltOre, MeltMetalObject |
| `glass` | MakeGlass |
| `ceramic` | MakeCeramicItem (Kiln) |
| `stone` | MakeCrafts / CarveFurniture / CarveStatue with inorganic non-metal material |
| `wood` | MakeCrafts / CarveFurniture with plant material |
| `bone` | MakeCrafts / CarveBone with creature material |

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
| `fortress_wealth()` | fn → int | Current total fortress wealth |

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

---

## DFHack Console Debug Commands

Run these from the DFHack console while a world is loaded:

```
# Full state dump
dwarfipelago status

# Manually start/stop the mod
dwarfipelago start
dwarfipelago stop

# Reset all persistent state
dwarfipelago reset

# Manually deliver an item (for testing)
dwarfipelago receive "Gold Bar"

# Peek at any storage key
lua print(dfhack.persistent.getWorldDataString("dwarfipelago/pending_item_created"))
lua print(dfhack.persistent.getWorldDataString("dwarfipelago/pending_checks"))
lua print(dfhack.persistent.getWorldDataString("dwarfipelago/craft_checks"))

# Print current craft counts
lua reqscript("internal/dwarfipelago/checks").print_craft_counts()
```
