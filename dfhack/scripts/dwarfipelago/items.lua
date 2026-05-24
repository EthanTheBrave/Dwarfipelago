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
    -- -setUnitToFort places them near the fortress entrance.
    local ok, err = pcall(function()
        for _ = 1, 3 do
            dfhack.run_script("modtools/create-unit",
                "-race", "GOBLIN",
                "-caste", "GOBLIN",
                "-setUnitToFort"
            )
        end
    end)
    if not ok then
        dfhack.printerr("[Dwarfipelago] goblin_ambush spawn failed: " .. tostring(err))
    end
end

local function recv_cave_bear()
    announce("Trap: A Cave Bear has found its way in!")
    local ok, err = pcall(function()
        dfhack.run_script("modtools/create-unit",
            "-race", "CAVE_BEAR",
            "-caste", "CAVE_BEAR",
            "-setUnitToFort"
        )
    end)
    if not ok then
        dfhack.printerr("[Dwarfipelago] cave_bear spawn failed: " .. tostring(err))
    end
end

local function recv_vermin_infestation()
    announce("Trap: Vermin Infestation! Rats everywhere!")
    -- Spawn 10 rats scattered through the fortress.
    local spawned = 0
    for _ = 1, 10 do
        local ok = pcall(function()
            dfhack.run_script("modtools/create-unit",
                "-race", "RAT",
                "-caste", "RAT",
                "-setUnitToFort"
            )
        end)
        if ok then spawned = spawned + 1 end
    end
    if spawned == 0 then
        dfhack.printerr("[Dwarfipelago] vermin_infestation: could not spawn any vermin")
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
    dfhack.persistent.setSiteData("dwarfipelago/trap/lost_caravan", "1")
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

-- Called by main.lua when the client delivers an item by name.
function M.receive(item_name)
    local handler = M.handlers[item_name]
    if handler then
        handler()
    else
        dfhack.printerr("[Dwarfipelago] Unknown item received: " .. tostring(item_name))
    end
end

return M
