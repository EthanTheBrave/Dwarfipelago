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

DwarfipelagoPanel = defclass(DwarfipelagoPanel, gui.ZScreen)
DwarfipelagoPanel.ATTRS{
    focus_path = "dwarfipelago/panel",
}

function DwarfipelagoPanel:init()
    local enabled  = state.is_enabled()
    local version  = ps("version",       "?")
    local goal_key = ps("goal",          "-1")
    local complete = ps("goal_complete", "0") == "1"
    local depot    = ps("depot_built",   "0") == "1"

    local coffers  = ps("unlock/wealth_coffers",     "0")
    local waves    = ps("unlock/immigration_waves",   "0")
    local military = ps("unlock/military_training",   "0")
    local baron    = ps("unlock/baron_charter",       "0") == "1"
    local count_c  = ps("unlock/count_charter",       "0") == "1"
    local duke     = ps("unlock/duke_charter",        "0") == "1"
    local monarch  = ps("unlock/monarch_invitation",  "0") == "1"
    local codex    = ps("unlock/master_builders_codex","0") == "1"
    local art_wpn  = ps("unlock/artifact_weapon",     "0") == "1"
    local art_arm  = ps("unlock/artifact_armor",      "0") == "1"

    local goal_str = GOAL_NAMES[goal_key] or "Not synced"
    local W, H = 44, 32

    self:addviews{
        widgets.Window{
            frame_title = ("Dwarfipelago v%s"):format(version),
            frame       = {w=W, h=H, t=3, l=3},
            resizable   = false,
            subviews    = {
                -- ── Status ──────────────────────────────────────────────────
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

                widgets.Label{frame={t=4, l=0}, text=string.rep("-", W-4)},

                -- ── Progression unlocks ─────────────────────────────────────
                widgets.Label{frame={t=5,  l=0}, text="Progression unlocks:"},
                widgets.Label{frame={t=6,  l=2}, text={"Merchant's Coffers:   ", coffers, "/5"}},
                widgets.Label{frame={t=7,  l=2}, text={"Immigration Waves:    ", waves,   "/5"}},
                widgets.Label{frame={t=8,  l=2}, text={"Military Training:    ", military,"/4"}},
                widgets.Label{frame={t=9,  l=2}, text={"Baron's Charter:      ", yn(baron)}},
                widgets.Label{frame={t=10, l=2}, text={"Count's Charter:      ", yn(count_c)}},
                widgets.Label{frame={t=11, l=2}, text={"Duke's Charter:       ", yn(duke)}},
                widgets.Label{frame={t=12, l=2}, text={"Monarch's Invitation: ", yn(monarch)}},
                widgets.Label{frame={t=13, l=2}, text={"Master Builder's Codex:", yn(codex)}},
                widgets.Label{frame={t=14, l=2}, text={"Artifact Weapon:      ", yn(art_wpn)}},
                widgets.Label{frame={t=15, l=2}, text={"Artifact Armor:       ", yn(art_arm)}},

                widgets.Label{frame={t=16, l=0}, text=string.rep("-", W-4)},

                -- ── Controls ────────────────────────────────────────────────
                widgets.Label{frame={t=17, l=0}, text="Controls:"},
                widgets.HotkeyLabel{
                    frame = {t=18, l=2},
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
                    frame = {t=19, l=2},
                    key   = "CUSTOM_SHIFT_R",
                    label = "Reset all AP state",
                    on_activate = function()
                        dfhack.run_command("dwarfipelago", "reset")
                        self:dismiss()
                    end,
                },

                widgets.Label{frame={t=21, l=0}, text=string.rep("-", W-4)},

                widgets.HotkeyLabel{
                    frame = {t=22, l=2},
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
    default_pos     = {x=8, y=2},
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
    DwarfipelagoPanel{}:show()
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
