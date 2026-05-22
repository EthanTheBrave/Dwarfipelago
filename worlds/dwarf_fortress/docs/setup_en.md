# Dwarf Fortress Setup Guide

## Required Software

- [Dwarf Fortress](https://store.steampowered.com/app/975370/Dwarf_Fortress/) (Steam) or [Classic](https://www.bay12games.com/dwarves/)
- [DFHack](https://github.com/DFHack/dfhack/releases) (bundled with the Steam version)
- [Archipelago](https://archipelago.gg/) 0.4.0+
- Python 3.10+

## Installation

### 1. Install the AP World

Copy the `dwarf_fortress` folder into your Archipelago `worlds/` directory, then restart Archipelago.

Alternatively, package and install as an `.apworld`:
```
cd path/to/Dwarfipelago
zip -r dwarf_fortress.apworld worlds/dwarf_fortress/
```
Then drag the `.apworld` file onto the Archipelago launcher.

### 2. Install the DFHack Mod

Copy `dfhack/scripts/dwarfipelago/` into your Dwarf Fortress installation's `dfhack/scripts/` directory.

Steam path (Windows): `C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress\dfhack\scripts\`

### 3. Install Python Dependencies

```
pip install -r requirements.txt
```

## Creating a Session

Create a `DwarfFortress.yaml` file:

```yaml
name: YourName
game: Dwarf Fortress
description: My DF world

Dwarf Fortress:
  goal: slay_megabeast        # slay_megabeast | legendary_wealth
  wealth_goal_amount: 100000  # only used when goal is legendary_wealth
  trap_item_weight: 20        # 0–100, percentage of filler that are traps
```

Then generate your session as normal through the Archipelago launcher or CLI.

## Playing

1. Start Dwarf Fortress and load (or embark on) a fortress
2. In the DFHack console, run: `dwarfipelago/main start`
3. In a separate terminal, run the client:
   ```
   python DwarfFortressClient.py --server archipelago.gg:PORT --name YourName
   ```
4. Play DF normally — the client will automatically detect milestones and send/receive items

## Troubleshooting

- **DFHack not found**: Make sure DFHack is installed and running (you should see the DFHack console alongside DF)
- **Client can't connect to DFHack**: Verify DFHack's remote server is enabled at `127.0.0.1:5000`
- **Items not spawning**: Check the client log; items are delivered to your active stockpile areas
