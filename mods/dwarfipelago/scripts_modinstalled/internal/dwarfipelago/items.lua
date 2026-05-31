--@ module = true
-- Item spawning for Dwarfipelago.
-- Called when the AP client delivers an item to the fortress.
-- Each handler uses dfhack.run_script or direct df API calls to apply the effect.

local M = {}

-- ── Helpers ───────────────────────────────────────────────────────────────────

-- Return the center tile of the first trade depot in the fortress, or nil.
-- The depot is 5×5; (x1+2, y1+2) is its center tile.
local function find_trade_depot_center()
    for _, bld in ipairs(df.global.world.buildings.all) do
        if df.building_tradedepotst:is_instance(bld) then
            return bld.x1 + 2, bld.y1 + 2, bld.z
        end
    end
    return nil
end

-- Spawn items at the trade depot (the designated AP delivery point).
-- Falls back to a living citizen's tile if no depot exists yet.
-- createitem places items at the keyboard cursor, so we set the cursor first.
local function spawn_item(item_type, material, quantity)
    quantity = quantity or 1

    -- Prefer the trade depot center; fall back to any living citizen.
    local cx, cy, cz = find_trade_depot_center()
    if cx then
        df.global.cursor.x = cx
        df.global.cursor.y = cy
        df.global.cursor.z = cz
    else
        local anchored = false
        for _, unit in ipairs(df.global.world.units.active) do
            if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
                df.global.cursor.x = unit.pos.x
                df.global.cursor.y = unit.pos.y
                df.global.cursor.z = unit.pos.z
                anchored = true
                break
            end
        end
        if not anchored then
            dfhack.printerr("[Dwarfipelago] spawn_item: no depot or citizen — cannot place " .. item_type)
            return
        end
    end

    for _ = 1, quantity do
        -- createitem is a DFHack plugin command; use run_command, not run_script.
        -- e.g. createitem SMALLGEM INORGANIC:RUBY
        local ok, err = pcall(function()
            dfhack.run_command("createitem", item_type, material)
        end)
        if not ok then
            dfhack.printerr("[Dwarfipelago] Failed to spawn " .. item_type .. ": " .. tostring(err))
        end
    end
end

local function announce(msg)
    dfhack.gui.showAnnouncement("[AP] " .. msg, COLOR_GREEN, true)
end

-- Return the position of a living citizen as a spawn anchor (guaranteed walkable).
-- Falls back to map centre if no citizens are found.
local function get_fort_spawn_pos()
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
            return tostring(unit.pos.x), tostring(unit.pos.y), tostring(unit.pos.z)
        end
    end
    local map = df.global.world.map
    return tostring(math.floor(map.x_count / 2)),
           tostring(math.floor(map.y_count / 2)),
           tostring(map.z_count - 1)
end

-- Find the entity ID of a goblin civilisation in the world so spawned goblins
-- belong to an enemy faction. Returns -1 if none found (e.g. goblin-free worlds).
local function find_goblin_civ_id()
    local creatures = df.global.world.raws.creatures.all
    for _, ent in ipairs(df.global.world.entities.all) do
        local ok, id = pcall(function()
            if ent.race >= 0 and ent.race < #creatures then
                if creatures[ent.race].creature_id == "GOBLIN" then
                    return ent.id
                end
            end
        end)
        if ok and id then return id end
    end
    return -1
end

-- ── Item handlers: trade goods ────────────────────────────────────────────────
-- createitem syntax: <item-token> <material>
--   Cut gems  → SMALLGEM INORGANIC:<gem>   (SMALLGEM = cut gem; ROUGH = uncut)
--   Metal bars → BAR INORGANIC:<metal>
--   Figurines  → FIGURINE INORGANIC:<stone>

local function recv_cut_sapphire()
    spawn_item("SMALLGEM", "INORGANIC:SAPPHIRE")
    announce("Received: Cut Sapphire!")
end

local function recv_cut_ruby()
    spawn_item("SMALLGEM", "INORGANIC:RUBY")
    announce("Received: Cut Ruby!")
end

local function recv_cut_diamond()
    spawn_item("SMALLGEM", "INORGANIC:DIAMOND")
    announce("Received: Cut Diamond!")
end

local function recv_gold_bar()
    spawn_item("BAR", "INORGANIC:GOLD")
    announce("Received: Gold Bar!")
end

local function recv_silver_bar()
    spawn_item("BAR", "INORGANIC:SILVER")
    announce("Received: Silver Bar!")
end

local function recv_steel_bar()
    spawn_item("BAR", "INORGANIC:STEEL")
    announce("Received: Steel Bar!")
end

local function recv_masterwork_craft()
    -- FIGURINE is the correct item token for a craft figurine.
    spawn_item("FIGURINE", "INORGANIC:OBSIDIAN")
    announce("Received: Masterwork Craft!")
end

-- ── Item handlers: resources ──────────────────────────────────────────────────
-- createitem syntax:
--   Food (edible growths) → PLANT_GROWTH PLANT:<plant>:<growth>
--   Wood logs             → WOOD PLANT_MAT:<tree>:WOOD
--   Iron ore boulders     → BOULDER INORGANIC:<ore>
--   Fuel bars             → BAR COAL:COKE  (or COAL:CHARCOAL)

local function recv_food_bundle()
    for _ = 1, 5 do
        spawn_item("PLANT_GROWTH", "PLANT:MUSHROOM_HELMET_PLUMP:MUSHROOM")
    end
    announce("Received: Food Bundle (5 plump helmets)!")
end

local function recv_wood_bundle()
    for _ = 1, 5 do
        spawn_item("WOOD", "PLANT_MAT:OAK:WOOD")
    end
    announce("Received: Wood Bundle (5 logs)!")
end

local function recv_iron_ore_bundle()
    for _ = 1, 5 do
        spawn_item("BOULDER", "INORGANIC:LIMONITE")
    end
    announce("Received: Iron Ore Bundle!")
end

local function recv_coal_bundle()
    for _ = 1, 3 do
        spawn_item("BAR", "COAL:COKE")
    end
    announce("Received: Coal Bundle!")
end

-- ── Item handlers: traps ──────────────────────────────────────────────────────

local function recv_goblin_ambush()
    announce("Trap: Goblin Ambush incoming!")
    -- Spawn 3 hostile goblins via modtools/create-unit.
    -- -location is required; we anchor to a living citizen's tile.
    -- Goblins are assigned to their civilisation's civ ID so they are treated as
    -- enemies. -setUnitToFort is intentionally NOT used — that would make them
    -- friendly fortress members instead of raiders.
    local x, y, z   = get_fort_spawn_pos()
    local civ_id_str = tostring(find_goblin_civ_id())
    local ok, err = pcall(function()
        for _ = 1, 3 do
            dfhack.run_script("modtools/create-unit",
                "-race",     "GOBLIN",
                "-civId",    civ_id_str,
                "-groupId",  "-1",
                "-location", "[", x, y, z, "]"
            )
        end
    end)
    if not ok then
        dfhack.printerr("[Dwarfipelago] goblin_ambush spawn failed: " .. tostring(err))
    end
end

local function recv_cave_bear()
    announce("Trap: A Cave Bear has found its way in!")
    -- Wild (civId=-1) cave bear — wild animals attack dwarves on sight.
    -- -setUnitToFort is intentionally NOT used as that would tame the bear.
    local x, y, z = get_fort_spawn_pos()
    local ok, err = pcall(function()
        dfhack.run_script("modtools/create-unit",
            "-race",     "CAVE_BEAR",
            "-civId",    "-1",
            "-groupId",  "-1",
            "-location", "[", x, y, z, "]"
        )
    end)
    if not ok then
        dfhack.printerr("[Dwarfipelago] cave_bear spawn failed: " .. tostring(err))
    end
end

local function recv_vermin_infestation()
    announce("Trap: Vermin Infestation! Giant rats everywhere!")
    -- RAT is a [VERMIN_SOIL] creature and cannot be spawned as a full unit.
    -- GIANT_RAT is a proper hostile creature that serves the same narrative role.
    -- Wild (civId=-1) so they attack dwarves. Spread across a 10-tile radius.
    local x, y, z = get_fort_spawn_pos()
    local spawned = 0
    for _ = 1, 10 do
        local ok = pcall(function()
            dfhack.run_script("modtools/create-unit",
                "-race",          "GIANT_RAT",
                "-civId",         "-1",
                "-groupId",       "-1",
                "-location",      "[", x, y, z, "]",
                "-locationRange", "[", "10", "10", "0", "]"
            )
        end)
        if ok then spawned = spawned + 1 end
    end
    if spawned == 0 then
        dfhack.printerr("[Dwarfipelago] vermin_infestation: could not spawn any giant rats")
    end
end

local function recv_tantrum_trigger()
    -- Push the most-stressed living citizen past the tantrum threshold.
    -- The tantrum threshold in DF is ~200,000 stress; 500,000 is well past it.
    local target = nil
    local highest_stress = -math.huge
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit)
            and dfhack.units.isAlive(unit)
            and unit.status.current_soul
        then
            local stress = unit.status.current_soul.personality.stress
            if stress > highest_stress then
                highest_stress = stress
                target = unit
            end
        end
    end
    if target and target.status.current_soul then
        target.status.current_soul.personality.stress = 500000
        local name = dfhack.TranslateName(dfhack.units.getVisibleName(target))
        announce("Trap: " .. (name ~= "" and name or "A dwarf") .. " has had enough!")
    else
        -- No eligible dwarf found (e.g. very early embark with no stress data).
        announce("Trap: Something sinister stirs in the fortress...")
        dfhack.printerr("[Dwarfipelago] tantrum_trigger: no eligible citizen found")
    end
end

local function recv_lost_caravan()
    -- Flag that the next caravan should be skipped / arrive empty.
    dfhack.persistent.saveWorldDataString("dwarfipelago/trap/lost_caravan", "1")
    announce("Trap: A caravan has been lost on the road...")
end

-- ── Megabeast spawn helpers ───────────────────────────────────────────────────

-- Search for an open, non-surface floor tile well below ground.
-- Randomly samples positions across multiple z-levels so it handles any
-- embark layout without a full tile scan. Returns x, y, z or nil.
local function find_underground_spawn()
    if not dfhack.isMapLoaded() then return nil end
    local map = df.global.world.map

    -- Estimate surface z from a living citizen (fallback: upper 40% of map).
    local surface_z = math.floor(map.z_count * 0.6)
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
            surface_z = unit.pos.z
            break
        end
    end

    local z_high = math.max(2, surface_z - 10)
    local z_low  = math.max(2, surface_z - 40)

    for z = z_high, z_low, -1 do
        for _ = 1, 30 do
            local x = math.random(5, map.x_count - 6)
            local y = math.random(5, map.y_count - 6)
            local block = dfhack.maps.getTileBlock(x, y, z)
            if block then
                local lx, ly = x % 16, y % 16
                local shape  = df.tiletype.attrs[block.tiletype[lx][ly]].shape
                if shape == df.tiletype_shape.FLOOR
                        and not block.designation[lx][ly].outside then
                    return x, y, z
                end
            end
        end
    end
    return nil
end

-- Carve a 5×5 area of floor tiles around the spawn point and reveal hidden tiles
-- so the breach looks like the beast smashed its way through.
local function carve_breach(cx, cy, cz)
    for dx = -2, 2 do
        for dy = -2, 2 do
            local nx, ny = cx + dx, cy + dy
            local block = dfhack.maps.getTileBlock(nx, ny, cz)
            if block then
                local lx, ly = nx % 16, ny % 16
                local tt    = block.tiletype[lx][ly]
                local shape = df.tiletype.attrs[tt].shape
                if shape ~= df.tiletype_shape.FLOOR and shape ~= df.tiletype_shape.OPEN then
                    local floor_tt = dfhack.maps.findSimilarTileType(tt, df.tiletype_shape.FLOOR)
                    if floor_tt and floor_tt ~= 0 then
                        block.tiletype[lx][ly] = floor_tt
                    end
                end
                block.designation[lx][ly].hidden = false
            end
        end
    end
    local b = dfhack.maps.getTileBlock(cx, cy, cz)
    if b then dfhack.maps.enableBlockUpdates(b, true) end
end

-- Map a spawn tile position to a compass direction relative to the embark centre.
-- Returns one of 8 directional strings, or "depths" if very close to centre.
local function get_spawn_direction(sx, sy)
    local map = df.global.world.map
    local dx  = sx - (map.x_count / 2)
    local dy  = sy - (map.y_count / 2)  -- positive y = south in DF
    if math.abs(dx) < 4 and math.abs(dy) < 4 then return "depths" end
    local angle = (math.deg(math.atan2(dy, dx)) + 360) % 360
    -- 0=E 45=SE 90=S 135=SW 180=W 225=NW 270=N 315=NE
    local dirs = { "eastern", "southeastern", "southern", "southwestern",
                   "western", "northwestern", "northern", "northeastern" }
    return dirs[math.floor((angle + 22.5) / 45) % 8 + 1]
end

-- Scan creature raws for a random megabeast type present in this world.
local function pick_megabeast_type()
    local candidates = {}
    for _, creature in ipairs(df.global.world.raws.creatures.all) do
        for _, caste in ipairs(creature.caste) do
            if caste.flags.MEGABEAST then
                table.insert(candidates, creature.creature_id)
                break
            end
        end
    end
    return #candidates > 0 and candidates[math.random(#candidates)] or "DRAGON"
end

-- Spawn a precursor threat (giant cave spider) underground as a Training 2 warm-up.
local function spawn_precursor_threat()
    local x, y, z = find_underground_spawn()
    if not x then
        local sx, sy, sz = get_fort_spawn_pos()
        x, y, z = tonumber(sx), tonumber(sy), tonumber(sz)
        dfhack.gui.showAnnouncement(
            "[AP] Warning: no underground tile found — precursor spawned at surface instead.",
            COLOR_YELLOW, true)
        dfhack.printerr("[Dwarfipelago] spawn_precursor_threat: underground search failed, falling back to surface")
    end
    local ok, err = pcall(function()
        dfhack.run_script("modtools/create-unit",
            "-race", "GIANT_CAVE_SPIDER", "-civId", "-1", "-groupId", "-1",
            "-location", "[", tostring(x), tostring(y), tostring(z), "]")
    end)
    if not ok then
        dfhack.gui.showAnnouncement(
            "[AP] Error: precursor creature could not be spawned. Check the DFHack console.",
            COLOR_RED, true)
        dfhack.printerr("[Dwarfipelago] precursor spawn failed: " .. tostring(err))
    end
end

-- Spawn the AP-controlled megabeast target. Picks a random type from the world's
-- raws, finds an underground tile, spawns there, carves a breach, and stores the
-- new unit's ID so only that specific kill triggers victory.
local function spawn_target_megabeast()
    if dfhack.persistent.getWorldDataString("dwarfipelago/megabeast/spawned") == "1" then
        return  -- already summoned this world (e.g. reloaded mid-session)
    end

    local x, y, z = find_underground_spawn()
    if not x then
        local sx, sy, sz = get_fort_spawn_pos()
        x, y, z = tonumber(sx), tonumber(sy), tonumber(sz)
        dfhack.gui.showAnnouncement(
            "[AP] Warning: no underground tile found — megabeast spawned at surface level.",
            COLOR_YELLOW, true)
        dfhack.printerr("[Dwarfipelago] spawn_target_megabeast: underground search failed, falling back to surface")
    end

    local beast_type = pick_megabeast_type()
    dfhack.persistent.saveWorldDataString("dwarfipelago/megabeast/target_type", beast_type)

    local pre_count = #df.global.world.units.all
    local ok, err = pcall(function()
        dfhack.run_script("modtools/create-unit",
            "-race", beast_type, "-civId", "-1", "-groupId", "-1",
            "-location", "[", tostring(x), tostring(y), tostring(z), "]")
    end)
    if not ok then
        dfhack.gui.showAnnouncement(
            "[AP] CRITICAL: Megabeast could not be spawned — the Slay Megabeast goal cannot be completed.",
            COLOR_RED, true)
        dfhack.gui.showAnnouncement(
            "[AP] This is likely a DFHack or mod compatibility issue. Consider regenerating your world.",
            COLOR_RED, true)
        dfhack.printerr("[Dwarfipelago] megabeast spawn failed: " .. tostring(err))
        return
    end

    -- Identify the newly added unit and persist its ID for targeted kill detection.
    for i = pre_count, #df.global.world.units.all - 1 do
        local u = df.global.world.units.all[i]
        if u then
            local ok2, is_mega = pcall(dfhack.units.isMegabeast, u)
            if ok2 and is_mega then
                dfhack.persistent.saveWorldDataString(
                    "dwarfipelago/megabeast/target_id", tostring(u.id))
                break
            end
        end
    end

    dfhack.persistent.saveWorldDataString("dwarfipelago/megabeast/spawned", "1")

    local display = beast_type:gsub("_", " "):lower():gsub("^%l", string.upper)
    local dir     = get_spawn_direction(x, y)
    dfhack.gui.showAnnouncement(
        ("[AP] A deep tremor rolls through the %s stone... a %s has awakened. Hunt it down."):format(dir, display),
        COLOR_RED, true)
    print(("[Dwarfipelago] Megabeast spawned: %s at %d,%d,%d (direction: %s)"):format(beast_type, x, y, z, dir))
end

-- ── Item handlers: progression locks ─────────────────────────────────────────

local function recv_merchants_coffer()
    local key = "dwarfipelago/unlock/wealth_coffers"
    local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
    dfhack.persistent.saveWorldDataString(key, tostring(n))
    announce(("Merchant's Coffer received! Wealth tier %d/5 unlocked"):format(n))
end

local function recv_immigration_wave()
    local key = "dwarfipelago/unlock/immigration_waves"
    local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
    dfhack.persistent.saveWorldDataString(key, tostring(n))
    announce(("Immigration Wave received! Population tier %d/5 unlocked"):format(n))
end

local function recv_barons_charter()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/baron_charter", "1")
    announce("Baron's Charter received! Baron appointment is now recognisable.")
end

local function recv_counts_charter()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/count_charter", "1")
    announce("Count's Charter received! Count appointment is now recognisable.")
end

local function recv_dukes_charter()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/duke_charter", "1")
    announce("Duke's Charter received! Duke appointment is now recognisable.")
end

local function recv_monarchs_invitation()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/monarch_invitation", "1")
    announce("Monarch's Invitation received! The Monarch may now take residence.")
end

local function recv_military_training()
    local key = "dwarfipelago/unlock/military_training"
    local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
    dfhack.persistent.saveWorldDataString(key, tostring(n))

    if n == 1 then
        announce("Military Training received! Ancient combat techniques studied... (1/3)")
        dfhack.gui.showAnnouncement(
            "[AP] A deep rumbling echoes from below. Something has noticed your fortress.",
            COLOR_YELLOW, true)
    elseif n == 2 then
        announce("Military Training received! Your soldiers sharpen their blades... (2/3)")
        dfhack.gui.showAnnouncement(
            "[AP] A creature stirs in the tunnels — a precursor to something far worse.",
            COLOR_YELLOW, true)
        spawn_precursor_threat()
    else
        announce("Military Training received! Your military is ready — the beast awakens! (3/3)")
        spawn_target_megabeast()
    end
end

-- ── Dispatch table ────────────────────────────────────────────────────────────
-- Maps AP item name → handler function.
-- Names must match items.py exactly.

M.handlers = {
    ["Cut Sapphire"]         = recv_cut_sapphire,
    ["Cut Ruby"]             = recv_cut_ruby,
    ["Cut Diamond"]          = recv_cut_diamond,
    ["Gold Bar"]             = recv_gold_bar,
    ["Silver Bar"]           = recv_silver_bar,
    ["Steel Bar"]            = recv_steel_bar,
    ["Masterwork Craft"]     = recv_masterwork_craft,

    ["Food Bundle"]          = recv_food_bundle,
    ["Wood Bundle"]          = recv_wood_bundle,
    ["Iron Ore Bundle"]      = recv_iron_ore_bundle,
    ["Coal Bundle"]          = recv_coal_bundle,

    ["Goblin Ambush"]        = recv_goblin_ambush,
    ["Cave Bear Incursion"]  = recv_cave_bear,
    ["Vermin Infestation"]   = recv_vermin_infestation,
    ["Tantrum Trigger"]      = recv_tantrum_trigger,
    ["Lost Caravan"]         = recv_lost_caravan,

    ["Merchant's Coffer"]    = recv_merchants_coffer,
    ["Immigration Wave"]     = recv_immigration_wave,
    ["Baron's Charter"]      = recv_barons_charter,
    ["Count's Charter"]      = recv_counts_charter,
    ["Duke's Charter"]       = recv_dukes_charter,
    ["Monarch's Invitation"] = recv_monarchs_invitation,
    ["Military Training"]    = recv_military_training,
}

-- ── Blueprint items ───────────────────────────────────────────────────────────
-- Workshop blueprints unlock the ability to build specific workshops.
-- The unlock_blueprint function is defined in main.lua and writes to
-- persistent storage so the onJobInitiated hook can check it.

local BLUEPRINT_NAMES = {
    -- Workshops
    "Craftsdwarf's Workshop Blueprint",
    "Forge Blueprint",
    "Kitchen Blueprint",
    "Jeweler's Workshop Blueprint",
    "Clothier's Shop Blueprint",
    "Tanner's Blueprint",
    "Mechanic's Workshop Blueprint",
    "Magma Forge Blueprint",
    "Siege Workshop Blueprint",
    "Soap Maker's Workshop Blueprint",
    "Ashery Blueprint",
    "Bowyer's Workshop Blueprint",
    "Screw Press Blueprint",
    "Fishery Blueprint",
    "Loom Blueprint",
    "Dyer's Workshop Blueprint",
    "Butcher's Shop Blueprint",
    "Farmer's Workshop Blueprint",
    "Carpenter's Workshop Blueprint",
    "Stoneworker's Workshop Blueprint",
    "Still Blueprint",
    "Leather Works Blueprint",
    -- Furnaces
    "Smelter Blueprint",
    "Magma Smelter Blueprint",
    "Wood Furnace Blueprint",
    "Glass Furnace Blueprint",
    "Kiln Blueprint",
    "Magma Kiln Blueprint",
    "Magma Glass Furnace Blueprint",
    -- Buildings
    "Farm Plot Blueprint",
}

-- Register blueprint handlers dynamically.
-- Write directly to persistent storage rather than calling unlock_blueprint()
-- from dwarfipelago.lua, because each script has its own _ENV and cross-script
-- global calls resolve to nil.
for _, bp_name in ipairs(BLUEPRINT_NAMES) do
    M.handlers[bp_name] = function()
        dfhack.persistent.saveWorldDataString("dwarfipelago/blueprint/" .. bp_name, "1")
        dfhack.gui.showAnnouncement(
            ("[AP] Blueprint received: %s"):format(bp_name),
            COLOR_GREEN, true)
        print(("[Dwarfipelago] Blueprint unlocked: %s"):format(bp_name))
    end
end

-- Called by main.lua when the client delivers an item by name.
function M.receive(item_name)
    local handler = M.handlers[item_name]
    if handler then
        handler()
    else
        dfhack.printerr("[Dwarfipelago] Unknown item received: " .. tostring(item_name))
    end
end

-- reqscript returns the script's _ENV, not the explicit return value.
-- Copy all module exports into _ENV so callers can access them as globals.
for k, v in pairs(M) do _ENV[k] = v end
return M
