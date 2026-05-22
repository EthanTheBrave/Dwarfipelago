-- Dwarfipelago main entry point.
-- Usage (DFHack console):
--   dwarfipelago/main start   -- enable and register hooks
--   dwarfipelago/main stop    -- disable and unregister hooks
--   dwarfipelago/main status  -- show current state
--   dwarfipelago/main reset   -- wipe persistent state (use with care)
--   dwarfipelago/main receive <item_name>  -- manually deliver an item (for testing)

local state  = require("dwarfipelago.state")
local checks = require("dwarfipelago.checks")
local items  = require("dwarfipelago.items")

local eventful   = require("plugins.eventful")
local repeatUtil = require("repeat-util")

local SCRIPT_NAME = "dwarfipelago"
local POLL_TICKS  = 100  -- poll wealth/trade checks every N ticks

-- ── Poll loop: wealth & trade milestones ─────────────────────────────────────
-- Runs every POLL_TICKS game ticks. Skips production checks (handled by eventful).

local function poll_checks()
    if not state.is_enabled() then return end

    for _, check in ipairs(checks.checks) do
        -- Skip production flags — those are set by the job hook and just read here.
        -- Wealth and trade checks are polled every tick window.
        if not state.is_location_checked(check.id) then
            local ok, result = pcall(check.fn)
            if ok and result then
                local newly_checked = state.mark_location_checked(check.id)
                if newly_checked then
                    -- Signal the AP client via a persistent queue.
                    -- The client reads this queue and sends LocationChecks to the server.
                    local queue_key = "dwarfipelago/pending_checks"
                    local raw = dfhack.persistent.getSiteData(queue_key) or "[]"
                    local queue = dfhack.json.decode(raw) or {}
                    table.insert(queue, check.id)
                    dfhack.persistent.setSiteData(queue_key, dfhack.json.encode(queue))

                    print(("[Dwarfipelago] Check: %s (%d)"):format(check.name, check.id))
                end
            end
        end
    end
end

-- ── eventful hook: job completion → production flags ─────────────────────────

local function on_job_completed(job)
    if not state.is_enabled() then return end

    local flag = checks.job_to_production_flag(job)
    if flag and not checks.production_flag(flag) then
        checks.set_production_flag(flag)
        -- Production flags will be picked up on the next poll cycle.
    end
end

-- ── Caravan arrival hook ─────────────────────────────────────────────────────
-- eventful.onCaravanArrival is not a standard event; we detect caravans
-- via the unit list on each poll cycle instead.
-- TODO: implement caravan detection in poll_checks using df.global.ui.caravans

-- ── Start / stop ──────────────────────────────────────────────────────────────

local function start()
    state.set_enabled(true)

    -- Register job completion hook
    eventful.onJobCompleted[SCRIPT_NAME] = on_job_completed

    -- Register poll loop
    repeatUtil.scheduleEvery(SCRIPT_NAME, POLL_TICKS, "ticks", poll_checks)

    print("[Dwarfipelago] Started. Listening for fortress milestones.")
    print("[Dwarfipelago] Make sure DwarfFortressClient.py is running.")
end

local function stop()
    state.set_enabled(false)

    -- Unregister hooks
    eventful.onJobCompleted[SCRIPT_NAME] = nil
    repeatUtil.cancel(SCRIPT_NAME)

    print("[Dwarfipelago] Stopped.")
end

-- ── CLI dispatch ──────────────────────────────────────────────────────────────

local args = { ... }
local cmd  = args[1] or "start"

if cmd == "start" then
    start()
elseif cmd == "stop" then
    stop()
elseif cmd == "status" then
    state.dump()
elseif cmd == "reset" then
    stop()
    state.reset()
elseif cmd == "receive" then
    local item_name = table.concat(args, " ", 2)
    if item_name == "" then
        dfhack.printerr("Usage: dwarfipelago/main receive <Item Name>")
    else
        items.receive(item_name)
    end
else
    print("Usage: dwarfipelago/main [start|stop|status|reset|receive <item>]")
end
