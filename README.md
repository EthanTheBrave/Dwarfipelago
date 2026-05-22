# Dwarfipelago

A [Dwarf Fortress](https://www.bay12games.com/dwarves/) integration for the [Archipelago](https://archipelago.gg/) multiworld randomizer.

Complete economic and production milestones in your fortress to send items to other Archipelago players. Receive trade goods, resources, and (beware) traps from other games.

## Requirements

- Dwarf Fortress (Steam/itch.io 2022+ or Classic)
- [DFHack](https://github.com/DFHack/dfhack) (bundled with the Steam version; install separately for Classic)
- Python 3.10+
- An [Archipelago](https://archipelago.gg/) installation (for the AP world)

## Components

| Component | Path | Description |
|-----------|------|-------------|
| AP World | `worlds/dwarf_fortress/` | Archipelago world definition — install into your AP `worlds/` folder or package as `.apworld` |
| DFHack Mod | `dfhack/scripts/dwarfipelago/` | Lua scripts — copy into your DF `dfhack/scripts/` folder |
| AP Client | `DwarfFortressClient.py` | Run alongside DF to bridge the game and AP server |

## Quick Setup

1. **Install the AP World**
   - Copy `worlds/dwarf_fortress/` into your Archipelago `worlds/` directory
   - Or package it: `zip -r dwarf_fortress.apworld worlds/dwarf_fortress/`

2. **Install the DFHack mod**
   - Copy `dfhack/scripts/dwarfipelago/` into your DF installation's `dfhack/scripts/` folder

3. **Install Python dependencies**
   ```
   pip install -r requirements.txt
   ```

4. **Generate your Archipelago session** with a `DwarfFortress.yaml` options file (see `worlds/dwarf_fortress/docs/setup_en.md`)

5. **Start Dwarf Fortress** with DFHack active, then load a fortress

6. **Run the client**
   ```
   python DwarfFortressClient.py --server archipelago.gg:PORT --name YourSlotName
   ```

7. **In the DFHack console**, enable the mod:
   ```
   dwarfipelago/main start
   ```

## Win Conditions (configurable in options)

- **Slay a Megabeast** — kill a dragon, titan, or other megabeast
- **Legendary Wealth** — reach a configurable fortress wealth target
- **Legendary Skill** — any dwarf reaches Legendary skill level

## Locations (Checks)

Completing these milestones sends items to other players:

- **Wealth milestones**: Humble Beginnings → Growing Stronghold → Prosperous Fortress → Rich Citadel → Legendary Vault
- **First production**: first weapon, armor, meal, brew, metal bar, gem cut, and more (~18 milestones)
- **Trade events**: first caravan trade, first export, meeting the outpost liaison

## Items Received

| Type | Examples |
|------|---------|
| Trade goods | Cut gems, gold/silver/steel bars, masterwork crafts |
| Resources | Food bundles, wood bundles, iron ore, coal |
| Traps | Goblin ambush, cave bear incursion, vermin infestation, tantrum trigger |

## Development

See the plan at `.claude/plans/i-want-to-make-dreamy-harbor.md` and memory references in `.claude/projects/`.
