--@ module = true
-- Bestiary: a census of what this world's creature raws actually contain, so the
-- megabeast-siege encounter system only ever spawns creatures that exist in the
-- loaded world. Worlds vary (some have no dragons; every world's Forgotten
-- Beasts and Titans are unique), so the wave/climax pickers query this instead of
-- assuming a fixed list.
--
-- Built once per world via refresh() (call on load) and cached. Scanning ~900
-- creatures is fast, but the cache keeps per-wave selection trivial.

local M = {}

local log = reqscript("internal/dwarfipelago/log")

-- Category -> the caste flag that defines it. All resolve on this DF build
-- (verified via the bestiary probe); reads are pcall-guarded regardless so an
-- unknown flag name on some future build degrades to "no members" not an error.
local CATEGORY_FLAGS = {
    megabeast       = "MEGABEAST",
    semimegabeast   = "SEMIMEGABEAST",
    forgotten_beast = "FEATURE_BEAST",
    titan           = "TITAN",
    night           = "NIGHT_CREATURE_HUNTER",
    large_predator  = "LARGE_PREDATOR",
}

local _cache = nil

-- True if any caste of the creature has the named flag.
local function creature_has_flag(creature, name)
    for _, caste in ipairs(creature.caste) do
        local ok, v = pcall(function() return caste.flags[name] end)
        if ok and v == true then return true end
    end
    return false
end

-- Scan creature raws into category id-lists plus a present-set of creature_ids.
local function build()
    local c = { total = 0, present = {} }
    for cat in pairs(CATEGORY_FLAGS) do c[cat] = {} end
    for _, creature in ipairs(df.global.world.raws.creatures.all) do
        c.total = c.total + 1
        local id = creature.creature_id
        c.present[id] = true
        for cat, flag in pairs(CATEGORY_FLAGS) do
            if creature_has_flag(creature, flag) then
                c[cat][#c[cat] + 1] = id
            end
        end
    end
    return c
end

-- Empty census used before a world is loaded, so callers never hit nil fields.
local function empty()
    local c = { total = 0, present = {} }
    for cat in pairs(CATEGORY_FLAGS) do c[cat] = {} end
    return c
end

-- (Re)scan the loaded world. Call once on world load; safe to call repeatedly.
function M.refresh()
    if not dfhack.isMapLoaded() then return end
    _cache = build()
    log.info(("Bestiary: %d creatures (mega=%d semi=%d FB=%d titan=%d night=%d pred=%d)"):format(
        _cache.total, #_cache.megabeast, #_cache.semimegabeast, #_cache.forgotten_beast,
        #_cache.titan, #_cache.night, #_cache.large_predator))
end

-- Cached census; lazily builds on first use if the world is loaded.
function M.census()
    if not _cache then M.refresh() end
    return _cache or empty()
end

-- Is a specific creature token present in this world?
function M.has(token)
    return M.census().present[token] == true
end

-- Random creature_id from a category present in this world, or nil if none.
local function pick_from(cat)
    local list = M.census()[cat]
    if not list or #list == 0 then return nil end
    return list[math.random(#list)]
end
function M.random_megabeast()       return pick_from("megabeast")       end
function M.random_semimegabeast()   return pick_from("semimegabeast")   end
function M.random_forgotten_beast() return pick_from("forgotten_beast") end
function M.random_titan()           return pick_from("titan")           end

-- Filter a list of candidate race tokens down to those present in this world.
-- Lets the wave pickers list an ideal roster and drop whatever this world lacks.
function M.filter_present(tokens)
    local out = {}
    for _, t in ipairs(tokens) do
        if M.has(t) then out[#out + 1] = t end
    end
    return out
end

-- reqscript returns _ENV; mirror exports so callers see them as fields.
for k, v in pairs(M) do _ENV[k] = v end
return M
