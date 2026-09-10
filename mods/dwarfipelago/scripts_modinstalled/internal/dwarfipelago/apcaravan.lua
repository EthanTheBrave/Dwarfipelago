--@ module = true
-- Native Archipelago caravan: put the AP shop goods on a docked caravan as real
-- tool items (so DF's own trade screen renders them with the AP-logo sprite and
-- their real names), then detect when the player trades for one and grant the
-- AP purchase. The mod's raws ship SHOP_SLOTS placeholder materials (apraws.py);
-- this module writes each slot's real name and price into the loaded material,
-- spawns instances of the goods, and watches the trade.
--
-- Data it reads/writes (dfhack persistent world data):
--   dwarfipelago/shop            {slot: {item,player,price,tier,bought}}  (AP client)
--   (goods are ITEM_TOOL_AP_TIER<tier> of material INORGANIC:AP_SHOP_<slot>)
--   dwarfipelago/ap_caravan_items {item_id: slot}   injected items, this module
--   dwarfipelago/shop_buy        [slot,...]         purchase queue (AP client reads)
--   dwarfipelago/shop_pending    {slot: true}       awaiting AP confirmation

local json = require('json')
local log = reqscript("internal/dwarfipelago/log")
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

-- ── Shop materials ───────────────────────────────────────────────────────────
-- Each shop slot is an ITEM_TOOL_AP_TIER<tier> made of INORGANIC:AP_SHOP_<slot>.
-- The material carries both the good's display name and its price, and the raws
-- only ship placeholders for them, so this module writes the real values into the
-- loaded materials. That is what makes the shop work in *any* world generated
-- with the mod, whether or not the AP client had scouted the shop before
-- world-gen (the client's per-seed raw bake is a fallback for the same values).

-- DF values a tool as (itemdef VALUE) x (material MATERIAL_VALUE); the AP tier
-- tools carry VALUE:100 (apraws.TOOL_VALUE).
local TOOL_VALUE = 100

-- slot(string) -> index into world.raws.inorganics, built on first use.
local _slot_mat = nil

local function build_slot_mat()
    local map = {}
    for i, raw in ipairs(df.global.world.raws.inorganics) do
        local slot = raw.id:match("^AP_SHOP_(%d+)$")
        if slot then map[slot] = i end
    end
    _slot_mat = map
    return map
end

-- The inorganic raw for a slot, or nil when this world has no such material.
-- Re-checks the cached index against its id so loading a different save (which
-- reloads the raws) rebuilds the map instead of writing to the wrong material.
local function inorganic_for(slot_str)
    local want = "AP_SHOP_" .. slot_str
    local map = _slot_mat or build_slot_mat()
    local idx = map[slot_str]
    local raw = idx and df.global.world.raws.inorganics[idx]
    if raw and raw.id == want then return raw end
    map = build_slot_mat()
    idx = map[slot_str]
    raw = idx and df.global.world.raws.inorganics[idx]
    return (raw and raw.id == want) and raw or nil
end

-- One warning per session for a world whose raws predate the shop materials.
local function warn_missing_raws(n)
    if M._warned_missing_raws then return end
    M._warned_missing_raws = true
    log.warn(("%d shop slot(s) have no AP_SHOP material in this world's raws, so their "):format(n)
        .. "goods trade as unnamed iron at a flat price. This world was generated with a mod "
        .. "build that predates the shop materials - regenerate the world with the current "
        .. "Dwarfipelago mod enabled.")
end

-- Write this seed's name and price into every shop slot's material. In-memory
-- only: DF reloads raws from the save on each load, so this re-applies from the
-- poll loop and is never written back. Compare-then-write makes it a no-op after
-- the first tick and self-healing after a reload. Returns the number of fields
-- changed.
function M.apply_shop_materials()
    local shop = decode(ps("shop"), {})
    if not next(shop) then return 0 end
    local changed, missing = 0, 0
    for slot_str, e in pairs(shop) do
        local raw = inorganic_for(slot_str)
        if not raw then
            missing = missing + 1
        else
            local mat = raw.material
            local name = tostring(e.item or "")
            local player = tostring(e.player or "")
            if name ~= "" and player ~= "" then name = name .. " (" .. player .. ")" end
            if name ~= "" and mat.state_name.Solid ~= name then
                if pcall(function()
                            mat.state_name.Solid = name
                            mat.state_adj.Solid = name
                        end) then
                    changed = changed + 1
                else
                    M._write_failed = true
                end
            end
            local price = tonumber(e.price)
            if price and price > 0 then
                local value = math.max(1, math.floor(price / TOOL_VALUE + 0.5))
                if mat.material_value ~= value then
                    if pcall(function() mat.material_value = value end) then
                        changed = changed + 1
                    else
                        M._write_failed = true
                    end
                end
            end
        end
    end
    if missing > 0 then warn_missing_raws(missing) end
    if M._write_failed and not M._warned_write_failed then
        M._warned_write_failed = true
        log.warn("Could not write shop names/prices into the loaded materials; the goods "
            .. "keep whatever the world's raws hold. If those are placeholders, connect the "
            .. "AP client before generating a world so it bakes the names in.")
    end
    return changed
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
-- Third return is false when the fallback was used - this world's raws predate
-- the shop materials, so the good has no name and no price.
local function material_for(mat_token)
    local mi = dfhack.matinfo.find(mat_token)
    if mi then return mi.type, mi.index, true end
    mi = dfhack.matinfo.find("INORGANIC:IRON")
    if mi then return mi.type, mi.index, false end
    return 0, 0, false
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

-- Send the currently docked caravan on its way (Energy-Link dismiss): flip its
-- caravan_state to Leaving so DF retires it normally. Works on whatever caravan
-- is at the depot - the gorlak shop caravan or an Energy-Link-called one.
-- Returns true if a caravan was told to leave.
function M.depart_ap_caravan()
    local m = a_merchant()
    local civ = m and m.civ_id
    if not civ then return false end
    local n = 0
    for _, c in ipairs(df.global.plotinfo.caravans) do
        pcall(function()
            if c.entity == civ
                    and (c.trade_state == df.caravan_state.T_trade_state.AtDepot
                         or c.trade_state == df.caravan_state.T_trade_state.Approaching) then
                c.trade_state = df.caravan_state.T_trade_state.Leaving
                n = n + 1
            end
        end)
    end
    return n > 0
end

-- Create one AP good as a trader-flagged tool item at the depot.
-- Returns the item, or nil.
local function spawn_good(tool_id, mat_token, depot, owner_ent)
    local sub = tool_subtype(tool_id)
    if not sub then return nil end
    local merchant = a_merchant()
    local mt, mi, named = material_for(mat_token)
    if not named then M.unnamed_goods = (M.unnamed_goods or 0) + 1 end
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

-- ── Which goods this visit carries ───────────────────────────────────────────
-- The gorlaks trade their own wares; the AP goods are sprinkled in among them, a
-- rotating handful per visit rather than the whole unlocked shop at once. Sized
-- so every unlocked slot is offered within VISITS_TO_CYCLE visits however many
-- coffers you hold, which keeps rules.py's "reachable once you have the coffers"
-- promise honest - a slot can look random without ever being starved out.
local MIN_GOODS_PER_VISIT = 3
local VISITS_TO_CYCLE = 3

-- Fisher-Yates, matching caves.lua's shuffle.
local function shuffle(t)
    for i = #t, 2, -1 do
        local j = math.random(i)
        t[i], t[j] = t[j], t[i]
    end
    return t
end

-- Slots that could be offered right now: unlocked by coffer tier, not bought,
-- not awaiting the client's purchase confirmation.
local function eligible_slots(shop, pending, coffers)
    local out = {}
    for slot_str, e in pairs(shop) do
        local tier = math.max(1, math.min(5, tonumber(e.tier) or 1))
        if tier <= coffers and (tonumber(e.bought) or 0) == 0 and not pending[slot_str] then
            out[#out + 1] = slot_str
        end
    end
    table.sort(out, function(a, b) return tonumber(a) < tonumber(b) end)
    return out
end

-- This visit's goods, drawn from a persisted shuffled rotation: the pick looks
-- random, but the queue is only refilled once it empties, so every eligible slot
-- comes up before any repeats.
local function choose_visit_slots(shop, pending, coffers)
    local elig = eligible_slots(shop, pending, coffers)
    if #elig == 0 then return {} end
    local is_elig = {}
    for _, s in ipairs(elig) do is_elig[s] = true end
    local want = math.max(MIN_GOODS_PER_VISIT, math.ceil(#elig / VISITS_TO_CYCLE))

    local queue = decode(ps("shop_offer_queue"), {})
    local picked, seen, refills = {}, {}, 0
    while #picked < want and refills < 2 do
        if #queue == 0 then
            -- Cycle finished: reshuffle whatever is still eligible and unpicked.
            local rest = {}
            for _, s in ipairs(elig) do
                if not seen[s] then rest[#rest + 1] = s end
            end
            if #rest == 0 then break end
            queue = shuffle(rest)
            refills = refills + 1
        end
        local s = table.remove(queue, 1)
        -- Stale queue entries (bought or pending since it was built) just fall out.
        if is_elig[s] and not seen[s] then
            seen[s] = true
            picked[#picked + 1] = s
        end
    end
    pset("shop_offer_queue", json.encode(queue))
    return picked
end

-- Inject this visit's AP goods onto the docked caravan, alongside its own wares.
function M.inject_ap_goods()
    if not M.caravan_docked() then return 0 end
    if not is_ap_caravan() then return 0 end   -- AP goods only on the gorlak caravan
    local depot = find_depot()
    local owner_ent = caravan_owner_entity(depot)
    M.unnamed_goods = 0
    local shop = decode(ps("shop"), {})
    local pending = decode(ps("shop_pending"), {})
    local injected = decode(ps("ap_caravan_items"), {})   -- item_id(str) -> slot
    local coffers = tonumber(ps("unlock/wealth_coffers")) or 0

    -- Chosen once, when the caravan docks, and held until it leaves
    -- (clear_ap_goods drops the selection). An empty pick is re-tried each tick,
    -- so a coffer arriving mid-visit puts goods out straight away.
    local visit = decode(ps("shop_visit_slots"), {})
    if #visit == 0 then
        visit = choose_visit_slots(shop, pending, coffers)
        pset("shop_visit_slots", json.encode(visit))
    end

    -- which slots already have a live injected item?
    local live = {}
    for _, slot in pairs(injected) do live[tostring(slot)] = true end

    local n = 0
    for _, slot_str in ipairs(visit) do
        local e = shop[slot_str]
        -- shared per-tier tool (grouping header) + per-slot material (the name),
        -- matching apraws.py's ITEM_TOOL_AP_TIER<n> and INORGANIC:AP_SHOP_<slot>.
        local tier = e and math.max(1, math.min(5, tonumber(e.tier) or 1))
        local tool = tier and ("ITEM_TOOL_AP_TIER" .. tier)
        local mat = "INORGANIC:AP_SHOP_" .. slot_str
        if e and tool_subtype(tool) and (tonumber(e.bought) or 0) == 0
                and not pending[slot_str] and not live[slot_str] then
            local it = spawn_good(tool, mat, depot, owner_ent)
            if it then
                injected[tostring(it.id)] = tonumber(slot_str)
                n = n + 1
            end
        end
    end
    pset("ap_caravan_items", json.encode(injected))
    if M.unnamed_goods > 0 then warn_missing_raws(M.unnamed_goods) end
    return n
end

-- True while a merchant is carrying the item, i.e. the caravan is packing it back
-- onto the wagons. Not a purchase. A dwarf hauling a bought good also has a
-- holder, so the holder must specifically be a merchant.
local function held_by_merchant(it)
    local u
    pcall(function() u = dfhack.items.getHolderUnit(it) end)
    if not u then return false end
    local m = false
    pcall(function() m = u.flags1.merchant end)
    return m == true
end

-- Detect AP goods the player actually traded for, and queue those purchases for
-- the AP client. Call from the poll loop.
--
-- A good counts as bought ONLY when it is still on the map, its trader flag is
-- cleared, and no merchant is holding it. Every other state means the caravan
-- still owns it.
--
-- In particular a *missing* item is NOT a purchase. Merchants stay in
-- units.active while they pack up and walk off, so caravan_docked() is still true
-- during departure and this runs while DF removes the goods it is taking home.
-- Treating "item gone" as "traded" fired location checks for goods the player
-- never bought (and could not afford), permanently consuming those slots.
function M.detect_ap_trades()
    local injected = decode(ps("ap_caravan_items"), {})
    if not next(injected) then return 0 end
    local pending = decode(ps("shop_pending"), {})
    local queue = decode(ps("shop_buy"), {})
    local n, dropped = 0, 0
    for id_str, slot in pairs(injected) do
        local it = df.item.find(tonumber(id_str))
        if not it then
            -- Left with the caravan. Stop tracking it; the slot stays unbought
            -- and comes back around on a later visit via the rotation.
            injected[id_str] = nil
            dropped = dropped + 1
        else
            -- Default true so a failed read never reads as a purchase.
            local tr = true
            pcall(function() tr = it.flags.trader end)
            if not tr and not held_by_merchant(it) then
                pending[tostring(slot)] = true
                queue[#queue + 1] = slot
                injected[id_str] = nil
                n = n + 1
            end
        end
    end
    if n > 0 or dropped > 0 then
        pset("ap_caravan_items", json.encode(injected))
    end
    if n > 0 then
        pset("shop_pending", json.encode(pending))
        pset("shop_buy", json.encode(queue))
    end
    return n
end

-- On caravan departure, remove any AP goods the player did not buy so they never
-- linger in the fort, and clear the injected-item record.
-- Safe to call every tick while no caravan is docked: it returns immediately once
-- there is nothing on the books. Level-triggered on purpose - the old edge-
-- triggered call (a docked->undocked transition held in a Lua local) was skipped
-- whenever the script reloaded across a departure, stranding entries that the
-- NEXT caravan's detect pass then misread as purchases a year later.
function M.clear_ap_goods()
    local injected = decode(ps("ap_caravan_items"), {})
    local visit = decode(ps("shop_visit_slots"), {})
    if not next(injected) and not next(visit) then return 0 end

    local remaining, n = {}, 0
    for id_str, slot in pairs(injected) do
        local it = df.item.find(tonumber(id_str))
        if it then
            local tr = false
            pcall(function() tr = it.flags.trader end)
            if tr then
                pcall(function() dfhack.items.remove(it) end)
                -- items.remove is a no-op while the game is paused. Keep anything
                -- that did not actually go on the books so a later tick retries,
                -- rather than forgetting it and leaving it in the fort forever.
                local gone = false
                pcall(function()
                    local still = df.item.find(tonumber(id_str))
                    gone = (still == nil) or (still.flags.garbage_collect == true)
                end)
                if gone then n = n + 1 else remaining[id_str] = slot end
            end
        end
    end
    pset("ap_caravan_items", json.encode(remaining))
    -- Next caravan draws a fresh selection from the rotation.
    pset("shop_visit_slots", json.encode({}))
    return n
end

for k, v in pairs(M) do _ENV[k] = v end
return M
