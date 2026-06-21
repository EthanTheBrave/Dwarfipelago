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
-- border tile index layout (indices 1–21 used by make_frame).
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

local function make_list(lines)
    local choices = {}
    for _, line in ipairs(lines) do
        if type(line) == "string" then
            table.insert(choices, {text=line, pen=COLOR_WHITE})
        else
            table.insert(choices, line)
        end
    end
    return widgets.List{
        frame      = {t=0, b=0},
        choices    = choices,
        text_pen   = COLOR_WHITE,
        cursor_pen = COLOR_CYAN,
    }
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
            or def.key == "monarch_invitation" or def.key == "RotGK" then
                goto continue
            end
        elseif goal == 1 then
            if def.key == "military_training" or def.key == "baron_charter"
            or def.key == "count_charter" or def.key == "duke_charter"
            or def.key == "monarch_invitation" or def.key == "RotGK"
            or def.key == "artifact_weapon" or def.key == "artifact_armor" then
                goto continue
            end
        elseif goal == 2 then
            if def.key == "military_training" or def.key == "RotGK"
            or def.key == "artifact_armor" or def.key == "wealth_coffers" then
                goto continue
            end
        elseif goal == 3 then
            if def.key == "military_training" or def.key == "baron_charter"
            or def.key == "count_charter" or def.key == "duke_charter"
            or def.key == "monarch_invitation" or def.key == "RotGK"
            or def.key == "wealth_coffers" then
                goto continue
            end
        elseif goal == 4 then
            if def.key == "military_training" or def.key == "baron_charter"
            or def.key == "count_charter" or def.key == "duke_charter"
            or def.key == "monarch_invitation" or def.key == "wealth_coffers" then
                goto continue
            elseif def.key == "RotGK" then
                def.max = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/king_remains_goal") or 99)
            end
        end
        local raw = ps("unlock/" .. def.key, "0")
        if def.max then
            item_count(def.label, raw, def.max)
        else
            item_bool(def.label, raw == "1")
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

local DEPTH_THRESHOLDS  = {10, 25, 50, 75, 100}
local TILES_THRESHOLDS  = {100, 500, 2000, 5000, 10000}
local CROPS_THRESHOLDS  = {50, 100, 250, 500, 1000}
local WEALTH_THRESHOLDS = {1000, 10000, 50000, 100000, 500000}

local PROD_FLAGS = {
    {"Crafted item",   "crafted_item",  "Weapon forged",  "weapon"},
    {"Armor crafted",  "armor",         "Furniture made", "furniture"},
    {"Meal prepared",  "meal",          "Brew complete",  "brew"},
    {"Metal bar",      "metal_bar",     "Stone block",    "stone_block"},
    {"Cloth woven",    "cloth",         "Leather tanned", "leather"},
    {"Gem cut",        "gem",           "Mechanism",      "mechanism"},
    {"Trap built",     "trap",          "Cage built",     "cage"},
    {"Barrel made",    "barrel",        "Chest made",     "chest"},
    {"Table made",     "table",         "Bed made",       "bed"},
    {"Anvil forged",   "anvil",         "Millstone",      "millstone"},
    {"Minecart",       "minecart",      nil,              nil},
}

local function build_progress_lines()
    local lines = {}

    local function hdr(s)
        table.insert(lines, {text=s, pen=COLOR_CYAN})
    end
    local function row(s, pen)
        table.insert(lines, {text=s, pen=pen or COLOR_WHITE})
    end
    local function blank()
        table.insert(lines, {text=""})
    end

    -- Mining
    hdr("Mining")
    local depth = checks.mining_depth()
    local tiles = checks.mining_count()
    local nd = next_thresh(depth, DEPTH_THRESHOLDS)
    local nt = next_thresh(tiles, TILES_THRESHOLDS)
    row(("  Depth:  %d levels%s"):format(
        depth, nd and ("  (next: %d)"):format(nd) or "  (all done!)"))
    row(("  Tiles:  %s excavated%s"):format(
        fmt_num(tiles), nt and ("  (next: %s)"):format(fmt_num(nt)) or "  (all done!)"))
    local c1 = checks.mining_flag("cavern1")
    local c2 = checks.mining_flag("cavern2")
    local c3 = checks.mining_flag("cavern3")
    local mg = checks.mining_flag("magma")
    row(("  Cavern 1: %-3s  2: %-3s  3: %-3s    Magma: %-3s"):format(
        c1 and "YES" or "no", c2 and "YES" or "no",
        c3 and "YES" or "no", mg and "YES" or "no"))

    -- Farming
    blank()
    hdr("Farming")
    local crops = checks.crops_harvested()
    local nc = next_thresh(crops, CROPS_THRESHOLDS)
    row(("  Crops harvested: %s%s"):format(
        fmt_num(crops), nc and ("  (next: %s)"):format(fmt_num(nc)) or "  (all done!)"))

    -- Treasury
    blank()
    hdr("Treasury  (coins + cut gems)")
    local wealth = checks.treasury_wealth()
    local nw = next_thresh(wealth, WEALTH_THRESHOLDS)
    row(("  Current: %s%s"):format(
        fmt_num(wealth), nw and ("  (next: %s)"):format(fmt_num(nw)) or "  (all done!)"))

    -- Production
    blank()
    hdr("Production  (first completed)")
    for _, pair in ipairs(PROD_FLAGS) do
        local a_lbl, a_key, b_lbl, b_key = pair[1], pair[2], pair[3], pair[4]
        local a_val = checks.production_flag(a_key)
        if b_lbl then
            local b_val = checks.production_flag(b_key)
            local pen = (a_val or b_val) and COLOR_WHITE or COLOR_DARKGRAY
            row(("  %-16s %-4s  %-16s %-4s"):format(
                a_lbl .. ":", a_val and "YES" or "no",
                b_lbl .. ":", b_val and "YES" or "no"), pen)
        else
            row(("  %-16s %-4s"):format(a_lbl .. ":", a_val and "YES" or "no"),
                a_val and COLOR_WHITE or COLOR_DARKGRAY)
        end
    end

    -- Trade & diplomacy
    blank()
    hdr("Trade & Diplomacy")
    local function tf(key) return checks.trade_flag(key) end
    row(("  Dwarven caravan: %-3s  Liaison: %-3s"):format(
        tf("dwarven_caravan") and "YES" or "no",
        tf("liaison_met") and "YES" or "no"))
    row(("  Elven caravan:  %-3s  Human caravan: %-3s"):format(
        tf("elven_caravan") and "YES" or "no",
        tf("human_caravan") and "YES" or "no"))
    row(("  Raid: %-3s  Recovery: %-3s  Diplomacy: %-3s"):format(
        tf("first_raid") and "YES" or "no",
        tf("first_recovery") and "YES" or "no",
        tf("first_diplomacy") and "YES" or "no"))

    -- Nobles
    blank()
    hdr("Nobles")
    local function noble(code)
        local ok, units = pcall(dfhack.units.getUnitsByNobleRole, code)
        return ok and units ~= nil and #units > 0
    end
    local mayor   = noble("MAYOR")
    local baron   = noble("BARON")   and ps("unlock/baron_charter",      "0") == "1"
    local count   = noble("COUNT")   and ps("unlock/count_charter",      "0") == "1"
    local duke    = noble("DUKE")    and ps("unlock/duke_charter",       "0") == "1"
    local monarch = (noble("KING") or noble("QUEEN"))
                    and ps("unlock/monarch_invitation", "0") == "1"
    row(("  Mayor: %-3s   Baron: %-3s   Count: %-3s"):format(
        mayor and "YES" or "no", baron and "YES" or "no", count and "YES" or "no"))
    row(("  Duke:  %-3s   Monarch: %-3s"):format(
        duke and "YES" or "no", monarch and "YES" or "no"))

    -- Fortress
    blank()
    hdr("Fortress")
    local pop = 0
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
            pop = pop + 1
        end
    end
    local fw = checks.fortress_wealth()
    row(("  Population:      %d citizens"):format(pop))
    row(("  Fortress wealth: %s"):format(fmt_num(fw)))

    return lines
end

-- ── Craftsanity list ──────────────────────────────────────────────────────────

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
        })
    end
    -- Sort: in-progress (count desc) → not-started (alpha) → done (alpha)
    table.sort(list, function(a, b)
        if a.is_done ~= b.is_done then return not a.is_done end
        if (a.count > 0) ~= (b.count > 0) then return a.count > b.count end
        if a.count ~= b.count then return a.count > b.count end
        return a.label < b.label
    end)

    local n_done = 0
    for _, e in ipairs(list) do
        if e.is_done then
            n_done = n_done + 1
            row(("  %-26s  %6s   DONE (%d/%d)"):format(
                e.label, fmt_num(e.count), checks_per_item, checks_per_item),
                COLOR_GREEN)
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
    local craft_counts = checks.get_all_craft_counts()
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
    -- -- Sort: done (alpha) → not done (alpha) 
    table.sort(list, function(a, b)
        return a.done > b.done
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

-- Live-refresh the Shop tab (shrine status can change while the panel is open).
-- Throttled so we rebuild the list only a couple of times a second.
function DwarfipelagoPanel:onRenderFrame(dc, rect)
    DwarfipelagoPanel.super.onRenderFrame(self, dc, rect)
    self._refresh_tick = (self._refresh_tick or 0) + 1
    if self._shop_refresh and self._refresh_tick % 30 == 0 then
        pcall(self._shop_refresh)
    end
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

    local W, H = 62, 48

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

    -- ── Tab 2: Unlocks ────────────────────────────────────────────────
    local function UnlocksTab()
        table.insert(tab_list, "Unlocks")
        return widgets.Panel{
            subviews = { make_list(build_unlocks_lines()) },
        }
    end

    -- ── Tab 3: Progress ───────────────────────────────────────────────
    local function ProgressTab()
        table.insert(tab_list, "Progress")
        return widgets.Panel{
            subviews = { make_list(build_progress_lines()) },
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
                        dfhack.run_command("dwarfipelago", "reset")
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

    -- ── Tab 9: Shop ───────────────────────────────────────────────────
    -- Coffer-gated merchant shop. Select a slot and press Enter to spend minted
    -- coins on its item. Slot data is written by the AP client (dwarfipelago/shop).
    function ShopTab()
        table.insert(tab_list, "Shop")
        local sjson = require('json')

        local function read_state()
            local sraw = ps("shop", "")
            local shop = (sraw ~= "" and sjson.decode(sraw)) or {}
            local praw = ps("shop_pending", "")
            local pending = (praw ~= "" and sjson.decode(praw)) or {}
            local coffers = tonumber(ps("unlock/wealth_coffers", "0")) or 0
            local _, total_j = nil, 0
            pcall(function() _, total_j = checks.find_fortress_coins_energy() end)
            local coins = math.floor((total_j or 0) / 1000)
            local unlocked = ps("shop_unlocked", "0") == "1"
            local prograw = ps("shrine_progress", "")
            local prog = (prograw ~= "" and sjson.decode(prograw)) or {}
            return shop, pending, coffers, coins, unlocked, prog
        end

        local function build_choices(shop, pending, coffers, coins, unlocked)
            local choices, slots = {}, {}
            for k in pairs(shop) do table.insert(slots, tonumber(k)) end
            table.sort(slots)
            for _, sn in ipairs(slots) do
                local e = shop[tostring(sn)]
                local price = tonumber(e.price) or 0
                local state, pen, buyable
                if e.bought == 1 then
                    state, pen = "SOLD", COLOR_DARKGRAY
                elseif pending[tostring(sn)] then
                    state, pen = "PENDING", COLOR_LIGHTBLUE
                elseif not unlocked then
                    state, pen = "shrine needed", COLOR_DARKGRAY
                elseif coffers < (e.tier or 1) then
                    state, pen = ("LOCKED (%d coffers)"):format(e.tier or 1), COLOR_RED
                elseif coins < price then
                    state, pen = "need coins", COLOR_YELLOW
                else
                    state, pen, buyable = "BUY", COLOR_GREEN, true
                end
                local text = ("%-20.20s -> %-12.12s %8s* [%s]"):format(
                    tostring(e.item or "?"), tostring(e.player or "?"), fmt_num(price), state)
                table.insert(choices, {text = text, pen = pen, slot = sn, buyable = buyable})
            end
            if #choices == 0 then
                table.insert(choices, {text = "(waiting for the AP client -- shop items load shortly)",
                                       pen = COLOR_DARKGRAY})
            end
            return choices
        end

        local chk = function(b) return b and {text="yes", pen=COLOR_GREEN} or {text="no", pen=COLOR_RED} end
        local shrine_head, req_label, bar_sel, coin_label, shop_list

        -- Bar type options: value stored to persistent state so the AP client can read it
        local BAR_REQ = {gold=5, coke=20, silver=10}
        local BAR_OPTS = {
            {label="Gold   (5 req)",   value="gold"},
            {label="Coke   (20 req)",  value="coke"},
            {label="Silver (10 req)",  value="silver"},
        }

        local function head_text(unlocked)
            if unlocked then
                return {{text="Shrine: DETECTED", pen=COLOR_GREEN}, "  (shop is open)"}
            end
            return {{text="Shrine: NOT DETECTED", pen=COLOR_RED},
                    "  - build/repair the temple to open the shop"}
        end

        local function req_text(prog, btype)
            local req = BAR_REQ[btype] or 5
            local vc  = (prog.value  or 0) >= (prog.value_req or 5000) and COLOR_GREEN or COLOR_YELLOW
            local bc  = (prog.bars   or 0) >= req                      and COLOR_GREEN or COLOR_YELLOW
            return {
                "  Value: ",  {text=fmt_num(prog.value or 0).."/"..fmt_num(prog.value_req or 5000), pen=vc},
                "   Altar: ", chk(prog.altar),
                "   Box: ",   chk(prog.bin),
                "   Bars: ",  {text=("%d/%d"):format(prog.bars or 0, req), pen=bc},
            }
        end

        local function coin_text(coffers, coins)
            return {
                "  Coins: ", {text=fmt_num(coins).."*",      pen=COLOR_YELLOW},
                "   Coffers: ",       {text=tostring(coffers).."/5",  pen=COLOR_CYAN},
                "   (Enter to buy)",
            }
        end

        local function refresh()
            local shop, pending, coffers, coins, unlocked, prog = read_state()
            local btype = bar_sel and bar_sel:getOptionValue() or
                          dfhack.persistent.getWorldDataString("dwarfipelago/shrine_bar_type") or "gold"
            if shrine_head then shrine_head:setText(head_text(unlocked)) end
            if req_label   then req_label:setText(req_text(prog, btype)) end
            if coin_label  then coin_label:setText(coin_text(coffers, coins)) end
            if shop_list   then
                shop_list:setChoices(build_choices(shop, pending, coffers, coins, unlocked),
                                     shop_list:getSelected())
            end
        end

        local shop0, pending0, coffers0, coins0, unlocked0, prog0 = read_state()
        local init_bar = dfhack.persistent.getWorldDataString("dwarfipelago/shrine_bar_type") or "gold"

        shrine_head = widgets.Label{frame={t=0, l=0}, text=head_text(unlocked0)}
        req_label   = widgets.Label{frame={t=1, l=0}, text=req_text(prog0, init_bar)}
        bar_sel = widgets.CycleHotkeyLabel{
            frame          = {t=2, l=0},
            key            = "CUSTOM_B",
            label          = "  Bar type: ",
            options        = BAR_OPTS,
            initial_option = init_bar,
            on_change      = function(value)
                dfhack.persistent.saveWorldDataString("dwarfipelago/shrine_bar_type", value)
                refresh()
            end,
        }
        coin_label = widgets.Label{frame={t=3, l=0}, text=coin_text(coffers0, coins0)}
        shop_list = widgets.List{
            frame      = {t=5, b=0},
            text_pen   = COLOR_WHITE,
            cursor_pen = COLOR_CYAN,
            choices    = build_choices(shop0, pending0, coffers0, coins0, unlocked0),
            on_submit  = function(_, choice)
                if choice and choice.buyable and choice.slot then
                    dfhack.run_command("dwarfipelago", "buy-shop", tostring(choice.slot))
                    refresh()
                end
            end,
        }
        self._shop_refresh = refresh   -- onRenderFrame calls this to live-update
        return widgets.Panel{subviews={shrine_head, req_label, bar_sel, coin_label, shop_list}}
    end

    local tabviews = {}
    table.insert(tabviews, StatusTab())
    table.insert(tabviews, UnlocksTab())
    table.insert(tabviews, ProgressTab())
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
    -- Shop tab is always present so the shrine status shows immediately; the slot
    -- list fills in once the AP client writes shop data (refreshed by onRenderFrame).
    table.insert(tabviews, ShopTab())

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

-- Auto-discovery table — DFHack registers this widget when the script is loaded.
-- Widget name as seen by the overlay system: "dwarfipelago-panel.hotspot"
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
