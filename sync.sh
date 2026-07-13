#!/usr/bin/env bash
# Sync the dwarfipelago mod from the repo to all install locations.
set -e

SRC="/home/localadmin/df/Dwarfipelago/mods/dwarfipelago/"
TARGETS=(
    "/home/localadmin/gameDF/mods/dwarfipelago/"
    "/home/localadmin/.local/share/Bay 12 Games/Dwarf Fortress/data/installed_mods/dwarfipelago (8)/"
)

for DEST in "${TARGETS[@]}"; do
    echo "→ $DEST"
    rsync -a --delete "$SRC" "$DEST"
done

echo "done"
