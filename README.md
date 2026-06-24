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

1. Launch the **Dwarf Fortress Client** from the AP launcher and run `/dfinstall` once to add the preset to your `prefs/world_gen.txt`
2. When creating a new world in DF, open the world gen menu and select **"DwarfipelagoWorld"** from the saved presets list
3. Generate and embark as normal

### What the preset does

| Setting | Value | Reason |
|---------|-------|--------|
| World size | Small (65×65) | Balanced play duration; faster gen than Medium/Large |
| History length | 120 years | Short enough to keep human/elf civs alive; longer runs often leave only goblins |
| Civilizations | 20 | Ensures human, elf, dwarf, and goblin civs all exist |
| Playable civ required | Yes | Rejects worlds with no dwarf civ to embark with |
| Forest regions (min) | 2 regions | Guarantees elf habitat exists |
| Grassland regions (min) | 2 regions | Guarantees human habitat exists |
| Volcanoes (min) | 5 | Ensures magma access for deep AP checks |
| Megabeasts | 4 cap | Enough for the Slay Megabeast goal without overwhelming |
| Cavern layers | 3 full layers | Required for all cavern breach AP checks |
| Magma sea + HFS | Enabled | Required for Reached the Magma Sea and Welcome to the Circus checks |
| Mineral scarcity | 100 (standard) | Full mineral density — not scarce |

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
| `slay_megabeast` | Wage a war campaign - muster a military, weather roaming warbands, and slay the megabeast that falls upon your fortress | 2 |
| `mountainhome` | Achieve Mountainhome status - the monarch takes residence in your fortress (very difficult) | 5 |
| `king_remains` | Treasure hunters, Kobolds and Goblins has plundered our great halls and took the remains of our great king. They have traded them outside of our realm and we need our friends to help find them. We need to find all X remains (`remains_great_king`, default 10) to bring our great king back into our halls. | 0 |

</details>

---

<details>
<summary>The Slay Megabeast Goal - How It Works</summary>

The Slay Megabeast goal is a **war campaign**, not a single fight. This explains the *mechanics* so you can prepare - the exact encounters and the beast itself are left as surprises.

### War Readiness

Your progress is measured by a hidden **War Readiness** level (1-10). Readiness rises as you receive **Military Training** items from your multiworld partners - there are **ten** of them. Each one:

- **Raises your War Readiness**, and
- **Delivers a war shipment** to your trade depot - escalating gear that gets better with every tier (and occasionally a bonus). One of them also brings a **veteran champion dwarf** who joins your fortress as a ready-made squad leader.

### Your fortress has to earn it

Readiness isn't handed to you by items alone - past the early tiers it's **gated by actually building a military**:

- **A real barracks** - a squad with an **armor stand and a weapon rack** assigned to it. (Those are *metal* furniture, so build up a metals industry: smelt ore and set up a forge.)
- **Trained soldiers** - several dwarves drilled to a high weapon skill.

Until you meet these, your readiness is **capped** no matter how many training items you've banked. Reaching each milestone also completes a location check (**Barracks Established**, **Training Completed**), sending items to your partners.

### The war comes to you

Once the campaign begins, your fortress is **raided periodically** (you'll get a short warning before each attack). The strength of each raid **scales with your current War Readiness** - the further along your war effort, the more dangerous they become. Anything the attackers drop is yours to keep. Keep your military equipped and drilled; these raids are how the campaign builds toward the finale.

### Summoning the beast (the finale)

The megabeast is **never forced on you**. When you have gathered everything the goal requires - **all ten Military Training**, an **Artifact Weapon**, and enough population (**Immigration Waves**) - a **Summon the Megabeast** button unlocks in the panel's **War** tab. Press it **when your fortress is ready**; the beast arrives in dramatic fashion and marches on you. **Slay it to win.**

Killing some other megabeast before you summon the goal target won't count - only the summoned beast does.

### Quick tips

- Stand up a **metal industry early** - you need it for the barracks furniture and for replacing battle losses.
- Don't sit on Military Training items - **build the barracks and train soldiers** so your readiness keeps climbing.
- Watch the **War** tab in the `[AP]` panel: it tracks your training count, readiness, barracks/soldier status, and tells you when the beast can be summoned.
- Keep a **water source or moat** near your defenses - not every threat fights with steel, and some arrive wreathed in **fire**. Water both douses blazes and makes a deadly obstacle.

</details>

---

<details>
<summary>Locations (Checks)</summary>

Completing these milestones sends items to other players:

- **Treasury milestones** - Humble Beginnings (1,000☼) through Legendary Vault (500,000☼) — based on the combined value of **minted coins and cut gems** in fortress stocks, not total fortress wealth
- **First production** - first weapon forged, armor crafted, meal prepared, brew completed, metal bar smelted, gem cut, and more (18 milestones)
- **Trade & diplomacy** - dwarven/elven/human caravan visits, outpost liaison meeting, first raid, first artifact recovery, first act of diplomacy (an elven/human caravan-visit check auto-completes if that civilisation doesn't exist in your world, so it can't soft-lock the seed)
- **Fortress status** - noble appointments and civilisation recognition milestones
- **Fortress titles** - Hamlet, Village, Town, City, Metropolis (population + wealth thresholds)
- **Mining** - depth milestones (10/25/50/75/100 levels below the surface), tiles excavated (100 → 10,000), and breach events (First/Second/Third Cavern, Reached the Magma Sea, Welcome to the Circus)
- **Farming** - harvested-crop milestones (50 / 100 / 250 / 500 / 1,000 crops)
- **Infrastructure** - Built a Well, Pumped Water, Pumped Magma
- **Biology** - First Eggs Hatched, Caged a Hostile Beast
- **Deep / Endgame** - Mined Adamantine, Sold an Artifact
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
<summary>Crafting Permits</summary>

Crafting Permits turn item production itself into a progression gate: until you receive the permit for an item, any job that would make it is cancelled in-game with a one-time notice (the same enforcement style as workshop blueprints). Permits arrive from the multiworld as their own items.

This is an **opt-in** layer on top of Craftsanity — **Craftsanity must be enabled**, because permits add 97 additional items to the pool.

Set `craftpermits` in your options YAML:

| Value | Behaviour |
|-------|-----------|
| `off` | No permits required - craft anything you have the workshop for (default) |
| `on` | You **start with** permits for Beds, Charcoal, Leather, Cloth, Alcohol, and Prepared Meal; every other permitted item must be unlocked from the multiworld |
| `all` | Every permitted item is gated - you start with no permits |

Permit enforcement is goal-independent and stacks with the workshop blueprint gate: you need both the workshop's blueprint *and* the item's permit before a dwarf will complete the job.

### Example YAML

```yaml
craftsanity: on        # required - permits do nothing without craftsanity
craftpermits: on       # off | on | all
```

</details>

---

<details>
<summary>Energy Link</summary>

Energy Link connects your fortress to the multiworld's shared energy pool. You contribute surplus production into the pool, and spend energy to call a caravan early when you need to trade.

Enable it with `energy_link: true` in your options YAML (off by default).

### Depositing energy

From the **Energy** tab of the in-game panel (or the console commands below) you can convert fortress goods into shared energy:

| Resource | Rate |
|----------|------|
| Alcohol | 100 kJ per unit |
| Prepared food | 50 kJ per item |
| Minted coins | 1 kJ per ☼ of face value |

Deposited energy is sent to the shared pool and is available to every Energy Link player in the session.

### Calling a caravan early

Spend energy from the pool to **request a caravan** before its normal seasonal arrival. The mod calculates the energy cost, the client deducts it from the shared pool if you can afford it, and the caravan is then spawned and arrives - leaving again on its own schedule like any normal caravan. If the pool can't cover the cost, the request is declined.

### Console commands

```
# Deposit a specific coin value (☼) into the shared pool
dwarfipelago deposit-coins 500
```

Ale and food deposits, the current pool balance (shown in MJ and raw kJ), and the "call a caravan" action are all available from the panel's **Energy** tab.

</details>

---

<details>
<summary>Items Received</summary>

| Type | Examples |
|------|---------|
| Workshop blueprints | 29 blueprints that unlock workshops, furnaces, and farm plots - **progression items** (see Progression section below) |
| Progression locks | Merchant's Coffer (x5), Immigration Wave (x5), Noble Ladder charters (x4), Military Training (x10) - gate milestone checks and goal completion |
| Prestige rewards | Artifact Weapon (adamantine battle axe), Artifact Armor (full adamantine set), Master Builder's Codex (genuine indestructible **artifact** adamantine door) |
| Trade goods | Cut gems, gold/silver/steel bars, masterwork crafts |
| Resources | Food bundles, wood bundles, iron ore, coal |
| Industry materials | Flux stone, pig iron, charcoal, cloth bolts, tanned leather, **bags of sand** (glassmaking), raw clay (kaolinite for porcelain), plus rare low-grade copper tools (pick/axe/sword) |
| Traps | Goblin ambush, cave bear incursion, vermin infestation, tantrum trigger, lost caravan |
| Crafting Permits | When `craftpermits` is enabled, each permit item unlocks the ability to craft one item type (e.g. you can't make a table until the Table permit arrives). See the Crafting Permits section. |
| Remains of the Great King | Treasure-hunt goal item - collect all of them (`king_remains` goal) to win. |

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

#### Military Training (x10) - Slay Megabeast

The Slay Megabeast goal is a full war campaign. Ten **Military Training** items drive a **War Readiness** level (1-10) as you prepare your fortress for the beast.

**Each training item delivers an escalating war shipment** - weapons, then armor, then full kits, with bigger steel-bar shipments at higher tiers. **Tiers 7-10 arrive in adamantine** (a deliberate late-game power spike; blunt weapons stay steel). Every shipment also has a chance to include a bonus from a **war-materiel pool** (extra weapons, crossbows and bolts, trap components, war dogs, forge supplies, field medicine), and a one-time **veteran champion dwarf** joins your fortress as a ready-made squad leader - a rare chance with each training, guaranteed by the eighth.

**War Readiness is gated by your fortress, not just the items.** Readiness 1-4 flows freely; **5-6 requires a set-up barracks** (a squad with an armor stand and weapon rack); **7-9 requires four soldiers trained to combat skill 10+**. Building these fires two new location checks, **Barracks Established** and **Training Completed**.

**Roaming warbands attack on a campaign clock** - a random 2-4 in-game months apart (with a day's warning) once readiness begins. Their size, gear, veterancy, and composition scale with your readiness: from copper-armed kobolds and lone goblins early, to iron- and steel-clad mixed warbands led by named veterans with troll/ogre escorts at the high end. The loot they drop is yours to keep.

**The climax:** once you hold all ten training items plus an **Artifact Weapon** and at least **two Immigration Waves**, the war effort is complete - and the beast is **never forced on you**. A **Summon the Megabeast** button appears in the panel's **War** tab; press it when your fortress is ready. The target megabeast then **falls from the sky** onto your lands - gouging a smoking crater, or (if it's a fire-immune beast such as a dragon or bronze colossus) crashing down wreathed in flame. Slay it to win. Killing a stray megabeast before you summon the AP target won't trigger victory.

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
