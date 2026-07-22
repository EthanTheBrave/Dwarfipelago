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
| `dwarfipelago/shop_buy` | JSON `int[]` | Lua | Merchant's Shop slot indices the player has purchased; Python fulfils each (deducts coins, sends the item) then clears the queue |

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
| `dwarfipelago/craft_count_index` | JSON `string[]` | Lua | Every craft flag that has been incremented this world; lets `status` enumerate dynamic material-split keys |
| `dwarfipelago/skill/<name>` | Integer string | Lua | Highest level of skill `<name>` already counted toward skillsanity checks (so re-scans don't re-fire levels already sent) |
| `dwarfipelago/blueprint/<name>` | `"1"` or absent | Lua | Set when a blueprint item has been received |
| `dwarfipelago/unlock/wealth_coffers` | Integer string | Lua | How many Merchant's Coffers received (0–5); gates wealth tier checks. Coffers also cap coin minting / gem cutting, but **only when `goal` is `"1"` (legendary_wealth)** — under other goals minting/cutting is never blocked |
| `dwarfipelago/unlock/immigration_waves` | Integer string | Lua | How many Immigration Waves received (0–5); gates title/population checks |
| `dwarfipelago/unlock/baron_charter` | `"1"` or absent | Lua | Set when Baron's Charter received; gates Baron Appointed check |
| `dwarfipelago/unlock/count_charter` | `"1"` or absent | Lua | Set when Count's Charter received; gates Count Appointed check |
| `dwarfipelago/unlock/duke_charter` | `"1"` or absent | Lua | Set when Duke's Charter received; gates Duke Appointed check |
| `dwarfipelago/unlock/monarch_invitation` | `"1"` or absent | Lua | Set when Monarch's Invitation received; gates Monarch Takes Residence check |
| `dwarfipelago/unlock/military_training` | Integer string | Lua | How many Military Training items received (0–10); drives **War Readiness** for the slay_megabeast goal. Each grants an escalating war shipment (steel, adamantine at tiers 7+), a chance of bonus war material, and a one-time champion dwarf. Effective readiness past 4 is gated in-fort by a set-up barracks (5-6) and 4 soldiers at combat skill 10+ (7-9); roaming-warband difficulty scales with it |
| `dwarfipelago/unlock/artifact_weapon` | `"1"` or absent | Lua | Set when Artifact Weapon received; gates slay_megabeast and mountainhome goals |
| `dwarfipelago/unlock/artifact_armor` | `"1"` or absent | Lua | Set when Artifact Armor received; gates population_boom prestige requirement |
| `dwarfipelago/unlock/master_builders_codex` | `"1"` or absent | Lua | Set when Master Builder's Codex received; gates legendary_wealth, mountainhome, and population_boom goals |
| `dwarfipelago/unlock/RotGK` | Integer string | Lua | How many Remains of the Great King received; the king_remains goal completes when this reaches `king_remains_goal` |
| `dwarfipelago/unlock/mining_depth` | Integer string | Lua | How many Progressive Mining Depth items received (0–4); each lowers the allowed dig floor by one cavern tier (only enforced when config `mining_depth` is `"1"`) |
| `dwarfipelago/unlock/sunlight_tonic` | `"1"` or absent | Lua | Set when the Sunlight Tonic is received; dwarves may then walk freely in sunlight (no cave-adaptation nausea) |
| `dwarfipelago/craftlock/<flag>` | `"1"` or absent | Lua | Set when the Crafting Permit for `<flag>` is received. When `crafting_permits` is non-zero, jobs producing an item whose flag is unset are cancelled |
| `dwarfipelago/depot_built` | `"1"` or absent | Lua | Set once the starting trade depot has been placed or adopted |
| `dwarfipelago/shop_unlocked` | `"0"` or `"1"` | Lua | `"1"` while a valid **Merchant's Shrine** stands (a temple zone with a built altar, a container, the required bars — 5 gold / 10 silver / 20 coke — and value ≥ 5000☼); the shop is only buyable while set |
| `dwarfipelago/shop_unlocked_announced` | `"1"` or `""` | Lua | Dedupe flag so the "shop has opened" announcement fires once per opening |
| `dwarfipelago/shop_pending` | JSON `{slot: true}` | Lua | Slots the player has bought that await client confirmation; the panel/buy guard treat them as unavailable until the item is confirmed (then the slot's `bought` flag is set in `shop`) |
| `dwarfipelago/shrine_progress` | Float string | Lua | Progress (0–1 across the shrine's requirements) toward opening the shop, for the panel's Shop tab |
| `dwarfipelago/megabeast/spawned` | `"1"` or absent | Lua | Set once the climax megabeast has been summoned. The summon is **player-initiated** (`dwarfipelago summon-beast` / the panel War tab's button), allowed only once the full war effort - 10 Military Training + Artifact Weapon + 2 Immigration Waves - is in hand. Prevents re-summoning on reload and stops roaming waves |
| `dwarfipelago/megabeast/target_id` | Integer string | Lua | Unit ID of the pinned target megabeast; only this unit's death counts for the goal (natural megabeasts are cleared at load) |
| `dwarfipelago/megabeast/champion` | `"1"` or absent | Lua | Set once the one-time veteran champion dwarf has joined (rare chance per Military Training, guaranteed at tier 8) |
| `dwarfipelago/megabeast/next_wave_tick` | Integer string | Lua | Absolute game tick when the next roaming warband is due (`cur_year*403200 + cur_year_tick`); a random 2-4 in-game months ahead |
| `dwarfipelago/megabeast/wave_warned` | `"1"` or `""` | Lua | Set when the ~1-day-out warning for the pending wave has been announced; cleared when the next wave is scheduled |
| `dwarfipelago/mining/dig_count` | Integer string | Lua | Cumulative dig/channel/ramp jobs completed (tiles-excavated milestones) |
| `dwarfipelago/mining/surface_z` | Integer string | Lua | Captured surface z-level (baseline for depth milestones) |
| `dwarfipelago/mining/deepest_z` | Integer string | Lua | Deepest z any mining job has reached |
| `dwarfipelago/mining/cavern1`..`cavern3` | `"1"` or absent | Lua | Set when the 1st/2nd/3rd cavern layer is breached |
| `dwarfipelago/mining/ceiling/cavern1`..`cavern3` | Integer string | Lua | Z-level of the ceiling (topmost tile) of each cavern layer, recorded by `compute_cavern_ceilings()` and used to place custom caves in the gaps between layers |
| `dwarfipelago/mining/ceilings_done` | `"1"` or absent | Lua | Set once all three cavern ceiling z-levels have been measured; gates custom cave generation |
| `dwarfipelago/mining/magma` | `"1"` or absent | Lua | Set when the magma sea is reached |
| `dwarfipelago/mining/circus` | `"1"` or absent | Lua | Set when the Circus (underworld) is breached |
| `dwarfipelago/farming/crop_count` | Integer string | Lua | Cumulative harvested crops (harvest milestones) |
| `dwarfipelago/caves/generated` | `"1"` or absent | Lua | Set once all custom caves have been carved and stocked; prevents re-generation on reload |
| `dwarfipelago/caves/fragment_index` | Integer string | Lua | How many Cave Map Fragment hints have been revealed so far (0–6); incremented by `caves.reveal_next()` each time a fragment item is received |
| `dwarfipelago/cave/N/x` | Integer string | Lua | Map X coordinate of custom cave N (1–6); `-1` if the cave could not be placed |
| `dwarfipelago/cave/N/y` | Integer string | Lua | Map Y coordinate of custom cave N |
| `dwarfipelago/cave/N/z` | Integer string | Lua | Map Z coordinate (floor level) of custom cave N |
| `dwarfipelago/cave/N/type` | `"treasure"` or `"trap"` | Lua | Type of custom cave N — treasure caves send an AP check on discovery; trap caves also spawn hostile underground creatures |
| `dwarfipelago/cave/N/discovered` | `"0"` or `"1"` | Lua | Set to `"1"` when a living citizen first walks within the cave footprint; read by the Python client to fire the matching AP location check |
| `dwarfipelago/cave/N/revealed` | `"0"` or `"1"` | Lua | Set to `"1"` when a Cave Map Fragment hint for cave N has been announced (currently unused by the client; reserved for future UI) |

### Config (written by Python, read by Lua)

| Key | Format | Written by | Description |
|-----|--------|------------|-------------|
| `dwarfipelago/goal` | `"0"`–`"5"` | Python | Goal type from slot data (0=slay_megabeast, 1=legendary_wealth, 2=population_boom, 3=mountainhome, 4=king_remains, 5=dwarfsanity) |
| `dwarfipelago/wealth_goal` | Integer string | Python | Wealth target for legendary_wealth goal |
| `dwarfipelago/pop_goal` | Integer string | Python | Population target for population_boom goal |
| `dwarfipelago/king_remains_goal` | Integer string | Python | Number of Remains of the Great King required for the king_remains goal |
| `dwarfipelago/crafting_permits` | `"0"`, `"1"`, or `"2"` | Python | Crafting Permits mode: 0=off, 1=on (start with a basic set), 2=all. When non-zero, Lua cancels jobs for items whose `craftlock/<flag>` is not set |
| `dwarfipelago/energy_enabled` | `"0"` or `"1"` | Python | Whether Energy Link is enabled for this slot |
| `dwarfipelago/energy_link` | Integer string | Python | Current shared energy pool balance (kJ) available to spend; read by Lua to price/approve an early caravan |
| `dwarfipelago/caravan_energy_cost` | Integer string | Lua | Energy cost (kJ) of a requested early caravan, for Python to deduct from the pool |
| `dwarfipelago/request_caravan` | `"1"` or `"0"` | Lua | Set to `"1"` when the player requests an early caravan; Python deducts the cost and responds |
| `dwarfipelago/spawn_caravan_approved` | `"1"` or `"0"` | Python | Python sets `"1"` once the energy cost is deducted; Lua spawns the caravan then clears it |
| `dwarfipelago/ap_caravan_active` | `"1"` or `"0"` | Lua | Tracks whether an AP-summoned caravan is currently present (prevents stacking requests) |
| `dwarfipelago/energy_deposit` | Integer string | Lua | Energy (joules) the player has deposited (ale/food/coins) awaiting send to the pool; Python reads and clears |
| `dwarfipelago/use_energy_link` | `"Y"` or absent | Lua | Set when a deposit has occurred, signalling Python to process `energy_deposit` |
| `dwarfipelago/deathlink_threshold` | Integer string | Python | Dwarves (or % of pop) per DeathLink send/receive; option max is 50 |
| `dwarfipelago/deathlink_percentage` | `"0"` or `"1"` | Python | When `"1"`, threshold is treated as % of current population instead of a flat count |
| `dwarfipelago/seed` | Integer string | Python | World identity — used to scope AP storage keys and detect wrong-world loads |
| `dwarfipelago/received_index` | Integer string | Python | Count of received AP items already applied in-game; restored on reconnect so items aren't re-delivered (and counter-based progression items aren't double-counted) |
| `dwarfipelago/version` | Version string | Lua | Mod version recorded on `start()` |
| `dwarfipelago/craftsanity_enabled` | `"0"`, `"1"`, or `"2"` | Python | Craftsanity mode: 0=off, 1=on (crafted), 2=storage |
| `dwarfipelago/craftsanity_materials` | `"0"` or `"1"` | Python | When `"1"`, craft counts are split by material type (e.g. `barrel_wood` vs `barrel_metal`) |
| `dwarfipelago/custom_caves` | `"0"` or `"1"` | Python | Whether the Custom Caves feature is enabled for this slot; written by `_sync_slot_data` from `slot_data["custom_caves"]` |
| `dwarfipelago/deathlink` | `"0"` or `"1"` | Python | Whether DeathLink is enabled for this slot |
| `dwarfipelago/mining_depth` | `"0"` or `"1"` | Python | Whether **Progressive Mining Depth** gating is on. When `"1"`, Lua caps dig jobs at the floor implied by `unlock/mining_depth` |
| `dwarfipelago/craftsanity_max` | Integer string | Python | Total items to craft per item for all of its checks combined |
| `dwarfipelago/craftsanity_threshold` | Integer string | Python | Crafts per check (a check fires every N produced) |
| `dwarfipelago/craftsanity_labels` | JSON `{flag: label}` | Python | Display name for each craft flag, shown on the panel's Crafts tab |
| `dwarfipelago/skillsanity_enabled` | `"0"` or `"1"` | Python | Whether Skillsanity is enabled for this slot |
| `dwarfipelago/skillsanity_max_level` | Integer string | Python | Highest skill level that fires a check (1=Novice … 15=Legendary) |
| `dwarfipelago/skillsanity_behaviour` | `"0"` or `"1"` | Python | Level mechanic for pre-skilled arrivals: `0`=leave untouched (all levels fire at once), `1`=lower to the next unclaimed check |
| `dwarfipelago/shop_enabled` | `"0"` or `"1"` | Python | Whether the Merchant's Shop is enabled for this slot |
| `dwarfipelago/shop` | JSON `{slot: {item, price, bought}}` | Python | The shop's slot contents — one multiworld item and its coin price per slot |

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

Flag keys are **lowercase**, with spaces as underscores. With materials enabled,
the suffix is the resolved material (also lowercase).

| Key | Description |
|-----|-------------|
| `dwarfipelago/craft_count/barrel_metal` | Total Metal Barrels crafted/stored (when `craftsanity_materials` is `"1"`) |
| `dwarfipelago/craft_count/barrel_wood` | Total Wooden Barrels crafted/stored (when `craftsanity_materials` is `"1"`) |
| `dwarfipelago/craft_count/barrel` | Total Barrels of any material (when `craftsanity_materials` is `"0"`) |
| `dwarfipelago/craft_count/glass` | Total Glass items (Glass has only one material type, so always stored without suffix) |


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
- **Material split** — when `craftsanity_materials` is `"1"`, a material-relevant
  item's flag gets a `_<material>` suffix (e.g. `table_wood`, `blocks_stone`).
  `mat_craft_flag(job)` resolves the material, token-first, with fallbacks so it
  works for both manual jobs and Manager work orders:
  1. decode `job.mat_type`/`job.mat_index` and match the raw token —
     `IS_METAL` flag → `metal`, `GLASS` → `glass`, `CLAY`/`KAOLINITE`/`PORCELAIN`
     → `ceramic`, `INORGANIC` → `stone`, `:WOOD` → `wood`, `LEATHER` → `leather`,
     `SILK`/`YARN` → `cloth`, `BONE` → `bone`;
  2. else read the job's `material_category` bitfield (generic "any wood/stone" jobs);
  3. else scan the job's consumed/produced **items** for a usable material
     (manual workshop jobs often leave `mat_type = -1`);
  4. last resort: builtin `mat_type` (0 → `stone`, 3–5 → `glass`).

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
| `increment_craft_count(flag)` | fn → int | Increment and persist a craft count (also records the flag in the craft index), returns new total |
| `get_craft_count(flag)` | fn → int | Read current craft count for a flag |
| `get_all_craft_counts()` | fn → table | `{flag = count}` for every flag in the craft index with count > 0 (used by `status`) |
| `clear_craft_counts()` | fn | Wipe all recorded craft counts and the index (used by `reset`) |
| `fortress_wealth()` | fn → int | Current total fortress wealth (items + buildings + stocks) |
| `treasury_wealth()` | fn → int | Combined value of minted coins + cut gems **currently in fortress stocks** (live scan; used for the panel's wealth display) |
| `treasury_created_wealth()` | fn → int | **Lifetime** value of all coins minted + gems cut this world (a running counter, unaffected by later spending). Drives the **legendary_wealth** goal and the wealth-tier checks |

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

### `caves`

Custom cave generation, discovery detection, and Cave Map Fragment hint system.
Only active when `dwarfipelago/custom_caves` is `"1"`.

| Symbol | Type | Description |
|--------|------|-------------|
| `generate()` | fn | Carve and stock all custom caves on a fresh seed. No-ops if already done (`caves/generated == "1"`) or if cavern ceilings haven't been measured yet (`mining/ceilings_done != "1"`). Called from `poll_checks()` in `dwarfipelago.lua` after `compute_cavern_ceilings()`. |
| `check_discoveries()` | fn → table | Poll for living citizens within ±4 tiles of any undiscovered cave centre. Returns a list of `{index, cave_type, x, y, z}` for newly discovered caves and marks them as discovered in persistent storage. Called every poll cycle from `dwarfipelago.lua`. |
| `get_hint(idx)` | fn → string | Return a displayable hint string for cave `idx` (1–6). Treasure caves return an approximate coordinate string; trap caves return a cardinal-direction warning. Returns a "too worn to read" string if the cave was never placed. |
| `reveal_next()` | fn | Increment `caves/fragment_index` and announce the next cave hint via `dfhack.gui.showAnnouncement`. Called from `items.lua` when a Cave Map Fragment is received. Extra calls past index 6 show a "all caves already revealed" notice. |

Cave shapes are organic ovals carved with a random horizontal radius rx ∈ {3, 4} and vertical radius ry ∈ {2, 3}. Edge tiles are probabilistically included/excluded so the silhouette is irregular. The vaulted centre (dist² < 0.5 from ellipse centre) is 3 z-levels tall; outer tiles are 2 z-levels tall.

---

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

The popup is a resizable `widgets.Window` containing a `widgets.TabBar` + `widgets.Pages`,
each page a `widgets.Panel`. Tabs are built **dynamically** — several appear only when
the matching feature is enabled for the slot — so their absolute index is not fixed.
Full order:
`{"Status", "Unlocks", "Progress", "Caves", "Crafts", "Controls", "Energy", "Permits", "Skills", "Shop", "War"}`

| Tab | Shown when | Contents |
|-----|-----------|----------|
| **Status** | always | enabled state, goal, completion, depot status |
| **Unlocks** | always | progression unlock counts/flags — **built dynamically** from `items.UNLOCK_DEFS` |
| **Progress** | always | goal progress (wealth/population/remains toward target) |
| **Caves** | custom caves on | custom-cave discovery and hint status |
| **Crafts** | craftsanity on | craftsanity craft counts vs thresholds |
| **Controls** | always | Restart/Start (`Shift+S`), Reset all AP state (`Shift+R`), Reset seed (`Shift+D`) |
| **Energy** | `energy_enabled` | Energy Link pool balance (MJ + raw kJ), Deposit Ale/Food/Coins, and call-a-caravan |
| **Permits** | craftpermits on | crafting-permit (craftlock) status per item |
| **Skills** | skillsanity on | skillsanity per-skill level progress |
| **Shop** | `merchant_shop` on | Merchant's Shop slots/prices, shrine progress, and buy controls |
| **War** | slay_megabeast goal | War Readiness, barracks/soldier status, and the **Summon the Megabeast** button |

`open_panel()` toggles: calling it again while open dismisses the existing instance.

### Adding a status field

Add a `widgets.Label` to the **Status** page's `subviews` (Tab 1 in `pages`), with
`frame = {t=N, l=0}` where `t` is the row within that page. Read plain persistent
keys with the local `ps(key, default)` helper; read the enabled flag via
`state.is_enabled()` (it's stored as a JSON object, not a plain string). Use the
`yn(bool [,yes_color, no_color])` helper for YES/no values.

### Adding a progression unlock

You usually **don't** edit the panel — add an entry to `items.UNLOCK_DEFS` (in
`items.lua`) with `{ key, label, max? }` and it appears on the Unlocks tab
automatically (and in `dwarfipelago status`).

### Adding a control button

Add a `widgets.HotkeyLabel` to the **Controls** page's `subviews` (locate the page by its `"Controls"` label — the tab order is dynamic, so don't assume a fixed index):
```lua
widgets.HotkeyLabel{
    frame = {t=5, l=2},           -- next free row under the existing controls
    key   = "CUSTOM_SHIFT_X",     -- DFHack key binding name
    label = "My action",
    on_activate = function()
        dfhack.run_command("dwarfipelago", "some-subcommand")
        self:dismiss()
    end,
},
```

Available `CUSTOM_SHIFT_*` keys: A–Z. Taken: **S** (Restart/Start), **R** (Reset), **D** (Reset seed).

### Moving the `[AP]` hotspot button

The corner button position is set in `DwarfipelagoHotspot.ATTRS`:
```lua
default_pos = {x=6, y=2},   -- x= column from left, y= row from top (1-indexed)
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

# Clear the stored AP seed so this saved world can join a freshly generated slot
# (keeps checks/unlocks/craft counts; use 'reset' for a full wipe)
dwarfipelago resetseed

# Manually deliver an item (for testing)
dwarfipelago receive "Gold Bar"

# Deposit into the shared Energy Link pool (requires energy_enabled)
dwarfipelago deposit-coins 500
dwarfipelago deposit-ale
dwarfipelago deposit-food

# Call an AP-summoned caravan early / send the current one away (Energy Link)
dwarfipelago call-caravan
dwarfipelago dismiss-caravan

# Buy Merchant's Shop slot N (requires the shop open — build a Merchant's Shrine)
dwarfipelago buy-shop 3

# Summon the target megabeast (slay_megabeast goal; needs the full war effort:
# 10 Military Training + Artifact Weapon + 2 Immigration Waves)
dwarfipelago summon-beast

# Run a mechanic verification test (no name = list them). Tests:
#   spawn [RACE] | find <substr> | goblin | cavebear | vermin | spider
#   megabeast | migrants | caravan [dwarf|elf|human|goblin]
dwarfipelago test caravan elf

# Peek at any storage key
lua print(dfhack.persistent.getWorldDataString("dwarfipelago/pending_item_created"))
lua print(dfhack.persistent.getWorldDataString("dwarfipelago/pending_checks"))

# Check custom cave state (N = 1..6)
lua print(dfhack.persistent.getWorldDataString("dwarfipelago/caves/generated"))
lua print(dfhack.persistent.getWorldDataString("dwarfipelago/cave/1/type"))
lua print(dfhack.persistent.getWorldDataString("dwarfipelago/cave/1/discovered"))

# Force a Cave Map Fragment hint for cave N (bypasses the item system)
lua reqscript("internal/dwarfipelago/caves").reveal_next()

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
