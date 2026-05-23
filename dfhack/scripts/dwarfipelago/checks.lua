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
}

-- ── Production flag helpers ───────────────────────────────────────────────────
-- Flags are set by the eventful job hook in main.lua and stored in site data.
-- Key format: "dwarfipelago/prod/<flag_name>"

function M.set_production_flag(flag)
    dfhack.persistent.setSiteData("dwarfipelago/prod/" .. flag, "1")
end

function M.production_flag(flag)
    local val = dfhack.persistent.getSiteData("dwarfipelago/prod/" .. flag)
    return val == "1"
end

function M.set_trade_flag(flag)
    dfhack.persistent.setSiteData("dwarfipelago/trade/" .. flag, "1")
end

function M.trade_flag(flag)
    local val = dfhack.persistent.getSiteData("dwarfipelago/trade/" .. flag)
    return val == "1"
end

-- ── Job type → production flag mapping ───────────────────────────────────────
-- Called by main.lua's eventful job hook to classify completed jobs.

-- DFHack job type enum values (df.job_type) — abbreviated list.
-- Full list: https://docs.dfhack.org/en/latest/docs/dev/Lua%20API.html
local JOB_TO_FLAG = {
    -- Crafting
    [df.job_type.MakeCrafts]        = "crafted_item",
    [df.job_type.CarveStatue]       = "crafted_item",
    [df.job_type.MakeTotem]         = "crafted_item",
    -- Weapons / armor
    [df.job_type.MakeWeapon]        = "weapon",
    [df.job_type.MakeAmmo]          = "weapon",
    [df.job_type.MakeArmor]         = "armor",
    [df.job_type.MakeHelm]          = "armor",
    [df.job_type.MakeGloves]        = "armor",
    [df.job_type.MakeBoots]         = "armor",
    [df.job_type.MakePants]         = "armor",
    [df.job_type.MakeShield]        = "armor",
    -- Furniture
    [df.job_type.MakeTable]         = "table",
    [df.job_type.MakeChair]         = "furniture",
    [df.job_type.MakeChest]         = "chest",
    [df.job_type.MakeCabinet]       = "furniture",
    [df.job_type.MakeBed]           = "bed",
    [df.job_type.MakeDoor]          = "furniture",
    [df.job_type.MakeFloodgate]     = "furniture",
    [df.job_type.MakeBarrel]        = "barrel",
    [df.job_type.MakeBucket]        = "furniture",
    [df.job_type.MakeCage]          = "cage",
    [df.job_type.MakeMechanism]     = "mechanism",
    -- Food / drink
    [df.job_type.PrepareMeal]       = "meal",
    [df.job_type.BrewDrink]         = "brew",
    -- Materials
    [df.job_type.SmeltOre]          = "metal_bar",
    [df.job_type.MeltMetalObject]   = "metal_bar",
    [df.job_type.CutBlock]          = "stone_block",
    [df.job_type.WeaveCloth]        = "cloth",
    [df.job_type.ProcessPlants]     = "cloth",  -- also produces thread
    [df.job_type.TanHide]           = "leather",
    [df.job_type.CutGems]           = "gem",
    [df.job_type.EncrustedWithGems] = "gem",
    -- Traps
    [df.job_type.ConstructTrap]     = "trap",
    [df.job_type.LinkBuildingToTrigger] = "trap",
}

function M.job_to_production_flag(job)
    if job and job.job_type then
        return JOB_TO_FLAG[job.job_type]
    end
    return nil
end

-- Expose wealth accessor so main.lua can use it for the goal check
-- without duplicating the DF50 / Classic fallback logic.
M.fortress_wealth = fortress_wealth

return M
