"""
Archipelago launcher integration for Dwarf Fortress.

When this module is imported by the AP launcher it registers two buttons:

  • "Dwarf Fortress"        (Type.GAME)   — launches dfhack.exe / the DF executable
  • "Dwarf Fortress Client" (Type.CLIENT) — launches DwarfFortressClient.py

The game executable path is read from host.yaml (dwarf_fortress_options.game_path).
If it is not set, common Steam install locations are tried as a fallback.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional

# ── Launcher component registration ───────────────────────────────────────────
# worlds.LauncherComponents is only present inside a full AP installation.

try:
    from worlds.LauncherComponents import Component, Type, launch_subprocess, components
    _HAS_LAUNCHER = True
except ImportError:
    _HAS_LAUNCHER = False


# ── DF executable discovery ───────────────────────────────────────────────────

_STEAM_CANDIDATES: list[str] = [
    # Windows — 32-bit Steam
    r"C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress\dfhack.exe",
    # Windows — 64-bit Steam
    r"C:\Program Files\Steam\steamapps\common\Dwarf Fortress\dfhack.exe",
    # Linux — default Steam library
    os.path.expanduser("~/.steam/steam/steamapps/common/Dwarf Fortress/dfhack"),
    # Linux — flatpak Steam
    os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam"
                       "/steamapps/common/Dwarf Fortress/dfhack"),
    # macOS — Steam
    os.path.expanduser("~/Library/Application Support/Steam"
                       "/steamapps/common/Dwarf Fortress/dfhack"),
]


def _get_df_executable() -> Optional[str]:
    """Return the DF executable path from settings, or fall back to Steam defaults."""
    # 1. Try AP settings (host.yaml).
    try:
        from settings import get_settings
        path = str(get_settings().dwarf_fortress_options.game_path)
        if os.path.isfile(path):
            return path
    except Exception:
        pass

    # 2. Try common Steam install locations.
    for path in _STEAM_CANDIDATES:
        if os.path.isfile(path):
            return path

    return None


# ── Launcher callbacks ────────────────────────────────────────────────────────

def launch_game(*args) -> None:
    """
    Launch Dwarf Fortress (with DFHack).

    Prefers dfhack.exe / dfhack so the remote API is available immediately.
    Falls back to Dwarf Fortress.exe if dfhack is not found.
    """
    exe = _get_df_executable()
    if not exe:
        _show_not_found_error()
        return

    cwd = os.path.dirname(exe)
    try:
        subprocess.Popen([exe], cwd=cwd)
    except OSError as e:
        _show_error("Failed to launch Dwarf Fortress", str(e))


def launch_client(*args) -> None:
    """Launch DwarfFortressClient.py via the AP subprocess helper."""
    try:
        import DwarfFortressClient
    except ModuleNotFoundError:
        _show_error(
            "DwarfFortressClient not found",
            "DwarfFortressClient.py was not found in your Archipelago installation.\n\n"
            "Copy DwarfFortressClient.py from the Dwarfipelago repo into the root of "
            "your Archipelago installation and try again.",
        )
        return

    if _HAS_LAUNCHER:
        launch_subprocess(DwarfFortressClient.main, name="Dwarf Fortress Client")
    else:
        # Fallback: run as a subprocess of the current Python interpreter.
        script = os.path.join(os.path.dirname(sys.argv[0]), "DwarfFortressClient.py")
        subprocess.Popen([sys.executable, script])


# ── Error helpers ─────────────────────────────────────────────────────────────

def _show_not_found_error() -> None:
    _show_error(
        "Dwarf Fortress not found",
        "Could not locate the Dwarf Fortress executable.\n\n"
        "Set the path in your Archipelago host.yaml:\n\n"
        "  dwarf_fortress_options:\n"
        "    game_path: C:\\Path\\To\\dfhack.exe",
    )


def _show_error(title: str, message: str) -> None:
    try:
        import tkinter.messagebox as mb
        mb.showerror(title, message)
    except Exception:
        # No GUI available — print to stderr so CI / headless runs still see it.
        print(f"[Dwarfipelago] ERROR — {title}: {message}", file=sys.stderr)


# ── Register components ───────────────────────────────────────────────────────

if _HAS_LAUNCHER:
    components += [
        Component(
            "Dwarf Fortress",
            func=launch_game,
            component_type=Type.GAME,
            game_name="Dwarf Fortress",
        ),
        Component(
            "Dwarf Fortress Client",
            func=launch_client,
            component_type=Type.CLIENT,
            game_name="Dwarf Fortress",
        ),
    ]
