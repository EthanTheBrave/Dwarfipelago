# Changelog

## 2.0.1

Bugfix release. 2.0.0 seeds and worlds remain playable and installing this requires
no regeneration — see **What carries over** for the two exceptions.

### Merchant's Shop

- **Goods you never bought were being marked as purchased.** Location checks fired
  for items left behind in the caravan's stock, permanently consuming those slots
  and releasing the items to their recipients for free. Two independent causes:
  - A good counted as sold the moment its item left the map — which is also
    exactly what happens when the caravan packs it up and takes it home. A sale
    now requires the item to still exist, to have its trader flag cleared, and to
    not be held by a merchant.
  - Cleanup of a departed caravan's goods ran on a docked-to-undocked transition
    held in memory, so a save/reload across the departure skipped it and stranded
    the bookkeeping. Those entries then sat untouched until the *next* caravan
    docked — a year later in one report — and were misread in a batch. Cleanup now
    runs on any idle tick, so nothing can be stranded.
- Unbought goods left in a caravan's stock return to the rotation properly and come
  back around on a later visit.
- Goods that a paused game failed to remove are retried, instead of being forgotten
  and left in the fortress permanently.
- **Shop goods were selectable as a crafting material, and leaked the whole shop.**
  The per-slot materials carried `[IS_STONE]` and inherited `STONE_TEMPLATE`'s
  `[ITEMS_HARD]`/`[ITEMS_QUERN]`, so every good turned up in stone and
  hard-material pickers — "Make rock blocks" listed them between Alabaster and
  Andesite. Those entries show each good's **real multiworld item name**, so the
  entire shop could be read without buying anything. The materials now carry no
  usage flags at all, so nothing in game can select them.

### The Archipelago caravan

- **Establishing contact with the gorlaks was a single silent attempt.** It ran only
  on Merchant's Coffer #1, marked itself successful *before* checking whether the
  civilization even existed, and reported failure to the DFHack console alone — so a
  world without the Archipelago civ produced no caravan, no shop, and no visible
  explanation for the rest of the run. Contact is now recorded only when it actually
  succeeds, retried on each later coffer until it does, and both failure modes (no
  civ / summon failed) announce themselves in game.
- **A world with no Archipelago civilization no longer quietly consumes your run.**
  With the shop enabled and no gorlak civ present — meaning the world was generated
  without the mod ticked in DF's world-gen mod list — the client refuses to bind the
  run's seed to that world and keeps saying why, while the mod raises a
  screen-stopping popup followed by repeating reminders. The world stays unbound, so
  the same multiworld seed is still usable once a correct world exists.
- `dwarfipelago test worldcheck` now verifies the gorlak civilization exists, and
  notes that they must additionally be a **neighbor of your embark** to send
  caravans at all.
- The setup guide gained a "Choosing an embark site" section, and an "If you got it
  wrong" table separating the two failure modes: a non-neighbor embark is fixed by
  **re-embarking elsewhere in the same world** (the seed is stored against the world,
  so the run carries over and received items are re-delivered), while a missing civ
  needs a new world. Neither was documented anywhere before.

### Logic and checks

- **Shield, Mace and Tactics skill checks never fired** — 45 locations dead, three
  skills at 15 tiers each. The skill flag is maintained in two places, `df_item` in
  the apworld's `locations.py` and `skill` in the mod's `checks.lua`, and three of
  them disagreed by a letter (`shieldwarf`/`shielddwarf`, `macedwarf`/`macerdwarf`,
  `tatics`/`tactics`). The client derives the storage key it polls from the seed, so
  it was watching an address the mod never wrote to: no error, just silence. All 87
  flags are now verified identical on both sides, and each list carries a comment
  explaining the coupling.
- **The Checks tab showed Mined Adamantine as reachable with no mining depth.** The
  in-game tracker builds its options from `slot_data`, and its mapping table never
  listed `mining_depth`; unmapped options read as 0, so the adamantine rule took its
  "no depth system" branch and returned true outright. `trades_inlogic` had the same
  hole and was missing from `slot_data` entirely. Both are carried through now, and
  the table documents why anything a rule branches on has to be listed.

### Traps

- **The Lost Caravan trap no longer blanket-mutates every trade good.** It set
  `flags.rotten` on *all* trader items — 400+ bars, stones and cages in one
  report — on the untested assumption that this was "inert on non-organic goods",
  and set wear on items that cannot be worn. Rot is now limited to genuinely
  perishable item types and wear to wearable ones, and caged livestock is killed
  the way DFHack's own `destroyUnit` does it, since draining blood alone does not
  reliably finish a unit.

### Install

- **The mod was searched for in the wrong folder.** The DF data root was taken as
  `dirname(game_path)`, but `game_path` may legitimately point at `dfhack.exe` —
  and the standalone DFHack Steam app lives in `.../common/DFHack/hack/`, nowhere
  near DF. The client now locates the real DF base folder by looking for DF's own
  markers, then by checking the sibling install in the same Steam library.

### What carries over

| | |
|---|---|
| **Applies to existing seeds immediately** | Every Merchant's Shop fix, the Checks tab fix, caravan contact, the missing-civ failsafe, and the Mace skill checks — all client- and mod-side. |
| **Needs a regenerated seed** | Shield and Tactics. Their flag lives in the apworld and is baked into `slot_data` at generation, so those 30 locations stay dead on a seed rolled under 2.0.0. |
| **Needs a regenerated world** | The shop-material fix. Raws are written into a save at world generation, so an existing world keeps the selectable, name-leaking materials. |
| **Cannot be recovered** | Shop slots already consumed by a false purchase. Those checks are server-side truth once sent. |

## 2.0.0

136 commits since 1.3.2. The headline is that the Merchant's Shop stopped being a
custom window bolted onto a shrine and became a real Dwarf Fortress caravan you
trade with on DF's own trade screen.

### Breaking

- **Seeds must be regenerated.** Locations, items, options and reachability logic
  all changed, so 1.3.x seeds are not playable on 2.0. `2.0.0` starts a new
  compatibility line; the client refuses mismatched seeds rather than letting
  them fail halfway in.
- **Worlds must be regenerated.** The mod ships new raws (the `ARCHIPELAGO`
  civilization and 50 shop materials) that only enter a save at world-gen. The
  mod jumps to `NUMERIC_VERSION:15` with `EARLIEST_COMPATIBLE` raised to match,
  so DF flags older saves instead of loading them into a world that has none of it.

### The Merchant's Shop is now a real caravan

- The shop is carried by a **native caravan from the `ARCHIPELAGO` civilization**,
  a gorlak trading people generated into your world. Receiving your first
  Merchant's Coffer establishes contact and brings them to your trade depot;
  after that they visit like any trade partner.
- **You trade on DF's own trade screen.** No overlay, no custom window, no
  keybind. Goods appear grouped under `AP Items (Tier N)`, and trading for one
  sends its multiworld location check.
- **You pay with anything.** The old design wanted minted coins; the caravan
  takes whatever a caravan takes, at the item's value.
- The gorlaks **trade their own wares too**, with the AP goods sprinkled among
  them — a rotating handful per visit rather than the whole unlocked shop. The
  rotation is drawn without replacement, so every unlocked slot comes up within
  about three visits and none can be starved out.
- Each good's **name and price are written into its material while your fortress
  runs**, so any world generated with the mod enabled shows the right names and
  prices regardless of when you connected the client.
- **Dwarfipelagius**, the merchant god, joins your civilization's worshippable
  deities.

### New checks and content

- **Fortress life** (6): legendary dwarf, tavern, library, harnessed power,
  completed trade, tamed beast.
- **Production firsts**: steel bar, glass, soap, instrument, coins, roast,
  patient treated, birth — each gated on the job or reaction that actually makes
  it, so embark stock no longer fires them.
- **Combat, strange moods and artifacts**, plus enemy-kill counts for the Slay
  Megabeast goal.
- **Silk** as a first-class material: silk-from-thread, material-typed craft
  counting, its own permit and overlay.
- Room checks renamed to `* Established`, beast kills to `* Slain`.
- `Survived a Siege` replaced by `First Siege`, which fires when a siege begins.

### Megabeast goal

- Later wave tiers (7-9) and defense scaling ramped up.
- Sieges gain elite marksmen, steel bolts, deeper ammo, building-destroyer
  wall-breakers at readiness 7+, and semi-megabeast champions at 8+.
- Warbands share a civ so they stop infighting; elves get wood armor at armored
  tiers.
- Warband warnings use a screen-stopping popup.

### Panel

- A **Checks tab**: all milestone checks grouped by category, done/open, as an
  in-fort tracker.
- A **Goal tab** with live goal progress.
- **AP-logic reachability** on the Checks and Craftsanity tabs — locked vs open,
  evaluated against the real `rules.py`.

### Items and traps

- **Stress Blockers**: resets the unhappiest dwarf,
  children included, and clears mental-break moods.
- **Miracle Cure**: fully heals a random injured dwarf.
- Traps merged into a single weighted list, all gated by `trap_item_weight`, with
  **per-trap enable options**.
- **Lost Caravan** implemented: the cursed caravan's cargo arrives rotten, and it
  takes caged trade animals with it while sparing wagon-pullers and your own.
- Ensnaring Webs now catches half the fort rather than every citizen.

### Options

- Per-trap toggles; DeathLink split into separate send and receive amounts.
- `exclude_deep_endgame_checks: yes_and_sanity` also keeps adamantine out of
  craft and skill checks.
- All FPS helpers folded behind a single **Performance Assist** option
  (FPS-adaptive poll backoff, spatter cleaning, fast-heat, cleanowned,
  deteriorate, opt-in Timestream).

### Install and client

- The client **installs the preset and mod and launches DF for you** on connect,
  so world-gen always reads current files.
- DF data locations are detected across Windows, macOS and Linux, covering both
  the Steam user-data directory and the install directory, and the mod installs
  to every root DF might read.
- `/dfuninstall` removes the installed-mod folders and strips the world-gen
  preset, leaving your mod source and saves alone.
- One aggregated status RPC per poll instead of about eleven reads.
- Energy Link accepts raw food (meat, fish, cheese, eggs, plants) as well as
  prepared meals, and its call-caravan summons your **own** civilization's
  caravan — which is what it always did, but now the docs say so.

### Fixes

- Trade depots no longer spawn in mid-air. (again..........)
- Cave floors are repathed after carving so dwarves can walk on them.
- `Sold an Artifact` handles caravan-carried and contained items; `Caged a
  Hostile Beast` no longer relies on the removed `isEnemy`.
- Only fort-crafted items count toward "first made" milestones.
- Livestock deaths no longer count toward DeathLink.
- Migrants honor restricted work details and arrive with labors enabled and a
  small random skill set.
- Location and zone checks stopped scanning every building each poll, which was
  causing input hitches that scaled with temples and guildhalls.
