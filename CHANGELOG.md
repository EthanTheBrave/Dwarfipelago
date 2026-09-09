# Changelog

## 2.0.1

Bugfix. 2.0.0 seeds and worlds remain playable — no regeneration required to
install this, though see the caveat below.

### Fixes

- **Shield, Mace and Tactics skill checks never fired.** All 45 locations (three
  skills x 15 tiers) were dead. The skill flag is maintained in two places —
  `df_item` in the apworld's `locations.py` and `skill` in the mod's
  `checks.lua` — and three of them disagreed by a letter (`shieldwarf` vs
  `shielddwarf`, `macedwarf` vs `macerdwarf`, `tatics` vs `tactics`). The client
  builds the DFHack storage key it polls from the seed, so it was watching an
  address the mod never wrote to: no error, just silence. All 87 flags are now
  verified identical on both sides, and both lists carry a comment explaining the
  coupling.

> **Mace** is fixed on existing seeds — the mod held the wrong spelling there.
> **Shield and Tactics** are not: their flag lives in the apworld and is baked
> into `slot_data` at generation, so those 30 locations stay dead on a seed rolled
> under 2.0.0. Regenerate to pick them up.

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
