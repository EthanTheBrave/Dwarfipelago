"""
Standalone entry point for the Dwarfipelago AP client.

When launched via the Archipelago launcher this file is NOT needed — the client
is bundled inside the worlds/dwarf_fortress/ package (worlds/dwarf_fortress/DwarfFortressClient.py)
and started automatically by the launcher component defined in client.py.

This shim exists for users who want to run the client directly from a terminal
without the AP launcher, e.g.:
    python DwarfFortressClient.py --server archipelago.gg:PORT --name YourName
"""

import sys
import os

# Allow running from the repo root even if it isn't on sys.path.
sys.path.insert(0, os.path.dirname(__file__))

from worlds.dwarf_fortress.DwarfFortressClient import main

if __name__ == "__main__":
    main()
