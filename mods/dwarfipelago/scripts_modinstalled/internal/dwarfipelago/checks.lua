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

-- ── Wealth milestones ─────────────────────────────────────────────────────────

-- Returns current total fortress wealth (items + buildings + stocks).
-- DF 50+ (Steam / 2022+) renamed df.global.ui → df.global.plotinfo.
-- We try plotinfo first so both versions are supported.
local function fortress_wealth()
    local ok, result = pcall(function()
        return df.global.plotinfo.tasks.wealth
    end)
    if ok and type(result) == "number" then return result end

    -- Fallback for Classic DF (pre-50).
    ok, result = pcall(function()
        return df.global.ui.tasks.wealth
    end)
    if ok and type(result) == "number" then return result end

    return 0
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

local function exported_wealth()
    local ok, result = pcall(function()
        return df.global.plotinfo.tasks.wealth_exported
    end)
    if ok and type(result) == "number" then return result end

    ok, result = pcall(function()
        return df.global.ui.tasks.wealth_exported
    end)
    if ok and type(result) == "number" then return result end

    return 0
end

local function has_fortress_title(pop_req, created_req, exported_req)
    return function()
        if citizen_count() < pop_req then return false end
        return fortress_wealth() >= created_req or exported_wealth() >= exported_req
    end
end

M.checks = {
    -- Wealth milestones
    { id = 37370000, name = "Humble Beginnings",   fn = function() return fortress_wealth() >= 1000    end },
    { id = 37370001, name = "Growing Stronghold",  fn = function() return fortress_wealth() >= 10000   end },
    { id = 37370002, name = "Prosperous Fortress", fn = function() return fortress_wealth() >= 50000   end },
    { id = 37370003, name = "Rich Citadel",        fn = function() return fortress_wealth() >= 100000  end },
    { id = 37370004, name = "Legendary Vault",     fn = function() return fortress_wealth() >= 500000  end },

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
    { id = 37370107, name = "First Stone Block Cut",   fn = function() return M.production_flag("stone_block")    end },
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

    -- Trade / export milestones
    { id = 37370200, name = "First Trade Completed",    fn = function() return M.trade_flag("trade_completed")    end },
    { id = 37370201, name = "First Export",             fn = function() return M.trade_flag("first_export")       end },
    { id = 37370202, name = "Dwarven Caravan Visit",    fn = function() return M.trade_flag("dwarven_caravan")    end },
    { id = 37370203, name = "Elven Caravan Visit",      fn = function() return M.trade_flag("elven_caravan")      end },
    { id = 37370204, name = "Human Caravan Visit",      fn = function() return M.trade_flag("human_caravan")      end },
    { id = 37370205, name = "Outpost Liaison Meeting",  fn = function() return M.trade_flag("liaison_met")        end },

    -- Fortress status / noble appointments
    -- Position codes match vanilla DF entity_default.txt. KING covers both king
    -- and queen (DF stores a single position code with gendered display names).
    { id = 37370300, name = "Mayor Elected",           fn = function() return has_noble_role("MAYOR")             end },
    { id = 37370301, name = "Baron Appointed",         fn = function() return has_noble_role("BARON")             end },
    { id = 37370302, name = "Count Appointed",         fn = function() return has_noble_role("COUNT")             end },
    { id = 37370303, name = "Duke Appointed",          fn = function() return has_noble_role("DUKE")              end },
    { id = 37370304, name = "Monarch Takes Residence", fn = function()
        -- Try KING first (vanilla code); fall back to QUEEN in case a modded
        -- civ uses a separate code for the female ruler.
        return has_noble_role("KING") or has_noble_role("QUEEN")
    end },

    -- Fortress title milestones (population + created OR exported wealth)
    { id = 37370400, name = "Hamlet Established",     fn = has_fortress_title(20,   5000,    500) },
    { id = 37370401, name = "Village Established",    fn = has_fortress_title(50,  25000,   2500) },
    { id = 37370402, name = "Town Established",       fn = has_fortress_title(80, 100000,  10000) },
    { id = 37370403, name = "City Established",       fn = has_fortress_title(110, 200000, 20000) },
    { id = 37370404, name = "Metropolis Established", fn = has_fortress_title(140, 300000, 30000) },
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

-- Crafting
map("MakeCrafts",              "crafted_item")
map("CarveStatue",             "crafted_item")  -- pre-50 name
map("CarveFurniture",          "crafted_item")  -- DF 50+ name
map("MakeTotem",               "crafted_item")
-- Weapons / armor
map("MakeWeapon",              "weapon")
map("MakeAmmo",                "weapon")
map("MakeArmor",               "armor")
map("MakeHelm",                "armor")
map("MakeGloves",              "armor")
map("MakeBoots",               "armor")
map("MakePants",               "armor")
map("MakeShield",              "armor")
-- Furniture
map("MakeTable",               "table")
map("MakeChair",               "furniture")
map("MakeChest",               "chest")
map("MakeCabinet",             "furniture")
map("MakeBed",                 "bed")
map("MakeDoor",                "furniture")
map("MakeFloodgate",           "furniture")
map("MakeBarrel",              "barrel")
map("MakeBucket",              "furniture")
map("MakeCage",                "cage")
map("MakeMechanism",           "mechanism")
-- Food / drink
map("PrepareMeal",             "meal")
map("BrewDrink",               "brew")
-- Materials
map("SmeltOre",                "metal_bar")
map("MeltMetalObject",         "metal_bar")
map("CutBlock",                "stone_block")
map("WeaveCloth",              "cloth")
map("ProcessPlants",           "cloth")   -- also produces thread
map("TanHide",                 "leather")
map("CutGems",                 "gem")
map("EncrustedWithGems",       "gem")
-- Traps
map("ConstructTrap",           "trap")
map("LinkBuildingToTrigger",   "trap")

function M.job_to_production_flag(job)
    if job and job.job_type then
        return JOB_TO_FLAG[job.job_type]
    end
    return nil
end

-- Expose wealth accessor so main.lua can use it for the goal check
-- without duplicating the DF50 / Classic fallback logic.
M.fortress_wealth = fortress_wealth

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
cmap("MakeTotem",       "altar")
cmap("MakeDoor",        "door")
cmap("MakeCage",        "cage")
cmap("MakeBox",         "bin")
cmap("CutBlock",        "blocks")
cmap("MakeWheelbarrow", "wheelbarrow")
cmap("MakeGrate",       "grate")
cmap("MakeCorkscrew",   "corkscrew")
cmap("MakeAnimalTrap",  "animal_trap")
cmap("MakeBall",        "ball")
cmap("MakeArmorStand",  "armor_stand")
cmap("MakePedestal",    "pedestal")
cmap("MakeBucket",      "bucket")
cmap("MakeSpike",       "spike")

-- craftable_materials (unambiguous by job type)
cmap("WeaveCloth",      "cloth")
cmap("ProcessPlants",   "cloth")
cmap("TanHide",         "leather")
cmap("SmeltOre",        "metal")
cmap("MeltMetalObject", "metal")
cmap("MakeGlass",       "glass")
cmap("MakeCeramicItem", "ceramics")

-- Jobs where the flag depends on the job's primary material (stone/bone/wood).
local NEEDS_MAT_CHECK = {}
local function matjob(name)
    local v = df.job_type[name]
    if v ~= nil then NEEDS_MAT_CHECK[v] = true end
end
matjob("MakeCrafts")
matjob("CarveBone")
matjob("CarveStatue")
matjob("CarveFurniture")

local function mat_craft_flag(job)
    local ok, mat = pcall(dfhack.matinfo.decode, job.mat_type, job.mat_index)
    if not ok or not mat then return nil end
    if mat.mode == "inorganic" then
        local raw = mat.inorganic
        if raw and raw.flags.IS_METAL then return "metal" end
        return "stone"
    elseif mat.mode == "plant" then
        return "wood"
    elseif mat.mode == "creature" then
        return "bone"
    end
    return nil
end

-- Returns the AP craftable_items/materials flag for a completed job,
-- or nil if the job type is not tracked for quantity checks.
function M.job_to_craft_flag(job)
    if not job or not job.job_type then return nil end
    local flag = JOB_TO_CRAFT_FLAG[job.job_type]
    if flag then return flag end
    if NEEDS_MAT_CHECK[job.job_type] then
        return mat_craft_flag(job)
    end
    return nil
end

-- ── Craft count helpers ───────────────────────────────────────────────────────
-- Cumulative counts of completed production jobs per flag, persisted in world
-- data under "dwarfipelago/craft_count/<flag_name>".
-- Incremented by the eventful job hook in dwarfipelago.lua.
-- The AP client polls these directly to decide when a milestone threshold is met.

local CRAFT_COUNT_PREFIX = "dwarfipelago/craft_count/"

function M.increment_craft_count(flag)
    local key = CRAFT_COUNT_PREFIX .. flag
    local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
    dfhack.persistent.saveWorldDataString(key, tostring(n))
    return n
end

function M.get_craft_count(flag)
    return tonumber(dfhack.persistent.getWorldDataString(CRAFT_COUNT_PREFIX .. flag)) or 0
end

-- reqscript returns the script's _ENV, not the explicit return value.
-- Copy all module exports into _ENV so callers can access them as globals.
for k, v in pairs(M) do _ENV[k] = v end
return M
