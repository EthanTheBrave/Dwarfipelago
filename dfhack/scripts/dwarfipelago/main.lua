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

-- Set to true while we are applying a received DeathLink so that the death
-- hook does not count those kills toward our own outgoing DeathLink threshold.
local applying_recv_deathlink = false

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

    local unit = df.unit.find(uid)
    if not unit then return end

    -- ── Goal: megabeast kill ──────────────────────────────────────────────────
    if not state.is_goal_complete() and goal_setting("goal", -1) == 0 then
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

    -- ── DeathLink: count citizen deaths ──────────────────────────────────────
    -- Skip deaths we inflicted ourselves when applying a received DeathLink,
    -- so those don't feed back into our outgoing threshold.
    if applying_recv_deathlink then return end
    if dfhack.units.isCitizen(unit) then
        local count = state.increment_death_count()
        -- Python polls death_count vs deathlinks_sent and fires the Bounce packets.
        print(("[Dwarfipelago] Citizen death #%d counted for DeathLink"):format(count))
    end
end

-- ── DeathLink: apply received kills ──────────────────────────────────────────
-- Called from the poll loop. Reads pending_recv, kills threshold-many random
-- citizens per pending DeathLink, then clears the counter.

local function apply_pending_recv_deathlinks()
    if not state.is_enabled() then return end
    local pending = state.get_pending_recv()
    if pending <= 0 then return end

    state.clear_pending_recv()

    local threshold = goal_setting("deathlink_threshold", 5)
    local to_kill   = pending * threshold

    -- Collect living citizens into a list, then shuffle it.
    local candidates = {}
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
            table.insert(candidates, unit)
        end
    end

    -- Fisher-Yates shuffle for variety.
    for i = #candidates, 2, -1 do
        local j = math.random(i)
        candidates[i], candidates[j] = candidates[j], candidates[i]
    end

    applying_recv_deathlink = true
    local killed = 0
    for i = 1, math.min(to_kill, #candidates) do
        local unit = candidates[i]
        local ok, err = pcall(function()
            dfhack.run_script("modtools/kill-unit", "--unit", tostring(unit.id))
        end)
        if ok then
            killed = killed + 1
        else
            dfhack.printerr("[Dwarfipelago] kill-unit failed: " .. tostring(err))
        end
    end
    applying_recv_deathlink = false

    dfhack.gui.showAnnouncement(
        ("[AP] DeathLink! %d dwarves have met a mysterious fate."):format(killed),
        COLOR_RED, true)
    print(("[Dwarfipelago] DeathLink applied: %d/%d dwarves killed"):format(killed, to_kill))
end

-- ── Poll loop: wealth, trade, and goal milestones ─────────────────────────────
-- Runs every POLL_TICKS game ticks. Production checks are handled by eventful.

local function poll_checks()
    if not state.is_enabled() then return end

    apply_pending_recv_deathlinks()
    check_goal_by_poll()
    detect_caravans()
    detect_trade_export()

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

-- ── Caravan & trade detection ────────────────────────────────────────────────
-- Scans the active unit list for merchant and diplomat units each poll tick,
-- then maps them to their civilisation's race to set the appropriate trade
-- flags in checks.lua. Also tracks exported wealth to detect completed trades.

local CARAVAN_RACES = {
    DWARF = "dwarven_caravan",
    ELF   = "elven_caravan",
    HUMAN = "human_caravan",
}

local function detect_caravans()
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isAlive(unit) then
            -- Merchant units mark a caravan visit for that race.
            if unit.flags1.merchant then
                local creature = df.creature_raw.find(unit.race)
                if creature then
                    local flag = CARAVAN_RACES[creature.creature_id]
                    if flag and not checks.trade_flag(flag) then
                        checks.set_trade_flag(flag)
                        print(("[Dwarfipelago] Caravan detected: %s"):format(creature.creature_id))
                    end
                end
            end

            -- Diplomat / outpost liaison detection.
            if unit.flags1.diplomat and not checks.trade_flag("liaison_met") then
                checks.set_trade_flag("liaison_met")
                print("[Dwarfipelago] Outpost liaison detected")
            end
        end
    end
end

-- Detect first trade / first export by checking the fortress exported-wealth
-- counter. DF increments this when goods are sold to a caravan, so a value
-- above zero means at least one trade has been completed.
local function detect_trade_export()
    if checks.trade_flag("trade_completed") and checks.trade_flag("first_export") then
        return  -- both already fired
    end

    -- DF50+ uses plotinfo; Classic uses ui.
    local exported = 0
    local ok, result = pcall(function()
        return df.global.plotinfo.tasks.wealth_exported
    end)
    if ok and type(result) == "number" then
        exported = result
    else
        ok, result = pcall(function()
            return df.global.ui.tasks.wealth_exported
        end)
        if ok and type(result) == "number" then
            exported = result
        end
    end

    if exported > 0 then
        if not checks.trade_flag("trade_completed") then
            checks.set_trade_flag("trade_completed")
            print("[Dwarfipelago] First trade detected (exported wealth > 0)")
        end
        if not checks.trade_flag("first_export") then
            checks.set_trade_flag("first_export")
            print("[Dwarfipelago] First export detected (exported wealth > 0)")
        end
    end
end

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
