-- dwarfipelago-zlevel-delete.lua   (TEST/DEV HELPER -- SAVE FIRST!)
-- Deletes EVERY tile on a random z-level below the surface (a full-level wipe).
-- This removes all support for everything above that level, so expect a massive
-- cave-in, and total drainage/flooding if the level held water or magma.
-- Put the look cursor on a SURFACE tile (ground reference), then run:
--   dwarfipelago-zlevel-delete
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

-- Iterate blocks (16x16 each) on the chosen z and blank every tile.
local deleted = 0
for _, b in ipairs(df.global.world.map.map_blocks) do
    if b.map_pos.z == target_z then
        for lx = 0, 15 do
            for ly = 0, 15 do
                b.tiletype[lx][ly] = df.tiletype.OpenSpace
                pcall(function() b.designation[lx][ly].flow_size = 0 end)
                pcall(function() b.designation[lx][ly].hidden = false end)
                deleted = deleted + 1
            end
        end
        pcall(function() dfhack.maps.enableBlockUpdates(b, true, true) end)
    end
end

pcall(function() df.global.world.reindex_pathfinding = true end)

print(("deleted the ENTIRE z=%d (%d tiles, ground reference z=%d)")
    :format(target_z, deleted, gz))
print("Brace for cave-ins -- everything above that level just lost its support.")
