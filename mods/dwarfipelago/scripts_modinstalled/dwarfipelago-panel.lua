--@ module = true
-- Dwarfipelago status and control panel.
-- Can be opened three ways:
--   1. Click the [AP] hotspot button in the corner of the fortress screen.
--   2. Run: dwarfipelago panel
--   3. Run directly: dwarfipelago-panel

local gui     = require('gui')
local overlay = require('plugins.overlay')
local widgets = require('gui.widgets')
local state   = reqscript('internal/dwarfipelago/state')
local items   = reqscript('internal/dwarfipelago/items')

-- ── Helpers ───────────────────────────────────────────────────────────────────

local function ps(key, default)
    return dfhack.persistent.getWorldDataString("dwarfipelago/" .. key) or default
end

local GOAL_NAMES = {
    ["0"] = "Slay Megabeast",
    ["1"] = "Legendary Wealth",
    ["2"] = "Population Boom",
    ["3"] = "Mountainhome",
}

local function yn(val, yes_color, no_color)
    if val then
        return {text="YES", pen=yes_color or COLOR_GREEN}
    else
        return {text="no",  pen=no_color  or COLOR_DARKGRAY}
    end
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
    local W, H = 44, 22

    -- Build Unlocks tab subviews dynamically from UNLOCK_DEFS so new unlocks
    -- added to items.lua show up here automatically.
    local unlock_subviews = { widgets.Label{frame={t=0, l=0}, text="Progression unlocks:"} }
    for i, def in ipairs(items.UNLOCK_DEFS) do
        local raw  = ps("unlock/" .. def.key, "0")
        local text = {def.label .. ": "}
        if def.max then
            table.insert(text, raw)
            table.insert(text, "/" .. def.max)
        else
            table.insert(text, yn(raw == "1"))
        end
        table.insert(unlock_subviews, widgets.Label{frame={t=i+1, l=2}, text=text})
    end

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
                        text  = {"Complete: ", yn(complete)},
                    },
                    widgets.Label{
                        frame = {t=3, l=0},
                        text  = {
                            "Depot:    ",
                            {text=depot and "built" or "pending",
                             pen=depot and COLOR_GREEN or COLOR_YELLOW},
                        },
                    },
                },
            },
            -- ── Tab 2: Unlocks (generated from items.UNLOCK_DEFS) ────────────
            widgets.Panel{ subviews = unlock_subviews },
            -- ── Tab 3: Controls ──────────────────────────────────────────────
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
        },
    }

    self:addviews{
        widgets.Window{
            frame_title = ("Dwarfipelago v%s"):format(version),
            frame       = {w=W, h=H, t=3, l=3},
            resizable   = true,
            resize_min  = {w=44, h=18},
            subviews    = {
                widgets.TabBar{
                    frame        = {t=0, l=0},
                    labels       = {"Status", "Unlocks", "Controls"},
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
