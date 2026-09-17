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
8. [DFHack: persistent state](#8-dfhack-persistent-state)
9. [DFHack: reading raws at runtime](#9-dfhack-reading-raws-at-runtime)
10. [DFHack: creating items](#10-dfhack-creating-items)
11. [DFHack: creating buildings and reading zones](#11-dfhack-creating-buildings-and-reading-zones)
12. [DFHack: inventing a god](#12-dfhack-inventing-a-god)
13. [DFHack: reacting to events](#13-dfhack-reacting-to-events)
14. [DFHack: overlays on DF's own screens](#14-dfhack-overlays-on-dfs-own-screens)
15. [DFHack: building a panel](#15-dfhack-building-a-panel)
16. [Performance](#16-performance)
17. [Debugging](#17-debugging)

---

## 1. The three rules that explain most confusion

### Raws enter a save at world generation, and never again

This is the single most important thing to understand, and the wiki does not put
it anywhere near prominently enough.

When you generate a world, DF copies the enabled mods' raws **into the save**.
From then on, that save reads its own copy. Editing `mods/yourmod/objects/*.txt`
afterwards changes nothing for existing saves — not on reload, not on a DFHack
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
installs to `steamapps/common/DFHack/hack/` — a completely different tree. Look
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
  makes DF refuse older saves — correct when your raws changed in a way that
  breaks them, unkind otherwise.

**`scripts_modinstalled/` is added to DFHack's script path automatically** when
the mod is enabled. A script at `scripts_modinstalled/yourmod.lua` is runnable as
`yourmod` in the DFHack console. Subfolders work as paths:
`internal/yourmod/state.lua` is `reqscript("internal/yourmod/state")`.

### Raws are single-byte text. Keep them ASCII

DF reads raws as single-byte text, not UTF-8. A curly apostrophe or an em dash in
a `[NAME:...]` token renders as garbage.

This bites hardest when generating raws programmatically. Writing with strict
`latin-1` will *raise* on the first non-encodable character — and if you opened
the file first, you have already truncated it to zero bytes. Transliterate to
ASCII before writing, and use a replacing error handler as a backstop.

Comments in Lua are fine (the lexer discards them), but anything that reaches
DF — announcement text, item names, material names — should be ASCII.

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

- **`[NAME:singular:plural]`** — both are required.
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
material pickers** — "Make rock blocks" will list it between Alabaster and
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

This is in-memory only — DF reloads raws from the save on every load — so re-apply
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
Do not try to change `unit.race` on the merchants at runtime — DF re-derives it
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

- **`prefs/world_gen.txt` may live in either data root** (see §1). If a player
  has both, install to both.
- **Appending is safe.** Multiple `[WORLD_GEN]` blocks coexist; players pick by
  title. Do not rewrite the file.
- **DF reads it at startup.** Restart DF before the preset appears.
- **`REGION_COUNTS:<biome>:<count>:<min>:<max>`** — the last two are the minimum
  and maximum number of *regions* of that biome. Setting a minimum is how you
  guarantee a habitat exists for a civ that needs it.
- **`PLAYABLE_CIVILIZATION_REQUIRED:1`** rejects worlds with no playable civ,
  which saves rerolling by hand.

Presets constrain generation; they cannot guarantee any particular *embark* has
what you need. See the neighbour problem in §5.

---

## 8. DFHack: persistent state

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
  empty returns `""`. That distinction is genuinely useful — "never armed" versus
  "armed and then cleared" — but only if you are deliberate about it.

It is world data, not fort data, so it survives abandoning and re-embarking in
the same world. If you want something to persist across re-embark, this is how.

---

## 9. DFHack: reading raws at runtime

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
anything not in this world's raws — which is how you detect "world generated
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

## 10. DFHack: creating items

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
actually **equip** an item — a weapon in a hand, armour on a torso — pass both an
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

## 11. DFHack: creating buildings and reading zones

Constructing a real, finished building:

```lua
dfhack.buildings.constructBuilding{
    type   = df.building_type.TradeDepot,
    pos    = {x = tx, y = ty, z = z},
    width  = 5,
    height = 5,
}
```

This creates it complete — no job, no materials, no dwarves. The position is the
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

Use `df.global.world.buildings.other.ANY_ZONE`, not `buildings.all` — the latter
is every building in the fort and much more expensive to walk.

Room quality (the "Decent Quarters" / "Royal Bedroom" tiers) is a value DF
computes per zone. Read it rather than recomputing from furniture.

---

## 12. DFHack: inventing a god

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

## 13. DFHack: reacting to events

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
  items, poll `df.global.world.manager_orders` as well or you will miss
  everything made through the manager.

Prefer events to polling wherever the game will tell you. They are far cheaper
than scanning, and they keep working when your poll loop is throttled.

---

## 14. DFHack: overlays on DF's own screens

An overlay is a widget DFHack draws on top of a DF screen. This is how you add
information to vanilla UI you do not control — marking which workshop tasks are
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
  `<scriptname>.<key>` — here `yourmod-overlays.mywidget`, which is what
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
the single largest DFHack cost — several times the Lua update total — precisely
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

Scraping is fragile by nature — it breaks if DF changes its layout or the player
uses a different font width. Match loosely, guard with `pcall`, and degrade to
drawing nothing rather than drawing in the wrong place.

---

## 15. DFHack: building a panel

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
can mean different things on different tabs** without conflicting — only the
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

`label` and `enabled` accept functions, evaluated at render — so a button can
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

## 16. Performance

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

## 17. Debugging

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
in the in-game console — verify player-facing instructions in the real console.

### Log so a crash tells you something

A hard DF crash produces **no Lua traceback** — the process is simply gone. The
only evidence is what you wrote before it died. Two habits that pay for
themselves:

- **A session header** at startup recording mod version, DF and DFHack versions,
  OS, and which script paths are loaded. Most "it doesn't work" reports are
  answered by that block alone — especially duplicate installs, which are common
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

- [DF Wiki: Modding](https://dwarffortresswiki.org/index.php/Modding) — token
  reference; authoritative on what tokens exist
- [DFHack Lua API](https://docs.dfhack.org/en/stable/docs/dev/Lua%20API.html) —
  the API reference
- `hack/lua/` in your DFHack install — the actual source, and often faster than
  the docs for "what does this return"
- `hack/scripts/` — real working examples of nearly everything

This repo is itself an extended example: `mods/dwarfipelago/` for raws and Lua,
and `LUA_INTERFACE.md` for how a mod and an external client exchange state.
