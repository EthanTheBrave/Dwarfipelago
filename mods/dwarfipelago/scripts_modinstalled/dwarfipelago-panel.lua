--@ module = true
-- Dwarfipelago status and control panel.
-- Can be opened three ways:
--   1. Click the [AP] hotspot button in the corner of the fortress screen.
--   2. Run: dwarfipelago panel
--   3. Run directly: dwarfipelago-panel

local gui           = require('gui')
local overlay       = require('plugins.overlay')
local widgets       = require('gui.widgets')
local dialogs       = require('gui.dialogs')
local textures      = require('gui.textures')
local scriptmanager = require('script-manager')
local state    = reqscript('internal/dwarfipelago/state')
local items    = reqscript('internal/dwarfipelago/items')
local checks   = reqscript('internal/dwarfipelago/checks')
local log      = reqscript("internal/dwarfipelago/log")

local to_pen = dfhack.pen.parse

-- ── Archipelago panel frame style ─────────────────────────────────────────────
-- Builds a custom frame table each render (stored as a function so paint_frame
-- calls it with the current resizable state, keeping texpos values fresh across
-- graphics resets).
--
-- Art upgrade path: replace `tp` below with a handle table loaded from a
-- custom PNG shipped with the mod:
--   local ap_handles = dfhack.textures.loadTileset(
--       dfhack.getModRootPath('dwarfipelago') .. '/art/ap-border.png', 8, 12, true)
--   local function tp(offset) return dfhack.textures.getTexposByHandle(ap_handles[offset]) end
-- The PNG must be a 22×1 tile sheet (8×12 px per tile) matching DFHack's
-- border tile index layout (indices 1-21 used by make_frame).
local function make_ap_frame(_resizable)
    local tp = textures.tp_border_window
    local fg = COLOR_LIGHTCYAN
    local bg = COLOR_BLACK
    return {
        frame_pen          = to_pen{ch=206,  fg=fg, bg=bg},
        title_pen          = to_pen{fg=COLOR_BLACK, bg=COLOR_CYAN},
        inactive_title_pen = to_pen{fg=COLOR_CYAN,  bg=bg},
        signature_pen      = false,
        paused_pen         = to_pen{fg=COLOR_RED, bg=bg},
        -- corners
        lt_frame_pen  = to_pen{tile=tp(1),  ch=201, fg=fg, bg=bg},
        rt_frame_pen  = to_pen{tile=tp(3),  ch=187, fg=fg, bg=bg},
        lb_frame_pen  = to_pen{tile=tp(15), ch=200, fg=fg, bg=bg},
        rb_frame_pen  = to_pen{tile=tp(17), ch=188, fg=fg, bg=bg},
        -- outer edges
        t_frame_pen   = to_pen{tile=tp(2),  ch=205, fg=fg, bg=bg},
        b_frame_pen   = to_pen{tile=tp(16), ch=205, fg=fg, bg=bg},
        l_frame_pen   = to_pen{tile=tp(8),  ch=186, fg=fg, bg=bg},
        r_frame_pen   = to_pen{tile=tp(10), ch=186, fg=fg, bg=bg},
        -- inner T-junctions (tab bar divider line meets the border)
        tTi_frame_pen = to_pen{tile=tp(21), ch=203, fg=fg, bg=bg},
        bTi_frame_pen = to_pen{tile=tp(20), ch=202, fg=fg, bg=bg},
        lTi_frame_pen = to_pen{tile=tp(19), ch=204, fg=fg, bg=bg},
        rTi_frame_pen = to_pen{tile=tp(18), ch=185, fg=fg, bg=bg},
        -- outer T-junctions
        tTe_frame_pen = to_pen{tile=tp(11), ch=203, fg=fg, bg=bg},
        bTe_frame_pen = to_pen{tile=tp(12), ch=202, fg=fg, bg=bg},
        lTe_frame_pen = to_pen{tile=tp(13), ch=204, fg=fg, bg=bg},
        rTe_frame_pen = to_pen{tile=tp(14), ch=185, fg=fg, bg=bg},
        -- internal divider bars and cross
        v_frame_pen   = to_pen{tile=tp(5),  ch=179, fg=fg, bg=bg},
        h_frame_pen   = to_pen{tile=tp(6),  ch=196, fg=fg, bg=bg},
        x_frame_pen   = to_pen{tile=tp(4),  ch=197, fg=fg, bg=bg},
    }
end

-- ── Helpers ───────────────────────────────────────────────────────────────────

local function ps(key, default)
    return dfhack.persistent.getWorldDataString("dwarfipelago/" .. key) or default
end

local GOAL_NAMES = {
    ["0"] = "Slay Megabeast",
    ["1"] = "Legendary Wealth",
    ["2"] = "Population Boom",
    ["3"] = "Mountainhome",
    ["4"] = "Remains of the Great King",
    ["5"] = "Dwarfsanity",
}

local function yn(val, yes_color, no_color)
    if val then
        return {text="YES", pen=yes_color or COLOR_GREEN}
    else
        return {text="no",  pen=no_color  or COLOR_DARKGRAY}
    end
end

local function fmt_num(n)
    local s = tostring(math.floor(n or 0))
    return s:reverse():gsub("(%d%d%d)", "%1,"):reverse():gsub("^,", "")
end

-- Adaptive energy display: MJ for large values, kJ for medium, J for tiny.
local function fmt_energy(j)
    j = math.max(0, math.floor(j or 0))
    if j >= 1000000 then
        return string.format("%.2f MJ", j / 1000000)
    elseif j >= 1000 then
        return string.format("%.1f kJ", j / 1000)
    else
        return string.format("%d J", j)
    end
end

local function next_thresh(val, thresholds)
    for _, t in ipairs(thresholds) do
        if val < t then return t end
    end
end

local function bp_label(name)
    return name:gsub(" Blueprint$", "")
end

-- Live status of a milestone by its AP location id, by calling the real check
-- fn from checks.checks. Panel rows use this instead of re-reading raw flags, so
-- the panel can never drift from the actual checks (a check added to checks.lua
-- shows up here as soon as its id is listed). Returns true/false, or nil if the
-- id isn't a known check.
local _check_fn_by_id
local function check_status(id)
    if not _check_fn_by_id then
        _check_fn_by_id = {}
        for _, c in ipairs(checks.checks) do _check_fn_by_id[c.id] = c.fn end
    end
    local fn = _check_fn_by_id[id]
    if not fn then return nil end
    local ok, r = pcall(fn)
    return ok and r or false
end

-- widgets.List ignores a top-level `pen` on a string choice — it draws every
-- row in text_pen — so per-row colors must live in a text token. Wrap each
-- line's text+pen into a token so green/red/cyan actually show.
local function lines_to_choices(lines)
    local choices = {}
    for _, line in ipairs(lines) do
        if type(line) == "string" then
            table.insert(choices, {text = {{text = line, pen = COLOR_WHITE}}})
        elseif type(line.text) == "table" then
            table.insert(choices, line)   -- already tokenized; leave as-is
        else
            table.insert(choices, {text = {{text = line.text or "", pen = line.pen or COLOR_WHITE}}})
        end
    end
    return choices
end
local function make_list(lines, frame)
    return widgets.List{
        frame      = frame or {t=0, b=0},
        choices    = lines_to_choices(lines),
        text_pen   = COLOR_WHITE,
        cursor_pen = COLOR_CYAN,
    }
end

-- ── Checks list (in-fort milestone tracker) ──────────────────────────────────
-- The static milestone checks (checks.checks) grouped by category, each marked
-- done (sent) or open, so players can see progress without the AP tracker.
-- Per-item craft/skill checks are dynamic + client-side, so they are not listed.
local CHECK_CATEGORIES = {
    { name = "Rooms",                   lo = 0,    hi = 99   },
    { name = "First Production",        lo = 100,  hi = 199  },
    { name = "Trade & Diplomacy",       lo = 200,  hi = 299  },
    { name = "Nobles",                  lo = 300,  hi = 399  },
    { name = "Settlement Size",         lo = 400,  hi = 699  },
    { name = "Mining & Caverns",        lo = 700,  hi = 729  },
    { name = "Farming",                 lo = 730,  hi = 739  },
    { name = "Infrastructure & Health", lo = 740,  hi = 759  },
    { name = "Endgame",                 lo = 760,  hi = 769  },
    { name = "Military & Combat",       lo = 770,  hi = 799  },
    { name = "Fortress Life",           lo = 3000, hi = 3999 },
}
-- AP-logic gate written by the client (dwarfipelago/accessible_checks, JSON
-- {accessible=[ids], locked=[ids]}). The client evaluates the real rules.py
-- against received items, so a check is "locked" only if it is explicitly in
-- the locked list; anything else (ungated, or reachable) counts as open.
-- Returns a {id=true} set of locked ids, or nil if the client hasn't pushed yet.
local function read_locked_set()
    local raw = dfhack.persistent.getWorldDataString("dwarfipelago/accessible_checks")
    if not raw or raw == "" then return nil end
    local ok, data = pcall(function() return require('json').decode(raw) end)
    if not ok or type(data) ~= "table" or type(data.locked) ~= "table" then return nil end
    local set = {}
    for _, id in ipairs(data.locked) do set[id] = true end
    return set
end
-- Checks-tab sort mode: false = category id order; true = actionable (open)
-- first, then locked, then done. Toggled by the Sort button (persists per session).
local checks_sort = false

-- Milestone checks a victory goal drops from the seed (mirrors the goal filter
-- in worlds/dwarf_fortress/__init__.py). Excluded ones are hidden entirely.
local GOAL_NOBLE_LADDER = {37370301, 37370302, 37370303, 37370304}  -- active: mountainhome (3) only
local GOAL_SIEGE        = {37370770, 37370771, 37370792, 37370793, 37370794, 37370795, 37370796}  -- active: slay_megabeast (0) only
local GOAL_BEAST_SLAIN  = {37370782, 37370783, 37370784, 37370785}  -- excluded on slay_megabeast (0)
local function goal_excluded_set()
    local goal = tonumber(ps("goal", "-1")) or -1
    local ex = {}
    if goal < 0 then return ex end   -- goal not synced yet -> exclude nothing
    if goal ~= 3 then for _, id in ipairs(GOAL_NOBLE_LADDER) do ex[id] = true end end
    if goal ~= 0 then for _, id in ipairs(GOAL_SIEGE)        do ex[id] = true end end
    if goal == 0 then for _, id in ipairs(GOAL_BEAST_SLAIN)  do ex[id] = true end end
    return ex
end
local function build_checks_lines()
    local BASE = 37370000
    local locked_set = read_locked_set()   -- nil until the client pushes AP logic
    local excluded = goal_excluded_set()   -- checks not active for the current goal
    -- Sort rank when "actionable first" is on: open (do now) < locked < done.
    local function check_rank(id)
        if state.is_location_checked(id) then return 2 end   -- done -> bottom
        if locked_set and locked_set[id] then return 1 end   -- can't do yet -> middle
        return 0                                             -- actionable -> top
    end
    local function order(a, b)
        if checks_sort then
            local ra, rb = check_rank(a.id), check_rank(b.id)
            if ra ~= rb then return ra < rb end
        end
        return a.id < b.id
    end
    local by_cat, other = {}, {}
    for _, c in ipairs(checks.checks) do
        local off, placed = c.id - BASE, false
        for i, cat in ipairs(CHECK_CATEGORIES) do
            if off >= cat.lo and off <= cat.hi then
                by_cat[i] = by_cat[i] or {}; table.insert(by_cat[i], c); placed = true; break
            end
        end
        if not placed then table.insert(other, c) end
    end
    local lines, tdone, tlocked, texcluded, tactive = {""}, 0, 0, 0, 0   -- lines[1] is the summary
    local function emit(catname, list)
        if not list or #list == 0 then return end
        table.sort(list, order)
        local done, active, buf = 0, 0, {}
        for _, c in ipairs(list) do
            if excluded[c.id] then
                texcluded = texcluded + 1   -- not active for this goal: hidden entirely
            else
                active = active + 1; tactive = tactive + 1
                local sent = state.is_location_checked(c.id)
                local locked = (not sent) and locked_set and locked_set[c.id]
                local mark, pen
                if sent then
                    done = done + 1; tdone = tdone + 1; mark, pen = "[x]", COLOR_GREEN
                elseif locked then
                    tlocked = tlocked + 1; mark, pen = "[ ]", COLOR_LIGHTRED   -- red = can't do it yet
                else
                    mark, pen = "[ ]", COLOR_WHITE
                end
                table.insert(buf, {text = ("  %s %s"):format(mark, c.name), pen = pen})
            end
        end
        if #buf == 0 then return end   -- entire category is inactive for this goal
        table.insert(lines, {text = ("%s  (%d/%d)"):format(catname, done, active), pen = COLOR_CYAN})
        for _, l in ipairs(buf) do table.insert(lines, l) end
        table.insert(lines, "")
    end
    for i, cat in ipairs(CHECK_CATEGORIES) do emit(cat.name, by_cat[i]) end
    emit("Other", other)
    if locked_set then
        lines[1] = {text = ("Milestones sent: %d / %d    reachable: %d    locked: %d")
            :format(tdone, tactive, tactive - tdone - tlocked, tlocked), pen = COLOR_YELLOW}
        table.insert(lines, {text = "[x] done   [ ] open   red = can't do yet", pen = COLOR_DARKGRAY})
    else
        lines[1] = {text = ("Milestones sent: %d / %d      [x] done   [ ] open"):format(tdone, tactive), pen = COLOR_YELLOW}
        table.insert(lines, {text = "Connect the AP client to see which locked checks AP logic is gating.", pen = COLOR_DARKGRAY})
    end
    if texcluded > 0 then
        table.insert(lines, {text = ("%d checks not applicable to the current goal are hidden."):format(texcluded), pen = COLOR_DARKGRAY})
    end
    table.insert(lines, {text = "Per-item craft/skill checks are client-side (see the AP tracker).", pen = COLOR_DARKGRAY})
    return lines
end

-- ── Unlocks list ──────────────────────────────────────────────────────────────

local function build_unlocks_lines()
    local lines = {}
    local goal = tonumber(ps("goal", 0))


    local function hdr(s)
        table.insert(lines, {text=s, pen=COLOR_CYAN})
    end
    local function item_bool(label, val)
        table.insert(lines, {
            text = ("  %-28s%s"):format(label .. ":", val and "YES" or "no"),
            pen  = val and COLOR_WHITE or COLOR_DARKGRAY,
        })
    end
    local function item_count(label, val, max)
        local n = tonumber(val) or 0
        table.insert(lines, {
            text = ("  %-28s%d/%d"):format(label .. ":", n, max),
            pen  = n > 0 and COLOR_WHITE or COLOR_DARKGRAY,
        })
    end

    hdr("Progression Items")
    for _, def in ipairs(items.UNLOCK_DEFS) do
        if goal == 0 then
            if def.key == "wealth_coffers" or def.key == "baron_charter"
            or def.key == "count_charter" or def.key == "duke_charter"
            or def.key == "monarch_invitation" or def.key == "RotGK"
            or def.key == "dwarfsanity" then
                goto continue
            end
        elseif goal == 1 then
            if def.key == "military_training" or def.key == "baron_charter"
            or def.key == "count_charter" or def.key == "duke_charter"
            or def.key == "monarch_invitation" or def.key == "RotGK"
            or def.key == "artifact_weapon" or def.key == "artifact_armor"
            or def.key == "dwarfsanity" then
                goto continue
            end
        elseif goal == 2 then
            if def.key == "military_training" or def.key == "RotGK"
            or def.key == "artifact_armor" or def.key == "wealth_coffers"
            or def.key == "dwarfsanity" then
                goto continue
            end
        elseif goal == 3 then
            if def.key == "military_training" or def.key == "baron_charter"
            or def.key == "count_charter" or def.key == "duke_charter"
            or def.key == "monarch_invitation" or def.key == "RotGK"
            or def.key == "wealth_coffers" or def.key == "dwarfsanity" then
                goto continue
            end
        elseif goal == 4 then
            if def.key == "military_training" or def.key == "baron_charter"
            or def.key == "count_charter" or def.key == "duke_charter"
            or def.key == "monarch_invitation" or def.key == "wealth_coffers"
            or def.key == "dwarfsanity" then
                goto continue
            elseif def.key == "RotGK" then
                def.max = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/king_remains_goal") or 99)
            end
        elseif goal == 5 then
            if def.key == "military_training" or def.key == "baron_charter"
            or def.key == "count_charter" or def.key == "duke_charter"
            or def.key == "monarch_invitation" or def.key == "wealth_coffers"
            or def.key == "RotGK" then
                goto continue
            elseif def.key == "dwarfsanity" then
                local count = 0
                for _ in pairs(items.BLUEPRINT_NAMES) do count = count + 1 end
                for _ in pairs(items.CRAFTING_LOCK_ITEMS) do count = count + 1 end
                def.max = count
            end
        end
        if def.key ~= "dwarfsanity" then
            local raw = ps("unlock/" .. def.key, "0")
            if def.max then
                item_count(def.label, raw, def.max)
            else
                item_bool(def.label, raw == "1")
            end
        else -- collection for dwarfsanity
            local collected = 0
            for _, bp_name in ipairs(items.BLUEPRINT_NAMES) do
                if ps("blueprint/" .. bp_name, "0") == "1" then
                    collected = collected + 1
                end
            end
            for _, item_name in pairs(items.CRAFTING_LOCK_ITEMS) do
                local flag = item_name:lower():gsub(" ", "_")
                local done_flag = tonumber(ps("craftlock/" .. flag, "0"))
                if done_flag >= 1 then
                    collected = collected + 1
                end
            end
            item_count(def.label, collected, def.max)
        end
        ::continue::
    end

    table.insert(lines, {text = ""})
    hdr("Workshop Blueprints")
    for _, bp_name in ipairs(items.BLUEPRINT_NAMES) do
        local received = ps("blueprint/" .. bp_name, "0") == "1"
        item_bool(bp_label(bp_name), received)
    end

    return lines
end

-- ── Progress list ─────────────────────────────────────────────────────────────

local TILES_THRESHOLDS  = {100, 500, 2000, 5000, 10000}
local DEPTH_TIER_LABELS = { "Cavern 1 ceiling", "Cavern 2 ceiling", "Cavern 3 ceiling", "Magma Sea" }

-- ── Goal progress ──────────────────────────────────────────────────────────────
-- Consolidated view of the selected AP goal and live progress toward it.
local function build_goal_lines()
    local lines = {}
    local function hdr(s) table.insert(lines, {text=s, pen=COLOR_CYAN}) end
    local function row(s, pen) table.insert(lines, {text=s, pen=pen or COLOR_WHITE}) end
    local function blank() table.insert(lines, {text=""}) end
    local function pct(cur, target) return target > 0 and math.min(100, math.floor(cur / target * 100)) or 0 end

    local goal_key = ps("goal", "-1")
    local complete = ps("goal_complete", "0") == "1"

    hdr("Goal")
    row("  " .. (GOAL_NAMES[goal_key] or "Not synced"))
    row(("  Complete:  %s"):format(complete and "YES" or "no"),
        complete and COLOR_GREEN or COLOR_DARKGRAY)
    blank()

    hdr("Progress")
    if goal_key == "1" then
        local created = checks.treasury_created_wealth()
        local target  = tonumber(ps("wealth_goal", "100000")) or 100000
        row(("  AP wealth:  %s / %s  (%d%%)"):format(fmt_num(created), fmt_num(target), pct(created, target)),
            created >= target and COLOR_GREEN or COLOR_WHITE)
        row("  Minted coins + cut gems, capped by your Merchant's Coffer tier.", COLOR_DARKGRAY)
    elseif goal_key == "2" then
        local pop = 0
        for _, u in ipairs(df.global.world.units.active) do
            if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then pop = pop + 1 end
        end
        local target = tonumber(ps("pop_goal", "300")) or 300
        row(("  Population: %d / %d  (%d%%)"):format(pop, target, pct(pop, target)),
            pop >= target and COLOR_GREEN or COLOR_WHITE)
    elseif goal_key == "4" then
        local have   = tonumber(ps("unlock/RotGK", "0")) or 0
        local target = tonumber(ps("king_remains_goal", "0")) or 0
        row(("  Remains recovered: %d / %d  (%d%%)"):format(have, target, pct(have, target)),
            (target > 0 and have >= target) and COLOR_GREEN or COLOR_WHITE)
    elseif goal_key == "5" then
        local collected, total = 0, 0
        for _, bp in ipairs(items.BLUEPRINT_NAMES) do
            total = total + 1
            if ps("blueprint/" .. bp, "0") == "1" then collected = collected + 1 end
        end
        for _, item_name in pairs(items.CRAFTING_LOCK_ITEMS) do
            total = total + 1
            local flag = item_name:lower():gsub(" ", "_")
            if (tonumber(ps("craftlock/" .. flag, "0")) or 0) >= 1 then collected = collected + 1 end
        end
        row(("  Recovered: %d / %d  (%d%%)"):format(collected, total, pct(collected, total)),
            (total > 0 and collected >= total) and COLOR_GREEN or COLOR_WHITE)
        row("  Blueprints + permits (see the Unlocks tab for details).", COLOR_DARKGRAY)
    elseif goal_key == "0" then
        row("  Muster the war effort, then summon and slay the beast.")
        row("  See the War tab for war-effort progress.", COLOR_DARKGRAY)
    elseif goal_key == "3" then
        row("  Climb the noble ladder until the monarch takes residence.")
        row("  See the Unlocks tab for charter progression.", COLOR_DARKGRAY)
    else
        row("  Not synced to an AP goal yet.", COLOR_DARKGRAY)
    end

    return lines
end

-- ── Craftsanity list ──────────────────────────────────────────────────────────

local function build_caves_lines()
    local lines = {}

    local function hdr(s)      table.insert(lines, {text=s, pen=COLOR_CYAN})          end
    local function row(s, pen) table.insert(lines, {text=s, pen=pen or COLOR_WHITE})  end
    local function blank()     table.insert(lines, {text=""})                         end

    -- Excavation milestones
    hdr("Excavation")
    local tiles = checks.mining_count()
    local nt = next_thresh(tiles, TILES_THRESHOLDS)
    row(("  Tiles:  %s excavated%s"):format(
        fmt_num(tiles), nt and ("  (next: %s)"):format(fmt_num(nt)) or "  (all done!)"))

    -- Cavern access
    blank()
    hdr("Cavern Access")
    local c1 = checks.mining_flag("cavern1")
    local c2 = checks.mining_flag("cavern2")
    local c3 = checks.mining_flag("cavern3")
    local mg = checks.mining_flag("magma")
    row(("  Cavern 1: %-3s  2: %-3s  3: %-3s    Magma: %-3s"):format(
        c1 and "YES" or "no", c2 and "YES" or "no",
        c3 and "YES" or "no", mg and "YES" or "no"))
    local appr = checks.cavern_approach()
    if appr then
        local nm = ({"First", "Second", "Third"})[appr.cavern]
        local nextstr = appr.next_pct and ("next check: %d%%"):format(appr.next_pct)
            or "next: breach!"
        row(("  Toward %s Cavern: %d%%  (%s)"):format(nm, math.floor(appr.pct), nextstr))
        if appr.levels_remaining then
            row(("    %d z-levels to its ceiling"):format(appr.levels_remaining))
        end
    elseif c1 and c2 and c3 then
        row("  All caverns breached!", COLOR_GREEN)
    end

    -- Progressive mining depth
    blank()
    if checks.mining_depth_enabled() then
        local unlocks  = checks.mining_depth_unlocks()
        local no_limit = unlocks >= 4
        hdr(no_limit
            and ("Mining Depth  (%d/4 - no limit)"):format(math.min(unlocks, 4))
            or  ("Mining Depth  (%d/4 unlocked)"):format(unlocks))
        for tier = 1, 4 do
            local done     = unlocks >= tier
            local is_limit = not no_limit and (unlocks == tier - 1)
            local status   = done and "done" or (is_limit and "LOCKED  <- current" or "locked")
            local pen      = done and COLOR_GREEN or (is_limit and COLOR_YELLOW or COLOR_DARKGRAY)
            row(("  [%d] %-22s %s"):format(tier, DEPTH_TIER_LABELS[tier] .. ":", status), pen)
        end
    else
        hdr("Mining Depth")
        row("  Progressive depth not enabled for this seed.", COLOR_DARKGRAY)
    end

    -- Custom caves
    blank()
    hdr("Custom Caves")
    local caves_gen = ps("caves/generated", "0") == "1"
    if not caves_gen then
        row("  Not yet generated.", COLOR_DARKGRAY)
    else
        local frag_used = tonumber(ps("caves/fragment_index", "0")) or 0
        local n_found   = 0
        for i = 1, 6 do
            if ps("cave/" .. i .. "/discovered", "0") == "1" then n_found = n_found + 1 end
        end
        local secrets = ps("caves/secrets_done", "0") == "1"
        row(("  Fragments used: %d/6   Caves found: %d/6   Secrets: %s"):format(
            frag_used, n_found, secrets and "done" or "pending"),
            n_found == 6 and COLOR_GREEN or COLOR_WHITE)
        for i = 1, 6, 2 do
            local j  = i + 1
            local d1 = ps("cave/" .. i .. "/discovered", "0") == "1"
            local d2 = ps("cave/" .. j .. "/discovered", "0") == "1"
            local pen = (d1 and d2) and COLOR_GREEN
                     or (not d1 and not d2) and COLOR_DARKGRAY
                     or COLOR_WHITE
            row(("  Cave #%d: %-3s          Cave #%d: %-3s"):format(
                i, d1 and "YES" or "no",
                j, d2 and "YES" or "no"), pen)
        end
    end

    return lines
end

local function build_crafts_lines()
    local lines = {}
    local json  = require('json')

    local function hdr(s)      table.insert(lines, {text=s, pen=COLOR_CYAN})     end
    local function row(s, pen) table.insert(lines, {text=s, pen=pen or COLOR_WHITE}) end
    local function blank()     table.insert(lines, {text=""})                    end

    local enabled = tonumber(ps("craftsanity_enabled", "0")) or 0
    if enabled == 0 then
        row("  Craftsanity is not enabled for this seed.", COLOR_DARKGRAY)
        return lines
    end

    local threshold  = math.max(1, tonumber(ps("craftsanity_threshold", "1")) or 1)
    local max_val    = tonumber(ps("craftsanity_max", "0")) or 0
    local labels_raw = ps("craftsanity_labels", "{}")
    local labels     = json.decode(labels_raw) or {}

    -- AP-logic gate: flags the client evaluated as not yet craftable (missing
    -- workshop/material). Those rows show red. Empty until the client pushes.
    local locked_set = {}
    local locked_raw = ps("craftsanity_locked", "")
    if locked_raw ~= "" then
        local ok, arr = pcall(function() return json.decode(locked_raw) end)
        if ok and type(arr) == "table" then
            for _, f in ipairs(arr) do locked_set[f] = true end
        end
    end

    if max_val == 0 or next(labels) == nil then
        row("  Waiting for AP client to sync craftsanity data...", COLOR_DARKGRAY)
        return lines
    end

    local checks_per_item = math.ceil(max_val / threshold)
    hdr(("  threshold: %-5d max: %-8s checks/item: %d"):format(
        threshold, fmt_num(max_val), checks_per_item))
    blank()
    row(("  %-26s  %6s   %s"):format("Item", "Count", "Progress"), COLOR_CYAN)
    row("  " .. string.rep("-", 52), COLOR_DARKGRAY)

    -- Build display list
    local craft_counts = checks.get_all_craft_counts()
    local list = {}
    for flag, label in pairs(labels) do
        local count  = craft_counts[flag] or 0
        local done_n = math.min(math.floor(count / threshold), checks_per_item)
        table.insert(list, {
            label   = label,
            flag    = flag,
            count   = count,
            done_n  = done_n,
            is_done = done_n >= checks_per_item,
            locked  = locked_set[flag] or false,
        })
    end
    -- Sort: in-progress (count desc) → not-started (alpha) → done (alpha)
    table.sort(list, function(a, b)
        if a.is_done ~= b.is_done then return not a.is_done end
        if (a.count > 0) ~= (b.count > 0) then return a.count > b.count end
        if a.count ~= b.count then return a.count > b.count end
        return a.label < b.label
    end)

    local n_done, n_locked = 0, 0
    for _, e in ipairs(list) do
        if e.is_done then
            n_done = n_done + 1
            row(("  %-26s  %6s   DONE (%d/%d)"):format(
                e.label, fmt_num(e.count), checks_per_item, checks_per_item),
                COLOR_GREEN)
        elseif e.locked then
            n_locked = n_locked + 1
            row(("  %-26s  %6s   locked"):format(e.label, fmt_num(e.count)), COLOR_LIGHTRED)
        elseif e.count == 0 then
            row(("  %-26s  %6s   --"):format(e.label, "0"), COLOR_DARKGRAY)
        else
            local next_target = (e.done_n + 1) * threshold
            -- Plain ASCII "->": DF renders the CP437 font, so a UTF-8 arrow shows
            -- as garbage bytes.
            row(("  %-26s  %6s -> %-7s %d/%d"):format(
                e.label, fmt_num(e.count), fmt_num(next_target),
                e.done_n, checks_per_item))
        end
    end

    blank()
    row("  " .. string.rep("-", 52), COLOR_DARKGRAY)
    row(("  Items complete: %d / %d"):format(n_done, #list),
        n_done >= #list and COLOR_GREEN or COLOR_WHITE)
    if n_locked > 0 then
        row(("  %d not craftable yet (red = missing workshop/material)"):format(n_locked),
            COLOR_DARKGRAY)
    end

    return lines
end

-- ── Permit list ──────────────────────────────────────────────────────────

local function build_permit_lines()
    local lines = {}
    local function hdr(s)      table.insert(lines, {text=s, pen=COLOR_CYAN})     end
    local function row(s, pen) table.insert(lines, {text=s, pen=pen or COLOR_WHITE}) end
    local function blank()     table.insert(lines, {text=""})                    end

    blank()
    row(("  %-26s  %6s"):format("Item", "Permit Obtained"), COLOR_CYAN)
    row("  " .. string.rep("-", 52), COLOR_DARKGRAY)

    -- Build display list
    local list = {}
    for _, item_name in pairs(items.CRAFTING_LOCK_ITEMS) do
        local flag = item_name:lower():gsub(" ", "_")
        local done_flag = ps("craftlock/" .. flag, "0")
        if done_flag == "0" then
            done_flag = 0
        else
            done_flag = 1
        end

        table.insert(list, {
            label = item_name,
            done  = done_flag,
        })
    end
    
    table.sort(list, function(a, b)
        -- 1. Sort by done (descending: 1 before 0)
        if a.done ~= b.done then
            return a.done > b.done
        end
        -- 2. If done is the same, sort by label (ascending: A to Z)
        return a.label < b.label
    end)
    
    local n_done = 0
    for _, e in ipairs(list) do
        if e.done == 1 then
            n_done = n_done + 1
            row(("  %-26s  %6s"):format(
                e.label, "DONE"),
                COLOR_GREEN)
        else
            row(("  %-26s  %6s"):format(
                e.label, "N/A"),
                COLOR_WHITE)
        end
    end
    blank()
    row("  " .. string.rep("-", 52), COLOR_DARKGRAY)
    row(("  Items complete: %d / %d"):format(n_done, #list),
        n_done >= #list and COLOR_GREEN or COLOR_WHITE)
    return lines
end


-- ── Skill list ──────────────────────────────────────────────────────────

local function build_skill_lines()
    local lines = {}
    local function hdr(s)      table.insert(lines, {text=s, pen=COLOR_CYAN})     end
    local function row(s, pen) table.insert(lines, {text=s, pen=pen or COLOR_WHITE}) end
    local function blank()     table.insert(lines, {text=""})                    end

    blank()
    row(("  %-26s  %6s"):format("Skill Name", "Skill Level"), COLOR_CYAN)
    row("  " .. string.rep("-", 52), COLOR_DARKGRAY)

    -- Build display list
    local skill_counts = checks.get_all_skill_counts()
    local list = {}
    local max_level = tonumber(ps("skillsanity_max_level", "15"))
    for skill_name, skill_level in pairs(skill_counts) do
        table.insert(list, {
            label = skill_name,
            level  = skill_level,
        })
    end
    -- -- Sort: done (alpha) → not done (alpha) 
    table.sort(list, function(a, b)
        return a.level > b.level
    end)
    
    local n_done = 0
    for _, e in ipairs(list) do
        if e.level >= max_level then
            n_done = n_done + 1
            row(("  %-26s  %6s"):format(
                e.label, tostring(max_level) .. "/" .. tostring(max_level)),
                COLOR_GREEN)
        else
            row(("  %-26s  %6s"):format(
                e.label, tostring(e.level) .. "/" .. tostring(max_level)),
                COLOR_WHITE)
        end
    end
    blank()
    row("  " .. string.rep("-", 52), COLOR_DARKGRAY)
    row(("  Items complete: %d / %d"):format(n_done, #list),
        n_done >= #list and COLOR_GREEN or COLOR_WHITE)
    return lines
end

-- ── Status / control popup ────────────────────────────────────────────────────

local _panel_instance = nil

DwarfipelagoPanel = defclass(DwarfipelagoPanel, gui.ZScreen)
DwarfipelagoPanel.ATTRS{
    focus_path = "dwarfipelago/panel",
}

function DwarfipelagoPanel:onDismiss()
    _panel_instance = nil
end

function DwarfipelagoPanel:onInput(keys)
    if keys._MOUSE_L and not self:isMouseOver() then
        self:dismiss()
        return true
    end
    return DwarfipelagoPanel.super.onInput(self, keys)
end

function DwarfipelagoPanel:init()
    local enabled  = state.is_enabled()
    local version  = ps("version",       "?")
    local goal_key = ps("goal",          "-1")
    local complete = ps("goal_complete", "0") == "1"
    local depot    = ps("depot_built",   "0") == "1"

    local goal_str = GOAL_NAMES[goal_key] or "Not synced"
    local tab_list = {}


    -- Goal-specific target string
    local target_str
    if goal_key == "1" then
        local wg = tonumber(ps("wealth_goal", "100000")) or 100000
        target_str = "Target:   " .. fmt_num(wg) .. " wealth"
    elseif goal_key == "2" then
        local pg = tonumber(ps("pop_goal", "300")) or 300
        target_str = "Target:   " .. tostring(pg) .. " citizens"
    elseif goal_key == "4" then
        local kg = tonumber(ps("king_remains_goal", ""))
        target_str = "Target:   " .. (kg and tostring(kg) or "?") .. " remains"
    end

    -- DeathLink display
    local dl_on     = ps("deathlink",            "0") == "1"
    local dl_thresh = tonumber(ps("deathlink_threshold",  "0")) or 0
    local dl_pct    = ps("deathlink_percentage", "0") == "1"
    local dl_detail = dl_on and (dl_pct
        and ("  (%d%% of population)"):format(dl_thresh)
        or  ("  (every %d deaths)"):format(dl_thresh)) or ""

    local W, H = 76, 48

    -- Tab 1 Status -----------------------
    function StatusTab()
        table.insert(tab_list, "Status")
        return widgets.Panel{
            subviews = {
                widgets.Label{
                    frame = {t=0, l=0},
                    text  = {
                        "Status:   ",
                        {text=enabled and "RUNNING" or "STOPPED",
                        pen=enabled and COLOR_GREEN or COLOR_RED},
                    },
                },
                widgets.Label{
                    frame = {t=1, l=0},
                    text  = {"Goal:     ", goal_str},
                },
                widgets.Label{
                    frame = {t=2, l=0},
                    text  = target_str or "",
                },
                widgets.Label{
                    frame = {t=3, l=0},
                    text  = {"Complete: ", yn(complete)},
                },
                widgets.Label{
                    frame = {t=4, l=0},
                    text  = {
                        "Depot:    ",
                        {text=depot and "built" or "pending",
                        pen=depot and COLOR_GREEN or COLOR_YELLOW},
                    },
                },
                widgets.Label{
                    frame = {t=5, l=0},
                    text  = {
                        "DeathLink: ",
                        {text=dl_on and "ON" or "off",
                        pen=dl_on and COLOR_GREEN or COLOR_DARKGRAY},
                        {text=dl_detail, pen=COLOR_WHITE},
                    },
                },
                (function()
                    local energy_on = ps("energy_enabled", "0") == "1"
                    if not energy_on then return widgets.Label{frame={t=6,l=0}, text=""} end
                    local pool     = tonumber(ps("energy_link", "0")) or 0
                    local caravan  = ps("ap_caravan_active", "0") == "1"
                    return widgets.Label{
                        frame = {t=6, l=0},
                        text  = {
                            "Energy:   ",
                            {text=fmt_energy(pool), pen=COLOR_CYAN},
                            {text=caravan and "  [Caravan docked]" or "", pen=COLOR_GREEN},
                        },
                    }
                end)(),
            },
        }
    end

    -- ── Tab: Goal ─────────────────────────────────────────────────────
    local function GoalTab()
        table.insert(tab_list, "Goal")
        return widgets.Panel{
            subviews = { make_list(build_goal_lines()) },
        }
    end

    -- ── Tab 2: Unlocks ────────────────────────────────────────────────
    local function UnlocksTab()
        table.insert(tab_list, "Unlocks")
        return widgets.Panel{
            subviews = { make_list(build_unlocks_lines()) },
        }
    end

    local function ChecksTab()
        table.insert(tab_list, "Checks")
        local list = make_list(build_checks_lines(), {t=2, b=0})
        local function refresh() list:setChoices(lines_to_choices(build_checks_lines())) end
        return widgets.Panel{
            subviews = {
                widgets.HotkeyLabel{
                    frame       = {t=0, l=0},
                    key         = "CUSTOM_SHIFT_O",
                    label       = function()
                        return checks_sort and "Sort: actionable first (ON)"
                                            or  "Sort: by category (OFF)"
                    end,
                    on_activate = function()
                        checks_sort = not checks_sort
                        refresh()
                    end,
                },
                list,
            },
        }
    end

    local function CavesTab()
        table.insert(tab_list, "Caves")
        return widgets.Panel{
            subviews = { make_list(build_caves_lines()) },
        }
    end

    -- ── Tab 4: Crafts ─────────────────────────────────────────────────
    local function CraftsanityTab()
        table.insert(tab_list, "Crafts")
        return widgets.Panel{
            subviews = { make_list(build_crafts_lines()) },
        }
    end

    -- ── Tab 5: Controls ──────────────────────────────────────────────

    local function ControlsTab()
        table.insert(tab_list, "Controls")
        return widgets.Panel{
            subviews = {
                widgets.Label{frame={t=0, l=0}, text="Controls:"},
                widgets.HotkeyLabel{
                    frame = {t=2, l=2},
                    key   = "CUSTOM_SHIFT_S",
                    label = enabled and "Restart mod" or "Start mod",
                    on_activate = function()
                        if enabled then
                            dfhack.run_command("dwarfipelago", "stop")
                            dfhack.run_command("dwarfipelago", "start")
                        else
                            dfhack.run_command("dwarfipelago", "start")
                        end
                        self:dismiss()
                    end,
                },
                widgets.HotkeyLabel{
                    frame = {t=3, l=2},
                    key   = "CUSTOM_SHIFT_R",
                    label = "Reset all AP state",
                    on_activate = function()
                        dfhack.run_command("dwarfipelago", "progress-wipe")
                        self:dismiss()
                    end,
                },
                widgets.HotkeyLabel{
                    frame = {t=4, l=2},
                    key   = "CUSTOM_SHIFT_D",
                    label = "Reset seed",
                    on_activate = function()
                        dfhack.run_command("dwarfipelago", "resetseed")
                        self:dismiss()
                    end,
                },
            },
        }
    end

    -- ── Tab 6: Energy ─────────────────────────────────────────────────
    function EnergyTab()
        local pool    = tonumber(ps("energy_link", "0")) or 0
        local caravan = ps("ap_caravan_active", "0") == "1"
        local pending = ps("request_caravan", "0") == "1"

        local season = 0
        pcall(function() season = df.global.world.cur_season end)
        local snames = {"Spring","Summer","Fall","Winter"}
        local scosts = {300, 150, 50, 500}
        local sname  = snames[(season % 4) + 1]
        local scost  = scosts[(season % 4) + 1]

        local ale_count = 0
        pcall(function() ale_count = checks.count_fortress_drinks() end)
        local food_count = 0
        pcall(function() food_count = #checks.find_fortress_food() end)
        local _, coins_j = 0, 0
        pcall(function() _, coins_j = checks.find_fortress_coins_energy() end)
        local coins_val = math.floor(coins_j / 1000)  -- ☼ face value

        local status_tag = caravan and "  [Caravan docked]"
                    or (pending and "  [Request pending]" or "")
        local status_pen = caravan and COLOR_GREEN or COLOR_YELLOW

        local pool_mj_str  = fmt_energy(pool)
        local pool_kj_str  = pool >= 1000000
            and ("(" .. fmt_num(math.floor(pool / 1000)) .. " kJ)") or ""
        table.insert(tab_list, "Energy")
        return widgets.Panel{ subviews = {
            widgets.Label{frame={t=0,l=0}, text={
                "Pool:     ",
                {text=pool_mj_str,  pen=COLOR_CYAN},
                "  ",
                {text=pool_kj_str,  pen=COLOR_DARKGRAY},
                {text=status_tag,   pen=status_pen},
            }},
            widgets.Label{frame={t=1,l=0}, text={
                "Season:   ",
                {text=sname, pen=COLOR_WHITE},
                "  Caravan cost: ",
                {text=fmt_num(scost).." MJ",
                pen=(pool >= scost * 1000000) and COLOR_GREEN or COLOR_RED},
            }},
            widgets.Label{frame={t=2,l=0}, text={
                "Stocks:   ",
                {text=fmt_num(ale_count).." ale", pen=COLOR_YELLOW},
                "  ",
                {text=fmt_num(food_count).." food", pen=COLOR_YELLOW},
                "  ",
                {text=fmt_num(coins_val).." * in coins", pen=COLOR_YELLOW},
            }},
            widgets.HotkeyLabel{
                frame={t=4,l=2}, key="CUSTOM_SHIFT_A",
                label="Deposit Ale",
                on_activate=function()
                    self:dismiss()
                    local avail = 0
                    pcall(function() avail = checks.count_fortress_drinks() end)
                    dialogs.showInputPrompt(
                        "Deposit Ale",
                        ("Ale units to deposit (available: %d, 100 kJ each):"):format(avail),
                        COLOR_WHITE, "",
                        function(text)
                            local n = math.floor(tonumber(text) or 0)
                            if n > 0 then
                                dfhack.run_command("dwarfipelago", "deposit-ale", tostring(n))
                            end
                        end
                    )
                end,
            },
            widgets.HotkeyLabel{
                frame={t=5,l=2}, key="CUSTOM_SHIFT_F",
                label="Deposit Food",
                on_activate=function()
                    self:dismiss()
                    local avail = 0
                    pcall(function() avail = #checks.find_fortress_food() end)
                    dialogs.showInputPrompt(
                        "Deposit Food",
                        ("Food items to deposit (available: %d, 50 kJ each):"):format(avail),
                        COLOR_WHITE, "",
                        function(text)
                            local n = math.floor(tonumber(text) or 0)
                            if n > 0 then
                                dfhack.run_command("dwarfipelago", "deposit-food", tostring(n))
                            end
                        end
                    )
                end,
            },
            widgets.HotkeyLabel{
                frame={t=6,l=2}, key="CUSTOM_SHIFT_C",
                label=("Deposit Coins (%s * avail)"):format(fmt_num(coins_val)),
                on_activate=function()
                    self:dismiss()
                    local avail = 0
                    pcall(function()
                        local _, cj = checks.find_fortress_coins_energy()
                        avail = math.floor(cj / 1000)
                    end)
                    dialogs.showInputPrompt(
                        "Deposit Coins",
                        ("Coin value to deposit in * (available: %s *, 1 kJ per *):"):format(fmt_num(avail)),
                        COLOR_WHITE, "",
                        function(text)
                            local n = math.floor(tonumber(text) or 0)
                            if n > 0 then
                                dfhack.run_command("dwarfipelago", "deposit-coins", tostring(n))
                            end
                        end
                    )
                end,
            },
            widgets.HotkeyLabel{
                frame={t=8,l=2}, key="CUSTOM_SHIFT_V",
                label=("Call Caravan (%d MJ, %s)"):format(scost, sname),
                on_activate=function()
                    dfhack.run_command("dwarfipelago", "call-caravan")
                    self:dismiss()
                end,
            },
        }}
    end

    -- ── Tab 7: Permits ─────────────────────────────────────────────────
    function PermitsTab()
        table.insert(tab_list, "Permits")
        return widgets.Panel{
            subviews = { make_list(build_permit_lines()) },
        }
    end

    -- ── Tab 8: Skills ─────────────────────────────────────────────────
    function SkillsTab()
        table.insert(tab_list, "Skills")
        return widgets.Panel{
            subviews = { make_list(build_skill_lines()) },
        }
    end

    -- ── Tab: War Effort (Slay Megabeast goal only) ────────────────────────────
    -- War status plus the player-initiated "summon the beast" button: the beast is
    -- never forced - the player chooses when to face it once the war effort
    -- (10 Military Training + Artifact Weapon + 2 Immigration Waves) is complete.
    function WarTab()
        table.insert(tab_list, "War")
        local spawned  = ps("megabeast/spawned", "0") == "1"
        local complete = ps("goal_complete", "0") == "1"
        local mt   = tonumber(ps("unlock/military_training", "0")) or 0
        local imm  = tonumber(ps("unlock/immigration_waves", "0")) or 0
        local art  = ps("unlock/artifact_weapon", "0") == "1"
        local barracks, soldiers = false, 0
        pcall(function() barracks = checks.barracks_is_set_up() end)
        pcall(function() soldiers = checks.count_military_skill(10) end)
        local cap = 4
        if barracks then cap = 6 end
        if barracks and soldiers >= 4 then cap = 9 end
        local ready = mt >= 10 and art and imm >= 2

        local status, status_pen
        if complete then     status, status_pen = "The beast is SLAIN - victory!",                 COLOR_GREEN
        elseif spawned then  status, status_pen = "The beast walks your lands - slay it!",          COLOR_RED
        elseif ready then    status, status_pen = "The war effort is complete - summon when ready!", COLOR_LIGHTRED
        else                 status, status_pen = "Mustering the war effort...",                    COLOR_YELLOW end

        local summon_lbl
        if spawned then     summon_lbl = "Beast already summoned"
        elseif ready then   summon_lbl = "Summon the Megabeast!"
        else                summon_lbl = "Summon the Megabeast  (war effort incomplete)" end

        return widgets.Panel{ subviews = {
            widgets.Label{frame={t=0,l=0}, text="War Effort  (Slay Megabeast)", text_pen=COLOR_CYAN},
            widgets.Label{frame={t=2,l=2}, text=("Military Training: %d/10      War Readiness: %d/9"):format(mt, math.min(mt, cap))},
            widgets.Label{frame={t=3,l=2}, text=("Barracks: %-3s   Soldiers at skill 10: %d/4"):format(barracks and "YES" or "no", soldiers)},
            widgets.Label{frame={t=4,l=2}, text=("Artifact Weapon: %-3s   Immigration: %d/2"):format(art and "YES" or "no", imm)},
            widgets.Label{frame={t=6,l=2}, text={{text="Beast: "}, {text=status, pen=status_pen}}},
            widgets.HotkeyLabel{
                frame = {t=8,l=2},
                key   = "CUSTOM_SHIFT_M",
                label = summon_lbl,
                on_activate = function()
                    dfhack.run_command("dwarfipelago", "summon-beast")
                    self:dismiss()
                end,
            },
        }}
    end

    local tabviews = {}
    table.insert(tabviews, StatusTab())
    table.insert(tabviews, GoalTab())
    if tonumber(ps("goal", "-1")) == 0 then
        table.insert(tabviews, WarTab())
    end
    table.insert(tabviews, UnlocksTab())
    table.insert(tabviews, ChecksTab())
    table.insert(tabviews, CavesTab())
    if ps("craftsanity_enabled", "0") ~= "0" then
        table.insert(tabviews, CraftsanityTab())
    end   
    table.insert(tabviews, ControlsTab())
    if ps("energy_enabled", "0") ~= "0" then
        table.insert(tabviews, EnergyTab())
    end
    if ps("crafting_permits", "0") ~= "0" then
        table.insert(tabviews, PermitsTab())
    end
    if ps("skillsanity_enabled", "0") ~= "0" then
        table.insert(tabviews, SkillsTab())
    end
    local pages = widgets.Pages{
        frame = {t=4, b=2},
        subviews = tabviews,
    }

    self:addviews{
        widgets.Window{
            frame_title       = ("Dwarfipelago v%s"):format(version),
            frame             = {w=W, h=H, t=3, l=3},
            resizable         = true,
            resize_min        = {w=46, h=20},
            frame_style       = make_ap_frame,
            frame_background  = to_pen{ch=32, fg=0, bg=COLOR_BLACK, write_to_lower=true},
            subviews    = {
                widgets.TabBar{
                    frame        = {t=0, l=0},
                    labels       = tab_list,
                    on_select    = function(idx) pages:setSelected(idx) end,
                    get_cur_page = function() return pages:getSelected() end,
                },
                pages,
                widgets.HotkeyLabel{
                    frame = {b=0, l=2},
                    key   = "LEAVESCREEN",
                    label = "Close",
                    on_activate = function() self:dismiss() end,
                },
            },
        },
    }
end

-- ── Archipelago logo tileset ──────────────────────────────────────────────────

local _ap_logo_handles = nil
local function load_ap_logo()
    if _ap_logo_handles then return end
    local mod_path = scriptmanager.getModSourcePath('dwarfipelago')
    if not mod_path then return end
    local path = mod_path .. 'scripts_modinstalled/art/ap-logo.png'
    local ok, result = pcall(dfhack.textures.loadTileset, path, 24, 36, true)
    if ok and result and #result > 0 then
        _ap_logo_handles = result
    end
end

-- ── Corner hotspot widget ─────────────────────────────────────────────────────

local _ap_hotspot_positioned = false

DwarfipelagoHotspot = defclass(DwarfipelagoHotspot, overlay.OverlayWidget)
DwarfipelagoHotspot.ATTRS{
    desc            = "Dwarfipelago: click [AP] to open the status and control panel",
    default_pos     = {x=42, y=-1},
    default_enabled = true,
    hotspot         = true,
    viewscreens     = {"dwarfmode"},
    frame           = {w=4, h=3},
}

function DwarfipelagoHotspot:init()
    self.frame_background = to_pen{ch=32, fg=COLOR_LIGHTCYAN, bg=COLOR_BLUE}
    pcall(load_ap_logo)
    self:addviews{
        widgets.Label{
            frame = {t=0, l=0},
            text_pen = to_pen{fg=COLOR_LIGHTCYAN, bg=COLOR_BLUE},
            text = 'AP',
            visible = function() return not _ap_logo_handles end,
        },
    }
end

function DwarfipelagoHotspot:onRenderBody(dc)
    if not _ap_logo_handles then
        self:renderSubviews(dc)
        return
    end
    local W, H = 4, 3
    local idx = 1
    for row = 0, H - 1 do
        for col = 0, W - 1 do
            if idx <= #_ap_logo_handles then
                local texpos = dfhack.textures.getTexposByHandle(_ap_logo_handles[idx])
                dc:seek(col, row):char(219, to_pen{ch=219, tile=texpos, fg=COLOR_WHITE, bg=COLOR_BLUE})
                idx = idx + 1
            end
        end
    end
end

function DwarfipelagoHotspot:overlay_onupdate()
    if not _ap_hotspot_positioned then
        _ap_hotspot_positioned = true
        dfhack.run_command('overlay', 'position', 'dwarfipelago-panel.hotspot', 'default')
    end
end

function DwarfipelagoHotspot:onInput(keys)
    if keys._MOUSE_L then
        local x, y = self:getMouseFramePos()
        if x then
            open_panel()
            return true
        end
    end
    return DwarfipelagoHotspot.super.onInput(self, keys)
end

-- ── Module exports ────────────────────────────────────────────────────────────

function open_panel()
    if _panel_instance then
        _panel_instance:dismiss()
    else
        _panel_instance = DwarfipelagoPanel{}
        _panel_instance:show()
    end
end

-- Auto-discovery table - DFHack registers this widget when the script is loaded.
-- The screen-scrape overlays (permits, buildmenu) live in dwarfipelago-overlays.lua.
OVERLAY_WIDGETS = {
    hotspot = DwarfipelagoHotspot,
}

-- When called directly (not as a module), open the panel immediately.
if not dfhack.current_script_is_module() then
    if dfhack.isMapLoaded() then
        open_panel()
    else
        dfhack.printerr("[Dwarfipelago] Load a fortress first.")
    end
end
