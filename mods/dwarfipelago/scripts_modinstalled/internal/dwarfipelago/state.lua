--@ module = true
-- Persistent state management for Dwarfipelago.
-- All data is stored in DFHack's world-level persistent storage so it survives
-- save/reload cycles. Keys are namespaced under "dwarfipelago/".

local M = {}
local json = require('json')

local KEY_CHECKED        = "dwarfipelago/checked_locations"
local KEY_RECEIVED       = "dwarfipelago/received_items"
local KEY_ENABLED        = "dwarfipelago/enabled"
local KEY_GOAL_COMPLETE  = "dwarfipelago/goal_complete"
local KEY_DEATH_COUNT    = "dwarfipelago/death_count"    -- cumulative citizen deaths
local KEY_DL_SENT        = "dwarfipelago/deathlinks_sent" -- deathlinks dispatched to AP
local KEY_DL_RECV        = "dwarfipelago/pending_recv"   -- incoming deathlinks to apply
local KEY_DEPOT_BUILT    = "dwarfipelago/depot_built"    -- starting trade depot placed

-- All craft-count flag names (match AP craftable_items / craftable_materials options).
-- Must stay in sync with JOB_TO_CRAFT_FLAG and NEEDS_MAT_CHECK in checks.lua.
local CRAFT_FLAGS = {
    -- craftable_items
    "altar", "door", "cage", "bin", "blocks", "wheelbarrow", "grate",
    "corkscrew", "animal_trap", "ball", "armor_stand", "pedestal", "bucket", "spike",
    -- craftable_materials
    "cloth", "stone", "leather", "ceramic", "metal", "bone", "wood", "glass",
}

-- -- Internal helpers ----------------------------------------------------------

local function read_table(key)
    local raw = dfhack.persistent.getWorldDataString(key)
    if raw and raw ~= "" then
        return json.decode(raw) or {}
    end
    return {}
end

local function write_table(key, tbl)
    dfhack.persistent.saveWorldDataString(key, json.encode(tbl))
end

-- -- Checked locations ---------------------------------------------------------

-- Returns a set (table with location_id -> true) of already-checked locations.
function M.get_checked_locations()
    return read_table(KEY_CHECKED)
end

-- Mark a location as checked.
function M.mark_location_checked(location_id)
    local checked = M.get_checked_locations()
    if not checked[tostring(location_id)] then
        checked[tostring(location_id)] = true
        write_table(KEY_CHECKED, checked)
        return true  -- newly checked
    end
    return false  -- already checked
end

function M.is_location_checked(location_id)
    local checked = M.get_checked_locations()
    return checked[tostring(location_id)] == true
end

-- -- Received items ------------------------------------------------------------

-- Returns the index of the last item that has been applied in-game.
-- AP sends items with a monotonically increasing index; we track where we are.
function M.get_received_item_index()
    local data = read_table(KEY_RECEIVED)
    return data.index or 0
end

function M.set_received_item_index(index)
    local data = read_table(KEY_RECEIVED)
    data.index = index
    write_table(KEY_RECEIVED, data)
end

-- -- Enable/disable flag -------------------------------------------------------

function M.is_enabled()
    local data = read_table(KEY_ENABLED)
    return data.enabled == true
end

function M.set_enabled(value)
    write_table(KEY_ENABLED, { enabled = value })
end

-- -- DeathLink: death counting -------------------------------------------------

-- Increment the citizen death counter and return the new total.
function M.increment_death_count()
    local n = (tonumber(dfhack.persistent.getWorldDataString(KEY_DEATH_COUNT)) or 0) + 1
    dfhack.persistent.saveWorldDataString(KEY_DEATH_COUNT, tostring(n))
    return n
end

function M.get_death_count()
    return tonumber(dfhack.persistent.getWorldDataString(KEY_DEATH_COUNT)) or 0
end

-- -- DeathLink: outgoing (sent to AP) -----------------------------------------

function M.get_deathlinks_sent()
    return tonumber(dfhack.persistent.getWorldDataString(KEY_DL_SENT)) or 0
end

function M.set_deathlinks_sent(n)
    dfhack.persistent.saveWorldDataString(KEY_DL_SENT, tostring(n))
end

-- -- DeathLink: incoming (received from AP, kills to apply) -------------------

function M.get_pending_recv()
    return tonumber(dfhack.persistent.getWorldDataString(KEY_DL_RECV)) or 0
end

function M.increment_pending_recv()
    local n = M.get_pending_recv() + 1
    dfhack.persistent.saveWorldDataString(KEY_DL_RECV, tostring(n))
end

function M.clear_pending_recv()
    dfhack.persistent.saveWorldDataString(KEY_DL_RECV, "0")
end

-- -- Goal completion -----------------------------------------------------------

function M.is_goal_complete()
    return dfhack.persistent.getWorldDataString(KEY_GOAL_COMPLETE) == "1"
end

-- Mark the goal as complete and announce it in-game.
-- Returns true if this is the first time (i.e. was not already complete).
function M.mark_goal_complete()
    if M.is_goal_complete() then return false end
    dfhack.persistent.saveWorldDataString(KEY_GOAL_COMPLETE, "1")
    return true
end

-- -- Debug helpers -------------------------------------------------------------

function M.dump()
    print("[Dwarfipelago] Checked locations:", json.encode(M.get_checked_locations()))
    print("[Dwarfipelago] Received item index:", M.get_received_item_index())
    print("[Dwarfipelago] Goal complete:", M.is_goal_complete())
    print("[Dwarfipelago] Citizen deaths:", M.get_death_count())
    print("[Dwarfipelago] DeathLinks sent:", M.get_deathlinks_sent())
    print("[Dwarfipelago] Pending recv DeathLinks:", M.get_pending_recv())
    print("[Dwarfipelago] Trade depot placed:", dfhack.persistent.getWorldDataString(KEY_DEPOT_BUILT) == "1")
    print("[Dwarfipelago] Enabled:", M.is_enabled())
    -- Craft counts: enumerate via the checks index so dynamic material-split
    -- keys (e.g. "table_wood") show up, not just the legacy hardcoded flags.
    local checks = reqscript("internal/dwarfipelago/checks")
    print("[Dwarfipelago] Craft counts:", json.encode(checks.get_all_craft_counts()))

    -- Progression unlocks (same data the panel shows, via items.UNLOCK_DEFS).
    local items_defs = reqscript("internal/dwarfipelago/items")
    print("[Dwarfipelago] Unlocks:")
    for _, def in ipairs(items_defs.UNLOCK_DEFS or {}) do
        local raw = dfhack.persistent.getWorldDataString("dwarfipelago/unlock/" .. def.key)
        if def.max then
            print(("    %-23s %d/%d"):format(def.label .. ":", tonumber(raw) or 0, def.max))
        else
            print(("    %-23s %s"):format(def.label .. ":", raw == "1" and "yes" or "no"))
        end
    end

    -- -- Mining --------------------------------------------------------------
    local function num(key) return tonumber(dfhack.persistent.getWorldDataString(key)) end
    local dug      = num("dwarfipelago/mining/dig_count") or 0
    local surface  = num("dwarfipelago/mining/surface_z")
    local deepest  = num("dwarfipelago/mining/deepest_z")
    local depth    = (surface and deepest) and math.max(surface - deepest, 0) or 0
    print("[Dwarfipelago] Blocks dug:", dug)
    print("[Dwarfipelago] Depth below surface:", depth)
    print("[Dwarfipelago] Caverns breached:",
        dfhack.persistent.getWorldDataString("dwarfipelago/mining/cavern1") == "1" and 1 or 0,
        dfhack.persistent.getWorldDataString("dwarfipelago/mining/cavern2") == "1" and 2 or "-",
        dfhack.persistent.getWorldDataString("dwarfipelago/mining/cavern3") == "1" and 3 or "-",
        "| Magma sea:",
        dfhack.persistent.getWorldDataString("dwarfipelago/mining/magma") == "1")

    -- -- Farming -------------------------------------------------------------
    print("[Dwarfipelago] Crops harvested:", num("dwarfipelago/farming/crop_count") or 0)

    -- -- Blueprints received -------------------------------------------------
    local items = reqscript("internal/dwarfipelago/items")
    local names = items.BLUEPRINT_NAMES or {}
    local have = {}
    for _, name in ipairs(names) do
        if dfhack.persistent.getWorldDataString("dwarfipelago/blueprint/" .. name) == "1" then
            table.insert(have, name)
        end
    end
    print(("[Dwarfipelago] Blueprints received (%d/%d):"):format(#have, #names))
    for _, name in ipairs(have) do
        print("    - " .. name)
    end
end

function M.reset()
    dfhack.persistent.saveWorldDataString(KEY_CHECKED, "")
    dfhack.persistent.saveWorldDataString(KEY_RECEIVED, "")
    dfhack.persistent.saveWorldDataString(KEY_ENABLED, "")
    dfhack.persistent.saveWorldDataString(KEY_GOAL_COMPLETE, "")
    dfhack.persistent.saveWorldDataString(KEY_DEATH_COUNT, "")
    dfhack.persistent.saveWorldDataString(KEY_DL_SENT, "")
    dfhack.persistent.saveWorldDataString(KEY_DL_RECV, "")
    dfhack.persistent.saveWorldDataString(KEY_DEPOT_BUILT, "")
    dfhack.persistent.saveWorldDataString("dwarfipelago/mining/surface_z", "")
    dfhack.persistent.saveWorldDataString("dwarfipelago/mining/deepest_z", "")
    dfhack.persistent.saveWorldDataString("dwarfipelago/mining/dig_count", "")
    dfhack.persistent.saveWorldDataString("dwarfipelago/mining/cavern1", "")
    dfhack.persistent.saveWorldDataString("dwarfipelago/mining/cavern2", "")
    dfhack.persistent.saveWorldDataString("dwarfipelago/mining/cavern3", "")
    dfhack.persistent.saveWorldDataString("dwarfipelago/mining/magma", "")
    dfhack.persistent.saveWorldDataString("dwarfipelago/farming/crop_count", "")

    -- Craft counts: legacy hardcoded flags + every dynamic key via the index.
    for _, flag in ipairs(CRAFT_FLAGS) do
        dfhack.persistent.saveWorldDataString("dwarfipelago/craft_count/" .. flag, "")
    end
    reqscript("internal/dwarfipelago/checks").clear_craft_counts()

    -- Progression unlocks, received blueprints, and one-shot flags.
    local items = reqscript("internal/dwarfipelago/items")
    for _, def in ipairs(items.UNLOCK_DEFS or {}) do
        dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/" .. def.key, "")
    end
    for _, name in ipairs(items.BLUEPRINT_NAMES or {}) do
        dfhack.persistent.saveWorldDataString("dwarfipelago/blueprint/" .. name, "")
    end
    dfhack.persistent.saveWorldDataString("dwarfipelago/megabeast/spawned", "")
    dfhack.persistent.saveWorldDataString("dwarfipelago/deity_id", "")
    dfhack.persistent.saveWorldDataString("dwarfipelago/religion_id", "")
    print("[Dwarfipelago] State reset.")
end

-- reqscript returns the script's _ENV, not the explicit return value.
-- Copy all module exports into _ENV so callers can access them as
-- env.set_enabled(), env.is_enabled(), etc.
for k, v in pairs(M) do _ENV[k] = v end
return M
