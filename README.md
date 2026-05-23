# Dwarfipelago

A [Dwarf Fortress](https://www.bay12games.com/dwarves/) integration for the [Archipelago](https://archipelago.gg/) multiworld randomizer.

Complete economic and production milestones in your fortress to send items to other Archipelago players. Receive trade goods, resources, and (beware) traps from other games.

## Requirements

- Dwarf Fortress (Steam 2022+ or Classic)
- [DFHack](https://github.com/DFHack/dfhack) — bundled with the Steam version; install separately for Classic
- [Archipelago](https://archipelago.gg/) 0.4.0+

## Components

| Component | Path | Description |
|-----------|------|-------------|
| AP World | `worlds/dwarf_fortress/` | Archipelago world definition — install into your AP `worlds/` folder or package as `.apworld` |
| DFHack Mod | `dfhack/scripts/dwarfipelago/` | Lua scripts — copy into your DF `dfhack/scripts/` folder |
| AP Client | `DwarfFortressClient.py` | Copy into your Archipelago root; launched from the AP launcher |

## Quick Setup

1. **Install the AP World**
   - Copy `worlds/dwarf_fortress/` into your Archipelago `worlds/` directory
   - Or package it: `zip -r dwarf_fortress.apworld worlds/dwarf_fortress/`

2. **Install the DFHack mod**
   - Copy `dfhack/scripts/dwarfipelago/` into your DF installation's `dfhack/scripts/` folder
   - Steam (Windows): `C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress\dfhack\scripts\`

3. **Install the AP Client**
   - Copy `DwarfFortressClient.py` into the root of your Archipelago installation (same folder as `ArchipelagoLauncher.exe`)

4. **Configure the game path** in your Archipelago `host.yaml`:
   ```yaml
   dwarf_fortress_options:
     game_path: C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress\dfhack.exe
   ```

5. **Generate your Archipelago session** with a `DwarfFortress.yaml` options file (see `worlds/dwarf_fortress/docs/setup_en.md`)

6. **In the Archipelago launcher:**
   - Click **Dwarf Fortress** to launch the game
   - Load or embark on a fortress
   - Click **Dwarf Fortress Client** and connect to your server
   - The mod starts automatically once your fortress is loaded — no DFHack console commands needed

## Win Conditions

Configurable per-slot in your options YAML:

| Goal | Description |
|------|-------------|
| `population_boom` | Grow your fortress to a configurable population (default: 300 dwarves) *(default)* |
| `legendary_wealth` | Reach a configurable fortress wealth target (default: 100,000☼) |
| `slay_megabeast` | Kill a dragon, titan, or other megabeast |
| `mountainhome` | Achieve Mountainhome status — the monarch takes residence in your fortress (very difficult) |

## Locations (Checks)

Completing these milestones sends items to other players:

- **Wealth milestones** — Humble Beginnings → Growing Stronghold → Prosperous Fortress → Rich Citadel → Legendary Vault
- **First production** — first weapon forged, armor crafted, meal prepared, brew completed, metal bar smelted, gem cut, and more (18 milestones)
- **Trade & diplomacy** — first caravan trade, first export, dwarven/elven/human caravan visits, outpost liaison meeting
- **Fortress status** — noble appointments and civilisation recognition milestones
- **Fortress titles** — Hamlet, Village, Town, City, Metropolis (population + wealth thresholds)

## Items Received

| Type | Examples |
|------|---------|
| Trade goods | Cut gems, gold/silver/steel bars, masterwork crafts |
| Resources | Food bundles, wood bundles, iron ore, coal |
| Traps | Goblin ambush, cave bear incursion, vermin infestation, tantrum trigger |

## DeathLink

Dwarfipelago supports Archipelago's DeathLink system with a configurable threshold:

- Every **N dwarf deaths** (default: 5) in your fortress sends one DeathLink to all connected DeathLink players
- Receiving a DeathLink kills **N random dwarves** in your fortress
- Set `deathlink_threshold: 1` in your options for classic one-death-equals-one-death behaviour

## Troubleshooting

- **"Dwarf Fortress not found"** — set `game_path` in `host.yaml` (see Step 4 above)
- **Client can't connect to DFHack** — ensure DFHack is running and its remote API is active on `127.0.0.1:5000`
- **Mod doesn't start automatically** — load a fortress first and wait ~5 seconds; you can also run `dwarfipelago/main start` manually in the DFHack console
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
- [ ] Validate `df.job_type` enum values against a live DFHack console for all production checks
- [ ] Validate `createitem` material strings against DF raws (gem types, metal bar identifiers)
- [ ] Write end-to-end test instructions in `docs/`
- [ ] Package and test as a proper `.apworld` file

### Ideas / Future Features

- [ ] **Skill milestone locations** — first Skilled / Expert / Master dwarf per skill category (originally cut for scope)
- [ ] **Combat milestone locations** — first kill, first siege survived, first forgotten beast
- [ ] **Artifact creation check** — a dwarf goes into a strange mood and produces an artifact
- [ ] **Custom AP items** — define unique DF-flavored items as raw reactions for cleaner in-game delivery
- [ ] **Overlay UI** — DFHack overlay panel showing current AP connection status and recent items
- [ ] **Multi-fortress support** — allow switching between saves without resetting AP state
- [ ] **DeathLink targeting** — option to target specific skill types when applying received DeathLink deaths

---
