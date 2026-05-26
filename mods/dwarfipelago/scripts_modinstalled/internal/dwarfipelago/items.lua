--@ module = true
-- Item spawning for Dwarfipelago.
-- Called when the AP client delivers an item to the fortress.
-- Each handler uses dfhack.run_script or direct df API calls to apply the effect.

local M = {}

-- ── Helpers ───────────────────────────────────────────────────────────────────

-- Spawn a single item at the trade depot / first available stockpile.
-- Falls back to dropping it at the cursor position if no depot exists.
local function spawn_item(item_type, material, quantity)
    quantity = quantity or 1
    for _ = 1, quantity do
        -- createitem script: "createitem <item-token> <material>"
        -- e.g. createitem SMALLGEM INORGANIC:RUBY
        local ok, err = pcall(function()
            dfhack.run_script("createitem", item_type, material)
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
for _, bp_name in ipairs(BLUEPRINT_NAMES) do
    M.handlers[bp_name] = function()
        -- unlock_blueprint is a global function defined in main.lua
        unlock_blueprint(bp_name)
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
