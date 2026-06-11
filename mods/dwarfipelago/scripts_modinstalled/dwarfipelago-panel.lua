--@ module = true
-- Dwarfipelago status and control panel.
-- Can be opened three ways:
--   1. Click the [AP] hotspot button in the corner of the fortress screen.
--   2. Run: dwarfipelago panel
--   3. Run directly: dwarfipelago-panel

local gui     = require('gui')
local overlay = require('plugins.overlay')
local widgets = require('gui.widgets')
local dialogs = require('gui.dialogs')
local state   = reqscript('internal/dwarfipelago/state')
local items   = reqscript('internal/dwarfipelago/items')
local checks  = reqscript('internal/dwarfipelago/checks')

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
        local raw = ps("unlock/" .. def.key, "0")
        if def.max then
            item_count(def.label, raw, def.max)
        else
            item_bool(def.label, raw == "1")
        end
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
    row(("  Trade done: %-3s      First export: %-3s"):format(
        tf("trade_completed") and "YES" or "no",
        tf("first_export") and "YES" or "no"))
    row(("  Dwarven caravan: %-3s  Liaison: %-3s"):format(
        tf("dwarven_caravan") and "YES" or "no",
        tf("liaison_met") and "YES" or "no"))
    row(("  Elven caravan:  %-3s  Human caravan: %-3s"):format(
        tf("elven_caravan") and "YES" or "no",
        tf("human_caravan") and "YES" or "no"))

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
            row(("  %-26s  %6s → %-7s %d/%d"):format(
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

-- ── Status / control popup ────────────────────────────────────────────────────

local _panel_instance = nil

DwarfipelagoPanel = defclass(DwarfipelagoPanel, gui.ZScreen)
DwarfipelagoPanel.ATTRS{
    focus_path = "dwarfipelago/panel",
}

function DwarfipelagoPanel:onDismiss()
    _panel_instance = nil
end

function DwarfipelagoPanel:init()
    local enabled  = state.is_enabled()
    local version  = ps("version",       "?")
    local goal_key = ps("goal",          "-1")
    local complete = ps("goal_complete", "0") == "1"
    local depot    = ps("depot_built",   "0") == "1"

    local goal_str = GOAL_NAMES[goal_key] or "Not synced"

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

    local pages = widgets.Pages{
        frame = {t=2, b=2},
        subviews = {
            -- ── Tab 1: Status ────────────────────────────────────────────────
            widgets.Panel{
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
                        local mj       = math.floor(pool / 1000000)
                        local caravan  = ps("ap_caravan_active", "0") == "1"
                        return widgets.Label{
                            frame = {t=6, l=0},
                            text  = {
                                "Energy:   ",
                                {text=fmt_num(mj) .. " MJ", pen=COLOR_CYAN},
                                {text=caravan and "  [Caravan docked]" or "", pen=COLOR_GREEN},
                            },
                        }
                    end)(),
                },
            },
            -- ── Tab 2: Unlocks ────────────────────────────────────────────────
            widgets.Panel{
                subviews = { make_list(build_unlocks_lines()) },
            },
            -- ── Tab 3: Progress ───────────────────────────────────────────────
            widgets.Panel{
                subviews = { make_list(build_progress_lines()) },
            },
            -- ── Tab 4: Crafts ─────────────────────────────────────────────────
            widgets.Panel{
                subviews = { make_list(build_crafts_lines()) },
            },
            -- ── Tab 5: Controls ──────────────────────────────────────────────
            widgets.Panel{
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
            },
            -- ── Tab 6: Energy ─────────────────────────────────────────────────
            (function()
                if ps("energy_enabled", "0") ~= "1" then
                    return widgets.Panel{ subviews = {
                        widgets.Label{frame={t=1,l=1}, text={
                            {text="Energy Link not enabled for this slot.", pen=COLOR_DARKGRAY}
                        }},
                    }}
                end

                local pool    = tonumber(ps("energy_link", "0")) or 0
                local mj      = math.floor(pool / 1000000)
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

                local status_tag = caravan and "  [Caravan docked]"
                               or (pending and "  [Request pending]" or "")
                local status_pen = caravan and COLOR_GREEN or COLOR_YELLOW

                return widgets.Panel{ subviews = {
                    widgets.Label{frame={t=0,l=0}, text={
                        "Pool:     ",
                        {text=fmt_num(mj).." MJ", pen=COLOR_CYAN},
                        {text=status_tag, pen=status_pen},
                    }},
                    widgets.Label{frame={t=1,l=0}, text={
                        "Season:   ",
                        {text=sname, pen=COLOR_WHITE},
                        "  Caravan cost: ",
                        {text=fmt_num(scost).." MJ",
                         pen=(mj >= scost) and COLOR_GREEN or COLOR_RED},
                    }},
                    widgets.Label{frame={t=2,l=0}, text={
                        "Stocks:   ",
                        {text=fmt_num(ale_count).." ale", pen=COLOR_YELLOW},
                        "  ",
                        {text=fmt_num(food_count).." food", pen=COLOR_YELLOW},
                        "  ",
                        {text=fmt_num(math.floor(coins_j/1000)).." kJ in coins", pen=COLOR_YELLOW},
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
                                ("Ale units to deposit (available: %d, 1 MJ each):"):format(avail),
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
                                ("Food items to deposit (available: %d, 0.5 MJ each):"):format(avail),
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
                        label=("Deposit Coins (all, ~%.1f MJ)"):format(coins_j/1000000),
                        on_activate=function()
                            dfhack.run_command("dwarfipelago", "deposit-coins")
                            self:dismiss()
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
                    widgets.HotkeyLabel{
                        frame={t=9,l=2}, key="CUSTOM_SHIFT_D",
                        label="Dismiss Caravan",
                        on_activate=function()
                            dfhack.run_command("dwarfipelago", "dismiss-caravan")
                            self:dismiss()
                        end,
                    },
                }}
            end)(),
        },
    }

    self:addviews{
        widgets.Window{
            frame_title = ("Dwarfipelago v%s"):format(version),
            frame       = {w=W, h=H, t=3, l=3},
            resizable   = true,
            resize_min  = {w=46, h=20},
            subviews    = {
                widgets.TabBar{
                    frame        = {t=0, l=0},
                    labels       = {"Status", "Unlocks", "Progress", "Crafts", "Controls", "Energy"},
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

-- ── Corner hotspot widget ─────────────────────────────────────────────────────

DwarfipelagoHotspot = defclass(DwarfipelagoHotspot, overlay.OverlayWidget)
DwarfipelagoHotspot.ATTRS{
    desc            = "Dwarfipelago: click [AP] to open the status and control panel",
    default_pos     = {x=6, y=2},
    default_enabled = true,
    hotspot         = true,
    viewscreens     = {"dwarfmode"},
    frame           = {w=4, h=1},
}

function DwarfipelagoHotspot:init()
    self:addviews{
        widgets.Label{
            frame = {t=0, l=0},
            text  = {{text="[AP]", pen=COLOR_CYAN}},
        },
    }
end

function DwarfipelagoHotspot:overlay_onupdate()
    -- no automatic trigger; opens on click only
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
