-- Dwarfipelago main entry point.
-- Usage (DFHack console):
--   dwarfipelago start              -- enable and register hooks
--   dwarfipelago stop               -- disable and unregister hooks
--   dwarfipelago status             -- show current state
--   dwarfipelago reset              -- wipe persistent state (use with care)
--   dwarfipelago receive <item>     -- manually deliver an item (for testing)

-- Internal modules live under internal/dwarfipelago/ to keep them out of the
-- DFHack launcher autocomplete. Use reqscript (not require) so they hot-reload
-- when edited without restarting DFHack.
local state  = reqscript("internal/dwarfipelago/state")
local checks = reqscript("internal/dwarfipelago/checks")
local items  = reqscript("internal/dwarfipelago/items")
local json   = require('json')

-- DFHack built-in plugins use the standard require().
local eventful   = require("plugins.eventful")
local repeatUtil = require("repeat-util")

local SCRIPT_NAME = "dwarfipelago"
local POLL_TICKS  = 100  -- poll wealth/trade/goal checks every N ticks

-- Set to true while we are applying a received DeathLink so that the death
-- hook does not count those kills toward our own outgoing DeathLink threshold.
local applying_recv_deathlink = false

-- ── Goal settings helpers ─────────────────────────────────────────────────────
-- The Python client writes these to persistent storage after connecting.
-- goal: 0 = slay_megabeast, 1 = legendary_wealth, 2 = population_boom, 3 = mountainhome

local function goal_setting(key, default)
    return tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/" .. key)) or default
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
    elseif goal == 3 then  -- mountainhome
        -- Mountainhome is achieved when the monarch (king/queen) takes residence.
        local ok_k, has_king  = pcall(dfhack.units.getUnitsByNobleRole, "KING")
        local ok_q, has_queen = pcall(dfhack.units.getUnitsByNobleRole, "QUEEN")
        local has_monarch = (ok_k and has_king and #has_king > 0)
                         or (ok_q and has_queen and #has_queen > 0)
        if has_monarch then
            if state.mark_goal_complete() then
                dfhack.gui.showAnnouncement(
                    "[AP] Goal reached: Mountainhome! The monarch has arrived. Victory!",
                    COLOR_CYAN, true)
                print("[Dwarfipelago] Goal complete: Mountainhome!")
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
        -- modtools/kill-unit does not exist in modern DFHack; use the Lua API
        -- directly. Try dfhack.units.kill() first (available in newer builds),
        -- then fall back to blood depletion which causes natural bleed-out death.
        local ok, err = pcall(function()
            if dfhack.units.kill then
                dfhack.units.kill(unit)
            else
                unit.body.blood_count = 0
            end
        end)
        if ok then
            killed = killed + 1
        else
            dfhack.printerr("[Dwarfipelago] kill unit failed: " .. tostring(err))
        end
    end
    applying_recv_deathlink = false

    dfhack.gui.showAnnouncement(
        ("[AP] DeathLink! %d dwarves have met a mysterious fate."):format(killed),
        COLOR_RED, true)
    print(("[Dwarfipelago] DeathLink applied: %d/%d dwarves killed"):format(killed, to_kill))
end

-- ── Caravan & trade detection ────────────────────────────────────────────────
-- Defined before poll_checks because poll_checks calls them directly (they are
-- locals, so forward references would resolve to nil at call time).

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

-- ── Craft quantity milestone checks ──────────────────────────────────────────
-- Called each poll tick. Reads the AP-client-written config
-- ("dwarfipelago/craft_checks") and fires a location check for each
-- entry whose cumulative craft count has reached its threshold.
-- The config is a JSON array written by the AP client in _sync_slot_data:
--   [{"flag": "metal_bar", "threshold": 10, "id": 37370500, "name": "..."}]

local function check_craft_milestones()
    for _, cfg in ipairs(checks.get_craft_check_configs()) do
        local loc_id    = cfg.id
        local flag      = cfg.flag
        local threshold = cfg.threshold
        if not (loc_id and flag and threshold) then goto continue end
        if state.is_location_checked(loc_id) then goto continue end

        if checks.get_craft_count(flag) >= threshold then
            local newly_checked = state.mark_location_checked(loc_id)
            if newly_checked then
                local queue_key = "dwarfipelago/pending_checks"
                local raw   = dfhack.persistent.getWorldDataString(queue_key) or "[]"
                local queue = json.decode(raw) or {}
                table.insert(queue, loc_id)
                dfhack.persistent.saveWorldDataString(queue_key, json.encode(queue))

                local label = cfg.name or (flag .. " x" .. tostring(threshold))
                dfhack.gui.showAnnouncement(
                    ("[AP] Craft milestone reached: %s!"):format(label),
                    COLOR_GREEN, true)
                print(("[Dwarfipelago] Craft milestone: %s count>=%d (location %d)"):format(
                    flag, threshold, loc_id))
            end
        end
        ::continue::
    end
end

-- ── Poll loop: wealth, trade, and goal milestones ─────────────────────────────
-- Runs every POLL_TICKS game ticks. Production checks are handled by eventful.

local function poll_checks()
    if not state.is_enabled() then return end

    apply_pending_recv_deathlinks()
    check_goal_by_poll()
    detect_caravans()
    detect_trade_export()
    check_craft_milestones()

    for _, check in ipairs(checks.checks) do
        if not state.is_location_checked(check.id) then
            local ok, result = pcall(check.fn)
            if ok and result then
                local newly_checked = state.mark_location_checked(check.id)
                if newly_checked then
                    local queue_key = "dwarfipelago/pending_checks"
                    local raw = dfhack.persistent.getWorldDataString(queue_key) or "[]"
                    local queue = json.decode(raw) or {}
                    table.insert(queue, check.id)
                    dfhack.persistent.saveWorldDataString(queue_key, json.encode(queue))

                    print(("[Dwarfipelago] Check: %s (%d)"):format(check.name, check.id))
                end
            end
        end
    end
end

-- ── eventful hook: job completion → production flags ─────────────────────────

local function on_job_completed(job)
    if not state.is_enabled() then return end

    -- Boolean first-production flags (drive the existing BASE_ID+100 checks).
    local prod_flag = checks.job_to_production_flag(job)
    if prod_flag and not checks.production_flag(prod_flag) then
        checks.set_production_flag(prod_flag)
    end

    -- Cumulative craft counts (drive the new quantity-based checks).
    -- Uses specific AP option names (door, cage, metal, cloth, …) rather than
    -- the generic aggregated names used by the boolean system above.
    local craft_flag = checks.job_to_craft_flag(job)
    if craft_flag then
        checks.increment_craft_count(craft_flag)
    end
end

-- ── Workshop / furnace / building blueprint enforcement ─────────────────────
-- When a dwarf tries to build a locked structure, the job is cancelled.
-- Unlocked blueprints are tracked in persistent storage by the AP client:
--   key "dwarfipelago/blueprint/<name>" = "1" when received.

-- Workshops (df.workshop_type → blueprint name)
-- Built with a helper so nil enum values (names that changed between DF
-- versions) are silently skipped rather than causing "table index is nil".
local WORKSHOP_BLUEPRINTS = {}
local function wmap(name, bp)
    local v = df.workshop_type[name]
    if v ~= nil then WORKSHOP_BLUEPRINTS[v] = bp end
end
wmap("Craftsdwarfs",     "Craftsdwarf's Workshop Blueprint")
wmap("MetalsmithsForge", "Forge Blueprint")
wmap("MagmaForge",       "Magma Forge Blueprint")
wmap("Kitchen",          "Kitchen Blueprint")
wmap("Jewelers",         "Jeweler's Workshop Blueprint")
wmap("Clothiers",        "Clothier's Shop Blueprint")
wmap("Tanners",          "Tanner's Blueprint")
wmap("Mechanics",        "Mechanic's Workshop Blueprint")
wmap("Siege",            "Siege Workshop Blueprint")
wmap("SoapMaker",        "Soap Maker's Workshop Blueprint")
wmap("Ashery",           "Ashery Blueprint")
wmap("Bowyers",          "Bowyer's Workshop Blueprint")
wmap("ScrewPress",       "Screw Press Blueprint")
wmap("Fishery",          "Fishery Blueprint")
wmap("Loom",             "Loom Blueprint")
wmap("Dyers",            "Dyer's Workshop Blueprint")
wmap("Butchers",         "Butcher's Shop Blueprint")
wmap("Farmers",          "Farmer's Workshop Blueprint")

-- Furnaces (df.furnace_type → blueprint name)
local FURNACE_BLUEPRINTS = {}
local function fmap(name, bp)
    local v = df.furnace_type[name]
    if v ~= nil then FURNACE_BLUEPRINTS[v] = bp end
end
fmap("Smelter",           "Smelter Blueprint")
fmap("MagmaSmelter",      "Magma Smelter Blueprint")
fmap("WoodFurnace",       "Wood Furnace Blueprint")
fmap("GlassFurnace",      "Glass Furnace Blueprint")
fmap("Kiln",              "Kiln Blueprint")
fmap("MagmaKiln",         "Magma Kiln Blueprint")
fmap("MagmaGlassFurnace", "Magma Glass Furnace Blueprint")

local function is_blueprint_unlocked(blueprint_name)
    local val = dfhack.persistent.getWorldDataString("dwarfipelago/blueprint/" .. blueprint_name)
    return val == "1"
end

function unlock_blueprint(blueprint_name)
    dfhack.persistent.saveWorldDataString("dwarfipelago/blueprint/" .. blueprint_name, "1")
    dfhack.gui.showAnnouncement(
        ("[AP] Blueprint received: %s"):format(blueprint_name),
        COLOR_GREEN, true)
    print(("[Dwarfipelago] Blueprint unlocked: %s"):format(blueprint_name))
end

-- Hook: cancel construction of locked workshops, furnaces, and farm plots.
-- Called via eventful.onJobInitiated — fires when a new job is created.
local function on_job_initiated(job)
    if not state.is_enabled() then return end

    -- Only care about construction jobs.
    if job.job_type ~= df.job_type.ConstructBuilding then return end

    local bld = dfhack.job.getHolder(job)
    if not bld then return end

    local blueprint_name = nil

    -- Check workshops
    if df.building_workshopst:is_instance(bld) then
        blueprint_name = WORKSHOP_BLUEPRINTS[bld.type]

    -- Check furnaces
    elseif df.building_furnacest:is_instance(bld) then
        blueprint_name = FURNACE_BLUEPRINTS[bld.type]

    -- Check farm plots
    elseif df.building_farmplotst:is_instance(bld) then
        blueprint_name = "Farm Plot Blueprint"
    end

    if not blueprint_name then return end  -- ungated building, allow it

    if not is_blueprint_unlocked(blueprint_name) then
        dfhack.job.removeJob(job)
        dfhack.gui.showAnnouncement(
            ("[AP] Cannot build: %s not yet received!"):format(blueprint_name),
            COLOR_YELLOW, true)
    end
end

-- ── Start / stop ──────────────────────────────────────────────────────────────

local function start()
    state.set_enabled(true)

    -- Register hooks
    eventful.onJobCompleted[SCRIPT_NAME] = on_job_completed
    eventful.onUnitDeath[SCRIPT_NAME]    = on_unit_death
    eventful.onJobInitiated[SCRIPT_NAME] = on_job_initiated

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
    eventful.onJobInitiated[SCRIPT_NAME] = nil
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
        dfhack.printerr("Usage: dwarfipelago receive <Item Name>")
    else
        items.receive(item_name)
    end
else
    print("Usage: dwarfipelago [start|stop|status|reset|receive <item>]")
end
