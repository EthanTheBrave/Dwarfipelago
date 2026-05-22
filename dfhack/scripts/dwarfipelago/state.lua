-- Persistent state management for Dwarfipelago.
-- All data is stored in DFHack's site-level persistent storage so it survives
-- save/reload cycles. Keys are namespaced under "dwarfipelago/".

local M = {}

local KEY_CHECKED   = "dwarfipelago/checked_locations"
local KEY_RECEIVED  = "dwarfipelago/received_items"
local KEY_ENABLED   = "dwarfipelago/enabled"

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

-- ── Debug helpers ─────────────────────────────────────────────────────────────

function M.dump()
    print("[Dwarfipelago] Checked locations:", dfhack.json.encode(M.get_checked_locations()))
    print("[Dwarfipelago] Received item index:", M.get_received_item_index())
    print("[Dwarfipelago] Enabled:", M.is_enabled())
end

function M.reset()
    dfhack.persistent.setSiteData(KEY_CHECKED, "")
    dfhack.persistent.setSiteData(KEY_RECEIVED, "")
    dfhack.persistent.setSiteData(KEY_ENABLED, "")
    print("[Dwarfipelago] State reset.")
end

return M
