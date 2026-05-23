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
| `slay_megabeast` | Kill a dragon, titan, or other megabeast *(default)* |
| `legendary_wealth` | Reach a configurable fortress wealth target (default: 100,000☼) |
| `population_boom` | Grow your fortress to a configurable population (default: 300 dwarves) |

## Locations (Checks)

Completing these milestones sends items to other players:

- **Wealth milestones** — Humble Beginnings → Growing Stronghold → Prosperous Fortress → Rich Citadel → Legendary Vault
- **First production** — first weapon forged, armor crafted, meal prepared, brew completed, metal bar smelted, gem cut, and more (18 milestones)
- **Trade & diplomacy** — first caravan trade, first export, dwarven/elven/human caravan visits, outpost liaison meeting
- **Fortress status** — noble appointments and civilisation recognition milestones

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
