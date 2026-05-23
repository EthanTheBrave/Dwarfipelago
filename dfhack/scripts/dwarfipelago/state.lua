-- Persistent state management for Dwarfipelago.
-- All data is stored in DFHack's site-level persistent storage so it survives
-- save/reload cycles. Keys are namespaced under "dwarfipelago/".

local M = {}

local KEY_CHECKED        = "dwarfipelago/checked_locations"
local KEY_RECEIVED       = "dwarfipelago/received_items"
local KEY_ENABLED        = "dwarfipelago/enabled"
local KEY_GOAL_COMPLETE  = "dwarfipelago/goal_complete"
local KEY_DEATH_COUNT    = "dwarfipelago/death_count"    -- cumulative citizen deaths
local KEY_DL_SENT        = "dwarfipelago/deathlinks_sent" -- deathlinks dispatched to AP
local KEY_DL_RECV        = "dwarfipelago/pending_recv"   -- incoming deathlinks to apply

-- ── Internal helpers ──────────────────────────────────────────────────────────

local function read_table(key)
    local raw = dfhack.persistent.getSiteData(key)
    if raw and raw ~= "" then
        return dfhack.json.decode(raw) or {}
    end
    return {}
end

local function write_table(key, tbl)
    dfhack.persistent.setSiteData(key, dfhack.json.encode(tbl))
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
    local n = (tonumber(dfhack.persistent.getSiteData(KEY_DEATH_COUNT)) or 0) + 1
    dfhack.persistent.setSiteData(KEY_DEATH_COUNT, tostring(n))
    return n
end

function M.get_death_count()
    return tonumber(dfhack.persistent.getSiteData(KEY_DEATH_COUNT)) or 0
end

-- ── DeathLink: outgoing (sent to AP) ─────────────────────────────────────────

function M.get_deathlinks_sent()
    return tonumber(dfhack.persistent.getSiteData(KEY_DL_SENT)) or 0
end

function M.set_deathlinks_sent(n)
    dfhack.persistent.setSiteData(KEY_DL_SENT, tostring(n))
end

-- ── DeathLink: incoming (received from AP, kills to apply) ───────────────────

function M.get_pending_recv()
    return tonumber(dfhack.persistent.getSiteData(KEY_DL_RECV)) or 0
end

function M.increment_pending_recv()
    local n = M.get_pending_recv() + 1
    dfhack.persistent.setSiteData(KEY_DL_RECV, tostring(n))
end

function M.clear_pending_recv()
    dfhack.persistent.setSiteData(KEY_DL_RECV, "0")
end

-- ── Goal completion ───────────────────────────────────────────────────────────

function M.is_goal_complete()
    return dfhack.persistent.getSiteData(KEY_GOAL_COMPLETE) == "1"
end

-- Mark the goal as complete and announce it in-game.
-- Returns true if this is the first time (i.e. was not already complete).
function M.mark_goal_complete()
    if M.is_goal_complete() then return false end
    dfhack.persistent.setSiteData(KEY_GOAL_COMPLETE, "1")
    return true
end

-- ── Debug helpers ─────────────────────────────────────────────────────────────

function M.dump()
    print("[Dwarfipelago] Checked locations:", dfhack.json.encode(M.get_checked_locations()))
    print("[Dwarfipelago] Received item index:", M.get_received_item_index())
    print("[Dwarfipelago] Goal complete:", M.is_goal_complete())
    print("[Dwarfipelago] Citizen deaths:", M.get_death_count())
    print("[Dwarfipelago] DeathLinks sent:", M.get_deathlinks_sent())
    print("[Dwarfipelago] Pending recv DeathLinks:", M.get_pending_recv())
    print("[Dwarfipelago] Enabled:", M.is_enabled())
end

function M.reset()
    dfhack.persistent.setSiteData(KEY_CHECKED, "")
    dfhack.persistent.setSiteData(KEY_RECEIVED, "")
    dfhack.persistent.setSiteData(KEY_ENABLED, "")
    dfhack.persistent.setSiteData(KEY_GOAL_COMPLETE, "")
    dfhack.persistent.setSiteData(KEY_DEATH_COUNT, "")
    dfhack.persistent.setSiteData(KEY_DL_SENT, "")
    dfhack.persistent.setSiteData(KEY_DL_RECV, "")
    print("[Dwarfipelago] State reset.")
end

return M
