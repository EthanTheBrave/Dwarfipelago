-- Dwarfipelago main entry point.
-- Usage (DFHack console):
--   dwarfipelago start              -- enable and register hooks
--   dwarfipelago stop               -- disable and unregister hooks
--   dwarfipelago status             -- show current state
--   dwarfipelago reset              -- wipe persistent state (use with care)
--   dwarfipelago resetseed          -- clear AP seed lock so this world can join a new slot
--   dwarfipelago receive <item>     -- manually deliver an item (for testing)
--   dwarfipelago test <name> [args] -- run a mechanic verification test (e.g. spawn, goblin)

-- Internal modules live under internal/dwarfipelago/ to keep them out of the
-- DFHack launcher autocomplete. Use reqscript (not require) so they hot-reload
-- when edited without restarting DFHack.
local state  = reqscript("internal/dwarfipelago/state")
local checks = reqscript("internal/dwarfipelago/checks")
local items  = reqscript("internal/dwarfipelago/items")
local log    = reqscript("internal/dwarfipelago/log")
local json   = require('json')

-- DFHack built-in plugins use the standard require().
local eventful   = require("plugins.eventful")
local repeatUtil = require("repeat-util")

local SCRIPT_NAME = "dwarfipelago"
local SCRIPT_VERSION = "1.0.5"
local POLL_TICKS  = 100  -- poll wealth/trade/goal checks every N ticks

-- Set to true while we are applying a received DeathLink so that the death
-- hook does not count those kills toward our own outgoing DeathLink threshold.
local applying_recv_deathlink = false

-- Job types that count as "mining" for the depth / tiles-excavated milestones.
-- Built defensively so names absent in a given DF version are skipped.
local MINING_JOBS = {}
for _, name in ipairs({
    "Dig", "CarveUpwardStaircase", "CarveDownwardStaircase",
    "CarveUpDownStaircase", "CarveRamp", "DigChannel",
}) do
    local v = df.job_type[name]
    if v ~= nil then MINING_JOBS[v] = true end
end

-- Reverse-map a block's global_feature id to the embark's map_feature object.
-- World-independent: feature_global_idx maps each map_features[i] to its global
-- id, so we scan it live (~11 entries) rather than hardcoding anything.
local function feature_for_global(gf)
    local feat
    pcall(function()
        for i, gid in ipairs(df.global.world.features.feature_global_idx) do
            if gid == gf then
                feat = df.global.world.features.map_features[i]
                return
            end
        end
    end)
    return feat
end

-- Set a mining milestone flag once, announcing the first time it's reached.
local function set_mining_milestone(key, msg)
    local k = "dwarfipelago/mining/" .. key
    if dfhack.persistent.getWorldDataString(k) ~= "1" then
        dfhack.persistent.saveWorldDataString(k, "1")
        dfhack.gui.showAnnouncement("[AP] " .. msg, COLOR_GREEN, true)
        log.info("Mining milestone: " .. msg)
    end
end

-- Per-session tracking for "milestone reached but locked" notifications.
-- Keyed by AP location ID; prevents repeating the same announcement every poll.
local _notified_locked = {}

-- Set to true once natural megabeasts have been cleared for the slay_megabeast goal.
-- Reset each script load so a fresh cleanup runs on every fortress load.
local _megabeast_cleanup_done = false

-- Per-tier announcement tracking for treasury job blocking.
-- Prevents spam when standing orders keep retrying a blocked MintCoins/CutGems job.
-- Keyed by coffer count (0 = no coffers yet, 1–4 = tier cap reached).
-- Resets on each script load so the player gets a reminder after every reload.
local _treasury_block_notified = {}

-- Per-flag announcement tracking for crafting item locks. Prevents an announcement
-- flood when a workshop or work order queues many instances of a locked job type.
-- Keyed by base craft flag string. Resets on each script load.
local _craftlock_notified = {}

local WEALTH_LOCK_TIERS = {
    { id = 37370000, threshold = 1000,   coffers = 1, name = "Humble Beginnings (1,000)"    },
    { id = 37370001, threshold = 10000,  coffers = 2, name = "Growing Stronghold (10,000)"  },
    { id = 37370002, threshold = 50000,  coffers = 3, name = "Prosperous Fortress (50,000)" },
    { id = 37370003, threshold = 100000, coffers = 4, name = "Rich Citadel (100,000)"       },
    { id = 37370004, threshold = 500000, coffers = 5, name = "Legendary Vault (500,000)"    },
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

    -- goal == 0 (slay_megabeast) is handled by the on_unit_death hook below.

    if goal == 1 then  -- legendary_wealth
        local target = goal_setting("wealth_goal", 100000)
        if checks.treasury_wealth() >= target
                and goal_setting("unlock/wealth_coffers", 0) >= 5
                and goal_setting("unlock/immigration_waves", 0) >= 3
                and goal_setting("unlock/master_builders_codex", 0) == 1 then
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
        local has_prestige = goal_setting("unlock/master_builders_codex", 0) == 1
                          or goal_setting("unlock/artifact_weapon", 0) == 1
                          or goal_setting("unlock/artifact_armor", 0) == 1
        if count >= target
                and goal_setting("unlock/immigration_waves", 0) >= 5
                and has_prestige then
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
                and goal_setting("unlock/immigration_waves", 0) >= 5
                and goal_setting("unlock/master_builders_codex", 0) == 1
                and goal_setting("unlock/artifact_weapon", 0) == 1 then
            if state.mark_goal_complete() then
                dfhack.gui.showAnnouncement(
                    "[AP] Goal reached: Mountainhome! The monarch has arrived. Victory!",
                    COLOR_CYAN, true)
                print("[Dwarfipelago] Goal complete: Mountainhome!")
            end
        end
    elseif goal == 4 then -- Remains of the Great King
        -- RotGK is achieved when you received all your remains
        amt = goal_setting("unlock/RotGK", 0)
        if amt >= goal_setting("king_remains_goal", 100) then
            if state.mark_goal_complete() then
                dfhack.gui.showAnnouncement(
                    "[AP] Goal reached: Remains of the Great King! The Great King is fully assembled back in our great halls. Victory!",
                    COLOR_CYAN, true)
                print("[Dwarfipelago] Goal complete: Remains of the Great King!")
            end
        end
    end
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
                and goal_setting("unlock/military_training", 0) >= 4
                and goal_setting("unlock/immigration_waves", 0) >= 2
                and goal_setting("unlock/artifact_weapon", 0) == 1 then
            -- Only count the AP-summoned target; ignore any stray megabeasts.
            -- If no target ID is stored (fallback), any megabeast kill counts.
            local target_id = tonumber(
                dfhack.persistent.getWorldDataString("dwarfipelago/megabeast/target_id"))
            local is_target = (not target_id) or (unit.id == target_id)
            if is_target then
                if state.mark_goal_complete() then
                    -- Version-safe name lookup (dfhack.TranslateName is absent in
                    -- newer DFHack; getReadableName replaces it).
                    local name = ""
                    pcall(function()
                        if dfhack.units.getReadableName then
                            name = dfhack.units.getReadableName(unit) or ""
                        elseif dfhack.translation and dfhack.translation.translateName then
                            name = dfhack.translation.translateName(dfhack.units.getVisibleName(unit)) or ""
                        elseif dfhack.TranslateName then
                            name = dfhack.TranslateName(dfhack.units.getVisibleName(unit)) or ""
                        end
                    end)
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
            log.error("kill unit failed: " .. tostring(err))
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

-- True if a Civilization entity of the given creature token exists in this world.
local function civ_exists(token)
    local creatures = df.global.world.raws.creatures.all
    for _, ent in ipairs(df.global.world.entities.all) do
        local ok, match = pcall(function()
            local r = ent.race
            return ent.type == df.historical_entity_type.Civilization
                and r >= 0 and r < #creatures and creatures[r].creature_id == token
        end)
        if ok and match then return true end
    end
    return false
end

-- An elf/human caravan can never visit if that civilisation doesn't exist in the
-- world, which would leave its "X Caravan Visit" location permanently unreachable
-- (an AP soft-lock). Auto-satisfy those checks once so the multiworld stays
-- completable. The dwarven caravan always comes from the parent civ, so it's
-- never auto-satisfied.
local _caravan_autosat_done = false
local function auto_satisfy_absent_caravans()
    if _caravan_autosat_done then return end
    _caravan_autosat_done = true
    for token, flag in pairs({ ELF = "elven_caravan", HUMAN = "human_caravan" }) do
        if not checks.trade_flag(flag) and not civ_exists(token) then
            checks.set_trade_flag(flag)
            print(("[Dwarfipelago] No %s civilization in this world; auto-satisfied %s.")
                :format(token, flag))
        end
    end
end

local function detect_caravans()
    auto_satisfy_absent_caravans()
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

-- ability to force a caravan
local function getCiv(civ)
    civ = string.lower(tostring(civ))
    for _,entity in ipairs(df.global.world.entities.all) do
        if string.lower(entity.entity_raw.code) == civ then return entity end
    end
end

local function spawnCaravan()
    civ = getCiv("MOUNTAIN")  -- FOREST = Elves / PLAINS = humans / MOUNTAIN = dwarves
    df.global.timed_events:insert('#', {
        new=true,
        type=df.timed_event_type['Caravan'],
        season=df.global.cur_season,
        season_ticks=df.global.cur_season_tick,
        entity=civ,
        feature_ind=-1,
    })
    dfhack.persistent.saveWorldDataString("dwarfipelago/use_energy_link", "Y")
end


-- Detect first trade / first export by checking the fortress exported-wealth
-- counter. DF increments this when goods are sold to a caravan, so a value
-- above zero means at least one trade has been completed.
local function detect_trade_export()
    if checks.trade_flag("trade_completed") and checks.trade_flag("first_export") then
        return  -- both already fired
    end

    -- Use the same multi-path lookup that checks.lua uses for wealth-gate checks.
    -- DF50 Steam nests exported wealth as tasks.wealth.exported; Classic uses a
    -- flat tasks.wealth_exported field.  exported_wealth() tries both forms and
    -- both global bases (plotinfo / ui) so we don't miss either variant.
    local exported = checks.exported_wealth()

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

-- ── Manager work-order tracking ───────────────────────────────────────────────
-- eventful.onJobCompleted does NOT fire for jobs generated by Manager work
-- orders, so those crafts never reach on_job_completed. Instead we watch each
-- order's amount_left and count the difference when it drops, resolving the
-- craft flag from the order itself (it carries the same job_type/item_subtype/
-- mat_type fields a job does). Manual jobs still count via on_job_completed, so
-- this only fills the work-order gap and does not double-count.
local _order_amounts    = {}     -- order id -> last seen amount_left
local _order_probe_logged = false

local function poll_manager_orders()
    local ok, list = pcall(function()
        local mo = df.global.world.manager_orders
        return mo.all or mo
    end)
    if not ok or not list then return end

    if not _order_probe_logged then
        _order_probe_logged = true
        local n = 0
        pcall(function() for _ in ipairs(list) do n = n + 1 end end)
        log.info(("Manager-order tracking active (%d order(s) present)."):format(n))
    end

    local seen = {}
    for _, order in ipairs(list) do
        local id   = order.id
        local left = order.amount_left
        if id ~= nil and left ~= nil then
            seen[id] = true
            local prev = _order_amounts[id]
            if prev and left < prev then
                local delta = prev - left
                local flag
                pcall(function() flag = checks.job_to_craft_flag(order) end)
                if flag then
                    for _ = 1, delta do checks.increment_craft_count(flag) end
                    if flag == "honey" then
                        for _ = 1, delta do checks.increment_craft_count("bee_wax") end
                    elseif flag == "oil" then
                        for _ = 1, delta do checks.increment_craft_count("press_cake") end
                    end
                end
                local pflag
                pcall(function() pflag = checks.job_to_production_flag(order) end)
                if pflag and not checks.production_flag(pflag) then
                    checks.set_production_flag(pflag)
                end
            end
            _order_amounts[id] = left
        end
    end
    -- Drop tracking for orders that no longer exist.
    for id in pairs(_order_amounts) do
        if not seen[id] then _order_amounts[id] = nil end
    end
end

-- ── Screw pump activity ───────────────────────────────────────────────────────
-- Fires pump_water or pump_magma the first time a powered screw pump is found
-- adjacent to the appropriate liquid.  Runs every poll tick; bails as soon as
-- both flags are set.
local function detect_pump_activity()
    if checks.production_flag("pump_water") and checks.production_flag("pump_magma") then return end

    local function liquid_at(x, y, z)
        local ok, blk = pcall(dfhack.maps.getTileBlock, x, y, z)
        if not ok or not blk then return nil end
        local des = blk.designation[x % 16][y % 16]
        if not des then return nil end
        local flow = 0
        pcall(function() flow = des.flow_size end)
        if flow == 0 then return nil end
        local is_magma = false
        pcall(function() is_magma = des.liquid_type end)
        return is_magma and "magma" or "water"
    end

    pcall(function()
        for _, bld in ipairs(df.global.world.buildings.all) do
            local ok_t, btype = pcall(function() return bld:getType() end)
            if not (ok_t and btype == df.building_type.ScrewPump) then goto skip_pump end

            -- Must be connected to a machine network (power source present).
            local connected = false
            pcall(function() connected = bld.machine_id >= 0 end)
            if not connected then goto skip_pump end

            -- Check the five tiles that could be the intake: directly below,
            -- and the four horizontal neighbours one level down.
            local x, y, z = bld.x1, bld.y1, bld.z
            for _, d in ipairs({{0,0,-1},{-1,0,-1},{1,0,-1},{0,-1,-1},{0,1,-1}}) do
                local liq = liquid_at(x + d[1], y + d[2], z + d[3])
                if liq == "water" and not checks.production_flag("pump_water") then
                    checks.set_production_flag("pump_water")
                    dfhack.gui.showAnnouncement("[AP] Water has been pumped!", COLOR_GREEN, true)
                    print("[Dwarfipelago] Check: Pumped Water")
                elseif liq == "magma" and not checks.production_flag("pump_magma") then
                    checks.set_production_flag("pump_magma")
                    dfhack.gui.showAnnouncement("[AP] Magma has been pumped!", COLOR_GREEN, true)
                    print("[Dwarfipelago] Check: Pumped Magma")
                end
            end
            if checks.production_flag("pump_water") and checks.production_flag("pump_magma") then return end
            ::skip_pump::
        end
    end)
end

-- ── Egg hatch detection ───────────────────────────────────────────────────────
-- Scans active units for the born_from_egg flag (set on chicks/hatchlings).
local function detect_egg_hatch()
    if checks.production_flag("egg_hatched") then return end
    pcall(function()
        for _, unit in ipairs(df.global.world.units.active) do
            local ok, from_egg = pcall(function() return unit.flags2.born_from_egg end)
            if ok and from_egg then
                checks.set_production_flag("egg_hatched")
                dfhack.gui.showAnnouncement("[AP] Eggs have hatched in the fortress!", COLOR_GREEN, true)
                print("[Dwarfipelago] Check: First Eggs Hatched")
                return
            end
        end
    end)
end

-- ── Caged megabeast detection ─────────────────────────────────────────────────
local function detect_caged_megabeast()
    if checks.production_flag("caged_megabeast") then return end
    pcall(function()
        for _, unit in ipairs(df.global.world.units.active) do
            local ok, is_mega = pcall(dfhack.units.isMegabeast, unit)
            if ok and is_mega then
                local caged = false
                pcall(function() caged = unit.flags1.caged end)
                if caged then
                    checks.set_production_flag("caged_megabeast")
                    dfhack.gui.showAnnouncement("[AP] A megabeast has been caged!", COLOR_GREEN, true)
                    print("[Dwarfipelago] Check: Caged a Megabeast")
                    return
                end
            end
        end
    end)
end

-- ── Artifact departure detection ──────────────────────────────────────────────
-- Fires sold_artifact when any world artifact's item has been removed from the
-- game (i.e. left the fortress via trade, theft, or other departure).
local function detect_sold_artifact()
    if checks.production_flag("sold_artifact") then return end
    pcall(function()
        for _, artifact in ipairs(df.global.world.artifacts.all) do
            local item_id = -1
            pcall(function() item_id = artifact.item_id end)
            if item_id < 0 then goto skip_art end
            local item = df.item.find(item_id)
            if not item then goto skip_art end
            local gone = false
            pcall(function() gone = item.flags.removed end)
            if not gone then
                pcall(function() gone = item.pos.x < 0 end)
            end
            if gone then
                checks.set_production_flag("sold_artifact")
                dfhack.gui.showAnnouncement("[AP] An artifact has left the fortress!", COLOR_GREEN, true)
                print("[Dwarfipelago] Check: Sold an Artifact")
                return
            end
            ::skip_art::
        end
    end)
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

    -- Capture the surface z-level once, early (before much digging), from a
    -- living citizen's position. Used as the reference for mining-depth checks.
    if not tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/mining/surface_z")) then
        for _, unit in ipairs(df.global.world.units.active) do
            if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
                dfhack.persistent.saveWorldDataString("dwarfipelago/mining/surface_z", tostring(unit.pos.z))
                break
            end
        end
    end

    -- Count Manager work-order completions (their jobs don't fire onJobCompleted).
    -- Done before the depot gate so craft counts accumulate like manual jobs do.
    poll_manager_orders()

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
    detect_pump_activity()
    detect_egg_hatch()
    detect_caged_megabeast()
    detect_sold_artifact()

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

    -- Well construction detection.
    if job.job_type == df.job_type.ConstructBuilding then
        local ok_bld, bld = pcall(dfhack.job.getHolder, job)
        if ok_bld and bld and not checks.production_flag("well") then
            local ok_t, btype = pcall(function() return bld:getType() end)
            if ok_t and btype == df.building_type.Well then
                checks.set_production_flag("well")
                dfhack.gui.showAnnouncement("[AP] A well has been constructed!", COLOR_GREEN, true)
                print("[Dwarfipelago] Check: Built a Well")
            end
        end
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

    -- Mining tracking — count excavation jobs and record the deepest z reached.
    -- Drives the depth and tiles-mined milestone checks (checks.lua).
    if MINING_JOBS[job.job_type] then
        local key_c = "dwarfipelago/mining/dig_count"
        local n = (tonumber(dfhack.persistent.getWorldDataString(key_c)) or 0) + 1
        dfhack.persistent.saveWorldDataString(key_c, tostring(n))

        local ok, jz = pcall(function() return job.pos.z end)
        if ok and jz then
            local key_d = "dwarfipelago/mining/deepest_z"
            local cur = tonumber(dfhack.persistent.getWorldDataString(key_d))
            if not cur or jz < cur then
                dfhack.persistent.saveWorldDataString(key_d, tostring(jz))
            end
        end

        -- Cavern / magma sea breach detection via the dug tile's map feature.
        local okb, blk = pcall(dfhack.maps.getTileBlock, job.pos.x, job.pos.y, job.pos.z)
        if okb and blk then
            local gf = blk.global_feature
            if gf and gf >= 0 then
                local feat = feature_for_global(gf)
                if feat then
                    local t = tostring(feat._type)
                    if t:find("subterranean_from_layers") then
                        local sd = 0
                        pcall(function() sd = feat.start_depth end)
                        if sd == 0 then
                            set_mining_milestone("cavern1", "You have breached the first cavern!")
                        elseif sd == 1 then
                            set_mining_milestone("cavern2", "You have breached the second cavern!")
                        elseif sd == 2 then
                            set_mining_milestone("cavern3", "You have breached the third cavern!")
                        end
                    elseif t:find("magma_core") then
                        set_mining_milestone("magma", "You have reached the Magma Sea!")
                    elseif t:find("underworld") then
                        set_mining_milestone("circus", "You have breached the Circus — the end is nigh!")
                    end
                end
            end
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

-- ── Treasury job gating (MintCoins / CutGems) ────────────────────────────────
-- Blocks coin minting and gem cutting when the current treasury wealth has reached
-- the cap for the player's current Merchant's Coffer tier. Uses the same
-- WEALTH_LOCK_TIERS table as the locked-notification system for consistency.

local TREASURY_JOB_TYPES = {}
local function tjmap(name)
    local v = df.job_type[name]
    if v ~= nil then TREASURY_JOB_TYPES[v] = true end
end
tjmap("MintCoins")
tjmap("CutGems")

local function check_treasury_job_gate(job)
    if not TREASURY_JOB_TYPES[job.job_type] then return end

    local coffers = goal_setting("unlock/wealth_coffers", 0)

    -- No coffers yet — block all minting and cutting.
    if coffers == 0 then
        dfhack.job.removeJob(job)
        if not _treasury_block_notified[0] then
            _treasury_block_notified[0] = true
            dfhack.gui.showAnnouncement(
                "[AP] Cannot mint coins or cut gems — awaiting first Merchant's Coffer!",
                COLOR_YELLOW, true)
        end
        return
    end

    -- All five coffers received — no cap, allow freely.
    if coffers >= 5 then return end

    -- Check whether current treasury has already reached this tier's ceiling.
    local tier = WEALTH_LOCK_TIERS[coffers]
    if checks.treasury_wealth() >= tier.threshold then
        dfhack.job.removeJob(job)
        if not _treasury_block_notified[coffers] then
            _treasury_block_notified[coffers] = true
            dfhack.gui.showAnnouncement(
                ("[AP] %s reached — minting and gem cutting paused. Awaiting Merchant's Coffer (%d/5)."):format(
                    tier.name, coffers),
                COLOR_YELLOW, true)
        end
    end
end

-- ── Crafting item gate ────────────────────────────────────────────────────────
-- When craftitems mode is 1 (on) or 2 (all), every craft job is checked against
-- the craftlock flags written by the "Crafting X" AP item handlers in items.lua.
-- Jobs for locked items are removed one tick after initiation (same pattern as the
-- blueprint gate) and the player is notified once per session per locked item type.

-- Set of flags that can be craft-locked (mirrors CRAFTING_LOCK_ITEMS in items.lua).
local CRAFTLOCK_FLAGS = {}
pcall(function()
    local lock_items = reqscript("internal/dwarfipelago/items").CRAFTING_LOCK_ITEMS
    for _, item_name in ipairs(lock_items) do
        CRAFTLOCK_FLAGS[item_name:lower():gsub(" ", "_")] = true
    end
end)

local function check_craftitem_gate(job)
    local mode = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/crafting_permits")) or 0
    if mode == 0 then return end

    local base_flag
    pcall(function() base_flag = checks.job_to_base_craft_flag(job) end)
    if not base_flag or not CRAFTLOCK_FLAGS[base_flag] then return end

    if dfhack.persistent.getWorldDataString("dwarfipelago/craftlock/" .. base_flag) == "1" then return end

    dfhack.timeout(1, "ticks", function()
        pcall(function() dfhack.job.removeJob(job) end)
    end)

    if not _craftlock_notified[base_flag] then
        _craftlock_notified[base_flag] = true
        dfhack.gui.showAnnouncement(
            ("[AP] Cannot craft %s — crafting permit not yet received!"):format(
                base_flag:gsub("_", " ")),
            COLOR_YELLOW, true)
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
-- These four are granted by the default start_inventory option, so under normal
-- settings the player receives the blueprint at connect and can build them
-- immediately. They MUST still be gated here so that removing them from
-- start_inventory actually prevents building until the blueprint is received.
wmap("Carpenters",       "Carpenter's Workshop Blueprint")
wmap("Masons",           "Stoneworker's Workshop Blueprint")
wmap("Still",            "Still Blueprint")
wmap("Leatherworks",     "Leather Works Blueprint")

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

-- Hook: remove designations for locked workshops, furnaces, and farm plots.
-- Called via eventful.onBuildingCreated — fires the moment a player places a
-- building designation, before any materials are claimed or jobs are queued.
-- Deconstructing here gives immediate feedback and prevents dwarf retry spam.
local function on_job_initiated(job)
    if not state.is_enabled() then return end

    check_treasury_job_gate(job)
    check_craftitem_gate(job)

    -- Only care about construction jobs.
    if job.job_type ~= df.job_type.ConstructBuilding then return end

    local bld = dfhack.job.getHolder(job)
    if not bld then return end

    local blueprint_name = nil

    if df.building_workshopst:is_instance(bld) then
        blueprint_name = WORKSHOP_BLUEPRINTS[bld.type]
    elseif df.building_furnacest:is_instance(bld) then
        blueprint_name = FURNACE_BLUEPRINTS[bld.type]
    elseif df.building_farmplotst:is_instance(bld) then
        blueprint_name = "Farm Plot Blueprint"
    end

    if not blueprint_name then return end  -- ungated building, allow it

    if not is_blueprint_unlocked(blueprint_name) then
        -- Announce immediately so the player sees feedback right away.
        dfhack.gui.showAnnouncement(
            ("[AP] Cannot build: %s not yet received!"):format(blueprint_name),
            COLOR_YELLOW, true)
        -- Defer deconstruction by one tick — removing a job inline during
        -- onJobInitiated crashes DF because the engine is mid-update.
        dfhack.timeout(1, "ticks", function()
            pcall(function() dfhack.buildings.deconstruct(bld) end)
        end)
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
    local item = df.item.find(item_id)

    -- Count harvested crops (PLANT items) for the farming milestone checks.
    -- item_to_info skips PLANT for the event queue, so we count it here directly.
    if item then
        local ok, t = pcall(function() return df.item_type[item:getType()] end)
        if ok and t == "PLANT" then
            local key = "dwarfipelago/farming/crop_count"
            local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
            dfhack.persistent.saveWorldDataString(key, tostring(n))
        end

        -- Adamantine detection: fires the first time any adamantine item is created
        -- (raw adamantine boulders when mined, or strands/wafers in some DF versions).
        if not checks.production_flag("adamantine") then
            local ok_mat, mat = pcall(dfhack.matinfo.decode, item)
            if ok_mat and mat then
                local ok_tok, token = pcall(function() return mat:getToken() end)
                if ok_tok and token and token:upper():find("ADAMANTINE") then
                    checks.set_production_flag("adamantine")
                    dfhack.gui.showAnnouncement("[AP] Adamantine has been discovered!", COLOR_CYAN, true)
                    print("[Dwarfipelago] Check: Mined Adamantine")
                end
            end
        end
    end

    local info = item_to_info(item)
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
        log.warn("ensure_trade_depot: no position found — will retry next load")
        return
    end

    -- Helper: clear a 5×5 area and attempt to place the depot there.
    -- Returns the constructed building on success, nil on failure.
    local map = df.global.world.map

    -- Count liquid (water/magma) tiles in the clamped 5×5 footprint at (tx,ty).
    -- A tile's liquid is in designation.flow_size (0 = dry, 1–7 = liquid depth),
    -- independent of its shape — a shallow-water tile is still a "floor" shape,
    -- which is why a shape-only check let the depot spawn on water. We use this
    -- to prefer a dry candidate before resorting to draining/filling tiles.
    local function footprint_liquid_count(tx, ty)
        tx = math.max(1, math.min(tx, map.x_count - 6))
        ty = math.max(1, math.min(ty, map.y_count - 6))
        local count = 0
        for dy = 0, 4 do
            for dx = 0, 4 do
                local bx, by = tx + dx, ty + dy
                pcall(function()
                    local block = dfhack.maps.getTileBlock(bx, by, sz)
                    if block and block.designation[bx % 16][by % 16].flow_size > 0 then
                        count = count + 1
                    end
                end)
            end
        end
        return count
    end

    -- Prepare the 5×5 footprint: drain any liquid AND convert every tile to a
    -- solid floor, so the depot never sits on water (or a wall/ramp/tree).
    local function prepare_footprint(tx, ty)
        for dy = 0, 4 do
            for dx = 0, 4 do
                pcall(function()
                    local bx, by = tx + dx, ty + dy
                    local block = dfhack.maps.getTileBlock(bx, by, sz)
                    if not block then return end
                    local lx, ly = bx % 16, by % 16
                    local desig = block.designation[lx][ly]
                    -- Drain water/magma sitting on this tile.
                    if desig.flow_size > 0 then
                        desig.flow_size     = 0
                        desig.flow_forbid   = false
                        desig.liquid_static = false
                    end
                    -- Convert walls/ramps/trees/open tiles to a matching floor.
                    local new_tt = dfhack.maps.findSimilarTileType(
                        block.tiletype[lx][ly], df.tiletype_shape.FLOOR)
                    if new_tt and new_tt ~= 0 then
                        block.tiletype[lx][ly] = new_tt
                    end
                    desig.hidden = false
                    -- Ask the engine to recompute liquid flow around the change
                    -- so neighbouring water doesn't immediately re-flood the tile.
                    pcall(dfhack.maps.enableBlockUpdates, block, true, true)
                end)
            end
        end
    end

    local function try_place(tx, ty)
        -- Clamp so the full 5×5 footprint stays inside the map.
        tx = math.max(1, math.min(tx, map.x_count - 6))
        ty = math.max(1, math.min(ty, map.y_count - 6))
        local x2, y2 = tx + 4, ty + 4

        prepare_footprint(tx, ty)

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

    -- Candidate placements 7 tiles out in each cardinal direction (west first).
    -- Prefer the driest footprint so we only drain/fill tiles when no fully dry
    -- spot exists; original direction order breaks ties.
    local candidates = {
        { sx - 7, sy     },  -- west
        { sx + 7, sy     },  -- east
        { sx,     sy - 7 },  -- north
        { sx,     sy + 7 },  -- south
    }
    for idx, c in ipairs(candidates) do
        c.order  = idx
        c.liquid = footprint_liquid_count(c[1], c[2])
    end
    table.sort(candidates, function(a, b)
        if a.liquid ~= b.liquid then return a.liquid < b.liquid end
        return a.order < b.order
    end)

    local bld, tx, ty
    for _, c in ipairs(candidates) do
        local b, px, py = try_place(c[1], c[2])
        if b then
            bld, tx, ty = b, px, py
            if c.liquid > 0 then
                log.info(("Trade depot footprint had %d liquid tile(s) — drained and filled before placing"):format(c.liquid))
            end
            break
        end
        log.warn(("Depot placement failed at %d,%d — trying next candidate"):format(c[1], c[2]))
    end

    if not bld then
        log.error("Failed to place trade depot in any direction")
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
    pcall(function()
        dfhack.gui.showZoomAnnouncement(
            df.announcement_type.CARAVAN_ARRIVAL,
            {x=tx, y=ty, z=sz},
            "[AP] A Trading Post has been established near your starting wagon!",
            COLOR_GREEN, true)
    end)
    print(("[Dwarfipelago] Trade depot placed at %d,%d,%d"):format(tx, ty, sz))
end

-- ── World validation ──────────────────────────────────────────────────────────

local function check_civilization_diversity()
    local has_human, has_elf = false, false
    local creatures = df.global.world.raws.creatures.all
    pcall(function()
        for _, ent in ipairs(df.global.world.entities.all) do
            if ent.race >= 0 and ent.race < #creatures then
                local race_id = creatures[ent.race].creature_id
                if race_id == "HUMAN" then has_human = true end
                if race_id == "ELF"   then has_elf   = true end
            end
        end
    end)
    if not has_human then
        dfhack.gui.showAnnouncement(
            "[AP] Warning: No human civilization found in this world. Human caravans will not appear.",
            COLOR_YELLOW, true)
        log.warn("No human civilization detected — world may be missing human civs.")
    end
    if not has_elf then
        dfhack.gui.showAnnouncement(
            "[AP] Warning: No elf civilization found in this world. Elf caravans will not appear.",
            COLOR_YELLOW, true)
        log.warn("No elf civilization detected — world may be missing elf civs.")
    end
end

-- ── Start / stop ──────────────────────────────────────────────────────────────

local function start()
    state.set_enabled(true)
    dfhack.persistent.saveWorldDataString("dwarfipelago/version", SCRIPT_VERSION)
    log.info(("Started (v%s). Log file: %s"):format(SCRIPT_VERSION, log.path()))
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

    -- Enable the corner [AP] overlay button.
    pcall(dfhack.run_command, "overlay", "enable", "dwarfipelago-panel.hotspot")

    check_civilization_diversity()

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

    -- Hide the corner [AP] overlay button.
    pcall(dfhack.run_command, "overlay", "disable", "dwarfipelago-panel.hotspot")

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
elseif cmd == "resetseed" then
    -- Clear the stored AP world identity so this DF save can be reconnected to a
    -- freshly generated AP slot (new seed) without the client rejecting it with
    -- "This saved world does not match this slot." Lets you keep a test world
    -- across regenerations. Other AP state (checks, unlocks, craft counts) is
    -- left intact — use "dwarfipelago reset" for a full wipe.
    local ok = pcall(function()
        dfhack.persistent.deleteWorldData("dwarfipelago/seed")
    end)
    if not ok then
        -- Older API without deleteWorldData: blank it (client treats "" as fresh).
        dfhack.persistent.saveWorldDataString("dwarfipelago/seed", "")
    end
    print("[Dwarfipelago] Seed expectation cleared. Reconnect the AP client to adopt the new slot's seed.")
elseif cmd == "panel" then
    reqscript("dwarfipelago-panel").open_panel()
elseif cmd == "receive" then
    local item_name = table.concat(args, " ", 2)
    if item_name == "" then
        dfhack.printerr("Usage: dwarfipelago receive <Item Name>")
    else
        items.receive(item_name)
    end
elseif cmd == "test" then
    -- Manual mechanic verification: dwarfipelago test <name> [args]
    items.run_test(args[2], { table.unpack(args, 3) })
else
    print("Usage: dwarfipelago [start|stop|status|reset|resetseed|panel|receive <item>|test <name>]")
end
