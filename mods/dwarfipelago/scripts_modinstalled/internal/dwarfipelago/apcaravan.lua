--@ module = true
-- Native Archipelago caravan: put the AP shop goods on a docked caravan as real
-- tool items, so DF's own trade screen lists them, then grant the AP purchase
-- when the player trades for one. The raws ship placeholder materials
-- (apraws.py); this module writes each slot's real name and price into them.
--
-- Data it reads/writes (dfhack persistent world data):
--   dwarfipelago/shop            {slot: {item,player,price,tier,bought}}  (AP client)
--   (goods are ITEM_TOOL_AP_TIER<tier> of material INORGANIC:AP_SHOP_<slot>)
--   dwarfipelago/ap_caravan_items {item_id: slot}   injected items, this module
--   dwarfipelago/ap_thief_items   {item_id: slot}   goods awaiting a thief's corpse
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
-- Each slot is an ITEM_TOOL_AP_TIER<tier> of INORGANIC:AP_SHOP_<slot>, whose
-- material carries the good's name and price. Writing those at runtime is what
-- makes the shop work in any world built with the mod, scouted or not.

-- DF values a tool as (itemdef VALUE) x (material MATERIAL_VALUE); the AP tier
-- tools carry VALUE:100 (apraws.TOOL_VALUE).
local TOOL_VALUE = 100

-- A shop slot's material, or nil if this world's raws predate them. matinfo.find
-- is authoritative and caches no index, so a save reload cannot misaim a write
-- (world.raws.inorganics is a struct whose list is .all - indexing it is a trap).
local function slot_material(slot_str)
    local mi = dfhack.matinfo.find("INORGANIC:AP_SHOP_" .. slot_str)
    return mi and mi.material or nil
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

-- Write this seed's names and prices into the slot materials. In-memory only, so
-- it re-applies from the poll loop after each load; compare-then-write makes it a
-- no-op once applied. Returns the number of fields changed.
function M.apply_shop_materials()
    local shop = decode(ps("shop"), {})
    if not next(shop) then return 0 end
    local changed, missing = 0, 0
    for slot_str, e in pairs(shop) do
        local mat = slot_material(slot_str)
        if not mat then
            missing = missing + 1
        else
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

-- Any civ's merchant, for "is a caravan here at all".
local function a_merchant()
    for _, u in ipairs(df.global.world.units.active) do
        local m = false
        pcall(function() m = u.flags1.merchant end)
        if m and dfhack.units.isAlive(u) then return u end
    end
    return nil
end

-- The gorlak caravan's merchant (nil if absent); its civ_id owns the goods via
-- ENTITY_ITEMOWNER. Not units.active's first merchant: that pick is arbitrary.
local function ap_merchant()
    for _, u in ipairs(df.global.world.units.active) do
        local ok = false
        pcall(function() ok = u.flags1.merchant and u.civ_id >= 0 end)
        if ok and dfhack.units.isAlive(u) then
            local code
            pcall(function() code = df.historical_entity.find(u.civ_id).entity_raw.code end)
            if code == "ARCHIPELAGO" then return u end
        end
    end
    return nil
end

-- Resolve a material token to type/index, falling back to iron. Third return is
-- false on fallback: this world's raws predate the shop, so the good is nameless.
local function material_for(mat_token)
    local mi = dfhack.matinfo.find(mat_token)
    if mi then return mi.type, mi.index, true end
    mi = dfhack.matinfo.find("INORGANIC:IRON")
    if mi then return mi.type, mi.index, false end
    return 0, 0, false
end

-- Any civ's caravan at a depot; drives the panel's "[Caravan docked]" status.
function M.caravan_docked()
    return find_depot() ~= nil and a_merchant() ~= nil
end

-- The gorlak caravan specifically, even when other civs share the depot. AP
-- goods go only on it; dwarf/elf/human caravans are left untouched.
function M.ap_caravan_docked()
    return find_depot() ~= nil and ap_merchant() ~= nil
end

-- Energy-Link dismiss: flip the docked caravan's state to Leaving so DF retires
-- it. Deliberately any caravan, gorlak or Energy-Link-called. True if one left.
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

-- Create one AP good as a trader-flagged tool item at the depot; nil on failure.
-- Only called when there is real work to do, never per poll tick.
local function spawn_good(tool_id, mat_token, depot, merchant, owner_ent)
    local sub = tool_subtype(tool_id)
    if not sub then return nil end
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
-- A rotating handful per visit, not the whole unlocked shop. Sized so every slot
-- is offered within VISITS_TO_CYCLE visits, keeping rules.py's "reachable once
-- you have the coffers" honest - random-looking, but never starved out.
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

-- This visit's goods, from a persisted shuffled rotation. The queue refills only
-- once empty, so every eligible slot comes up before any repeats.
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
    local depot = find_depot()
    local merchant = depot and ap_merchant()
    if not merchant then return 0 end   -- the gorlak caravan is not here
    local owner_ent = merchant.civ_id
    M.unnamed_goods = 0
    local shop = decode(ps("shop"), {})
    local pending = decode(ps("shop_pending"), {})
    local injected = decode(ps("ap_caravan_items"), {})   -- item_id(str) -> slot
    local coffers = tonumber(ps("unlock/wealth_coffers")) or 0

    -- Chosen once per visit and held until it leaves. An empty pick retries each
    -- tick, so a coffer arriving mid-visit puts goods out at once.
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
            local it = spawn_good(tool, mat, depot, merchant, owner_ent)
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

-- Who holds the item, or nil: "merchant" (caravan packing up, not a purchase),
-- "citizen" (ours, hauling a purchase), or "other" - a thief, e.g. a langur.
local function holder_of(it)
    local u
    pcall(function() u = dfhack.items.getHolderUnit(it) end)
    if not u then return nil, nil end
    local m = false
    pcall(function() m = u.flags1.merchant end)
    if m then return "merchant", u end
    local c = false
    pcall(function() c = dfhack.units.isCitizen(u) end)
    return (c and "citizen" or "other"), u
end

-- Kill wildlife that steals an AP good so it can be recovered; false writes it off.
local KILL_THIEVES = true

-- Wildlife only: tame animals and non-animal thieves (a kobold) are spared and
-- written off instead. Pack animals are merchant-flagged, so never reach this.
local function is_wild_animal(u)
    local animal, tame = false, true
    pcall(function() animal = dfhack.units.isAnimal(u) end)
    pcall(function() tame = dfhack.units.isTame(u) end)
    return animal and not tame
end

-- dfhack.units.kill is absent on older builds; zeroing blood bleeds out instead.
-- The death is async, so reap_thief_goods collects the good once the body drops it.
local function strike_down(u)
    local dead = false
    pcall(function() dead = dfhack.units.isKilled(u) end)
    if dead then return true end
    return pcall(function()
        if dfhack.units.kill then dfhack.units.kill(u) else u.body.blood_count = 0 end
    end)
end

-- Queue the purchases the player traded for. Bought means ONLY: still on the map,
-- trader cleared, no merchant holding it. A *missing* item is not a purchase -
-- merchants linger in units.active while packing, and counting those fired checks.
function M.detect_ap_trades()
    local injected = decode(ps("ap_caravan_items"), {})
    if not next(injected) then return 0 end
    local pending = decode(ps("shop_pending"), {})
    local queue = decode(ps("shop_buy"), {})
    local thieved = decode(ps("ap_thief_items"), {})
    local n, dropped, stolen, killed = 0, 0, 0, 0
    for id_str, slot in pairs(injected) do
        local it = df.item.find(tonumber(id_str))
        if not it then
            -- Left with the caravan. Stop tracking it; the slot stays unbought
            -- and comes back around on a later visit via the rotation.
            injected[id_str] = nil
            dropped = dropped + 1
        else
            local kind, holder = holder_of(it)
            if kind == "other" then
                -- A thief has it: not a purchase, and untracking it here means no
                -- later pass can remove it out from under the unit.
                injected[id_str] = nil
                if KILL_THIEVES and is_wild_animal(holder) and strike_down(holder) then
                    -- The reaper removes it once the corpse drops it.
                    thieved[id_str] = slot
                    killed = killed + 1
                else
                    stolen = stolen + 1
                end
            else
                -- Default true so a failed read never reads as a purchase.
                local tr = true
                pcall(function() tr = it.flags.trader end)
                if not tr and kind ~= "merchant" then
                    pending[tostring(slot)] = true
                    queue[#queue + 1] = slot
                    injected[id_str] = nil
                    n = n + 1
                end
            end
        end
    end
    if n > 0 or dropped > 0 or stolen > 0 or killed > 0 then
        pset("ap_caravan_items", json.encode(injected))
    end
    if killed > 0 then
        pset("ap_thief_items", json.encode(thieved))
        log.info(("Struck down %d thieving animal(s) carrying AP shop goods."):format(killed))
        pcall(function()
            dfhack.gui.showAnnouncement(
                "[AP] A thieving creature was struck down making off with Archipelago "
                .. "merchandise.", COLOR_YELLOW, true)
        end)
    end
    if stolen > 0 then
        log.info(("%d AP shop good(s) were carried off and written off; their slots stay "):format(stolen)
            .. "unbought and come back around on a later visit.")
    end
    if n > 0 then
        pset("shop_pending", json.encode(pending))
        pset("shop_buy", json.encode(queue))
    end
    return n
end

-- Remove a struck-down thief's loot, but only once it is out of the corpse's
-- inventory: pulling an item out of a unit is what this module must never do.
function M.reap_thief_goods()
    local doomed = decode(ps("ap_thief_items"), {})
    if not next(doomed) then return 0 end
    local remaining, n = {}, 0
    for id_str, slot in pairs(doomed) do
        local it = df.item.find(tonumber(id_str))
        if it then
            if holder_of(it) then
                remaining[id_str] = slot   -- still being carried; retry next tick
            else
                pcall(function() dfhack.items.remove(it) end)
                -- items.remove no-ops while paused; keep it and retry later.
                local gone = false
                pcall(function()
                    local still = df.item.find(tonumber(id_str))
                    gone = (still == nil) or (still.flags.garbage_collect == true)
                end)
                if gone then n = n + 1 else remaining[id_str] = slot end
            end
        end
    end
    pset("ap_thief_items", json.encode(remaining))
    return n
end

-- On departure, remove unbought AP goods so they never linger in the fort. Safe
-- every tick; level-triggered on purpose, since an edge held in a Lua local was
-- skipped whenever the script reloaded across a departure, stranding entries.
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
            if tr and holder_of(it) then
                -- Carried by someone: never remove from an inventory. Dropping the
                -- trader flag takes it off the trade screen and untracks it.
                pcall(function() it.flags.trader = false end)
            elseif tr then
                pcall(function() dfhack.items.remove(it) end)
                -- items.remove no-ops while paused; keep it and retry later rather
                -- than forgetting it and leaving it in the fort forever.
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
