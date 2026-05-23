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
local POLL_TICKS  = 100  -- poll wealth/trade/goal checks every N ticks

-- ── Goal settings helpers ─────────────────────────────────────────────────────
-- The Python client writes these to persistent storage after connecting.
-- goal: 0 = slay_megabeast, 1 = legendary_wealth, 2 = population_boom

local function goal_setting(key, default)
    return tonumber(dfhack.persistent.getSiteData("dwarfipelago/" .. key)) or default
end

-- ── Goal completion: poll-based checks (wealth & population) ─────────────────

local function check_goal_by_poll()
    if state.is_goal_complete() then return end

    local goal = goal_setting("goal", -1)
    if goal == -1 then return end  -- slot data not yet synced from Python client

    if goal == 1 then  -- legendary_wealth
        local target = goal_setting("wealth_goal", 100000)
        if checks.fortress_wealth() >= target then
            if state.mark_goal_complete() then
                dfhack.gui.showAnnouncement(
                    "[AP] Goal reached: Legendary Wealth! Victory is yours.",
                    COLOR_CYAN, true)
                print("[Dwarfipelago] Goal complete: Legendary Wealth!")
            end
        end

    elseif goal == 2 then  -- population_boom
        local target = goal_setting("pop_goal", 300)
        local count = 0
        for _, unit in ipairs(df.global.world.units.active) do
            if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
                count = count + 1
            end
        end
        if count >= target then
            if state.mark_goal_complete() then
                dfhack.gui.showAnnouncement(
                    ("[AP] Goal reached: Population Boom! (%d dwarves). Victory!"):format(count),
                    COLOR_CYAN, true)
                print("[Dwarfipelago] Goal complete: Population Boom!")
            end
        end
    end
    -- goal == 0 (slay_megabeast) is handled by the on_unit_death hook below.
end

-- ── Goal completion: eventful hook (megabeast death) ─────────────────────────

local function on_unit_death(uid)
    if not state.is_enabled() then return end
    if state.is_goal_complete() then return end
    if goal_setting("goal", -1) ~= 0 then return end  -- not a slay_megabeast game

    local unit = df.unit.find(uid)
    if not unit then return end

    local ok, is_mega = pcall(dfhack.units.isMegabeast, unit)
    if ok and is_mega then
        if state.mark_goal_complete() then
            local name = dfhack.TranslateName(dfhack.units.getVisibleName(unit))
            dfhack.gui.showAnnouncement(
                ("[AP] Goal reached: %s has been slain! Victory!"):format(
                    name ~= "" and name or "The megabeast"),
                COLOR_CYAN, true)
            print("[Dwarfipelago] Goal complete: Megabeast slain!")
        end
    end
end

-- ── Poll loop: wealth, trade, and goal milestones ─────────────────────────────
-- Runs every POLL_TICKS game ticks. Production checks are handled by eventful.

local function poll_checks()
    if not state.is_enabled() then return end

    check_goal_by_poll()

    for _, check in ipairs(checks.checks) do
        if not state.is_location_checked(check.id) then
            local ok, result = pcall(check.fn)
            if ok and result then
                local newly_checked = state.mark_location_checked(check.id)
                if newly_checked then
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
-- TODO: implement caravan detection in poll_checks using df.global.world.caravans

-- ── Start / stop ──────────────────────────────────────────────────────────────

local function start()
    state.set_enabled(true)

    -- Register hooks
    eventful.onJobCompleted[SCRIPT_NAME] = on_job_completed
    eventful.onUnitDeath[SCRIPT_NAME]    = on_unit_death

    -- Register poll loop
    repeatUtil.scheduleEvery(SCRIPT_NAME, POLL_TICKS, "ticks", poll_checks)

    print("[Dwarfipelago] Started. Listening for fortress milestones.")
    print("[Dwarfipelago] Make sure DwarfFortressClient.py is running.")
end

local function stop()
    state.set_enabled(false)

    -- Unregister hooks
    eventful.onJobCompleted[SCRIPT_NAME] = nil
    eventful.onUnitDeath[SCRIPT_NAME]    = nil
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
