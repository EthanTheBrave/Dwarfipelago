# Dwarf Fortress Setup Guide

## Required Software

- [Dwarf Fortress](https://store.steampowered.com/app/975370/Dwarf_Fortress/) (Steam) or [Classic](https://www.bay12games.com/dwarves/)
- [DFHack](https://github.com/DFHack/dfhack/releases) — bundled with the Steam version, required for Classic
- [Archipelago](https://archipelago.gg/) 0.4.0+

## Installation

### 1. Install the AP World

Copy the `dwarf_fortress` folder into your Archipelago `worlds/` directory, then restart Archipelago.

Alternatively, package and install as an `.apworld`:
```
cd path/to/Dwarfipelago/worlds
zip -r ../dwarf_fortress.apworld dwarf_fortress/
```
Then drag the `.apworld` file onto the Archipelago launcher.

> **Important:** The zip command must be run from inside the `worlds/` directory so that
> `dwarf_fortress/__init__.py` sits at the top level of the archive — not nested under
> `worlds/dwarf_fortress/`. AP will silently fail to load a world with the wrong zip structure.

### 2. Install the DFHack Mod

Copy `dfhack/scripts/dwarfipelago/` into your Dwarf Fortress `dfhack/scripts/` directory:

- **Steam (Windows):** `C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress\dfhack\scripts\`
- **Steam (Linux):** `~/.steam/steam/steamapps/common/Dwarf Fortress/dfhack/scripts/`

### 3. Configure the Game Path (first time only)

Open your Archipelago `host.yaml` and add:

```yaml
dwarf_fortress_options:
  game_path: C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress\dfhack.exe
```

Adjust the path to match your DF installation.  The Steam version of DF ships with DFHack built in — using `dfhack.exe` is strongly recommended as it starts both DF and DFHack in one step.

## Creating a Session

Create a `DwarfFortress.yaml` file:

```yaml
name: YourName
game: Dwarf Fortress
description: My DF world

Dwarf Fortress:
  goal: population_boom          # population_boom | legendary_wealth | slay_megabeast | mountainhome
  wealth_goal_amount: 100000    # only used when goal is legendary_wealth
  population_goal_amount: 300   # only used when goal is population_boom (range: 20–500)
  trap_item_weight: 20          # 0–100, percentage of filler that are traps
  deathlink_threshold: 5        # how many dwarf deaths trigger one DeathLink (1–20)
```

Then generate your session as normal through the Archipelago launcher or CLI.

## Playing

The AP client is bundled inside the world package — there is no separate file to copy into your Archipelago root.

1. In the Archipelago launcher, click **Dwarf Fortress** to launch the game
2. Embark on a new fortress (or load an existing one)
3. In the Archipelago launcher, click **Dwarf Fortress Client** and enter your server details
4. The client detects when a world is loaded and starts the mod automatically
5. Play DF normally — milestones are detected automatically and items flow both ways

> **Note:** You can also start the mod manually at any time from the DFHack console:
> ```
> dwarfipelago/main start
> ```

## Troubleshooting

- **"Dwarf Fortress not found" error:** Set `game_path` in `host.yaml` as described in Step 3 above
- **"Dwarf Fortress Client" button missing from launcher:** Make sure the `dwarf_fortress` world package is installed in your Archipelago `worlds/` directory and restart the launcher
- **DFHack not found:** Make sure DFHack is installed — Steam DF includes it; for Classic DF, install it separately
- **Client can't connect to DFHack:** Verify DFHack's remote API is enabled at `127.0.0.1:5000`. In DFHack console: `enable dfhack-run-server` or check `dfhack-config/init.lua`
- **Items not spawning:** Check the client log window; items are delivered via DFHack script calls
- **Mod not starting automatically:** Load a fortress first, then wait one poll cycle (~5 s). You can always run `dwarfipelago/main start` manually
