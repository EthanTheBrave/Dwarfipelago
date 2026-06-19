-- Appends the DwarfipelagoWorld preset to the DF user prefs/world_gen.txt
-- if it isn't already there.  Safe to run multiple times.
--
-- Usage (DFHack console):
--     dwarfipelago-worldgen-install

local PRESET_TITLE = "DwarfipelagoWorld"

local PRESET = [==[

[WORLD_GEN]
	[TITLE:DwarfipelagoWorld]
	[DIM:65:65]
	[EMBARK_POINTS:1504]
	[END_YEAR:120]
	[BEAST_END_YEAR:100:80]
	[REVEAL_ALL_HISTORY:1]
	[CULL_HISTORICAL_FIGURES:0]
	[ELEVATION:1:400:202:202]
	[RAINFALL:0:100:101:101]
	[TEMPERATURE:25:75:101:101]
	[DRAINAGE:0:100:101:101]
	[VOLCANISM:0:100:101:101]
	[SAVAGERY:0:100:101:101]
	[ELEVATION_FREQUENCY:1:1:1:1:1:1]
	[RAIN_FREQUENCY:1:1:1:1:1:1]
	[DRAINAGE_FREQUENCY:1:1:1:1:1:1]
	[TEMPERATURE_FREQUENCY:1:1:1:1:1:1]
	[SAVAGERY_FREQUENCY:1:1:1:1:1:1]
	[VOLCANISM_FREQUENCY:1:1:1:1:1:1]
	[POLE:NORTH_AND_OR_SOUTH]
	[MINERAL_SCARCITY:100]
	[MEGABEAST_CAP:4]
	[SEMIMEGABEAST_CAP:9]
	[TITAN_NUMBER:3]
	[TITAN_ATTACK_TRIGGER:3:0:3]
	[DEMON_NUMBER:22]
	[NIGHT_TROLL_NUMBER:11]
	[BOGEYMAN_NUMBER:11]
	[NIGHTMARE_NUMBER:11]
	[VAMPIRE_NUMBER:11]
	[WEREBEAST_NUMBER:11]
	[WEREBEAST_ATTACK_TRIGGER:2:2:2]
	[SECRET_NUMBER:22]
	[REGIONAL_INTERACTION_NUMBER:22]
	[DISTURBANCE_INTERACTION_NUMBER:22]
	[EVIL_CLOUD_NUMBER:11]
	[EVIL_RAIN_NUMBER:11]
	[GENERATE_DIVINE_MATERIALS:1]
	[GENERATE_MYTHICAL_MATERIALS:1]
	[ALLOW_MYTHICAL_HEALING:1]
	[ALLOW_DIVINATION:1]
	[ALLOW_DEMONIC_EXPERIMENTS:1]
	[ALLOW_NECROMANCER_EXPERIMENTS:1]
	[ALLOW_NECROMANCER_LIEUTENANTS:1]
	[ALLOW_NECROMANCER_GHOULS:1]
	[ALLOW_NECROMANCER_SUMMONS:1]
	[GOOD_SQ_COUNTS:6:63:127]
	[EVIL_SQ_COUNTS:6:63:127]
	[PEAK_NUMBER_MIN:3]
	[PARTIAL_OCEAN_EDGE_MIN:1]
	[COMPLETE_OCEAN_EDGE_MIN:0]
	[VOLCANO_MIN:5]
	[REGION_COUNTS:SWAMP:66:0:0]
	[REGION_COUNTS:DESERT:66:0:0]
	[REGION_COUNTS:FOREST:264:2:2]
	[REGION_COUNTS:MOUNTAINS:528:0:0]
	[REGION_COUNTS:OCEAN:528:0:0]
	[REGION_COUNTS:GLACIER:0:0:0]
	[REGION_COUNTS:TUNDRA:0:0:0]
	[REGION_COUNTS:GRASSLAND:264:2:2]
	[REGION_COUNTS:HILLS:528:0:0]
	[EROSION_CYCLE_COUNT:250]
	[RIVER_MINS:25:25]
	[PERIODICALLY_ERODE_EXTREMES:1]
	[OROGRAPHIC_PRECIPITATION:1]
	[SUBREGION_MAX:2750]
	[CAVERN_LAYER_COUNT:3]
	[CAVERN_LAYER_OPENNESS_MIN:0]
	[CAVERN_LAYER_OPENNESS_MAX:100]
	[CAVERN_LAYER_PASSAGE_DENSITY_MIN:0]
	[CAVERN_LAYER_PASSAGE_DENSITY_MAX:100]
	[CAVERN_LAYER_WATER_MIN:0]
	[CAVERN_LAYER_WATER_MAX:100]
	[HAVE_BOTTOM_LAYER_1:1]
	[HAVE_BOTTOM_LAYER_2:1]
	[LEVELS_ABOVE_GROUND:15]
	[LEVELS_ABOVE_LAYER_1:5]
	[LEVELS_ABOVE_LAYER_2:1]
	[LEVELS_ABOVE_LAYER_3:1]
	[LEVELS_ABOVE_LAYER_4:1]
	[LEVELS_ABOVE_LAYER_5:2]
	[LEVELS_AT_BOTTOM:1]
	[CAVE_MIN_SIZE:5]
	[CAVE_MAX_SIZE:25]
	[MOUNTAIN_CAVE_MIN:6]
	[NON_MOUNTAIN_CAVE_MIN:12]
	[MYTHICAL_SITE_NUM:200]
	[ALL_CAVES_VISIBLE:0]
	[SHOW_EMBARK_TUNNEL:2]
	[TOTAL_CIV_NUMBER:20]
	[TOTAL_CIV_POPULATION:15000]
	[SITE_CAP:400]
	[PLAYABLE_CIVILIZATION_REQUIRED:1]
	[ELEVATION_RANGES:528:1056:528]
	[RAIN_RANGES:264:528:264]
	[DRAINAGE_RANGES:264:528:264]
	[SAVAGERY_RANGES:264:528:264]
	[VOLCANISM_RANGES:264:528:264]
]==]

-- Locate the DF user data directory where world_gen.txt actually lives.
-- Steam DF on Windows stores user prefs in %APPDATA%\Bay 12 Games\Dwarf Fortress\
-- not in the DF install directory.
local function find_prefs_path()
    local appdata = os.getenv("APPDATA")
    if appdata and appdata ~= "" then
        local candidate = appdata .. "/Bay 12 Games/Dwarf Fortress/prefs/world_gen.txt"
        local f = io.open(candidate, "r")
        if f then f:close(); return candidate end
        -- File doesn't exist yet but directory might — still valid path to create into
        local dir_check = io.open(appdata .. "/Bay 12 Games/Dwarf Fortress/prefs/", "r")
        if dir_check then dir_check:close(); return candidate end
    end
    -- Fallback: DF install dir (classic/Linux/Mac layout)
    local ok, base = pcall(dfhack.getDFPath)
    if ok and base and base ~= "" then
        return base .. "/prefs/world_gen.txt"
    end
    return nil
end

local prefs_path = find_prefs_path()
if not prefs_path then
    qerror("Could not locate prefs/world_gen.txt — is DF installed correctly?")
end

-- Read existing content
local existing = ""
local rf = io.open(prefs_path, "r")
if rf then
    existing = rf:read("*a")
    rf:close()
end

if existing:find(PRESET_TITLE, 1, true) then
    print("[Dwarfipelago] World gen preset is already installed in " .. prefs_path)
    return
end

local wf = io.open(prefs_path, "a")
if not wf then
    qerror("Could not open " .. prefs_path .. " for writing")
end
wf:write(PRESET)
wf:close()

print("[Dwarfipelago] World gen preset installed to:")
print("  " .. prefs_path)
print("[Dwarfipelago] Restart DF for DwarfipelagoWorld to appear in the preset list.")
