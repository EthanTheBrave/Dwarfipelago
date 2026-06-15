-- dwarfipelago-tile-delete.lua   (TEST/DEV HELPER -- SAVE FIRST)
-- Picks a random z-level below the surface and blanks a bunch of random tiles on
-- it to open space (deletes them). Undermining support can trigger cave-ins.
-- Put the look cursor on a SURFACE tile (used as the "ground" reference), run:
--   dwarfipelago-tile-delete
local NUM       = 1000 -- how many tiles to delete
local DEPTH_MIN = 3    -- min z-levels below ground
local DEPTH_MAX = 100  -- max z-levels below ground

-- Ground reference z: cursor, else first citizen.
local gz
pcall(function() local c = guidm.getCursorPos(); if c then gz = c.z end end)
if not gz then
    for _, u in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(u) then gz = u.pos.z break end
    end
end
if not gz then qerror("No cursor and no citizen for a ground reference - place the look cursor.") end

local target_z = math.max(1, gz - math.random(DEPTH_MIN, DEPTH_MAX))
local xmax = df.global.world.map.x_count - 1
local ymax = df.global.world.map.y_count - 1

local deleted = 0
for _ = 1, NUM do
    local x, y = math.random(0, xmax), math.random(0, ymax)
    local b = dfhack.maps.getTileBlock(x, y, target_z)
    if b then
        local lx, ly = x % 16, y % 16
        b.tiletype[lx][ly] = df.tiletype.OpenSpace
        pcall(function() b.designation[lx][ly].flow_size = 0 end)
        pcall(function() b.designation[lx][ly].hidden = false end)   -- so we can see it
        pcall(function() dfhack.maps.enableBlockUpdates(b, true, true) end)
        deleted = deleted + 1
    end
end

-- Nudge the map to recompute (helps the holes render / flows start).
pcall(function() df.global.world.reindex_pathfinding = true end)

print(("deleted %d tiles on z=%d (ground reference z=%d)"):format(deleted, target_z, gz))
print("Most sub-surface tiles are solid rock; the holes show where it hits dug/")
print("open areas, and may trigger cave-ins or flooding if it opened an aquifer/sea.")
