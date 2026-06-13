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

-- Returns the combined value of all minted coins (COIN) and cut gems (SMALLGEM)
-- currently in fortress stocks — not carried by any unit, not belonging to traders.
-- Value per stack = stack_size × material.material_value.
-- Both item types require AP-gated blueprints (Screw Press and Jeweler's Workshop)
-- and their material values vary widely, keeping embark-site luck meaningful.
local function treasury_wealth()
    local total = 0
    for _, item in ipairs(df.global.world.items.all) do
        local itype = item:getType()
        if (itype == df.item_type.COIN or itype == df.item_type.SMALLGEM)
                and not item.flags.in_inventory
                and not item.flags.trader then
            local ok, mat = pcall(dfhack.matinfo.decode, item.mat_type, item.mat_index)
            local mat_value = 1
            if ok and mat and mat.material then
                mat_value = mat.material.material_value or 1
            end
            total = total + (item.stack_size or 1) * mat_value
        end
    end
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
    -- Wealth milestones — based on combined coin + cut-gem value in fortress stocks.
    -- Each tier requires the matching Merchant's Coffer count to have been received.
    { id = 37370000, name = "Humble Beginnings (1,000)",    fn = function() return unlock_count("wealth_coffers") >= 1 and treasury_wealth() >= 1000    end },
    { id = 37370001, name = "Growing Stronghold (10,000)",  fn = function() return unlock_count("wealth_coffers") >= 2 and treasury_wealth() >= 10000   end },
    { id = 37370002, name = "Prosperous Fortress (50,000)", fn = function() return unlock_count("wealth_coffers") >= 3 and treasury_wealth() >= 50000   end },
    { id = 37370003, name = "Rich Citadel (100,000)",       fn = function() return unlock_count("wealth_coffers") >= 4 and treasury_wealth() >= 100000  end },
    { id = 37370004, name = "Legendary Vault (500,000)",    fn = function() return unlock_count("wealth_coffers") >= 5 and treasury_wealth() >= 500000  end },

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
    { id = 37370118, name = "First Anvil Forged",      fn = function() return M.production_flag("anvil")          end },
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

    -- Mining: depth below the surface z-level (deepest mining job reached).
    { id = 37370700, name = "Delved 10 Levels Deep",  fn = function() return M.mining_depth() >= 10  end },
    { id = 37370701, name = "Delved 25 Levels Deep",  fn = function() return M.mining_depth() >= 25  end },
    { id = 37370702, name = "Delved 50 Levels Deep",  fn = function() return M.mining_depth() >= 50  end },
    { id = 37370703, name = "Delved 75 Levels Deep",  fn = function() return M.mining_depth() >= 75  end },
    { id = 37370704, name = "Delved 100 Levels Deep", fn = function() return M.mining_depth() >= 100 end },

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
    { id = 37370750, name = "First Eggs Hatched", fn = function() return M.production_flag("egg_hatched")     end },
    { id = 37370751, name = "Caged a Hostile Beast", fn = function() return M.production_flag("caged_hostile_beast") end },

    -- Deep / endgame.
    { id = 37370760, name = "Mined Adamantine", fn = function() return M.production_flag("adamantine")    end },
    { id = 37370761, name = "Sold an Artifact", fn = function() return M.production_flag("sold_artifact") end },
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

    local group_id = df.global.plotinfo.group_id  -- fortress entity; civ_id is the mountainhome and doesn't match player squads
    local SITE_INVASION   = df.army_controller_goal_type.SITE_INVASION
    local RECOVER_ARTIFACT = df.army_controller_goal_type.RECOVER_ARTIFACT
    local DIPLOMACY        = df.army_controller_goal_type.DIPLOMACY

    for _, squad in ipairs(df.global.world.squads.all) do
        if squad.entity_id == group_id then
            local ctrl_id = squad.assigned_army_controller_id
            if ctrl_id ~= -1 then
                local ctrl = nil
                for _, c in ipairs(df.global.world.army_controllers.all) do
                    if c.id == ctrl_id then ctrl = c; break end
                end
                if ctrl then
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
    end
end

-- ── Mining helpers ────────────────────────────────────────────────────────────
-- Mining state is written by the eventful job hook in dwarfipelago.lua:
--   dwarfipelago/mining/surface_z  — z-level of the embark surface (captured once)
--   dwarfipelago/mining/deepest_z  — lowest z any mining job has reached
--   dwarfipelago/mining/dig_count  — cumulative count of mining jobs completed

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

-- Crafting — any Craftsdwarf's Workshop output counts as a "crafted item"
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
-- Furniture — both Make* (pre-50/Classic) and Construct* (DF50+ Steam) variants
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
map("EncrustedWithGems",       "gem")
-- Traps
map("ConstructTrap",           "trap")
map("LinkBuildingToTrigger",   "trap")
-- Standalone production checks
map("ForgeAnvil",              "anvil")
map("ConstructMillstone",      "millstone")
map("MakeMillstone",           "millstone")   -- pre-50 name if it exists
map("MakeTool",                "TOOL_FIRST")  -- subtype dispatch below

-- Minecart subtype: MakeTool item_subtype 16
local TOOL_FIRST_FLAG = { [16] = "minecart" }

function M.job_to_production_flag(job)
    if job and job.job_type then
        local flag = JOB_TO_FLAG[job.job_type]
        if flag == "TOOL_FIRST" then
            return TOOL_FIRST_FLAG[tonumber(job.item_subtype)]
        end
        return flag
    end
    return nil
end

-- Expose wealth accessors so main.lua can use them without duplicating logic.
M.fortress_wealth  = fortress_wealth
M.treasury_wealth  = treasury_wealth
M.exported_wealth  = exported_wealth

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
cmap("MakeFigurine",            "crafts")
cmap("MakeAmulet",              "crafts")
cmap("MakeScepter",             "crafts")
cmap("MakeCrown",               "crafts")
cmap("MakeRing",                "crafts")
cmap("MakeEarring",             "crafts")
cmap("MakeBracelet",            "crafts")
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
cmap("MakeShoes",               "footwear")
cmap("ConstructBag",            "bag")
cmap("MintCoins",               "coins")
cmap("MakeChain",               "rope/chain")
cmap("ForgeAnvil",              "anvil")



local TOOL_SUBTYPE_FLAG = {}
local function tools_subtype(subtype_id, flag)
    TOOL_SUBTYPE_FLAG[subtype_id] = flag
end
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

local TRAP_SUBTYPE_FLAG = {}
local function trap_subtype(subtype_id, flag)
    TRAP_SUBTYPE_FLAG[subtype_id] = flag
end
trap_subtype(1, "corkscrew")
trap_subtype(2, "ball")
trap_subtype(4, "spike")

local SHIELD_SUBTYPE_FLAG = {}
local function shield_subtype(subtype_id, flag)
    SHIELD_SUBTYPE_FLAG[subtype_id] = flag
end
shield_subtype(0, "shield")
shield_subtype(1, "buckler")
shield_subtype(2, "shield")
shield_subtype(3, "shield")
shield_subtype(4, "shield")
shield_subtype(5, "shield")

local WEAPON_SUBTYPE_FLAG = {}
local function weapon_subtype(subtype_id, flag)
    WEAPON_SUBTYPE_FLAG[subtype_id] = flag
end
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
end
helm_subtype(0, "helm")
helm_subtype(1, "headgear_clothing")
helm_subtype(2, "headgear_clothing")
helm_subtype(3, "headgear_clothing")
helm_subtype(4, "headgear_clothing")
helm_subtype(5, "headgear_clothing")
helm_subtype(6, "headgear_clothing")
helm_subtype(7, "headgear_clothing")
helm_subtype(8, "headgear_clothing")
helm_subtype(9, "headgear_clothing")
helm_subtype(10, "headgear_clothing")
helm_subtype(11, "headgear_clothing")
helm_subtype(12, "helm")
helm_subtype(13, "headgear_clothing")
helm_subtype(14, "headgear_clothing")
helm_subtype(15, "headgear_clothing")


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
-- entry resolved to nil and the table was empty — breaking all reaction flags.
local REACTION_SUBTYPE_FLAG = {}
local function reaction_subtype(name, flag)
    REACTION_SUBTYPE_FLAG[name] = flag
end
reaction_subtype("LIGNITE_TO_COAL",                 "coke_bars")
reaction_subtype("BITUMINOUS_COAL_TO_COAL",         "coke_bars")
reaction_subtype("MAKE_PEARLASH",                   "pearlash")
reaction_subtype("MAKE_PLASTER_POWDER",             "gypsum_plaster")
reaction_subtype("MAKE_QUICKLIME",                  "quicklime")
reaction_subtype("MAKE_PARCHMENT",                  "sheet")
reaction_subtype("PRESS_PLANT_PAPER",               "sheet")
reaction_subtype("MAKE_SHEET_FROM_PLANT",           "sheet")
reaction_subtype("BREW_DRINK_FROM_PLANT",           "alcohol")
reaction_subtype("BREW_DRINK_FROM_PLANT_GROWTH",    "alcohol")
reaction_subtype("MAKE_MILK_OF_LIME",               "milk_of_lime")
reaction_subtype("RENDER_FAT",                      "tallow")
reaction_subtype("PRESS_OIL_FRUIT",                 "oil")
reaction_subtype("PRESS_OIL",                       "oil")
reaction_subtype("PRESS_HONEYCOMB",                 "honey")
reaction_subtype("MAKE_SOAP_FROM_OIL",              "soap")
reaction_subtype("MAKE_SOAP_FROM_TALLOW",           "soap")


local UARMOR_SUBTYPE_FLAG = {}
local function uarmor_subtype(subtype_id, flag)
    UARMOR_SUBTYPE_FLAG[subtype_id] = flag
end
uarmor_subtype(0, "upper_body_armor")
uarmor_subtype(1, "upper_body_clothing")
uarmor_subtype(2, "upper_body_armor")
uarmor_subtype(3, "upper_body_clothing")
uarmor_subtype(4, "upper_body_clothing")
uarmor_subtype(5, "upper_body_clothing")
uarmor_subtype(6, "upper_body_clothing")
uarmor_subtype(7, "upper_body_clothing")
uarmor_subtype(8, "upper_body_clothing")
uarmor_subtype(9, "upper_body_clothing")
uarmor_subtype(10, "upper_body_clothing")
uarmor_subtype(11, "upper_body_clothing")
uarmor_subtype(12, "upper_body_armor")
uarmor_subtype(13, "upper_body_clothing")
uarmor_subtype(14, "upper_body_armor")
uarmor_subtype(15, "upper_body_clothing")
uarmor_subtype(16, "upper_body_armor")
uarmor_subtype(17, "upper_body_clothing")
uarmor_subtype(18, "upper_body_armor")
uarmor_subtype(19, "upper_body_clothing")

local GARMOR_SUBTYPE_FLAG = {}
local function garmor_subtype(subtype_id, flag)
    GARMOR_SUBTYPE_FLAG[subtype_id] = flag
end
garmor_subtype(0, "gauntlets")
garmor_subtype(1, "hand_clothing")
garmor_subtype(2, "hand_clothing")
garmor_subtype(3, "gauntlets")
garmor_subtype(4, "hand_clothing")
garmor_subtype(5, "gauntlets")
garmor_subtype(6, "hand_clothing")
garmor_subtype(7, "gauntlets")
garmor_subtype(8, "hand_clothing")
garmor_subtype(9, "gauntlets")
garmor_subtype(10, "hand_clothing")

local LARMOR_SUBTYPE_FLAG = {}
local function larmor_subtype(subtype_id, flag)
    LARMOR_SUBTYPE_FLAG[subtype_id] = flag
end
larmor_subtype(0, "lower_body_clothing")
larmor_subtype(1, "lower_body_armor")
larmor_subtype(2, "lower_body_armor")
larmor_subtype(3, "lower_body_clothing")
larmor_subtype(4, "lower_body_clothing")
larmor_subtype(5, "lower_body_clothing")
larmor_subtype(6, "lower_body_clothing")
larmor_subtype(7, "lower_body_clothing")
larmor_subtype(8, "lower_body_clothing")
larmor_subtype(9, "lower_body_armor")
larmor_subtype(10, "lower_body_clothing")
larmor_subtype(11, "lower_body_armor")
larmor_subtype(12, "lower_body_clothing")
larmor_subtype(13, "lower_body_armor")
larmor_subtype(14, "lower_body_clothing")
larmor_subtype(15, "lower_body_armor")
larmor_subtype(16, "lower_body_clothing")

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

        -- Metal is only reliable via the inorganic raw's IS_METAL flag.
        local is_metal = false
        pcall(function()
            is_metal = (mat.inorganic and mat.inorganic.flags and mat.inorganic.flags.IS_METAL) or false
        end)
        if is_metal then return "metal" end

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
        if up:find("CLAY") or up:find("PORCELAIN") or up:find("KAOLINITE") then return "ceramic" end
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
    mug=true, totem=true, window=true, battle_axe=true,
    mace=true, pick=true, short_sword=true, spear=true,
    war_hammer=true, anvil=true, coins=true,
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
    if NON_MATERIAL[flag] then return flag end
    local need_mat = dfhack.persistent.getWorldDataString('dwarfipelago/craftsanity_materials')
    if tonumber(need_mat) == 1 then
        local material_used = mat_craft_flag(job)
        if not material_used then return flag end  -- nil guard: fall back to base key
        return flag .. "_" .. material_used
    end
    return flag
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
-- Each coin item contributes (stack_size × material_value × 1000) joules.
-- Returns (list_of_{item,j}, total_j).
function M.find_fortress_coins_energy()
    local found   = {}
    local total_j = 0
    for _, item in ipairs(df.global.world.items.all) do
        local ok, t = pcall(function() return item:getType() end)
        if ok and t == df.item_type.COIN
                and not item.flags.removed
                and not item.flags.trader
                and not item.flags.in_inventory
                and not item.flags.in_job then
            local j = 0
            pcall(function()
                local ok2, mat = pcall(dfhack.matinfo.decode, item.mat_type, item.mat_index)
                if ok2 and mat and mat.material then
                    j = (item.stack_size or 1) * (mat.material.material_value or 1) * 1000
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

-- reqscript returns the script's _ENV, not the explicit return value.
-- Copy all module exports into _ENV so callers can access them as globals.
for k, v in pairs(M) do _ENV[k] = v end
return M
