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

-- Per-session tracking for "milestone reached but locked" notifications.
-- Keyed by AP location ID; prevents repeating the same announcement every poll.
local _notified_locked = {}

-- Set to true once natural megabeasts have been cleared for the slay_megabeast goal.
-- Reset each script load so a fresh cleanup runs on every fortress load.
local _megabeast_cleanup_done = false

local WEALTH_LOCK_TIERS = {
    { id = 37370000, threshold = 1000,   coffers = 1, name = "Humble Beginnings"   },
    { id = 37370001, threshold = 10000,  coffers = 2, name = "Growing Stronghold"  },
    { id = 37370002, threshold = 50000,  coffers = 3, name = "Prosperous Fortress" },
    { id = 37370003, threshold = 100000, coffers = 4, name = "Rich Citadel"        },
    { id = 37370004, threshold = 500000, coffers = 5, name = "Legendary Vault"     },
}

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
        if checks.treasury_wealth() >= target
                and goal_setting("unlock/wealth_coffers", 0) >= 5
                and goal_setting("unlock/immigration_waves", 0) >= 3 then
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
        if count >= target
                and goal_setting("unlock/immigration_waves", 0) >= 5 then  -- population_boom
            if state.mark_goal_complete() then
                dfhack.gui.showAnnouncement(
                    ("[AP] Goal reached: Population Boom! (%d dwarves). Victory!"):format(count),
                    COLOR_CYAN, true)
                print("[Dwarfipelago] Goal complete: Population Boom!")
            end
        end

    elseif goal == 3 then  -- mountainhome
        -- Mountainhome is achieved when the monarch (king/queen) takes residence
        -- and the Monarch's Invitation has been received from the multiworld.
        local ok_k, has_king  = pcall(dfhack.units.getUnitsByNobleRole, "KING")
        local ok_q, has_queen = pcall(dfhack.units.getUnitsByNobleRole, "QUEEN")
        local has_monarch = (ok_k and has_king and #has_king > 0)
                         or (ok_q and has_queen and #has_queen > 0)
        if has_monarch
                and goal_setting("unlock/monarch_invitation", 0) == 1
                and goal_setting("unlock/immigration_waves", 0) >= 5 then
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
        if ok and is_mega
                and goal_setting("unlock/military_training", 0) >= 3
                and goal_setting("unlock/immigration_waves", 0) >= 2 then
            -- Only count the AP-summoned target; ignore any stray megabeasts.
            -- If no target ID is stored (fallback), any megabeast kill counts.
            local target_id = tonumber(
                dfhack.persistent.getWorldDataString("dwarfipelago/megabeast/target_id"))
            local is_target = (not target_id) or (unit.id == target_id)
            if is_target then
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

    local threshold     = goal_setting("deathlink_threshold", 5)
    local is_percentage = goal_setting("deathlink_percentage", 0) == 1

    local per_link
    if is_percentage then
        local pop = 0
        for _, unit in ipairs(df.global.world.units.active) do
            if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
                pop = pop + 1
            end
        end
        per_link = math.max(1, math.floor(pop * threshold / 100))
    else
        per_link = threshold
    end
    local to_kill = pending * per_link

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

-- ── Megabeast goal: remove natural megabeasts ────────────────────────────────
-- For the slay_megabeast goal, all naturally-spawned megabeasts are silently
-- removed when the fortress loads. The AP-controlled target is summoned via
-- Military Training items instead, keeping the encounter on the multiworld's
-- terms. Natural megabeasts that were already killed in a previous session are
-- simply absent — this scan is fast and safe to repeat on each reload.

local function cleanup_natural_megabeasts()
    if _megabeast_cleanup_done then return end

    local goal = goal_setting("goal", -1)
    if goal == -1 then return end  -- slot data not yet synced from Python; retry next tick

    _megabeast_cleanup_done = true
    if goal ~= 0 then return end  -- only relevant for slay_megabeast

    -- Don't remove the AP-summoned target if it already exists this world.
    local target_id = tonumber(
        dfhack.persistent.getWorldDataString("dwarfipelago/megabeast/target_id"))

    local cleaned = 0
    for _, unit in ipairs(df.global.world.units.all) do
        local ok, alive = pcall(dfhack.units.isAlive, unit)
        if ok and alive then
            local ok2, is_mega = pcall(dfhack.units.isMegabeast, unit)
            if ok2 and is_mega and unit.id ~= target_id then
                pcall(function()
                    if dfhack.units.kill then
                        dfhack.units.kill(unit)
                    else
                        unit.body.blood_count = 0
                    end
                end)
                cleaned = cleaned + 1
            end
        end
    end

    if cleaned > 0 then
        print(("[Dwarfipelago] Cleared %d natural megabeast(s) — AP target arrives via Military Training"):format(cleaned))
    end
end

-- ── Locked milestone notifications ───────────────────────────────────────────
-- When a wealth tier threshold is met in-game but the matching Merchant's Coffer
-- hasn't arrived yet, announce it once so the player knows to look for it.
-- Fires at most once per tier per session; skips tiers already checked.

local function check_locked_notifications()
    local coffers = goal_setting("unlock/wealth_coffers", 0)
    local wealth  = checks.treasury_wealth()
    for _, tier in ipairs(WEALTH_LOCK_TIERS) do
        if not state.is_location_checked(tier.id)
                and not _notified_locked[tier.id]
                and wealth >= tier.threshold
                and coffers < tier.coffers then
            _notified_locked[tier.id] = true
            dfhack.gui.showAnnouncement(
                ("[AP] %s reached — waiting for Merchant's Coffer (%d/5)"):format(
                    tier.name, coffers),
                COLOR_YELLOW, true)
            print(("[Dwarfipelago] Wealth milestone locked: %s (have %d/5 coffers)"):format(
                tier.name, coffers))
        end
    end
end

-- Forward declaration so poll_checks can call ensure_trade_depot, which is
-- defined later in the file (after the item event helpers).
local ensure_trade_depot

-- ── Poll loop: wealth, trade, and goal milestones ─────────────────────────────
-- Runs every POLL_TICKS game ticks. Production checks are handled by eventful.

local function poll_checks()
    if not state.is_enabled() then return end
    -- repeatUtil fires the callback immediately on registration, and again
    -- during world-loading screens.  Do nothing until the fortress map is
    -- fully live and the simulation is running.
    if not dfhack.isMapLoaded() then return end

    -- All AP checks are gated on a trade depot existing.  ensure_trade_depot
    -- retries every poll tick (every POLL_TICKS game ticks) until it succeeds,
    -- so it naturally defers until units and map data are fully loaded.
    cleanup_natural_megabeasts()

    if dfhack.persistent.getWorldDataString("dwarfipelago/depot_built") ~= "1" then
        ensure_trade_depot()
        return
    end

    apply_pending_recv_deathlinks()
    check_goal_by_poll()
    check_locked_notifications()
    detect_caravans()
    detect_trade_export()

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

    -- Cumulative craft counts — incremented here, polled by the AP client.
    -- Threshold comparisons and location check firing happen on the Python side.
    local craft_flag = checks.job_to_craft_flag(job)
    if craft_flag then
        checks.increment_craft_count(craft_flag)
        if craft_flag == "honey" then
            checks.increment_craft_count("bee_wax")
        elseif craft_flag == "oil" then
            checks.increment_craft_count("press_cake")
        end
    end

    -- Stockpile detection: StoreItemInStockpile fires when a dwarf deposits an
    -- item. Used in place of the non-existent onItemPutInStockpile event.
    if job.job_type == df.job_type.StoreItemInStockpile then
        for _, item_ref in ipairs(job.items) do
            local item = df.item.find(item_ref.item_id)
            local info = item_to_info(item)
            if info then
                for _, ref in ipairs(item.general_refs) do
                    if df.general_ref_building_holderst:is_instance(ref) then
                        local bld = df.building.find(ref.building_id)
                        if bld and df.building_stockpilest:is_instance(bld) then
                            info.stockpile_name   = bld.name ~= "" and bld.name or nil
                            info.stockpile_number = bld.stockpile_number
                            break
                        end
                    end
                end
                queue_item_event("dwarfipelago/pending_item_stockpiled", info)
            end
        end
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

-- ── Item event helpers ────────────────────────────────────────────────────────

local ITEM_EVENT_CAP = 500  -- prevent runaway growth if Python client is slow

-- Item types we don't care about for AP tracking purposes.
local SKIP_ITEM_TYPES = {
    CORPSE = true, CORPSEPIECE = true, REMAINS = true, VERMIN = true,
    PLANT = true, PLANT_GROWTH = true, FISH_RAW = true, BODY_PARTS=true,
}

-- Converts a df.item pointer to a plain table safe for JSON serialisation.
-- Returns nil for item types in the skip list or if the item is invalid.
local function item_to_info(item)
    if not item then return nil end
    local type_name = df.item_type[item:getType()] or "UNKNOWN"
    if SKIP_ITEM_TYPES[type_name] then return nil end

    local mat_str = "unknown"
    local ok, mat = pcall(dfhack.matinfo.decode, item)
    if ok and mat then
        mat_str = mat:toString() or mat_str
    end

    -- Not all item structs expose a quality field (e.g. REMAINS, LIQUID_MISC).
    local quality = 0
    pcall(function() quality = item.quality end)

    return {
        id       = item.id,
        type     = type_name,
        material = mat_str,
        quality  = quality,
        artifact = item.flags.artifact == true,
    }
end

-- Append one entry to a world-data JSON queue, capping at ITEM_EVENT_CAP.
local function queue_item_event(key, entry)
    local raw   = dfhack.persistent.getWorldDataString(key) or "[]"
    local queue = json.decode(raw) or {}
    table.insert(queue, entry)
    if #queue > ITEM_EVENT_CAP then table.remove(queue, 1) end
    dfhack.persistent.saveWorldDataString(key, json.encode(queue))
end

-- ── onItemCreated hook ────────────────────────────────────────────────────────
-- Fires whenever DF creates a new item (crafted output, dropped loot, etc.).
-- Pushes item info to "dwarfipelago/pending_item_created" for the Python client.

local function on_item_created(item_id)
    if not state.is_enabled() then return end
    local info = item_to_info(df.item.find(item_id))
    if info then
        queue_item_event("dwarfipelago/pending_item_created", info)
    end
end

-- ── Starting trade depot ──────────────────────────────────────────────────────
-- On the first start of a new world, build a Trade Depot near the starting
-- wagon so AP-delivered items land in a predictable, accessible location.
-- Runs once per world; the result is stored in persistent data.

ensure_trade_depot = function()
    if dfhack.persistent.getWorldDataString("dwarfipelago/depot_built") == "1" then
        return  -- already placed this world
    end

    -- If the player already built a trade depot, adopt it as the delivery point.
    for _, bld in ipairs(df.global.world.buildings.all) do
        if df.building_tradedepotst:is_instance(bld) then
            dfhack.persistent.saveWorldDataString("dwarfipelago/depot_built", "1")
            print("[Dwarfipelago] Existing trade depot adopted as AP delivery point.")
            return
        end
    end

    -- Find the starting position.
    -- Priority 1: embark wagon (VEHICLE item — present on fresh embark)
    local sx, sy, sz
    pcall(function()
        for _, item in ipairs(df.global.world.items.all) do
            if item:getType() == df.item_type.VEHICLE then
                sx, sy, sz = item.pos.x, item.pos.y, item.pos.z
                return
            end
        end
    end)
    -- Priority 2: citizen scan
    if not sx then
        for _, unit in ipairs(df.global.world.units.active) do
            if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
                sx, sy, sz = unit.pos.x, unit.pos.y, unit.pos.z
                break
            end
        end
    end
    -- Priority 3: any alive unit
    if not sx then
        for _, unit in ipairs(df.global.world.units.active) do
            if dfhack.units.isAlive(unit) then
                sx, sy, sz = unit.pos.x, unit.pos.y, unit.pos.z
                break
            end
        end
    end
    -- Priority 4: map center, z borrowed from any unit at all
    if not sx then
        local m = df.global.world.map
        for _, unit in ipairs(df.global.world.units.active) do
            if unit.pos.z > 0 then
                sx = math.floor(m.x_count / 2)
                sy = math.floor(m.y_count / 2)
                sz = unit.pos.z
                break
            end
        end
    end
    if not sx then
        dfhack.printerr("[Dwarfipelago] ensure_trade_depot: no position found — will retry next load")
        return
    end

    -- Helper: clear a 5×5 area and attempt to place the depot there.
    -- Returns the constructed building on success, nil on failure.
    local map = df.global.world.map
    local function try_place(tx, ty)
        -- Clamp so the full 5×5 footprint stays inside the map.
        tx = math.max(1, math.min(tx, map.x_count - 6))
        ty = math.max(1, math.min(ty, map.y_count - 6))
        local x2, y2 = tx + 4, ty + 4

        -- Flatten terrain: convert walls/ramps/trees to floor so the depot
        -- can be placed.  findSimilarTileType picks the closest floor variant
        -- for the existing material; the pcall guards against any API mismatch.
        for dy = 0, 4 do
            for dx = 0, 4 do
                pcall(function()
                    local bx, by = tx + dx, ty + dy
                    local block = dfhack.maps.getTileBlock(bx, by, sz)
                    if not block then return end
                    local lx, ly = bx % 16, by % 16
                    local new_tt = dfhack.maps.findSimilarTileType(
                        block.tiletype[lx][ly], df.tiletype_shape.FLOOR)
                    if new_tt and new_tt ~= 0 then
                        block.tiletype[lx][ly] = new_tt
                        block.designation[lx][ly].hidden = false
                    end
                end)
            end
        end

        -- Clear buildings overlapping the footprint.
        local blds_to_remove = {}
        for _, b in ipairs(df.global.world.buildings.all) do
            if b.z == sz and b.x1 <= x2 and b.x2 >= tx and
                             b.y1 <= y2 and b.y2 >= ty then
                table.insert(blds_to_remove, b)
            end
        end
        for _, b in ipairs(blds_to_remove) do
            pcall(function() dfhack.buildings.deconstruct(b) end)
        end

        -- Clear items on the footprint.
        local items_to_remove = {}
        for _, item in ipairs(df.global.world.items.all) do
            if item.pos.z == sz and
               item.pos.x >= tx and item.pos.x <= x2 and
               item.pos.y >= ty and item.pos.y <= y2 then
                table.insert(items_to_remove, item)
            end
        end
        for _, item in ipairs(items_to_remove) do
            pcall(function() dfhack.items.remove(item) end)
        end

        -- Attempt construction.
        local ok, result = pcall(function()
            return dfhack.buildings.constructBuilding{
                type   = df.building_type.TradeDepot,
                pos    = {x = tx, y = ty, z = sz},
                width  = 5,
                height = 5,
            }
        end)
        if ok and result then
            return result, tx, ty
        end
        return nil
    end

    -- Try each cardinal direction (7 tiles out), west first.
    local candidates = {
        { sx - 7, sy     },  -- west
        { sx + 7, sy     },  -- east
        { sx,     sy - 7 },  -- north
        { sx,     sy + 7 },  -- south
    }
    local bld, tx, ty
    for _, c in ipairs(candidates) do
        local b, px, py = try_place(c[1], c[2])
        if b then
            bld, tx, ty = b, px, py
            break
        end
        print(("[Dwarfipelago] Depot placement failed at %d,%d — trying next direction"):format(c[1], c[2]))
    end

    if not bld then
        dfhack.printerr("[Dwarfipelago] Failed to place trade depot in any direction")
        return
    end

    -- Instantly complete: set to max build stage, then remove the construction
    -- job so no dwarf tries to "finish" it and triggers a materials warning.
    pcall(function()
        local max = bld:getMaxBuildStage()
        if max and max > 0 then bld:setBuildStage(max) end
    end)
    pcall(function()
        local to_remove = {}
        for i = 0, #bld.jobs - 1 do
            local job = bld.jobs[i]
            if job and job.job_type == df.job_type.ConstructBuilding then
                table.insert(to_remove, job)
            end
        end
        for _, job in ipairs(to_remove) do
            dfhack.job.removeJob(job)
        end
    end)

    dfhack.persistent.saveWorldDataString("dwarfipelago/depot_built", "1")
    dfhack.gui.showAnnouncement(
        "[AP] A Trading Post has been established near your starting wagon!",
        COLOR_GREEN, true)
    print(("[Dwarfipelago] Trade depot placed at %d,%d,%d"):format(tx, ty, sz))
end

-- ── Start / stop ──────────────────────────────────────────────────────────────

local function start()
    state.set_enabled(true)

    -- Register hooks
    eventful.onJobCompleted[SCRIPT_NAME]        = on_job_completed
    eventful.onUnitDeath[SCRIPT_NAME]           = on_unit_death
    eventful.onJobInitiated[SCRIPT_NAME]        = on_job_initiated
    -- enableEvent initializes the onItemCreated hook table; without this call
    -- the table is nil and the registration below silently does nothing.
    eventful.enableEvent(eventful.eventType.ITEM_CREATED, 1)
    eventful.enableEvent(eventful.eventType.JOB_COMPLETED, 1)
    eventful.enableEvent(eventful.eventType.JOB_INITIATED, 1)
    eventful.enableEvent(eventful.eventType.UNIT_DEATH, 1)
    eventful.onItemCreated[SCRIPT_NAME] = on_item_created

    -- Register poll loop
    repeatUtil.scheduleEvery(SCRIPT_NAME, POLL_TICKS, "ticks", poll_checks)

    print("[Dwarfipelago] Started. Listening for fortress milestones.")
    print("[Dwarfipelago] Make sure DwarfFortressClient.py is running.")
end

local function stop()
    state.set_enabled(false)

    -- Unregister hooks
    eventful.onJobCompleted[SCRIPT_NAME]        = nil
    eventful.onUnitDeath[SCRIPT_NAME]           = nil
    eventful.onJobInitiated[SCRIPT_NAME]        = nil
    if eventful.onItemCreated then
        eventful.onItemCreated[SCRIPT_NAME] = nil
    end
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
