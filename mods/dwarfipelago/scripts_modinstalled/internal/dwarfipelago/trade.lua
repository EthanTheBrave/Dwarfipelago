--@ module = true
-- Merchant trade window: a caravan-style two-pane trade screen opened at the
-- shrine altar. Left pane = purchasable AP shop goods; right pane = an offer
-- basket built from items stored in the shrine's container. Coins/gems count at
-- full value, everything else at 50%. Confirm consumes the offered items and
-- queues the goods' purchases for the AP client (dwarfipelago/shop_buy).
--
-- Backend is reqscript-able; the overlay and panel call M.open()/M.is_shrine_altar().

local gui     = require('gui')
local widgets = require('gui.widgets')
local json    = require('json')

local M = {}

local OFFER_NONCOIN_MULT = 0.5   -- non coin/gem items are worth half their value

local function ps(key, default)
    local v = dfhack.persistent.getWorldDataString("dwarfipelago/" .. key)
    if v == nil or v == "" then return default end
    return v
end

local function decode_or(raw, default)
    if not raw or raw == "" then return default end
    local ok, v = pcall(json.decode, raw)
    if ok and type(v) == "table" then return v end
    return default
end

local SHRINE_BAR_TOKS = { gold = "GOLD", coke = "COKE", silver = "SILVER" }

-- Resolve the claimed shrine's temple zone (bbox) from shrine_progress.
function M.shrine_zone()
    local raw = ps("shrine_progress", "")
    if raw == "" then return nil end
    local ok, prog = pcall(json.decode, raw)
    if not ok or not prog or not prog.zone then return nil end
    for _, z in ipairs(df.global.world.buildings.other.ANY_ZONE) do
        if z.id == prog.zone then
            return {
                id = z.id,
                x1 = math.min(z.x1, z.x2), x2 = math.max(z.x1, z.x2),
                y1 = math.min(z.y1, z.y2), y2 = math.max(z.y1, z.y2),
                z  = z.z,
            }
        end
    end
    return nil
end

local function overlaps(b, zn)
    return b.z == zn.z and b.x1 <= zn.x2 and b.x2 >= zn.x1
        and b.y1 <= zn.y2 and b.y2 >= zn.y1
end

-- True when bld is the offering-place altar sitting in the claimed shrine zone.
-- Uses the OFFERING_PLACE list (same source the shrine detector trusts) rather
-- than a hardcoded class name.
function M.is_shrine_altar(bld)
    if not bld then return false end
    local zn = M.shrine_zone()
    if not zn then return false end
    local is_offering = false
    for _, b in ipairs(df.global.world.buildings.other.OFFERING_PLACE) do
        if b.id == bld.id then is_offering = true; break end
    end
    return is_offering and overlaps(bld, zn)
end

function M.shop_unlocked()
    return ps("shop_unlocked", "0") == "1"
end

-- True while an Archipelago caravan is currently docked at the trade depot.
function M.ap_caravan_docked()
    return ps("ap_caravan_active", "0") == "1"
end

-- The AP shop is caravan-only: buying is possible only while an Archipelago
-- caravan is docked at the depot. Goods stay limited to the unlocked coffer tiers.
function M.shop_accessible()
    return M.ap_caravan_docked()
end

function M.is_trade_depot(bld)
    return (bld and df.building_tradedepotst:is_instance(bld)) and true or false
end

-- Adjusted ☼ value of an offer item: coins/gems at full, else half (floored).
local function item_offer_value(it, itype)
    local ok, v = pcall(dfhack.items.getValue, it)
    if not ok or not v then return 0, false end
    local coingem = (itype == df.item_type.COIN or itype == df.item_type.SMALLGEM)
    if coingem then return v, true end
    return math.floor(v * OFFER_NONCOIN_MULT), false
end

-- Offer candidates, by entry point. coins/gems count full, everything else half.
--   context "depot" (caravan): items slated for trade at the trade depot.
--   context "altar" (shrine, default): pedestal/display-case items, plus coins
--     and cut gems sitting in a stockpile (loose, or inside a bin on a stockpile
--     tile).
function M.offer_items(context)
    local marker_id = tonumber(ps("shrine_marker", "")) or -1
    local out, counted = {}, {}
    local function collect(it)
        if not it or counted[it.id] then return end
        counted[it.id] = true
        if it.id == marker_id then return end
        local val, coingem = item_offer_value(it, it:getType())
        if val > 0 then
            local ok, name = pcall(dfhack.items.getDescription, it, 0, true)
            out[#out + 1] = { id = it.id, name = ok and name or "?", value = val, coingem = coingem }
        end
    end

    if context == "depot" then
        -- Items brought to the trade depot for trade (TEMP role; PERM entries are
        -- the depot's own construction materials).
        for _, b in ipairs(df.global.world.buildings.all) do
            if df.building_tradedepotst:is_instance(b) then
                for _, ci in ipairs(b.contained_items) do
                    -- fortress goods staged for trade: TEMP role, and NOT the
                    -- caravan's own merchandise (which carries the trader flag).
                    local it = ci.item
                    if ci.use_mode == df.building_item_role_type.TEMP and it and not it.flags.trader then
                        collect(it)
                    end
                end
            end
        end
    else
        -- Altar: displayed items (pedestals + display cases) ...
        for _, b in ipairs(df.global.world.buildings.all) do
            if df.building_display_furniturest:is_instance(b) then
                for _, entry in ipairs(b.displayed_items) do
                    collect(type(entry) == "number" and df.item.find(entry) or entry)
                end
            end
        end
        -- ... plus coins + cut gems on stockpile tiles (climb out of any bin).
        local function on_stockpile(it)
            local ground, c = it, dfhack.items.getContainer(it)
            while c do ground = c; c = dfhack.items.getContainer(ground) end
            local p = ground.pos
            if not p then return false end
            local bld = dfhack.buildings.findAtTile(p.x, p.y, p.z)
            return bld and df.building_stockpilest:is_instance(bld)
        end
        for _, it in ipairs(df.global.world.items.all) do
            local itype = it:getType()
            if (itype == df.item_type.COIN or itype == df.item_type.SMALLGEM)
                    and not counted[it.id] and on_stockpile(it) then
                collect(it)
            end
        end
    end

    table.sort(out, function(a, b) return a.value > b.value end)
    return out
end

-- Buyable AP shop goods with state, from the AP-written shop data.
function M.goods()
    local shop     = decode_or(ps("shop", ""), {})
    local pending  = decode_or(ps("shop_pending", ""), {})
    local coffers  = tonumber(ps("unlock/wealth_coffers", "0")) or 0
    local unlocked = M.shop_accessible()

    local slots = {}
    for k in pairs(shop) do slots[#slots + 1] = tonumber(k) end
    table.sort(slots)

    local out = {}
    for _, sn in ipairs(slots) do
        local e = shop[tostring(sn)]
        local price = tonumber(e.price) or 0
        local tier  = tonumber(e.tier) or 1
        local state, buyable
        if e.bought == 1 then
            state = "SOLD"
        elseif pending[tostring(sn)] then
            state = "PENDING"
        elseif not unlocked then
            state = "shop closed"
        elseif coffers < tier then
            state = ("need %d coffers"):format(tier)
        else
            state, buyable = "buyable", true
        end
        out[#out + 1] = {
            slot = sn, item = tostring(e.item or "?"), player = tostring(e.player or "?"),
            price = price, tier = tier, state = state, buyable = buyable,
        }
    end
    return out, coffers, unlocked
end

-- Complete a trade: validate the selected goods and offered value, then consume
-- the offered items and queue the purchases. Returns ok(bool), message(string).
function M.confirm(slots, offer_ids)
    if not slots or #slots == 0 then return false, "Select at least one item to buy." end
    if not M.shop_accessible() then return false, "The shop is closed - no shrine or docked caravan." end

    local shop    = decode_or(ps("shop", ""), {})
    local pending = decode_or(ps("shop_pending", ""), {})
    local coffers = tonumber(ps("unlock/wealth_coffers", "0")) or 0

    local total_price = 0
    for _, sn in ipairs(slots) do
        local e = shop[tostring(sn)]
        if not e then return false, "A selected item is no longer available." end
        if e.bought == 1 or pending[tostring(sn)] then
            return false, ("'%s' was already purchased."):format(tostring(e.item or "item"))
        end
        local tier = tonumber(e.tier) or 1
        if coffers < tier then
            return false, ("Tier %d locked - receive %d Merchant's Coffer(s)."):format(tier, tier)
        end
        total_price = total_price + (tonumber(e.price) or 0)
    end

    -- Value the offered items (re-resolve ids so nothing stale is trusted).
    local offered, items = 0, {}
    for _, id in ipairs(offer_ids or {}) do
        local it = df.item.find(id)
        if it then
            local val = select(1, item_offer_value(it, it:getType()))
            if val > 0 then offered = offered + val; items[#items + 1] = it end
        end
    end
    if offered < total_price then
        return false, ("Not enough offered value: need %d, offered %d."):format(total_price, offered)
    end

    -- Consume the offered items. remove() refuses anything still flagged
    -- in_building, so first detach from whatever holds it - a display pedestal
    -- (displayed_items) or the trade depot (contained_items) - clear in_building,
    -- set on_ground, and drop it to the floor. Otherwise depot trade goods (the
    -- goods hauled in for trade) survive the trade.
    for _, it in ipairs(items) do
        local iid = it.id
        pcall(function()
            for _, b in ipairs(df.global.world.buildings.all) do
                if df.building_display_furniturest:is_instance(b) then
                    for i = #b.displayed_items - 1, 0, -1 do
                        if b.displayed_items[i] == iid then b.displayed_items:erase(i) end
                    end
                elseif df.building_tradedepotst:is_instance(b) then
                    for i = #b.contained_items - 1, 0, -1 do
                        local ci = b.contained_items[i]
                        if ci.item and ci.item.id == iid then b.contained_items:erase(i) end
                    end
                end
            end
            it.flags.in_building = false
            it.flags.on_ground   = true
            local p = it.pos
            if p then dfhack.items.moveToGround(it, {x = p.x, y = p.y, z = p.z}) end
        end)
        pcall(function() dfhack.items.remove(it) end)
    end

    -- Mark pending + append to the client buy queue.
    for _, sn in ipairs(slots) do pending[tostring(sn)] = true end
    dfhack.persistent.saveWorldDataString("dwarfipelago/shop_pending", json.encode(pending))
    local queue = decode_or(ps("shop_buy", ""), {})
    for _, sn in ipairs(slots) do queue[#queue + 1] = sn end
    dfhack.persistent.saveWorldDataString("dwarfipelago/shop_buy", json.encode(queue))

    return true, ("Traded for %d item(s) (%d value offered)."):format(#slots, offered)
end

-- ── Trade window ──────────────────────────────────────────────────────────────

local SORTS = {
    { label = "price", value = "price" },
    { label = "tier",  value = "tier" },
    { label = "buyer", value = "player" },
}

MerchantTradeScreen = defclass(MerchantTradeScreen, gui.ZScreen)
MerchantTradeScreen.ATTRS{ focus_path = "dwarfipelago/trade", context = "altar" }

function MerchantTradeScreen:init()
    self.sel_goods = {}   -- [slot]=true
    self.sel_offer = {}   -- [item id]=true
    self.sort_key  = "price"

    -- Big two-column layout that mirrors the vanilla caravan trade screen:
    -- a greeting header, "Caravan goods" | "Your fortress" boxes with the value
    -- and check box on the right of each row, and a bottom action bar.
    local W, H = 128, 46
    self:addviews{
        widgets.Window{
            frame_title = self.context == "depot" and "Archipelago Caravan" or "Merchant Shop",
            frame       = { w = W, h = H },
            resizable   = true,
            resize_min  = { w = 96, h = 34 },
            subviews    = {
                -- Greeting header, in the style of the merchant's intro banner.
                widgets.Panel{
                    frame       = { t = 0, l = 0, r = 0, h = 5 },
                    frame_style = gui.FRAME_INTERIOR,
                    subviews    = {
                        widgets.Label{ view_id = "greet_name", frame = { t = 0, l = 0 } },
                        widgets.Label{ view_id = "greet_line", frame = { t = 1, l = 0 } },
                        widgets.Label{ view_id = "greet_mood", frame = { t = 2, l = 0 } },
                    },
                },
                -- Left column: search field over the caravan's goods, grouped by
                -- coffer tier. The List draws its own scrollbar when it overflows.
                widgets.Panel{
                    frame       = { t = 5, b = 4, l = 0, w = 64 },
                    frame_style = gui.FRAME_INTERIOR,
                    frame_title = "Caravan goods",
                    subviews    = {
                        widgets.EditField{
                            view_id = "goods_search", frame = { t = 0, l = 0, r = 0 },
                            label_text = "Search: ",
                            on_change = function(text) self.goods_query = text; self:refresh() end,
                        },
                        widgets.List{
                            view_id = "goods", frame = { t = 2, b = 0, l = 0, r = 0 },
                            on_submit = function(_, c) if c and c.slot then self:toggle_good(c.slot) end end,
                        },
                    },
                },
                -- Right column: search field over the fort's offered goods.
                widgets.Panel{
                    frame       = { t = 5, b = 4, l = 64, r = 0 },
                    frame_style = gui.FRAME_INTERIOR,
                    frame_title = "Your fortress",
                    subviews    = {
                        widgets.EditField{
                            view_id = "offer_search", frame = { t = 0, l = 0, r = 0 },
                            label_text = "Search: ",
                            on_change = function(text) self.offer_query = text; self:refresh() end,
                        },
                        widgets.List{
                            view_id = "offer", frame = { t = 2, b = 0, l = 0, r = 0 },
                            on_submit = function(_, c) if c and c.id then self:toggle_offer(c.id) end end,
                        },
                    },
                },
                -- Bottom action bar: per-side totals then the buttons.
                widgets.Label{ view_id = "lfoot", frame = { b = 2, l = 1 } },
                widgets.Label{ view_id = "rfoot", frame = { b = 2, l = 66 } },
                widgets.HotkeyLabel{
                    frame = { b = 0, l = 1 }, key = "CUSTOM_A", label = "Mark all",
                    on_activate = function() self:mark_all(true) end,
                },
                widgets.HotkeyLabel{
                    frame = { b = 0, l = 16 }, key = "CUSTOM_SHIFT_A", label = "Unmark all",
                    on_activate = function() self:mark_all(false) end,
                },
                widgets.HotkeyLabel{
                    frame = { b = 0, l = 33 }, key = "CUSTOM_C", label = "Trade",
                    on_activate = function() self:do_confirm() end,
                },
                widgets.Label{ view_id = "msg", frame = { b = 0, l = 46 } },
            },
        },
    }
    self:refresh()
end

function MerchantTradeScreen:toggle_good(slot)
    self.sel_goods[slot] = (not self.sel_goods[slot]) or nil
    self:refresh()
end

function MerchantTradeScreen:toggle_offer(id)
    self.sel_offer[id] = (not self.sel_offer[id]) or nil
    self:refresh()
end

-- Mark or unmark every buyable good at once (the bar's Mark all / Unmark all).
function MerchantTradeScreen:mark_all(select)
    self.sel_goods = {}
    if select then
        local goods = M.goods()
        for _, g in ipairs(goods) do
            if g.buyable then self.sel_goods[g.slot] = true end
        end
    end
    self:refresh()
end

function MerchantTradeScreen:refresh()
    local goods, coffers = M.goods()
    local offer = M.offer_items(self.context)
    local gq = (self.goods_query or ""):lower()
    local oq = (self.offer_query or ""):lower()

    -- Selection totals span every item, not just what the search currently shows.
    local required = 0
    for _, g in ipairs(goods) do
        if self.sel_goods[g.slot] and g.buyable then required = required + g.price end
    end
    local offered = 0
    for _, o in ipairs(offer) do
        if self.sel_offer[o.id] then offered = offered + o.value end
    end

    -- Goods list: filtered by the search box, grouped into coffer-tier tiles
    -- (a grey full-width bar per tier). The List draws its own scrollbar.
    local by_tier, tiers = {}, {}
    for _, g in ipairs(goods) do
        if gq == "" or g.item:lower():find(gq, 1, true) then
            if not by_tier[g.tier] then by_tier[g.tier] = {}; tiers[#tiers + 1] = g.tier end
            table.insert(by_tier[g.tier], g)
        end
    end
    table.sort(tiers)

    local BAR_W = 60
    local gchoices = {}
    for _, t in ipairs(tiers) do
        local list = by_tier[t]
        table.sort(list, function(a, b) return a.price < b.price end)
        local label = ("Tier %d  %s"):format(t, t <= coffers and "(unlocked)"
            or ("(need %d coffer%s)"):format(t, t == 1 and "" or "s"))
        gchoices[#gchoices + 1] = { text = {{
            text = ("%-" .. BAR_W .. "s"):format(label),
            pen  = { fg = COLOR_BLACK, bg = COLOR_GREY },
        }} }
        for _, g in ipairs(list) do
            local marked = self.sel_goods[g.slot] and true or false
            local pen = COLOR_WHITE
            if not g.buyable then pen = COLOR_DARKGRAY
            elseif marked      then pen = COLOR_LIGHTGREEN end
            local right = g.buyable and ("[%s]"):format(marked and "x" or " ")
                                     or  ("(%s)"):format(g.state)
            gchoices[#gchoices + 1] = {
                text = ("  %-36.36s Value:%5d*  %s"):format(g.item, g.price, right),
                pen = pen, slot = g.buyable and g.slot or nil,
            }
        end
    end
    if #gchoices == 0 then
        gchoices[1] = { text = gq ~= "" and "  (no goods match your search)"
                                        or  "  (the caravan has no goods yet)", pen = COLOR_DARKGRAY }
    end

    -- Offer list: fort goods, filtered by its own search box.
    local ochoices = {}
    for _, o in ipairs(offer) do
        if oq == "" or (o.name or ""):lower():find(oq, 1, true) then
            local marked = self.sel_offer[o.id] and true or false
            local vpen = o.coingem and COLOR_YELLOW or COLOR_GRAY
            ochoices[#ochoices + 1] = {
                text = ("  %-36.36s Value:%5d*  [%s]"):format(o.name or "?", o.value, marked and "x" or " "),
                pen = marked and COLOR_LIGHTGREEN or vpen, id = o.id,
            }
        end
    end
    if #ochoices == 0 then
        ochoices[1] = { text = oq ~= "" and "  (no goods match your search)"
            or (self.context == "depot"
                and "  (mark fort goods for trade at the depot to offer them)"
                or  "  (store coins/goods in the shrine's container)"), pen = COLOR_DARKGRAY }
    end

    self.subviews.goods:setChoices(gchoices, self.subviews.goods:getSelected())
    self.subviews.offer:setChoices(ochoices, self.subviews.offer:getSelected())

    -- Greeting banner.
    self.subviews.greet_name:setText({{ text = "The Archipelago Caravan", pen = COLOR_YELLOW }})
    self.subviews.greet_line:setText({{
        text = '"Wonders from across the multiworld - what catches your eye?"', pen = COLOR_CYAN }})
    self.subviews.greet_mood:setText({
        ("%d coffer%s unlocked."):format(coffers, coffers == 1 and "" or "s"),
        { text = "   Enter: mark/unmark", pen = COLOR_GRAY },
    })

    -- Bottom totals, one per side.
    self.subviews.lfoot:setText({
        { text = "Archipelago Caravan", pen = COLOR_YELLOW },
        "   Required: ", { text = ("%d*"):format(required), pen = COLOR_CYAN },
    })
    local balance = offered - required
    local bal_pen = COLOR_GRAY
    if required > 0 then bal_pen = offered >= required and COLOR_LIGHTGREEN or COLOR_LIGHTRED end
    self.subviews.rfoot:setText({
        { text = "Your fortress", pen = COLOR_YELLOW },
        "   Offered: ", { text = ("%d*"):format(offered), pen = COLOR_LIGHTGREEN },
        "   Balance: ", { text = ("%d*"):format(balance), pen = bal_pen },
    })
end

function MerchantTradeScreen:do_confirm()
    local slots, ids = {}, {}
    for slot in pairs(self.sel_goods) do slots[#slots + 1] = slot end
    for id   in pairs(self.sel_offer) do ids[#ids + 1] = id end
    local ok, msg = M.confirm(slots, ids)
    if ok then
        self.sel_goods, self.sel_offer = {}, {}
        pcall(function() dfhack.gui.showAnnouncement("[AP] " .. msg, COLOR_GREEN, true) end)
    end
    self:refresh()
    self.subviews.msg:setText({ text = msg, pen = ok and COLOR_LIGHTGREEN or COLOR_LIGHTRED })
end

function MerchantTradeScreen:onInput(keys)
    if keys._MOUSE_L and not self:isMouseOver() then self:dismiss(); return true end
    return MerchantTradeScreen.super.onInput(self, keys)
end

local _trade_instance = nil
function MerchantTradeScreen:onDismiss() _trade_instance = nil end

-- Open the trade window (no-op if the shop is closed). context "depot" offers
-- items slated for trade at the depot; "altar" (default) offers pedestal +
-- stockpiled coins/gems.
function M.open(context)
    if not M.shop_accessible() then
        pcall(function() dfhack.gui.showAnnouncement(
            "[AP] The shop is closed - visit the shrine or a docked Archipelago caravan.", COLOR_YELLOW, true) end)
        return
    end
    if _trade_instance then _trade_instance:dismiss() end
    _trade_instance = MerchantTradeScreen{context = context or "altar"}
    _trade_instance:show()
end

-- reqscript returns the script's _ENV, not the explicit return value.
-- Copy all module exports into _ENV so callers can access them as globals.
for k, v in pairs(M) do _ENV[k] = v end
return M
