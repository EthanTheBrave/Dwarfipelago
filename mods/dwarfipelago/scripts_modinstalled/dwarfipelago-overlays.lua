--@ module = true
-- Dwarfipelago screen-scrape overlays, kept separate from the panel UI.
--
-- DF doesn't expose the workshop task list, the work-orders job list, or the Build
-- menu as data, so these overlays read the rendered screen (confirmed readable, not
-- TrueType, on this build) and repaint locked entries. Two widgets, registered as
-- "dwarfipelago-overlays.permits" and "dwarfipelago-overlays.buildmenu":
--   * PermitOverlay   - reds out "Make ..." tasks that need a Crafting Permit
--   * BuildMenuOverlay - reds out workshops/furnaces you lack the blueprint for
-- Both are enabled/disabled by dwarfipelago.lua's start()/stop().

local overlay = require('plugins.overlay')
local to_pen  = dfhack.pen.parse

-- ── Shared keyword matching ───────────────────────────────────────────────────

-- Flatten a {value -> {keywords}} map into {keyword, value} pairs, longest keyword
-- first so a phrase ("training spear") is matched before a single word it contains
-- ("spear"), with no hand-ordering.
local function build_matchers(keyword_map)
    local matchers = {}
    for value, keywords in pairs(keyword_map) do
        for _, keyword in ipairs(keywords) do
            matchers[#matchers + 1] = { keyword = keyword, value = value }
        end
    end
    table.sort(matchers, function(a, b) return #a.keyword > #b.keyword end)
    return matchers
end

-- The value of the first matcher whose keyword is in `text`, or nil. Single words
-- match on word boundaries (so "bin" never matches "binding"); phrases match as
-- plain substrings.
local function match_keyword(text, matchers)
    text = text:lower()
    for _, m in ipairs(matchers) do
        local found
        if m.keyword:find(" ", 1, true) then
            found = text:find(m.keyword, 1, true)
        else
            found = text:find("%f[%a]" .. m.keyword .. "%f[%A]")
        end
        if found then return m.value end
    end
end

-- Read one screen row back as a plain string.
local function read_screen_row(y, width)
    local chars = {}
    for x = 0, width - 1 do
        local pen = dfhack.screen.readTile(x, y)
        local ch = pen and pen.ch
        chars[x + 1] = (ch and ch >= 32 and ch < 127) and string.char(ch) or " "
    end
    return table.concat(chars)
end

local LOCKED_ITEM_PEN = to_pen{ fg = COLOR_RED, bg = COLOR_BLACK, bold = true }
local LOCKED_NOTE_PEN = to_pen{ fg = COLOR_RED, bg = COLOR_BLACK }
local RESCAN_FRAMES   = 2    -- frames between screen re-reads; lower = snappier, costs
                             -- a full-screen scan more often (only on menu screens)

-- ── Crafting-permit overlay ───────────────────────────────────────────────────
-- With Crafting Permits on, the workshop task list (and the work-orders job list)
-- still shows crafts you lack the permit for as if they were makeable (the mod just
-- cancels the job if you queue one). This marks those rows as locked in DF's own
-- "unavailable" style - red text plus a "[Requires <Permit>]" note - the way DF
-- renders a truly unmakeable craft like "[Requires Window]".

-- Permit flag -> the word(s) DF shows for that craft. A "Make ..." row needs that
-- permit if it contains one of these. Most display names equal the permit name;
-- only the mismatches need spelling out (chest/coffer = Container, casket = Burial
-- Container, goblet = Liquid Container, coke = Coke Bars). The flag is the permit
-- item name lowercased with spaces turned into underscores (see items.lua).
local PERMIT_KEYWORDS = {
    -- furniture
    beds = {"bed"}, chair = {"chair", "throne"}, table = {"table"}, cabinet = {"cabinet"},
    container = {"chest", "coffer"}, burial_container = {"casket", "coffin", "sarcophagus"},
    bin = {"bin"}, barrel = {"barrel"}, bucket = {"bucket"}, bookcase = {"bookcase"},
    cage = {"cage"}, statue = {"statue"}, slab = {"slab"}, pedestal = {"pedestal"},
    door = {"door", "Portal", "portal"}, floodgate = {"floodgate"}, grate = {"grate"}, hatch_cover = {"hatch cover"},
    altar = {"altar"}, armor_stand = {"armor stand"}, weapon_rack = {"weapon rack"},
    -- tools, mechanisms, misc
    mechanism = {"mechanisms"}, minecart = {"minecart"}, wheelbarrow = {"wheelbarrow"},
    stepladder = {"stepladder"}, corkscrew = {"corkscrew"}, pipe_section = {"pipe section"},
    millstone = {"millstone"}, quern = {"quern"}, splint = {"splint"}, crutch = {"crutch"},
    traction_bench = {"traction bench"}, animal_trap = {"animal trap"},
    -- weapons, armor, traps
    blocks = {"blocks", "block", "bricks"}, spike = {"spike"}, ball = {"ball"},
    buckler = {"buckler"}, shield = {"shield"}, helm = {"helm"}, gauntlets = {"gauntlets"},
    mace = {"mace"}, spear = {"spear"}, pick = {"pick"}, anvil = {"anvil"},
    battle_axe = {"battle axe"}, short_sword = {"short sword"}, war_hammer = {"war hammer"},
    crossbow = {"crossbow"}, bolt = {"bolt", "bolts"},
    training_axe = {"training axe"}, training_spear = {"training spear"}, training_sword = {"training sword"},
    ballista_parts = {"ballista parts"}, ballista_arrows = {"ballista arrow"}, catapult_parts = {"catapult parts"},
    lower_body_armor = {"leggings", "greaves"}, upper_body_armor = {"leather armor", "breastplate"},
    -- materials, industry, food
    metal_bars = {"bars", "ore", "metal object", "wafers"}, coke_bars = {"coke"}, charcoal = {"charcoal"}, ash = {"ash"},
    pearlash = {"pearlash"}, quicklime = {"quicklime"}, gypsum_plaster = {"gypsum plaster", "plaster powder"},
    glass = {"raw clear glass", "raw crystal glass", "raw green glass" }, window = {"window"}, jug = {"jug"}, large_pot = {"pot"}, hive = {"hive"},
    liquid_container = {"flasks", "vials", "waterskins"}, cup = {"cup", "mugs", "goblets"}, toy = {"toy"}, totem = {"totem"}, crafts = {"crafts"},
    book_binding = {"book binding"}, scroll_roller = {"scroll roller"},
    leather = {"hide"}, cloth = {"into cloth", "into silk", "metal cloth"}, sheet = {"sheet", "parchment",}, dye = {"dye"}, bag = {"bag"},
    ["rope/chain"] = {"rope", "chain"}, soap = {"soap"}, coins = {"coins"},
    alcohol = {"drink from fruit", "drink from plant", "mead"}, lye = {"lye"}, potash = {"potash"}, tallow = {"fat"},
    oil = {"oil"}, honey = {"honey"}, prepared_meal = {"meal"}, milk_of_lime = {"milk of lime"},
    -- cloths
    lower_body_clothing = {"loincloth", "thong", "braies", "trousers", "skirt", ""},
    headgear_clothing = {"face veil", "mask", "headscarf", "head veil", "turban", "cap", "hood"},
    upper_body_clothing = {"tunic", "shirt", "dress", "vest", "toga", "coat", "robe", "mail shirt", "cape", "cloak"},
    hand_clothing = {"gloves", "mittens"},
    footwear = {"socks", "chausses", "shoes", "boots"},

}
local PERMIT_MATCHERS = build_matchers(PERMIT_KEYWORDS)
local function permit_required_by(craft_name)
    return match_keyword(craft_name, PERMIT_MATCHERS)
end

-- "armor_stand" -> "Armor Stand", for the note text.
local function permit_label(flag)
    return (flag:gsub("_", " "):gsub("(%a)(%w*)", function(first, rest) return first:upper() .. rest end))
end

local function permits_enabled()
    return (dfhack.persistent.getWorldDataString("dwarfipelago/crafting_permits") or "0") ~= "0"
end
local function permit_received(flag)
    return dfhack.persistent.getWorldDataString("dwarfipelago/craftlock/" .. flag) == "1"
end

local TASK_NAME_WIDTH = 44  -- craft names fit well within this

-- Read only a fixed window starting at "Make", so text far to the right sharing
-- the same screen row (the squad panel on a workshop, or the map "Elevation N"
-- readout on the work-orders screen) is never pulled into the craft name.
function text_override(row, y, start_text, end_pos)
    local craft = row:sub(start_text, start_text + TASK_NAME_WIDTH):gsub("%s+$", "")
    if craft:find("Requires") then return end
    local flag = permit_required_by(craft:sub(end_pos))      -- drop the prefix
    if flag and not permit_received(flag) then
        return { y = y, col = start_text - 1, text = craft, flag = flag }
    end
end

-- If a screen row is a permit-locked "Make ..." task, return where/what to mark;
-- otherwise nil. (DF's own "[Requires ...]" rows are left alone.)
local function locked_task_on_row(row, y)
    local make_at = row:find("Make %S")
    local forge_at = row:find("Forge %S")
    local tan_at = row:find("Tan a %S")
    local brew_at = row:find("Brew %S")
    local assemble_at = row:find("Assemble %S")
    local smelt_at = row:find("Smelt %S")
    local melt_at = row:find("Melt %S")
    local prepare_at = row:find("Prepare %S")
    local render_at = row:find("Render %S")
    local press_at = row:find("Press %S")
    local weave_at = row:find("Weave %S")




    if not make_at then
        if not forge_at then
            if not tan_at then
                if not brew_at then
                    if not assemble_at then
                        if not smelt_at then
                            if not melt_at then
                                if not prepare_at then
                                    if not render_at then
                                        if not press_at then
                                            if not weave_at then
                                                return
                                            else -- Weave
                                                return text_override(row, y, weave_at, 7)
                                            end
                                        else -- Press
                                            return text_override(row, y, press_at, 7)
                                        end
                                    else -- Render
                                        return text_override(row, y, render_at, 8)
                                    end
                                else -- Prepare
                                    return text_override(row, y, prepare_at, 9)
                                end
                            else -- Melt
                                 return text_override(row, y, melt_at, 6)
                            end
                        else -- Smelt
                            return text_override(row, y, smelt_at, 7)
                        end
                    else -- Assemble
                        return text_override(row, y, assemble_at, 10)
                    end
                else -- Brew
                    return text_override(row, y, brew_at, 6)
                end
            else -- Tan a
                return text_override(row, y, tan_at, 7)
            end
        else -- Forge
            return text_override(row, y, forge_at, 7)
        end
    end
    return text_override(row, y, make_at, 6)
end



PermitOverlay = defclass(PermitOverlay, overlay.OverlayWidget)
PermitOverlay.ATTRS{
    desc            = "Dwarfipelago: marks workshop tasks that need a Crafting Permit as locked",
    default_pos     = {x = 1, y = 1},
    default_enabled = true,
    viewscreens     = {
        'dwarfmode/ViewSheets/BUILDING/Workshop',  -- a workshop's Tasks tab
        'dwarfmode/Info/WORK_ORDERS/Create',       -- the create-work-order job picker
    },
    frame           = {w = 1, h = 1},
}

function PermitOverlay:init()
    self.locked_rows = {}
    self.frames_since_scan = RESCAN_FRAMES
end

-- Re-read the screen and remember which rows are permit-locked.
function PermitOverlay:scan()
    local width, height = dfhack.screen.getWindowSize()
    local rows = {}
    for y = 0, height - 1 do
        local locked = locked_task_on_row(read_screen_row(y, width), y)
        if locked then rows[#rows + 1] = locked end
    end
    self.locked_rows = rows
end

function PermitOverlay:onRenderBody(dc)
    if not permits_enabled() then
        self.locked_rows = {}
        return
    end
    self.frames_since_scan = self.frames_since_scan + 1
    if self.frames_since_scan >= RESCAN_FRAMES then
        self.frames_since_scan = 0
        self:scan()
    end
    for _, row in ipairs(self.locked_rows) do
        dfhack.screen.paintString(LOCKED_ITEM_PEN, row.col, row.y, row.text)
        dfhack.screen.paintString(LOCKED_NOTE_PEN, row.col + 1, row.y + 1,
            "[Requires " .. permit_label(row.flag) .. " Permit]")
    end
end

-- ── Build-menu blueprint overlay ──────────────────────────────────────────────
-- On the Build menu (b -> Workshops / Furnaces / ...), recolor workshop & furnace
-- entries whose blueprint you haven't received in red, so it's clear at a glance
-- what you can actually build. The menu list isn't exposed as data
-- (main_interface.building has no choices vector), but the labels are readable.
-- Categories (cyan) are left alone; only recognized building labels get touched.

-- Blueprint name (the "dwarfipelago/blueprint/<name>" key) -> the word(s) the Build
-- menu shows for it. Mismatches with the menu label are the norm (Metalsmith =
-- Forge, Crafts = Craftsdwarf's, Stoneworker = Mason). "magma forge"/"magma smelter"
-- must beat "forge"/"smelter"; build_matchers' longest-first sort handles that. Note
-- "leather works" (not bare "leather") so it doesn't catch the "Clothing and
-- leather" category.
local BLUEPRINT_KEYWORDS = {
    -- Workshops
    ["Carpenter's Workshop Blueprint"]   = {"carpenter"},
    ["Stoneworker's Workshop Blueprint"] = {"stoneworker", "mason"},
    ["Craftsdwarf's Workshop Blueprint"] = {"craftsdwarf", "crafts"},
    ["Forge Blueprint"]                  = {"metalsmith"},
    ["Magma Forge Blueprint"]            = {"magma forge"},
    ["Jeweler's Workshop Blueprint"]     = {"jeweler"},
    ["Mechanic's Workshop Blueprint"]    = {"mechanic"},
    ["Ashery Blueprint"]                 = {"ashery"},
    ["Bowyer's Workshop Blueprint"]      = {"bowyer"},
    ["Siege Workshop Blueprint"]         = {"siege"},
    ["Screw Press Blueprint"]            = {"screw press"},
    ["Soap Maker's Workshop Blueprint"]  = {"soap"},
    -- Clothing and leather
    ["Clothier's Shop Blueprint"]        = {"clothier"},
    ["Leather Works Blueprint"]          = {"leather"},
    ["Tanner's Blueprint"]               = {"tanner"},
    ["Dyer's Workshop Blueprint"]        = {"dyer"},
    ["Loom Blueprint"]                   = {"loom"},
    -- Farming
    ["Farmer's Workshop Blueprint"]      = {"farmer"},
    ["Still Blueprint"]                  = {"still"},
    ["Kitchen Blueprint"]                = {"kitchen"},
    ["Fishery Blueprint"]                = {"fishery"},
    ["Butcher's Shop Blueprint"]         = {"butcher"},
    -- Furnaces
    ["Smelter Blueprint"]                = {"smelter"},
    ["Magma Smelter Blueprint"]          = {"magma smelter"},
    ["Wood Furnace Blueprint"]           = {"wood furnace"},
    ["Glass Furnace Blueprint"]          = {"glass furnace"},
    ["Kiln Blueprint"]                   = {"kiln"},
    ["Magma Kiln Blueprint"]             = {"magma kiln"},
    ["Magma Glass Furnace Blueprint"]    = {"magma glass furnace"},
    -- Farm plot
    ["Farm Plot Blueprint"]              = {"farm plot"},
}
local BLUEPRINT_MATCHERS = build_matchers(BLUEPRINT_KEYWORDS)

local function blueprint_received(name)
    return dfhack.persistent.getWorldDataString("dwarfipelago/blueprint/" .. name) == "1"
end

-- Split a screen row into menu cells - text runs separated by 2+ spaces - each with
-- its 0-based start column. Cells are isolated, so the Build menu's several columns
-- (and the status bar above it) are handled without special-casing.
local function row_cells(row)
    local cells, pos = {}, 1
    while true do
        local start = row:find("%S", pos)
        if not start then break end
        local gap  = row:find("%s%s", start)
        local stop = gap and gap - 1 or #row
        cells[#cells + 1] = { col = start - 1, text = row:sub(start, stop) }
        if not gap then break end
        pos = gap + 1
    end
    return cells
end

BuildMenuOverlay = defclass(BuildMenuOverlay, overlay.OverlayWidget)
BuildMenuOverlay.ATTRS{
    desc            = "Dwarfipelago: reds out Build-menu workshops/furnaces you lack the blueprint for",
    default_pos     = {x = 1, y = 1},
    default_enabled = true,
    viewscreens     = {'dwarfmode/Building'},
    frame           = {w = 1, h = 1},
}

function BuildMenuOverlay:init()
    self.locked_cells = {}
    self.frames_since_scan = RESCAN_FRAMES
end

-- Re-read the Build menu and remember which building cells are blueprint-locked.
function BuildMenuOverlay:scan()
    local width, height = dfhack.screen.getWindowSize()
    local found = {}
    for y = 0, height - 1 do
        for _, cell in ipairs(row_cells(read_screen_row(y, width))) do
            local blueprint = match_keyword(cell.text, BLUEPRINT_MATCHERS)
            if blueprint and not blueprint_received(blueprint) then
                found[#found + 1] = { y = y, col = cell.col, text = cell.text }
            end
        end
    end
    self.locked_cells = found
end

function BuildMenuOverlay:onRenderBody(dc)
    self.frames_since_scan = self.frames_since_scan + 1
    if self.frames_since_scan >= RESCAN_FRAMES then
        self.frames_since_scan = 0
        self:scan()
    end
    for _, cell in ipairs(self.locked_cells) do
        dfhack.screen.paintString(LOCKED_ITEM_PEN, cell.col, cell.y, cell.text)
    end
end

-- Auto-discovery table - DFHack registers these when the script is loaded.
-- Widget names: "dwarfipelago-overlays.permits", "dwarfipelago-overlays.buildmenu".
OVERLAY_WIDGETS = {
    permits   = PermitOverlay,
    buildmenu = BuildMenuOverlay,
}
