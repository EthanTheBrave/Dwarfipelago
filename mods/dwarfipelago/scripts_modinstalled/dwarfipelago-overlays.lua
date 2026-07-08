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
local UNLOCKED_NOTE_PEN = to_pen{ fg = COLOR_WHITE, bg = COLOR_BLACK }
local COMPLETED_NOTE_PEN = to_pen{ fg = COLOR_GREEN, bg = COLOR_BLACK }

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
    container = {"chest", "coffer", "box"}, burial_container = {"casket", "coffin", "sarcophagus"},
    bin = {"bin"}, barrel = {"barrel"}, bucket = {"bucket"}, bookcase = {"bookcase"},
    cage = {"cage", "terrarium"}, statue = {"statue"}, slab = {"slab"}, pedestal = {"pedestal"},
    door = {"door", "Portal", "portal"}, floodgate = {"floodgate"}, grate = {"grate"}, hatch_cover = {"hatch cover"},
    altar = {"altar"}, armor_stand = {"armor stand"}, weapon_rack = {"weapon rack"}, display_case = {"display case"},
    -- tools, mechanisms, misc
    mechanism = {"mechanisms"}, minecart = {"minecart"}, wheelbarrow = {"wheelbarrow"},
    stepladder = {"stepladder"}, corkscrew = {"corkscrew"}, pipe_section = {"pipe section", "tube"},
    millstone = {"millstone"}, quern = {"quern"}, splint = {"splint"}, crutch = {"crutch"},
    traction_bench = {"traction bench"}, animal_trap = {"animal trap"},
    -- weapons, traps
    blocks = {"blocks", "block", "bricks"}, menacing_spike = {"spike"}, spiked_ball = {"ball"},
    mace = {"mace"}, spear = {"spear"}, pick = {"pick"}, anvil = {"anvil"},
    battle_axe = {"battle axe"}, short_sword = {"short sword"}, war_hammer = {"war hammer"},
    crossbow = {"crossbow"}, bolt_thrower_parts = {"bolt thrower parts"}, bolt = {"bolts"},
    training_axe = {"training axe"}, training_spear = {"training spear"}, training_sword = {"training sword"},
    ballista_parts = {"ballista parts"}, ballista_arrows = {"ballista arrow"}, catapult_parts = {"catapult parts"},
    giant_axe_blade = {"axe blade"}, serrated_disc = {"disc"},
    -- materials, industry, food
    metal_bars = {"bars", "ore", "metal object", "wafers"}, coke_bars = {"coke"}, charcoal = {"charcoal"}, ash = {"ash"},
    pearlash = {"pearlash"}, quicklime = {"quicklime"}, gypsum_plaster = {"gypsum plaster", "plaster powder"},
    glass = {"raw clear glass", "raw crystal glass", "raw green glass" }, window = {"window"}, jug = {"jug"}, large_pot = {"pot"}, hive = {"hive"},
    liquid_container = {"flasks", "vials", "waterskins"}, cup = {"cups", "mugs", "goblets"}, toy = {"toy"}, totem = {"totem"}, crafts = {"crafts"},
    book_binding = {"book binding"}, scroll_roller = {"scroll roller"},
    leather = {"hide"}, cloth = {"into cloth", "into silk", "metal cloth"}, sheet = {"sheet", "parchment",}, dye = {"dye"}, bag = {"bag"},
    ["rope/chain"] = {"rope", "chain"}, soap = {"soap"}, coins = {"coins"},
    alcohol = {"drink from fruit", "drink from plant", "mead"}, lye = {"lye"}, potash = {"potash"}, tallow = {"fat"},
    oil = {"oil"}, honey = {"honey"}, prepared_meal = {"meal"}, milk_of_lime = {"milk of lime"}, amulet = {"amulet"}, bracelet = {"bracelet"},
    crown = {"crown"}, die = {"die"}, earring = {"earring"}, figurine = {"figurine"}, nest_box = {"nest box"}, ring = {" ring"},
    scepter = {"scepter"}, quire = {"quire"}, scroll = {"scroll"}, codex = {"book"},
    -- cloths
    greaves = {"greaves"}, buckler = {"buckler"}, shield = {"shield"}, helm = {"helm"}, gauntlets = {"gauntlets"},
    leather_armor = {"leather armor"}, breastplate = {"breastplate"},
    mail_shirt = {"mail shirt"}, socks = {"socks"}, backpack = {"backpack"}, quiver = {"quiver"},
    face_veil = {"face_viel"}, mask = {"mask"}, headscarf = {"headscarf"}, head_veil = {"head veil"}, turban = {"turban"},
    cap = {"cap"}, hood = {"hood"}, leggings = {"leggings"}, loincloth = {"loincloth"}, thong = {"thong"},
    braies = {"braies"}, trousers = {"trousers"}, skirt = {"skirt"}, gloves = {"gloves"}, mittens = {"mittens"},
    tunic = {"tunic"}, shirt = {"cloth shirt", "yarn shirt"}, dress = {"dress"}, vest = {"vest"}, toga = {"toga"}, coat = {"coat"},
    robe = {"robe"}, cape = {"cape"}, cloak = {"cloak"}, chausses = {"chausses"}, shoes = {"shoes"}, low_boots = {"low boots"},
    high_boots = {"high boots"}
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

-- DF verb prefixes for workshop/furnace tasks.
-- `skip` = chars to drop to reach the item name (verb + space, 1-based).
-- Read only a fixed window starting at the verb, so text far to the right sharing
-- the same screen row (the squad panel on a workshop, or the map "Elevation N"
-- readout on the work-orders screen) is never pulled into the craft name.
local TASK_VERBS = {
    { pattern = "Make %S",     skip = 6  },
    { pattern = "Forge %S",    skip = 7  },
    { pattern = "Tan a %S",    skip = 7  },
    { pattern = "Brew %S",     skip = 6  },
    { pattern = "Assemble %S", skip = 10 },
    { pattern = "Smelt %S",    skip = 7  },
    { pattern = "Melt %S",     skip = 6  },
    { pattern = "Prepare %S",  skip = 9  },
    { pattern = "Render %S",   skip = 8  },
    { pattern = "Press %S",    skip = 7  },
    { pattern = "Weave %S",    skip = 7  },
    { pattern = "Bind %S",    skip = 6  },
    { pattern = "Mint %S",    skip = 6  },
}

-- If a screen row is a permit-locked task, return where/what to mark; otherwise nil.
-- (DF's own "[Requires ...]" rows are left alone.)
local function locked_task_on_row(row, y)
    for _, verb in ipairs(TASK_VERBS) do
        local pos = row:find(verb.pattern)
        if pos then
            local craft = row:sub(pos, pos + TASK_NAME_WIDTH):gsub("%s+$", "")
            if craft:find("Requires") then return end
            local flag = permit_required_by(craft:sub(verb.skip))
            if flag and not permit_received(flag) then
                return { y = y, col = pos - 1, text = craft, flag = flag }
            end
            return  -- verb matched but task isn't permit-locked; no need to check further
        end
    end
end



PermitOverlay = defclass(PermitOverlay, overlay.OverlayWidget)
PermitOverlay.ATTRS{
    desc            = "Dwarfipelago: marks workshop tasks that need a Crafting Permit as locked",
    default_pos     = {x = 1, y = 1},
    default_enabled = true,
    viewscreens     = {
        'dwarfmode/ViewSheets/BUILDING/Workshop',  -- a workshop's Tasks tab
        'dwarfmode/ViewSheets/BUILDING/Furnace',   -- furnaces (smelter, kiln, glass furnace, etc.)
        'dwarfmode/Info/WORK_ORDERS/Create',       -- the create-work-order job picker
        'dwarfmode/ViewSheets/BUILDING/Furnace',
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
    local width = dfhack.screen.getWindowSize()
    for _, row in ipairs(self.locked_rows) do
        dfhack.screen.paintString(LOCKED_ITEM_PEN, row.col, row.y, row.text)
        -- Skip our note if DF already has a [Requires ...] on the row below.
        if not read_screen_row(row.y + 1, width):find("[Requires", 1, true) then
            dfhack.screen.paintString(LOCKED_NOTE_PEN, row.col + 1, row.y + 1,
                "[Requires " .. permit_label(row.flag) .. " Permit]")
        end
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
    ["Clothier's Shop Blueprint"]        = {"clothes", "clothier"},
    ["Leather Works Blueprint"]          = {"leather", "leatherworks", "leather works"},
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
            -- Skip category-header cells (e.g. "Clothing and leather", "Machines/fluids")
            -- so bare keywords like "leather" don't false-positive on them.
            if not cell.text:find(" and ", 1, true) and not cell.text:find("/", 1, true) then
                local blueprint = match_keyword(cell.text, BLUEPRINT_MATCHERS)
                if blueprint and not blueprint_received(blueprint) then
                    found[#found + 1] = { y = y, col = cell.col, text = cell.text }
                end
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


CraftsanityOverlay = defclass(CraftsanityOverlay, overlay.OverlayWidget)
CraftsanityOverlay.ATTRS{
    desc            = "Dwarfipelago: marks workshop tasks that still requires X amount of Crafting",
    default_pos     = {x = 1, y = 1},
    default_enabled = true,
    viewscreens     = {
        'dwarfmode/ViewSheets/BUILDING/Workshop',  -- a workshop's Tasks tab
        'dwarfmode/ViewSheets/BUILDING/Furnace',   -- furnaces (smelter, kiln, glass furnace, etc.)
        'dwarfmode/Info/WORK_ORDERS/Create',       -- the create-work-order job picker
    },
    frame           = {w = 1, h = 1},
}

function CraftsanityOverlay:init()
    self.locked_rows = {}
    self.task_rows = {}
    self.frames_since_scan = RESCAN_FRAMES
end

local TASK_LINE = {
    "Make .*%S",
    "Forge .*%S",
    "Tan a .*%S",
    "Brew .*%S",
    "Assemble .*%S",
    "Smelt .*%S",
    "Melt .*%S",
    "Prepare .*%S",
    "Render .*%S",
    "Press .*%S",
    "Bind .*%S",
    "Mint .*%S",
}

local MATERIAL_KEYWORDS = {
    wood = {"wooden"}, stone = {"rock"}, bone = {"bone", "ivory/tooth", "horn"},
    ceramic = {"clay"}, metal = {"aluminum", "billon", "metal", "brass",
    "bronze", "copper", "electrum", "elemental", "steel", "pewter", "gold", "iron",
    "lead", "nickel", "platinum", "silver", "tin", "zinc"}, 
    glass = {"glass"}, leather = {"leather"}, cloth = {" cloth", "yarn"},
    adamantine = {"adamantine"}
}

local function material_required_by(craft_name)
    for material, material_table in pairs(MATERIAL_KEYWORDS)
    do
        for _, keyword in pairs(material_table)
        do
            if string.find(craft_name, keyword) then
                return material
            end
        end
    end
end

local CRAFTSANITY_KEYWORDS = {
    beds = {"bed"}, corkscrew = {"corkscrew"}, blocks = {"blocks", "bricks"}, menacing_spike = {"spike"},
    spiked_ball = {"ball"}, altar = {"altar"}, animal_trap = {"animal trap"}, armor_stand = {"armor stand"}, barrel = {"barrel"},
    bin = {"bin"}, bookcase = {"bookcase"}, bucket = {"bucket"}, buckler = {"buckler"}, cabinet = {"cabinet"},
    cage = {"cage", "terrarium"}, burial_container = {"casket", "sarcophagus", "coffin"}, chair = {"chair", "throne"}, container = {"chest", "coffer", "box"}, crutch = {"crutch"},
    door = {"door", "portal", "Portal"}, floodgate = {"floodgate"}, grate = {"grate"}, hatch_cover = {"hatch cover"},
    minecart = {"minecart"}, pedestal = {"pedestal"}, pipe_section = {"pipe section", "tube"}, shield = {"shield"},
    splint = {"splint"}, stepladder = {"stepladder"}, table = {"table"}, training_axe = {"training axe"},
    training_spear = {"training spear"}, training_sword = {"training sword"}, weapon_rack = {"weapon rack"},
    wheelbarrow = {"wheelbarrow"}, crossbow = {"crossbow"}, bolt_thrower_parts = {"bolt thrower parts"}, bolt = {"bolts"}, millstone = {"millstone"},
    quern = {"quern"}, slab = {"slab"}, statue = {"statue"}, mechanism = {"mechanism", "mechanisms"}, 
    traction_bench = {"traction bench"}, crafts = {"crafts"}, liquid_container = {"flasks", "vials", "waterskins"},
    goblet = {"goblet", "goblets"}, mug = {"mugs"}, cup = {"cups"}, toy = {"toy"}, totem = {"totem"}, gauntlets = {"gauntlets"},
    helm = {"helm"}, ballista_parts = {"ballista parts"}, catapult_parts = {"catapult parts"}, ballista_arrows = {"ballista arrow"},
    ash = {"ash"}, charcoal = {"charcoal"}, metal_bars = {"bars", "ore", "metal object", "wafers"}, coke_bars = {"coke"},
    pearlash = {"pearlash"}, gypsum_plaster = {"plaster powder"}, jug = {"jug"}, large_pot = {"pot"},  hive = {"hive"},
    quicklime = {"quicklime"}, glass = {"raw green glass", "raw clear glass", "raw crystal glass"}, window = {"window"}, book_binding = {"book binding"},
    scroll_roller = {"scroll rollers"}, leather = {"hide"}, sheet = {"sheet", "parchment"}, cloth = {"into cloth"}, alcohol = {"Brew drink", "mead"},
    lye = {"lye"}, potash = {"potash"}, milk_of_lime = {"milk of lime"}, prepared_meal = {"meal"},
    tallow = {"tallow"}, oil = {"oil"}, press_cake = {"press_cake"}, honey = {"honey"}, bee_wax = {"bee wax"},
    dye = {"dye"}, bag = {"bag"}, rope_chain = {"rope", "chain"}, battle_axe = {"battle axe"},
    mace = {"mace"}, pick = {"pick"}, short_sword = {"short sword"}, spear = {"spear"}, war_hammer = {"war hammer"},
    anvil = {"anvil"}, coins = {"coins"}, soap = {"soap"}, display_case = {"display case"}, amulet = {"amulet"}, bracelet = {"bracelet"},
    crown = {"crown"}, die = {"die"}, earring = {"earring"}, figurine = {"figurine"}, nest_box = {"nest box"}, ring = {" ring"},
    scepter = {"scepter"}, greaves = {"greaves"}, quire = {"quire"}, scroll = {"scroll"}, codex = {"book"},
    leather_armor = {"leather armor"}, breastplate = {"breastplate"}, mail_shirt = {"mail shirt"}, socks = {"socks"},
    backpack = {"backpack"}, quiver = {"quiver"}, face_veil = {"face_viel"}, mask = {"mask"}, headscarf = {"headscarf"},
    head_veil = {"head veil"}, turban = {"turban"}, cap = {"cap"}, hood = {"hood"}, leggings = {"leggings"}, loincloth = {"loincloth"}, thong = {"thong"},
    braies = {"braies"}, trousers = {"trousers"}, skirt = {"skirt"}, gloves = {"gloves"}, mittens = {"mittens"},
    tunic = {"tunic"}, shirt = {"cloth shirt", "yarn shirt"}, dress = {"dress"}, vest = {"vest"}, toga = {"toga"}, coat = {"coat"},
    robe = {"robe"}, cape = {"cape"}, cloak = {"cloak"}, chausses = {"chausses"}, shoes = {"shoes"}, low_boots = {"low boots"},
    high_boots = {"high boots"}, giant_axe_blade = {"axe blade"}, serrated_disc = {"disc"},
}

local function craftsanity_required_by(craft_name)
    for craft, craft_table in pairs(CRAFTSANITY_KEYWORDS)
    do
        for _, keyword in pairs(craft_table)
        do
            if string.find(craft_name, keyword .. " ") then
                return craft
            end
        end
    end
end

local function craftsanity_enabled()
    return (dfhack.persistent.getWorldDataString("dwarfipelago/craftsanity_enabled") or "0") ~= "0"
end
local function craftsanity_materials_enabled()
    return (dfhack.persistent.getWorldDataString("dwarfipelago/craftsanity_materials") or "0") ~= "0"
end
local function craftsanity_max()
    return (dfhack.persistent.getWorldDataString("dwarfipelago/craftsanity_max") or "999")
end
local function craft_count(craft, material)
    if craft == "rope_chain" then craft = "rope/chain" end
    if material ~= "" then
        return dfhack.persistent.getWorldDataString("dwarfipelago/craft_count/" .. craft .. "_" .. material)
    else
        return dfhack.persistent.getWorldDataString("dwarfipelago/craft_count/" .. craft)
    end
end

local function task_on_row(row, y)
    for _, verb in ipairs(TASK_LINE) do
        local pos = row:find(verb)
        if pos then
            -- ".*%S" is greedy, so its end would run to the last non-space on the whole
            -- row - on the work-orders screen that is the map's "Elevation N" readout off
            -- to the right, flinging the counter out over the map. Bound the label to the
            -- first run of 2+ spaces after the verb (the panel/map gap) so the counter
            -- lands right after the craft name.
            local finish = (row:find("  ", pos) or (#row + 1)) - 1
            local material = ""
            local craft = craftsanity_required_by(row)
            if craft then 
                if craft == "beds" or craft == "ash" or craft == "charcoal" or craft == "metal_bars" or craft == "coke_bars"
                or craft == "pearlash" or craft == "gypsum_plaster" or craft == "quicklime" or craft == "glass" or craft == "leather"
                or craft == "sheet" or craft == "cloth" or craft == "alcohol" or craft == "lye" or craft == "potash" or craft == "milk_of_lime"
                or craft == "prepared_meal" or craft == "tallow" or craft == "oil" or craft == "press_cake" or craft == "honey" 
                or craft == "bee wax" or craft == "dye" or craft == "soap" or craft == "training_axe" or craft == "training_spear"
                or craft == "training_sword" or craft == "cup" or craft == "ballista_parts" or craft == "catapult_parts" or craft == "millstone"
                or craft == "quern" or craft == "slab" or craft == "mug" or craft == "totem" or craft == "window"
                or craft == "display_case" or craft == "bolt_thrower_parts" or craft == "quire" or craft == "scroll"
                or craft == "leather_armor" or craft == "codex"
                then -- these don't have other material types
                    return { y = y, start = pos, finish = finish, mat = material, craft = craft}
                end
                if craftsanity_enabled() then
                    local mat = material_required_by(row)
                    if mat then material = mat end
                end
                return { y = y, start = pos, finish = finish, mat = material, craft = craft}
            else
                return
            end
        end
    end
end


-- Re-read the screen and remember which rows needs craftsanity.
function CraftsanityOverlay:scan()
    local width, height = dfhack.screen.getWindowSize()
    local rows = {}
    local task = {}
    for y = 0, height - 1 do
        local t = task_on_row(read_screen_row(y, width), y)
        if t then task[#task + 1] = t end
    end
    self.task_rows = task
end

function CraftsanityOverlay:onRenderBody(dc)
    if not craftsanity_enabled() then
        self.task_rows = {}
        return
    end
    max = craftsanity_max()
    self.frames_since_scan = self.frames_since_scan + 1
    if self.frames_since_scan >= RESCAN_FRAMES then
        self.frames_since_scan = 0
        self:scan()
    end
    local width = dfhack.screen.getWindowSize()
    for id, row in ipairs(self.task_rows) do
        amt = craft_count(row.craft, row.mat)
        if amt and tonumber(amt) >= tonumber(max) then
            dfhack.screen.paintString(COMPLETED_NOTE_PEN, row.finish + 1, row.y, "(" .. max .. "/" .. max .. ")")
        elseif amt then
            dfhack.screen.paintString(UNLOCKED_NOTE_PEN, row.finish + 1, row.y, "(" .. amt .. "/" .. max .. ")")
        -- else
        --     dfhack.screen.paintString(UNLOCKED_NOTE_PEN, row.finish + 1, row.y, "(N/A)")
        end
    end
end

-- Auto-discovery table - DFHack registers these when the script is loaded.
-- Widget names: "dwarfipelago-overlays.permits", "dwarfipelago-overlays.buildmenu".
OVERLAY_WIDGETS = {
    permits   = PermitOverlay,
    buildmenu = BuildMenuOverlay,
    craftsanity = CraftsanityOverlay,
}
