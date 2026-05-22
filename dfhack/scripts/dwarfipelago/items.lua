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
        -- createitem script: "createitem <type> <material> [<quantity>]"
        -- e.g. createitem ITEM_GEM_ROUGH ONYX
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

local function recv_cut_sapphire()
    spawn_item("ITEM_GEM_ROUGH", "SAPPHIRE")
    announce("Received: Cut Sapphire!")
end

local function recv_cut_ruby()
    spawn_item("ITEM_GEM_ROUGH", "RUBY")
    announce("Received: Cut Ruby!")
end

local function recv_cut_diamond()
    spawn_item("ITEM_GEM_ROUGH", "DIAMOND")
    announce("Received: Cut Diamond!")
end

local function recv_gold_bar()
    spawn_item("ITEM_BAR", "METAL:GOLD")
    announce("Received: Gold Bar!")
end

local function recv_silver_bar()
    spawn_item("ITEM_BAR", "METAL:SILVER")
    announce("Received: Silver Bar!")
end

local function recv_steel_bar()
    spawn_item("ITEM_BAR", "METAL:STEEL")
    announce("Received: Steel Bar!")
end

local function recv_masterwork_craft()
    spawn_item("ITEM_CRAFTS", "STONE:OBSIDIAN")
    announce("Received: Masterwork Craft!")
end

-- ── Item handlers: resources ──────────────────────────────────────────────────

local function recv_food_bundle()
    for _ = 1, 5 do
        spawn_item("ITEM_FOOD", "MUSHROOM_HELMET_PLUMP:MUSHROOM")
    end
    announce("Received: Food Bundle (5 meals)!")
end

local function recv_wood_bundle()
    for _ = 1, 5 do
        spawn_item("ITEM_WOOD", "WOOD:OAK")
    end
    announce("Received: Wood Bundle (5 logs)!")
end

local function recv_iron_ore_bundle()
    for _ = 1, 5 do
        spawn_item("ITEM_BOULDER", "STONE:LIMONITE")
    end
    announce("Received: Iron Ore Bundle!")
end

local function recv_coal_bundle()
    for _ = 1, 3 do
        spawn_item("ITEM_BAR", "COAL:COKE")
    end
    announce("Received: Coal Bundle!")
end

-- ── Item handlers: traps ──────────────────────────────────────────────────────

local function recv_goblin_ambush()
    -- Spawn a small goblin squad near the fortress entrance.
    -- TODO: use modtools/create-unit with goblin race, set to hostile.
    -- For now, use migrants-now as a placeholder and flag for future impl.
    announce("Trap: Goblin Ambush incoming!")
    dfhack.printerr("[Dwarfipelago] TRAP goblin_ambush: unit spawning not yet implemented")
end

local function recv_cave_bear()
    -- Spawn a hostile cave bear.
    announce("Trap: A Cave Bear has found its way in!")
    dfhack.printerr("[Dwarfipelago] TRAP cave_bear: unit spawning not yet implemented")
end

local function recv_vermin_infestation()
    -- Spawn many vermin (rats) throughout the fortress.
    announce("Trap: Vermin Infestation! Rats everywhere!")
    dfhack.printerr("[Dwarfipelago] TRAP vermin_infestation: not yet implemented")
end

local function recv_tantrum_trigger()
    -- Make a random happy dwarf very unhappy (lower needs drastically).
    announce("Trap: A dwarf has had enough!")
    dfhack.printerr("[Dwarfipelago] TRAP tantrum_trigger: not yet implemented")
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
