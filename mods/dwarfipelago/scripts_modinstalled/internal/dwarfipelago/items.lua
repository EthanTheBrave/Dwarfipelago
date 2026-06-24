--@ module = true
-- Item spawning for Dwarfipelago.
-- Called when the AP client delivers an item to the fortress.
-- Each handler uses dfhack.run_script or direct df API calls to apply the effect.

local M = {}

local log      = reqscript("internal/dwarfipelago/log")
local bestiary = reqscript("internal/dwarfipelago/bestiary")

-- ── Helpers ───────────────────────────────────────────────────────────────────

-- Return the center tile of the first trade depot in the fortress, or nil.
-- The depot is 5×5; (x1+2, y1+2) is its center tile.
local function find_trade_depot_center()
    for _, bld in ipairs(df.global.world.buildings.all) do
        if df.building_tradedepotst:is_instance(bld) then
            return bld.x1 + 2, bld.y1 + 2, bld.z
        end
    end
    return nil
end

-- Spawn items at the trade depot (the designated AP delivery point).
-- Falls back to a living citizen's tile if no depot exists yet.
-- createitem places items at the keyboard cursor, so we set the cursor first.
--
-- Returns the number of items actually created. createitem PRINTS errors like
-- "Unrecognized material!" instead of raising, so we capture its output via
-- run_command_silent and treat any error marker as a failure. This lets callers
-- reliably fall back to a different token (e.g. weapon -> steel bars).
local function spawn_item(item_type, material, quantity)
    quantity = quantity or 1

    -- Prefer the trade depot center; fall back to any living citizen.
    local cx, cy, cz = find_trade_depot_center()
    if cx then
        df.global.cursor.x = cx
        df.global.cursor.y = cy
        df.global.cursor.z = cz
    else
        local anchored = false
        for _, unit in ipairs(df.global.world.units.active) do
            if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
                df.global.cursor.x = unit.pos.x
                df.global.cursor.y = unit.pos.y
                df.global.cursor.z = unit.pos.z
                anchored = true
                break
            end
        end
        if not anchored then
            log.error("spawn_item: no depot or citizen - cannot place " .. item_type)
            return 0
        end
    end

    -- Prefer run_command_silent so we can read createitem's output and detect
    -- bad-token failures; fall back to run_command (no detection) if it's absent.
    local has_silent = type(dfhack.run_command_silent) == "function"
    local created = 0
    for _ = 1, quantity do
        -- e.g. createitem SMALLGEM INORGANIC:RUBY
        if has_silent then
            local ok, r1, r2 = pcall(dfhack.run_command_silent, "createitem", item_type, material)
            -- run_command_silent returns output + status (order-agnostic capture).
            local out = (type(r1) == "string" and r1)
                     or (type(r2) == "string" and r2) or ""
            if (not ok) or out:find("nrecognized") then
                log.error(("Failed to spawn %s [%s]: %s"):format(
                    item_type, material, out ~= "" and out:gsub("%s+", " ") or "createitem error"))
            else
                created = created + 1
            end
        else
            local ok = pcall(dfhack.run_command, "createitem", item_type, material)
            if ok then
                created = created + 1
            else
                log.error(("Failed to spawn %s [%s]"):format(item_type, material))
            end
        end
    end
    return created
end

-- Show an AP announcement. If pos ({x,y,z}) is given, the announcement is
-- clickable in the announcements list and zooms the map to that tile.
-- Falls back to a plain showAnnouncement if zoom fails (e.g. bad pos).
local function announce(msg, pos, atype)
    if pos then
        local ok = pcall(function()
            dfhack.gui.showZoomAnnouncement(
                atype or df.announcement_type.CARAVAN_ARRIVAL,
                pos, "[AP] " .. msg, COLOR_GREEN, true)
        end)
        if ok then return end
    end
    dfhack.gui.showAnnouncement("[AP] " .. msg, COLOR_GREEN, true)
end

-- Returns the trade depot center as a pos table, or nil if no depot exists.
local function depot_pos()
    local cx, cy, cz = find_trade_depot_center()
    if cx then return {x=cx, y=cy, z=cz} end
end

-- Shorthand for announcements about items spawned at the trade depot.
local function announce_at_depot(msg)
    announce(msg, depot_pos())
end

-- Version-safe unit display name. DFHack moved name translation across versions:
--   newer: dfhack.units.getReadableName(unit) / dfhack.translation.translateName(name)
--   older: dfhack.TranslateName(name)
-- Returns "" if none are available.
local function unit_display_name(unit)
    local name = ""
    pcall(function()
        if dfhack.units.getReadableName then
            name = dfhack.units.getReadableName(unit) or ""
        elseif dfhack.translation and dfhack.translation.translateName then
            name = dfhack.translation.translateName(dfhack.units.getVisibleName(unit)) or ""
        elseif dfhack.TranslateName then
            name = dfhack.TranslateName(dfhack.units.getVisibleName(unit)) or ""
        end
    end)
    return name
end

-- Return the position of a living citizen as a spawn anchor (guaranteed walkable).
-- Falls back to map centre if no citizens are found.
local function get_fort_spawn_pos()
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
            return tostring(unit.pos.x), tostring(unit.pos.y), tostring(unit.pos.z)
        end
    end
    local map = df.global.world.map
    return tostring(math.floor(map.x_count / 2)),
           tostring(math.floor(map.y_count / 2)),
           tostring(map.z_count - 1)
end

-- Find the entity ID of a goblin civilisation in the world so spawned goblins
-- belong to an enemy faction. Returns -1 if none found (e.g. goblin-free worlds).
local function find_goblin_civ_id()
    local creatures = df.global.world.raws.creatures.all
    for _, ent in ipairs(df.global.world.entities.all) do
        local ok, id = pcall(function()
            if ent.race >= 0 and ent.race < #creatures then
                if creatures[ent.race].creature_id == "GOBLIN" then
                    return ent.id
                end
            end
        end)
        if ok and id then return id end
    end
    return -1
end

-- Find a civilization entity id for a creature token (e.g. "ELF", "HUMAN",
-- "DWARF"), preferring an actual Civilization entity. Returns nil if none exist.
local function find_civ_id(token)
    local creatures = df.global.world.raws.creatures.all
    local fallback
    for _, ent in ipairs(df.global.world.entities.all) do
        local ok, is_match, is_civ = pcall(function()
            local r = ent.race
            local m = (r >= 0 and r < #creatures and creatures[r].creature_id == token)
            return m, (ent.type == df.historical_entity_type.Civilization)
        end)
        if ok and is_match then
            fallback = fallback or ent.id
            if is_civ then return ent.id end
        end
    end
    return fallback
end

-- ── Item handlers: trade goods ────────────────────────────────────────────────
-- createitem syntax: <item-token> <material>
--   Cut gems  → SMALLGEM INORGANIC:<gem>   (SMALLGEM = cut gem; ROUGH = uncut)
--   Metal bars → BAR INORGANIC:<metal>
--   Figurines  → FIGURINE INORGANIC:<stone>

local function recv_cut_sapphire()
    spawn_item("SMALLGEM", "INORGANIC:SAPPHIRE")
    announce_at_depot("Received: Cut Sapphire!")
end

local function recv_cut_ruby()
    spawn_item("SMALLGEM", "INORGANIC:RUBY")
    announce_at_depot("Received: Cut Ruby!")
end

local function recv_cut_diamond()
    -- Diamond tokens vary by world gen; try known variants then scan raws.
    local tokens = {
        "INORGANIC:DIAMOND_CLEAR", "INORGANIC:DIAMOND_BLUE", "INORGANIC:DIAMOND_RED",
        "INORGANIC:DIAMOND_YELLOW", "INORGANIC:DIAMOND_BROWN", "INORGANIC:DIAMOND_BLACK",
    }
    for _, raw in ipairs(df.global.world.raws.inorganics) do
        local id = raw.id or ""
        if id:find("DIAMOND") then table.insert(tokens, "INORGANIC:" .. id) end
    end
    local spawned = false
    for _, tok in ipairs(tokens) do
        if dfhack.matinfo.find(tok) and spawn_item("SMALLGEM", tok) > 0 then
            spawned = true
            break
        end
    end
    if not spawned then
        spawn_item("SMALLGEM", "INORGANIC:SAPPHIRE")
        log.warn("recv_cut_diamond: no diamond material found, substituted sapphire")
    end
    announce_at_depot("Received: Cut Diamond!")
end

local function recv_gold_bar()
    spawn_item("BAR", "INORGANIC:GOLD")
    announce_at_depot("Received: Gold Bar!")
end

local function recv_silver_bar()
    spawn_item("BAR", "INORGANIC:SILVER")
    announce_at_depot("Received: Silver Bar!")
end

local function recv_steel_bar()
    spawn_item("BAR", "INORGANIC:STEEL")
    announce_at_depot("Received: Steel Bar!")
end

local function recv_masterwork_craft()
    -- FIGURINE is the correct item token for a craft figurine.
    spawn_item("FIGURINE", "INORGANIC:OBSIDIAN")
    announce_at_depot("Received: Masterwork Craft!")
end

-- ── Item handlers: resources ──────────────────────────────────────────────────
-- createitem syntax:
--   Food (edible growths) → PLANT_GROWTH PLANT:<plant>:<growth>
--   Wood logs             → WOOD PLANT_MAT:<tree>:WOOD
--   Iron ore boulders     → BOULDER INORGANIC:<ore>
--   Fuel bars             → BAR COAL:COKE  (or COAL:CHARCOAL)

local function recv_food_bundle()
    for _ = 1, 5 do
        spawn_item("PLANT_GROWTH", "PLANT:MUSHROOM_HELMET_PLUMP:MUSHROOM")
    end
    announce_at_depot("Received: Food Bundle (5 plump helmets)!")
end

local function recv_wood_bundle()
    for _ = 1, 5 do
        spawn_item("WOOD", "PLANT_MAT:OAK:WOOD")
    end
    announce_at_depot("Received: Wood Bundle (5 logs)!")
end

local function recv_iron_ore_bundle()
    for _ = 1, 5 do
        spawn_item("BOULDER", "INORGANIC:LIMONITE")
    end
    announce_at_depot("Received: Iron Ore Bundle!")
end

local function recv_coal_bundle()
    for _ = 1, 3 do
        spawn_item("BAR", "COAL:COKE")
    end
    announce_at_depot("Received: Coal Bundle!")
end

-- ── Item handlers: filler items ──────────────────────────────────────────────
-- These are items the DF world contributes to the multiworld pool. The DF
-- player may receive them back if the AP server places them at DF locations.

local function recv_dwarven_ale()
    spawn_item("DRINK", "PLANT_MAT:MUSHROOM_HELMET_PLUMP:DRINK", 3)
    announce_at_depot("Received: Dwarven Ale! A cask of plump helmet brew.")
end

local function recv_stone_trinket()
    spawn_item("FIGURINE", "INORGANIC:MARBLE")
    announce_at_depot("Received: Stone Trinket! A finely carved marble figurine.")
end

local function recv_bone_crafts()
    spawn_item("FIGURINE", "CREATURE_MAT:DWARF:BONE")
    announce_at_depot("Received: Bone Crafts!")
end

local function recv_raw_ore()
    spawn_item("BOULDER", "INORGANIC:MAGNETITE", 3)
    announce_at_depot("Received: Raw Ore! Magnetite boulders ready for smelting.")
end

local function recv_wooden_cup()
    spawn_item("GOBLET", "PLANT_MAT:OAK:WOOD")
    announce_at_depot("Received: Wooden Cup!")
end

-- New useful industry-material filler. Each falls back to a known-good spawn if
-- the primary material/token isn't accepted by this DF version's createitem.
local function recv_flux_stone()
    spawn_item("BOULDER", "INORGANIC:LIMESTONE", 4)
    announce("Received: Flux Stone! Limestone for steelmaking.")
end

local function recv_pig_iron_bar()
    if spawn_item("BAR", "INORGANIC:PIG_IRON", 2) == 0 then
        spawn_item("BAR", "INORGANIC:IRON", 2)
    end
    announce("Received: Pig Iron Bars!")
end

local function recv_charcoal()
    if spawn_item("BAR", "COAL:CHARCOAL", 3) == 0 then
        spawn_item("BAR", "COAL:COKE", 3)
    end
    announce("Received: Charcoal! Fuel for forges and furnaces.")
end

local function recv_cloth_bolt()
    spawn_item("CLOTH", "PLANT_MAT:GRASS_TAIL_PIG:THREAD", 3)
    announce("Received: Cloth Bolts! Ready for the loom or clothier.")
end

local function recv_tanned_leather()
    if spawn_item("SKIN_TANNED", "CREATURE_MAT:COW:LEATHER", 3) == 0 then
        spawn_item("CLOTH", "PLANT_MAT:GRASS_TAIL_PIG:THREAD", 3)
    end
    announce("Received: Tanned Leather!")
end

-- Bag of sand for glassmaking. Sand isn't a free-standing item - it lives inside
-- a bag - so createitem (one item at a time) can't make it. We use the lower-level
-- dfhack.items.createItem API (which returns handles): make a cloth bag (BOX) and
-- a POWDER_MISC of a SOIL_SAND inorganic, then nest the sand in the bag. Falls
-- back to limestone flux if anything in the chain isn't supported on this build.
local function recv_bag_of_sand()
    local ok, err = pcall(function()
        local unit
        for _, u in ipairs(df.global.world.units.active) do
            if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then unit = u; break end
        end
        if not unit then error("no living citizen to anchor the spawn") end

        local function find_mat(tokens)
            for _, t in ipairs(tokens) do
                local mi = dfhack.matinfo.find(t)
                if mi then return mi.type, mi.index end
            end
        end
        -- Bag fabric.
        local ct, ci = find_mat({ "CREATURE_MAT:COW:LEATHER", "PLANT_MAT:GRASS_TAIL_PIG:THREAD" })  -- leather: moveToContainer works (thread fails)
        -- Sand: any inorganic flagged SOIL_SAND (what the glass furnace accepts).
        local st, si
        for i, raw in ipairs(df.global.world.raws.inorganics) do
            if raw.flags and raw.flags.SOIL_SAND then st, si = 0, i; break end
        end
        if not st then
            st, si = find_mat({ "INORGANIC:SAND_TAN", "INORGANIC:SAND_BLACK",
                                "INORGANIC:SAND_YELLOW", "INORGANIC:SAND_WHITE", "INORGANIC:SAND_RED" })
        end
        if not ct or not st then error("could not resolve bag/sand material") end

        -- Deliver to the trade depot (the AP drop point), like spawn_item does.
        local dx, dy, dz = find_trade_depot_center()

        local made = 0
        for _ = 1, 3 do
            local bag  = dfhack.items.createItem(unit, df.item_type.BAG, -1, ct, ci, false)
            local sand = dfhack.items.createItem(unit, df.item_type.POWDER_MISC, -1, st, si, false)
            if bag and bag[1] and sand and sand[1] then
                dfhack.items.moveToContainer(sand[1], bag[1])
                if dx then dfhack.items.moveToGround(bag[1], {x = dx, y = dy, z = dz}) end
                made = made + 1
            end
        end
        if made == 0 then error("createItem produced no items") end
    end)
    if not ok then
        log.error("bag_of_sand: " .. tostring(err))
        spawn_item("BOULDER", "INORGANIC:LIMESTONE", 3)  -- useful fallback so the gift isn't wasted
        announce("Received: a Sand shipment (delivered as flux - bag-of-sand spawn unavailable).")
        return
    end
    announce("Received: Bags of Sand! Ready for the glass furnace.")
end

-- Raw clay as mineable clay STONE boulders. Kilns gather earthenware/stoneware
-- clay from tiles (no item works for that), but kaolinite is a real stone used for
-- porcelain, so kaolinite boulders may be usable there. Falls back to fire clay
-- boulders, then fired clay blocks (always-useful construction material).
local function recv_raw_clay()
    local n = spawn_item("BOULDER", "INORGANIC:KAOLINITE", 4)
    if n == 0 then n = spawn_item("BOULDER", "INORGANIC:FIRE_CLAY", 4) end
    if n == 0 then n = spawn_item("BLOCKS", "INORGANIC:FIRE_CLAY", 4) end
    announce("Received: Raw Clay! Clay stone (kaolinite for porcelain).")
end

-- Low-grade (copper) tools/gear - useful recovery, intentionally rare.
local function recv_copper_pick()
    if spawn_item("WEAPON:ITEM_WEAPON_PICK", "INORGANIC:COPPER") == 0 then
        spawn_item("BAR", "INORGANIC:COPPER", 2)
    end
    announce("Received: a Copper Pick. Crude, but it digs.")
end

local function recv_copper_axe()
    if spawn_item("WEAPON:ITEM_WEAPON_AXE_BATTLE", "INORGANIC:COPPER") == 0 then
        spawn_item("BAR", "INORGANIC:COPPER", 2)
    end
    announce("Received: a Copper Axe. Good for trees and trouble.")
end

local function recv_copper_short_sword()
    if spawn_item("WEAPON:ITEM_WEAPON_SWORD_SHORT", "INORGANIC:COPPER") == 0 then
        spawn_item("BAR", "INORGANIC:COPPER", 2)
    end
    announce("Received: a Copper Short Sword.")
end

-- ── Item handlers: useful items ───────────────────────────────────────────────

local function recv_masterwork_crafts()
    spawn_item("FIGURINE", "INORGANIC:OBSIDIAN")
    announce_at_depot("Received: Masterwork Crafts! A masterwork obsidian figurine.")
end

local function recv_dwarven_steel_sword()
    -- Try to spawn an actual short sword; fall back to steel bars if the weapon
    -- token isn't accepted by this DF version's createitem.
    if spawn_item("WEAPON:ITEM_WEAPON_SWORD_SHORT", "INORGANIC:STEEL") == 0 then
        spawn_item("BAR", "INORGANIC:STEEL", 3)
    end
    announce_at_depot("Received: Dwarven Steel Sword!")
end

local function recv_fine_cloth()
    -- Pig tail is the iconic dwarven fibre crop; its thread material makes cloth.
    spawn_item("CLOTH", "PLANT_MAT:GRASS_TAIL_PIG:THREAD", 3)
    announce_at_depot("Received: Fine Cloth!")
end

local function recv_adamantine_fiber()
    -- Adamantine cloth material token may vary by DF version; fall back to cloth.
    if spawn_item("CLOTH", "INORGANIC:ADAMANTINE", 2) == 0 then
        spawn_item("CLOTH", "PLANT_MAT:GRASS_TAIL_PIG:THREAD", 3)
    end
    announce_at_depot("Received: Adamantine Fiber!")
end

-- ── Item handlers: livestock ──────────────────────────────────────────────────
-- Spawns a small group of tame, fortress-owned animals. Always guarantees at
-- least one male (caste 0) and one female (caste 1) so the pair can breed.
-- Total count is 2-5; extras are random sex.

local function spawn_livestock(race_token, name)
    local tokens = type(race_token) == "table" and race_token or {race_token}
    local race_idx
    for _, tok in ipairs(tokens) do
        for i, cr in ipairs(df.global.world.raws.creatures.all) do
            if cr.creature_id == tok then race_idx = i; break end
        end
        if race_idx then break end
    end
    if not race_idx then
        log.error("spawn_livestock: creature not found in raws: " .. table.concat(tokens, "/"))
        announce_at_depot(("Received: %s! (spawn failed - creature absent from world raws)"):format(name))
        return
    end

    local ncastes = 0
    pcall(function()
        for _ in ipairs(df.global.world.raws.creatures.all[race_idx].caste) do
            ncastes = ncastes + 1
        end
    end)
    local female_caste = math.max(1, ncastes - 1)

    -- Guaranteed pair first, then 0-3 random extras for a total of 2-5.
    local count = math.random(2, 5)
    local castes_to_spawn = {0, female_caste}
    for _ = 1, count - 2 do
        table.insert(castes_to_spawn, math.random(0, female_caste))
    end

    local dx, dy, dz = find_trade_depot_center()
    if not dx then
        local sx, sy, sz = get_fort_spawn_pos()
        dx, dy, dz = tonumber(sx), tonumber(sy), tonumber(sz)
    end

    local cur_year = df.global.cur_year
    local spawned = 0
    for _, caste in ipairs(castes_to_spawn) do
        local ok, err = pcall(function()
            local unit = dfhack.units.create(race_idx, caste)
            if not unit then error("create returned nil") end
            pcall(function() unit.birth_year = cur_year - math.random(2, 5) end)
            if not dfhack.units.teleport(unit, {x = dx, y = dy, z = dz}) then
                unit.pos.x, unit.pos.y, unit.pos.z = dx, dy, dz
            end
            df.global.world.units.active:insert('#', unit)
            -- Assign to the player's civilization so the animal appears as owned.
            pcall(function() unit.civ_id = df.global.plotinfo.civ_id end)
            pcall(function() unit.civ_id = df.global.ui.civ_id end)
            pcall(function() unit.flags1.tame = true end)
            pcall(function() unit.flags2.tame = true end)
            pcall(function() unit.flags3.tame = true end)
            pcall(function() unit.flags1.active_invader = false end)
            pcall(function() unit.flags1.marauder       = false end)
            pcall(function()
                unit.training_level = df.animal_training_level.Domesticated
            end)
            dfhack.units.makeown(unit)
            spawned = spawned + 1
        end)
        if not ok then
            log.error(("spawn_livestock(%s): %s"):format(race_token, tostring(err)))
        end
    end

    if spawned > 0 then
        announce_at_depot(("Received: %s! %d animal(s) have joined the fortress."):format(name, spawned))
    else
        announce_at_depot(("Received: %s! (spawn failed - check DFHack console)"):format(name))
    end
end

local function recv_breeding_pigs()     spawn_livestock("PIG",                  "Breeding Pigs")     end
local function recv_breeding_chickens() spawn_livestock("BIRD_CHICKEN",          "Breeding Chickens") end
local function recv_breeding_alpacas()  spawn_livestock("ALPACA",                "Breeding Alpacas")  end
local function recv_breeding_cows()     spawn_livestock({"CATTLE", "COW"},       "Breeding Cows")     end
local function recv_breeding_sheep()    spawn_livestock("SHEEP",                 "Breeding Sheep")    end
local function recv_breeding_yaks()     spawn_livestock("YAK",                   "Breeding Yaks")     end

local function recv_sunlight_tonic()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/sunlight_tonic", "1")
    announce_at_depot("Sunlight Tonic received! Your dwarves may now walk freely in sunlight.")
end

-- ── Item handlers: progression gate items ────────────────────────────────────
-- These items are purely flag-based - receiving them writes a persistent key
-- that the goal-completion checks in dwarfipelago.lua read back.

local function recv_artifact_weapon()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/artifact_weapon", "1")
    -- Deliver an artifact-tier weapon (adamantine), falling back to steel.
    if spawn_item("WEAPON:ITEM_WEAPON_AXE_BATTLE", "INORGANIC:ADAMANTINE") == 0 then
        if spawn_item("WEAPON:ITEM_WEAPON_AXE_BATTLE", "INORGANIC:STEEL") == 0 then
            spawn_item("BAR", "INORGANIC:STEEL", 3)
        end
    end
    dfhack.gui.showAnnouncement(
        "[AP] An Artifact Weapon has been delivered to your fortress! Your champions stand ready.",
        COLOR_GREEN, true)
    print("[Dwarfipelago] Progression item received: Artifact Weapon")
end

local function recv_artifact_armor()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/artifact_armor", "1")
    -- A full set of artifact-tier armor (adamantine), falling back to steel.
    local mat = "INORGANIC:ADAMANTINE"
    if spawn_item("ARMOR:ITEM_ARMOR_BREASTPLATE", mat) == 0 then
        mat = "INORGANIC:STEEL"
        spawn_item("ARMOR:ITEM_ARMOR_BREASTPLATE", mat)
    end
    spawn_item("HELM:ITEM_HELM_HELM",          mat)
    spawn_item("SHIELD:ITEM_SHIELD_SHIELD",    mat)
    spawn_item("GLOVES:ITEM_GLOVES_GAUNTLETS", mat)
    spawn_item("PANTS:ITEM_PANTS_GREAVES",     mat)
    spawn_item("SHOES:ITEM_SHOES_BOOTS",       mat)
    dfhack.gui.showAnnouncement(
        "[AP] Artifact Armor has been delivered to your soldiers! Your defenders are emboldened.",
        COLOR_GREEN, true)
    print("[Dwarfipelago] Progression item received: Artifact Armor")
end

-- Create a genuine artifact door at the depot. Built artifact doors are
-- indestructible, so we must set the artifact flag + Artifact quality on the
-- item (createitem alone makes an ordinary door). Returns true on success.
local function spawn_artifact_door()
    local result = false
    pcall(function()
        local unit
        for _, u in ipairs(df.global.world.units.active) do
            if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then unit = u; break end
        end
        if not unit then return end

        local mt, mi
        for _, tok in ipairs({ "INORGANIC:ADAMANTINE", "INORGANIC:PLATINUM",
                               "INORGANIC:GOLD", "INORGANIC:MARBLE" }) do
            local found = dfhack.matinfo.find(tok)
            if found then mt, mi = found.type, found.index; break end
        end
        if not mt then return end

        local made = dfhack.items.createItem(unit, df.item_type.DOOR, -1, mt, mi, false)
        local door = made and made[1]
        if not door then return end

        -- Register a genuine artifact: a record in world.artifacts.all that the
        -- door links to via a general_ref. Order matters - the record is added
        -- first, then the item is linked and flagged. If any step fails the door
        -- stays a plain, BUILDABLE door rather than the half-set "artifact with no
        -- record" state that dwarves refuse to haul/build.
        pcall(function()
            local arts = df.global.world.artifacts
            local newid = 0
            for _, a in ipairs(arts.all) do
                if a.id and a.id >= newid then newid = a.id + 1 end
            end
            local rec = df.artifact_record:new()
            rec.id   = newid
            rec.item = door
            arts.all:insert('#', rec)
            local ref = df.general_ref_is_artifactst:new()
            ref.artifact_id = newid
            door.general_refs:insert('#', ref)
            door.flags.artifact = true
            door.quality = df.item_quality.Artifact
        end)

        local dx, dy, dz = find_trade_depot_center()
        if dx then pcall(function() dfhack.items.moveToGround(door, { x = dx, y = dy, z = dz }) end) end
        result = true
    end)
    return result
end

local function recv_master_builders_codex()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/master_builders_codex", "1")
    -- A genuine artifact door (indestructible once built). Fall back to a plain
    -- best-material door if the artifact path fails on this build.
    if not spawn_artifact_door() then
        for _, m in ipairs({ "INORGANIC:ADAMANTINE", "INORGANIC:PLATINUM",
                             "INORGANIC:GOLD", "INORGANIC:MARBLE" }) do
            if spawn_item("DOOR", m) > 0 then break end
        end
    end
    dfhack.gui.showAnnouncement(
        "[AP] A Master Builder's Codex arrives with an artifact door! To build it, raise the " ..
        "build material list's Max Quality filter to Artifact (it's hidden at Masterful by default).",
        COLOR_GREEN, true)
    print("[Dwarfipelago] Progression item received: Master Builder's Codex")
end

local function recv_king_remains()
    amt = dfhack.persistent.getWorldDataString("dwarfipelago/unlock/RotGK")
    if amt == nil or amt == 0 then
        dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/RotGK", "1")
    else
        new_amt = tonumber(amt) + 1
        dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/RotGK", tostring(new_amt))
    end
    print("[Dwarfipelago] Progression item received: Remains of the Great King")
end

-- ── Item handlers: junk traps (AP filler trap items sent back to DF) ─────────
-- These items land back in the DF player's inventory as padding. They have no
-- meaningful in-game effect - just a flavour announcement.

local function recv_cave_fisher_silk()
    -- Silk cloth woven from cave fisher silk. CLOTH item, creature silk material.
    spawn_item("CLOTH", "CREATURE_MAT:CAVE_FISHER:SILK", 2)
    announce_at_depot("A bundle of cave fisher silk has been deposited at your trade depot.")
end

local function recv_dwarf_bones()
    -- A grim totem carved from dwarf bone. TOTEM item, creature bone material.
    spawn_item("TOTEM", "CREATURE_MAT:DWARF:BONE")
    announce_at_depot("A grim package of dwarf bones has arrived. An ill omen...")
end

local function recv_goblin_trophy()
    -- A goblin-bone totem - the classic war trophy.
    spawn_item("TOTEM", "CREATURE_MAT:GOBLIN:BONE")
    announce_at_depot("A goblin trophy has been delivered. Someone out there is mocking you.")
end

-- Search for a walkable surface tile (outside == true) near a map edge.
-- Biases toward the embark perimeter so spawned hostiles have to path inward,
-- giving dwarves time to react. Returns x, y, z or nil on failure.
local function find_surface_spawn_pos()
    if not dfhack.isMapLoaded() then return nil end
    local map = df.global.world.map

    -- Estimate surface z from a living citizen (fallback: upper portion of map).
    local surface_z = math.floor(map.z_count * 0.7)
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
            surface_z = unit.pos.z
            break
        end
    end

    local z_lo = math.max(0, surface_z - 3)
    local z_hi = math.min(map.z_count - 1, surface_z + 5)
    local m    = 4  -- stay off the very map edge to avoid bound issues

    -- Four generators, one per embark edge (N/S/W/E).
    local edge_gens = {
        function() return math.random(m, map.x_count-1-m), math.random(m, 10)                   end,
        function() return math.random(m, map.x_count-1-m), math.random(map.y_count-11, map.y_count-1-m) end,
        function() return math.random(m, 10),               math.random(m, map.y_count-1-m)     end,
        function() return math.random(map.x_count-11, map.x_count-1-m), math.random(m, map.y_count-1-m) end,
    }

    for z = z_hi, z_lo, -1 do
        for _ = 1, 60 do
            local x, y = edge_gens[math.random(4)]()
            local block = dfhack.maps.getTileBlock(x, y, z)
            if block then
                local lx, ly = x % 16, y % 16
                local ok = false
                pcall(function()
                    local des   = block.designation[lx][ly]
                    local shape = df.tiletype.attrs[block.tiletype[lx][ly]].shape
                    ok = des.outside and des.flow_size == 0
                      and (shape == df.tiletype_shape.FLOOR
                        or shape == df.tiletype_shape.RAMP)
                end)
                if ok then return x, y, z end
            end
        end
    end
    return nil
end

-- ── Item handlers: traps ──────────────────────────────────────────────────────
-- Hostile-spawn traps create units directly through the dfhack.units API instead
-- of the modtools/create-unit script (which errors on this build:
-- "Cannot read field world.arena_spawn"). Each trap still falls back to a
-- reliable non-spawn effect if the spawn fails, so the trap always does *something*.

-- Create a unit via the dfhack.units API and drop it onto the map as a live actor.
--   race_token  : creature raw id, e.g. "GOBLIN", "CAVE_BEAR"
--   pos         : {x=,y=,z=} walkable tile to place it on
--   opts.civ_id : civilisation id (-1 = wild); goblins use the goblin civ
--   opts.invader: set invader/marauder flags so a civ unit actually attacks
-- Returns the created unit, or nil on failure.
-- Resolve a creature raw index from a token or list of candidate tokens. Returns
-- index, matched_token or nil. Lets callers pass fallbacks (e.g. several bear
-- species) so a token missing from this world's raws doesn't kill the spawn.
local function resolve_race(race_token)
    local tokens = (type(race_token) == "table") and race_token or { race_token }
    for _, tok in ipairs(tokens) do
        for i, cr in ipairs(df.global.world.raws.creatures.all) do
            if cr.creature_id == tok then return i, tok end
        end
    end
    return nil, tokens
end

local function create_unit(race_token, pos, opts)
    opts = opts or {}
    local result
    local ok, err = pcall(function()
        local race_idx, resolved = resolve_race(race_token)
        if not race_idx then
            error("no matching creature for " .. table.concat(resolved, "/"))
        end

        -- dfhack.units.create() builds the unit (body, soul, mind) and adds it to
        -- world.units.all, but NOT to world.units.active, and with no map position.
        local unit = dfhack.units.create(race_idx, 0)
        if not unit then error("dfhack.units.create returned nil") end

        -- Place on the map (teleport sets tile occupancy) and register as active.
        if not dfhack.units.teleport(unit, {x = pos.x, y = pos.y, z = pos.z}) then
            unit.pos.x, unit.pos.y, unit.pos.z = pos.x, pos.y, pos.z
        end
        df.global.world.units.active:insert('#', unit)

        unit.civ_id = opts.civ_id or -1

        -- A freshly created unit is neutral wildlife (it just stands around). To
        -- make a trap creature an actual threat we flag it as an active hostile:
        --   active_invader → the game treats it as a hostile that seeks targets
        --   marauder       → roams/attacks rather than fleeing
        -- For civ units (goblins) civ_id is also set so they invade as that race.
        if opts.hostile then
            unit.flags1.active_invader = true
            unit.flags1.marauder       = true
            pcall(function() unit.animal.population.region_x = -1 end)  -- detach from any wild pop
        end
        result = unit
    end)
    if not ok then
        local label = (type(race_token) == "table") and table.concat(race_token, "/") or tostring(race_token)
        log.error("create_unit(" .. label .. "): " .. tostring(err))
        return nil
    end
    return result
end

-- Add `amount` stress to up to `count` random living citizens (all if count nil).
-- Returns how many were affected.
local function stress_citizens(amount, count)
    local citizens = {}
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit)
                and unit.status.current_soul then
            table.insert(citizens, unit)
        end
    end
    for i = #citizens, 2, -1 do
        local j = math.random(i)
        citizens[i], citizens[j] = citizens[j], citizens[i]
    end
    local n = count and math.min(count, #citizens) or #citizens
    for i = 1, n do
        local soul = citizens[i].status.current_soul
        pcall(function()
            soul.personality.stress = (soul.personality.stress or 0) + amount
        end)
    end
    return n
end

-- Destroy up to `max_items` food/drink items (vermin eating stores). Collects
-- first, then removes, so we never mutate the list mid-iteration.
local FOOD_ITEM_TYPES = {
    FOOD = true, MEAT = true, FISH = true, CHEESE = true, EGG = true,
    PLANT = true, PLANT_GROWTH = true, DRINK = true, GLOB = true,
}
local function destroy_food(max_items)
    local targets = {}
    for _, item in ipairs(df.global.world.items.all) do
        if #targets >= max_items then break end
        local ok, tn = pcall(function() return df.item_type[item:getType()] end)
        if ok and FOOD_ITEM_TYPES[tn] then table.insert(targets, item) end
    end
    local removed = 0
    for _, item in ipairs(targets) do
        if pcall(function() dfhack.items.remove(item) end) then removed = removed + 1 end
    end
    return removed
end

local function recv_goblin_ambush()
    -- Spawn outside near the embark perimeter so goblins have to path in.
    local x, y, z = find_surface_spawn_pos()
    local civ_id  = find_goblin_civ_id()
    local spawned = 0
    if x then
        for _ = 1, 3 do
            if create_unit("GOBLIN", {x = x, y = y, z = z},
                           {civ_id = civ_id, hostile = true}) then
                spawned = spawned + 1
            end
        end
    end
    local spawn_pos = x and {x=x, y=y, z=z} or nil
    if spawned > 0 then
        announce("Trap: Goblin Ambush! Raiders approach from outside!",
            spawn_pos, df.announcement_type.AMBUSH_AMBUSHER)
    else
        local n = stress_citizens(60000)
        log.warn("goblin_ambush: unit spawn unavailable, applied raid-fear stress to " .. n .. " dwarves")
        announce("Trap: A goblin ambush descends - panic grips your dwarves!",
            spawn_pos, df.announcement_type.AMBUSH_AMBUSHER)
    end
end

local function recv_cave_bear()
    -- Spawn on the surface so the bear has to approach the fortress entrance.
    local x, y, z = find_surface_spawn_pos()
    local BEARS = { "BLIND_CAVE_BEAR", "CAVE_BEAR", "BEAR_GRIZZLY", "BEAR_BLACK", "BEAR_POLAR", "BEAR_SLOTH" }
    local spawn_pos = x and {x=x, y=y, z=z} or nil
    if x and create_unit(BEARS, {x = x, y = y, z = z}, {civ_id = -1, hostile = true}) then
        announce("Trap: A Cave Bear has been spotted outside!",
            spawn_pos, df.announcement_type.BEAST_AMBUSH)
    else
        local n = stress_citizens(120000, 3)
        log.warn("cave_bear: unit spawn unavailable, applied beast-scare stress to " .. n .. " dwarves")
        announce("Trap: Something large and angry circles your fortress...",
            spawn_pos, df.announcement_type.BEAST_AMBUSH)
    end
end

local function recv_catsplosion()
    local count = math.random(10, 20)
    local race_idx
    for i, cr in ipairs(df.global.world.raws.creatures.all) do
        if cr.creature_id == "CAT" then race_idx = i; break end
    end
    if not race_idx then
        announce("Trap: Catsplosion! (no cats in world raws - the cats escaped to another timeline)")
        return
    end
    local dx, dy, dz = find_trade_depot_center()
    if not dx then
        local sx, sy, sz = get_fort_spawn_pos()
        dx, dy, dz = tonumber(sx), tonumber(sy), tonumber(sz)
    end
    local cur_year = df.global.cur_year
    local spawned = 0
    for i = 1, count do
        local caste = (i <= 2) and (i - 1) or math.random(0, 1)
        local ok, err = pcall(function()
            local unit = dfhack.units.create(race_idx, caste)
            if not unit then error("create returned nil") end
            pcall(function() unit.birth_year = cur_year - math.random(1, 4) end)
            if not dfhack.units.teleport(unit, {x = dx, y = dy, z = dz}) then
                unit.pos.x, unit.pos.y, unit.pos.z = dx, dy, dz
            end
            df.global.world.units.active:insert('#', unit)
            pcall(function() unit.civ_id = df.global.plotinfo.civ_id end)
            pcall(function() unit.civ_id = df.global.ui.civ_id end)
            pcall(function() unit.flags1.tame = true end)
            pcall(function() unit.flags2.tame = true end)
            pcall(function() unit.flags3.tame = true end)
            pcall(function() unit.flags1.active_invader = false end)
            pcall(function() unit.flags1.marauder       = false end)
            pcall(function() unit.training_level = df.animal_training_level.Domesticated end)
            dfhack.units.makeown(unit)
            spawned = spawned + 1
        end)
        if not ok then log.error(("catsplosion: %s"):format(tostring(err))) end
    end
    local pos = dx and {x=dx, y=dy, z=dz} or nil
    if spawned > 0 then
        announce(("Trap: Catsplosion! %d cats have invaded the fortress!"):format(spawned), pos)
    else
        announce("Trap: Catsplosion! The cats are... somewhere. Good luck.")
    end
end

-- Return a random tile inside a stockpile. Prefers food stockpiles; falls back
-- to any stockpile; falls back to get_fort_spawn_pos if none exist.
local function find_stockpile_pos()
    local food_piles, any_piles = {}, {}
    for _, bld in ipairs(df.global.world.buildings.all) do
        if df.building_stockpilest:is_instance(bld) then
            local is_food = false
            pcall(function() is_food = bld.settings.flags.food end)
            table.insert(is_food and food_piles or any_piles, bld)
        end
    end
    local pool = #food_piles > 0 and food_piles or any_piles
    if #pool == 0 then return get_fort_spawn_pos() end
    local bld = pool[math.random(#pool)]
    local x = math.random(bld.x1, bld.x2)
    local y = math.random(bld.y1, bld.y2)
    return x, y, bld.z
end

local function recv_vermin_infestation()
    -- Spawn inside the fortress - rats materialise directly in your stockpiles.
    local x, y, z = find_stockpile_pos()
    local spawned = 0
    local RATS = { "GIANT_RAT", "RAT", "GIANT_MOUSE", "MOUSE", "GIANT_MOLE", "MOLE_DWARF" }
    for _, cr in ipairs(df.global.world.raws.creatures.all) do
        local id = cr.creature_id or ""
        if id:find("RAT") or id:find("MOUSE") or id:find("MOLE") or id:find("VERMIN") then
            table.insert(RATS, id)
        end
    end
    if x then
        for _ = 1, 10 do
            if create_unit(RATS, {x = x, y = y, z = z}, {civ_id = -1, hostile = false}) then
                spawned = spawned + 1
            end
        end
    end
    local spawn_pos = x and {x=x, y=y, z=z} or nil
    if spawned > 0 then
        announce("Trap: Vermin Infestation! Giant rats everywhere!",
            spawn_pos, df.announcement_type.VERMIN_CAGE_ESCAPE)
    else
        local eaten = destroy_food(20)
        log.warn("vermin_infestation: unit spawn unavailable, vermin ate " .. eaten .. " food/drink items")
        announce(("Trap: Vermin Infestation! They have devoured %d of your stores."):format(eaten),
            spawn_pos, df.announcement_type.VERMIN_CAGE_ESCAPE)
    end
end

local function recv_tantrum_trigger()
    -- Push the most-stressed living citizen past the tantrum threshold.
    -- The tantrum threshold in DF is ~200,000 stress; 500,000 is well past it.
    local target = nil
    local highest_stress = -math.huge
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit)
            and dfhack.units.isAlive(unit)
            and unit.status.current_soul
        then
            local stress = unit.status.current_soul.personality.stress
            if stress > highest_stress then
                highest_stress = stress
                target = unit
            end
        end
    end
    if target and target.status.current_soul then
        target.status.current_soul.personality.stress = 500000
        local name = unit_display_name(target)
        local tpos = {x=target.pos.x, y=target.pos.y, z=target.pos.z}
        announce("Trap: " .. (name ~= "" and name or "A dwarf") .. " has had enough!",
            tpos, df.announcement_type.CITIZEN_TANTRUM)
    else
        -- No eligible dwarf found (e.g. very early embark with no stress data).
        announce("Trap: Something sinister stirs in the fortress...")
        log.error("tantrum_trigger: no eligible citizen found")
    end
end

local function recv_lost_caravan()
    -- Flag that the next caravan should be skipped / arrive empty.
    dfhack.persistent.saveWorldDataString("dwarfipelago/trap/lost_caravan", "1")
    announce("Trap: A caravan has been lost on the road...")
end

-- ── Megabeast spawn helpers ───────────────────────────────────────────────────

-- Search for an open, non-surface floor tile well below ground.
-- Randomly samples positions across multiple z-levels so it handles any
-- embark layout without a full tile scan. Returns x, y, z or nil.
local function find_underground_spawn()
    if not dfhack.isMapLoaded() then return nil end
    local map = df.global.world.map

    -- Estimate surface z from a living citizen (fallback: upper 40% of map).
    local surface_z = math.floor(map.z_count * 0.6)
    for _, unit in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(unit) and dfhack.units.isAlive(unit) then
            surface_z = unit.pos.z
            break
        end
    end

    local z_high = math.max(2, surface_z - 10)
    local z_low  = math.max(2, surface_z - 40)

    for z = z_high, z_low, -1 do
        for _ = 1, 30 do
            local x = math.random(5, map.x_count - 6)
            local y = math.random(5, map.y_count - 6)
            local block = dfhack.maps.getTileBlock(x, y, z)
            if block then
                local lx, ly = x % 16, y % 16
                local shape  = df.tiletype.attrs[block.tiletype[lx][ly]].shape
                if shape == df.tiletype_shape.FLOOR
                        and not block.designation[lx][ly].outside then
                    return x, y, z
                end
            end
        end
    end
    return nil
end


-- Map a spawn tile position to a compass direction relative to the embark centre.
-- Returns one of 8 directional strings, or "depths" if very close to centre.
local function get_spawn_direction(sx, sy)
    local map = df.global.world.map
    local dx  = sx - (map.x_count / 2)
    local dy  = sy - (map.y_count / 2)  -- positive y = south in DF
    if math.abs(dx) < 4 and math.abs(dy) < 4 then return "depths" end
    -- math.atan2 was removed in Lua 5.3+ (DFHack's Lua); math.atan takes (y, x).
    local angle = (math.deg(math.atan(dy, dx)) + 360) % 360
    -- 0=E 45=SE 90=S 135=SW 180=W 225=NW 270=N 315=NE
    local dirs = { "eastern", "southeastern", "southern", "southwestern",
                   "western", "northwestern", "northern", "northeastern" }
    return dirs[math.floor((angle + 22.5) / 45) % 8 + 1]
end

-- Scan creature raws for a random megabeast type present in this world.
local function pick_megabeast_type()
    local candidates = {}
    for _, creature in ipairs(df.global.world.raws.creatures.all) do
        for _, caste in ipairs(creature.caste) do
            if caste.flags.MEGABEAST then
                table.insert(candidates, creature.creature_id)
                break
            end
        end
    end
    return #candidates > 0 and candidates[math.random(#candidates)] or "DRAGON"
end

-- Spawn a precursor threat (giant cave spider) underground as a Training 2 warm-up.
local function spawn_precursor_threat()
    local x, y, z = find_underground_spawn()
    if not x then
        local sx, sy, sz = get_fort_spawn_pos()
        x, y, z = tonumber(sx), tonumber(sy), tonumber(sz)
        dfhack.gui.showAnnouncement(
            "[AP] Warning: no underground tile found - precursor spawned at surface instead.",
            COLOR_YELLOW, true)
        log.warn("spawn_precursor_threat: underground search failed, falling back to surface")
    end
    if not create_unit({ "GIANT_CAVE_SPIDER", "CAVE_SPIDER_GIANT", "SPIDER_CAVE_GIANT" },
                       {x = x, y = y, z = z}, {civ_id = -1, hostile = true}) then
        dfhack.gui.showAnnouncement(
            "[AP] Error: precursor creature could not be spawned. Check the DFHack console.",
            COLOR_RED, true)
        log.error("precursor spawn failed")
    end
end

-- A readable name for the beast: its proper/historical name if it has one, else
-- the creature's singular raw name ("dragon"), else the raw token.
local function beast_label(unit, species)
    local label
    pcall(function() label = dfhack.units.getReadableName(unit) end)
    if label and label ~= "" then return label end
    pcall(function()
        for _, cr in ipairs(df.global.world.raws.creatures.all) do
            if cr.creature_id == species then label = cr.name[0]; break end
        end
    end)
    return (label and label ~= "") and label or species
end

-- ── Curated impact crater for the climax ──────────────────────────────────────
local CRATER_RIM_R = 6   -- radius at the surface rim
local CRATER_DEPTH = 5   -- z-levels carved (stepped bowl with ramped walls)

-- Walkable tile shapes - used to confirm carving produced ground to stand on.
local function tile_walkable(x, y, z)
    local blk = dfhack.maps.getTileBlock(x, y, z)
    if not blk then return false end
    local ok, walk = pcall(function()
        local shape = df.tiletype.attrs[blk.tiletype[x % 16][y % 16]].shape
        return shape == df.tiletype_shape.FLOOR or shape == df.tiletype_shape.RAMP
            or shape == df.tiletype_shape.STAIR_UP or shape == df.tiletype_shape.STAIR_UPDOWN
    end)
    return ok and walk == true
end

local function set_dig(x, y, z, kind)
    local blk = dfhack.maps.getTileBlock(x, y, z)
    if blk then pcall(function() blk.designation[x % 16][y % 16].dig = kind end) end
end

-- True if the crater footprint (a touch wider than the rim, through the whole
-- dig column) has no standing liquid - so it won't flood from a river/pond. We do
-- NOT reject aquifers here (they cover large parts of many maps); the carve
-- strips the aquifer instead.
local function footprint_is_dry(cx, cy, sz, rim, depth)
    local cr = rim + 2
    for z = sz, sz - depth, -1 do
        for dx = -cr, cr do
            for dy = -cr, cr do
                if dx * dx + dy * dy <= cr * cr then
                    local blk = dfhack.maps.getTileBlock(cx + dx, cy + dy, z)
                    if blk then
                        local wet = false
                        pcall(function()
                            if blk.designation[(cx + dx) % 16][(cy + dy) % 16].flow_size > 0 then wet = true end
                        end)
                        if wet then return false end
                    end
                end
            end
        end
    end
    return true
end

-- A surface impact site set back from every edge (so the full bowl fits), biased
-- toward an edge (away from a central fort), and DRY (no nearby water/aquifer, so
-- the crater won't flood). Returns x,y,z or nil. An outside floor tile.
local function find_crater_center(rim)
    if not dfhack.isMapLoaded() then return nil end
    local map = df.global.world.map
    local inset = rim + 3
    if map.x_count <= inset * 2 or map.y_count <= inset * 2 then return nil end

    local surface_z = math.floor(map.z_count * 0.7)
    for _, u in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then surface_z = u.pos.z; break end
    end

    for _ = 1, 150 do
        local x, y
        local edge = math.random(4)
        if edge == 1 then x = math.random(inset, map.x_count-1-inset); y = inset + math.random(0, 8)
        elseif edge == 2 then x = math.random(inset, map.x_count-1-inset); y = map.y_count-1-inset - math.random(0, 8)
        elseif edge == 3 then x = inset + math.random(0, 8); y = math.random(inset, map.y_count-1-inset)
        else x = map.x_count-1-inset - math.random(0, 8); y = math.random(inset, map.y_count-1-inset) end
        for z = math.min(map.z_count-1, surface_z+4), math.max(1, surface_z-4), -1 do
            local blk = dfhack.maps.getTileBlock(x, y, z)
            if blk then
                local lx, ly = x % 16, y % 16
                local ok = false
                pcall(function()
                    local des   = blk.designation[lx][ly]
                    local shape = df.tiletype.attrs[blk.tiletype[lx][ly]].shape
                    ok = des.outside and des.flow_size == 0 and shape == df.tiletype_shape.FLOOR
                end)
                if ok and footprint_is_dry(x, y, z, rim, CRATER_DEPTH) then return x, y, z end
            end
        end
    end
    return nil
end

-- Gouge a circular impact crater: channel a disc at each layer, narrowing with
-- depth, so dig-now builds a stepped bowl with ramped walls the beast climbs out
-- of. The very bottom is dug to a solid floor for footing. dig-now sets correct
-- tiletypes + ramps + reveals. Returns the crater-floor tile, or nil if carving
-- produced no walkable ground.
-- Keyed by shape NAME (not enum value) so a name absent from this build's
-- df.tiletype_shape doesn't create a nil table key. Matched via reverse lookup.
local CRATER_TREE_SHAPE_NAMES = {
    TREE = true, TRUNK_BRANCH = true, BRANCH = true,
    TWIG = true, SAPLING = true, SHRUB = true,
}
local function carve_crater(cx, cy, sz)
    -- dig-now skips trees, so first clear any tree/shrub tiles in the bowl
    -- footprint (canopy above down to just below the floor) to open space - the
    -- "impact" obliterates them. Then dig-now can carve the ground cleanly.
    for z = sz + 6, sz - CRATER_DEPTH - 1, -1 do
        for dx = -CRATER_RIM_R, CRATER_RIM_R do
            for dy = -CRATER_RIM_R, CRATER_RIM_R do
                if dx * dx + dy * dy <= CRATER_RIM_R * CRATER_RIM_R then
                    local x, y = cx + dx, cy + dy
                    local blk = dfhack.maps.getTileBlock(x, y, z)
                    if blk then
                        local lx, ly = x % 16, y % 16
                        pcall(function()
                            local shapename = df.tiletype_shape[df.tiletype.attrs[blk.tiletype[lx][ly]].shape]
                            local is_tree = (shapename and CRATER_TREE_SHAPE_NAMES[shapename])
                                or (dfhack.maps.getPlantAtTile(x, y, z) ~= nil)
                            if is_tree then
                                blk.tiletype[lx][ly] = df.tiletype.OpenSpace
                                blk.designation[lx][ly].hidden = false
                            end
                        end)
                    end
                end
            end
        end
    end

    for d = 0, CRATER_DEPTH - 1 do
        local z, r = sz - d, CRATER_RIM_R - d
        for dx = -r, r do
            for dy = -r, r do
                if dx * dx + dy * dy <= r * r then
                    set_dig(cx + dx, cy + dy, z, df.tile_dig_designation.Channel)
                end
            end
        end
    end
    local zbot = sz - CRATER_DEPTH
    for dx = -2, 2 do
        for dy = -2, 2 do
            if dx * dx + dy * dy <= 4 then
                set_dig(cx + dx, cy + dy, zbot, df.tile_dig_designation.Default)
            end
        end
    end
    pcall(function()
        dfhack.run_command("dig-now",
            ("%d,%d,%d"):format(cx - CRATER_RIM_R, cy - CRATER_RIM_R, zbot),
            ("%d,%d,%d"):format(cx + CRATER_RIM_R, cy + CRATER_RIM_R, sz), "--clean")
    end)
    -- Strip the aquifer over a margin wider than the bowl (so it can't seep in
    -- from the sides) and clear any standing water. This is what lets the crater
    -- form on the common aquifer maps without flooding.
    local arim = CRATER_RIM_R + 3
    for z = sz, zbot - 1, -1 do
        for dx = -arim, arim do
            for dy = -arim, arim do
                if dx * dx + dy * dy <= arim * arim then
                    local x, y = cx + dx, cy + dy
                    pcall(function() dfhack.maps.removeTileAquifer(x, y, z) end)
                    local blk = dfhack.maps.getTileBlock(x, y, z)
                    if blk then pcall(function() blk.designation[x % 16][y % 16].flow_size = 0 end) end
                end
            end
        end
    end
    for _, t in ipairs({ { cx, cy }, { cx+1, cy }, { cx-1, cy }, { cx, cy+1 }, { cx, cy-1 } }) do
        if tile_walkable(t[1], t[2], zbot) then return t[1], t[2], zbot end
    end
    return nil
end

-- A living citizen's position (target for the pathability guarantee).
local function any_citizen_pos()
    for _, u in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
            return { x = u.pos.x, y = u.pos.y, z = u.pos.z }
        end
    end
end

-- Does this creature token have fire immunity (so it can stand in its own flaming
-- impact)? Scans caste flags.
local function creature_fire_immune(token)
    for _, cr in ipairs(df.global.world.raws.creatures.all) do
        if cr.creature_id == token then
            for _, caste in ipairs(cr.caste) do
                local ok, v = pcall(function()
                    return caste.flags.FIREIMMUNE or caste.flags.FIREIMMUNE_SUPER
                end)
                if ok and v == true then return true end
            end
            return false
        end
    end
    return false
end

-- A random fire-immune megabeast present in this world (DRAGON / BRONZE COLOSSUS),
-- or nil if none - used for the flaming-impact landing.
local function pick_fire_immune_megabeast()
    local immune = {}
    for _, id in ipairs(bestiary.census().megabeast) do
        if creature_fire_immune(id) then immune[#immune + 1] = id end
    end
    if #immune > 0 then return immune[math.random(#immune)] end
end

-- Wreathe a tile in dragonfire (flow type 6) over a disc - a fiery impact.
local function spawn_fire_disc(x, y, z, r)
    for dx = -r, r do
        for dy = -r, r do
            if dx * dx + dy * dy <= r * r then
                pcall(function() dfhack.maps.spawnFlow({ x = x + dx, y = y + dy, z = z }, 6, 0, 0, 50000) end)
            end
        end
    end
end

-- The climax: the megabeast falls from the sky, gouging a crater near the map
-- edge, and rises to march on the fort. If a clean crater floor can't be made, it
-- lands in the open instead - and if a fire-immune beast is available, wreathed in
-- a flaming impact. The spawn tile is always verified walkable + reachable so the
-- goal can never soft-lock. Uses create_unit; the beast id is pinned so the goal
-- hook counts THIS kill. Fires once per world.
local function spawn_target_megabeast()
    if dfhack.persistent.getWorldDataString("dwarfipelago/megabeast/spawned") == "1" then
        return  -- already summoned this world (e.g. reloaded mid-session)
    end

    -- Impact site: a set-back surface tile, else a near-edge tile, else the fort.
    local cx, cy, sz = find_crater_center(CRATER_RIM_R)
    if not cx then cx, cy, sz = find_surface_spawn_pos() end
    if not cx then
        local fx, fy, fz = get_fort_spawn_pos()
        cx, cy, sz = tonumber(fx), tonumber(fy), tonumber(fz)
    end
    if not cx then
        dfhack.gui.showAnnouncement(
            "[AP] CRITICAL: no spawn tile for the megabeast - the goal cannot be completed.", COLOR_RED, true)
        log.error("spawn_target_megabeast: no spawn position")
        return
    end

    -- Gouge the crater (best-effort flavor). cbx/cby/cbz = its floor, or nil.
    local cbx, cby, cbz = carve_crater(cx, cy, sz)

    -- Choose a spawn tile that is GUARANTEED walkable AND able to path to the
    -- fort, so the beast can never get stuck (in a tree, root, wall, or the
    -- crater). Preference: the crater floor (if reachable) -> a reachable surface
    -- tile -> a citizen's own tile (trivially walkable + reachable) last.
    local citizen = any_citizen_pos()
    local function reachable(x, y, z)
        if not (x and tile_walkable(x, y, z)) then return false end
        if not citizen then return true end
        local ok, r = pcall(dfhack.maps.canWalkBetween, { x = x, y = y, z = z }, citizen)
        return ok and r == true
    end

    local bx, by, bz, in_crater
    if reachable(cbx, cby, cbz) then
        bx, by, bz, in_crater = cbx, cby, cbz, true
    else
        for _ = 1, 40 do
            local fx, fy, fz = find_surface_spawn_pos()
            if reachable(fx, fy, fz) then bx, by, bz = fx, fy, fz; break end
        end
    end
    if not bx and citizen then bx, by, bz = citizen.x, citizen.y, citizen.z end
    if not bx then
        dfhack.gui.showAnnouncement(
            "[AP] CRITICAL: no reachable spawn tile for the megabeast - the goal cannot be completed.", COLOR_RED, true)
        log.error("spawn_target_megabeast: no reachable spawn position")
        return
    end

    -- Species: in the open (no crater), prefer a fire-immune beast so we can wreathe
    -- the impact in flame; otherwise any world megabeast.
    local species = in_crater and (bestiary.random_megabeast() or pick_megabeast_type())
        or (pick_fire_immune_megabeast() or bestiary.random_megabeast() or pick_megabeast_type())
    local fiery = (not in_crater) and creature_fire_immune(species)

    local beast = create_unit(species, { x = bx, y = by, z = bz }, { civ_id = -1, hostile = true })
    if not beast then
        dfhack.gui.showAnnouncement(
            ("[AP] CRITICAL: could not spawn the megabeast (%s) - the goal cannot be completed."):format(tostring(species)),
            COLOR_RED, true)
        log.error("spawn_target_megabeast: create_unit failed for " .. tostring(species))
        return
    end
    dfhack.persistent.saveWorldDataString("dwarfipelago/megabeast/target_id", tostring(beast.id))
    dfhack.persistent.saveWorldDataString("dwarfipelago/megabeast/spawned", "1")

    -- Escort: wild brutes - but NOT in the fiery case (the fire would burn them).
    if not fiery then
        local escorts = bestiary.filter_present({ "TROLL", "OGRE" })
        if #escorts > 0 then
            for _ = 1, 2 do
                create_unit(escorts[math.random(#escorts)], { x = bx, y = by, z = bz }, { civ_id = -1, hostile = true })
            end
        end
    end

    -- Fiery impact: a fire-immune beast crashes down wreathed in dragonfire.
    if fiery then spawn_fire_disc(bx, by, bz, 3) end

    local dir = get_spawn_direction(bx, by)
    local where = (dir == "depths") and "the heart of your lands" or ("the " .. dir .. " reaches")
    local msg
    if in_crater then
        msg = "[AP] A STAR FALLS! %s crashes from the sky into %s, gouging a smoking crater, and rises to march on your fortress. Slay it for victory!"
    elseif fiery then
        msg = "[AP] A BURNING STAR FALLS! %s crashes to earth in %s, wreathed in flame, and strides from the inferno toward your fortress. Slay it for victory!"
    else
        msg = "[AP] %s descends upon your fortress from %s. Slay it for victory!"
    end
    dfhack.gui.showAnnouncement(msg:format(beast_label(beast, species), where), COLOR_RED, true)
    log.info(("Megabeast climax: %s (id %d) at (%d,%d,%d) in_crater=%s fiery=%s"):format(
        tostring(species), beast.id, bx, by, bz, tostring(in_crater), tostring(fiery)))
    print("[Dwarfipelago] Megabeast climax: " .. tostring(species))
end
M.spawn_target_megabeast = spawn_target_megabeast

-- ── Megabeast siege: roaming warbands ─────────────────────────────────────────
-- Time-paced enemy waves for the Slay Megabeast goal. Difficulty scales with the
-- player's War Readiness level (1-9); readiness 10 is the curated breach. Units
-- spawn at the embark perimeter and are armed via the verified createItem +
-- moveToInventory recipe (no_floor=false, explicit body part), so a naked goblin
-- becomes a real threat. Skill buff is best-effort (pcall-guarded). The wave
-- scheduler that calls spawn_warband lives in dwarfipelago.lua.

-- Subtype index for an itemdef id (e.g. "ITEM_WEAPON_SWORD_SHORT"), or nil.
local function itemdef_subtype(defs, id)
    for _, d in ipairs(defs) do
        if d.id == id then return d.subtype end
    end
end

-- First body part whose flags include flagname (UPPERBODY, HEAD, ...), or nil.
local function find_body_part(unit, flagname)
    local caste = df.global.world.raws.creatures.all[unit.race].caste[unit.caste]
    local parts = caste.body_info.body_parts
    for i = 0, #parts - 1 do
        local ok, v = pcall(function() return parts[i].flags[flagname] end)
        if ok and v == true then return i end
    end
end

-- All body part ids with flagname (e.g. both hands for GRASP -> weapon + shield).
local function find_body_parts(unit, flagname)
    local caste = df.global.world.raws.creatures.all[unit.race].caste[unit.caste]
    local parts = caste.body_info.body_parts
    local ids = {}
    for i = 0, #parts - 1 do
        local ok, v = pcall(function() return parts[i].flags[flagname] end)
        if ok and v == true then ids[#ids + 1] = i end
    end
    return ids
end

-- Create one item and force it into the unit's inventory on a specific body part.
-- The two non-obvious requirements (verified via the bestiary probe): no_floor
-- MUST be false (item needs a map position) and body_part MUST be explicit (-1
-- fails). Returns true on success.
local function equip_item(unit, item_type, subtype, mat, role, body_id)
    if not (subtype and body_id) then return false end
    local ok = pcall(function()
        local made = dfhack.items.createItem(unit, item_type, subtype, mat.type, mat.index, false)
        local item = made and made[1]
        if item then
            -- createItem flags new items forbidden; clear it so the loot the
            -- enemy drops on death is grabbable (a reward, not busywork).
            item.flags.forbid = false
            dfhack.items.moveToInventory(item, unit, role, body_id)
        end
    end)
    return ok
end

-- Raise a unit's trained level in a skill (adds the skill if absent). For making
-- spawned warriors veterans rather than green recruits.
local function set_skill(unit, skill_id, level)
    local soul = unit.status and unit.status.current_soul
    if not soul then return end
    for _, sk in ipairs(soul.skills) do
        if sk.id == skill_id then
            if sk.rating < level then sk.rating = level end
            return
        end
    end
    soul.skills:insert("#", { new = true, id = skill_id, rating = level })
end

-- Per-readiness wave config (tunable). Difficulty curve: 1-3 very easy, 4 easy-
-- to-medium, 5-6 medium, 7-9 hard. armor: none|shield|light(breast+helm)|full.
local WARBAND_TIERS = {
    [1] = { size = {2, 2},  mat = "COPPER", armor = "none",   skill = {0, 0}, pool = "easy", escort = 0 },
    [2] = { size = {2, 3},  mat = "COPPER", armor = "none",   skill = {0, 1}, pool = "easy", escort = 0 },
    [3] = { size = {3, 3},  mat = "COPPER", armor = "shield", skill = {0, 1}, pool = "easy", escort = 0 },
    [4] = { size = {3, 4},  mat = "IRON",   armor = "shield", skill = {2, 3}, pool = "mid",  escort = 0 },
    [5] = { size = {4, 5},  mat = "IRON",   armor = "light",  skill = {3, 4}, pool = "mid",  escort = 0 },
    [6] = { size = {5, 6},  mat = "IRON",   armor = "light",  skill = {4, 5}, pool = "mid",  escort = 0 },
    [7] = { size = {6, 7},  mat = "IRON",   armor = "full",   skill = {6, 7}, pool = "hard", escort = 25 },
    [8] = { size = {7, 8},  mat = "IRON",   armor = "full",   skill = {7, 8}, pool = "hard", escort = 50 },
    [9] = { size = {8, 10}, mat = "STEEL",  armor = "full",   skill = {8, 9}, pool = "hard", escort = 75 },
}

-- Race pools by tier keyword (filtered to what the world actually has at spawn).
local WARBAND_POOLS = {
    easy = { "KOBOLD", "GOBLIN" },
    mid  = { "GOBLIN", "ELF", "HUMAN", "REPTILE_MAN", "SERPENT_MAN", "BAT_MAN" },
    hard = { "GOBLIN", "HUMAN", "ANT_MAN", "REPTILE_MAN", "SERPENT_MAN" },
}
local WARBAND_ESCORTS = { "TROLL", "OGRE" }

-- Weapon options: {itemdef id, matching job_skill name}. Picked per unit.
local WARBAND_WEAPONS = {
    { "ITEM_WEAPON_SWORD_SHORT", "SWORD" },
    { "ITEM_WEAPON_AXE_BATTLE",  "AXE" },
    { "ITEM_WEAPON_SPEAR",       "SPEAR" },
    { "ITEM_WEAPON_MACE",        "MACE" },
}

-- Worn-armor pieces for a tier keyword: {item_type, itemdef vector, id, part flag}.
local function armor_pieces(kind)
    local W = df.global.world.raws.itemdefs
    local p = {}
    if kind == "light" or kind == "full" then
        p[#p + 1] = { df.item_type.ARMOR, W.armor, "ITEM_ARMOR_BREASTPLATE", "UPPERBODY" }
        p[#p + 1] = { df.item_type.HELM,  W.helms, "ITEM_HELM_HELM",         "HEAD" }
    end
    if kind == "full" then
        p[#p + 1] = { df.item_type.PANTS, W.pants, "ITEM_PANTS_GREAVES", "LOWERBODY" }
        p[#p + 1] = { df.item_type.SHOES, W.shoes, "ITEM_SHOES_BOOTS",   "STANCE" }
    end
    return p
end

-- Arm a humanoid: weapon (+off-hand shield) + armor set. Returns the weapon's
-- job_skill name so the caller can buff the matching skill.
local function equip_warrior(unit, mat, give_shield, armor_kind)
    local W = df.global.world.raws.itemdefs
    local grasps = find_body_parts(unit, "GRASP")

    local wpn = WARBAND_WEAPONS[math.random(#WARBAND_WEAPONS)]
    local wpn_sub = itemdef_subtype(W.weapons, wpn[1])
    if not wpn_sub then  -- fall back to the short sword if this world lacks it
        wpn = WARBAND_WEAPONS[1]; wpn_sub = itemdef_subtype(W.weapons, wpn[1])
    end
    equip_item(unit, df.item_type.WEAPON, wpn_sub, mat, df.inv_item_role_type.Weapon, grasps[1])

    if give_shield and grasps[2] then
        equip_item(unit, df.item_type.SHIELD, itemdef_subtype(W.shields, "ITEM_SHIELD_SHIELD"),
                   mat, df.inv_item_role_type.Weapon, grasps[2])
    end
    for _, pc in ipairs(armor_pieces(armor_kind)) do
        equip_item(unit, pc[1], itemdef_subtype(pc[2], pc[3]), mat,
                   df.inv_item_role_type.Worn, find_body_part(unit, pc[4]))
    end
    return wpn[2]
end

-- Buff combat skills (weapon + fighter/dodge, plus shield/armor when worn).
local function buff_warrior(unit, weapon_skill, level, has_shield, has_armor)
    if not level or level <= 0 then return end
    pcall(function()
        local js = df.job_skill
        local function s(name) local id = js[name]; if id then set_skill(unit, id, level) end end
        s(weapon_skill); s("MELEE_COMBAT"); s("DODGING")  -- MELEE_COMBAT = the "Fighter" skill
        if has_shield then s("SHIELD") end
        if has_armor  then s("ARMOR")  end
    end)
end

-- Spawn a roaming warband for the given readiness level (1-9). Returns the count
-- spawned. Picks a surface-edge tile so the enemies march in.
local function spawn_warband(readiness)
    local tier = WARBAND_TIERS[readiness]
    if not tier then log.warn("spawn_warband: no tier for readiness " .. tostring(readiness)); return 0 end

    local x, y, z = find_surface_spawn_pos()
    if not x then
        local sx, sy, sz = get_fort_spawn_pos()
        x, y, z = tonumber(sx), tonumber(sy), tonumber(sz)
    end
    if not x then log.error("spawn_warband: no spawn position found"); return 0 end

    -- Requested material with fallbacks (steel may be absent from a world).
    local mat = dfhack.matinfo.find("INORGANIC:" .. tier.mat)
        or dfhack.matinfo.find("INORGANIC:IRON")
        or dfhack.matinfo.find("INORGANIC:COPPER")

    local pool = bestiary.filter_present(WARBAND_POOLS[tier.pool] or {})
    if #pool == 0 then pool = bestiary.filter_present({ "GOBLIN" }) end
    if #pool == 0 then log.error("spawn_warband: no usable race present in world"); return 0 end

    local goblin_civ = find_goblin_civ_id()
    local give_shield = (tier.armor == "shield" or tier.armor == "full")
    local has_armor   = (tier.armor == "light" or tier.armor == "full")
    local n = math.random(tier.size[1], tier.size[2])

    local spawned = 0
    for _ = 1, n do
        local race = pool[math.random(#pool)]
        local civ  = (race == "GOBLIN") and goblin_civ or -1
        local unit = create_unit(race, { x = x, y = y, z = z }, { civ_id = civ, hostile = true })
        if unit then
            if mat then
                pcall(function()
                    local wskill = equip_warrior(unit, mat, give_shield, tier.armor)
                    buff_warrior(unit, wskill, math.random(tier.skill[1], tier.skill[2]), give_shield, has_armor)
                end)
            end
            spawned = spawned + 1
        end
    end

    -- Higher tiers: a chance of one armed beast brute (weapon only - armor fit on
    -- a troll/ogre-sized body is unreliable).
    if tier.escort and tier.escort > 0 and math.random(100) <= tier.escort then
        local beasts = bestiary.filter_present(WARBAND_ESCORTS)
        if #beasts > 0 then
            local brute = create_unit(beasts[math.random(#beasts)], { x = x, y = y, z = z },
                                      { civ_id = -1, hostile = true })
            if brute and mat then
                local grasps = find_body_parts(brute, "GRASP")
                equip_item(brute, df.item_type.WEAPON,
                           itemdef_subtype(df.global.world.raws.itemdefs.weapons, "ITEM_WEAPON_AXE_BATTLE"),
                           mat, df.inv_item_role_type.Weapon, grasps[1])
                buff_warrior(brute, "AXE", math.floor((tier.skill[1] + tier.skill[2]) / 2), false, false)
            end
            if brute then spawned = spawned + 1 end
        end
    end

    if spawned > 0 then
        dfhack.gui.showAnnouncement(
            ("[AP] A roaming warband attacks! %d enemies close on the fortress."):format(spawned),
            COLOR_RED, true)
        log.info(("Warband spawned: readiness %d, %d enemies at (%d,%d,%d)"):format(readiness, spawned, x, y, z))
    end
    return spawned
end
M.spawn_warband = spawn_warband

-- ── Item handlers: progression locks ─────────────────────────────────────────

local function recv_merchants_coffer()
    local key = "dwarfipelago/unlock/wealth_coffers"
    local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
    dfhack.persistent.saveWorldDataString(key, tostring(n))
    announce(("Merchant's Coffer received! Wealth tier %d/5 unlocked"):format(n))
end

-- Create `count` adult dwarves and enlist them as fortress citizens. Used for the
-- Immigration Wave: `force Migrants` only queues a wave the parent civ may have no
-- one to fill (it reports success but brings nobody), so we add citizens directly.
-- Returns how many were successfully made.
-- A lore-ish dwarf name: a random word from the dwarven language, else a curated
-- fallback. Set as a nickname so spawned migrants display a name, not "Peasant".
local DWARF_NAME_FALLBACK = {
    "Urist", "Solon", "Bomrek", "Zuglar", "Catten", "Lokum", "Kadol", "Reg",
    "Sibrek", "Tholtig", "Ducim", "Asmel", "Datan", "Erush", "Goden", "Kogan",
    "Litast", "Meng", "Nako", "Oddom", "Rith", "Sazir", "Tun", "Vabok", "Zaneg",
}
local function dwarf_name()
    local nm
    pcall(function()
        local lang = df.global.world.raws.language
        local idx
        for i, tr in ipairs(lang.translations) do
            if tr.name == "DWARF" then idx = i; break end
        end
        if idx then
            local words = lang.translations[idx].words
            local n = 0
            for _ in ipairs(words) do n = n + 1 end
            if n > 0 then
                local raw = words[math.random(0, n - 1)]
                local w = (type(raw) == "string") and raw or raw.value
                if w and #w > 0 then nm = w:sub(1, 1):upper() .. w:sub(2):lower() end
            end
        end
    end)
    if not nm or nm == "" then nm = DWARF_NAME_FALLBACK[math.random(#DWARF_NAME_FALLBACK)] end
    return nm
end

-- Pick a civilian-clothing subtype id (armorlevel 0) from an itemdef vector.
local function clothing_subtype(defs)
    local fallback
    for _, d in ipairs(defs) do
        fallback = fallback or d.id
        local lvl
        pcall(function() lvl = d.armorlevel end)
        if lvl == 0 then return d.id end
    end
    return fallback
end

-- Create a basic cloth outfit (body/legs/feet) at the depot so a new dwarf can
-- dress themselves. spawn_item already places items at the depot center.
local function make_outfit()
    local idefs = df.global.world.raws.itemdefs
    local cloth = "PLANT_MAT:GRASS_TAIL_PIG:THREAD"
    local body = clothing_subtype(idefs.armor)
    local legs = clothing_subtype(idefs.pants)
    local feet = clothing_subtype(idefs.shoes)
    if body then spawn_item("ARMOR:" .. body, cloth) end
    if legs then spawn_item("PANTS:" .. legs, cloth) end
    if feet then spawn_item("SHOES:" .. feet, cloth) end
end

local function spawn_citizen_dwarves(count)
    local race_idx
    for i, cr in ipairs(df.global.world.raws.creatures.all) do
        if cr.creature_id == "DWARF" then race_idx = i; break end
    end
    if not race_idx then return 0 end

    -- Count castes (MALE/FEMALE) so we can vary sex.
    local ncastes = 0
    pcall(function() for _ in ipairs(df.global.world.raws.creatures.all[race_idx].caste) do ncastes = ncastes + 1 end end)

    -- Drop them at the depot (or a citizen's tile).
    local dx, dy, dz = find_trade_depot_center()
    if not dx then
        local sx, sy, sz = get_fort_spawn_pos()
        dx, dy, dz = tonumber(sx), tonumber(sy), tonumber(sz)
    end

    local cur_year = df.global.cur_year
    local made = 0
    for _ = 1, count do
        pcall(function()
            local caste = (ncastes > 0) and math.random(0, ncastes - 1) or 0
            local unit = dfhack.units.create(race_idx, caste)
            if not unit then error("create returned nil") end
            -- Make them adults (~20-40 yrs) so they aren't spawned as babies.
            pcall(function() unit.birth_year = cur_year - math.random(20, 40) end)
            if dx then
                if not dfhack.units.teleport(unit, {x = dx, y = dy, z = dz}) then
                    unit.pos.x, unit.pos.y, unit.pos.z = dx, dy, dz
                end
            end
            df.global.world.units.active:insert('#', unit)
            dfhack.units.makeown(unit)   -- enlist as a fortress member
            pcall(function() dfhack.units.setNickname(unit, dwarf_name()) end)
            pcall(make_outfit)           -- cloth outfit at the depot to dress with
            made = made + 1
        end)
    end
    return made
end

local function recv_immigration_wave()
    local key = "dwarfipelago/unlock/immigration_waves"
    local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
    dfhack.persistent.saveWorldDataString(key, tostring(n))

    -- Directly add citizen dwarves (reliable). 'force Migrants' was unreliable -
    -- it reports success but often brings nobody when the parent civ has no
    -- migrants available.
    local wave = math.random(2, 5)
    local made = spawn_citizen_dwarves(wave)
    if made == 0 then
        -- Last resort: ask the game for a wave the normal way.
        pcall(function() dfhack.run_command("force", "Migrants") end)
        announce(("Immigration Wave received! A wave of migrants approaches. (tier %d/5)"):format(n))
    else
        announce(("Immigration Wave received! %d migrant(s) join the fortress. (tier %d/5)"):format(made, n))
    end
end

local function recv_barons_charter()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/baron_charter", "1")
    announce("Baron's Charter received! Baron appointment is now recognisable.")
end

local function recv_counts_charter()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/count_charter", "1")
    announce("Count's Charter received! Count appointment is now recognisable.")
end

local function recv_dukes_charter()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/duke_charter", "1")
    announce("Duke's Charter received! Duke appointment is now recognisable.")
end

local function recv_monarchs_invitation()
    dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/monarch_invitation", "1")
    announce("Monarch's Invitation received! The Monarch may now take residence.")
end

-- Escalating combat gear granted by Military Training tiers 1-10. Steel
-- throughout; later tiers grant fuller loadouts and bigger bar shipments so each
-- copy ramps up (arming a growing army for war). All spawns go through
-- spawn_item (pcall-guarded; logs failures), so a token absent from this DF
-- version is simply skipped rather than breaking the grant.
local STEEL = "INORGANIC:STEEL"
local WAR_GEAR_WEAPON = {
    AXE_BATTLE  = "WEAPON:ITEM_WEAPON_AXE_BATTLE",
    SWORD_SHORT = "WEAPON:ITEM_WEAPON_SWORD_SHORT",
    SPEAR       = "WEAPON:ITEM_WEAPON_SPEAR",
    MACE        = "WEAPON:ITEM_WEAPON_MACE",
    HAMMER_WAR  = "WEAPON:ITEM_WEAPON_HAMMER_WAR",
}
local WAR_GEAR_ARMOR = {
    breast    = "ARMOR:ITEM_ARMOR_BREASTPLATE",
    helm      = "HELM:ITEM_HELM_HELM",
    gauntlets = "GLOVES:ITEM_GLOVES_GAUNTLETS",
    greaves   = "PANTS:ITEM_PANTS_GREAVES",
    boots     = "SHOES:ITEM_SHOES_BOOTS",
    shield    = "SHIELD:ITEM_SHIELD_SHIELD",
}
-- Per-tier package: weapons, armor pieces, and steel bars. Escalates 1 -> 10.
local WAR_GEAR_TIERS = {
    [1]  = { weapons = { "AXE_BATTLE", "SWORD_SHORT" } },
    [2]  = { armor   = { "breast", "helm", "shield" } },
    [3]  = { armor   = { "gauntlets", "greaves", "boots" }, weapons = { "SPEAR", "HAMMER_WAR" } },
    [4]  = { weapons = { "SWORD_SHORT", "MACE" }, bars = 3 },
    [5]  = { armor   = { "breast", "helm", "greaves", "boots", "shield" } },
    [6]  = { weapons = { "AXE_BATTLE", "SPEAR", "MACE" }, bars = 4 },
    [7]  = { armor   = { "breast", "helm", "gauntlets", "greaves", "boots", "shield" } },
    [8]  = { weapons = { "SWORD_SHORT", "HAMMER_WAR", "AXE_BATTLE" }, bars = 6 },
    [9]  = { armor   = { "breast", "helm", "greaves", "boots", "shield" }, weapons = { "SPEAR", "MACE" } },
    [10] = { armor   = { "breast", "helm", "gauntlets", "greaves", "boots", "shield" },
             weapons = { "AXE_BATTLE", "SWORD_SHORT", "SPEAR" }, bars = 10 },
}
-- Blunt weapons can't be adamantine (too light) - keep them steel even at the
-- adamantine tiers so they still spawn.
local WAR_GEAR_BLUNT = { MACE = true, HAMMER_WAR = true }
local function grant_war_gear(tier)
    local pkg = WAR_GEAR_TIERS[math.min(tier, 10)] or {}
    -- Tiers 7+ upgrade to adamantine (a deliberate late-game power spike).
    local mat = (tier >= 7) and "INORGANIC:ADAMANTINE" or STEEL
    for _, w in ipairs(pkg.weapons or {}) do
        spawn_item(WAR_GEAR_WEAPON[w], WAR_GEAR_BLUNT[w] and STEEL or mat)
    end
    for _, a in ipairs(pkg.armor or {}) do spawn_item(WAR_GEAR_ARMOR[a], mat) end
    if pkg.bars then spawn_item("BAR", mat, pkg.bars) end
end

-- The champion: a veteran dwarf war-leader who joins the fortress as a citizen.
-- Not fully geared (he uses fortress equipment) but legendary-ish in several
-- combat skills, ideal as a squad commander. Spawns once per world.
local function spawn_super_dwarf()
    if dfhack.persistent.getWorldDataString("dwarfipelago/megabeast/champion") == "1" then return false end
    local race_idx
    for i, cr in ipairs(df.global.world.raws.creatures.all) do
        if cr.creature_id == "DWARF" then race_idx = i; break end
    end
    if not race_idx then return false end
    local dx, dy, dz = find_trade_depot_center()
    if not dx then
        local sx, sy, sz = get_fort_spawn_pos()
        dx, dy, dz = tonumber(sx), tonumber(sy), tonumber(sz)
    end
    if not dx then return false end

    local unit
    local ok = pcall(function()
        unit = dfhack.units.create(race_idx, math.random(0, 1))
        if not unit then error("create returned nil") end
        unit.birth_year = df.global.cur_year - math.random(30, 60)
        if not dfhack.units.teleport(unit, { x = dx, y = dy, z = dz }) then
            unit.pos.x, unit.pos.y, unit.pos.z = dx, dy, dz
        end
        df.global.world.units.active:insert('#', unit)
        dfhack.units.makeown(unit)
        pcall(function() dfhack.units.setNickname(unit, dwarf_name()) end)
        pcall(make_outfit)
        local lvl = math.random(11, 13)
        for _, sname in ipairs({ "AXE", "SWORD", "MELEE_COMBAT", "DODGING", "SHIELD", "ARMOR" }) do
            local id = df.job_skill[sname]
            if id then set_skill(unit, id, lvl) end
        end
    end)
    if not ok or not unit then log.error("spawn_super_dwarf failed"); return false end

    dfhack.persistent.saveWorldDataString("dwarfipelago/megabeast/champion", "1")
    announce_at_depot("A grizzled war-veteran has joined your fortress - skilled with several weapons and born to lead. Make them your military commander!")
    return true
end

-- A pool of bonus WAR materiel. Each Military Training receipt has a flat chance
-- (EXTRA_CHANCE) to also drop ONE random pick from here, on top of the tier's
-- normal gear. Combat-adjacent: weapons, ammo, traps, defense, war beasts, forge
-- supplies, field medicine. All go through spawn_item/spawn_livestock (guarded).
local EXTRA_POOL = {
    -- Weapons & ammunition
    function()  -- a random steel weapon
        local w = ({ "AXE_BATTLE", "SWORD_SHORT", "SPEAR", "MACE", "HAMMER_WAR" })[math.random(5)]
        spawn_item("WEAPON:ITEM_WEAPON_" .. w, STEEL)
    end,
    function() spawn_item("WEAPON:ITEM_WEAPON_CROSSBOW", STEEL); spawn_item("AMMO:ITEM_AMMO_BOLTS", STEEL, 10) end,
    function() spawn_item("AMMO:ITEM_AMMO_BOLTS", STEEL, 25) end,                   -- a quiver's worth
    function() spawn_item("WEAPON:ITEM_WEAPON_PIKE", STEEL) end,                    -- reach weapon
    function() spawn_item("WEAPON:ITEM_WEAPON_AXE_GREAT", "INORGANIC:ADAMANTINE") end, -- rare adamantine
    -- Armor & shields
    function() spawn_item("SHIELD:ITEM_SHIELD_SHIELD", STEEL); spawn_item("HELM:ITEM_HELM_HELM", STEEL) end,
    function() spawn_item("ARMOR:ITEM_ARMOR_BREASTPLATE", STEEL); spawn_item("PANTS:ITEM_PANTS_GREAVES", STEEL) end,
    function() spawn_item("ARMOR:ITEM_ARMOR_MAIL_SHIRT", STEEL) end,
    -- Traps & fortification
    function() spawn_item("TRAPPARTS", "INORGANIC:STEEL", 4) end,                   -- mechanisms
    function() spawn_item("TRAPCOMP:ITEM_TRAPCOMP_LARGESERRATEDDISC", STEEL) end,   -- trap weapon
    function() spawn_item("TRAPCOMP:ITEM_TRAPCOMP_MENACINGSPIKE", STEEL, 3) end,    -- trap weapons
    function() spawn_item("CAGE", "INORGANIC:STEEL") end,                           -- capture invaders
    -- War beasts
    function() spawn_livestock("DOG", "a pack of war dogs") end,
    -- Forge supplies (turn into more gear)
    function() spawn_item("BAR", STEEL, 6) end,                                     -- steel bars
    function() spawn_item("BAR", "COAL:COKE", 6) end,                               -- fuel
    function() spawn_item("BOULDER", "INORGANIC:MAGNETITE", 4) end,                 -- iron ore
    function() spawn_item("BAR", "INORGANIC:ADAMANTINE", 2) end,                    -- rare: 2 wafers
    function() spawn_item("ANVIL", "INORGANIC:IRON") end,                           -- an anvil
    -- Field medicine & rations (keep soldiers fighting)
    function() spawn_item("CLOTH", "PLANT_MAT:GRASS_TAIL_PIG:THREAD", 5) end,       -- bandages
    function() spawn_item("DRINK", "PLANT_MAT:MUSHROOM_HELMET_PLUMP:DRINK", 5) end, -- rations
}

local SUPER_DWARF_CHANCE = 10   -- percent chance per receipt before the tier-8 guarantee
local EXTRA_CHANCE       = 25   -- percent chance of a bonus extra-pool gift

local function recv_military_training()
    local key = "dwarfipelago/unlock/military_training"
    local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
    dfhack.persistent.saveWorldDataString(key, tostring(n))

    -- Escalating war shipment (adamantine from tier 7). The beast is NOT summoned
    -- here - the breach fires from the poll on the full war effort.
    grant_war_gear(n)

    -- The champion: a rare chance at any tier, GUARANTEED by tier 8 if not yet here.
    if dfhack.persistent.getWorldDataString("dwarfipelago/megabeast/champion") ~= "1"
            and (n >= 8 or math.random(100) <= SUPER_DWARF_CHANCE) then
        spawn_super_dwarf()
    end

    -- Sometimes a bonus gift from the extra pool (flat chance, no tier ramp).
    if math.random(100) <= EXTRA_CHANCE then
        EXTRA_POOL[math.random(#EXTRA_POOL)]()
    end

    announce(("Military Training received! War Readiness rises. (%d/10)"):format(math.min(n, 10)))
end

-- Progressive Mining Depth: each copy lowers the dig floor one cavern tier.
-- dwarfipelago.lua reads unlock/mining_depth to set the floor.
local function recv_progressive_mining_depth()
    local key = "dwarfipelago/unlock/mining_depth"
    local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
    dfhack.persistent.saveWorldDataString(key, tostring(n))

    local where = ({
        [1] = "the first cavern",
        [2] = "the second cavern",
        [3] = "the third cavern",
        [4] = "the magma sea and the depths below",
    })[n] or "deeper still"
    announce(("Progressive Mining Depth received! You may now dig to %s. (%d/4)")
        :format(where, math.min(n, 4)))
end

-- ── Progression unlock definitions ───────────────────────────────────────────
-- Single source of truth for all progression unlocks.
-- The panel reads this to build its Unlocks tab automatically.
-- Add new entries here when adding a new progression item handler.
--   key  → suffix after "dwarfipelago/unlock/" in persistent storage
--   label → display name shown in the panel
--   max  → if set, treated as a counter (shows "n/max"); otherwise a boolean

M.UNLOCK_DEFS = {
    { key = "wealth_coffers",        label = "Merchant's Coffers",     max = 5 },
    { key = "immigration_waves",     label = "Immigration Waves",      max = 5 },
    { key = "military_training",     label = "Military Training",      max = 4 },
    { key = "RotGK",                 label = "Remains of the Great King"},
    { key = "baron_charter",         label = "Baron's Charter" },
    { key = "count_charter",         label = "Count's Charter" },
    { key = "duke_charter",          label = "Duke's Charter" },
    { key = "monarch_invitation",    label = "Monarch's Invitation" },
    { key = "master_builders_codex", label = "Master Builder's Codex" },
    { key = "artifact_weapon",       label = "Artifact Weapon" },
    { key = "artifact_armor",        label = "Artifact Armor" },
    { key = "sunlight_tonic",        label = "Sunlight Tonic" },
    { key = "mining_depth",          label = "Progressive Mining Depth", max = 4 },
}

-- ── Dispatch table ────────────────────────────────────────────────────────────
-- Maps AP item name → handler function.
-- Names must match items.py exactly.

M.handlers = {
    -- Filler items
    ["Dwarven Ale"]          = recv_dwarven_ale,
    ["Stone Trinket"]        = recv_stone_trinket,
    ["Bone Crafts"]          = recv_bone_crafts,
    ["Raw Ore"]              = recv_raw_ore,
    ["Wooden Cup"]           = recv_wooden_cup,
    ["Flux Stone"]           = recv_flux_stone,
    ["Pig Iron Bar"]         = recv_pig_iron_bar,
    ["Charcoal"]             = recv_charcoal,
    ["Cloth Bolt"]           = recv_cloth_bolt,
    ["Tanned Leather"]       = recv_tanned_leather,
    ["Bag of Sand"]          = recv_bag_of_sand,
    ["Raw Clay"]             = recv_raw_clay,
    ["Copper Pick"]          = recv_copper_pick,
    ["Copper Axe"]           = recv_copper_axe,
    ["Copper Short Sword"]   = recv_copper_short_sword,

    -- Useful items
    ["Masterwork Crafts"]    = recv_masterwork_crafts,
    ["Dwarven Steel Sword"]  = recv_dwarven_steel_sword,
    ["Fine Cloth"]           = recv_fine_cloth,
    ["Adamantine Fiber"]     = recv_adamantine_fiber,
    ["Sunlight Tonic"]       = recv_sunlight_tonic,

    -- Livestock
    ["Breeding Pigs"]        = recv_breeding_pigs,
    ["Breeding Chickens"]    = recv_breeding_chickens,
    ["Breeding Alpacas"]     = recv_breeding_alpacas,
    ["Breeding Cows"]        = recv_breeding_cows,
    ["Breeding Sheep"]       = recv_breeding_sheep,
    ["Breeding Yaks"]        = recv_breeding_yaks,

    -- Progression items
    ["Artifact Weapon"]        = recv_artifact_weapon,
    ["Artifact Armor"]         = recv_artifact_armor,
    ["Master Builder's Codex"] = recv_master_builders_codex,
    ["Remains of the Great King"] = recv_king_remains,

    -- Junk trap items (filler traps sent back to DF)
    ["Cave Fisher Silk"]       = recv_cave_fisher_silk, --currently disabled in Client
    ["Dwarf Bones"]            = recv_dwarf_bones,
    ["Goblin Trophy"]          = recv_goblin_trophy,

    ["Cut Sapphire"]         = recv_cut_sapphire,
    ["Cut Ruby"]             = recv_cut_ruby,
    ["Cut Diamond"]          = recv_cut_diamond,
    ["Gold Bar"]             = recv_gold_bar,
    ["Silver Bar"]           = recv_silver_bar,
    ["Steel Bar"]            = recv_steel_bar,
    ["Masterwork Craft"]     = recv_masterwork_craft,

    ["Food Bundle"]          = recv_food_bundle,
    ["Wood Bundle"]          = recv_wood_bundle,
    ["Iron Ore Bundle"]      = recv_iron_ore_bundle,
    ["Coal Bundle"]          = recv_coal_bundle,

    ["Goblin Ambush"]        = recv_goblin_ambush,
    ["Cave Bear Incursion"]  = recv_cave_bear,
    ["Vermin Infestation"]   = recv_vermin_infestation,
    ["Tantrum Trigger"]      = recv_tantrum_trigger,
    ["Lost Caravan"]         = recv_lost_caravan,
    ["Catsplosion"]          = recv_catsplosion,

    ["Merchant's Coffer"]    = recv_merchants_coffer,
    ["Immigration Wave"]     = recv_immigration_wave,
    ["Baron's Charter"]      = recv_barons_charter,
    ["Count's Charter"]      = recv_counts_charter,
    ["Duke's Charter"]       = recv_dukes_charter,
    ["Monarch's Invitation"] = recv_monarchs_invitation,
    ["Military Training"]    = recv_military_training,
    ["Progressive Mining Depth"] = recv_progressive_mining_depth,
}

-- ── Blueprint items ───────────────────────────────────────────────────────────
-- Workshop blueprints unlock the ability to build specific workshops.
-- The unlock_blueprint function is defined in main.lua and writes to
-- persistent storage so the onJobInitiated hook can check it.

local BLUEPRINT_NAMES = {
    -- Workshops
    "Craftsdwarf's Workshop Blueprint",
    "Forge Blueprint",
    "Kitchen Blueprint",
    "Jeweler's Workshop Blueprint",
    "Clothier's Shop Blueprint",
    "Tanner's Blueprint",
    "Mechanic's Workshop Blueprint",
    "Magma Forge Blueprint",
    "Siege Workshop Blueprint",
    "Soap Maker's Workshop Blueprint",
    "Ashery Blueprint",
    "Bowyer's Workshop Blueprint",
    "Screw Press Blueprint",
    "Fishery Blueprint",
    "Loom Blueprint",
    "Dyer's Workshop Blueprint",
    "Butcher's Shop Blueprint",
    "Farmer's Workshop Blueprint",
    "Carpenter's Workshop Blueprint",
    "Stoneworker's Workshop Blueprint",
    "Still Blueprint",
    "Leather Works Blueprint",
    -- Furnaces
    "Smelter Blueprint",
    "Magma Smelter Blueprint",
    "Wood Furnace Blueprint",
    "Glass Furnace Blueprint",
    "Kiln Blueprint",
    "Magma Kiln Blueprint",
    "Magma Glass Furnace Blueprint",
    -- Buildings
    "Farm Plot Blueprint",
}

-- Exposed so the status command / panel can list blueprints and received state.
M.BLUEPRINT_NAMES = BLUEPRINT_NAMES

-- Register blueprint handlers dynamically.
-- Write directly to persistent storage rather than calling unlock_blueprint()
-- from dwarfipelago.lua, because each script has its own _ENV and cross-script
-- global calls resolve to nil.
for _, bp_name in ipairs(BLUEPRINT_NAMES) do
    M.handlers[bp_name] = function()
        dfhack.persistent.saveWorldDataString("dwarfipelago/blueprint/" .. bp_name, "1")
        dfhack.gui.showAnnouncement(
            ("[AP] Blueprint received: %s"):format(bp_name),
            COLOR_GREEN, true)
        print(("[Dwarfipelago] Blueprint unlocked: %s"):format(bp_name))
    end
end

-- ── Crafting lock items ───────────────────────────────────────────────────────
-- Receiving "Crafting X" from the AP multiworld writes a craftlock flag that
-- dwarfipelago.lua's on_job_initiated hook reads to decide whether to allow the
-- job. Names must match CRAFT_ITEMS in items.py exactly (minus the "Crafting " prefix).

local CRAFTING_LOCK_ITEMS = {
    "Beds", "Corkscrew", "Blocks", "Spike", "Ball", "Altar", "Animal Trap",
    "Armor Stand", "Barrel", "Bin", "Bookcase", "Bucket", "Buckler", "Cabinet",
    "Cage", "Burial Container", "Chair", "Container", "Crutch", "Door",
    "Floodgate", "Grate", "Hatch Cover", "Minecart", "Pedestal", "Pipe Section",
    "Shield", "Splint", "Stepladder", "Table", "Training Axe", "Training Spear",
    "Training Sword", "Weapon Rack", "Wheelbarrow", "Crossbow", "Bolt",
    "Millstone", "Quern", "Slab", "Statue", "Mechanism", "Traction Bench",
    "Crafts", "Liquid Container", "Cup", "Toy", "Totem", "Helm",
    "Ballista Parts", "Catapult Parts", "Ballista Arrows", "Ash", "Charcoal",
    "Metal Bars", "Coke Bars", "Pearlash", "Gypsum Plaster", "Jug", "Large Pot",
    "Hive", "Quicklime", "Glass", "Window", "Book Binding", "Scroll Roller",
    "Leather", "Sheet", "Cloth", "Alcohol", "Lye", "Potash", "Milk of Lime",
    "Prepared Meal", "Tallow", "Oil", "Honey", "Headgear Clothing",
    "Upper Body Clothing", "Upper Body Armor", "Hand Clothing", "Gauntlets",
    "Lower Body Clothing", "Lower Body Armor", "Footwear", "Dye", "Bag",
    "Rope/Chain", "Battle Axe", "Mace", "Pick", "Short Sword", "Spear",
    "War Hammer", "Anvil", "Coins", "Soap",
}

M.CRAFTING_LOCK_ITEMS = CRAFTING_LOCK_ITEMS

for _, item_name in ipairs(CRAFTING_LOCK_ITEMS) do
    local flag = item_name:lower():gsub(" ", "_")
    M.handlers[item_name .. " Permit"] = function()
        dfhack.persistent.saveWorldDataString("dwarfipelago/craftlock/" .. flag, "1")
        dfhack.gui.showAnnouncement(
            ("[AP] Crafting permit received: %s"):format(item_name),
            COLOR_GREEN, true)
        print(("[Dwarfipelago] Craft unlocked: %s"):format(item_name))
    end
end

-- ── Test harness (dwarfipelago test <name>) ──────────────────────────────────
-- Manual in-game verification of the spawn / effect mechanics. Each test prints
-- what happened so a failure is obvious in the console.

local function _unit_in_active(unit)
    for _, u in ipairs(df.global.world.units.active) do
        if u.id == unit.id then return true end
    end
    return false
end

-- Low-level spawn check: create one unit via the dfhack.units API and report the
-- result. Isolates the API mechanic from the trap wrappers/fallbacks.
local function test_spawn(race)
    race = (race and race ~= "") and race:upper() or "DWARF"  -- DWARF always exists
    if not dfhack.isMapLoaded() then
        print("[test] No fortress loaded.")
        return
    end
    local x, y, z = get_fort_spawn_pos()
    if not x then
        print("[test] No spawn anchor (need a living citizen or a trade depot).")
        return
    end
    print(("[test] dfhack.units.create %s at (%d,%d,%d)..."):format(race, x, y, z))
    local unit = create_unit(race, {x = x, y = y, z = z}, {civ_id = -1, hostile = true})
    if not unit then
        print("[test] FAIL: create_unit returned nil (check error above; unknown race token?).")
        return
    end
    print(("[test] PASS: id=%d in_active=%s pos=(%d,%d,%d) civ=%d race=%d"):format(
        unit.id, tostring(_unit_in_active(unit)),
        unit.pos.x, unit.pos.y, unit.pos.z, unit.civ_id, unit.race))
    print("[test] Watch it in-game (does it move/act?), then save+reload to confirm no crash.")
end

-- List creature tokens in this world's raws matching a substring, so valid race
-- tokens can be discovered (e.g. "find BEAR" before using one in a spawn).
local function test_find(substr)
    if not substr or substr == "" then
        print("[test] Usage: dwarfipelago test find <substring>   e.g. test find BEAR")
        return
    end
    local needle = substr:upper()
    local matches = {}
    for _, cr in ipairs(df.global.world.raws.creatures.all) do
        local id = cr.creature_id or ""
        if id:upper():find(needle, 1, true) then
            table.insert(matches, id)
        end
    end
    if #matches == 0 then
        print("[test] No creature tokens contain '" .. needle .. "'.")
        return
    end
    print(("[test] %d creature token(s) matching '%s':"):format(#matches, needle))
    for _, id in ipairs(matches) do print("    " .. id) end
end

-- Ordered so 'dwarfipelago test' lists them predictably.
local TEST_LIST = {
    { "spawn",     "Spawn 1 unit via dfhack.units API + report status (arg: RACE, default DWARF)",
                   function(rest) test_spawn(rest[1]) end },
    { "find",      "List creature tokens matching a substring (arg: SUBSTR, e.g. BEAR)",
                   function(rest) test_find(rest[1]) end },
    { "goblin",    "Goblin Ambush trap (3 hostile goblins)",          function() recv_goblin_ambush() end },
    { "cavebear",  "Cave Bear Incursion trap",                        function() recv_cave_bear() end },
    { "catsplosion", "Catsplosion trap (10-20 fortress cats)",        function() recv_catsplosion() end },
    { "vermin",    "Vermin Infestation trap (rodents)",               function() recv_vermin_infestation() end },
    { "spider",    "Precursor threat (giant cave spider, underground)", function() spawn_precursor_threat() end },
    { "megabeast", "Force the goal megabeast (once per world)",        function() spawn_target_megabeast() end },
    { "wave",      "Spawn a roaming warband for a readiness level (arg: 1-9, default 1)",
                   function(rest) spawn_warband(tonumber(rest[1]) or 1) end },
    { "wave-now",  "Force the scheduled wave due now (tests the auto-scheduler; needs readiness>=1, slay_megabeast)",
                   function()
                       dfhack.persistent.saveWorldDataString("dwarfipelago/megabeast/next_wave_tick", "0")
                       dfhack.persistent.saveWorldDataString("dwarfipelago/megabeast/wave_warned", "1")
                       print("[test] Next wave forced due; it spawns on the next poll if readiness>=1 and goal is Slay Megabeast.")
                   end },
    { "migrants",  "Add a wave of citizen dwarves",                    function() recv_immigration_wave() end },
    { "spawn-livestock", "Spawn a breeding group of livestock (arg: pigs|chickens|alpacas|cows|sheep|yaks)",
                   function(rest)
                       local LIVESTOCK = {
                           pigs     = recv_breeding_pigs,
                           chickens = recv_breeding_chickens,
                           alpacas  = recv_breeding_alpacas,
                           cows     = recv_breeding_cows,
                           sheep    = recv_breeding_sheep,
                           yaks     = recv_breeding_yaks,
                       }
                       local animal = (rest[1] or ""):lower()
                       local fn = LIVESTOCK[animal]
                       if fn then
                           fn()
                       else
                           print("[test] Usage: dwarfipelago test spawn-livestock <animal>")
                           print("[test] Valid animals: " .. table.concat({"pigs","chickens","alpacas","cows","sheep","yaks"}, ", "))
                       end
                   end },
    { "worldcheck", "Verify this world meets Dwarfipelago requirements (run after world gen, before embark)",
                   function()
                       local issues = 0
                       local function pass(msg) print("[worldcheck] PASS  " .. msg) end
                       local function warn(msg) print("[worldcheck] WARN  " .. msg); issues = issues + 1 end
                       local function fail(msg) dfhack.printerr("[worldcheck] FAIL  " .. msg); issues = issues + 1 end

                       -- 1. World dimensions
                       local w, h
                       pcall(function()
                           w = df.global.world.world_data.world_width
                           h = df.global.world.world_data.world_height
                       end)
                       if not w then
                           fail("Could not read world dimensions - is a world loaded?")
                           return
                       end
                       local SIZE_NAMES = {[17]="Pocket",[33]="Smaller",[65]="Small",[129]="Medium",[257]="Large"}
                       local size_name = SIZE_NAMES[w] or "Unknown"
                       if w == 65 and h == 65 then
                           pass(("Size: %dx%d (Small)"):format(w, h))
                       else
                           warn(("Size: %dx%d (%s) - DwarfipelagoWorld preset uses Small (65x65)"):format(w, h, size_name))
                       end

                       -- 2. History length
                       local year
                       pcall(function() year = df.global.cur_year end)
                       if year then
                           if year >= 80 then
                               pass(("History: %d years"):format(year))
                           elseif year >= 40 then
                               warn(("History: %d years - shorter history may produce fewer sites and civs"):format(year))
                           else
                               fail(("History: %d years - very short, world likely lacks sites and civs needed for AP"):format(year))
                           end
                       end

                       -- 3. Civilization presence
                       local civs = { DWARF=false, HUMAN=false, ELF=false, GOBLIN=false }
                       local total_ents = 0
                       pcall(function()
                           local creatures = df.global.world.raws.creatures.all
                           for _, ent in ipairs(df.global.world.entities.all) do
                               total_ents = total_ents + 1
                               if ent.race >= 0 and ent.race < #creatures then
                                   local rid = creatures[ent.race].creature_id
                                   if civs[rid] ~= nil then civs[rid] = true end
                               end
                           end
                       end)
                       for _, race in ipairs({"DWARF","HUMAN","ELF","GOBLIN"}) do
                           if civs[race] then
                               pass("Civ: " .. race)
                           else
                               fail("Civ: " .. race .. " not found - related AP goals may be impossible")
                           end
                       end
                       print(("[worldcheck]       (%d total entities in world)"):format(total_ents))

                       -- 4. Active volcanoes (proxy for magma access)
                       local n_volc = 0
                       pcall(function()
                           local vs = df.global.world.world_data.active_volcanoes
                           if vs then n_volc = #vs end
                       end)
                       if n_volc >= 5 then
                           pass(("Volcanoes: %d active"):format(n_volc))
                       elseif n_volc >= 1 then
                           warn(("Volcanoes: %d active - magma access possible but limited; consider rerolling if smelting goals are required"):format(n_volc))
                       else
                           warn("Volcanoes: none detected - magma smelting goals may require a different embark site")
                       end

                       -- Summary
                       print("")
                       if issues == 0 then
                           print("[worldcheck] All checks passed - world is suitable for Dwarfipelago.")
                       else
                           print(("[worldcheck] %d issue(s) found - see above. Consider rerolling if critical."):format(issues))
                       end
                   end },
    { "caravan",   "Force a caravan (arg: dwarf|elf|human|goblin; default = parent civ)",
                   function(rest)
                       local token = ({ dwarf = "DWARF", elf = "ELF",
                                        human = "HUMAN", goblin = "GOBLIN" })[(rest[1] or ""):lower()]
                       local ok
                       if token then
                           local id = find_civ_id(token)
                           if not id then
                               print("[test] No " .. token .. " civilization exists in this world.")
                               return
                           end
                           ok = pcall(function() dfhack.run_command("force", "Caravan", tostring(id)) end)
                           print(ok and ("[test] Forced a " .. token .. " caravan (civ id " .. id .. ").")
                                     or  "[test] force Caravan failed.")
                       else
                           ok = pcall(function() dfhack.run_command("force", "Caravan") end)
                           print(ok and "[test] Forced the parent-civ (dwarven) caravan."
                                     or  "[test] force Caravan failed.")
                       end
                       print("[test] It enters at a map edge and walks to your depot; give it time. "
                             .. "A race not neighboring your embark may not actually arrive.")
                   end },
}

-- Dispatch a named test. `rest` is an array of any extra args after the name.
function M.run_test(name, rest)
    rest = rest or {}
    if not name or name == "" or name == "list" then
        print("[Dwarfipelago] Tests - run as: dwarfipelago test <name> [args]")
        for _, t in ipairs(TEST_LIST) do
            print(("  %-20s %s"):format(t[1], t[2]))
        end
        return
    end
    name = name:lower()
    for _, t in ipairs(TEST_LIST) do
        if t[1] == name then
            print("[Dwarfipelago] Running test: " .. name)
            local ok, err = pcall(t[3], rest)
            if not ok then
                dfhack.printerr("[Dwarfipelago] test '" .. name .. "' raised: " .. tostring(err))
            end
            return
        end
    end
    dfhack.printerr("[Dwarfipelago] Unknown test '" .. name .. "'. Run 'dwarfipelago test' to list.")
end

-- Called by main.lua when the client delivers an item by name.
function M.receive(item_name)
    local handler = M.handlers[item_name]
    if handler then
        handler()
    else
        log.error("Unknown item received: " .. tostring(item_name))
    end
end

-- reqscript returns the script's _ENV, not the explicit return value.
-- Copy all module exports into _ENV so callers can access them as globals.
for k, v in pairs(M) do _ENV[k] = v end
return M
