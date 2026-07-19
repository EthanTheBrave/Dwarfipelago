--@ module = true
-- Location check detection for Dwarfipelago.
-- Each function returns true if the condition is currently met in the fortress.
-- The AP location IDs must match locations.py (BASE_ID = 37370000).

local M = {}

-- ── Noble position helper ─────────────────────────────────────────────────────
-- Uses dfhack.units.getUnitsByNobleRole(code) which is available in DFHack 0.47+
-- and all DF50 builds. Returns true if at least one living unit holds the role.

local function has_noble_role(code)
    local ok, units = pcall(dfhack.units.getUnitsByNobleRole, code)
    return ok and units ~= nil and #units > 0
end

-- ── Room milestones ──────────────────────────────────────────────────────────

-- Quality tier (0-7) from getRoomDescription's exact return string.
-- Tiers map to DF room value thresholds: 0, 100, 250, 500, 1000, 1500, 2500, 10000.
local ROOM_TIER = {
    ["Meager Quarters"]       = 0, ["Modest Quarters"]       = 1,
    ["Quarters"]              = 2, ["Decent Quarters"]       = 3,
    ["Fine Quarters"]         = 4, ["Great Bedroom"]         = 5,
    ["Grand Bedroom"]         = 6, ["Royal Bedroom"]         = 7,

    ["Meager Office"]         = 0, ["Modest Office"]         = 1,
    ["Office"]                = 2, ["Decent Office"]         = 3,
    ["Splendid Office"]       = 4, ["Throne Room"]           = 5,
    ["Opulent Throne Room"]   = 6, ["Royal Throne Room"]     = 7,

    ["Meager Dining Room"]    = 0, ["Modest Dining Room"]    = 1,
    ["Dining Room"]           = 2, ["Decent Dining Room"]    = 3,
    ["Fine Dining Room"]      = 4, ["Great Dining Room"]     = 5,
    ["Grand Dining Room"]     = 6, ["Royal Dining Room"]     = 7,

    ["Grave"]                     = 0, ["Servant's Burial Chamber"] = 1,
    ["Burial Chamber"]            = 2, ["Tomb"]                     = 3,
    ["Fine Tomb"]                 = 4, ["Mausoleum"]                = 5,
    ["Grand Mausoleum"]           = 6, ["Royal Mausoleum"]          = 7,
}

local function zone_quality_rank(zone)
    local desc = ""
    pcall(function() desc = dfhack.buildings.getRoomDescription(zone) or "" end)
    return ROOM_TIER[desc] or -1
end

-- True if at least one Civzone of the given df.civzone_type exists.
local function has_zone_type(zone_type)
    local found = false
    pcall(function()
        for _, z in ipairs(df.global.world.buildings.all) do
            if not found then
                local ok, t = pcall(function() return z:getType() end)
                if ok and t == df.building_type.Civzone then
                    local ok2, st = pcall(function() return z:getSubtype() end)
                    if ok2 and st == zone_type then found = true end
                end
            end
        end
    end)
    return found
end

-- Best quality tier (0-7) reached by EACH quality-rated room type, as a table
-- keyed by df.civzone_type (Bedroom/Office/DiningHall/Tomb). -1 = no room of
-- that type yet. Computed in a single buildings.all pass and memoized per frame,
-- so the 20 per-room-tier checks that read it share one scan instead of 20.
local _room_q_cache, _room_q_frame = nil, -1
local function room_qualities()
    local frame = df.global.world.frame_counter or 0
    if _room_q_cache and _room_q_frame == frame then return _room_q_cache end
    local ct = df.civzone_type
    local q = { [ct.Bedroom] = -1, [ct.Office] = -1, [ct.DiningHall] = -1, [ct.Tomb] = -1 }
    pcall(function()
        for _, z in ipairs(df.global.world.buildings.all) do
            local ok, t = pcall(function() return z:getType() end)
            if ok and t == df.building_type.Civzone then
                local ok2, st = pcall(function() return z:getSubtype() end)
                if ok2 and q[st] ~= nil then
                    local r = zone_quality_rank(z)
                    if r > q[st] then q[st] = r end
                end
            end
        end
    end)
    _room_q_cache, _room_q_frame = q, frame
    return q
end

-- Best quality tier reached by a single room type (-1 if none of that type).
local function room_quality(zone_type)
    return room_qualities()[zone_type] or -1
end

-- True if any Civzone is assigned to a location whose abstract building passes
-- the given is_instance check (e.g. df.abstract_building_templest:is_instance).
local function has_location_type(check_fn)
    local found = false
    pcall(function()
        local site = dfhack.world.getCurrentSite()
        if not site then return end
        for _, z in ipairs(df.global.world.buildings.all) do
            if found then return end
            local ok, t = pcall(function() return z:getType() end)
            if ok and t == df.building_type.Civzone then
                local loc_id = -1
                pcall(function() loc_id = z.location_id end)
                if loc_id and loc_id >= 0 then
                    pcall(function()
                        for _, bld in ipairs(site.buildings) do
                            if bld.id == loc_id and check_fn(bld) then
                                found = true; break
                            end
                        end
                    end)
                end
            end
        end
    end)
    return found
end

-- Highest location_tier DF itself has already computed for any location
-- matching check_fn (e.g. abstract_building_templest/guildhallst instances).
-- Reads the game's own tracked tier/value (abstract_building_contents.location_tier
-- / .location_value, confirmed live via dfhack-run) instead of re-deriving it
-- from our own item scan - that previously drifted from what the in-game UI
-- shows, confusing players about when "First Temple"/"Temple Complex" should
-- fire. DF tiers: 0 = base (shrine / meeting place), 1 = mid (temple /
-- guildhall), 2 = top (temple complex / grand guildhall).
local function best_location_tier(check_fn)
    local best = -1
    pcall(function()
        local site = dfhack.world.getCurrentSite()
        if not site then return end
        for _, bld in ipairs(site.buildings) do
            if check_fn(bld) then
                local ok, tier = pcall(function() return bld.contents.location_tier end)
                if ok and tier and tier > best then best = tier end
            end
        end
    end)
    return best
end

-- Highest location_value DF has computed for any location matching check_fn -
-- the same number the in-game UI shows. Used for the panel's progress display
-- (best_location_tier above drives the actual AP check firing).
local function best_location_value(check_fn)
    local best = 0
    pcall(function()
        local site = dfhack.world.getCurrentSite()
        if not site then return end
        for _, bld in ipairs(site.buildings) do
            if check_fn(bld) then
                local ok, value = pcall(function() return bld.contents.location_value end)
                if ok and value and value > best then best = value end
            end
        end
    end)
    return best
end

-- ── Wealth helpers (kept for the legendary_wealth goal and panel display) ────

-- Returns current total fortress wealth (items + buildings + stocks).
-- DF 50+ (Steam / 2022+) renamed df.global.ui → df.global.plotinfo.
-- We try plotinfo first so both versions are supported.
-- DF50 stores fortress wealth as a STRUCT (plotinfo.tasks.wealth) whose .total is
-- the created-wealth figure shown in the fort status; older builds exposed it as a
-- plain number. Handle both, and fall back to a few field names.
local function fortress_wealth()
    for _, base in ipairs({ "plotinfo", "ui" }) do
        local w
        pcall(function() w = df.global[base].tasks.wealth end)
        if type(w) == "number" then return w end
        if w ~= nil then
            for _, f in ipairs({ "total", "created" }) do
                local v
                pcall(function() v = w[f] end)
                if type(v) == "number" then return v end
            end
        end
    end
    return 0
end

-- True if a unit is carrying the item, directly or nested inside a container it
-- holds (e.g. coins in a hauler's bag). Use this instead of item.flags.in_inventory,
-- which is also set for items in your own bins/coffers and wrongly excludes them.
local function held_by_unit(item)
    local it = item
    while it do
        if dfhack.items.getHolderUnit(it) then return true end
        it = dfhack.items.getContainer(it)
    end
    return false
end

-- Value of one coin/gem item, shared by the live treasury scan below and the
-- created-wealth counter in dwarfipelago.lua. A coin stack is worth 10 ×
-- material_value for a full 500 stack, i.e. each coin is material_value × 10 /
-- 500; a cut gem's base value is 20 × material_value (DF's cut-gem base value
-- of 20, per https://dwarffortresswiki.org/index.php/Value).
local function item_wealth_value(item, itype)
    local ok, mat = pcall(dfhack.matinfo.decode, item.mat_type, item.mat_index)
    local mat_value = 1
    if ok and mat and mat.material then
        mat_value = mat.material.material_value or 1
    end
    local stack = item.stack_size or 1
    if itype == df.item_type.COIN then
        return stack * mat_value * 10 / 500
    else
        return stack * mat_value * 20
    end
end

-- Returns the combined value of all minted coins (COIN) and cut gems (SMALLGEM)
-- currently in fortress stocks - not carried by any unit, not belonging to traders.
-- Both item types require AP-gated blueprints (Screw Press and Jeweler's Workshop)
-- and their material values vary widely, keeping embark-site luck meaningful.
local function treasury_wealth()
    local total = 0
    for _, item in ipairs(df.global.world.items.all) do
        local itype = item:getType()
        if (itype == df.item_type.COIN or itype == df.item_type.SMALLGEM)
                and not item.flags.trader
                and not held_by_unit(item) then
            total = total + item_wealth_value(item, itype)
        end
    end
    return math.floor(total)
end

local KEY_TREASURY_CREATED = "dwarfipelago/treasury/created_value"

-- Total coin/gem value ever minted/cut, independent of what's since been spent
-- at the shop, traded away, or exported - monotonic, only ever increases.
-- Used for the Legendary Wealth goal and the wealth-tier milestones instead of
-- the live treasury_wealth() scan above, so spending at the shop no longer
-- undoes wealth progress.
function M.treasury_created_wealth()
    return tonumber(dfhack.persistent.getWorldDataString(KEY_TREASURY_CREATED)) or 0
end

-- Add a newly-created coin/gem item's value to the created-wealth counter.
-- If `cap` is given, the counter is clamped to it - used to pace progress
-- behind the player's current Merchant's Coffer tier without blocking minting
-- or gem cutting themselves (those keep working freely for shop currency).
-- Returns the counter's new value.
function M.add_treasury_created_wealth(item, itype, cap)
    local delta = item_wealth_value(item, itype)
    if delta <= 0 then return M.treasury_created_wealth() end
    local total = M.treasury_created_wealth() + delta
    if cap then total = math.min(total, cap) end
    dfhack.persistent.saveWorldDataString(KEY_TREASURY_CREATED, tostring(total))
    return total
end

-- ── Progression lock helpers ──────────────────────────────────────────────────
-- Read how many copies of a progressive unlock item have been received, or
-- whether a single-copy unlock has arrived.  Keys written by items.lua handlers.

local function unlock_count(key)
    return tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/unlock/" .. key)) or 0
end

local function unlock_flag(key)
    return dfhack.persistent.getWorldDataString("dwarfipelago/unlock/" .. key) == "1"
end

-- ── Fortress title helpers ────────────────────────────────────────────────────
-- Titles require population AND (created wealth OR exported wealth).
-- https://dwarffortresswiki.org/index.php/Fortress
-- Defined before M.checks because has_fortress_title() is called immediately
-- (not wrapped in a closure) when the check entries are constructed.

local function citizen_count()
    local count = 0
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
            count = count + 1
        end
    end
    return count
end

-- Exported wealth. Try the wealth struct's .exported field, then a few legacy
-- names. Falls back to 0 (the created-wealth path already covers the title gate).
local function exported_wealth()
    for _, base in ipairs({ "plotinfo", "ui" }) do
        local v
        pcall(function() v = df.global[base].tasks.wealth.exported end)
        if type(v) == "number" then return v end
        pcall(function() v = df.global[base].tasks.wealth_exported end)
        if type(v) == "number" then return v end
    end
    return 0
end

local function has_fortress_title(pop_req, created_req, exported_req, waves_req)
    waves_req = waves_req or 0
    return function()
        if unlock_count("immigration_waves") < waves_req then return false end
        if citizen_count() < pop_req then return false end
        return fortress_wealth() >= created_req or exported_wealth() >= exported_req
    end
end

M.checks = {
    -- Room type milestones - first time each zone type is designated.
    { id = 37370000, name = "First Bedroom",     fn = function() return has_zone_type(df.civzone_type.Bedroom)   end },
    { id = 37370001, name = "First Office",      fn = function() return has_zone_type(df.civzone_type.Office)    end },
    { id = 37370002, name = "First Tomb",        fn = function() return has_zone_type(df.civzone_type.Tomb)      end },
    { id = 37370004, name = "First Dining Hall", fn = function() return has_zone_type(df.civzone_type.DiningHall) end },
    -- Temple tiers: DF's own location_tier - 0 = shrine, 1 = temple, 2 = temple complex.
    { id = 37370003, name = "First Shrine",    fn = function() return has_location_type(function(b) return df.abstract_building_templest:is_instance(b) end) end },
    { id = 37370010, name = "First Temple",    fn = function() return best_location_tier(function(b) return df.abstract_building_templest:is_instance(b) end) >= 1 end },
    { id = 37370011, name = "Temple Complex",  fn = function() return best_location_tier(function(b) return df.abstract_building_templest:is_instance(b) end) >= 2 end },

    -- Guildhall tiers: 0 = meeting place, 1 = guildhall, 2 = grand guildhall.
    { id = 37370012, name = "First Guildhall", fn = function() return best_location_tier(function(b) return df.abstract_building_guildhallst:is_instance(b) end) >= 1 end },
    { id = 37370013, name = "Grand Guildhall", fn = function() return best_location_tier(function(b) return df.abstract_building_guildhallst:is_instance(b) end) >= 2 end },

    -- Per-room-type quality milestones - each room type reaching tiers 3-7 (DF
    -- value thresholds 500 / 1000 / 1500 / 2500 / 10000). Names are DF's own room
    -- descriptions per tier. Ids 14-33 (the old single-best 5-9 are retired).
    { id = 37370014, name = "Decent Quarters",     fn = function() return room_quality(df.civzone_type.Bedroom)    >= 3 end },
    { id = 37370015, name = "Fine Quarters",       fn = function() return room_quality(df.civzone_type.Bedroom)    >= 4 end },
    { id = 37370016, name = "Great Bedroom",       fn = function() return room_quality(df.civzone_type.Bedroom)    >= 5 end },
    { id = 37370017, name = "Grand Bedroom",       fn = function() return room_quality(df.civzone_type.Bedroom)    >= 6 end },
    { id = 37370018, name = "Royal Bedroom",       fn = function() return room_quality(df.civzone_type.Bedroom)    >= 7 end },

    { id = 37370019, name = "Decent Office",       fn = function() return room_quality(df.civzone_type.Office)     >= 3 end },
    { id = 37370020, name = "Splendid Office",     fn = function() return room_quality(df.civzone_type.Office)     >= 4 end },
    { id = 37370021, name = "Throne Room",         fn = function() return room_quality(df.civzone_type.Office)     >= 5 end },
    { id = 37370022, name = "Opulent Throne Room", fn = function() return room_quality(df.civzone_type.Office)     >= 6 end },
    { id = 37370023, name = "Royal Throne Room",   fn = function() return room_quality(df.civzone_type.Office)     >= 7 end },

    { id = 37370024, name = "Decent Dining Room",  fn = function() return room_quality(df.civzone_type.DiningHall) >= 3 end },
    { id = 37370025, name = "Fine Dining Room",    fn = function() return room_quality(df.civzone_type.DiningHall) >= 4 end },
    { id = 37370026, name = "Great Dining Room",   fn = function() return room_quality(df.civzone_type.DiningHall) >= 5 end },
    { id = 37370027, name = "Grand Dining Room",   fn = function() return room_quality(df.civzone_type.DiningHall) >= 6 end },
    { id = 37370028, name = "Royal Dining Room",   fn = function() return room_quality(df.civzone_type.DiningHall) >= 7 end },

    { id = 37370029, name = "Tomb",                fn = function() return room_quality(df.civzone_type.Tomb)       >= 3 end },
    { id = 37370030, name = "Fine Tomb",           fn = function() return room_quality(df.civzone_type.Tomb)       >= 4 end },
    { id = 37370031, name = "Mausoleum",           fn = function() return room_quality(df.civzone_type.Tomb)       >= 5 end },
    { id = 37370032, name = "Grand Mausoleum",     fn = function() return room_quality(df.civzone_type.Tomb)       >= 6 end },
    { id = 37370033, name = "Royal Mausoleum",     fn = function() return room_quality(df.civzone_type.Tomb)       >= 7 end },

    -- First production milestones
    -- These are tracked via a persistent counter set by the eventful job hook in main.lua.
    -- The checks here read that counter from state.
    { id = 37370100, name = "First Crafted Item",      fn = function() return M.production_flag("crafted_item")    end },
    { id = 37370101, name = "First Weapon Forged",     fn = function() return M.production_flag("weapon")         end },
    { id = 37370102, name = "First Armor Crafted",     fn = function() return M.production_flag("armor")          end },
    { id = 37370103, name = "First Furniture Made",    fn = function() return M.production_flag("furniture")      end },
    { id = 37370104, name = "First Prepared Meal",     fn = function() return M.production_flag("meal")           end },
    { id = 37370105, name = "First Brew Complete",     fn = function() return M.production_flag("brew")           end },
    { id = 37370106, name = "First Metal Bar Smelted", fn = function() return M.production_flag("metal_bar")      end },
    { id = 37370107, name = "First Block Cut",         fn = function() return M.production_flag("stone_block")    end },
    { id = 37370108, name = "First Cloth Woven",       fn = function() return M.production_flag("cloth")          end },
    { id = 37370109, name = "First Leather Tanned",    fn = function() return M.production_flag("leather")        end },
    { id = 37370110, name = "First Gem Cut",           fn = function() return M.production_flag("gem")            end },
    { id = 37370111, name = "First Mechanism Made",    fn = function() return M.production_flag("mechanism")      end },
    { id = 37370112, name = "First Trap Built",        fn = function() return M.production_flag("trap")           end },
    { id = 37370113, name = "First Cage Constructed",  fn = function() return M.production_flag("cage")           end },
    { id = 37370114, name = "First Barrel Made",       fn = function() return M.production_flag("barrel")         end },
    { id = 37370115, name = "First Chest Made",        fn = function() return M.production_flag("chest")          end },
    { id = 37370116, name = "First Table Made",        fn = function() return M.production_flag("table")          end },
    { id = 37370117, name = "First Bed Made",          fn = function() return M.production_flag("bed")            end },
    { id = 37370118, name = "First Anvil Made",        fn = function() return M.production_flag("anvil")          end },
    { id = 37370119, name = "First Millstone Made",    fn = function() return M.production_flag("millstone")      end },
    { id = 37370120, name = "First Minecart Made",     fn = function() return M.production_flag("minecart")       end },

    -- Trade / export milestones
    { id = 37370202, name = "Dwarven Caravan Visit",    fn = function() return M.trade_flag("dwarven_caravan")    end },
    { id = 37370203, name = "Elven Caravan Visit",      fn = function() return M.trade_flag("elven_caravan")      end },
    { id = 37370204, name = "Human Caravan Visit",      fn = function() return M.trade_flag("human_caravan")      end },
    { id = 37370205, name = "Outpost Liaison Meeting",  fn = function() return M.trade_flag("liaison_met")        end },
    { id = 37370206, name = "First Raid",               fn = function() return M.trade_flag("first_raid")         end },
    { id = 37370207, name = "First Artifact Recovery",  fn = function() return M.trade_flag("first_recovery")     end },
    { id = 37370208, name = "First Act of Diplomacy",   fn = function() return M.trade_flag("first_diplomacy")    end },

    -- Fortress status / noble appointments
    -- Position codes match vanilla DF entity_default.txt. KING covers both king
    -- and queen (DF stores a single position code with gendered display names).
    -- Baron/Count/Duke/Monarch checks additionally require the matching charter.
    { id = 37370300, name = "Mayor Elected",           fn = function() return has_noble_role("MAYOR") end },
    { id = 37370301, name = "Baron Appointed",         fn = function() return unlock_flag("baron_charter")       and has_noble_role("BARON") end },
    { id = 37370302, name = "Count Appointed",         fn = function() return unlock_flag("count_charter")       and has_noble_role("COUNT") end },
    { id = 37370303, name = "Duke Appointed",          fn = function() return unlock_flag("duke_charter")        and has_noble_role("DUKE")  end },
    { id = 37370304, name = "Monarch Takes Residence", fn = function()
        if not unlock_flag("monarch_invitation") then return false end
        return has_noble_role("KING") or has_noble_role("QUEEN")
    end },

    -- Fortress title milestones (population + created OR exported wealth)
    -- Each tier also requires the matching Immigration Wave count.
    { id = 37370400, name = "Hamlet Established",     fn = has_fortress_title(20,   5000,    500, 1) },
    { id = 37370401, name = "Village Established",    fn = has_fortress_title(50,  25000,   2500, 2) },
    { id = 37370402, name = "Town Established",       fn = has_fortress_title(80, 100000,  10000, 3) },
    { id = 37370403, name = "City Established",       fn = has_fortress_title(110, 200000, 20000, 4) },
    { id = 37370404, name = "Metropolis Established", fn = has_fortress_title(140, 300000, 30000, 5) },

    -- Mining: progress toward each cavern, as a percentage of the depth from the
    -- previous reference (surface, then each cavern ceiling) down to the next
    -- cavern's ceiling. The breach itself (100%) is the separate "... Cavern
    -- Breached" location below.
    { id = 37370700, name = "25% to the First Cavern",  fn = function() return M.cavern_progress(1) >= 25 end },
    { id = 37370701, name = "50% to the First Cavern",  fn = function() return M.cavern_progress(1) >= 50 end },
    { id = 37370702, name = "25% to the Second Cavern", fn = function() return M.cavern_progress(2) >= 25 end },
    { id = 37370703, name = "50% to the Second Cavern", fn = function() return M.cavern_progress(2) >= 50 end },
    { id = 37370704, name = "50% to the Third Cavern",  fn = function() return M.cavern_progress(3) >= 50 end },

    -- Mining: cumulative tiles excavated.
    { id = 37370710, name = "Excavator I (100 tiles)",     fn = function() return M.mining_count() >= 100   end },
    { id = 37370711, name = "Excavator II (500 tiles)",    fn = function() return M.mining_count() >= 500   end },
    { id = 37370712, name = "Excavator III (2,000 tiles)", fn = function() return M.mining_count() >= 2000  end },
    { id = 37370713, name = "Excavator IV (5,000 tiles)",  fn = function() return M.mining_count() >= 5000  end },
    { id = 37370714, name = "Excavator V (10,000 tiles)",  fn = function() return M.mining_count() >= 10000 end },

    -- Mining: cavern / magma sea / circus breaches (detected via map feature on dig jobs).
    { id = 37370720, name = "First Cavern Breached",  fn = function() return M.mining_flag("cavern1") end },
    { id = 37370721, name = "Second Cavern Breached", fn = function() return M.mining_flag("cavern2") end },
    { id = 37370722, name = "Third Cavern Breached",  fn = function() return M.mining_flag("cavern3") end },
    { id = 37370723, name = "Reached the Magma Sea",  fn = function() return M.mining_flag("magma")   end },
    { id = 37370724, name = "Welcome to the Circus",   fn = function() return M.mining_flag("circus")  end },

    -- Farming: cumulative harvested crops (PLANT items).
    { id = 37370730, name = "Harvest 50 Crops",    fn = function() return M.crops_harvested() >= 50   end },
    { id = 37370731, name = "Harvest 100 Crops",   fn = function() return M.crops_harvested() >= 100  end },
    { id = 37370732, name = "Harvest 250 Crops",   fn = function() return M.crops_harvested() >= 250  end },
    { id = 37370733, name = "Harvest 500 Crops",   fn = function() return M.crops_harvested() >= 500  end },
    { id = 37370734, name = "Harvest 1,000 Crops", fn = function() return M.crops_harvested() >= 1000 end },

    -- Infrastructure: wells and screw pumps (polled each tick once built).
    { id = 37370740, name = "Built a Well",  fn = function() return M.production_flag("well")       end },
    { id = 37370741, name = "Pumped Water",  fn = function() return M.production_flag("pump_water") end },
    { id = 37370742, name = "Pumped Magma",  fn = function() return M.production_flag("pump_magma") end },

    -- Biology / animals.
    -- "First Eggs Hatched" (37370750) disabled: hatch detection unreliable on DF v50.
    -- { id = 37370750, name = "First Eggs Hatched", fn = function() return M.production_flag("egg_hatched")     end },
    { id = 37370751, name = "Caged a Hostile Beast", fn = function() return M.production_flag("caged_hostile_beast") end },

    -- Deep / endgame.
    { id = 37370760, name = "Mined Adamantine", fn = function() return M.production_flag("adamantine")    end },
    { id = 37370761, name = "Sold an Artifact", fn = function() return M.production_flag("sold_artifact") end },

    -- Military / siege (Slay Megabeast goal only; goal 0). Same milestones gate
    -- War Readiness in dwarfipelago.lua.
    { id = 37370770, name = "Barracks Established",
      fn = function() return dfhack.persistent.getWorldDataString("dwarfipelago/goal") == "0"
                          and M.barracks_is_set_up() end },
    { id = 37370771, name = "Training Completed",
      fn = function() return dfhack.persistent.getWorldDataString("dwarfipelago/goal") == "0"
                          and M.training_completed() end },
}

-- ── Production flag helpers ───────────────────────────────────────────────────
-- Flags are set by the eventful job hook in main.lua and stored in world data.
-- Key format: "dwarfipelago/prod/<flag_name>"

function M.set_production_flag(flag)
    dfhack.persistent.saveWorldDataString("dwarfipelago/prod/" .. flag, "1")
end

function M.production_flag(flag)
    local val = dfhack.persistent.getWorldDataString("dwarfipelago/prod/" .. flag)
    return val == "1"
end

function M.set_trade_flag(flag)
    dfhack.persistent.saveWorldDataString("dwarfipelago/trade/" .. flag, "1")
end

function M.trade_flag(flag)
    local val = dfhack.persistent.getWorldDataString("dwarfipelago/trade/" .. flag)
    return val == "1"
end

function M.detect_mission_checks()
    local all_done = M.trade_flag("first_raid")
                 and M.trade_flag("first_recovery")
                 and M.trade_flag("first_diplomacy")
    if all_done then return end

    -- Messenger/contact dispatches don't create a squad - the controller exists
    -- standalone in army_controllers with entity_id == group_id. Iterating
    -- controllers directly catches both squad-based missions and lone messengers.
    local group_id        = df.global.plotinfo.group_id
    local SITE_INVASION   = df.army_controller_goal_type.SITE_INVASION
    local RECOVER_ARTIFACT = df.army_controller_goal_type.RECOVER_ARTIFACT
    local DIPLOMACY        = df.army_controller_goal_type.DIPLOMACY

    for _, ctrl in ipairs(df.global.world.army_controllers.all) do
        if ctrl.entity_id == group_id then
            local goal = ctrl.goal
            if goal == SITE_INVASION and not M.trade_flag("first_raid") then
                M.set_trade_flag("first_raid")
                print("[Dwarfipelago] First raid detected")
            elseif goal == RECOVER_ARTIFACT and not M.trade_flag("first_recovery") then
                M.set_trade_flag("first_recovery")
                print("[Dwarfipelago] First artifact recovery detected")
            elseif goal == DIPLOMACY and not M.trade_flag("first_diplomacy") then
                M.set_trade_flag("first_diplomacy")
                print("[Dwarfipelago] First diplomacy mission detected")
            end
        end
    end
end

-- ── Mining helpers ────────────────────────────────────────────────────────────
-- Mining state is written by the eventful job hook in dwarfipelago.lua:
--   dwarfipelago/mining/surface_z  - z-level of the embark surface (captured once)
--   dwarfipelago/mining/deepest_z  - lowest z any mining job has reached
--   dwarfipelago/mining/dig_count  - cumulative count of mining jobs completed

-- Levels dug below the surface (0 if not yet tracked or only dug upward).
function M.mining_depth()
    local surface = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/mining/surface_z"))
    local deepest = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/mining/deepest_z"))
    if not surface or not deepest then return 0 end
    local depth = surface - deepest
    return depth > 0 and depth or 0
end

-- Cumulative tiles excavated.
function M.mining_count()
    return tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/mining/dig_count")) or 0
end

-- Cavern/magma breach flags, set by the mining hook when a dig job lands in the
-- matching feature (dwarfipelago/mining/cavern1|cavern2|cavern3|magma).
function M.mining_flag(name)
    return dfhack.persistent.getWorldDataString("dwarfipelago/mining/" .. name) == "1"
end

-- ── Cavern approach progress ──────────────────────────────────────────────────
-- Ceilings cached by compute_cavern_ceilings() in dwarfipelago.lua. Higher z =
-- closer to the surface.
local CAVERN_CEIL_KEYS = { [1] = "cavern1", [2] = "cavern2", [3] = "cavern3" }

local function ceiling_z(key)
    return tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/mining/ceiling/" .. key))
end

local function surface_z()
    return tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/mining/surface_z"))
end

-- Segment start for cavern n: the surface for cavern 1, else the previous
-- cavern's ceiling (falling back toward the surface if one is absent).
local function segment_start_z(n)
    if n <= 1 then return surface_z() end
    for k = n - 1, 1, -1 do
        local z = ceiling_z(CAVERN_CEIL_KEYS[k])
        if z then return z end
    end
    return surface_z()
end

-- Percent (0-100) from the segment start down to cavern n's ceiling, by the
-- deepest mining job reached. 0 if data is missing or this segment isn't started.
function M.cavern_progress(n)
    local target = ceiling_z(CAVERN_CEIL_KEYS[n])
    local start  = segment_start_z(n)
    local deepest = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/mining/deepest_z"))
    if not target or not start or not deepest then return 0 end
    local span = start - target
    if span <= 0 then return 0 end
    local pct = (start - deepest) / span * 100
    if pct < 0 then return 0 end
    if pct > 100 then return 100 end
    return pct
end

-- Panel helper: the shallowest un-breached cavern with its % progress, z-levels
-- to its ceiling, and next progress check (25/50, nil when the breach is next).
-- Returns nil when caverns are unknown or all three are breached.
function M.cavern_approach()
    local deepest = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/mining/deepest_z"))
    for n = 1, 3 do
        if not M.mining_flag("cavern" .. n) then
            local target = ceiling_z(CAVERN_CEIL_KEYS[n])
            if not target then return nil end
            local pct = M.cavern_progress(n)
            local thresholds = (n == 3) and { 50 } or { 25, 50 }
            local next_pct
            for _, t in ipairs(thresholds) do
                if pct < t then next_pct = t; break end
            end
            return {
                cavern = n,
                pct = pct,
                levels_remaining = deepest and math.max(0, deepest - target) or nil,
                next_pct = next_pct,  -- nil => next milestone is the breach itself
            }
        end
    end
    return nil  -- all three caverns breached
end

-- ── Progressive mining-depth lock (read-only view for the panel) ──────────────
-- Enforced in dwarfipelago.lua; this mirrors its tier mapping for display.
local MINING_FLOOR_KEYS = { [0] = "cavern1", [1] = "cavern2", [2] = "cavern3", [3] = "magma" }
local MINING_TIER_NAMES = {
    [0] = "Cavern 1", [1] = "Cavern 2", [2] = "Cavern 3", [3] = "Magma Sea",
}

-- True when the Progressive Mining Depth feature is enabled for this slot.
function M.mining_depth_enabled()
    return dfhack.persistent.getWorldDataString("dwarfipelago/mining_depth") == "1"
end

-- Count of Progressive Mining Depth items received (unlock/mining_depth).
function M.mining_depth_unlocks()
    return tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/unlock/mining_depth")) or 0
end

-- Deepest minable z and limiting layer name, or nil, nil for no limit (feature
-- off, final tier, or ceilings unknown). Falls through to the next deeper layer.
function M.mining_depth_limit()
    if not M.mining_depth_enabled() then return nil, nil end
    local unlocks = M.mining_depth_unlocks()
    if not MINING_FLOOR_KEYS[unlocks] then return nil, nil end  -- final tier
    for tier = unlocks, 0, -1 do
        local ceil = tonumber(
            dfhack.persistent.getWorldDataString("dwarfipelago/mining/ceiling/" .. MINING_FLOOR_KEYS[tier]))
        if ceil then return ceil + 1, MINING_TIER_NAMES[tier] end
    end
    return nil, nil
end

-- Cumulative harvested crops (PLANT items), incremented by the onItemCreated hook.
function M.crops_harvested()
    return tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/farming/crop_count")) or 0
end

-- ── Job type → production flag mapping ───────────────────────────────────────
-- Called by main.lua's eventful job hook to classify completed jobs.
--
-- Job type enum names can vary between DF versions (Steam vs Classic, DF 47 vs
-- DF 50+).  Building the table with a helper that silently skips any name that
-- is nil in the running version avoids "table index is nil" errors at load time.

local JOB_TO_FLAG = {}
local function map(name, flag)
    local v = df.job_type[name]
    if v ~= nil then JOB_TO_FLAG[v] = flag end
end

-- Crafting - any Craftsdwarf's Workshop output counts as a "crafted item"
map("MakeCrafts",              "crafted_item")
map("CarveStatue",             "crafted_item")  -- pre-50 name
map("CarveFurniture",          "crafted_item")  -- DF 50+ name
map("MakeTotem",               "crafted_item")
map("MakeFigurine",            "crafted_item")
map("MakeAmulet",              "crafted_item")
map("MakeScepter",             "crafted_item")
map("MakeCrown",               "crafted_item")
map("MakeRing",                "crafted_item")
map("MakeEarring",             "crafted_item")
map("MakeBracelet",            "crafted_item")
map("MakeToy",                 "crafted_item")
map("MakeFlask",               "crafted_item")
map("MakeGoblet",              "crafted_item")
map("ConstructStatue",         "crafted_item")
-- Weapons / armor
map("MakeWeapon",              "weapon")
map("MakeAmmo",                "weapon")
map("MakeArmor",               "armor")
map("MakeHelm",                "armor")
map("MakeGloves",              "armor")
map("MakeBoots",               "armor")
map("MakePants",               "armor")
map("MakeShield",              "armor")
-- Furniture - both Make* (pre-50/Classic) and Construct* (DF50+ Steam) variants
map("MakeTable",               "table")
map("ConstructTable",          "table")
map("MakeChair",               "furniture")
map("ConstructThrone",         "furniture")   -- DF50+ name for chair
map("MakeChest",               "chest")
map("ConstructChest",          "chest")
map("MakeCabinet",             "furniture")
map("ConstructCabinet",        "furniture")
map("MakeBed",                 "bed")
map("ConstructBed",            "bed")
map("MakeDoor",                "furniture")
map("ConstructDoor",           "furniture")
map("MakeFloodgate",           "furniture")
map("ConstructFloodgate",      "furniture")
map("MakeBarrel",              "barrel")
map("MakeBucket",              "furniture")
map("MakeCage",                "cage")
map("MakeMechanism",           "mechanism")
map("ConstructMechanisms",     "mechanism")
-- Food / drink
map("PrepareMeal",             "meal")
map("BrewDrink",               "brew")
-- Materials
map("SmeltOre",                "metal_bar")
map("MeltMetalObject",         "metal_bar")
map("CutBlock",                "stone_block")
map("ConstructBlocks",         "stone_block")  -- DF50+ name for cutting blocks
map("WeaveCloth",              "cloth")
map("ProcessPlants",           "cloth")   -- also produces thread
map("TanHide",                 "leather")
map("CutGems",                 "gem")
map("CutGlass",                "gem")   -- cutting glass also makes a SMALLGEM (CUTGEM skill)
map("EncrustWithGems",         "gem")   -- was "EncrustedWithGems" (nil in DF v50; real name has no "ed")
-- Traps. DF v50 has no ConstructTrap job_type; arming a trap is one of the
-- Load*Trap jobs, and wiring a lever/pressure plate is LinkBuildingToTrigger.
map("ConstructTrap",           "trap")  -- kept for older DF; nil-skipped on v50
map("LoadCageTrap",            "trap")
map("LoadStoneTrap",           "trap")
map("LoadWeaponTrap",          "trap")
map("LinkBuildingToTrigger",   "trap")
-- Standalone production checks
map("ForgeAnvil",              "anvil")
map("ConstructMillstone",      "millstone")
map("MakeMillstone",           "millstone")   -- pre-50 name if it exists
map("MakeTool",                "TOOL_FIRST")  -- subtype dispatch below

-- Minecart subtype: MakeTool item_subtype 16
local TOOL_FIRST_FLAG = { [16] = "minecart" }

-- Some "production" jobs have no dedicated job_type in DF v50 - they complete as
-- CustomReaction jobs and are identified by reaction_name (this is the same way
-- the craft-count path resolves them via REACTION_SUBTYPE_FLAG, which is why the
-- craftsanity Alcohol checks already work). Map those reaction names to the
-- first-production flag so e.g. "First Brew Complete" fires too.
local REACTION_TO_PROD = {}
local function rprod(name, flag) REACTION_TO_PROD[name] = flag end
rprod("BREW_DRINK_FROM_PLANT",        "brew")
rprod("BREW_DRINK_FROM_PLANT_GROWTH", "brew")
rprod("TAN_A_HIDE",                   "leather")

function M.job_to_production_flag(job)
    if job and job.job_type then
        local flag = JOB_TO_FLAG[job.job_type]
        if flag == "TOOL_FIRST" then
            return TOOL_FIRST_FLAG[tonumber(job.item_subtype)]
        end
        if flag then return flag end
        -- Fall back to reaction-name matching for CustomReaction jobs.
        local rname = ""
        pcall(function() rname = job.reaction_name or "" end)
        if rname ~= "" then return REACTION_TO_PROD[rname] end
    end
    return nil
end

-- Expose wealth accessors so main.lua can use them without duplicating logic.
M.fortress_wealth  = fortress_wealth
M.treasury_wealth  = treasury_wealth
M.exported_wealth  = exported_wealth

-- Room accessors for the panel.
M.has_zone_type        = has_zone_type
M.room_quality         = room_quality
M.best_location_tier   = best_location_tier
M.best_location_value  = best_location_value

function M.has_temple_zone()
    return has_location_type(function(b) return df.abstract_building_templest:is_instance(b) end)
end

function M.has_guildhall_zone()
    return has_location_type(function(b) return df.abstract_building_guildhallst:is_instance(b) end)
end

-- Returns the description string of the best-quality room (e.g. "Grand Bedroom"), or "".
function M.best_room_description()
    local best_rank = -1
    local best_desc = ""
    pcall(function()
        local ct = df.civzone_type
        for _, z in ipairs(df.global.world.buildings.all) do
            local ok, t = pcall(function() return z:getType() end)
            if ok and t == df.building_type.Civzone then
                local ok2, st = pcall(function() return z:getSubtype() end)
                if ok2 and (st == ct.Bedroom or st == ct.Office
                         or st == ct.DiningHall or st == ct.Tomb) then
                    local desc = ""
                    pcall(function() desc = dfhack.buildings.getRoomDescription(z) or "" end)
                    local r = ROOM_TIER[desc] or -1
                    if r > best_rank then best_rank = r; best_desc = desc end
                end
            end
        end
    end)
    return best_desc
end

-- ── Job type → craft count flag mapping ──────────────────────────────────────
-- Separate from JOB_TO_FLAG: maps jobs to the specific AP option names used in
-- craftable_items and craftable_materials (lowercase, underscored).
-- The AP client writes these same strings into the dwarfipelago/craft_checks
-- config so Lua counts and AP thresholds use identical flag names.

local JOB_TO_CRAFT_FLAG = {}
local function cmap(name, flag)
    local v = df.job_type[name]
    if v ~= nil then JOB_TO_CRAFT_FLAG[v] = flag end
end

-- craftable_items
cmap("MakeTool",                "TOOL_SUBTYPE")
cmap("ConstructDoor",           "door")
cmap("MakeCage",                "cage")
cmap("ConstructBin",            "bin")
cmap("ConstructBlocks",         "blocks")
cmap("ConstructGrate",          "grate")
cmap("MakeTrapComponent",       "TRAP_SUBTYPE")
cmap("ConstructBed",            "beds")
cmap("MakeAnimalTrap",          "animal_trap")
cmap("ConstructArmorStand",     "armor_stand")
cmap("MakePedestal",            "pedestal")
cmap("MakeBucket",              "bucket")
cmap("MakeBarrel",              "barrel")
cmap("MakeShield",              "SHIELD_SUBTYPE")
cmap("ConstructCabinet",        "cabinet")
cmap("ConstructCoffin",         "burial_container")
cmap("ConstructThrone",         "chair")
cmap("ConstructChest",          "container")
cmap("ConstructCrutch",         "crutch")
cmap("ConstructFloodgate",      "floodgate")
cmap("ConstructGrate",          "grate")
cmap("ConstructHatchCover",     "hatch_cover")
cmap("MakePipeSection",         "pipe_section")
cmap("ConstructSplint",         "splint")
cmap("ConstructTable",          "table")
cmap("MakeWeapon",              "WEAPON_SUBTYPE")
cmap("ConstructWeaponRack",     "weapon_rack")
cmap("MakeAmmo",                "bolt")
cmap("ConstructMillstone",      "millstone")
cmap("ConstructQuern",          "quern")
cmap("ConstructSlab",           "slab")
cmap("ConstructStatue",         "statue")
cmap("ConstructMechanisms",     "mechanism")
cmap("ConstructTractionBench",  "traction_bench")
cmap("ConstructBoltThrowerParts", "bolt_thrower_parts")
cmap("MakeFigurine",            "figurine")
cmap("MakeAmulet",              "amulet")
cmap("MakeScepter",             "scepter")
cmap("MakeCrown",               "crown")
cmap("MakeRing",                "ring")
cmap("MakeEarring",             "earring")
cmap("MakeBracelet",            "bracelet")
cmap("MakeCrafts",              "crafts")
cmap("MakeFlask",               "liquid_container")
cmap("MakeGoblet",              "GOBLET_SUBTYPE")
cmap("MakeToy",                 "toy")
cmap("MakeTotem",               "totem")
cmap("MakeHelm",                "HELM_SUBTYPE")
cmap("ConstructBallistaParts",  "ballista_parts")
cmap("ConstructCatapultParts",  "catapult_parts")
cmap("AssembleSiegeAmmo",       "ballista_arrows")
cmap("MakeAsh",                 "ash")
cmap("MakeCharcoal",            "charcoal")
cmap("SmeltOre",                "metal_bars")
cmap("MeltMetalObject",         "metal_bars")
cmap("CustomReaction",          "REACTION_SUBTYPE")
cmap("MakeRawGlass",            "glass")
cmap("MakeWindow",              "window")
cmap("TanHide",                 "leather")
cmap("WeaveCloth",              "cloth")
cmap("MakeLye",                 "lye")
cmap("MakePotashFromLye",       "potash")
cmap("MakePotashFromAsh",       "potash")
cmap("PrepareMeal",             "prepared_meal")
-- Vanilla brewing is the hardcoded BrewDrink job (not a CustomReaction), so map
-- it directly to the alcohol craft flag.
cmap("BrewDrink",               "alcohol")
cmap("MakeArmor",               "UARMOR_SUBTYPE")
cmap("MakeGloves",              "GARMOR_SUBTYPE")
cmap("MakePants",               "LARMOR_SUBTYPE")
cmap("MakeShoes",               "FARMOR_SUBTYPE")
cmap("ConstructBag",            "bag")
cmap("MintCoins",               "coins")
cmap("MakeChain",               "rope/chain")
cmap("ForgeAnvil",              "anvil")
cmap("MakeBackpack",            "backpack")
cmap("MakeQuiver",              "quiver")


local TOOL_SUBTYPE_FLAG = {}
local function tools_subtype(subtype_id, flag)
    TOOL_SUBTYPE_FLAG[subtype_id] = flag
end -- from itemdef_toolst
-- tools subtype
tools_subtype(28,        "altar")
tools_subtype(11,        "jug")
tools_subtype(12,        "large_pot")
tools_subtype(13,        "hive")
--tools_subtype(14,        "honeycomb")
tools_subtype(16,        "minecart")
tools_subtype(17,        "wheelbarrow")
tools_subtype(18,        "stepladder")
tools_subtype(19,        "scroll_roller")
tools_subtype(20,        "book_binding")
tools_subtype(23,        "bookcase")
tools_subtype(26,        "pedestal")
tools_subtype(27,        "pedestal") --actually a display case
tools_subtype(10,        "nest_box") 
tools_subtype(22,        "quire")
tools_subtype(21,        "scroll")
tools_subtype(29,        "die")

local TRAP_SUBTYPE_FLAG = {}
local function trap_subtype(subtype_id, flag)
    TRAP_SUBTYPE_FLAG[subtype_id] = flag
end
trap_subtype(0, "giant_axe_blade")
trap_subtype(1, "corkscrew")
trap_subtype(2, "spiked_ball")
trap_subtype(3, "serrated_disc")
trap_subtype(4, "menacing_spike")

local SHIELD_SUBTYPE_FLAG = {}
local function shield_subtype(subtype_id, flag)
    SHIELD_SUBTYPE_FLAG[subtype_id] = flag
end -- from itemdef_shieldst
shield_subtype(0, "shield")
shield_subtype(1, "buckler")
shield_subtype(2, "shield")
shield_subtype(3, "shield")
shield_subtype(4, "shield")
shield_subtype(5, "shield")

local WEAPON_SUBTYPE_FLAG = {}
local function weapon_subtype(subtype_id, flag)
    WEAPON_SUBTYPE_FLAG[subtype_id] = flag
end -- from itemdef_helmst
weapon_subtype(1,   "battle_axe")
weapon_subtype(2,   "war_hammer")
weapon_subtype(3,   "short_sword")
weapon_subtype(4,   "spear")
weapon_subtype(5,   "mace")
weapon_subtype(7,   "pick")
weapon_subtype(21,  "training_axe")
weapon_subtype(22,  "training_sword")
weapon_subtype(23,  "training_spear")
weapon_subtype(6,   "crossbow")
weapon_subtype(33,  "crossbow")
weapon_subtype(34,  "war_hammer")
weapon_subtype(36,  "mace")
weapon_subtype(37,  "crossbow")
weapon_subtype(39,  "spear")
weapon_subtype(41,   "crossbow")
weapon_subtype(42,   "battle_axe")
weapon_subtype(43,   "spear")


local HELM_SUBTYPE_FLAG = {}
local function helm_subtype(subtype_id, flag)
    HELM_SUBTYPE_FLAG[subtype_id] = flag
end -- itemdef_helmsst
helm_subtype(0, "helm")
helm_subtype(1, "cap")
helm_subtype(2, "hood")
helm_subtype(3, "turban")
helm_subtype(4, "mask")
helm_subtype(5, "head_veil")
helm_subtype(6, "face_veil")
helm_subtype(7, "headscarf")
helm_subtype(8, "cap")
helm_subtype(9, "mask")


local GOBLET_SUBTYPE_FLAG = {}
local function goblet_subtype(material_flag, flag)
    GOBLET_SUBTYPE_FLAG[material_flag] = flag
end
goblet_subtype("wood",   "cup")
goblet_subtype("stone",  "mug")
goblet_subtype("metal",  "goblet")
goblet_subtype("glass",  "goblet")

-- Keyed by the job's reaction_name STRING (job_to_craft_flag looks up
-- REACTION_SUBTYPE_FLAG[job.reaction_name]). The previous version keyed by
-- df.job_type[name], but these are reaction names (not job types), so every
-- entry resolved to nil and the table was empty - breaking all reaction flags.
local REACTION_SUBTYPE_FLAG = {}
local function reaction_subtype(name, flag)
    REACTION_SUBTYPE_FLAG[name] = flag
end
-- Vanilla smelter reactions are named *_TO_COKE (the product is coke), not
-- *_TO_COAL. The old names never matched, so making coke was neither counted nor
-- gated by the Coke Permit.
reaction_subtype("LIGNITE_TO_COKE",                 "coke_bars")
reaction_subtype("BITUMINOUS_COAL_TO_COKE",         "coke_bars")
reaction_subtype("MAKE_PEARLASH",                   "pearlash")
reaction_subtype("MAKE_PLASTER_POWDER",             "gypsum_plaster")
reaction_subtype("MAKE_QUICKLIME",                  "quicklime")
reaction_subtype("MAKE_PARCHMENT",                  "sheet")
reaction_subtype("PRESS_PLANT_PAPER",               "sheet")
reaction_subtype("MAKE_SHEET_FROM_PLANT",           "sheet")
reaction_subtype("BREW_DRINK_FROM_PLANT",           "alcohol")
reaction_subtype("BREW_DRINK_FROM_PLANT_GROWTH",    "alcohol")
reaction_subtype("TAN_A_HIDE",                      "leather")
reaction_subtype("MAKE_MILK_OF_LIME",               "milk_of_lime")
reaction_subtype("RENDER_FAT",                      "tallow")
reaction_subtype("PRESS_OIL_FRUIT",                 "oil")
reaction_subtype("PRESS_OIL",                       "oil")
reaction_subtype("PRESS_HONEYCOMB",                 "honey")
reaction_subtype("MAKE_SOAP_FROM_OIL",              "soap")
reaction_subtype("MAKE_SOAP_FROM_TALLOW",           "soap")
reaction_subtype("MAKE WOODEN DISPLAY CASE",        "display_case")
reaction_subtype("MAKE_WOODEN_DISPLAY_CASE",        "display_case")
reaction_subtype("MAKE_SCROLL",                     "scroll")
reaction_subtype("MAKE_QUIRE",                      "quire")
reaction_subtype("BIND_BOOK",                       "codex")




-- Clay items are fired at a Kiln as CustomReactions (not Construct*/MakeTool jobs),
-- so they reach here by reaction_name. Their material resolves to "ceramic" (the
-- clay reagent / fired CERAMIC_* product), giving e.g. "blocks_ceramic". Without
-- these, ceramic bricks/jugs/pots/hives/statues/crafts never counted.
reaction_subtype("MAKE_CLAY_BRICKS",                "blocks")
reaction_subtype("MAKE_CLAY_JUG",                   "jug")
reaction_subtype("MAKE_LARGE_CLAY_POT",             "large_pot")
reaction_subtype("MAKE_CLAY_HIVE",                  "hive")
reaction_subtype("MAKE_CLAY_STATUE",                "statue")
reaction_subtype("MAKE_CLAY_CRAFTS",                "crafts")

-- Forced material for clay reactions. A completed manual job carries the clay
-- reagent in job.items (so classify_mat resolves "ceramic"), but a MANAGER WORK
-- ORDER has no .items and leaves mat_type/mat_index unset - so mat_craft_flag
-- returned nil and the material suffix was dropped, storing the count under
-- e.g. "statue" instead of "statue_ceramic". The AP client reads the suffixed
-- key, so ceramic statues/blocks made via work orders never counted. These
-- reactions always fire clay into a CERAMIC_* product, so the material is known.
local REACTION_FORCE_MATERIAL = {
    MAKE_CLAY_BRICKS   = "ceramic",
    MAKE_CLAY_JUG      = "ceramic",
    MAKE_LARGE_CLAY_POT = "ceramic",
    MAKE_CLAY_HIVE     = "ceramic",
    MAKE_CLAY_STATUE   = "ceramic",
    MAKE_CLAY_CRAFTS   = "ceramic",
}


local UARMOR_SUBTYPE_FLAG = {}
local function uarmor_subtype(subtype_id, flag)
    UARMOR_SUBTYPE_FLAG[subtype_id] = flag
end --from itemdef_armorst
uarmor_subtype(0, "breastplate")
uarmor_subtype(1, "mail_shirt")
uarmor_subtype(2, "leather_armor")
uarmor_subtype(3, "coat")
uarmor_subtype(4, "shirt")
uarmor_subtype(5, "cloak")
uarmor_subtype(6, "tunic")
uarmor_subtype(7, "toga")
uarmor_subtype(8, "cape")
uarmor_subtype(9, "vest")
uarmor_subtype(10, "dress")
uarmor_subtype(11, "robe")
uarmor_subtype(12, "breatplate")
uarmor_subtype(13, "shirt")

local GARMOR_SUBTYPE_FLAG = {}
local function garmor_subtype(subtype_id, flag)
    GARMOR_SUBTYPE_FLAG[subtype_id] = flag
end -- from itemdef_glovesst
garmor_subtype(0, "gauntlets")
garmor_subtype(1, "gloves")
garmor_subtype(2, "mittens")
garmor_subtype(3, "gauntlets")
garmor_subtype(4, "gloves")

local LARMOR_SUBTYPE_FLAG = {}
local function larmor_subtype(subtype_id, flag)
    LARMOR_SUBTYPE_FLAG[subtype_id] = flag
end -- from df.itemdef_pantsst
larmor_subtype(0, "trousers")
larmor_subtype(1, "greaves")
larmor_subtype(2, "leggings")
larmor_subtype(3, "loincloth")
larmor_subtype(4, "thong")
larmor_subtype(5, "skirt")
larmor_subtype(6, "skirt")
larmor_subtype(7, "skirt")
larmor_subtype(8, "braies")
larmor_subtype(9, "greaves")
larmor_subtype(10, "skirt")

local FARMOR_SUBTYPE_FLAG = {}
local function farmor_subtype(subtype_id, flag)
    FARMOR_SUBTYPE_FLAG[subtype_id] = flag
end --from itemdef_shoesst
farmor_subtype(0, "shoes")
farmor_subtype(1, "high_boots")
farmor_subtype(2, "low_boots")
farmor_subtype(3, "sandal")
farmor_subtype(4, "chausse")
farmor_subtype(5, "socks")
farmor_subtype(6, "high_boots")
farmor_subtype(7, "shoes")

-- Construction jobs/orders that use a generic material category (e.g. "make
-- wooden table") set mat_type/mat_index to -1 and instead flag
-- material_category.wood / .stone / etc. Map those category fields to our flag.
local MATCAT_TO_FLAG = {
    wood = "wood",
    metal = "metal", bar = "metal",
    stone = "stone", rock = "stone",
    glass = "glass", glass2 = "glass", glass3 = "glass",
    leather = "leather",
    cloth = "cloth", yarn = "cloth", silk = "cloth", plant_cloth = "cloth",
    bone = "bone",
}

-- Classify a (mat_type, mat_index) pair into a craft material flag, or nil.
-- Detection is TOKEN-driven rather than .mode-driven, because a generic "any
-- stone" job stores mat_type=0/mat_index=-1, which decodes to a matinfo with no
-- specific raw and a nil .mode (token "INORGANIC") that the old branches missed.
local function classify_mat(mat_type, mat_index)
    local ok, mat = pcall(dfhack.matinfo.decode, mat_type, mat_index)
    if ok and mat then
        -- Raw material TOKEN, e.g. "PLANT_MAT:OAK:WOOD", "INORGANIC:GLASS_GREEN",
        -- "CREATURE_MAT:COW:LEATHER", or bare "INORGANIC" for generic stone.
        local token = ""
        pcall(function() token = mat:getToken() or "" end)
        if token == "" then pcall(function() token = mat:toString() or "" end) end
        local up = token:upper()

        -- Metal is detected via the material's IS_METAL flag. IS_METAL lives in the
        -- material_flags enum (mat.material.flags), NOT inorganic_flags - the old
        -- mat.inorganic.flags.IS_METAL was an invalid index that always resolved
        -- false, so every metal craft was misclassified as "stone".
        local is_metal = false
        pcall(function()
            is_metal = (mat.material and mat.material.flags and mat.material.flags.IS_METAL) or false
        end)
        if is_metal then
            if up:find("ADAMANTINE") then return "adamantine" end
            return "metal"
        end

        if mat.mode == "plant" then
            if up:find(":WOOD") then return "wood" end
            return "cloth"  -- plant fiber / thread
        elseif mat.mode == "creature" then
            if up:find("LEATHER") then return "leather" end
            if up:find(":SILK") then return "cloth" end
            return "bone"
        end

        -- Inorganic / builtin / generic (covers nil .mode when mat_index == -1).
        if up:find("GLASS") then return "glass" end
        -- Ceramic covers raw clay reagents (CLAY/KAOLINITE) and the fired products
        -- (INORGANIC:CERAMIC_EARTHENWARE / _STONEWARE / _PORCELAIN). The CERAMIC
        -- check must precede the INORGANIC->stone fallback below, since stoneware's
        -- token also contains "INORGANIC".
        if up:find("CLAY") or up:find("KAOLINITE") or up:find("CERAMIC") or up:find("PORCELAIN") then return "ceramic" end
        if up:find("INORGANIC") then return "stone" end
        if up:find(":WOOD") then return "wood" end
    end

    -- Builtin mat_type fallback: 0 = INORGANIC base (generic stone),
    -- 3..5 = builtin green/clear/crystal glass.
    if mat_type == 0 then return "stone" end
    if mat_type and mat_type >= 3 and mat_type <= 5 then return "glass" end
    return nil
end

local function mat_craft_flag(job)
    -- 0. Reactions whose material is fixed by the recipe (e.g. clay -> ceramic).
    --    Checked first because manager work orders carry neither .items nor a
    --    usable mat_type, so the steps below can't recover the material for them.
    local rname
    pcall(function() rname = job.reaction_name end)
    if rname and REACTION_FORCE_MATERIAL[rname] then
        return REACTION_FORCE_MATERIAL[rname]
    end

    -- 1. Material set directly on the job/order (mat_type/mat_index).
    local flag = classify_mat(job.mat_type, job.mat_index)
    if flag then return flag end

    -- 2. Generic category material (mat_type unset): read material_category.
    local cat_flag
    pcall(function()
        for k, v in pairs(job.material_category) do
            if v == true and MATCAT_TO_FLAG[k] then
                cat_flag = MATCAT_TO_FLAG[k]
                return
            end
        end
    end)
    if cat_flag then return cat_flag end

    -- 3. Material on the job's items. Manual workshop jobs (e.g. a stone table)
    --    often leave mat_type=-1 and no material_category, carrying the material
    --    only on the consumed/produced item. Manager orders have no .items, so
    --    this is skipped for them (they resolve via step 1).
    local item_flag
    pcall(function()
        if not job.items then return end
        for _, ref in ipairs(job.items) do
            local it = ref.item
            if (not it) and ref.item_id then it = df.item.find(ref.item_id) end
            if it then
                local f = classify_mat(it.mat_type, it.mat_index)
                if f then item_flag = f; return end
            end
        end
    end)
    return item_flag
end

-- Shared dispatch: resolve job_type + all subtype tables to the base craft flag
-- string, without any material suffix. Returns nil when not a tracked craft.
local function _job_flag_dispatch(job)
    if not job or not job.job_type then return nil end
    local flag = JOB_TO_CRAFT_FLAG[job.job_type]
    if not flag then return nil end

    if flag == "TOOL_SUBTYPE" then
        return TOOL_SUBTYPE_FLAG[tonumber(job.item_subtype)]
    elseif flag == "TRAP_SUBTYPE" then
        return TRAP_SUBTYPE_FLAG[tonumber(job.item_subtype)]
    elseif flag == "SHIELD_SUBTYPE" then
        return SHIELD_SUBTYPE_FLAG[tonumber(job.item_subtype)]
    elseif flag == "WEAPON_SUBTYPE" then
        return WEAPON_SUBTYPE_FLAG[tonumber(job.item_subtype)]
    elseif flag == "HELM_SUBTYPE" then
        return HELM_SUBTYPE_FLAG[tonumber(job.item_subtype)]
    elseif flag == "GOBLET_SUBTYPE" then
        return GOBLET_SUBTYPE_FLAG[mat_craft_flag(job)]
    elseif flag == "REACTION_SUBTYPE" then
        if string.find(job.reaction_name, "DYE") then return "dye" end
        return REACTION_SUBTYPE_FLAG[job.reaction_name]
    elseif flag == "UARMOR_SUBTYPE" then
        return UARMOR_SUBTYPE_FLAG[tonumber(job.item_subtype)]
    elseif flag == "GARMOR_SUBTYPE" then
        return GARMOR_SUBTYPE_FLAG[tonumber(job.item_subtype)]
    elseif flag == "LARMOR_SUBTYPE" then
        return LARMOR_SUBTYPE_FLAG[tonumber(job.item_subtype)]
    elseif flag == "FARMOR_SUBTYPE" then
        return FARMOR_SUBTYPE_FLAG[tonumber(job.item_subtype)]
    end
    return flag
end

-- Items tracked without a material suffix regardless of craftsanity_materials.
-- Hash table for O(1) lookup. Also the source of truth for coke_bars (not coke_bar).
local NON_MATERIAL = {
    beds=true, ash=true, charcoal=true, metal_bars=true, coke_bars=true,
    pearlash=true, gypsum_plaster=true, quicklime=true, glass=true,
    leather=true, sheet=true, cloth=true, alcohol=true,
    lye=true, potash=true, milk_of_lime=true, prepared_meal=true,
    tallow=true, oil=true, press_cake=true, honey=true,
    bee_wax=true, dye=true, soap=true, training_axe=true,
    training_spear=true, training_sword=true, cup=true, ballista_parts=true,
    catapult_parts=true, millstone=true, quern=true, slab=true,
    mug=true, totem=true, window=true,
}

-- Returns the base item flag for a job (no material suffix). Used by the
-- crafting-item gate in dwarfipelago.lua. Returns nil if not a tracked craft.
function M.job_to_base_craft_flag(job)
    return _job_flag_dispatch(job)
end

-- Returns the AP craftable_items/materials flag for a completed job,
-- or nil if the job type is not tracked for quantity checks.
function M.job_to_craft_flag(job)
    local flag = _job_flag_dispatch(job)
    if not flag then return nil end
    -- Traction benches are counted from their produced item in on_item_created
    -- (M.item_craft_flag): the job consumes a table + mechanism + chain of
    -- different materials, so the bench's own material can't be picked reliably
    -- from the reagents. Skip the job-side count to avoid a wrong-material or
    -- double count (the base flag is still exposed via job_to_base_craft_flag
    -- for the craft-permit gate).
    if flag == "traction_bench" then return nil end
    if NON_MATERIAL[flag] then return flag end
    local need_mat = dfhack.persistent.getWorldDataString('dwarfipelago/craftsanity_materials')
    if tonumber(need_mat) == 1 then
        local material_used = mat_craft_flag(job)
        if not material_used then return flag end  -- nil guard: fall back to base key
        return flag .. "_" .. material_used
    end
    return flag
end

-- Like job_to_craft_flag but for a produced ITEM (used when the craft is better
-- identified by its output than its job - e.g. traction benches). base_flag is
-- the craftable_items flag; the material suffix is taken from the item itself.
function M.item_craft_flag(base_flag, item)
    if NON_MATERIAL[base_flag] then return base_flag end
    local need_mat = dfhack.persistent.getWorldDataString('dwarfipelago/craftsanity_materials')
    if tonumber(need_mat) == 1 then
        local material_used = classify_mat(item.mat_type, item.mat_index)
        if not material_used then return base_flag end  -- nil guard: base key
        return base_flag .. "_" .. material_used
    end
    return base_flag
end

-- ── Craft count helpers ───────────────────────────────────────────────────────
-- Cumulative counts of completed production jobs per flag, persisted in world
-- data under "dwarfipelago/craft_count/<flag_name>".
-- Incremented by the eventful job hook in dwarfipelago.lua.
-- The AP client polls these directly to decide when a milestone threshold is met.

local CRAFT_COUNT_PREFIX = "dwarfipelago/craft_count/"
-- Index of every craft-count flag incremented in this world, so the status
-- command can enumerate dynamic material-split keys (e.g. "table_wood") that
-- aren't present in any hardcoded list.
local CRAFT_INDEX_KEY = "dwarfipelago/craft_count_index"

local function craft_index_add(flag)
    local json = require('json')
    local raw  = dfhack.persistent.getWorldDataString(CRAFT_INDEX_KEY)
    local list = (raw and raw ~= "") and json.decode(raw) or {}
    for _, f in ipairs(list) do
        if f == flag then return end
    end
    table.insert(list, flag)
    dfhack.persistent.saveWorldDataString(CRAFT_INDEX_KEY, json.encode(list))
end

function M.increment_craft_count(flag)
    local key = CRAFT_COUNT_PREFIX .. flag
    local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
    dfhack.persistent.saveWorldDataString(key, tostring(n))
    craft_index_add(flag)
    return n
end

function M.get_craft_count(flag)
    return tonumber(dfhack.persistent.getWorldDataString(CRAFT_COUNT_PREFIX .. flag)) or 0
end

-- Returns { flag = count } for every craft flag recorded this world (count > 0).
function M.get_all_craft_counts()
    local json = require('json')
    local raw  = dfhack.persistent.getWorldDataString(CRAFT_INDEX_KEY)
    local list = (raw and raw ~= "") and json.decode(raw) or {}
    local out = {}
    for _, f in ipairs(list) do
        local n = tonumber(dfhack.persistent.getWorldDataString(CRAFT_COUNT_PREFIX .. f)) or 0
        if n > 0 then out[f] = n end
    end
    return out
end

-- Clears all recorded craft counts and the index (used by 'dwarfipelago reset').
function M.clear_craft_counts()
    local json = require('json')
    local raw  = dfhack.persistent.getWorldDataString(CRAFT_INDEX_KEY)
    local list = (raw and raw ~= "") and json.decode(raw) or {}
    for _, f in ipairs(list) do
        dfhack.persistent.saveWorldDataString(CRAFT_COUNT_PREFIX .. f, "")
    end
    dfhack.persistent.saveWorldDataString(CRAFT_INDEX_KEY, "")
end

-- ── Energy Link helpers ───────────────────────────────────────────────────────

-- Count DRINK items in fortress stocks (not carried by traders).
-- Does NOT filter on in_inventory: items inside barrels/containers in DF have
-- in_inventory=true transitively, which would exclude all stocked drinks.
function M.count_fortress_drinks()
    local count = 0
    for _, item in ipairs(df.global.world.items.all) do
        local ok, t = pcall(function() return item:getType() end)
        if ok and t == df.item_type.DRINK
                and not item.flags.removed
                and not item.flags.trader then
            count = count + (item.stack_size or 1)
        end
    end
    return count
end

-- Return a list of DRINK items available to deposit (not in active jobs).
-- Skips items already claimed by a job; in_inventory is not checked because
-- drinks inside barrels/containers also carry that flag in DF.
function M.find_fortress_drinks()
    local drinks = {}
    for _, item in ipairs(df.global.world.items.all) do
        local ok, t = pcall(function() return item:getType() end)
        if ok and t == df.item_type.DRINK
                and not item.flags.removed
                and not item.flags.trader
                and not item.flags.in_job then
            table.insert(drinks, item)
        end
    end
    return drinks
end

-- Return all accessible food items in fortress stocks.
function M.find_fortress_food()
    local food = {}
    for _, item in ipairs(df.global.world.items.all) do
        local ok, t = pcall(function() return item:getType() end)
        if ok and t == df.item_type.FOOD
                and not item.flags.removed
                and not item.flags.trader
                and not item.flags.in_inventory
                and not item.flags.in_job then
            table.insert(food, item)
        end
    end
    return food
end

-- Return all accessible minted coins in fortress stocks with their energy values.
-- A coin stack is worth 10 × material_value per 500 coins, so each coin item
-- contributes (stack_size × material_value × 10 / 500 × 1000) joules.
-- Returns (list_of_{item,j}, total_j).
function M.find_fortress_coins_energy()
    local found   = {}
    local total_j = 0
    for _, item in ipairs(df.global.world.items.all) do
        local ok, t = pcall(function() return item:getType() end)
        if ok and t == df.item_type.COIN
                and not item.flags.removed
                and not item.flags.trader
                and not held_by_unit(item) then
            local j = 0
            pcall(function()
                local ok2, mat = pcall(dfhack.matinfo.decode, item.mat_type, item.mat_index)
                if ok2 and mat and mat.material then
                    -- Coin value: a stack of 500 is worth 10 * material_value, so a
                    -- coin is material_value * 10 / 500. Energy uses 1 val = 1000 J.
                    j = (item.stack_size or 1) * (mat.material.material_value or 1) * 10 / 500 * 1000
                end
            end)
            if j > 0 then
                table.insert(found, { item = item, j = j })
                total_j = total_j + j
            end
        end
    end
    return found, total_j
end

-- ── Skill level helpers ───────────────────────────────────────────────────────
-- Highest trained level of each tracked job skill among living citizens,
-- persisted in world data under "dwarfipelago/skill/<flag_name>".
-- Refreshed each poll tick by M.update_skill_levels (below). The AP client polls
-- these and fires the matching "<Level> <Skill>" location once the recorded level
-- reaches that location's threshold (Novice=1 .. Legendary=15).

local SKILL_COUNT_PREFIX = "dwarfipelago/skill/"

local SKILL_LIST = {
    { key = df.job_skill["CUT_STONE"], skill = "stonecutter", name = "Stonecutter"},
    { key = df.job_skill["ENGRAVE_STONE"], skill = "engraver", name = "Engraver"},
    { key = df.job_skill["MINING"], skill = "miner", name = "Miner"},
    { key = df.job_skill["WOODCUTTING"], skill = "woodcutter", name = "Wood Cutter"},
    { key = df.job_skill["HERBALISM"], skill = "herbalist", name = "Herbalist"},
    { key = df.job_skill["SPINNING"], skill = "spinner", name = "Spinner"},
    { key = df.job_skill["FISH"], skill = "fisherdwarf", name = "Fisherdwarf"},
    { key = df.job_skill["SNEAK"], skill = "ambusher", name = "Ambusher"},
    { key = df.job_skill["TRAPPING"], skill = "trapper", name = "Trapper"},
    { key = df.job_skill["GLASSMAKER"], skill = "glassmaker", name = "Glassmaker"},
    { key = df.job_skill["METALCRAFT"], skill = "metalcrafter", name = "Metal Crafter"},
    { key = df.job_skill["CUTGEM"], skill = "gemcutter", name = "Gem Cutter"},
    { key = df.job_skill["STONECRAFT"], skill = "stonecrafter", name = "Stone Crafter"},
    { key = df.job_skill["WOODCRAFT"], skill = "woodcrafter", name = "Wood Crafter"},
    { key = df.job_skill["ENCRUSTGEM"], skill = "gemsetter", name = "Gem Setter"},
    { key = df.job_skill["SMELT"], skill = "furnaceoperator", name = "Furnace Operator"},
    { key = df.job_skill["EXTRACT_STRAND"], skill = "strandextractor", name = "Strand Extractor"},
    { key = df.job_skill["PLANT"], skill = "planter", name = "Planter"},
    { key = df.job_skill["ANIMALTRAIN"], skill = "animaltrainer", name = "Animal Trainer"},
    { key = df.job_skill["SIEGECRAFT"], skill = "siegeengineer", name = "Siege Engineer"},
    { key = df.job_skill["FORGE_WEAPON"], skill = "weaponsmith", name = "Weaponsmith"},
    { key = df.job_skill["FORGE_ARMOR"], skill = "armorsmith", name = "Armorsmith"},
    { key = df.job_skill["BUTCHER"], skill = "butcher", name = "Butcher"},
    { key = df.job_skill["PROCESSFISH"], skill = "fishcleaner", name = "Fish Cleaner"},
    { key = df.job_skill["MILLING"], skill = "miller", name = "Miller"},
    { key = df.job_skill["MILK"], skill = "milker", name = "Milker"},
    { key = df.job_skill["CHEESEMAKING"], skill = "cheesemaker", name = "Cheese Maker"},
    { key = df.job_skill["PROCESSPLANTS"], skill = "thresher", name = "Thresher"},
    { key = df.job_skill["COOK"], skill = "cook", name = "Cook"},
    { key = df.job_skill["BONECARVE"], skill = "bonecarver", name = "Bone Carver"},
    { key = df.job_skill["SIEGEOPERATE"], skill = "siegeoperator", name = "Siege Operator"},
    { key = df.job_skill["MECHANICS"], skill = "mechanic", name = "Mechanic"},
    { key = df.job_skill["DIAGNOSE"], skill = "diagnostician", name = "Diagnostician"},
    { key = df.job_skill["SET_BONE"], skill = "bonedoctor", name = "Bone Doctor"},
    { key = df.job_skill["DRESS_WOUNDS"], skill = "wounddresser", name = "Wound Dresser"},
    { key = df.job_skill["SURGERY"], skill = "surgeon", name = "Surgeon"},
    { key = df.job_skill["SUTURE"], skill = "suturer", name = "Suturer"},
    { key = df.job_skill["WOOD_BURNING"], skill = "woodburner", name = "Wood Burner"},
    { key = df.job_skill["LYE_MAKING"], skill = "lyemaker", name = "Lye Maker"},
    { key = df.job_skill["POTASH_MAKING"], skill = "potashmaker", name = "Potash Maker"},
    { key = df.job_skill["DYER"], skill = "dyer", name = "Dyer"},
    { key = df.job_skill["OPERATE_PUMP"], skill = "pumpoperator", name = "Pump Operator"},
    { key = df.job_skill["SHEARING"], skill = "shearer", name = "Shearer"},
    { key = df.job_skill["GELD"], skill = "gelder", name = "Gelder"},
    { key = df.job_skill["CARPENTRY"], skill = "carpenter", name = "Carpenter"},
    { key = df.job_skill["MASONRY"], skill = "mason", name = "Mason"},
    { key = df.job_skill["DISSECT_FISH"], skill = "fishdissector", name = "Fish Dissector"},
    { key = df.job_skill["LEATHERWORK"], skill = "leatherworker", name = "Leatherworker"},
    { key = df.job_skill["CLOTHESMAKING"], skill = "clothier", name = "Clothier"},
    { key = df.job_skill["FORGE_FURNITURE"], skill = "blacksmith", name = "Blacksmith"},
    { key = df.job_skill["BOWYER"], skill = "bowyer", name = "Bowyer"},
    { key = df.job_skill["SOAP_MAKING"], skill = "soaper", name = "Soaper"},
    { key = df.job_skill["POTTERY"], skill = "potter", name = "Potter"},
    { key = df.job_skill["GLAZING"], skill = "glazer", name = "Glazer"},
    { key = df.job_skill["PRESSING"], skill = "presser", name = "Presser"},
    { key = df.job_skill["BEEKEEPING"], skill = "beekeeper", name = "Beekeeper"},
    { key = df.job_skill["WAX_WORKING"], skill = "waxworker", name = "Wax Worker"},
    { key = df.job_skill["PAPERMAKING"], skill = "papermaker", name = "Papermaker"},
    { key = df.job_skill["BOOKBINDING"], skill = "bookbinder", name = "Bookbinder"},
    { key = df.job_skill["RECORD_KEEPING"], skill = "recordkeeper", name = "Record Keeper"},
    { key = df.job_skill["ORGANIZATION"], skill = "organizer", name = "Organizer"},
    { key = df.job_skill["APPRAISAL"], skill = "appraiser", name = "Appraiser"},
    { key = df.job_skill["BREWING"], skill = "brewer", name = "Brewer"},
    { key = df.job_skill["CARVE_STONE"], skill = "stonecarver", name = "Stone Carver"},
    { key = df.job_skill["TANNER"], skill = "tanner", name = "Tanner"},
    { key = df.job_skill["WEAVING"], skill = "weaver", name = "Weaver"},
    { key = df.job_skill["RANGED_COMBAT"], skill = "archer", name = "Archer"},
    { key = df.job_skill["AXE"], skill = "axedwarf", name = "Axedwarf"},
    { key = df.job_skill["CROSSBOW"], skill = "crossbowdwarf", name = "Crossbowdwarf"},
    { key = df.job_skill["DODGING"], skill = "dodger", name = "Dodger"},
    { key = df.job_skill["DISCIPLINE"], skill = "discipline", name = "Discipline"},
    { key = df.job_skill["MELEE_COMBAT"], skill = "fighter", name = "Fighter"},
    { key = df.job_skill["HAMMER"], skill = "hammerdwarf", name = "Hammerdwarf"},
    { key = df.job_skill["MACE"], skill = "macerdwarf", name = "Macedwarf"},
    { key = df.job_skill["SPEAR"], skill = "speardwarf", name = "Speardwarf"},
    { key = df.job_skill["SWORD"], skill = "sworddwarf", name = "Sworddwarf"},
    { key = df.job_skill["ARMOR"], skill = "armordwarf", name = "Armordwarf"},
    { key = df.job_skill["STANCE_STRIKE"], skill = "kicker", name = "Kicker"},
    { key = df.job_skill["MILITARY_TACTICS"], skill = "tactics", name = "Tactics"},
    { key = df.job_skill["WRESTLING"], skill = "wrestler", name = "Wrestler"},
    { key = df.job_skill["GRASP_STRIKE"], skill = "striker", name = "Striker"},
    { key = df.job_skill["SHIELD"], skill = "shielddwarf", name = "Shielddwarf"},
    { key = df.job_skill["BITE"], skill = "biter", name = "Biter"},
    { key = df.job_skill["BLOWGUN"], skill = "blowgunner", name = "Blowgunner"},
    { key = df.job_skill["BOW"], skill = "bowdwarf", name = "Bowdwarf"},
    { key = df.job_skill["DAGGER"], skill = "knifedwarf", name = "Knifedwarf"},
    { key = df.job_skill["WHIP"], skill = "lasher", name = "Lasher"},
}

function M.get_skill_count(flag)
    return tonumber(dfhack.persistent.getWorldDataString(SKILL_COUNT_PREFIX .. flag)) or 0
end

-- Returns { flag = count } for every craft flag recorded this world (count > 0).
function M.get_all_skill_counts()
    local out = {}
    for _, skilltype in ipairs(SKILL_LIST) do
        local n = tonumber(dfhack.persistent.getWorldDataString(SKILL_COUNT_PREFIX .. skilltype.skill)) or -1
        if n >= 0 then out[skilltype.name] = n end
    end
    return out
end

-- Clears all recorded skill levels back to 0 (used by 'dwarfipelago reset').
-- Only resets skills that were initialised for this slot (level >= 0).
function M.clear_skill_counts()
    for _, skilltype in ipairs(SKILL_LIST) do
        local n = tonumber(dfhack.persistent.getWorldDataString(SKILL_COUNT_PREFIX .. skilltype.skill)) or -1
        if n >= 0 then dfhack.persistent.saveWorldDataString(SKILL_COUNT_PREFIX .. skilltype.skill, "0") end
    end
end

-- Highest level a unit has trained in a job skill (0 if untrained). Reads the
-- soul's skill vector directly (unit_skill.id == job_skill, .rating == level) so
-- it doesn't depend on a particular DFHack helper being present.
local function unit_skill_rating(unit, skill_id)
    local soul = unit.status and unit.status.current_soul
    if not soul then return 0 end
    for _, sk in ipairs(soul.skills) do
        if sk.id == skill_id then return sk.rating or 0 end
    end
    return 0
end

-- Lower a unit's trained level in a skill to `rating` (for the "lower skills"
-- mechanic, so a high-level migrant can't complete many checks at once). Clears
-- accumulated experience so the level doesn't immediately tick back up. No-op if
-- the unit is already at or below the target.
local function lower_unit_skill(unit, skill_id, rating)
    local soul = unit.status and unit.status.current_soul
    if not soul then return end
    for _, sk in ipairs(soul.skills) do
        if sk.id == skill_id and sk.rating > rating then
            sk.rating = rating
            sk.experience = 0
            return
        end
    end
end

-- Rescan citizens and update each tracked skill's recorded level. Called from the
-- poll loop. Only runs when skillsanity is enabled, and only touches skills the
-- client initialised for this slot (their key already exists). Recorded levels
-- are monotonic (a reached level stays reached) and capped at the slot's max
-- level. With behaviour == 1 (lower skills) over-levelled citizens are demoted to
-- one level above the recorded level, so each level-up is a single new check.
function M.update_skill_levels()
    if dfhack.persistent.getWorldDataString("dwarfipelago/skillsanity_enabled") ~= "1" then return end
    local max_level = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/skillsanity_max_level")) or 15
    local behaviour = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/skillsanity_behaviour")) or 0

    -- Living citizens, gathered once and reused for every tracked skill.
    local citizens = {}
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
            table.insert(citizens, unit)
        end
    end

    for _, st in ipairs(SKILL_LIST) do
        if st.key ~= nil then  -- skip any job_skill name absent in this DF build
            local key = SKILL_COUNT_PREFIX .. st.skill
            local cur = dfhack.persistent.getWorldDataString(key)
            if cur ~= nil and cur ~= "" then  -- only enabled/tracked skills
                local recorded = tonumber(cur) or 0
                local cap = (behaviour == 1) and math.min(recorded + 1, max_level) or max_level

                local best = 0
                for _, unit in ipairs(citizens) do
                    local r = unit_skill_rating(unit, st.key)
                    if behaviour == 1 and r > cap then
                        lower_unit_skill(unit, st.key, cap)
                        r = cap
                    end
                    if r > best then best = r end
                end

                local newrec = math.max(recorded, math.min(best, max_level))
                if newrec ~= recorded then
                    dfhack.persistent.saveWorldDataString(key, tostring(newrec))
                end
            end
        end
    end
end

-- ── Military / siege milestones (Slay Megabeast goal) ─────────────────────────
-- Feeds both the AP location checks above and the War Readiness gate in
-- dwarfipelago.lua (barracks -> readiness 5-6, 4 soldiers at skill 10 -> 7-9).

-- Combat skills that count as "military" for these milestones.
local MILITARY_SKILL_IDS = {}
for _, name in ipairs({ "AXE", "SWORD", "MACE", "HAMMER", "SPEAR", "MELEE_COMBAT" }) do
    local id = df.job_skill[name]
    if id then MILITARY_SKILL_IDS[#MILITARY_SKILL_IDS + 1] = id end
end

-- Number of living citizens whose best military skill is >= threshold.
function M.count_military_skill(threshold)
    local n = 0
    for _, u in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) and u.status.current_soul then
            local best = 0
            for _, sk in ipairs(u.status.current_soul.skills) do
                for _, mid in ipairs(MILITARY_SKILL_IDS) do
                    if sk.id == mid and (sk.rating or 0) > best then best = sk.rating end
                end
            end
            if best >= threshold then n = n + 1 end
        end
    end
    return n
end

-- "Training Completed" should reflect a soldier trained AFTER the campaign began,
-- not dwarves who embarked already skilled (DF v50 embark dwarves are often
-- experienced histfigs, which fired this check on world load). Snapshot the
-- Competent+ military count once per world, then fire only when it grows.
function M.training_completed()
    local cur = M.count_military_skill(3)
    local key = "dwarfipelago/megabeast/train_baseline"
    local base = dfhack.persistent.getWorldDataString(key)
    if base == nil or base == "" then
        dfhack.persistent.saveWorldDataString(key, tostring(cur))
        return false  -- first observation establishes the baseline; never fires now
    end
    return cur > (tonumber(base) or 0)
end

-- True when a squad has a barracks equipped for drill: an armor stand AND a
-- weapon rack assigned to it. (Beds are commonly separate sleeping quarters, so
-- they are not required - keeps the milestone from silently never firing.)
function M.barracks_is_set_up()
    local ok, result = pcall(function()
        for _, squad in ipairs(df.global.world.squads.all) do
            local has_stand, has_rack = false, false
            for _, room in ipairs(squad.rooms) do
                local bld = df.building.find(room.building_id)
                if bld then
                    local t = bld:getType()
                    if t == df.building_type.Armorstand then has_stand = true
                    elseif t == df.building_type.Weaponrack then has_rack = true end
                end
            end
            if has_stand and has_rack then return true end
        end
        return false
    end)
    return ok and result == true
end

-- reqscript returns the script's _ENV, not the explicit return value.
-- Copy all module exports into _ENV so callers can access them as globals.
for k, v in pairs(M) do _ENV[k] = v end
return M
