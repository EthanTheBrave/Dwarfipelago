# Dwarfipelago

A [Dwarf Fortress](https://www.bay12games.com/dwarves/) integration for the [Archipelago](https://archipelago.gg/) multiworld randomizer.

Complete economic and production milestones in your fortress to send items to other Archipelago players. Receive trade goods, resources, and (beware) traps from other games.

## Requirements

- Dwarf Fortress (Steam 2022+ or Classic)
- [DFHack](https://github.com/DFHack/dfhack) — Can also be downloaded through [Steam](https://store.steampowered.com/app/2346660/DFHack__Dwarf_Fortress_Modding_Engine/)
- [Archipelago](https://archipelago.gg/) 0.6.7

## Components

| Component | Path | Description |
|-----------|------|-------------|
| AP World | `worlds/dwarf_fortress/` | Archipelago world definition — install into your AP `worlds/` folder or package as `.apworld` |
| DFHack Mod | `mods/dwarfipelago/` | DFHack mod — copy into your DF installation's `mods/` folder |
| AP Client | `worlds/dwarf_fortress/DwarfFortressClient.py` | Bundled inside the AP world package — launched automatically by the AP launcher |

## Setup

See [`worlds/dwarf_fortress/docs/setup_en.md`](worlds/dwarf_fortress/docs/setup_en.md) for full installation and configuration instructions.

## Trade Depot

When you load a fortress with Dwarfipelago active, the mod automatically places a **Trade Depot** near your starting wagon. This depot serves as the central hub for Archipelago:

- **AP items you receive** (gems, bars, resources, traps) are spawned directly at the depot
- **Location checks** and **item delivery** are both held until the depot is established — nothing is sent to or received from the AP server before it exists

### What to expect on first load

1. Within a few in-game ticks of loading your fortress, you will see the announcement:
   > *[AP] A Trading Post has been established near your starting wagon!*
2. The depot is placed **7 tiles west** of your starting wagon and instantly completed — no dwarves or materials required
3. If that spot is blocked, the mod tries the other three cardinal directions automatically
4. If the player has already built a Trade Depot before the mod runs, the existing depot is adopted as the delivery point and no second one is placed

### If the depot is not appearing

- Make sure the mod is enabled in DF's mod manager and the installed_mods snapshot is up to date (see setup step 2)
- You can build a Trade Depot manually in any location — the mod will detect and adopt it on the next poll tick
- To force a retry, run in the DFHack console:
  ```
  lua dfhack.persistent.saveWorldDataString("dwarfipelago/depot_built", "0")
  ```
  Then save and reload your fortress

## Win Conditions

Configurable per-slot in your options YAML. Every goal also requires a minimum number of **Immigration Waves** (see Progression below).

| Goal | Description | Waves required |
|------|-------------|---------------|
| `population_boom` | Grow your fortress to a configurable population (default: 300 dwarves) *(default)* | 5 |
| `legendary_wealth` | Reach a configurable fortress wealth target (default: 100,000☼) | 3 |
| `slay_megabeast` | Kill a dragon, titan, or other megabeast | 2 |
| `mountainhome` | Achieve Mountainhome status — the monarch takes residence in your fortress (very difficult) | 5 |

## Locations (Checks)

Completing these milestones sends items to other players:

- **Wealth milestones** — Humble Beginnings (1,000☼) → Growing Stronghold (10,000☼) → Prosperous Fortress (50,000☼) → Rich Citadel (100,000☼) → Legendary Vault (500,000☼)
- **First production** — first weapon forged, armor crafted, meal prepared, brew completed, metal bar smelted, gem cut, and more (18 milestones)
- **Trade & diplomacy** — first caravan trade, first export, dwarven/elven/human caravan visits, outpost liaison meeting
- **Fortress status** — noble appointments and civilisation recognition milestones
- **Fortress titles** — Hamlet, Village, Town, City, Metropolis (population + wealth thresholds)

## Items Received

| Type | Examples |
|------|---------|
| Workshop blueprints | 29 blueprints that unlock workshops, furnaces, and farm plots — **progression items** (see Progression section below) |
| Progression locks | Merchant's Coffer (×5), Immigration Wave (×5), Noble Ladder charters (×4), Military Training (×3) — gate milestone checks and goal completion |
| Trade goods | Cut gems, gold/silver/steel bars, masterwork crafts |
| Resources | Food bundles, wood bundles, iron ore, coal |
| Traps | Goblin ambush, cave bear incursion, vermin infestation, tantrum trigger |

## Progression

### Workshop Blueprints

Workshop blueprints are the core Archipelago mechanic. Other players find your blueprints at their locations and send them to you, unlocking the matching structure in your fortress. Until you receive a blueprint, attempting to build that structure will be cancelled with a notification.

**Gated workshops:** Craftsdwarf's, Forge, Magma Forge, Kitchen, Jeweler's, Clothier's, Tanner's, Mechanic's, Siege, Soap Maker's, Ashery, Bowyer's, Screw Press, Fishery, Loom, Dyer's, Butcher's, Farmer's

**Gated furnaces:** Smelter, Magma Smelter, Wood Furnace, Glass Furnace, Kiln, Magma Kiln, Magma Glass Furnace

**Gated buildings:** Farm Plot

**Always available:** Carpenter's Workshop, Mason's Workshop, Still (dwarves need ale to survive)

### Progression Locks

Four systems of **progression lock items** gate milestone checks and goal completion. These items are found by your multiworld partners and sent to you; each one received unlocks the next tier of checks or advances your goal progress. All progression lock items are always present in the multiworld pool regardless of which goal you selected.

#### Merchant's Coffer (×5) — Wealth Tiers

Five coffers gate the five wealth milestone checks. Your fortress wealth may grow freely, but the AP check for each tier won't fire until the matching coffer arrives. If you reach a wealth tier without the coffer, a yellow announcement will remind you to look for it.

| Coffers received | Wealth check unlocked |
|---|---|
| 1 | Humble Beginnings (1,000☼) |
| 2 | Growing Stronghold (10,000☼) |
| 3 | Prosperous Fortress (50,000☼) |
| 4 | Rich Citadel (100,000☼) |
| 5 | Legendary Vault (500,000☼) |

The **Legendary Wealth** goal also requires all 5 coffers to complete.

#### Immigration Wave (×5) — Population Growth

Five waves gate the five fortress title checks (Hamlet through Metropolis) and scale up the population requirement for every goal's completion condition.

| Waves received | Title check unlocked | Also gates |
|---|---|---|
| 1 | Hamlet Established (pop 20) | — |
| 2 | Village Established (pop 50) | Slay Megabeast goal completion |
| 3 | Town Established (pop 80) | Legendary Wealth goal completion |
| 4 | City Established (pop 110) | — |
| 5 | Metropolis Established (pop 140) | Population Boom & Mountainhome goal completion |

#### Noble Ladder — Mountainhome

Four charter items gate the four upper noble appointment checks. The mayor is always accessible; higher ranks require the matching charter to have arrived from the multiworld.

| Item received | Check unlocked |
|---|---|
| Baron's Charter | Baron Appointed |
| Count's Charter | Count Appointed |
| Duke's Charter | Duke Appointed |
| Monarch's Invitation | Monarch Takes Residence |

The **Mountainhome** goal additionally requires the Monarch's Invitation before victory is recognised.

#### Military Training (×3) — Slay Megabeast

Three training items gate the megabeast slaying goal. Killing a megabeast without all three training items won't trigger victory — your military isn't considered ready yet.

## DeathLink

Dwarfipelago supports Archipelago's DeathLink system with a configurable threshold:

- Every **N dwarf deaths** (default: 5) in your fortress sends one DeathLink to all connected DeathLink players
- Receiving a DeathLink kills **N random dwarves** in your fortress
- Set `deathlink_threshold: 1` in your options for classic one-death-equals-one-death behaviour

## Troubleshooting

- **"Dwarf Fortress not found"** — set `game_path` in `host.yaml` (see Step 4 above)
- **Client can't connect to DFHack** — ensure DFHack is running and its remote API is active on `127.0.0.1:5000`
- **Mod doesn't start automatically** — load a fortress first and wait ~5 seconds; you can also run `dwarfipelago start` manually in the DFHack console
- **Items not arriving** — check the client log window; items are delivered via DFHack script calls when the client is connected

For full setup details see [`worlds/dwarf_fortress/docs/setup_en.md`](worlds/dwarf_fortress/docs/setup_en.md).

---

## Project Board

A running list of ideas, planned features, and things that still need doing. No particular order — just a place to capture thoughts before they disappear.

### To Do

- [x] Implement DFHack protobuf wire encoding for `RunCommand` to deliver items in-game
- [x] Implement trap item spawning in `items.lua` (goblin ambush, cave bear, vermin, tantrum)
- [x] Add `fill_slot_data` population goal amount to client sync so Lua reads the correct target
- [x] Goal completion detection and AP victory signaling (`ClientStatus.CLIENT_GOAL`)
- [x] Fortress status checks — noble appointments and civilisation recognition milestones
- [x] Batch DeathLink — configurable threshold (N deaths out / N deaths in), feedback-loop prevention
- [x] Archipelago Launcher integration — Dwarf Fortress and Dwarf Fortress Client buttons; mod auto-starts when a world is loaded
- [x] Wire up caravan detection (merchant/diplomat unit scanning, exported-wealth tracking for trade/export flags)
- [x] Fortress title location checks — Hamlet / Village / Town / City / Metropolis (population + wealth thresholds)
- [x] Mountainhome win condition — achieve Mountainhome status (monarch takes residence)
- [x] Progression lock items — Merchant's Coffer, Immigration Wave, Noble Ladder, Military Training gate milestone checks and goal completion
- [~] Validate `df.job_type` enum values against a live DFHack console for all production checks
- [~] Validate `createitem` material strings against DF raws (gem types, metal bar identifiers)
- [x] Write end-to-end test instructions in `docs/`

### Ideas / Future Features

- [ ] **Skill milestone locations** — first Skilled / Expert / Master dwarf per skill category (originally cut for scope)
- [ ] **Combat milestone locations** — first kill, first siege survived, first forgotten beast
- [ ] **Artifact creation check** — a dwarf goes into a strange mood and produces an artifact
- [ ] **Custom AP items** — define unique DF-flavored items as raw reactions for cleaner in-game delivery
- [ ] **Overlay UI** — DFHack overlay panel showing current AP connection status and recent items
- [ ] **Multi-fortress support** — allow switching between saves without resetting AP state
- [ ] **DeathLink targeting** — option to target specific skill types when applying received DeathLink deaths
- [ ] **Random Option for Crafting Check** — selects a specified number of random item checks to have included in AP gen
- [ ] **Rival Beast When MegaBeast is Victory** — finds a named beast during world gen and spawns them in when a specific check is sent

---
