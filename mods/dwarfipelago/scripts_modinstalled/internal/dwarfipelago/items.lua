--@ module = true
-- Item spawning for Dwarfipelago.
-- Called when the AP client delivers an item to the fortress.
-- Each handler uses dfhack.run_script or direct df API calls to apply the effect.

local M = {}

local log = reqscript("internal/dwarfipelago/log")

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
            log.error("spawn_item: no depot or citizen — cannot place " .. item_type)
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

-- Bag of sand for glassmaking. Sand isn't a free-standing item — it lives inside
-- a bag — so createitem (one item at a time) can't make it. We use the lower-level
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
        announce("Received: a Sand shipment (delivered as flux — bag-of-sand spawn unavailable).")
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

-- Low-grade (copper) tools/gear — useful recovery, intentionally rare.
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
-- Total count is 2–5; extras are random sex.

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
        announce_at_depot(("Received: %s! (spawn failed — creature absent from world raws)"):format(name))
        return
    end

    local ncastes = 0
    pcall(function()
        for _ in ipairs(df.global.world.raws.creatures.all[race_idx].caste) do
            ncastes = ncastes + 1
        end
    end)
    local female_caste = math.max(1, ncastes - 1)

    -- Guaranteed pair first, then 0–3 random extras for a total of 2–5.
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
        announce_at_depot(("Received: %s! (spawn failed — check DFHack console)"):format(name))
    end
end

local function recv_breeding_pigs()     spawn_livestock("PIG",                  "Breeding Pigs")     end
local function recv_breeding_chickens() spawn_livestock("BIRD_CHICKEN",          "Breeding Chickens") end
local function recv_breeding_alpacas()  spawn_livestock("ALPACA",                "Breeding Alpacas")  end
local function recv_breeding_cows()     spawn_livestock({"CATTLE", "COW"},       "Breeding Cows")     end
local function recv_breeding_sheep()    spawn_livestock("SHEEP",                 "Breeding Sheep")    end
local function recv_breeding_yaks()     spawn_livestock("YAK",                   "Breeding Yaks")     end

-- ── Item handlers: progression gate items ────────────────────────────────────
-- These items are purely flag-based — receiving them writes a persistent key
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
        -- door links to via a general_ref. Order matters — the record is added
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
-- meaningful in-game effect — just a flavour announcement.

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
    -- A goblin-bone totem — the classic war trophy.
    spawn_item("TOTEM", "CREATURE_MAT:GOBLIN:BONE")
    announce_at_depot("A goblin trophy has been delivered. Someone out there is mocking you.")
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
        announce("Trap: A goblin ambush descends — panic grips your dwarves!",
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
    -- Spawn inside the fortress — rats materialise directly in your stockpiles.
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

-- Carve a 5×5 area of floor tiles around the spawn point and reveal hidden tiles
-- so the breach looks like the beast smashed its way through.
local function carve_breach(cx, cy, cz)
    for dx = -2, 2 do
        for dy = -2, 2 do
            local nx, ny = cx + dx, cy + dy
            local block = dfhack.maps.getTileBlock(nx, ny, cz)
            if block then
                local lx, ly = nx % 16, ny % 16
                local tt    = block.tiletype[lx][ly]
                local shape = df.tiletype.attrs[tt].shape
                if shape ~= df.tiletype_shape.FLOOR and shape ~= df.tiletype_shape.OPEN then
                    local floor_tt = dfhack.maps.findSimilarTileType(tt, df.tiletype_shape.FLOOR)
                    if floor_tt and floor_tt ~= 0 then
                        block.tiletype[lx][ly] = floor_tt
                    end
                end
                block.designation[lx][ly].hidden = false
            end
        end
    end
    local b = dfhack.maps.getTileBlock(cx, cy, cz)
    if b then dfhack.maps.enableBlockUpdates(b, true) end
end

-- Map a spawn tile position to a compass direction relative to the embark centre.
-- Returns one of 8 directional strings, or "depths" if very close to centre.
local function get_spawn_direction(sx, sy)
    local map = df.global.world.map
    local dx  = sx - (map.x_count / 2)
    local dy  = sy - (map.y_count / 2)  -- positive y = south in DF
    if math.abs(dx) < 4 and math.abs(dy) < 4 then return "depths" end
    local angle = (math.deg(math.atan2(dy, dx)) + 360) % 360
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
            "[AP] Warning: no underground tile found — precursor spawned at surface instead.",
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

-- Summon the AP megabeast target via DFHack's 'force' command, which routes
-- through the game's own event system. This is version-safe, unlike
-- modtools/create-unit (broken on some DF builds: "world.arena_spawn not found").
--
-- We intentionally do NOT pin a target_id here: the goal hook in dwarfipelago.lua
-- counts any megabeast kill when no target_id is stored, and natural megabeasts
-- are cleared at world load, so the forced beast is the only one in play.
local function spawn_target_megabeast()
    if dfhack.persistent.getWorldDataString("dwarfipelago/megabeast/spawned") == "1" then
        return  -- already summoned this world (e.g. reloaded mid-session)
    end

    local ok, err = pcall(function()
        dfhack.run_command("force", "Megabeast")
    end)
    if not ok then
        dfhack.gui.showAnnouncement(
            "[AP] CRITICAL: Could not force a megabeast — the Slay Megabeast goal cannot be completed.",
            COLOR_RED, true)
        dfhack.gui.showAnnouncement(
            "[AP] This is likely a DFHack compatibility issue. Check the DFHack console / dwarfipelago.log.",
            COLOR_RED, true)
        log.error("force Megabeast failed: " .. tostring(err))
        return
    end

    dfhack.persistent.saveWorldDataString("dwarfipelago/megabeast/spawned", "1")
    dfhack.gui.showAnnouncement(
        "[AP] A great beast has been roused and now marches on your fortress. Slay it!",
        COLOR_RED, true)
    print("[Dwarfipelago] Megabeast summoned via DFHack 'force Megabeast'")
end

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

    -- Directly add citizen dwarves (reliable). 'force Migrants' was unreliable —
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

-- Escalating combat gear granted by Military Training tiers 1-3. These are
-- rewards that help the player prepare for the megabeast — not punishments.
-- All spawns go through spawn_item, which is pcall-guarded and logs failures;
-- each tier also includes steel bars so the player always gets usable material
-- even if a particular weapon/armor token isn't accepted by this DF version.
local function grant_war_gear(tier)
    if tier == 1 then
        -- Arm the recruits: a pair of steel weapons + bars to spare.
        spawn_item("WEAPON:ITEM_WEAPON_AXE_BATTLE",  "INORGANIC:STEEL")
        spawn_item("WEAPON:ITEM_WEAPON_SWORD_SHORT", "INORGANIC:STEEL")
    elseif tier == 2 then
        -- Armor the soldiers: torso, head, and shield.
        spawn_item("ARMOR:ITEM_ARMOR_BREASTPLATE", "INORGANIC:STEEL")
        spawn_item("HELM:ITEM_HELM_HELM",          "INORGANIC:STEEL")
        spawn_item("SHIELD:ITEM_SHIELD_SHIELD",    "INORGANIC:STEEL")
    elseif tier == 3 then
        -- Outfit the elite: full limb protection + heavier weapons.
        spawn_item("GLOVES:ITEM_GLOVES_GAUNTLETS", "INORGANIC:STEEL")
        spawn_item("PANTS:ITEM_PANTS_GREAVES",     "INORGANIC:STEEL")
        spawn_item("SHOES:ITEM_SHOES_BOOTS",       "INORGANIC:STEEL")
        spawn_item("WEAPON:ITEM_WEAPON_SPEAR",     "INORGANIC:STEEL")
        spawn_item("WEAPON:ITEM_WEAPON_HAMMER_WAR","INORGANIC:STEEL")
        spawn_item("BAR", "INORGANIC:STEEL", 5)
    end
end

local function recv_military_training()
    local key = "dwarfipelago/unlock/military_training"
    local n = (tonumber(dfhack.persistent.getWorldDataString(key)) or 0) + 1
    dfhack.persistent.saveWorldDataString(key, tostring(n))

    if n == 1 then
        grant_war_gear(1)
        announce("Military Training received! Your recruits are armed with steel weapons. (1/4)")
    elseif n == 2 then
        grant_war_gear(2)
        announce("Military Training received! Your soldiers don steel armor. (2/4)")
    elseif n == 3 then
        grant_war_gear(3)
        announce("Military Training received! Your elite are fully equipped — the beast nears. (3/4)")
    else
        -- Tier 4: the military is ready; summon the target megabeast.
        announce("Military Training received! Your military is ready — the beast awakens! (4/4)")
        spawn_target_megabeast()
    end
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
    { key = "RotGK",                 label = "Remains of the Great King", max = tonumber(dfhack.persistent.getWorldDataString("dwarfipelago/king_remains_goal"))},
    { key = "baron_charter",         label = "Baron's Charter" },
    { key = "count_charter",         label = "Count's Charter" },
    { key = "duke_charter",          label = "Duke's Charter" },
    { key = "monarch_invitation",    label = "Monarch's Invitation" },
    { key = "master_builders_codex", label = "Master Builder's Codex" },
    { key = "artifact_weapon",       label = "Artifact Weapon" },
    { key = "artifact_armor",        label = "Artifact Armor" },
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

    ["Merchant's Coffer"]    = recv_merchants_coffer,
    ["Immigration Wave"]     = recv_immigration_wave,
    ["Baron's Charter"]      = recv_barons_charter,
    ["Count's Charter"]      = recv_counts_charter,
    ["Duke's Charter"]       = recv_dukes_charter,
    ["Monarch's Invitation"] = recv_monarchs_invitation,
    ["Military Training"]    = recv_military_training,
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
    { "vermin",    "Vermin Infestation trap (rodents)",               function() recv_vermin_infestation() end },
    { "spider",    "Precursor threat (giant cave spider, underground)", function() spawn_precursor_threat() end },
    { "megabeast", "Force the goal megabeast (once per world)",        function() spawn_target_megabeast() end },
    { "migrants",  "Add a wave of citizen dwarves",                    function() recv_immigration_wave() end },
    { "pigs",      "Spawn a breeding group of pigs",                  function() recv_breeding_pigs()     end },
    { "chickens",  "Spawn a breeding group of chickens",              function() recv_breeding_chickens() end },
    { "alpacas",   "Spawn a breeding group of alpacas",               function() recv_breeding_alpacas()  end },
    { "cows",      "Spawn a breeding group of cows",                  function() recv_breeding_cows()     end },
    { "sheep",     "Spawn a breeding group of sheep",                 function() recv_breeding_sheep()    end },
    { "yaks",      "Spawn a breeding group of yaks",                  function() recv_breeding_yaks()     end },
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
        print("[Dwarfipelago] Tests — run as: dwarfipelago test <name> [args]")
        for _, t in ipairs(TEST_LIST) do
            print(("  %-10s %s"):format(t[1], t[2]))
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
