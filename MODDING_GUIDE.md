# Modding Dwarf Fortress: the parts the wiki skips

The DF wiki documents what each raw token *is*. It is much thinner on how the
pieces fit together, what silently does nothing, and where DFHack disagrees with
what you'd reasonably expect. This is a field guide to the second category,
written from things that actually broke while building Dwarfipelago.

Every example here is real code from this repo, and every gotcha is one that cost
someone a debugging session. Version-specific notes are against **DF 50.x /
DFHack 53.x**.

**Contents**

1. [The three rules that explain most confusion](#1-the-three-rules-that-explain-most-confusion)
2. [Mod layout and `info.txt`](#2-mod-layout-and-infotxt)
3. [Custom items: tools as a generic item chassis](#3-custom-items-tools-as-a-generic-item-chassis)
4. [Custom materials, and how they leak](#4-custom-materials-and-how-they-leak)
5. [Custom civilizations](#5-custom-civilizations)
6. [Graphics and tile pages](#6-graphics-and-tile-pages)
7. [World gen presets](#7-world-gen-presets)
8. [Splitting a mod into modules with `reqscript`](#8-splitting-a-mod-into-modules-with-reqscript)
9. [Persistent state](#9-persistent-state)
10. [Reading raws at runtime](#10-reading-raws-at-runtime)
11. [Creating items](#11-creating-items)
12. [Creating buildings and reading zones](#12-creating-buildings-and-reading-zones)
13. [Inventing a god](#13-inventing-a-god)
14. [Reacting to events](#14-reacting-to-events)
15. [Detecting that an item was made](#15-detecting-that-an-item-was-made)
16. [Overlays on DF's own screens](#16-overlays-on-dfs-own-screens)
17. [Building a panel](#17-building-a-panel)
18. [Cross-game state: DeathLink and Energy Link](#18-cross-game-state-deathlink-and-energy-link)
19. [Spawning a siege that actually works](#19-spawning-a-siege-that-actually-works)
20. [Telling the player something](#20-telling-the-player-something)
21. [Taking control away from the player](#21-taking-control-away-from-the-player)
22. [Carving terrain and making citizens](#22-carving-terrain-and-making-citizens)
23. [Performance](#23-performance)
24. [Debugging](#24-debugging)

---

## Part 1: Raws and data files

No DFHack required. These are the text files DF reads at world generation.

---
## 1. The three rules that explain most confusion

### Raws enter a save at world generation, and never again

This is the single most important thing to understand, and the wiki does not put
it anywhere near prominently enough.

When you generate a world, DF copies the enabled mods' raws **into the save**.
From then on, that save reads its own copy. Editing `mods/yourmod/objects/*.txt`
afterwards changes nothing for existing saves: not on reload, not on a DFHack
restart, not ever.

So:

- **New creature, item, material, entity, reaction?** New world required.
- **Changed a Lua script?** Takes effect on reload. Scripts are not raws.

A huge share of "my mod isn't working" is someone editing raws and testing on an
old save.

### `mods/` is your source; `data/installed_mods/` is what world gen reads

Two directories, and they are not the same:

```
<DF>/mods/yourmod/                     <- where you edit
<DF>/data/installed_mods/yourmod (3)/  <- snapshot DF actually reads at world gen
```

When you enable a mod, DF copies it into `data/installed_mods/` under a folder
named `<id> (<NUMERIC_VERSION>)`. Editing your source folder does **not** update
that snapshot. Disable and re-enable the mod in DF's mod manager to regenerate
it, or copy the files across yourself.

The version number is part of the folder name, so bumping `NUMERIC_VERSION`
creates a *new* folder. If a tool of yours writes into `yourmod (15)` and the
snapshot is now `yourmod (16)`, your writes go nowhere and nothing warns you.

There is a nastier consequence: **DFHack resolves mod script paths when the save
loads.** If the snapshot folder is renamed while a save is open, your scripts
stay pointed at the old path and your commands stop resolving with
`not a recognized command`. Reload the save.

### DF data locations differ per install

Depending on platform and how DF was installed, the "DF directory" may be the
install directory, a user-data directory, or both:

| Platform | User data directory |
|---|---|
| Windows | `%APPDATA%\Bay 12 Games\Dwarf Fortress\` |
| macOS | `~/Library/Application Support/Bay 12 Games/Dwarf Fortress/` |
| Linux | `~/.local/share/Bay 12 Games/Dwarf Fortress/` |

Both that and the install directory can hold `mods/`, `data/installed_mods/`,
`prefs/` and `save/`. If you write tooling, check every candidate root rather
than assuming.

And do not assume the DF folder is `dirname(path_to_executable)`. Players
legitimately point tools at `dfhack.exe`, and the standalone DFHack Steam app
installs to `steamapps/common/DFHack/hack/`, a completely different tree. Look
for DF's own markers (`data/vanilla`, `prefs`, `mods`) to confirm you found the
real thing.

---

## 2. Mod layout and `info.txt`

```
mods/yourmod/
  info.txt                  <- required
  objects/                  <- raws: creatures, items, materials, entities, reactions
  graphics/                 <- raws: tile pages and sprite definitions
    images/                 <- the actual PNGs
  scripts_modinstalled/     <- DFHack Lua, auto-added to the script path
```

`info.txt`:

```
[ID:yourmod]
[NUMERIC_VERSION:16]
[DISPLAYED_VERSION:2.0.1]
[EARLIEST_COMPATIBLE_NUMERIC_VERSION:15]
[EARLIEST_COMPATIBLE_DISPLAYED_VERSION:2.0.0]
[AUTHOR:Your Name]
[NAME:Your Mod]
[DESCRIPTION:One paragraph. No line breaks.]
```

- `NUMERIC_VERSION` is what DF compares and what names the snapshot folder. Bump
  it when content changes.
- `EARLIEST_COMPATIBLE_NUMERIC_VERSION` controls whether DF will load an existing
  save made with an older version of your mod. Raising it to the current version
  makes DF refuse older saves. That is correct when your raws changed in a way that
  breaks them, unkind otherwise.

**`scripts_modinstalled/` is added to DFHack's script path automatically** when
the mod is enabled. A script at `scripts_modinstalled/yourmod.lua` is runnable as
`yourmod` in the DFHack console. Subfolders work as paths:
`internal/yourmod/state.lua` is `reqscript("internal/yourmod/state")`.

### Raws are single-byte text. Keep them ASCII

DF reads raws as single-byte text, not UTF-8. A curly apostrophe or an em dash in
a `[NAME:...]` token renders as garbage.

This bites hardest when generating raws programmatically. Writing with strict
`latin-1` will *raise* on the first non-encodable character, and if you opened
the file first, you have already truncated it to zero bytes. Transliterate to
ASCII before writing, and use a replacing error handler as a backstop.

Comments in Lua are fine (the lexer discards them), but anything that reaches
DF (announcement text, item names, material names) should be ASCII.

---

## 3. Custom items: tools as a generic item chassis

`ITEM_TOOL` is the most flexible custom item type. Unlike weapons or armour it
has no required combat or wear properties, and no entity has to be granted it.

```
[OBJECT:ITEM]

[ITEM_TOOL:ITEM_TOOL_AP_TIER1]
	[NAME:AP Items (Tier 1):AP Items (Tier 1)]
	[VALUE:100]
	[TILE:15]
	[HARD_MAT]
	[SIZE:200]
	[MATERIAL_SIZE:1]
	[NO_DEFAULT_JOB]
```

Points that are not obvious:

- **`[NAME:singular:plural]`**: both are required.
- **`[NO_DEFAULT_JOB]`** stops the tool appearing as a craftable job at
  workshops. Without it, players can make your special item out of anything.
- **If no entity has `[TOOL:ITEM_TOOL_YOURS]`, no civilization will ever craft or
  trade it.** That is the cleanest way to make an item that only exists when your
  script creates one.

### Item value is item value x material value

```
item value = [VALUE:n] on the itemdef  x  [MATERIAL_VALUE:m] on the material
```

A `VALUE:100` tool made of a `MATERIAL_VALUE:10` material is worth 1000. This is
the lever for pricing custom items: keep the itemdef value fixed and vary the
material, or vice versa.

Watch out on the trade screen: **DF hides true values behind an estimate based on
your broker's Appraisal skill.** Above a skill-dependent cap it shows a single
capped number for *everything*, so a 2,000 and a 100,000 item look identical.
With no appraiser the cap is around 1,500. If you are debugging prices, read the
material value directly instead of trusting the screen:

```lua
dfhack.matinfo.find("INORGANIC:YOUR_MAT").material.material_value
```

And note that the raw item value is not the trade price. `dfhack.items.getValue`
takes an optional caravan:

```lua
dfhack.items.getValue(item)                 -- base value
dfhack.items.getValue(item, caravan_state)  -- modified by civ + trade agreements
```

So what a caravan charges depends on who it is and what you have agreed with
them, not on the itemdef alone.

---

## 4. Custom materials, and how they leak

A minimal inorganic:

```
[OBJECT:INORGANIC]

[INORGANIC:YOUR_MAT]
	[STATE_NAME_ADJ:ALL_SOLID:your material]
	[MATERIAL_VALUE:10]
	[DISPLAY_COLOR:7:0:0]
	[SPEC_HEAT:800]
	[IGNITE_POINT:NONE]
	[MELTING_POINT:11500]
	[BOILING_POINT:14000]
	[HEATDAM_POINT:NONE]
	[COLDDAM_POINT:NONE]
	[MAT_FIXED_TEMP:NONE]
	[SOLID_DENSITY:2670]
```

### The trap: templates and usage flags make your material selectable

The obvious way to write that is `[USE_MATERIAL_TEMPLATE:STONE_TEMPLATE]` plus
`[IS_STONE]`. Do that and your material shows up **in the player's crafting
material pickers**. "Make rock blocks" will list it between Alabaster and
Andesite.

Two separate causes:

- `[IS_STONE]` puts it in stone pickers.
- `STONE_TEMPLATE` silently grants `[ITEMS_HARD]` and `[ITEMS_QUERN]`, which
  offer it to any hard-material job.

If your material exists to carry a name or a value rather than to be crafted
with, **inherit no template and set no usage flags.** Copy the temperature and
density tokens literally, as above, so the material still behaves sanely.

This matters beyond tidiness. If the material's name is content the player should
not see yet, a crafting picker will happily display the whole list.

### Materials can be renamed and repriced at runtime

Raws are fixed at world gen, but the loaded material struct is not. You can
rewrite a material's display name and value while the game runs:

```lua
local mat = dfhack.matinfo.find("INORGANIC:YOUR_MAT").material
mat.state_name.Solid = "Some New Name"
mat.state_adj.Solid  = "Some New Name"
mat.material_value   = 42
```

This is in-memory only, because DF reloads raws from the save on every load, so re-apply
it from your poll loop. Compare before writing so it is a no-op after the first
pass, and it will self-heal after a reload.

Ship N placeholder materials in your raws, then write real names into them at
runtime. Your mod then works in any world generated with it, rather than only in
worlds generated after some external step.

---

## 5. Custom civilizations

An entity raw defines a civilization: what it is, what it makes, whether it
trades with you.

```
[OBJECT:ENTITY]

[ENTITY:ARCHIPELAGO]
	[CREATURE:GORLAK]
	[TRANSLATION:HUMAN]
	[DEFAULT_SITE_TYPE:CITY]
	[LIKES_SITE:CITY]
	[START_BIOME:ANY_GRASSLAND]
	[START_BIOME:ANY_SAVANNA]
	[BIOME_SUPPORT:ANY_FOREST:2]
	[ACTIVE_SEASON:SUMMER]
	[PROGRESS_TRIGGER_TRADE:1]
	[MERCHANT_NOBILITY]
	[MERCHANT_BODYGUARDS]
	[CURRENCY:COPPER:1]
	[TOOL:ITEM_TOOL_JUG]
	[PERMITTED_JOB:TRADER]
```

### Whether a civ's caravan ever reaches you

Three conditions, all required, and all easy to miss:

1. **The civ exists in the world.** Determined at world gen from `START_BIOME`
   and site preferences. A civ whose biomes never generated will not exist.
2. **It is a neighbour of your embark.** DF only sends caravans from civs whose
   territory borders your embark site. Check the **Neighbors** panel on the
   embark screen.
3. **Your fort is worth the trip.** `PROGRESS_TRIGGER_TRADE` and friends gate
   when they bother.

Condition 2 catches people out badly: the civ exists, the mod is installed,
everything looks right, and no caravan ever comes. It cannot be fixed after
embark except by re-embarking elsewhere in the same world.

### The race is the civ's, not the unit's

If you want merchants of a particular race, set `[CREATURE:X]` on the **entity**.
Do not try to change `unit.race` on the merchants at runtime. DF re-derives it
from the sending civ every tick and your edit reverts on unpause.

`[TRANSLATION:HUMAN]` is independent of race and just picks the name-generation
language.

`[ALL_MAIN_POPS_CONTROLLABLE]` and `SITE_CONTROLLABLE` affect whether the player
can embark *as* this civ. Leave `SITE_CONTROLLABLE` off if you only want them as
an NPC trade partner.

---

## 6. Graphics and tile pages

Two files. A tile page declares the sprite sheet:

```
[OBJECT:TILE_PAGE]

[TILE_PAGE:YOURMOD_ITEMS]
	[FILE:images/your_items.png]
	[TILE_DIM:32:32]
	[PAGE_DIM:1:1]
```

`TILE_DIM` is the pixel size of one tile; `PAGE_DIM` is the sheet size in tiles.
`FILE` is relative to the `graphics/` folder.

Then bind sprites to objects:

```
[OBJECT:GRAPHICS]

[TOOL_GRAPHICS:YOURMOD_ITEMS:0:0:ITEM_TOOL_YOURS]
```

The two numbers are the tile's x and y **in tiles, not pixels**. Both files must
start with a line matching the filename, then the `[OBJECT:...]` token.

---

## 7. World gen presets

A world gen preset is an appended block in `prefs/world_gen.txt`:

```
[WORLD_GEN]
	[TITLE:YourPreset]
	[DIM:65:65]
	[END_YEAR:120]
	[TOTAL_CIV_NUMBER:20]
	[PLAYABLE_CIVILIZATION_REQUIRED:1]
	[REGION_COUNTS:FOREST:264:2:2]
	[VOLCANO_MIN:5]
	[CAVERN_LAYER_COUNT:3]
```

Useful things to know:

- **`prefs/world_gen.txt` may live in either data root** (see section 1). If a player
  has both, install to both.
- **Appending is safe.** Multiple `[WORLD_GEN]` blocks coexist; players pick by
  title. Do not rewrite the file.
- **DF reads it at startup.** Restart DF before the preset appears.
- **`REGION_COUNTS:<biome>:<count>:<min>:<max>`**: the last two are the minimum
  and maximum number of *regions* of that biome. Setting a minimum is how you
  guarantee a habitat exists for a civ that needs it.
- **`PLAYABLE_CIVILIZATION_REQUIRED:1`** rejects worlds with no playable civ,
  which saves rerolling by hand.

Presets constrain generation; they cannot guarantee any particular *embark* has
what you need. See the neighbour problem in section 5.

---

## Part 2: DFHack scripting

Everything below needs DFHack. These run while the game is running.

---
## 8. Splitting a mod into modules with `reqscript`

Once a mod outgrows one file you want to split it up. DFHack's mechanism for this
is `reqscript`, and it has one piece of required boilerplate that is very easy to
get wrong because **the failure is silent**.

### The two halves

Every module needs a marker at the top:

```lua
--@ module = true
```

and an export line at the bottom:

```lua
local M = {}

function M.do_something() ... end
function M.do_another() ... end

-- reqscript returns the script's _ENV; copy exports so callers can use them.
for k, v in pairs(M) do _ENV[k] = v end
return M
```

Then callers do:

```lua
local log = reqscript("internal/yourmod/log")
log.info("hello")
```

### Why the `_ENV` line is needed

This is the part that catches people. **`reqscript` returns the script's
environment, not whatever you `return`.** The docs put it plainly: it "returns its
environment (i.e., a table of all global functions and variables)".

So a module that collects its functions in a local table `M` and ends with
`return M` has exported *nothing*. `M` is a local; it never reached `_ENV`. The
caller gets an environment table with no `do_something` in it, and the failure
looks like `attempt to call a nil value (field 'do_something')` at some unrelated
call site later.

The loop copies each entry from your module table into the environment, which is
what the caller actually receives. Keeping `return M` as well is harmless and
makes the file readable as a normal Lua module.

The alternative is to declare functions as globals directly (`function
do_something()` with no `local`), which lands them in `_ENV` automatically. The
`M` table plus the copy loop is tidier: everything exported is in one visible
place, and anything not in `M` stays private.

### The marker must be exactly right

`reqscript` refuses to load a script without the marker, and the accepted spellings
are stricter than they look:

```lua
--@ module = true    OK
--@module = true     OK
-- @module = true    NOT OK  (space after --)
 --@module = true    NOT OK  (leading whitespace)
---@module = true    NOT OK  (three dashes, so --@ is not at line start)
```

That last one is a real trap if you use a Lua language server, since `---@` is
LuaLS annotation syntax and an editor may reformat your marker into something DF
will not accept.

### Guard your side effects

`reqscript` executes the file. Anything at file scope runs on import, which is not
what you want for a script that is both a module and a command:

```lua
-- function definitions above

if dfhack_flags.module then
    return
end

-- main script code with side effects below
```

Without this, importing your main script to reach one helper also runs its command
line handling.

### Paths and reloading

The argument is a path relative to any registered script directory, without the
`.lua`:

```lua
reqscript("internal/yourmod/state")   -- scripts_modinstalled/internal/yourmod/state.lua
```

Circular dependencies are supported, provided the modules have no load-time side
effects. That is another reason to keep the `dfhack_flags.module` guard.

Modules are cached. Editing a module file and re-running your command may keep the
old version until the script is reloaded, which is a common source of "I fixed
that already".

---

## 9. Persistent state

DFHack gives you key-value storage scoped to the world, surviving save and
reload:

```lua
dfhack.persistent.saveWorldDataString("yourmod/some_key", "value")
local v = dfhack.persistent.getWorldDataString("yourmod/some_key")
dfhack.persistent.deleteWorldData("yourmod/some_key")
```

Conventions worth adopting:

- **Namespace every key** with your mod id. It is a global store.
- **Values are strings.** Numbers need `tonumber`; structures need JSON
  (`require('json')`).
- **Three states, not two.** A key never written returns `nil`; a key written
  empty returns `""`. That distinction is genuinely useful ("never armed" versus
  "armed and then cleared"), but only if you are deliberate about it.

It is world data, not fort data, so it survives abandoning and re-embarking in
the same world. If you want something to persist across re-embark, this is how.

---

## 10. Reading raws at runtime

### The `.all` trap

Several raw collections are **structs containing a vector**, not vectors:

```lua
-- WRONG: iterates nothing, raises no error
for i, raw in ipairs(df.global.world.raws.inorganics) do

-- RIGHT
for i, raw in ipairs(df.global.world.raws.inorganics.all) do
```

This applies to `inorganics`, `creatures`, `plants`, `itemdefs` and `entities`.
The failure mode is the worst kind: the loop body simply never runs, no error is
raised, and your code concludes the thing does not exist. If a scan mysteriously
finds nothing, check this first.

A quick way to tell:

```lua
print(#df.global.world.raws.inorganics)      -- errors: it is a struct
print(#df.global.world.raws.inorganics.all)  -- works
```

### Finding things by token

```lua
local mi = dfhack.matinfo.find("INORGANIC:IRON")
if mi then print(mi.type, mi.index) end
```

`matinfo.find` handles `INORGANIC:X`, `CREATURE_MAT:COW:LEATHER`,
`PLANT_MAT:MUSHROOM_HELMET_PLUMP:MUSHROOM` and similar. It returns `nil` for
anything not in this world's raws, which is how you detect "world generated
without my mod".

Item subtypes need a scan, because the numeric subtype is assigned at load:

```lua
local function tool_subtype(tool_id)
    for _, td in ipairs(df.global.world.raws.itemdefs.tools) do
        if td.id == tool_id then return td.subtype end
    end
end
```

### `getSubtype()` versus `.subtype`

```lua
item:getSubtype()   -- numeric subtype index; what you compare against
item.subtype        -- the itemdef OBJECT, not a number
```

Comparing `item.subtype` to a number silently never matches.

---

## 11. Creating items

```lua
local made = dfhack.items.createItem(unit, item_type, subtype, mat_type, mat_index, false)
local item = made and made[1]
```

- Returns a **table**, not an item. Take `[1]`.
- The unit argument is the creator/owner context, and is required.
- The last argument is `no_floor`. Passing `true` gives the item no map position,
  which breaks several later operations. Pass `false` unless you know otherwise.
- **New items are created forbidden.** Clear `item.flags.forbid` if you want
  dwarves to interact with it.

### Putting an item somewhere

```lua
dfhack.items.moveToBuilding(item, building, 0)
dfhack.items.moveToInventory(item, unit, role, body_part_id)
dfhack.items.moveToGround(item, pos)
```

`moveToInventory(item, unit[, use_mode[, body_part]])` defaults to
`use_mode = Hauled` and `body_part = -1`, which is fine for "carry this". To
actually **equip** an item (a weapon in a hand, armour on a torso) pass both an
explicit role and an explicit body part id; the `-1` default does not attach it.
Find the id by scanning the caste's body parts for the flag you want (`GRASP` for
hands, and note there are usually two).

### Making an item caravan merchandise

Not obvious, and it took a while to find: an item only counts as a caravan's
goods if it carries an ownership reference to the **merchants' civ**:

```lua
item.flags.trader = true
dfhack.items.moveToBuilding(item, depot, 0)
item.flags.in_building = true

local ref = df.general_ref_entity_itemownerst:new()
ref.entity_id = merchant_unit.civ_id
item.general_refs:insert("#", ref)
```

Without the ownership ref, DF omits the item from the trade list *and* leaves it
behind when the caravan departs. Read the civ from a docked merchant
(`unit.flags1.merchant`), not from some other item at the depot, which may carry
a stale owner.

### `items.remove` does nothing while paused

```lua
dfhack.items.remove(item)   -- no-op if the game is paused
```

If you clear tracking state assuming the removal succeeded, you leak items *and*
forget about them. Verify, and retry later if it did not take:

```lua
local still = df.item.find(id)
local gone = (still == nil) or (still.flags.garbage_collect == true)
```

---

## 12. Creating buildings and reading zones

Constructing a real, finished building:

```lua
dfhack.buildings.constructBuilding{
    type   = df.building_type.TradeDepot,
    pos    = {x = tx, y = ty, z = z},
    width  = 5,
    height = 5,
}
```

This creates it complete: no job, no materials, no dwarves. The position is the
building's **top-left corner**, not its centre, and the tiles must be clear.
Wrap it in `pcall` and be prepared for failure on uneven or occupied ground.

### Zones are not buildings

Player-designated zones (bedrooms, dining halls, temples) are civzones, found in
a separate list:

```lua
for _, z in ipairs(df.global.world.buildings.other.ANY_ZONE) do
    local ok, subtype = pcall(function() return z:getSubtype() end)
    if ok and subtype == df.civzone_type.Bedroom then
        -- ...
    end
end
```

Use `df.global.world.buildings.other.ANY_ZONE`, not `buildings.all`. The latter
is every building in the fort and much more expensive to walk.

Room quality (the "Decent Quarters" / "Royal Bedroom" tiers) is a value DF
computes per zone. Read it rather than recomputing from furniture.

---

## 13. Inventing a god

Adding a worshippable deity is not a raw at all. DF builds the "dedicate a
temple" list from **citizens' worship links**, so you create a historical figure
flagged as a deity, then link a citizen to it.

```lua
local hf = df.historical_figure:new()
hf.race  = dwarf_race_index
hf.caste = 0
hf.sex   = -1
-- every year/seconds field must be -1, or DF treats it as a real lifespan
hf.appeared_year, hf.born_year, hf.born_seconds = -1, -1, -1
hf.died_year, hf.died_seconds = -1, -1
hf.breed_id = -1

hf.name.has_name   = true
hf.name.first_name = "Yourgod"
hf.flags.deity     = true
hf.flags.never_cull = true

hf.info = df.historical_figure_info:new()
hf.info.metaphysical = {new = true}
hf.info.known_info   = {new = true}
for _, sphere in ipairs({df.sphere_type.TRADE, df.sphere_type.WEALTH}) do
    hf.info.metaphysical.spheres:insert('#', sphere)
end

hf.pool_id = -1
hf.id = df.global.hist_figure_next_id
df.global.hist_figure_next_id = df.global.hist_figure_next_id + 1
df.global.world.history.figures:insert('#', hf)
```

Then link a living citizen:

```lua
local lnk = df.histfig_hf_link_deityst:new()
lnk.target_hf     = deity_id
lnk.link_strength = 50
citizen_hf.histfig_links:insert('#', lnk)
```

One worshipping citizen is enough for the god to appear in the temple list.

Details that matter: the `-1` sentinels are not optional (a deity with a real
born year gets treated as a mortal), `hf.info.metaphysical` must be allocated
before you insert spheres, and you must increment `hist_figure_next_id` yourself.
Make the whole thing idempotent by scanning `history.figures` for your name
first, or every reload adds another god.

---

## 14. Reacting to events

`eventful` gives callbacks instead of polling:

```lua
local eventful = require('plugins.eventful')

eventful.enableEvent(eventful.eventType.JOB_COMPLETED, 1)
eventful.onJobCompleted[MY_MOD_NAME] = function(job) ... end

eventful.enableEvent(eventful.eventType.ITEM_CREATED, 1)
eventful.onItemCreated[MY_MOD_NAME] = function(item_id) ... end
```

- **`enableEvent` is required.** The handler table is not initialised until you
  call it, so registering a handler without it silently does nothing. The second
  argument is the tick frequency.
- **Key handlers by a unique name** so you can unregister cleanly
  (`eventful.onJobCompleted[MY_MOD_NAME] = nil`).
- Manager work orders do **not** fire `onJobCompleted`. If you count produced
  items, see section 15, which covers that gap and the rest of the item-detection
  problem in full.

Prefer events to polling wherever the game will tell you. They are far cheaper
than scanning, and they keep working when your poll loop is throttled.

---

## 15. Detecting that an item was made

"Count how many X the fort has produced" sounds like one question. It is actually
three, and each has a different answer with different blind spots.

### There is no single reliable signal

| Signal | Fires for | Misses |
|---|---|---|
| `onJobCompleted` | manual workshop jobs | manager work orders |
| `onItemCreated` | anything DF creates | nothing, but fires for far more than crafting |
| polling `manager_orders` | manager work orders | everything else |

**Manager work orders do not fire `onJobCompleted`.** That single fact is the
reason this section exists. A player who queues everything through the manager,
which is most players past the first year, would register nothing at all.

So you need at least two of the three, and you need to be careful that an item
made through a path covered by two of them is not counted twice.

### Both events must be enabled explicitly

```lua
local eventful = require('plugins.eventful')

eventful.enableEvent(eventful.eventType.ITEM_CREATED, 1)
eventful.enableEvent(eventful.eventType.JOB_COMPLETED, 1)

eventful.onItemCreated[MY_MOD]   = on_item_created
eventful.onJobCompleted[MY_MOD]  = on_job_completed
```

`enableEvent` initialises the handler table. Without it your assignment lands in
a table nobody reads, and you get silence rather than an error. The second
argument is how many ticks between checks; `1` means every tick.

Unregister by setting the same keys to `nil` when your mod stops, or a reload
leaves a stale handler pointing at dead state.

### `onItemCreated` gives you an id, not an item

```lua
local function on_item_created(item_id)
    if not state.is_enabled() then return end
    local item = df.item.find(item_id)
    if not item then return end
    local ok, type_name = pcall(function() return df.item_type[item:getType()] end)
    ...
end
```

The hook fires for **everything**: crafted output, butchery results, plants
harvested, loot on a dead goblin, items your own script creates. Filtering is
your job, and `item:getType()` is the main tool.

Watch for the self-inflicted case. If your mod creates items, its own creations
come back through this hook. When a gifted adamantine weapon would otherwise fire
"you mined adamantine", you need an explicit exclusion.

### Prefer the item over the job where you can

Counting from the produced item is more robust than counting from the job:

```lua
-- A mechanism is a TRAPPARTS item. Detecting the item is robust to HOW it was
-- made: manual job, manager order, anything. The job path (ConstructMechanisms)
-- misses manager orders entirely.
if type_name == "TRAPPARTS" and not production_flag("mechanism") then
    set_production_flag("mechanism")
end
```

The item exists no matter which route produced it. Use the job path only when the
item type alone cannot tell you what you need, such as when one item type has
several meanings.

### Job names changed in DF 50

If you do map job types, map both spellings:

```lua
map("MakeTable",      "table")   -- pre-50 / Classic
map("ConstructTable", "table")   -- DF 50+
map("CarveStatue",    "crafted_item")
map("CarveFurniture", "crafted_item")
```

A mod that only knows one set silently counts nothing on the other version.

### Catching manager orders by polling

Manager orders expose remaining and total counts, so you watch them fall:

```lua
for _, order in ipairs(df.global.world.manager_orders.all) do
    local prev = _order_amounts[order.id]
    if prev and order.amount_left < prev.left then
        local delta = prev.left - order.amount_left
        -- A player shrinking an order (x50 -> x25) also reduces amount_left.
        -- Subtract the change in total, or resizing counts as production.
        if prev.total and order.amount_total < prev.total then
            delta = delta - (prev.total - order.amount_total)
        end
        if delta > 0 then count(delta) end
    end
    _order_amounts[order.id] = {left = order.amount_left, total = order.amount_total}
end
```

The resize correction is the non-obvious part. Without it, a player trimming a
work order is indistinguishable from completing several jobs.

Note `manager_orders` is one of the struct-with-`.all` cases from section 10, and
older builds expose it directly, hence `mo.all or mo` if you support both.

### Storing counts

Counters go in persistent storage, one key per thing you count:

```lua
local key = "yourmod/craft_count/" .. flag
local raw = dfhack.persistent.getWorldDataString(key)
if raw == nil then return end          -- not tracked this game; do not create it
dfhack.persistent.saveWorldDataString(key, tostring((tonumber(raw) or 0) + 1))
```

**Only count what something asked you to count.** Pre-create keys for the things
this playthrough cares about, and treat a missing key as "not tracked" rather
than starting at zero. Otherwise every unrelated workshop job creates a key and
your persistent data grows without limit.

That distinction relies on `nil` versus `""` from section 9: a key that was never
written is genuinely absent, which is exactly the signal you need here.

### Passing item details to an external tool

If something outside DF needs the details, flatten the item at capture time.
Holding a `df.item` pointer across ticks is not safe:

```lua
local function item_to_info(item)
    local type_name = df.item_type[item:getType()] or "UNKNOWN"
    if SKIP_ITEM_TYPES[type_name] then return nil end
    local mat = "unknown"
    local ok, m = pcall(dfhack.matinfo.decode, item)
    if ok and m then mat = m:toString() or mat end
    local quality = 0
    pcall(function() quality = item.quality end)   -- not every item struct has it
    return {id = item.id, type = type_name, material = mat,
            quality = quality, artifact = item.flags.artifact == true}
end
```

`item.quality` does not exist on every item struct, so guard it. Then append to a
capped JSON queue so a slow or absent consumer cannot grow your save forever:

```lua
local ITEM_EVENT_CAP = 500

local function queue_item_event(key, entry)
    local queue = json.decode(dfhack.persistent.getWorldDataString(key) or "[]") or {}
    table.insert(queue, entry)
    if #queue > ITEM_EVENT_CAP then table.remove(queue, 1) end
    dfhack.persistent.saveWorldDataString(key, json.encode(queue))
end
```

Dropping the oldest entry is the right trade: an unbounded queue in world data
bloats every save and eventually stalls whatever parses it.

A skip list is worth having too. Corpses, body parts, vermin and harvested plants
are created constantly and are almost never what you mean by "made".

---

## 16. Overlays on DF's own screens

An overlay is a widget DFHack draws on top of a DF screen. This is how you add
information to vanilla UI you do not control: marking which workshop tasks are
locked, showing a progress counter next to a job, adding a button.

### Registering one

```lua
local overlay = require('plugins.overlay')
local widgets = require('gui.widgets')

MyOverlay = defclass(MyOverlay, overlay.OverlayWidget)
MyOverlay.ATTRS{
    desc            = "What this does, shown in the overlay control panel",
    default_pos     = {x = 1, y = 1},
    default_enabled = true,
    viewscreens     = {
        'dwarfmode/ViewSheets/BUILDING/Workshop',
        'dwarfmode/Info/WORK_ORDERS/Create',
    },
    frame = {w = 1, h = 1},
}

function MyOverlay:onRenderBody(dc)
    -- draw here
end

OVERLAY_WIDGETS = {
    mywidget = MyOverlay,
}
```

- **`OVERLAY_WIDGETS` is the whole registration mechanism.** DFHack discovers the
  global table when the script loads. The widget's public name becomes
  `<scriptname>.<key>`, here `yourmod-overlays.mywidget`, which is what
  `overlay enable` and `overlay disable` take.
- **`viewscreens` scopes it.** The widget only renders on those focus strings, so
  an overlay bound to a workshop sheet costs nothing everywhere else. Find the
  string for the screen you care about with `dfhack.gui.getCurFocus(true)`.
- **`frame = {w=1, h=1}`** is right when you paint at absolute coordinates rather
  than laying out child widgets.
- `default_enabled` only sets the initial state; players can toggle it, and their
  choice persists.

### Two update paths, very different costs

```lua
function MyOverlay:onRenderBody(dc)      -- every frame while the screen is up
function MyOverlay:overlay_onupdate()    -- periodic, cheaper
```

`onRenderBody` runs **every frame**. On your machine's own profile, overlays were
the single largest DFHack cost, several times the Lua update total, precisely
because of this. Do drawing there and nothing else.

### Reading what DF has drawn

There is no API for "what rows are in this list". The practical technique is to
scrape the rendered screen:

```lua
local function read_screen_row(y, width)
    local chars = {}
    for x = 0, width - 1 do
        local pen = dfhack.screen.readTile(x, y)
        local ch = pen and pen.ch
        chars[x + 1] = (ch and ch >= 32 and ch < 127) and string.char(ch) or " "
    end
    return table.concat(chars)
end
```

Walk the rows, match the text you care about, remember the y coordinates, then
paint next to them:

```lua
dfhack.screen.paintString(MY_PEN, x, y, "(3/15)")
```

Scraping every row every frame is far too expensive, so scan on a frame budget
and reuse the result:

```lua
local RESCAN_FRAMES = 2

function MyOverlay:onRenderBody(dc)
    self.frames_since_scan = self.frames_since_scan + 1
    if self.frames_since_scan >= RESCAN_FRAMES then
        self.frames_since_scan = 0
        self:scan()          -- the expensive screen read
    end
    for _, row in ipairs(self.rows) do
        dfhack.screen.paintString(MY_PEN, row.finish + 1, row.y, text_for(row))
    end
end
```

Two frames is a good default: imperceptible to the player, and it cuts the scan
cost by half or more. Reset the counter in `init` so the first render scans
immediately rather than showing a blank overlay.

Pens are made once, at file scope, not per frame:

```lua
local LOCKED_PEN    = to_pen{ fg = COLOR_RED,   bg = COLOR_BLACK, bold = true }
local COMPLETED_PEN = to_pen{ fg = COLOR_GREEN, bg = COLOR_BLACK }
```

Scraping is fragile by nature. It breaks if DF changes its layout or the player
uses a different font width. Match loosely, guard with `pcall`, and degrade to
drawing nothing rather than drawing in the wrong place.

---

## 17. Building a panel

For your own UI, rather than annotating DF's, build a window with `gui.widgets`.

### Skeleton

```lua
local gui     = require('gui')
local widgets = require('gui.widgets')

MyPanel = defclass(MyPanel, gui.ZScreen)
MyPanel.ATTRS{ focus_path = "yourmod/panel" }

function MyPanel:init()
    local tabviews, tab_list = {}, {}
    table.insert(tabviews, StatusTab())     -- each tab fn appends its own label
    table.insert(tabviews, ChecksTab())

    local pages = widgets.Pages{ frame = {t=4, b=2}, subviews = tabviews }

    self:addviews{
        widgets.Window{
            frame_title = "Your Mod",
            frame       = {w=76, h=48, t=3, l=3},
            resizable   = true,
            resize_min  = {w=46, h=20},
            subviews    = {
                widgets.TabBar{
                    frame  = {t=0, l=0},
                    labels = tab_list,
                    on_select = function(idx) pages:setSelected(idx) end,
                },
                pages,
            },
        },
    }
end
```

### Pages isolate input, which you can rely on

`Pages:init` sets every subview `visible = false` and shows only the selected
one, and DFHack dispatches input only to visible children. So the **same hotkey
can mean different things on different tabs** without conflicting, because only the
active tab ever receives the key.

Useful, but it does mean a collision will not announce itself. Keep a list of
what you have bound.

### The `widgets.List` pen trap

This one costs an afternoon. A `List` **ignores a top-level `pen` on a string
choice.** Colour has to be inside a text token:

```lua
-- IGNORED
{text = "Some row", pen = COLOR_LIGHTRED}

-- WORKS
{text = {{text = "Some row", pen = COLOR_LIGHTRED}}}
```

Worth writing one converter and routing every row through it:

```lua
local function lines_to_choices(lines)
    local choices = {}
    for _, line in ipairs(lines) do
        if type(line) == "string" then
            table.insert(choices, {text = {{text = line, pen = COLOR_WHITE}}})
        elseif type(line.text) == "table" then
            table.insert(choices, line)             -- already tokenised
        else
            table.insert(choices, {text = {{text = line.text or "", pen = line.pen or COLOR_WHITE}}})
        end
    end
    return choices
end
```

Then build plain `{text=..., pen=...}` lines everywhere and convert once.

### Use the light colour variants

On the panel's black background, `COLOR_BLUE` (1) and `COLOR_RED` (4) are close
to unreadable. Use `COLOR_LIGHTBLUE` (9) and `COLOR_LIGHTRED` (12). The dark
variants are fine as backgrounds, not as text.

### Buttons

```lua
widgets.HotkeyLabel{
    frame       = {t=8, l=0},
    key         = "CUSTOM_SHIFT_M",
    label       = function() return toggled and "Mode: ON" or "Mode: off" end,
    enabled     = function() return some_condition end,
    on_activate = function() ... end,
}
```

`label` and `enabled` accept functions, evaluated at render, so a button can
re-label itself from live state without you rebuilding the view.

For anything destructive, confirm first:

```lua
local dialogs = require('gui.dialogs')
dialogs.showYesNoPrompt("Reset everything",
    "This cannot be undone.", COLOR_RED,
    function() do_the_thing() end)
```

`dialogs.showInputPrompt` covers the "how many?" case.

### Refreshing

A `List` does not poll. Rebuild its choices when something changes:

```lua
local function refresh()
    list:setChoices(lines_to_choices(build_lines()))
end
```

Call that from whatever mutated the state, rather than rebuilding every frame.

---

## 18. Cross-game state: DeathLink and Energy Link

These are Archipelago concepts, but the DF-side problems are general: how do you
make a game event leave the fort, and how do you apply an outside event to it
without corrupting your own bookkeeping.

### DeathLink: counting deaths that are really yours

The send side hangs off `onUnitDeath`. The whole difficulty is deciding what
counts as a citizen death:

```lua
local function was_citizen(unit)
    local ok, civ_ok = pcall(function()
        return unit.civ_id == df.global.plotinfo.civ_id
    end)
    if not (ok and civ_ok) then return false end
    -- Owned livestock share the fort civ_id, so butchering would otherwise
    -- register as a citizen death.
    local anim = false
    pcall(function() anim = dfhack.units.isAnimal(unit) end)
    if anim then return false end
    if unit.flags1.merchant or unit.flags1.diplomat then return false end
    if unit.flags2.visitor or unit.flags2.visitor_uninvited then return false end
    if unit.flags2.resident then return false end
    return true
end
```

The livestock case is the one that bites. `civ_id` alone looks like the obvious
test and is wrong: every owned animal shares it, so a butcher shop quietly
becomes a death broadcaster.

Note this deliberately does not use the normal "is a citizen" helper, because by
the time the hook fires the unit is dead and liveness checks reject it. Death
hooks generally need a different predicate from the live ones.

### The re-entrancy trap

Applying an incoming death means killing your own dwarves, which fires your own
death hook, which wants to send a death out. Left alone, two linked games will
ping-pong until everyone is dead.

Mark the unit **before** killing it:

```lua
-- kill() may fire onUnitDeath synchronously here, or on a later tick.
-- Either way this death must not count toward our outgoing threshold.
deathlink_killed_ids[uid] = true

local ok, err = pcall(function()
    if dfhack.units.kill then
        dfhack.units.kill(unit)
    else
        unit.body.blood_count = 0   -- older builds: bleed out
    end
end)
if not ok then
    deathlink_killed_ids[uid] = nil  -- kill failed, let a real death count
end
```

Two details worth copying. The marking happens first because you cannot assume
the hook fires later. And the mark is *rolled back* if the kill failed, so a
dwarf who dies for real later still counts.

`dfhack.units.kill` does not exist on every build, hence the fallback. The old
`modtools/kill-unit` script is gone from modern DFHack.

### Picking victims

Collect living citizens, shuffle, then take from the front:

```lua
for i = #candidates, 2, -1 do
    local j = math.random(i)
    candidates[i], candidates[j] = candidates[j], candidates[i]
end
```

A plain Fisher-Yates. Without the shuffle you kill in unit-list order, which is
roughly arrival order, so the same unlucky dwarves die every time.

### Energy Link: a shared pool

Energy Link is a number several games add to and draw from. The DF side never
talks to the network; it writes intent to persistent storage and an external
client does the rest.

Deposit, in the mod:

```lua
local prev = tonumber(dfhack.persistent.getWorldDataString("yourmod/energy_deposit") or "0") or 0
dfhack.persistent.saveWorldDataString("yourmod/energy_deposit", tostring(prev + joules))
dfhack.persistent.saveWorldDataString("yourmod/use_energy_link", "Y")
```

The client polls, sees the flag, forwards the amount, then clears both keys. The
flag exists so the client can tell "nothing deposited" from "deposited zero".

Spending is a request, not an action, because only the client knows the pool
balance. The mod writes `request_caravan` and a cost; the client checks the pool,
deducts if affordable, and writes back an approval the mod acts on. The mod never
assumes it succeeded.

### Accumulate in the mod, clear from the client

The deposit key **adds to itself** rather than overwriting. Two deposits between
polls must not lose one, and the poll interval is long enough for that to happen.
Whoever consumes the value clears it, so the sequence is accumulate, read, zero,
and nothing falls through the gap.

The same shape works for any "tell the outside world something happened" queue.
For events that can repeat quickly, use a JSON array rather than a counter, so
two events in one interval cannot clobber each other:

```lua
local queue = json.decode(dfhack.persistent.getWorldDataString("yourmod/buy_queue") or "[]")
table.insert(queue, slot)
dfhack.persistent.saveWorldDataString("yourmod/buy_queue", json.encode(queue))
```

### Outside changes arrive as a count, not an event

The client cannot call into your Lua, so it increments a pending counter and your
poll drains it:

```lua
local pending = state.get_pending_recv()
if pending <= 0 then return end
state.clear_pending_recv()
-- apply `pending` deaths
```

Clear before applying. If applying throws halfway, you would otherwise reapply
the whole batch on the next poll, which for DeathLink means killing twice.

---

## 19. Spawning a siege that actually works

Creating a hostile unit is easy. Creating one that walks to the fortress, fights
the dwarves, and does not attack its own side takes three separate fixes, none of
which are obvious and all of which fail quietly.

### Creating the unit

```lua
local unit = dfhack.units.create(race_idx, 0)   -- caste 0
```

`dfhack.units.create` builds the body, soul and mind and adds the unit to
`world.units.all`, **but not to `world.units.active`, and with no map position**.
A unit in that state exists and does nothing at all. You have to finish the job:

```lua
if not dfhack.units.teleport(unit, {x=x, y=y, z=z}) then
    unit.pos.x, unit.pos.y, unit.pos.z = x, y, z   -- fallback
end
df.global.world.units.active:insert('#', unit)
```

`teleport` also sets tile occupancy, which the direct assignment does not, so
prefer it and treat the manual write as a fallback.

Resolve the race index from the creature token, and accept a list so a token
missing from this world's raws does not kill the spawn:

```lua
local function resolve_race(tokens)
    for _, tok in ipairs(tokens) do
        for i, cr in ipairs(df.global.world.raws.creatures.all) do
            if cr.creature_id == tok then return i, tok end
        end
    end
end
```

Note `modtools/create-unit` is not a reliable route on modern DFHack. On 53.x it
errors with `Cannot read field world.arena_spawn`. The direct API above works.

### Making it hostile

A freshly created unit is neutral wildlife. It stands there.

```lua
unit.flags1.active_invader = true   -- treated as a hostile that seeks targets
unit.flags1.marauder       = true   -- roams and attacks rather than fleeing
pcall(function() unit.animal.population.region_x = -1 end)  -- detach from wild pop
```

Both flags matter. `active_invader` alone gets you something the fort recognises
as an enemy but which may not come looking for anyone.

### Spawning at the edge so they path in

The interesting part. You do not want them appearing inside the fort, and you do
want them to walk in like a real siege. Pick a random tile in a band along one of
the four map edges, find the surface z of that column, and then apply the check
that makes the whole thing work:

```lua
local fg = fort_walk_group()          -- the fortress's walkable group
for _ = 1, 150 do
    local x, y = edge_gens[math.random(4)]()
    local z = column_surface_z(x, y, z_hi, z_lo)
    if z and dfhack.maps.getWalkableGroup({x=x, y=y, z=z}) == fg then
        return x, y, z                -- can actually reach the fort
    end
end
```

**`dfhack.maps.getWalkableGroup` is the key.** DF partitions the map into regions
that are mutually reachable on foot. If the spawn tile is in a different group
from the fortress, the attackers are stranded on a plateau or across a chasm and
will mill about forever. Comparing groups gives you the same guarantee a natural
siege has.

Keep a margin of a few tiles off the true edge to avoid bounds problems, and scan
the full z range rather than a window near the depot, or a steep embark will have
its edges missed entirely.

Have a fallback that drops the group check after N attempts. A wave landing
outdoors but fenced off is still better than no wave, and it will never be inside
the fort.

### Why the whole wave needs one civ id

This is the subtle one, and it is what the question at the top of this section is
really about.

```lua
-- A civ_id of -1 (wild) makes a unit hostile to EVERYONE, its own siege
-- included, so beasts, wall-breakers and champions would infight.
local civ_id = find_civ_id("GOBLIN") or any_enemy_civ_id()
```

`civ_id = -1` means wild, and wild means hostile to all. Spawn a goblin warband
plus a couple of semi-megabeast champions as wild units and they will attack each
other, usually before they reach your walls. The siege destroys itself and the
player sees a confusing brawl in a field.

The fix is to give **every unit in the wave the same civ id**, including the
beasts. Borrow an existing enemy civ as a banner: find the goblin civ, or fall
back to any civ hostile to the fort. They then read as one army, fight the fort
rather than each other, and your semi-megabeasts function as champions attached
to the warband instead of a third faction.

This also means a creature that is normally solitary wildlife can be recruited
into an organised siege without touching its raws.

### Arming them

Newly created units spawn empty-handed. Equip through the inventory API, and note
both constraints from section 11: you need an explicit body part id, and the
creating call needs `no_floor = false`.

```lua
local grasps = find_body_parts(unit, "GRASP")   -- usually two

equip_item(unit, df.item_type.WEAPON, weapon_subtype, mat,
           df.inv_item_role_type.Weapon, grasps[1])

if give_shield and grasps[2] then
    equip_item(unit, df.item_type.SHIELD, shield_subtype, mat,
               df.inv_item_role_type.Weapon, grasps[2])
end

for _, piece in ipairs(armor_pieces(armor_kind)) do
    equip_item(unit, piece.item_type, piece.subtype, mat,
               df.inv_item_role_type.Worn, find_body_part(unit, piece.body_flag))
end
```

Weapon and shield both use `inv_item_role_type.Weapon` and differ only by which
grasp they occupy. Armour uses `Worn` and needs the body part that matches the
piece.

Resolve every itemdef subtype by token with a fallback, because a world may not
have the weapon you asked for:

```lua
local sub = itemdef_subtype(W.weapons, "ITEM_WEAPON_PIKE")
if not sub then sub = itemdef_subtype(W.weapons, "ITEM_WEAPON_SWORD_SHORT") end
```

Clear `item.flags.forbid` on anything you create, or the loot the attackers drop
is unusable without the player manually unforbidding it.

### Making them competent

Equipment without skill produces a mob that flails. Raise the relevant skill on
the unit's soul:

```lua
local function set_skill(unit, skill_id, level)
    local soul = unit.status and unit.status.current_soul
    if not soul then return end
    for _, sk in ipairs(soul.skills) do
        if sk.id == skill_id then
            if sk.rating < level then sk.rating = level end
            return
        end
    end
    soul.skills:insert('#', {new = true, id = skill_id, rating = level})
end
```

Match the skill to the weapon you actually gave them. Scaling skill with wave
number is a cleaner difficulty curve than scaling unit count alone, which just
costs FPS.

### Scale to the fort, not to the clock

Waves that ignore what the player has built are either trivial or unfair. Read
the fort's actual defences (trap count, standing army size) and use that as a
multiplier alongside the wave tier. A player who turtles behind traps and one who
fields a militia both get a fight.

---

## 20. Telling the player something

DFHack has several announcement calls and they are not interchangeable. Picking
the wrong one is how a message gets ignored or, worse, interrupts play.

```lua
-- Coloured line in the announcement log. The default.
dfhack.gui.showAnnouncement("[AP] Something happened.", COLOR_GREEN, true)

-- Same, but clickable: selecting the log line zooms the view to pos.
dfhack.gui.showZoomAnnouncement(df.announcement_type.CARAVAN_ARRIVAL, pos,
                                "[AP] Goods arrived.", COLOR_GREEN, true)

-- Modal box that stops the screen. Use sparingly.
dfhack.gui.showPopupAnnouncement("[AP] This world cannot work.", COLOR_RED, true)
```

The third argument to the first two is `recenter`. The `announcement_type` picks
which log category and sound DF treats it as, so borrow one that matches the
tone; `CARAVAN_ARRIVAL` reads as neutral good news.

Rules of thumb that held up in practice:

- **Routine events**: `showAnnouncement`. Cheap and ignorable.
- **Something the player will want to look at**: `showZoomAnnouncement` with a
  position. A clickable line beats describing where a thing is.
- **Something that invalidates the session**: `showPopupAnnouncement`. A banner
  scrolls away unseen; a modal does not. Reserve it for "this cannot work", not
  for "you got an item".

Wrap zoom announcements with a plain fallback, since a bad position or a missing
announcement type will throw:

```lua
local ok = pcall(function()
    dfhack.gui.showZoomAnnouncement(atype, pos, msg, COLOR_GREEN, true)
end)
if not ok then dfhack.gui.showAnnouncement(msg, COLOR_GREEN, true) end
```

Prefix everything with a short tag like `[AP]`. Players run many mods, and an
unattributed message in the log is impossible to report a bug about.

---

## 21. Taking control away from the player

Gating what the player may build, dig or craft is a common mod goal and a good way
to crash DF if you do it at the wrong moment.

### Cancel the job, do not fight the UI

Let the player queue the action, then remove it:

```lua
local function on_job_initiated(job)
    if job.job_type ~= df.job_type.ConstructBuilding then return end
    local bld = dfhack.job.getHolder(job)
    if not bld or is_allowed(bld) then return end

    dfhack.gui.showAnnouncement("[AP] Cannot build that yet.", COLOR_YELLOW, true)

    -- Defer by one tick. Removing a job inline during onJobInitiated CRASHES DF,
    -- because the engine is mid-update over the job list.
    dfhack.timeout(1, "ticks", function()
        pcall(function() dfhack.buildings.deconstruct(bld) end)
    end)
end
```

**The deferral is not optional.** Mutating the job or building list from inside
the event that is iterating it is a hard crash, not a Lua error. `dfhack.timeout`
with one tick puts the work on the next update, where it is safe.

This is a general rule for event handlers: announce immediately so feedback feels
instant, defer anything structural.

### Identify what is being built

The building is on the job, and the type depends on the class:

```lua
if df.building_workshopst:is_instance(bld) then
    name = WORKSHOP_BLUEPRINTS[bld.type]
    if not name and bld.type == df.workshop_type.Custom then
        -- Custom workshops share one type; the real identity is the raw code.
        local def = df.global.world.raws.buildings.all[bld.custom_type]
        if def then name = CUSTOM_WORKSHOP_BLUEPRINTS[def.code] end
    end
elseif df.building_furnacest:is_instance(bld) then
    name = FURNACE_BLUEPRINTS[bld.type]
elseif df.building_farmplotst:is_instance(bld) then
    name = "Farm Plot"
end
if not name then return end   -- not gated, allow it
```

Custom workshops are the trap: every modded workshop is `workshop_type.Custom`,
so `bld.type` cannot distinguish them. Go through `custom_type` into the building
raws and match on `def.code`.

### Blocking a designation rather than a job

Digging is a designation, so clear the designation as well as the job, or the
dwarf simply re-takes it:

```lua
local blk = dfhack.maps.getTileBlock(job.pos.x, job.pos.y, job.pos.z)
if blk then
    blk.designation[job.pos.x % 16][job.pos.y % 16].dig = df.tile_dig_designation.No
end
dfhack.timeout(1, "ticks", function() pcall(function() dfhack.job.removeJob(job) end) end)
```

Note the `% 16`: block designations are indexed by position **within the 16x16
block**, not by world coordinate. Getting this wrong silently edits a different
tile, which is maddening to debug because everything looks correct.

Also remember a channel designation opens the level *below* its tile, so a depth
limit has to block it one z higher than an ordinary dig.

---

## 22. Carving terrain and making citizens

Two more things that look harder than they are, with one sharp edge each.

### Writing tiles

```lua
local function set_tile(x, y, z, tt)
    local b = dfhack.maps.getTileBlock(x, y, z)
    if not b then return end
    local lx, ly = x % 16, y % 16
    b.tiletype[lx][ly] = tt
    b.designation[lx][ly].feature_local  = false
    b.designation[lx][ly].feature_global = false
    dfhack.maps.enableBlockUpdates(b, false, false)
end
```

Again the `% 16` block-local indexing. Clearing the feature flags matters when you
carve near a cavern or the magma sea: leave them set and DF treats your new floor
as part of that feature, which can trigger breach events you did not intend.

Do not hardcode tiletype ids. Names differ between builds, so find one by its
attributes:

```lua
for i = df.tiletype._first_item, df.tiletype._last_item do
    local a = df.tiletype.attrs[i]
    if a and a.shape == df.tiletype_shape.FLOOR
         and a.material == df.tiletype_material.STONE then
        return i
    end
end
```

### The stale passability cache

This one cost a real bug. Writing tiletypes directly does **not** update DF's
pathfinding cache, so dwarves keep treating your newly carved floor as solid.
Nothing errors; they just refuse to walk there, and it looks like a pathing bug in
the game rather than in your mod.

```lua
df.global.world.reindex_pathfinding = true
```

Set it once after a carving pass, not per tile. Any script that edits tiles needs
this, which is why DFHack's own tile-editing scripts do the same.

### Creating a citizen

Same three steps as any unit (section 19), plus enlistment:

```lua
local unit = dfhack.units.create(race_idx, caste)
unit.birth_year = df.global.cur_year - math.random(20, 40)   -- else you spawn a baby
dfhack.units.teleport(unit, pos)
df.global.world.units.active:insert('#', unit)

dfhack.units.makeown(unit)    -- the actual enlistment
```

`dfhack.units.makeown` is the whole trick. On DF 53.x it fully integrates the
unit as a fortress member: civ, nobility eligibility, the units list, everything.
Getting there via `modtools/create-unit` fails on this build.

Two things `makeown` does not do, which you probably want:

```lua
enable_labors(unit)      -- otherwise they stand around doing nothing
set_name(unit, ...)      -- otherwise they are an unnamed generic dwarf
```

And set `birth_year` before enlisting, or you get a baby that cannot work and
needs care.

---

## 23. Performance

Your mod runs inside DF's main loop. Time you spend is frames the player loses.

**Do not scan every item or unit every tick.** `world.items.all` in a mature fort
is thousands of entries. If you must scan, gate it behind a flag so it stops once
its job is done:

```lua
if checks.production_flag("already_found_it") then return end
```

**Cache per-frame results.** If several checks need the same scan, do it once:

```lua
local _cache, _cache_frame = nil, -1
local function expensive()
    local frame = df.global.world.frame_counter
    if _cache and _cache_frame == frame then return _cache end
    _cache, _cache_frame = compute(), frame
    return _cache
end
```

**Persistent reads are not free.** `getWorldDataString` costs roughly 0.05 ms.
That is nothing once, and a real cost 120 times per tick. Decode a structure once
and reuse it rather than re-reading and re-parsing in a loop.

**Back off when the fort is struggling:**

```lua
local fps = dfhack.internal.getUnpausedFps()
```

Careful with the arithmetic: poll intervals are usually measured in *ticks*, and
a slow fort already stretches each tick in real time. Multiplying the interval on
a fort at 10 FPS can mean minutes of real time between polls.

**Overlays render every frame**, unlike poll callbacks. Keep `onRenderBody` cheap
and scope widgets to the viewscreens that need them.

Measure rather than guess:

```lua
local c = dfhack.internal.getPerfCounters()
-- elapsed_ms, total_overlay_ms, update_lua_ms, update_event_manager_ms, ...
```

Counters only accumulate while **unpaused**, so a paused game reports zeros.
`dfhack.internal.resetPerfCounters()` lets you A/B a change.

---

## 24. Debugging

### The console eats double quotes

DFHack's command tokenizer strips double quotes before your script sees them, and
the `lua` command runs only its first token. So this fails confusingly:

```
lua print(dfhack.persistent.getWorldDataString("yourmod/key"))
```

Two reliable forms:

```
lua print(dfhack.persistent.getWorldDataString('yourmod/key'))
:lua print(dfhack.persistent.getWorldDataString("yourmod/key"))
```

Single quotes pass through untouched. The `:lua` prefix takes the whole rest of
the line raw. Either works; mixing double quotes with plain `lua` does not.

### Run commands remotely

`dfhack-run` executes against a running DF over the remote API, which is ideal
for scripted testing:

```
./hack/dfhack-run lua "print(dfhack.isMapLoaded())"
```

Note it bypasses the console tokenizer, so quoting behaves differently there than
in the in-game console. Verify player-facing instructions in the real console.

### Log so a crash tells you something

A hard DF crash produces **no Lua traceback**, because the process is simply gone. The
only evidence is what you wrote before it died. Two habits that pay for
themselves:

- **A session header** at startup recording mod version, DF and DFHack versions,
  OS, and which script paths are loaded. Most "it doesn't work" reports are
  answered by that block alone, especially duplicate installs, which are common
  and invisible otherwise.
- **Bracket risky operations.** Write a marker before and after bulk or
  memory-touching work. A log ending at the opening marker with no closing one
  tells you exactly where it died. Only worth it for rare heavy operations, not
  per-tick code.

Open, append and close per line rather than holding a handle, so every line is
flushed before a crash can eat it.

### `pcall` everything that touches DF internals

Field names change between DF versions. An unguarded access in a poll loop
aborts the whole pass, silently disabling every check after it:

```lua
local function guard(label, fn)
    local ok, err = pcall(fn)
    if not ok then
        dfhack.printerr("[yourmod] step '" .. label .. "' failed: " .. tostring(err))
    end
end
```

Also default your variables to the *safe* value, so a failed read cannot be
mistaken for a real one:

```lua
local is_trader = true      -- not false
pcall(function() is_trader = item.flags.trader end)
```

---

## Further reading

- [DF Wiki: Modding](https://dwarffortresswiki.org/index.php/Modding): token
  reference; authoritative on what tokens exist
- [DFHack Lua API](https://docs.dfhack.org/en/stable/docs/dev/Lua%20API.html):
  the API reference
- `hack/lua/` in your DFHack install: the actual source, and often faster than
  the docs for "what does this return"
- `hack/scripts/`: real working examples of nearly everything

This repo is itself an extended example: `mods/dwarfipelago/` for raws and Lua,
and `LUA_INTERFACE.md` for how a mod and an external client exchange state.
