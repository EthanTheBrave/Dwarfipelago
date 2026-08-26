--@ module = true
-- Native Archipelago caravan: put the AP shop goods on a docked caravan as real
-- tool items (so DF's own trade screen renders them with the AP-logo sprite and
-- their real names), then detect when the player trades for one and grant the
-- AP purchase. Item defs are baked at world-gen by the client (apraws.py); this
-- module only spawns instances of them and watches the trade.
--
-- Data it reads/writes (dfhack persistent world data):
--   dwarfipelago/shop            {slot: {item,player,price,tier,bought}}  (AP client)
--   (goods are ITEM_TOOL_AP_TIER<tier> of material INORGANIC:AP_SHOP_<slot>)
--   dwarfipelago/ap_caravan_items {item_id: slot}   injected items, this module
--   dwarfipelago/shop_buy        [slot,...]         purchase queue (AP client reads)
--   dwarfipelago/shop_pending    {slot: true}       awaiting AP confirmation

local json = require('json')
local M = {}

local function ps(key)
    local v = dfhack.persistent.getWorldDataString("dwarfipelago/" .. key)
    if v == nil or v == "" then return nil end
    return v
end
local function pset(key, val) dfhack.persistent.saveWorldDataString("dwarfipelago/" .. key, val) end
local function decode(raw, default)
    if not raw then return default end
    local ok, v = pcall(json.decode, raw)
    return (ok and type(v) == "table") and v or default
end

local function find_depot()
    for _, b in ipairs(df.global.world.buildings.all) do
        if df.building_tradedepotst:is_instance(b) then return b end
    end
    return nil
end

-- A tool item's df subtype for a given raw id (ITEM_TOOL_AP_...).
local function tool_subtype(tool_id)
    for _, td in ipairs(df.global.world.raws.itemdefs.tools) do
        if td.id == tool_id then return td.subtype end
    end
    return nil
end

-- The df tool subtypes of our AP tier tools (ITEM_TOOL_AP_TIER<n>), so we can
-- recognise our own injected goods among the caravan's items.
local function ap_tool_subtypes()
    local set = {}
    for _, td in ipairs(df.global.world.raws.itemdefs.tools) do
        if td.id:match("^ITEM_TOOL_AP_TIER%d") then set[td.subtype] = true end
    end
    return set
end

-- True if an item is one of our injected AP goods. Uses getSubtype() (numeric);
-- item.subtype is the itemdef object, not the subtype index.
local function is_ap_tool(it, subset)
    if it:getType() ~= df.item_type.TOOL then return false end
    subset = subset or ap_tool_subtypes()
    return subset[it:getSubtype()] == true
end

local function a_merchant()
    for _, u in ipairs(df.global.world.units.active) do
        local m = false
        pcall(function() m = u.flags1.merchant end)
        if m and dfhack.units.isAlive(u) then return u end
    end
    return nil
end

-- The civ that owns this caravan's goods. The docked merchants ARE the caravan,
-- so their civ_id is the owner (a gorlak caravan's civ is the gorlak civ). AP
-- goods need a matching ENTITY_ITEMOWNER ref or DF will not list them as this
-- caravan's merchandise. Prefer the merchant civ over scanning depot items, which
-- may hold leftover goods or our own AP tools carrying a stale owner.
local function caravan_owner_entity(depot)
    local m = a_merchant()
    if m and m.civ_id and m.civ_id >= 0 then return m.civ_id end
    -- Fallback: read the owner off a real (non-AP) trader good.
    local subset = ap_tool_subtypes()
    for _, ci in ipairs(depot.contained_items) do
        local it = ci.item
        if not is_ap_tool(it, subset) then
            for _, r in ipairs(it.general_refs) do
                if r:getType() == df.general_ref_type.ENTITY_ITEMOWNER then return r.entity_id end
            end
        end
    end
    return nil
end

-- Resolve a material token (e.g. "INORGANIC:AP_SHOP_7") to type/index. Each shop
-- slot has its own inorganic whose name is the good; falls back to iron.
local function material_for(mat_token)
    local mi = dfhack.matinfo.find(mat_token)
    if mi then return mi.type, mi.index end
    mi = dfhack.matinfo.find("INORGANIC:IRON")
    if mi then return mi.type, mi.index end
    return 0, 0
end

-- A real caravan is docked when merchant units and a depot both exist.
function M.caravan_docked()
    return find_depot() ~= nil and a_merchant() ~= nil
end

-- True when the docked caravan is the Archipelago (gorlak) civ, i.e. the AP shop
-- caravan. AP goods and good-hiding apply only to this caravan; normal dwarf/elf/
-- human caravans are left untouched.
local function is_ap_caravan()
    local m = a_merchant()
    if not m or not m.civ_id or m.civ_id < 0 then return false end
    local e = df.historical_entity.find(m.civ_id)
    return e ~= nil and e.entity_raw.code == "ARCHIPELAGO"
end
M.is_ap_caravan = is_ap_caravan

-- Hide the caravan's own (non-AP) merchandise so only AP goods show on the trade
-- screen. Clears the trader flag: immediate and non-destructive (caged livestock
-- is only un-flagged, never removed, so no animals are loosed). Runs each poll
-- tick because the caravan unloads its goods from the wagons gradually. Only acts
-- on the AP (gorlak) caravan.
function M.hide_caravan_goods()
    if not is_ap_caravan() then return 0 end
    local subset = ap_tool_subtypes()
    local n = 0
    for _, it in ipairs(df.global.world.items.all) do
        local t = false
        pcall(function() t = it.flags.trader end)
        if t and not is_ap_tool(it, subset) then
            pcall(function() it.flags.trader = false end)
            n = n + 1
        end
    end
    return n
end

-- Create one AP good as a trader-flagged tool item at the depot.
-- Returns the item, or nil.
local function spawn_good(tool_id, mat_token, depot, owner_ent)
    local sub = tool_subtype(tool_id)
    if not sub then return nil end
    local merchant = a_merchant()
    local mt, mi = material_for(mat_token)
    local res = dfhack.items.createItem(merchant, df.item_type.TOOL, sub, mt, mi)
    local it = (type(res) == "table" and res[1]) or res
    if not it then return nil end
    pcall(function() it.flags.trader = true end)
    -- Put it in the depot as caravan merchandise so the trade screen lists it.
    pcall(function() dfhack.items.moveToBuilding(it, depot, 0) end)
    pcall(function() it.flags.in_building = true end)
    -- Register as caravan merchandise; without this DF omits it from the trade list.
    if owner_ent then
        local ref = df.general_ref_entity_itemownerst:new()
        ref.entity_id = owner_ent
        it.general_refs:insert("#", ref)
    end
    return it
end

-- Inject every unlocked, unbought, not-yet-injected shop good onto the caravan.
-- Coffer-gated: only slots whose tier <= current coffers are offered.
function M.inject_ap_goods()
    if not M.caravan_docked() then return 0 end
    if not is_ap_caravan() then return 0 end   -- AP goods only on the gorlak caravan
    local depot = find_depot()
    local owner_ent = caravan_owner_entity(depot)
    local shop = decode(ps("shop"), {})
    local pending = decode(ps("shop_pending"), {})
    local injected = decode(ps("ap_caravan_items"), {})   -- item_id(str) -> slot
    local coffers = tonumber(ps("unlock/wealth_coffers")) or 0

    -- which slots already have a live injected item?
    local live = {}
    for _, slot in pairs(injected) do live[tostring(slot)] = true end

    local n = 0
    for slot_str, e in pairs(shop) do
        local tier = math.max(1, math.min(5, tonumber(e.tier) or 1))
        -- shared per-tier tool (grouping header) + per-slot material (the name),
        -- matching apraws.py's ITEM_TOOL_AP_TIER<n> and INORGANIC:AP_SHOP_<slot>.
        local tool = "ITEM_TOOL_AP_TIER" .. tier
        local mat = "INORGANIC:AP_SHOP_" .. slot_str
        if tool_subtype(tool) and (tonumber(e.bought) or 0) == 0 and not pending[slot_str]
                and not live[slot_str] and tier <= coffers then
            local it = spawn_good(tool, mat, depot, owner_ent)
            if it then
                injected[tostring(it.id)] = tonumber(slot_str)
                n = n + 1
            end
        end
    end
    pset("ap_caravan_items", json.encode(injected))
    return n
end

-- Detect AP goods that were traded to the fort (trader flag cleared or item
-- gone) and queue their purchases for the AP client. Call from the poll loop.
function M.detect_ap_trades()
    local injected = decode(ps("ap_caravan_items"), {})
    if not next(injected) then return 0 end
    local pending = decode(ps("shop_pending"), {})
    local queue = decode(ps("shop_buy"), {})
    local n = 0
    for id_str, slot in pairs(injected) do
        local it = df.item.find(tonumber(id_str))
        local traded = false
        if not it then
            traded = true                     -- consumed/removed after trade
        else
            local tr = false
            pcall(function() tr = it.flags.trader end)
            if not tr then traded = true end   -- now fort-owned
        end
        if traded then
            pending[tostring(slot)] = true
            queue[#queue + 1] = slot
            injected[id_str] = nil
            n = n + 1
        end
    end
    if n > 0 then
        pset("ap_caravan_items", json.encode(injected))
        pset("shop_pending", json.encode(pending))
        pset("shop_buy", json.encode(queue))
    end
    return n
end

-- On caravan departure, remove any AP goods the player did not buy so they never
-- linger in the fort, and clear the injected-item record.
function M.clear_ap_goods()
    local injected = decode(ps("ap_caravan_items"), {})
    for id_str in pairs(injected) do
        local it = df.item.find(tonumber(id_str))
        if it then
            local tr = false
            pcall(function() tr = it.flags.trader end)
            if tr then pcall(function() dfhack.items.remove(it) end) end
        end
    end
    pset("ap_caravan_items", json.encode({}))
end

for k, v in pairs(M) do _ENV[k] = v end
return M
