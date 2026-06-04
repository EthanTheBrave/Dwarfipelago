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

-- ── Internal helpers ──────────────────────────────────────────────────────────

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

-- ── Checked locations ─────────────────────────────────────────────────────────

-- Returns a set (table with location_id → true) of already-checked locations.
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

-- ── Received items ────────────────────────────────────────────────────────────

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

-- ── Enable/disable flag ───────────────────────────────────────────────────────

function M.is_enabled()
    local data = read_table(KEY_ENABLED)
    return data.enabled == true
end

function M.set_enabled(value)
    write_table(KEY_ENABLED, { enabled = value })
end

-- ── DeathLink: death counting ─────────────────────────────────────────────────

-- Increment the citizen death counter and return the new total.
function M.increment_death_count()
    local n = (tonumber(dfhack.persistent.getWorldDataString(KEY_DEATH_COUNT)) or 0) + 1
    dfhack.persistent.saveWorldDataString(KEY_DEATH_COUNT, tostring(n))
    return n
end

function M.get_death_count()
    return tonumber(dfhack.persistent.getWorldDataString(KEY_DEATH_COUNT)) or 0
end

-- ── DeathLink: outgoing (sent to AP) ─────────────────────────────────────────

function M.get_deathlinks_sent()
    return tonumber(dfhack.persistent.getWorldDataString(KEY_DL_SENT)) or 0
end

function M.set_deathlinks_sent(n)
    dfhack.persistent.saveWorldDataString(KEY_DL_SENT, tostring(n))
end

-- ── DeathLink: incoming (received from AP, kills to apply) ───────────────────

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

-- ── Goal completion ───────────────────────────────────────────────────────────

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

-- ── Debug helpers ─────────────────────────────────────────────────────────────

function M.dump()
    print("[Dwarfipelago] Checked locations:", json.encode(M.get_checked_locations()))
    print("[Dwarfipelago] Received item index:", M.get_received_item_index())
    print("[Dwarfipelago] Goal complete:", M.is_goal_complete())
    print("[Dwarfipelago] Citizen deaths:", M.get_death_count())
    print("[Dwarfipelago] DeathLinks sent:", M.get_deathlinks_sent())
    print("[Dwarfipelago] Pending recv DeathLinks:", M.get_pending_recv())
    print("[Dwarfipelago] Trade depot placed:", dfhack.persistent.getWorldDataString(KEY_DEPOT_BUILT) == "1")
    print("[Dwarfipelago] Enabled:", M.is_enabled())
    local craft_counts = {}
    for _, flag in ipairs(CRAFT_FLAGS) do
        local n = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/craft_count/" .. flag)) or 0
        if n > 0 then craft_counts[flag] = n end
    end
    print("[Dwarfipelago] Craft counts:", json.encode(craft_counts))
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
    for _, flag in ipairs(CRAFT_FLAGS) do
        dfhack.persistent.saveWorldDataString("dwarfipelago/craft_count/" .. flag, "")
    end
    print("[Dwarfipelago] State reset.")
end

-- reqscript returns the script's _ENV, not the explicit return value.
-- Copy all module exports into _ENV so callers can access them as
-- env.set_enabled(), env.is_enabled(), etc.
for k, v in pairs(M) do _ENV[k] = v end
return M
