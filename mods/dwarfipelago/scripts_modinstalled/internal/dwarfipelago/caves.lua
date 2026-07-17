--@ module = true
-- Custom cave generation and discovery for Dwarfipelago.
--
-- Generates 6 pre-carved pockets in solid rock between cavern layers (2 per gap).
-- Treasure caves yield a multiworld item on discovery; trap caves spawn hostile
-- underground creatures.  Cave Map Fragment items reveal hints about cave locations.

local M = {}
local log = reqscript("internal/dwarfipelago/log")

-- Persistent storage keys
local KEY_DONE         = "dwarfipelago/caves/generated"
local KEY_FRAG_IDX     = "dwarfipelago/caves/fragment_index"
local KEY_PREFIX       = "dwarfipelago/cave/"
local KEY_SECRETS_DONE = "dwarfipelago/caves/secrets_done"
local KEY_SECRET1      = "dwarfipelago/cave/secret/1/"
local KEY_SECRET2      = "dwarfipelago/cave/secret/2/"
local NUM_CAVES        = 6  -- 2 per inter-cavern gap x 3 potential gaps

-- Tiletype IDs resolved at load time by scanning the enum, so we never depend on
-- a hardcoded number or a name that may differ between DF/DFHack versions.
-- (df.tiletype.RockFloor1 is nil in this build; df.tiletype[53] is Grass2StairD.)
local TT_OPEN_SPACE = df.tiletype.OpenSpace  -- 32; confirmed via console
local TT_ROCK_FLOOR = TT_OPEN_SPACE          -- fallback: should always be overwritten below
pcall(function()
    for i = df.tiletype._first_item, df.tiletype._last_item do
        local a = df.tiletype.attrs[i]
        if a and a.shape == df.tiletype_shape.FLOOR
             and a.material == df.tiletype_material.STONE then
            TT_ROCK_FLOOR = i
            break
        end
    end
end)

-- Item placement

-- Loot scattered across treasure cave floors.
local TREASURE_POOL = {
    {"BAR",         "INORGANIC:GOLD",                        6},
    {"BAR",         "INORGANIC:SILVER",                      8},
    {"BAR",         "INORGANIC:PLATINUM",                    4},
    {"BAR",         "INORGANIC:STEEL",                       6},
    {"BAR",         "INORGANIC:COPPER",                      8},
    {"FIGURINE",    "INORGANIC:GOLD",                        4},
    {"FIGURINE",    "INORGANIC:OBSIDIAN",                    5},
    {"FIGURINE",    "INORGANIC:MARBLE",                      6},
    {"CLOTH",       "PLANT_MAT:GRASS_TAIL_PIG:THREAD",       8},
    {"SKIN_TANNED", "CREATURE_MAT:COW:LEATHER",              6},
    {"BOULDER",     "INORGANIC:MAGNETITE",                   8},
    {"DRINK",       "PLANT_MAT:MUSHROOM_HELMET_PLUMP:DRINK", 5},
    {"BAR",         "INORGANIC:PIG_IRON",                    6},
    {"BOULDER",     "INORGANIC:LIMONITE",                    8},
    {"BAR",         "COAL:COKE",                             6},
}

-- Gem pairs for treasure caves: {primary, fallback}.
local GEM_POOL = {
    {"INORGANIC:RUBY",     "INORGANIC:GARNET"},
    {"INORGANIC:SAPPHIRE", "INORGANIC:AQUAMARINE"},
    {"INORGANIC:DIAMOND",  "INORGANIC:TOPAZ"},
    {"INORGANIC:EMERALD",  "INORGANIC:OLIVINE"},
    {"INORGANIC:AMETHYST", "INORGANIC:OPAL"},
}

-- Ore fallback chains for trap caves.
local IRON_ORES   = {"INORGANIC:HEMATITE",    "INORGANIC:MAGNETITE",    "INORGANIC:LIMONITE"}
local COPPER_ORES = {"INORGANIC:MALACHITE",   "INORGANIC:NATIVE_COPPER","INORGANIC:TETRAHEDRITE"}

-- Place `count` copies of (item_type, material) at (x,y,z) using the DFHack
-- createitem script (same mechanism as spawn_item in items.lua).
-- Returns the number successfully created.
local has_silent = type(dfhack.run_command_silent) == "function"
local function place_item_at(x, y, z, item_type, material, count)
    local ox = df.global.cursor.x
    local oy = df.global.cursor.y
    local oz = df.global.cursor.z
    df.global.cursor.x = x
    df.global.cursor.y = y
    df.global.cursor.z = z

    local created = 0
    for _ = 1, (count or 1) do
        if has_silent then
            local ok, r1, r2 = pcall(dfhack.run_command_silent, "createitem", item_type, material)
            local out = (type(r1) == "string" and r1) or (type(r2) == "string" and r2) or ""
            if ok and not out:find("nrecognized") then created = created + 1 end
        else
            if pcall(dfhack.run_command, "createitem", item_type, material) then
                created = created + 1
            end
        end
    end

    df.global.cursor.x = ox
    df.global.cursor.y = oy
    df.global.cursor.z = oz
    return created
end

-- Stock a cave with appropriate items immediately after carving.
-- floor_tiles: list of {x,y} positions from carve(); items are scattered across them.
local function stock_cave(cx, cy, cz, cave_type, floor_tiles)
    -- Pick a random floor tile for item placement, or fall back to centre.
    local function rand_pos()
        if floor_tiles and #floor_tiles > 0 then
            local t = floor_tiles[math.random(#floor_tiles)]
            return t.x, t.y, cz
        end
        return cx, cy, cz
    end

    if cave_type == "trap" then
        -- Ore piled in the centre so it looks like a tempting lode.
        local placed_iron = false
        for _, ore in ipairs(IRON_ORES) do
            if place_item_at(cx, cy, cz, "BOULDER", ore, 8) > 0 then
                placed_iron = true; break
            end
        end
        local placed_copper = false
        for _, ore in ipairs(COPPER_ORES) do
            if place_item_at(cx, cy, cz, "BOULDER", ore, 6) > 0 then
                placed_copper = true; break
            end
        end
        log.info(("Trap cave stocked: iron=%s copper=%s"):format(
            tostring(placed_iron), tostring(placed_copper)))
    else
        -- Shuffle treasure pool and pick 7-10 item types, each at a random floor tile.
        local pool = {}
        for _, v in ipairs(TREASURE_POOL) do table.insert(pool, v) end
        for i = #pool, 2, -1 do
            local j = math.random(i)
            pool[i], pool[j] = pool[j], pool[i]
        end
        local n_items = 7 + math.random(0, 3)
        for i = 1, math.min(n_items, #pool) do
            local px, py, pz = rand_pos()
            place_item_at(px, py, pz, pool[i][1], pool[i][2], pool[i][3])
        end
        -- 3-4 gem types, each batch at a different random floor tile.
        local gem_pool = {}
        for _, v in ipairs(GEM_POOL) do table.insert(gem_pool, v) end
        for i = #gem_pool, 2, -1 do
            local j = math.random(i)
            gem_pool[i], gem_pool[j] = gem_pool[j], gem_pool[i]
        end
        local n_gems = 3 + math.random(0, 1)
        for i = 1, math.min(n_gems, #gem_pool) do
            local gem = gem_pool[i]
            local px, py, pz = rand_pos()
            if place_item_at(px, py, pz, "SMALLGEM", gem[1], 3) == 0 then
                local px2, py2, pz2 = rand_pos()
                place_item_at(px2, py2, pz2, "SMALLGEM", gem[2], 3)
            end
        end
        log.info("Treasure cave stocked with hoard scattered across floor")
    end
end

-- Secret cave helpers

-- Spawn one creature of the given race token at (x,y,z).
-- Pass hostile=true to mark as active invader/marauder (for trap creatures).
-- Returns true on success.
function M.spawn_unit(race_token, x, y, z, hostile)
    local race_idx = nil
    for i = 0, #df.global.world.raws.creatures.all - 1 do
        if df.global.world.raws.creatures.all[i].creature_id == race_token then
            race_idx = i; break
        end
    end
    if not race_idx then return false end
    local ok = pcall(function()
        local u = dfhack.units.create(race_idx, 0)
        if not u then error("create returned nil") end
        if not dfhack.units.teleport(u, {x=x, y=y, z=z}) then
            u.pos.x, u.pos.y, u.pos.z = x, y, z
        end
        df.global.world.units.active:insert('#', u)
        pcall(function() u.civ_id = -1 end)
        if hostile then
            pcall(function() u.flags1.active_invader = true end)
            pcall(function() u.flags1.marauder       = true end)
        end
    end)
    return ok
end

-- Place a gold (or silver) coffin at (x,y,z) and register it as an artifact
-- named "Karl" so it displays as "Karl the Gold Coffin" in-game.
local function place_karls_coffin(x, y, z)
    local pre_n = #df.global.world.items.all
    if place_item_at(x, y, z, "COFFIN", "INORGANIC:GOLD",     1) == 0 then
        if place_item_at(x, y, z, "COFFIN", "INORGANIC:SILVER",   1) == 0 then
            place_item_at(x, y, z, "COFFIN", "INORGANIC:PLATINUM", 1)
        end
    end
    pcall(function()
        local all  = df.global.world.items.all
        if #all <= pre_n then return end
        -- The newly created item is appended; search from pre_n forward for a COFFIN.
        local item = nil
        for i = pre_n, #all - 1 do
            local it = all[i]
            local ok, match = pcall(function() return it:getType() == df.item_type.COFFIN end)
            if ok and match then item = it; break end
        end
        if not item then return end

        local arts   = df.global.world.artifacts
        local new_id = #arts.all

        -- Register the artifact record first (mirrors spawn_artifact_door pattern).
        local ar = df.artifact_record:new()
        ar.id      = new_id
        ar.item    = item      -- item pointer, NOT item.id
        ar.unit_id = -1
        pcall(function() ar.mystery = false end)
        ar.name.has_name   = true
        ar.name.first_name = "Karl"
        arts.all:insert('#', ar)

        -- Add back-reference from item to artifact so DF shows the artifact name.
        local ref = df.general_ref_is_artifactst:new()
        ref.artifact_id = new_id
        item.general_refs:insert('#', ref)
        item.flags.artifact = true
        item.quality = df.item_quality.Artifact

        log.info("Karl's Coffin artifact registered (id=" .. ar.id .. ")")
    end)
end

-- Helpers

local function read_int(key)
    return tonumber(dfhack.persistent.getWorldDataString(key))
end

local function cavern_ceil(name)
    return read_int("dwarfipelago/mining/ceiling/" .. name)
end

local function cave_key(idx, field)
    return KEY_PREFIX .. idx .. "/" .. field
end

-- True iff (x,y,z) has the WALL shape (unbroken solid rock).
local function is_solid_wall(x, y, z)
    local ok, result = pcall(function()
        local tt = dfhack.maps.getTileType(x, y, z)
        if not tt then return false end
        local shape = df.tiletype_shape[df.tiletype.attrs[tt].shape]
        return shape == "WALL"
    end)
    return ok and result
end

-- Returns true if the area around (cx,cy,cz) is entirely solid walls.
-- Checks +/-9 in x/y (cave max-radius 8 + 1-tile border) and 0..4 in z
-- (floor + up to 2 open tiles + 2-tile solid ceiling margin).
local function site_ok(cx, cy, cz)
    for dx = -9, 9 do
        for dy = -9, 9 do
            for dz = 0, 4 do
                if not is_solid_wall(cx + dx, cy + dy, cz + dz) then return false end
            end
        end
    end
    return true
end

-- Change a single tile type and flush the block.
local function set_tile(x, y, z, tt)
    pcall(function()
        local b = dfhack.maps.getTileBlock(x, y, z)
        if not b then return end
        local lx, ly = x % 16, y % 16
        b.tiletype[lx][ly] = tt
        pcall(function()
            b.designation[lx][ly].feature_local  = false
            b.designation[lx][ly].feature_global = false
        end)
        dfhack.maps.enableBlockUpdates(b, false, false)
    end)
end

-- Hollow out an organic oval pocket centred on (cx,cy,cz).
-- Radii default to rx in [5,8] and ry in [4,6]; pass explicit values for a
-- fixed size (e.g. carve(x,y,z, 2,2) for a small spider-cave circle).
-- Edge tiles (ellipse dist^2 0.7-1.1) are included with linearly-falling
-- probability, giving a ragged, natural silhouette.
-- Height: 3 z-levels (floor + 2 open) in the inner half, 2 z-levels at edges.
-- Returns the list of {x,y} floor tile positions for use by stock_cave.
local function carve(cx, cy, cz, rx_in, ry_in)
    local rx = rx_in or math.random(5, 8)
    local ry = ry_in or math.random(4, 6)
    local floor_tiles = {}
    for dx = -(rx + 1), rx + 1 do
        for dy = -(ry + 1), ry + 1 do
            local dist2 = (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry)
            local include
            if dist2 < 0.7 then
                include = true
            elseif dist2 < 1.1 then
                -- Probability 100%->0% as dist2 crosses 0.7->1.1
                include = math.random(100) <= math.floor(100 * (1.1 - dist2) / 0.4)
            else
                include = false
            end
            if include then
                set_tile(cx + dx, cy + dy, cz,     TT_ROCK_FLOOR)
                set_tile(cx + dx, cy + dy, cz + 1, TT_OPEN_SPACE)
                if dist2 < 0.5 then
                    set_tile(cx + dx, cy + dy, cz + 2, TT_OPEN_SPACE)
                end
                table.insert(floor_tiles, {x = cx + dx, y = cy + dy})
            end
        end
    end
    return floor_tiles
end

-- Anchor positions for each cave, spread across map quadrants so caves in
-- different depth gaps never search the same starting region.
-- Indices 1-6 are AP caves; 7-8 are the two secret world caves.
local CAVE_ANCHORS = {
    {x=0.20, y=0.20},  -- 1: NW
    {x=0.75, y=0.75},  -- 2: SE
    {x=0.75, y=0.20},  -- 3: NE
    {x=0.20, y=0.75},  -- 4: SW
    {x=0.48, y=0.30},  -- 5: N-center
    {x=0.48, y=0.65},  -- 6: S-center
    {x=0.30, y=0.48},  -- 7: W-center  (spider silk secret)
    {x=0.65, y=0.48},  -- 8: E-center  (Karl's Coffin secret)
}

-- Find a suitable cave site in the z-range [z_lo, z_hi] (z_hi > z_lo = shallower).
-- `cave_idx` is the global cave number (1-8) used to pick a unique map anchor so
-- no two caves ever search the same x/y region regardless of which gap they occupy.
local function find_site(z_hi, z_lo, cave_idx)
    local margin = 5
    local lo = z_lo + margin
    local hi = z_hi - margin
    if lo >= hi then return nil end

    local map_w = df.global.world.map.x_count
    local map_h = df.global.world.map.y_count

    local anchor = CAVE_ANCHORS[cave_idx] or CAVE_ANCHORS[1]
    local base_x = math.floor(map_w * anchor.x)
    local base_y = math.floor(map_h * anchor.y)
    -- Spread caves proportionally through the gap rather than clustering at midpoint.
    -- Even cave_idx (1-indexed) goes in the upper third, odd goes in the lower third.
    local within_gap = (cave_idx - 1) % 2          -- 0 = first of pair, 1 = second
    local z_frac     = 0.30 + within_gap * 0.40    -- 0.30 or 0.70
    local z          = math.floor(lo + (hi - lo) * z_frac)

    for attempt = 0, 50 do
        local x = math.max(8, math.min(map_w - 9, base_x + (attempt * 7)  % 50))
        local y = math.max(8, math.min(map_h - 9, base_y + (attempt * 11) % 50))
        if site_ok(x, y, z) then return x, y, z end
    end
    return nil
end

-- Public API

-- Generate and carve all AP custom caves on a fresh seed.  No-ops if already
-- done or cavern ceilings haven't been computed yet.
-- Called from poll_checks() in dwarfipelago.lua after compute_cavern_ceilings().
function M.generate()
    if dfhack.persistent.getWorldDataString(KEY_DONE) == "1" then return end
    if dfhack.persistent.getWorldDataString("dwarfipelago/mining/ceilings_done") ~= "1" then return end

    local surface_z = read_int("dwarfipelago/mining/surface_z")
        or (df.global.world.map.z_count - 10)

    local c1 = cavern_ceil("cavern1")
    local c2 = cavern_ceil("cavern2")
    local c3 = cavern_ceil("cavern3")

    -- Build inter-layer gaps: {hi, lo} where hi > lo (hi = shallower z).
    local gaps = {}
    if c1 then table.insert(gaps, {hi = surface_z - 5, lo = c1 + 5}) end
    if c1 and c2 then table.insert(gaps, {hi = c1 - 5,      lo = c2 + 5}) end
    if c2 and c3 then table.insert(gaps, {hi = c2 - 5,      lo = c3 + 5}) end
    if #gaps == 0 then
        local mid = math.floor(df.global.world.map.z_count / 2)
        table.insert(gaps, {hi = mid + 20, lo = mid - 20})
    end

    -- Alternate treasure/trap so each pair of caves has one of each.
    local cave_types = {"treasure", "trap", "treasure", "trap", "treasure", "trap"}
    local cave_idx   = 1

    for gap_i, gap in ipairs(gaps) do
        for _ = 1, 2 do
            if cave_idx > NUM_CAVES then break end
            local x, y, z = find_site(gap.hi, gap.lo, cave_idx)
            local cave_type = cave_types[cave_idx]
            if x then
                local floor_tiles = carve(x, y, z)
                stock_cave(x, y, z, cave_type, floor_tiles)
                dfhack.persistent.saveWorldDataString(cave_key(cave_idx, "x"),    tostring(x))
                dfhack.persistent.saveWorldDataString(cave_key(cave_idx, "y"),    tostring(y))
                dfhack.persistent.saveWorldDataString(cave_key(cave_idx, "z"),    tostring(z))
                dfhack.persistent.saveWorldDataString(cave_key(cave_idx, "type"), cave_type)
                log.info(("Custom cave #%d (%s) at (%d,%d,%d)"):format(cave_idx, cave_type, x, y, z))
            else
                -- Mark as invalid so Python skips this slot cleanly.
                dfhack.persistent.saveWorldDataString(cave_key(cave_idx, "x"), "-1")
                log.warn(("Custom cave #%d: no suitable site in gap %d"):format(cave_idx, gap_i))
            end
            dfhack.persistent.saveWorldDataString(cave_key(cave_idx, "discovered"), "0")
            dfhack.persistent.saveWorldDataString(cave_key(cave_idx, "revealed"),   "0")
            cave_idx = cave_idx + 1
        end
    end

    -- Pad any remaining slots (< 3 gaps) with null entries for consistent indexing.
    while cave_idx <= NUM_CAVES do
        dfhack.persistent.saveWorldDataString(cave_key(cave_idx, "x"),          "-1")
        dfhack.persistent.saveWorldDataString(cave_key(cave_idx, "discovered"), "0")
        dfhack.persistent.saveWorldDataString(cave_key(cave_idx, "revealed"),   "0")
        cave_idx = cave_idx + 1
    end

    dfhack.persistent.saveWorldDataString(KEY_DONE, "1")
    log.info("Custom cave generation complete")
end

-- Check whether any living citizen is standing inside an undiscovered cave.
-- Returns a list of {index, cave_type, x, y, z} for newly-discovered caves
-- and marks each as discovered in persistent storage.
-- Called from the poll loop in dwarfipelago.lua.
function M.check_discoveries()
    if dfhack.persistent.getWorldDataString(KEY_DONE) ~= "1" then return {} end

    -- Collect undiscovered caves.
    local pending = {}
    for i = 1, NUM_CAVES do
        local x = tonumber(dfhack.persistent.getWorldDataString(cave_key(i, "x")))
        if x and x > 0 then
            if dfhack.persistent.getWorldDataString(cave_key(i, "discovered")) ~= "1" then
                pending[i] = {
                    x         = x,
                    y         = tonumber(dfhack.persistent.getWorldDataString(cave_key(i, "y"))),
                    z         = tonumber(dfhack.persistent.getWorldDataString(cave_key(i, "z"))),
                    cave_type = dfhack.persistent.getWorldDataString(cave_key(i, "type")) or "treasure",
                }
            end
        end
    end
    if not next(pending) then return {} end

    -- Build a lookup of all citizen positions (expanded by 2 tiles for edge detection).
    local occupied = {}
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
            for dx = -2, 2 do
                for dy = -2, 2 do
                    occupied[(unit.pos.x + dx) .. "," .. (unit.pos.y + dy) .. "," .. unit.pos.z] = true
                end
            end
        end
    end

    local newly = {}
    for idx, cave in pairs(pending) do
        local found = false
        for dx = -2, 2 do
            if found then break end
            for dy = -2, 2 do
                if occupied[(cave.x + dx) .. "," .. (cave.y + dy) .. "," .. cave.z] then
                    found = true; break
                end
            end
        end
        if found then
            dfhack.persistent.saveWorldDataString(cave_key(idx, "discovered"), "1")
            table.insert(newly, {index=idx, cave_type=cave.cave_type, x=cave.x, y=cave.y, z=cave.z})
        end
    end
    return newly
end

-- Return a displayable hint string for cave `idx`.
function M.get_hint(idx)
    local x  = tonumber(dfhack.persistent.getWorldDataString(cave_key(idx, "x")))
    if not x or x < 0 then return "The fragment is too worn to read." end
    local y  = tonumber(dfhack.persistent.getWorldDataString(cave_key(idx, "y")))
    local z  = tonumber(dfhack.persistent.getWorldDataString(cave_key(idx, "z")))
    local ct = dfhack.persistent.getWorldDataString(cave_key(idx, "type")) or "treasure"

    if ct == "trap" then
        local map_w = df.global.world.map.x_count
        local map_h = df.global.world.map.y_count
        local rx = x - math.floor(map_w / 2)
        local ry = y - math.floor(map_h / 2)
        local dir = (math.abs(rx) >= math.abs(ry))
            and (rx >= 0 and "east" or "west")
            or  (ry >= 0 and "south" or "north")
        return ("Danger lurks to the %s, deep underground (z=%d). Tread carefully!"):format(dir, z)
    else
        return ("Riches await at approximately (%d, %d), %d levels underground."):format(x, y, z)
    end
end

-- True once every generated cave has already been discovered (walked into by
-- a citizen), regardless of how many Cave Map Fragments have been received.
function M.all_discovered()
    for i = 1, NUM_CAVES do
        if dfhack.persistent.getWorldDataString(cave_key(i, "discovered")) ~= "1" then
            return false
        end
    end
    return true
end

-- Reveal the next unrevealed cave hint when a Cave Map Fragment is received.
-- Cave discovery isn't gated behind receiving fragments, so a player can find
-- every cave on their own before all fragments arrive - at that point a
-- fragment has nothing left to reveal and is just flavor.
function M.reveal_next()
    if M.all_discovered() then
        dfhack.gui.showAnnouncement(
            "[AP] Cave Map Fragment: just a stack of old paper - every cave has already been found.",
            COLOR_YELLOW, false)
        return
    end
    local next_idx = (tonumber(dfhack.persistent.getWorldDataString(KEY_FRAG_IDX)) or 0) + 1
    if next_idx > NUM_CAVES then
        dfhack.gui.showAnnouncement(
            "[AP] Cave Map Fragment: all known caves have already been revealed.",
            COLOR_YELLOW, false)
        return
    end
    local hint = M.get_hint(next_idx)
    dfhack.persistent.saveWorldDataString(KEY_FRAG_IDX, tostring(next_idx))
    dfhack.gui.showAnnouncement(
        ("[AP] Cave Map Fragment #%d: %s"):format(next_idx, hint),
        COLOR_CYAN, true)
    print(("[Dwarfipelago] Map fragment #%d: %s"):format(next_idx, hint))
end

-- Generate the two secret world-flavour caves.  Always generated alongside the
-- AP caves.  No-ops if already done or ceilings not measured yet.
--
--   Secret 1 - Spider Silk Cave (surface -> cavern 1 gap, slot 3 / SW quadrant):
--     Small oval (rx=2, ry=2).  3 wild cave spiders spawn at generation time;
--     they spin silk webs as they roam, giving dwarves a silk thread source before
--     the first cavern is breached.
--
--   Secret 2 - Karl's Coffin Cave (cavern 1 -> cavern 2 gap, slot 4 / NE quadrant):
--     Standard organic oval.  Contains a gold coffin registered as the artifact
--     "Karl" - displayed in-game as "Karl the Gold Coffin".  Stupid, but valuable.
function M.generate_secret_caves()
    if dfhack.persistent.getWorldDataString(KEY_SECRETS_DONE) == "1" then return end
    if dfhack.persistent.getWorldDataString("dwarfipelago/mining/ceilings_done") ~= "1" then return end

    local surface_z = read_int("dwarfipelago/mining/surface_z")
        or (df.global.world.map.z_count - 10)
    local c1 = cavern_ceil("cavern1")
    local c2 = cavern_ceil("cavern2")

    -- Secret 1: spider silk cave in the surface -> cavern 1 gap.
    if c1 then
        local x, y, z = find_site(surface_z - 5, c1 + 5, 7)
        if x then
            carve(x, y, z, 2, 2)
            local n = 0
            for _ = 1, 3 do
                if M.spawn_unit("SPIDER_CAVE", x, y, z, false) then n = n + 1 end
            end
            dfhack.persistent.saveWorldDataString(KEY_SECRET1 .. "x", tostring(x))
            dfhack.persistent.saveWorldDataString(KEY_SECRET1 .. "y", tostring(y))
            dfhack.persistent.saveWorldDataString(KEY_SECRET1 .. "z", tostring(z))
            log.info(("Secret cave 1 (spider silk) at (%d,%d,%d), %d spiders"):format(x, y, z, n))
        else
            log.warn("Secret cave 1 (spider silk): no suitable site found in surface->C1 gap")
        end
    end

    -- Secret 2: Karl's Coffin cave in the cavern 1 -> cavern 2 gap.
    if c1 and c2 then
        local x, y, z = find_site(c1 - 5, c2 + 5, 8)
        if x then
            carve(x, y, z)
            place_karls_coffin(x, y, z)
            dfhack.persistent.saveWorldDataString(KEY_SECRET2 .. "x", tostring(x))
            dfhack.persistent.saveWorldDataString(KEY_SECRET2 .. "y", tostring(y))
            dfhack.persistent.saveWorldDataString(KEY_SECRET2 .. "z", tostring(z))
            log.info(("Secret cave 2 (Karl's Coffin) at (%d,%d,%d)"):format(x, y, z))
        else
            log.warn("Secret cave 2 (Karl's Coffin): no suitable site found in C1->C2 gap")
        end
    end

    dfhack.persistent.saveWorldDataString(KEY_SECRETS_DONE, "1")
    log.info("Secret cave generation complete")
end

-- Copy all module exports into _ENV so reqscript callers can access them.
for k, v in pairs(M) do _ENV[k] = v end
return M
