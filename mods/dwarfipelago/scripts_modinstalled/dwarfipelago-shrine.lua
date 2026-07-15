--@ module = true
-- Shrine of Dwarfipelagius - in-world summon and Merchant Afterlife UI.

local M = {}
local gui           = require('gui')
local widgets       = require('gui.widgets')
local json          = require('json')
local overlay       = require('plugins.overlay')
local scriptmanager = require('script-manager')
local checks        = reqscript('internal/dwarfipelago/checks')

local to_pen = dfhack.pen.parse

-- -- Deity sprite --------------------------------------------------------------

local _deity_handles = nil
local _shrine_tile_handles = nil
local _shrine_icon_handle = nil

-- Loads the 32x32 single-tile icon used on the map building tile.
-- Separate from the 2x portrait used in the shrine screen panel.
local function load_shrine_map_icon()
    if _shrine_icon_handle then return end
    local mod_path = scriptmanager.getModSourcePath('dwarfipelago')
    if not mod_path then return end
    local path = mod_path .. 'graphics/images/dwarfipelagius.png'
    local ok, result = pcall(dfhack.textures.loadTileset, path, 32, 32, true)
    if ok and result and result[1] then
        _shrine_icon_handle = result[1]
    end
end

local function load_deity_sprite()
    if _deity_handles then return end
    local mod_path = scriptmanager.getModSourcePath('dwarfipelago')
    if not mod_path then return end
    -- Load from graphics/images/ where it is declared as a TILE_PAGE so DF
    -- pre-registers the texture before our script runs, guaranteeing a valid
    -- texpos at world-load time.
    local path = mod_path .. 'graphics/images/dwarfipelagius_2x.png'
    local ok, result = pcall(dfhack.textures.loadTileset, path, 32, 32, true)
    if ok and result and #result > 0 then
        _deity_handles = result
        return
    end
    -- Fallback: original location used by the shrine screen panel.
    path = mod_path .. 'scripts_modinstalled/art/dwarfipelagius_2x.png'
    ok, result = pcall(dfhack.textures.loadTileset, path, 32, 32, true)
    if ok and result and #result > 0 then
        _deity_handles = result
    end
end

-- Loads shrine_tile.png (32x64, 2 tiles: row0=pedestal, row1=deity face).
-- Returns the handle list or nil on failure.
local function load_shrine_tile()
    if _shrine_tile_handles then return _shrine_tile_handles end
    local mod_path = scriptmanager.getModSourcePath('dwarfipelago')
    if not mod_path then return nil end
    local path = mod_path .. 'graphics/images/shrine_tile.png'
    local ok, result = pcall(dfhack.textures.loadTileset, path, 32, 32, true)
    if ok and result and #result >= 2 then
        _shrine_tile_handles = result
        return result
    end
    dfhack.printerr('[shrine] load_shrine_tile failed: ' .. tostring(result))
    return nil
end

-- 2x2 tile widget that renders the deity sprite.
TileSprite = defclass(TileSprite, widgets.Widget)
TileSprite.ATTRS{ frame = {w=2, h=2} }

function TileSprite:onRenderBody(dc)
    if not _deity_handles then return end
    local idx = 1
    for row = 0, 1 do
        for col = 0, 1 do
            local texpos = dfhack.textures.getTexposByHandle(_deity_handles[idx])
            if texpos and texpos > 0 then
                dc:seek(col, row):char(219,
                    to_pen{ch=219, tile=texpos, fg=COLOR_WHITE, bg=COLOR_BLACK})
            end
            idx = idx + 1
        end
    end
end

local SHRINE_BLD_KEY = 'dwarfipelago/shrine_statue_id'

local function ps(key)
    return dfhack.persistent.getWorldDataString('dwarfipelago/' .. key) or ""
end

local function fmt_num(n)
    local s = tostring(math.floor(n or 0))
    return s:reverse():gsub("(%d%d%d)", "%1,"):reverse():gsub("^,", "")
end

-- -- In-world manifestation ----------------------------------------------------

local function find_shrine_pos()
    local result = nil
    pcall(function()
        local site = dfhack.world.getCurrentSite()
        if not site then return end
        for _, z in ipairs(df.global.world.buildings.all) do
            local ok, t = pcall(function() return z:getType() end)
            if ok and t == df.building_type.Civzone then
                local loc_id = -1
                pcall(function() loc_id = z.location_id end)
                if loc_id and loc_id >= 0 then
                    for _, bld in ipairs(site.buildings) do
                        if bld.id == loc_id
                                and df.abstract_building_templest:is_instance(bld) then
                            result = {
                                x = math.floor((z.x1 + z.x2) / 2),
                                y = math.floor((z.y1 + z.y2) / 2),
                                z = z.z,
                            }
                            return
                        end
                    end
                end
            end
        end
    end)
    return result
end

local function spawn_mist_ring(pos)
    if not pos then return end
    pcall(function()
        for dx = -2, 2 do
            for dy = -2, 2 do
                if dx * dx + dy * dy <= 5 then
                    dfhack.maps.spawnFlow(
                        {x = pos.x + dx, y = pos.y + dy, z = pos.z},
                        df.flow_type.Mist, 0, 0, 25000)
                end
            end
        end
    end)
end

local function summon_at_shrine(pos)
    spawn_mist_ring(pos)
    if pos then
        pcall(function()
            dfhack.gui.showZoomAnnouncement(
                df.announcement_type.CARAVAN_ARRIVAL,
                pos,
                "The veil grows thin. Dwarfipelagius answers from the merchant afterlife.",
                COLOR_GRAY, true)
        end)
    else
        dfhack.gui.showAnnouncement(
            "The veil grows thin. Dwarfipelagius stirs in the merchant afterlife.",
            COLOR_GRAY, true)
    end
end

local function announce_tithe(cost, item_name, pos)
    spawn_mist_ring(pos)
    dfhack.gui.showAnnouncement(
        ("You lay %s* upon the altar. The coins shimmer and are gone."):format(fmt_num(cost)),
        COLOR_DARKGRAY, false)
    dfhack.gui.showAnnouncement(
        "Dwarfipelagius receives the tithe. The wealth joins those who came before.",
        COLOR_DARKGRAY, false)
    dfhack.gui.showAnnouncement(
        ("Something stirs beyond the veil. %s is delivered from the merchant afterlife."):format(item_name),
        COLOR_GRAY, true)
end

-- -- Shrine building ----------------------------------------------------------

local function find_shrine_bld()
    local id_str = dfhack.persistent.getWorldDataString(SHRINE_BLD_KEY) or ""
    if id_str == "" then return nil end
    local id = tonumber(id_str)
    if not id then return nil end
    return df.building.find(id)
end

-- Returns the 0-based index of DWARFIPELAGO_SHRINE in world.raws.buildings.all,
-- or -1 if not present.
local function find_shrine_custom_idx()
    for i, def in ipairs(df.global.world.raws.buildings.all) do
        if def.code == "DWARFIPELAGO_SHRINE" then
            return i
        end
    end
    return -1
end

-- DF50 Itch does not load OBJECT:BUILDING from mod objects/ folders.
-- Inject a 1x1 custom workshop def at runtime.
-- dwarfipelagius.png is declared as TILE_PAGE DWARFIPELAGO_ICON so DF
-- pre-registers its texpos before this code runs.
-- graphics_normal[stage][bld_x][bld_y] renders at pos.y + bld_y - 1.
-- bld_y=0 renders one tile above; bld_y=1 renders on the building tile.
local function inject_shrine_def()
    local raws = df.global.world.raws

    -- Find existing def, or create it.
    local def = nil
    for _, d in ipairs(raws.buildings.all) do
        if d.code == 'DWARFIPELAGO_SHRINE' then def = d; break end
    end
    if not def then
        local id = raws.buildings.next_id
        raws.buildings.next_id = id + 1
        raws.buildings.all:insert('#', {
            new   = df.building_def_workshopst,
            code  = 'DWARFIPELAGO_SHRINE',
            name  = 'Shrine of Dwarfipelagius',
            id    = id,
            dim_x = 1,
            dim_y = 1,
        })
        def = raws.buildings.all[#raws.buildings.all - 1]
        raws.buildings.workshops:insert('#', def)
        def.build_stages = 1
        for stage = 0, 1 do
            def.tile[stage][0][0]          = 2
            def.tile_color[0][stage][0][0] = 14
            def.tile_color[1][stage][0][0] = 0
            def.tile_color[2][stage][0][0] = 0
        end
        dfhack.print('[shrine] injected DWARFIPELAGO_SHRINE raw def (id=' .. tostring(id) .. ')\n')
    end

    pcall(function()
        load_shrine_map_icon()
        local tp = _shrine_icon_handle and
            dfhack.textures.getTexposByHandle(_shrine_icon_handle)
        dfhack.print(('[shrine] icon texpos=%s\n'):format(tostring(tp)))
        if tp and tp > 0 then
            for stage = 0, 1 do
                def.graphics_normal[stage][0][1] = tp
            end
        end
    end)
end

-- Place a completed Shrine of Dwarfipelagius workshop at pos.
-- Idempotent: does nothing if a shrine is already placed.
local function place_shrine_bld(pos)
    if not pos then return end
    if find_shrine_bld() then return end
    inject_shrine_def()
    local custom_idx = find_shrine_custom_idx()
    if custom_idx < 0 then
        dfhack.printerr("[shrine] DWARFIPELAGO_SHRINE not found in raws after inject")
        return
    end
    local ok, err = pcall(function()
        -- Provide an explicit filter so constructBuilding skips df.building_def.find
        -- (which doesn't see runtime-injected defs).  completeBuild then force-
        -- finishes the job so no dwarf or materials are actually required.
        local bld = dfhack.buildings.constructBuilding{
            type    = df.building_type.Workshop,
            subtype = df.workshop_type.Custom,
            custom  = custom_idx,
            pos     = pos,
            width   = 1,
            height  = 1,
            filters = {{
                new          = true,
                item_type    = df.item_type.BAR,
                item_subtype = -1,
                mat_type     = -1,
                mat_index    = -1,
                quantity     = 1,
            }},
        }
        if not bld then error("constructBuilding failed") end
        bld:setBuildStage(bld:getMaxBuildStage())
        dfhack.buildings.completeBuild(bld)
        dfhack.persistent.saveWorldDataString(SHRINE_BLD_KEY, tostring(bld.id))
    end)
    if not ok then
        dfhack.printerr("[shrine] place_shrine_bld: " .. tostring(err))
    end
end

-- -- Shrine Screen -------------------------------------------------------------

ShrineScreen = defclass(ShrineScreen, gui.ZScreen)
ShrineScreen.ATTRS{ focus_path = 'dwarfipelago/shrine' }

function ShrineScreen:init(opts)
    self._shrine_pos = opts.pos
    self._tick       = 0

    pcall(load_deity_sprite)

    self._status_lbl = widgets.Label{frame={t=0, l=0}, text=""}
    self._coins_lbl  = widgets.Label{frame={t=1, l=0}, text=""}
    self._shop_list  = widgets.List{
        frame      = {t=3, b=2},
        text_pen   = COLOR_WHITE,
        cursor_pen = COLOR_YELLOW,
        on_submit  = self:callback('on_buy'),
    }
    self._hint_lbl = widgets.Label{
        frame = {b=0, l=0},
        text  = {
            {text="[Enter]", pen=COLOR_YELLOW}, " offer tithe     ",
            {text="[Esc]",   pen=COLOR_YELLOW}, " depart",
        },
    }

    -- Title text starts at l=3: 2 cells for sprite + 1 gap
    local has_sprite = (_deity_handles ~= nil)
    local title_l    = has_sprite and 3 or 0

    self:addviews{
        widgets.Window{
            frame       = {w=66, h=28},
            frame_title = "The Merchant Afterlife",
            frame_inset = 1,
            subviews    = {
                TileSprite{frame={t=0, l=0, w=2, h=2}},
                widgets.Label{
                    frame = {t=0, l=title_l},
                    text  = {
                        "Shrine of ",
                        {text="Dwarfipelagius", pen=COLOR_YELLOW},
                        {text=" - God of Trade, Wealth, and Jewels",
                         pen=COLOR_DARKGRAY},
                    },
                },
                widgets.Panel{
                    frame    = {t=3, b=0},
                    subviews = {
                        self._status_lbl,
                        self._coins_lbl,
                        self._shop_list,
                        self._hint_lbl,
                    },
                },
            },
        },
    }
    self:refresh()
end

function ShrineScreen:read_state()
    local sraw    = ps("shop")
    local shop    = (sraw ~= "" and json.decode(sraw)) or {}
    local praw    = ps("shop_pending")
    local pending = (praw ~= "" and json.decode(praw)) or {}
    local coffers = tonumber(ps("unlock/wealth_coffers")) or 0
    local total_j = 0
    pcall(function()
        local _, j = checks.find_fortress_coins_energy()
        total_j = j or 0
    end)
    local coins   = math.floor(total_j / 1000)
    local unlocked = ps("shop_unlocked") == "1"
    return shop, pending, coffers, coins, unlocked
end

function ShrineScreen:refresh()
    local shop, pending, coffers, coins, unlocked = self:read_state()

    if unlocked then
        self._status_lbl:setText(
            {text="Dwarfipelagius awaits your tithe. The veil stands open.",
             pen=COLOR_DARKGRAY})
    else
        self._status_lbl:setText(
            {text="The shrine does not answer. Its requirements are unmet.",
             pen=COLOR_RED})
    end

    self._coins_lbl:setText{
        {text=fmt_num(coins).."*", pen=COLOR_YELLOW},
        " in the vault     ",
        {text=tostring(coffers).."/5", pen=COLOR_CYAN},
        " coffers sanctified",
    }

    local choices = {}
    local slots = {}
    for k in pairs(shop) do table.insert(slots, tonumber(k)) end
    table.sort(slots)

    for _, sn in ipairs(slots) do
        local e      = shop[tostring(sn)]
        local cost   = tonumber(e.price) or 0
        local buyable = false
        local name_pen, cost_pen, right

        if e.bought == 1 then
            name_pen = COLOR_DARKGRAY
            right    = " [claimed]"
            cost_pen = COLOR_DARKGRAY
        elseif pending[tostring(sn)] then
            name_pen = COLOR_LIGHTBLUE
            right    = " [in transit]"
            cost_pen = COLOR_LIGHTBLUE
        elseif not unlocked or coffers < (e.tier or 1) then
            name_pen = COLOR_DARKGRAY
            right    = (" [need %d coffers]"):format(e.tier or 1)
            cost_pen = COLOR_DARKGRAY
        else
            buyable  = true
            right    = ("  %s*"):format(fmt_num(cost))
            cost_pen = coins >= cost and COLOR_CYAN or COLOR_RED
            name_pen = coins >= cost and COLOR_WHITE or COLOR_DARKGRAY
        end

        local from = e.player and ("  \x1a %s"):format(e.player) or ""
        table.insert(choices, {
            text    = {
                {text=("%-26.26s"):format(e.item or "???"), pen=name_pen},
                {text=("%-20.20s"):format(from),            pen=COLOR_DARKGRAY},
                {text=right,                                 pen=cost_pen},
            },
            buyable = buyable,
            slot    = sn,
            cost    = cost,
            name    = e.item or "???",
        })
    end

    if #choices == 0 then
        table.insert(choices, {
            text = {text="No offerings have arrived from the afterlife yet.",
                    pen=COLOR_DARKGRAY},
        })
    end

    self._shop_list:setChoices(choices, self._shop_list:getSelected())
end

function ShrineScreen:on_buy(_, choice)
    if not choice or not choice.buyable then return end
    announce_tithe(choice.cost, choice.name, self._shrine_pos)
    dfhack.run_command("dwarfipelago", "buy-shop", tostring(choice.slot))
    self:refresh()
end

function ShrineScreen:onRenderFrame(dc, rect)
    ShrineScreen.super.onRenderFrame(self, dc, rect)
    self._tick = self._tick + 1
    if self._tick % 30 == 0 then self:refresh() end
end

function ShrineScreen:onDismiss()
    dfhack.gui.showAnnouncement(
        "You depart the shrine. The veil remains.",
        COLOR_DARKGRAY, false)
end

-- -- Public API ----------------------------------------------------------------

function M.inject_shrine_def()
    inject_shrine_def()
end

-- Called the first time the shrine meets requirements.  Spawns mist, zooms the
-- camera, and places the shrine statue in-world.
function M.first_summon()
    local pos = find_shrine_pos()
    spawn_mist_ring(pos)
    if pos then
        pcall(function()
            dfhack.gui.showZoomAnnouncement(
                df.announcement_type.CARAVAN_ARRIVAL,
                pos,
                "The shrine stirs. Dwarfipelagius takes notice from the merchant afterlife.",
                COLOR_GRAY, true)
        end)
    else
        dfhack.gui.showAnnouncement(
            "The shrine stirs. Dwarfipelagius takes notice from the merchant afterlife.",
            COLOR_GRAY, true)
    end
    dfhack.gui.showAnnouncement(
        "Dwarfipelagius has accepted your offerings. The veil stands open.",
        COLOR_DARKGRAY, false)
    pcall(place_shrine_bld, pos)
end

function M.open_shrine()
    local pos = find_shrine_pos()
    summon_at_shrine(pos)
    ShrineScreen{pos = pos}:show()
end

-- -- Shrine building overlay --------------------------------------------------
-- Full-panel overlay: covers the building viewsheet with the shrine shop UI.

local SHRINE_VIEWSCREEN = 'dwarfmode/ViewSheets/BUILDING/Workshop/Custom/DWARFIPELAGO_SHRINE'

local function safe_json_decode(s)
    if not s or s == '' then return {} end
    local ok, v = pcall(json.decode, s)
    return (ok and type(v) == 'table') and v or {}
end

local function read_shrine_state()
    local shop     = safe_json_decode(ps('shop'))
    local pending  = safe_json_decode(ps('shop_pending'))
    local coffers  = tonumber(ps('unlock/wealth_coffers')) or 0
    local total_j  = 0
    pcall(function()
        local _, j = checks.find_fortress_coins_energy()
        total_j = j or 0
    end)
    local coins    = math.floor(total_j / 1000)
    local unlocked = ps('shop_unlocked') == '1'
    return shop, pending, coffers, coins, unlocked
end

ShrineFullOverlay = defclass(ShrineFullOverlay, overlay.OverlayWidget)
ShrineFullOverlay.ATTRS {
    desc            = 'Shrine of Dwarfipelagius inline worship panel.',
    default_pos     = {x=0, y=3},
    default_enabled = true,
    viewscreens     = SHRINE_VIEWSCREEN,
    frame           = {w=60, h=50},
}

function ShrineFullOverlay:init()
    pcall(load_deity_sprite)
    self._tick = 0
    self._pos  = nil
    pcall(function() self._pos = find_shrine_pos() end)

    self._status_lbl = widgets.Label{frame={t=3, l=0}, text=''}
    self._coins_lbl  = widgets.Label{frame={t=4, l=0}, text=''}
    self._shop_list  = widgets.List{
        frame      = {t=6, b=2},
        text_pen   = COLOR_WHITE,
        cursor_pen = COLOR_YELLOW,
        on_submit  = self:callback('on_buy'),
    }
    self._hint_lbl = widgets.Label{
        frame = {b=0, l=0},
        text  = {
            {text='[Enter]', pen=COLOR_YELLOW}, ' offer tithe  ',
            {text='[Esc]',   pen=COLOR_YELLOW}, ' close panel',
        },
    }

    self:addviews{
        TileSprite{frame={t=0, l=0, w=2, h=2}},
        widgets.Label{
            frame = {t=0, l=3},
            text  = {'Shrine of ', {text='Dwarfipelagius', pen=COLOR_YELLOW}},
        },
        widgets.Label{
            frame = {t=1, l=3},
            text  = {text='God of Trade, Wealth, and Jewels',
                     pen=COLOR_DARKGRAY},
        },
        widgets.Label{
            frame = {t=2, l=0},
            text  = string.rep('-', 99),
        },
        self._status_lbl,
        self._coins_lbl,
        self._shop_list,
        self._hint_lbl,
    }
    pcall(self._refresh, self)
end

local _FILL_PEN = to_pen{ch=32, bg=COLOR_BLACK, fg=COLOR_BLACK}

function ShrineFullOverlay:onRenderBody(dc)
    dfhack.screen.fillRect(
        _FILL_PEN,
        dc.clip_x1, dc.clip_y1, dc.clip_x2, dc.clip_y2)
    ShrineFullOverlay.super.onRenderBody(self, dc)
end

function ShrineFullOverlay:_refresh()
    local shop, pending, coffers, coins, unlocked = read_shrine_state()

    if unlocked then
        self._status_lbl:setText{
            text='Dwarfipelagius awaits your tithe. The veil stands open.',
            pen=COLOR_DARKGRAY}
    else
        self._status_lbl:setText{
            text='The shrine does not answer. Its requirements are unmet.',
            pen=COLOR_RED}
    end

    self._coins_lbl:setText{
        {text=fmt_num(coins)..'*', pen=COLOR_YELLOW},
        ' in the vault  ',
        {text=tostring(coffers)..'/5', pen=COLOR_CYAN},
        ' coffers sanctified',
    }

    local choices = {}
    local slots   = {}
    for k in pairs(shop) do table.insert(slots, tonumber(k)) end
    table.sort(slots)

    for _, sn in ipairs(slots) do
        local e    = shop[tostring(sn)]
        local cost = tonumber(e.price) or 0
        local name_pen, cost_pen, right

        if e.bought == 1 then
            name_pen = COLOR_DARKGRAY
            right    = ' [claimed]'
            cost_pen = COLOR_DARKGRAY
        elseif pending[tostring(sn)] then
            name_pen = COLOR_LIGHTBLUE
            right    = ' [in transit]'
            cost_pen = COLOR_LIGHTBLUE
        elseif not unlocked or coffers < (e.tier or 1) then
            name_pen = COLOR_DARKGRAY
            right    = (' [need %d coffers]'):format(e.tier or 1)
            cost_pen = COLOR_DARKGRAY
        else
            right    = ('  %s*'):format(fmt_num(cost))
            cost_pen = coins >= cost and COLOR_CYAN or COLOR_RED
            name_pen = coins >= cost and COLOR_WHITE or COLOR_DARKGRAY
        end

        local from = e.player and ('  \x1a %s'):format(e.player) or ''
        table.insert(choices, {
            text = {
                {text=('%-28.28s'):format(e.item or '???'), pen=name_pen},
                {text=('%-18.18s'):format(from),            pen=COLOR_DARKGRAY},
                {text=right,                                 pen=cost_pen},
            },
            buyable = (e.bought ~= 1 and not pending[tostring(sn)]
                       and unlocked and coffers >= (e.tier or 1)),
            slot = sn,
            cost = cost,
            name = e.item or '???',
        })
    end

    if #choices == 0 then
        table.insert(choices, {
            text = {text='No offerings have arrived from the afterlife yet.',
                    pen=COLOR_DARKGRAY},
        })
    end

    self._shop_list:setChoices(choices, self._shop_list:getSelected())
end

function ShrineFullOverlay:on_buy(_, choice)
    if not choice or not choice.buyable then return end
    announce_tithe(choice.cost, choice.name, self._pos)
    dfhack.run_command('dwarfipelago', 'buy-shop', tostring(choice.slot))
    self:_refresh()
end

function ShrineFullOverlay:onRenderFrame(dc, rect)
    ShrineFullOverlay.super.onRenderFrame(self, dc, rect)
    self._tick = self._tick + 1
    if self._tick % 30 == 0 then
        local ok, err = pcall(self._refresh, self)
        if not ok then
            dfhack.printerr('[shrine-overlay] refresh error: ' .. tostring(err))
        end
    end
end

-- Must be on M so overlay plugin finds it via reqscript return value.
M.OVERLAY_WIDGETS = {
    shrine_full = ShrineFullOverlay,
}

for k, v in pairs(M) do _ENV[k] = v end
return M
