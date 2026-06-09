# Dwarfipelago

A [Dwarf Fortress](https://www.bay12games.com/dwarves/) integration for the [Archipelago](https://archipelago.gg/) multiworld randomizer.

Complete economic and production milestones in your fortress to send items to other Archipelago players. Receive trade goods, resources, and (beware) traps from other games.

## Requirements

- Dwarf Fortress (Steam 2022+ or Classic)
- [DFHack](https://github.com/DFHack/dfhack) - Can also be downloaded through [Steam](https://store.steampowered.com/app/2346660/DFHack__Dwarf_Fortress_Modding_Engine/)
- [Archipelago](https://archipelago.gg/) 0.6.7

## Components

| Component | Path | Description |
|-----------|------|-------------|
| AP World | `worlds/dwarf_fortress/` | Archipelago world definition - install into your AP `worlds/` folder or package as `.apworld` |
| DFHack Mod | `mods/dwarfipelago/` | DFHack mod - copy into your DF installation's `mods/` folder |
| AP Client | `worlds/dwarf_fortress/DwarfFortressClient.py` | Bundled inside the AP world package - launched automatically by the AP launcher |

## Setup

See [`worlds/dwarf_fortress/docs/setup_en.md`](worlds/dwarf_fortress/docs/setup_en.md) for full installation and configuration instructions.

---

<details>
<summary>World Generation</summary>

Dwarfipelago is balanced for a **Small world** (65×65 region tiles). A recommended world gen preset is included in the repo.

### Setup

1. Copy `prefs/world_gen.txt` from this repo into your Dwarf Fortress `prefs/` folder (create the folder if it doesn't exist)
2. When creating a new world in DF, open the world gen menu and select **"DwarfipelagoWorld"** from the saved presets list
3. Generate and embark as normal

### What the preset does

| Setting | Value | Reason |
|---------|-------|--------|
| World size | Small (65×65) | Balanced play duration; faster gen than Medium/Large |
| Numbered civs | 20 | Ensures human and elf civilizations are present for caravan checks |
| Forest regions (min) | 2 | Guarantees elf habitat exists |
| Grassland regions (min) | 2 | Guarantees human habitat exists |
| Everything else | DF defaults | No other settings are changed |

### If you use a different preset

The mod will still work, but when you run `dwarfipelago start` it will warn you in-game (yellow announcement) if no human or elf civilization was found in the world. Human and elf caravan visit checks will be impossible to complete in that world.

</details>

---

<details>
<summary>Trade Depot</summary>

When you load a fortress with Dwarfipelago active, the mod automatically places a **Trade Depot** near your starting wagon. This depot serves as the central hub for Archipelago:

- **AP items you receive** (gems, bars, resources, traps) are spawned directly at the depot
- **Location checks** and **item delivery** are both held until the depot is established - nothing is sent to or received from the AP server before it exists

### What to expect on first load

1. Within a few in-game ticks of loading your fortress, you will see the announcement:
   > *[AP] A Trading Post has been established near your starting wagon!*
2. The depot is placed **7 tiles west** of your starting wagon and instantly completed - no dwarves or materials required
3. If that spot is blocked, the mod tries the other three cardinal directions automatically
4. If the player has already built a Trade Depot before the mod runs, the existing depot is adopted as the delivery point and no second one is placed

### If the depot is not appearing

- Make sure the mod is enabled in DF's mod manager and the installed_mods snapshot is up to date (see setup step 2)
- You can build a Trade Depot manually in any location - the mod will detect and adopt it on the next poll tick
- To force a retry, run in the DFHack console:
  ```
  lua dfhack.persistent.saveWorldDataString("dwarfipelago/depot_built", "0")
  ```
  Then save and reload your fortress

</details>

---

<details>
<summary>Win Conditions</summary>

Configurable per-slot in your options YAML. Every goal also requires a minimum number of **Immigration Waves** (see Progression below).

| Goal | Description | Waves required |
|------|-------------|---------------|
| `population_boom` | Grow your fortress to a configurable population (default: 300 dwarves) *(default)* | 5 |
| `legendary_wealth` | Accumulate a configurable treasury value in **minted coins and cut gems** (default: 100,000☼) | 3 |
| `slay_megabeast` | Kill a dragon, titan, or other megabeast | 2 |
| `mountainhome` | Achieve Mountainhome status - the monarch takes residence in your fortress (very difficult) | 5 |
| `kings_remains` | Treasure hunters, Kobolds and Goblins has plundered our great halls and took the remains of our great king. They have traded them outside of our realm and we need our friends to help find them. We need to find all X remains to bring our great king back into our halls. | 0 |

</details>

---

<details>
<summary>Locations (Checks)</summary>

Completing these milestones sends items to other players:

- **Treasury milestones** - Humble Beginnings (1,000☼) through Legendary Vault (500,000☼) — based on the combined value of **minted coins and cut gems** in fortress stocks, not total fortress wealth
- **First production** - first weapon forged, armor crafted, meal prepared, brew completed, metal bar smelted, gem cut, and more (18 milestones)
- **Trade & diplomacy** - first caravan trade, first export, dwarven/elven/human caravan visits, outpost liaison meeting (an elven/human caravan-visit check auto-completes if that civilisation doesn't exist in your world, so it can't soft-lock the seed)
- **Fortress status** - noble appointments and civilisation recognition milestones
- **Fortress titles** - Hamlet, Village, Town, City, Metropolis (population + wealth thresholds)
- **Mining** - depth milestones (10/25/50/75/100 levels below the surface), tiles excavated (100 → 10,000), and breach events (First/Second/Third Cavern, Reached the Magma Sea)
- **Farming** - harvested-crop milestones (50 / 100 / 250 / 500 / 1,000 crops)
- **Craftsanity** - optional crafting milestone checks (see below)

</details>

---

<details>
<summary>Craftsanity</summary>

Craftsanity adds location checks for producing crafted items in bulk. When enabled, crafting **N** of a given item (or item + material combination) sends a check to the AP server. The client polls DFHack's persistent craft counters and fires checks as thresholds are crossed.

### Enabling Craftsanity

Set `craftsanity` in your options YAML:

| Value | Behaviour |
|-------|-----------|
| `off` | No crafting checks (default) |
| `on` | Check fires when N items have been **crafted** |
| `storage` | Check fires when N items are **present in a stockpile** |

### Item Group

`craftsanity_item_group` selects which items generate checks. Choose a preset that matches your desired playtime, or pick `choose` and hand-pick items manually.

| Group | Items included | Good for |
|-------|---------------|----------|
| `easy` | 10 items - Beds, Blocks, Alcohol, Chair, Table, Door, Barrel, Bucket, Container, Cloth | Short sessions or casual runs |
| `medium` *(default)* | 25 items - Easy set plus Crafts, Cage, Leather, Mechanism, Prepared Meal, Bookcase, Cabinet, Floodgate, Animal Trap, Statue, Armor Stand, Pedestal, Weapon Rack, Corkscrew, Bin | Balanced early-game variety |
| `hard` | ~45 items - Medium set plus metalwork, glass, armour, weapons, food processing, and more | Extended runs with late-game crafting |
| `craftsanity` | All ~100 craftable items | Maximum locations; pairs well with materials enabled |
| `choose` | Manual - use the `craftsanity_items` list in your YAML | Full control over exactly which items are checks |

### Materials

`craftsanity_enable_materials: true` splits each item check into per-material variants - crafting **N Stone Blocks** and **N Metal Blocks** are separate checks. Use `craftsanity_materials` to restrict which material types are included (Stone, Wood, Metal, Glass, Leather, Cloth, Bone, Ceramic).

### Threshold and Amount

| Option | Description | Default |
|--------|-------------|---------|
| `craftsanity_max_amount` | Total items to produce per item (or item+material) for all checks combined | 15 |
| `craftsanity_threshold` | How many crafted items equals one check (e.g. `5` = a check every 5 produced) | 5 |

A `max_amount` of 15 with a `threshold` of 5 produces **3 checks** per item: at 5, 10, and a final check at 15.

### Example YAML

```yaml
craftsanity: on
craftsanity_item_group: medium       # easy | medium | hard | craftsanity | choose
craftsanity_enable_materials: false  # true to split checks by material type
craftsanity_max_amount: 15
craftsanity_threshold: 5
# Only used when craftsanity_item_group is 'choose':
# craftsanity_items:
#   - Beds
#   - Blocks
#   - Cloth
```

</details>

---

<details>
<summary>Items Received</summary>

| Type | Examples |
|------|---------|
| Workshop blueprints | 29 blueprints that unlock workshops, furnaces, and farm plots - **progression items** (see Progression section below) |
| Progression locks | Merchant's Coffer (x5), Immigration Wave (x5), Noble Ladder charters (x4), Military Training (x4) - gate milestone checks and goal completion |
| Prestige rewards | Artifact Weapon (adamantine battle axe), Artifact Armor (full adamantine set), Master Builder's Codex (genuine indestructible **artifact** adamantine door) |
| Trade goods | Cut gems, gold/silver/steel bars, masterwork crafts |
| Resources | Food bundles, wood bundles, iron ore, coal |
| Industry materials | Flux stone, pig iron, charcoal, cloth bolts, tanned leather, **bags of sand** (glassmaking), raw clay (kaolinite for porcelain), plus rare low-grade copper tools (pick/axe/sword) |
| Traps | Goblin ambush, cave bear incursion, vermin infestation, tantrum trigger, lost caravan |
| Crafting Items | Jobs listed in Craftsanity now requires a item that allows you to do those jobs. Can't make table without the Crafting Table Item. |

All received goods are delivered to the **trade depot**.

</details>

---

<details>
<summary>Progression</summary>

### Workshop Blueprints

Workshop blueprints are the core Archipelago mechanic. Other players find your blueprints at their locations and send them to you, unlocking the matching structure in your fortress. Until you receive a blueprint, attempting to build that structure will be cancelled with a notification.

**Gated workshops:** Craftsdwarf's, Forge, Magma Forge, Kitchen, Jeweler's, Clothier's, Tanner's, Mechanic's, Siege, Soap Maker's, Ashery, Bowyer's, Screw Press, Fishery, Loom, Dyer's, Butcher's, Farmer's

**Gated furnaces:** Smelter, Magma Smelter, Wood Furnace, Glass Furnace, Kiln, Magma Kiln, Magma Glass Furnace

**Gated buildings:** Farm Plot

**Granted at start by default:** Carpenter's Workshop, Mason's Workshop (Stoneworker's), Still, Leather Works — these blueprints are included in the default `start_inventory`, so you can build them immediately on a normal embark. They are still gated by the blueprint system: if you remove one from your `start_inventory`, that workshop becomes locked until you receive its blueprint from the multiworld.

### Progression Locks

Four systems of **progression lock items** gate milestone checks and goal completion. These items are found by your multiworld partners and sent to you; each one received unlocks the next tier of checks or advances your goal progress.

Progression locks are **filtered by your selected goal** — only the systems relevant to your goal are added to the multiworld pool, and lock-only locations that don't apply to your goal (e.g. the coffer-gated wealth tiers when you aren't playing Legendary Wealth) are omitted entirely.

#### Merchant's Coffer (x5) - Treasury Tiers

Five coffers gate the five treasury milestone checks. These thresholds measure the **combined value of minted coins and cut gems** held in your fortress stocks - not total fortress wealth. Your treasury may grow freely, but the AP check for each tier won't fire until the matching coffer arrives. If you reach a tier without the coffer, a yellow announcement will remind you to look for it.

| Coffers received | Wealth check unlocked |
|---|---|
| 1 | Humble Beginnings (1,000☼) |
| 2 | Growing Stronghold (10,000☼) |
| 3 | Prosperous Fortress (50,000☼) |
| 4 | Rich Citadel (100,000☼) |
| 5 | Legendary Vault (500,000☼) |

The **Legendary Wealth** goal also requires all 5 coffers and a treasury value at or above your configured `wealth_goal_amount` to complete.

#### Immigration Wave (x5) - Population Growth

Five waves gate the five fortress title checks (Hamlet through Metropolis) and scale up the population requirement for every goal's completion condition. Each Immigration Wave received also brings a small group of dwarves into your fortress as new citizens (arriving named and in basic clothing at the depot), so receiving them genuinely grows your population.

| Waves received | Title check unlocked | Also gates |
|---|---|---|
| 1 | Hamlet Established (pop 20) | - |
| 2 | Village Established (pop 50) | Slay Megabeast goal completion |
| 3 | Town Established (pop 80) | Legendary Wealth goal completion |
| 4 | City Established (pop 110) | - |
| 5 | Metropolis Established (pop 140) | Population Boom & Mountainhome goal completion |

#### Noble Ladder - Mountainhome

Four charter items gate the four upper noble appointment checks. The mayor is always accessible; higher ranks require the matching charter to have arrived from the multiworld.

| Item received | Check unlocked |
|---|---|
| Baron's Charter | Baron Appointed |
| Count's Charter | Count Appointed |
| Duke's Charter | Duke Appointed |
| Monarch's Invitation | Monarch Takes Residence |

The **Mountainhome** goal additionally requires the Monarch's Invitation before victory is recognised.

#### Military Training (x4) - Slay Megabeast

Four training items gate the megabeast slaying goal. The first three each **equip your fortress with escalating steel gear** (weapons, then armor, then full elite kit) to prepare your military. The **fourth** summons the target megabeast itself. Killing a megabeast before all four training items have arrived won't trigger victory - your military isn't considered ready yet, and the AP-summoned beast won't have appeared.

#### Remains of the Great King (RotGK) (x5 - x100) - Treasure Hunt
Throughout the Multiworld will contain this item. Collect all of them to reach your goal.


</details>

---

<details>
<summary>DeathLink</summary>

Dwarfipelago supports Archipelago's DeathLink system with a configurable threshold:

- Enable it with `deathlink: true` in your options YAML (off by default)
- Every **N dwarf deaths** (default: 5) in your fortress sends one DeathLink to all connected DeathLink players
- Receiving a DeathLink kills **N random dwarves** in your fortress
- Set `deathlink_threshold: 1` in your options for classic one-death-equals-one-death behaviour
- Set `deathlink_percentage: true` to treat the threshold as a **percentage of your current population** instead of a flat count

</details>

---

<details>
<summary>Troubleshooting</summary>

- **"Dwarf Fortress not found"** - set `game_path` in `host.yaml` (see Step 4 above)
- **Client can't connect to DFHack** - ensure DFHack is running and its remote API is active on `127.0.0.1:5000`
- **Mod doesn't start automatically** - load a fortress first and wait ~5 seconds; you can also run `dwarfipelago start` manually in the DFHack console
- **Items not arriving** - check the client log window; items are delivered via DFHack script calls when the client is connected

### Where to find errors

There are two separate error logs:

- **AP client window** - client, RPC, and network errors (with full tracebacks). This is the window opened by the **Dwarf Fortress Client** launcher button.
- **`<Dwarf Fortress>/dwarfipelago.log`** - in-game mod errors (item spawn failures, trade depot placement, etc.). The exact path is printed to the DFHack console when the mod starts; you can also print it with `lua print(reqscript("internal/dwarfipelago/log").path())`.

For full setup details see [`worlds/dwarf_fortress/docs/setup_en.md`](worlds/dwarf_fortress/docs/setup_en.md). For the Lua ↔ Python interface, see [`LUA_INTERFACE.md`](LUA_INTERFACE.md).

</details>

---

<details>
<summary>Project Board</summary>

A running list of ideas, planned features, and things that still need doing. No particular order - just a place to capture thoughts before they disappear.

### To Do

- [x] Implement DFHack protobuf wire encoding for `RunCommand` to deliver items in-game
- [x] Implement trap item spawning in `items.lua` (goblin ambush, cave bear, vermin, tantrum)
- [x] Add `fill_slot_data` population goal amount to client sync so Lua reads the correct target
- [x] Goal completion detection and AP victory signaling (`ClientStatus.CLIENT_GOAL`)
- [x] Fortress status checks - noble appointments and civilisation recognition milestones
- [x] Batch DeathLink - configurable threshold (N deaths out / N deaths in), feedback-loop prevention
- [x] Archipelago Launcher integration - Dwarf Fortress and Dwarf Fortress Client buttons; mod auto-starts when a world is loaded
- [x] Wire up caravan detection (merchant/diplomat unit scanning, exported-wealth tracking for trade/export flags)
- [x] Fortress title location checks - Hamlet / Village / Town / City / Metropolis (population + wealth thresholds)
- [x] Mountainhome win condition - achieve Mountainhome status (monarch takes residence)
- [x] Progression lock items - Merchant's Coffer, Immigration Wave, Noble Ladder, Military Training gate milestone checks and goal completion
- [~] Validate `df.job_type` enum values against a live DFHack console for all production checks
- [~] Validate `createitem` material strings against DF raws (gem types, metal bar identifiers)
- [x] Write end-to-end test instructions in `docs/`

### Ideas / Future Features

- [ ] **Skill milestone locations** - first Skilled / Expert / Master dwarf per skill category (originally cut for scope)
- [ ] **Combat milestone locations** - first kill, first siege survived, first forgotten beast
- [ ] **Artifact creation check** - a dwarf goes into a strange mood and produces an artifact
- [ ] **Custom AP items** - define unique DF-flavored items as raw reactions for cleaner in-game delivery
- [ ] **Overlay UI** - DFHack overlay panel showing current AP connection status and recent items
- [ ] **Multi-fortress support** - allow switching between saves without resetting AP state
- [ ] **DeathLink targeting** - option to target specific skill types when applying received DeathLink deaths
- [x] **Craftsanity item group presets** - Easy / Medium / Hard / Craftsanity / Choose dropdown replaces the raw item list for most players
- [ ] **Random Option for Crafting Check** - selects a specified number of random item checks to have included in AP gen
- [ ] **Rival Beast When MegaBeast is Victory** - finds a named beast during world gen and spawns them in when a specific check is sent

</details>

---
