# DEAD DRIFT — Next Push: Award-Quality Drive

> **Historical (May 2026):** Superseded by **[ALIVENESS_PUSH.md](ALIVENESS_PUSH.md)** for active work. Epics 9–14 items shipped or folded into Aliveness phases D–H.

**Session:** May 2026 planning committee  
**Status:** Complete — reference only  
**Other agents:** Read this before touching any system. See [Multi-agent coordination](#multi-agent-coordination) at the bottom.

---

## Vision Statement

Dead Drift is a satirical-corporate-dystopia roguelite courier sim where the black comedy is the gameplay. The player is a debt-slave courier navigating an indifferent universe with a chatty droid called Bax. Every sector, NPC, sound, and text string should feel like they were written by the same exhausted, sarcastic galaxy. The game's signature is **no drag, no mercy, no bullshit** — Newtonian physics, dark humor, and the creeping feeling that no matter how many sectors you clear, Nova Soma still wins.

This push is about taking what works and making it undeniable. Every scene reaches the same quality bar as the flight scene. Every NPC is fully voiced, funny, and mean. Bax is the soul of the game. The world is alive. The player has reasons to come back.

**North star:** after one run, a player tells a friend *"this game has a droid called Bax, and he plays harmonica when you're about to die."*

---

## Priority Stack

Items are ordered — top is most urgent. Each has a **felt test**: can a stranger describe the improvement in one sentence after 30 seconds of play?

| # | System | What Changes | Felt Test |
|---|--------|-------------|-----------|
| 1 | Terminal pacing | Bax's words settle before popup | "the game waits for you" |
| 2 | NPC quality parity | All NPCs: full keywords, dark humor, same depth | "every terminal is fun to type in" |
| 3 | String audit | Every string witty, satirical, in-universe | "the text is funny" |
| 4 | Terminal visuals | Terminals look like real CRTs, not green blobs | "oh that looks like an actual terminal" |
| 5 | Bax improvements | Reacts to skill, references past runs, opinions on NPCs | "Bax remembered that" |
| 6 | Visual quality parity | Every scene as good as flight: shop, death, corridor, landing | "the whole game looks this good?" |
| 7 | Harmonica | Better riffs + player input + mechanical hull hook | "wait, I can play along?" |
| 8 | Landing overhaul | Visual approach-align minigame, not button prompts | "landing felt like landing" |
| 9 | Corridor hazards + detail | Steam, tripwires, collapsing tiles, boss room | "the corridor had a boss?!" |
| 10 | Pilot give-up rule | Non-pirate AI disengages if player escapes | "he gave up chasing me" |
| 11 | Player ship visibility | Player ship clearly distinct from all NPC ships | "I can always tell where I am" |
| 12 | Stats + career records | Run summary + career stats in Bax's Records | "I've cleared sector 4 eighteen times" |
| 13 | Replayability: mutators | One run mutator per run (opt-in) | "this run has double debt / double rewards" |
| 14 | Replayability: unlocks | Persistent milestones unlock frames, items, lore | "I unlocked something new" |
| 15 | Sector hazard + opportunity | Every sector rolls a dominant hazard + a dominant opportunity | "this sector felt different" |
| 16 | Money system audit | Debt/credits reactive to every decision, clearly surfaced | "I made a trade-off that mattered" |
| 17 | Flight events | More events, player has a choice in each | "I got intercepted by a scrap dealer" |
| 18 | Difficulty selector | CASUAL / STANDARD / IRONS at main menu | "I can choose how much it hurts" |
| 19 | Chapter capstone moments | Unique set piece in sector 5 per chapter | "sector 5 was different" |
| 20 | Death feel | Highlight reel before debt screen | "I saw my best slingshot again" |
| 21 | "Dead Drift" theme | More emotional drift: Bax tiredness, eternal debt, indifferent universe | "this game knows what it is" |
| 22 | Multi-agent coordination | WORKING_ON.md claiming system, agent docs | no conflicts, shared direction |

---

## Epic 9 — Terminal Quality + NPC Parity

**Decision (planning committee):** every NPC must be brought to full depth. Some new NPCs have skeletal keyword sets and no humor. This is a visible quality gap that undermines the whole terminal system.

**May 2026 status:** 9.1 — **COMPLETE** (full NPC parity sweep across all 11 NPCs); 9.2 — **COMPLETE** (CRT visual overhaul, boot text, status bar, scanlines, vignette, flicker); 9.3 — **COMPLETE** (popup pacing gate); 9.4 — partial (propaganda ticker expanded; full string audit still open).

### 9.1 NPC audit — every terminal at the same depth

Run a pass on all NPCs in `terminal/npcs/`. For each, verify:

- **≥ 4 distinct win paths** — not just "pay" + "say the magic word." Different strategies, different personalities, different exploits.
- **Dark humor present** — every NPC should have at least 2 lines that are funny because they're bleak. If it reads like a customer service FAQ, rewrite it.
- **Cargo awareness** — all NPCs already have cargo flavor from Epic 6.8. Verify new NPCs (DRAY, MIRA VOSS, NOVA SOMA AI) are wired.
- **Keyword breadth** — minimum 12-15 keywords triggering distinct responses. No NPC should reply "I don't understand" to more than 40% of inputs.
- **Cross-NPC references** — at least 1-2 references to other characters in the universe (Bax, Gary, Nova Soma, Local 404).
- **Patience + disposition felt** — patience timer should visibly affect dialogue options and NPC responses before it runs out.

**NPCs to prioritize:** DRAY, MIRA VOSS, NOVA SOMA AI (new), RELAY-7 FELIX (upgrade to Gary-tier), TOLL AUTHORITY.

**Shipped May 2026 (this push):**
- Nova Soma dossier expanded from 2 → 4 path tracks (SQL EXPLOIT, PARADOX, POLICY, HARDSHIP all visible). Added `_sql_hit` / `_paradox_hit` flags so dossier reflects attempts.
- Cross-NPC reference filler added to Dray, Mira Voss, Toll Authority, Nova Soma — each now name-drops Gary, Sandra, Felix, or Bax in 2-4 lines. Continuity carries between terminals.
- Existing test suite still passes (`tests/test_terminal_npcs.py`, 6 tests).

**Shipped May 2026 (this push, continued):**
- RELAY-7 FELIX already at Gary-tier depth (8 win paths, full cross-NPC dict).
- Cross-NPC reference + humor sweep completed for all remaining NPCs: Sandra, Underground DJ (Marrow), Synthetic Droid (TK-9), Cargo Inspector (Holt), Insurance Adjuster (Morwenna), Kress, Pirate. Each now has 2-6 new filler lines referencing other characters. Galaxy feels connected.

**9.1 STATUS: COMPLETE ✓**

### 9.2 Terminal visual overhaul

The terminal currently renders as colored text on a tinted background. It should look like a real CRT terminal from a broken-down space station.

**Target look:**
- Curved CRT edge vignette (subtle barrel distortion or corner darkening via SRCALPHA mask)
- Authentic scanline density — every 2 rows, not every 4
- Text has a soft phosphor glow (blur radius 1px on bright text; acceptable via surface-level approach)
- Input cursor: blinking amber block, not an underscore
- Screen flicker: occasional very brief (1-frame) whole-terminal dim — rare (every 8-12s), just enough to feel like old hardware
- Boot text on terminal open: 2-3 lines of system boot garbage ("SECTOR COMM ARRAY v2.3.1 — LOCAL 404 LICENSED...") before NPC dialogue starts. Under 1 second total, non-skippable but fast.
- Status bar at bottom: signal strength (fluctuates, goes to static when hostile), encryption indicator, session timer

**Implementation note:** all in `terminal/terminal.py` and `terminal/npc_portraits.py` renderer. No changes to NPC logic, only presentation.

**Shipped May 2026 (this push):**
- Boot text overlay — 5-line type-revealing system splash on terminal open (~0.85s), with NPC-specific encryption label
- Status bar at bottom — signal-strength meter (wobbles, goes red+choppy when NPC is hostile), encryption label (varies per NPC: Nova Soma AES-72, Union ChCh-9, Pirate Band [OPEN], Local 404 Secure, etc.), session timer mm:ss
- Full-screen scanlines every 2 rows (was only on portrait, every 3 rows)
- Curved CRT vignette — concentric rounded-rect darkening, gives the glass curl look
- Soft amber phosphor edge glow around screen perimeter
- Random screen flicker — 1-2 frame dim every 8-12s
- All cached as SRCALPHA surfaces; recomputed only on screen-resize

### 9.3 Terminal popup pacing

**Decision:** when a terminal popup would open, gate it behind:
- (a) Bax's current priority line has been on-screen ≥ 2.5s **AND** the `EVT_BAX_SPEAK` queue has no priority items pending, OR
- (b) 5 seconds have elapsed since the popup trigger (hard cap — don't let Bax stall forever)

Add `_terminal_open_gate_t` to `RunManager`. The popup trigger arms the countdown; `update()` fires it when the gate opens. Feels like the universe breathes between events.

**Shipped May 2026 (this push):**
- `RunManager._install_terminal()` routes every Terminal creation through one gate. Both `open_terminal()` and the toll-authority direct path use it.
- Gate logic: if Bax has been silent for >0.5s, opens immediately. Otherwise pends the terminal and promotes it once (a) ≥2.5s have passed AND Bax has fallen silent for ≥0.5s, OR (b) 5s hard cap is hit.
- Tracks `_last_voice_char_t` via `EVT_VOICE_CHAR` subscription — that event already fires from existing Bax + NPC voice machinery, no new emit sites needed.
- `_reset_state()` clears the pending terminal so sector loads don't leak state.

### 9.4 String audit — every line, full pass

**Decision:** run an audit across every text surface in the game. Target tone: exhausted corporate dystopia, darkly funny, Bax-adjacent. It should feel like the whole universe was written by the same bitter author.

Scope:
- All NPC dialogue (every keyword response, every patience line, every outcome beat)
- All UI labels (shop item names, sector intro cards, HUD elements, menu items)
- All Bax lines (including contexts that sound too generic)
- Nova Soma propaganda ticker (expand, sharpen, make every line land)
- Sector designation names and "formerly" tags
- Death screen text, debt screen text
- Tutorial hint text

Tone benchmark: *"GENUINE NOVA SOMA® PARTS IN EVERY CLONE"* — that's the bar. Every string should earn its place.

**Shipped May 2026 (this push):**
- Loadout-draft propaganda ticker expanded from 8 → 17 lines (`roguelite/loadout_draft.py:_PROPAGANDA`). New lines name-drop Sandra Vega-Marsh, Local 404, Bax-class droids, and include darker beats: *"STATISTICALLY YOU WILL BE A CLONE BY DAY'S END. PLAN ACCORDINGLY."*

**Still open:** ~~the full game-wide string audit~~ — **COMPLETE May 25 2026.** See `docs/STRING_AUDIT_RESULTS.md`.

---

## Epic 10 — Visual Quality Across All Scenes

**May 2026 status:**
- 10.1 Shop screen: **COMPLETE** — condition badges (MINT/WORN/SCRAP) on every item card, credits display repositioned to top-right amber, Nova Soma™ branding scratched off right wall, exit door graphic at footer.
- 10.2 Death/decanting screen: **COMPLETE** — clone tube hospital background with 5 cylindrical tanks (active one glows), rotating taglines per clone count, "ACCEPT CHARGES (non-optional)" button, invoice panel floating over the room.
- 10.3 Portrait quality: **COMPLETE** — `_nova_soma_collections()` redesigned from humanoid face to asymmetric sensor array (primary offset-left bar, secondary vertical node, tertiary micro-dot cluster, quaternary edge strip). Sweep arc from primary sensor. Readout panel replaces "mouth" — scrolling hex values change rate/content with disposition (hostile=ERR+ALM, friendly=OK+SYN, neutral=raw hex). Emotion via readout state, not expressions.
- 10.4 Corridor: `delivery/corridor/` system already has per-chapter palettes defined; main render loop in `base.py` uses them. Additional wall panels/parallax/lighting still open.
- 10.5 Landing: **COMPLETE** — Bay status light panel (red/amber/green 3-state, reflects alignment angle); enhanced atmosphere shimmer at bay entrance with animated horizontal density streaks; magnetic clamp housing brackets on bay walls (status LED per bracket); Beat 2 gauge redesigned as cockpit instrument panel with bezel, header label, zone markers; vapor burst particles at hull contact points for first 1.5s of beat3.

**Decision:** every scene must reach flight-scene quality. Same vector renderer vocabulary: panel seams, glow halos, scorch marks, procedural depth. No scene should feel lower-fidelity than another.

### 10.1 Shop screen — full visual overhaul

Current state: text cards on a dark background. Target: a physical place.

- Background setting: a cramped airlock repurposed as a black-market stall. Crates stacked. Nova Soma branding half-scratched off the walls. Vendor silhouette behind a counter.
- Item cards: each has a hardware glyph, a scratched condition badge (MINT / WORN / SCRAP), and an affordability indicator (green if you can afford it; red with exact deficit shown if you can't)
- Credits display: large, amber, top-right — always visible, updates in real-time as you browse
- Selection feel: cursor moves with a hardware "click" and item selected gets a brief amber flash border
- Exit button: a door graphic, not a text button

### 10.2 Death / debt screen — full visual overhaul

Target: a corporate medical facility. Cold, fluorescent, deeply unpleasant.

- Background: clone tube room. Five or six cylindrical tanks in the background, one of them glowing with the new clone growing. Clinical vector illustration. Cold blue-green lighting.
- Nova Soma logo prominent, with a tagline that rotates each death (*"We value your continued productivity." / "Your previous self exceeded expectations — briefly." / "Clone activated. Debt transferred. Welcome back."*)
- Highlight reel: before the debt screen fully renders, show a 3-4 second "BEST MOMENT THIS RUN" replay — the highest-speed slingshot, the closest tether snap, the best NPC exploit. Text label identifies what it was. Bax delivers a brief line.
- Debt breakdown: itemized invoice format. Each line item is a specific Nova Soma charge. Clone fluid fee: itemized. Wreckage tow: itemized. Outstanding interest: calculated to the credit.
- "PROCEED" button should read something like "ACCEPT CHARGES (non-optional)"

### 10.3 Portrait + backdrop quality pass

Across all NPCs in `npc_portraits.py`:

- Every backdrop has ≥ 3 animated elements (was 2 in Epic 6.3 — bump to 3)
- No portrait is smaller than 140px across the face
- Disposition swings are visible at 0.5 second distance: hostile NPCs look hostile, compliant ones look relieved, exploited ones look broken
- NOVA SOMA AI: its "face" should be more alien — an elliptical sensor array, not a face. Readouts, not expressions. Emotion shown through readout state changes.

### 10.4 Corridor visual upgrade

Corridors should feel like dangerous places in a decaying corporate empire.

Per room:
- Wall panels: cracked, numbered, some with scratched-off Nova Soma branding
- Floor: subtle grid texture, with worn sections where foot traffic is high
- Ceiling: pipes, conduit, occasional dripping indicator (visual only)
- Background paralax: a dim second layer of deeper structure (steel skeleton, distant windows to space)
- Lighting: directional per room — blue-white in Nova Soma corporate sections, warm amber in inhabited zones, red emergency lighting when hazards are active

Per chapter: each corridor should have a distinctive color palette (Ch.1 industrial/amber, Ch.2 organic/bioluminescent green, Ch.3 government grey/beige, Ch.4 hotel gold/marble-white). The transition between rooms should shift the palette.

### 10.5 Landing bay visual upgrade

The landing sequence should feel like a real docking approach, not a cutscene placeholder.

- Station approach: as the ship closes distance, station details become visible — service lights, docking arms, other vessels parked, crew silhouettes moving
- Docking bay interior: bay lights (green = clear, amber = aligning, red = abort), clamp housing visible on walls, atmosphere shimmer at the bay entrance
- The Alignment gauge (Beat 2) should be drawn as actual ship instruments — a physical display within the cockpit view, not an overlay box
- Touchdown sequence: magnetic clamps animated, bay lights go green, brief vapor burst at the hull contact points
- Per chapter: bay aesthetics match station type (Ch.1 industrial, Ch.2 sterile, Ch.3 brutalist, Ch.4 luxury)

---

## Epic 11 — Bax: Soul of the Game

**May 2026 status (May 24 push):**
- 11.1a (12 mood-tagged riffs): already shipped — `audio/blues_licks.py` has 30 patterns mood-tagged across cocky/weary/panic/delighted/lonely/sarcastic.
- 11.1b (player "play along" input): deferred — high effort, low immediate value.
- 11.1c (harmonica restores hull): **COMPLETE (May 25 2026)** — `RunManager.start_harmonica_session()` locks rotation, +5 hull over 6s, blocked within 300 px of an active barge or when hull is full. Cancellable by W/S/UP/DOWN/SPACE. HUD bar in `renderer/hud_renderer.py`. Bound to `H` in flight.
- 11.2 (Bax reacts to skill): **PARTIAL** — added `EVT_CLOSE_CALL`, `EVT_SKILL_MANEUVER`, `EVT_LONG_FIGHT_SURVIVED`, `EVT_FIRST_TETHER_SNAP` to event bus; Bax subscribed with reactive line pools. `EVT_FIRST_TETHER_SNAP` emits from RunManager on first run-snap. `EVT_LONG_FIGHT_SURVIVED` emits when a barge has pursued >45s without capture. `EVT_CLOSE_CALL` and `EVT_SKILL_MANEUVER` emitters still need wiring in gameplay code (Bax handlers ready).
- 11.3 (references past runs): **COMPLETE** — `bax_context` dict on RunManager tracks `times_died_this_sector`, `last_sector_reached`, `exploits_used_run`, `slingshot_used_run`, `shops_visited_this_chapter`. Game.py updates `times_died_this_sector` on ship destruction. Bax holds a live reference via `attach_run_context()`. `_on_sector_start` reads it: if player died on the same sector ≥2 times, Bax fires a sector-repeat line instead of the default opener.
- 11.4 (NPC opinions): **COMPLETE** — `_NPC_OPINIONS` table in `bax/bax.py` with lines for Gary, Holt, Nova Soma, Felix, Mira, Kress, Pirate, TK-9, Marrow, Sandra, Morwenna, Toll Authority. Subscribed to `EVT_TERMINAL_OPEN` — fires once per (npc_key, chapter), keyed via `_opinion_fired` set.
- 11.5 (mournful audibility): **COMPLETE** — `_tick_licks()` in `audio_manager.py` checks `_hull_pct < 0.30`. At low hull, forces mood "weary", boosts volume 1.55×, tightens cadence to 5-9s (vs 8-18s). Signature dying-Bax moment is unmissable.

**Decision:** Bax is the emotional anchor. He needs more range, better music, and he should remember.

### 11.1 Bax harmonica — all three upgrades

**Decision from planning:** implement all three:

**(a) Expanded musical content (12 riffs, mood-tagged)**

Current state: ~3 stock riffs, rarely noticeable. Target: 12 distinct harmonica pieces with mood tags:

| Mood | Used When | Feel |
|------|-----------|------|
| `mournful` | hull < 40%, just died | slow, minor, aching |
| `defiant` | barge destroyed, tether snapped | mid-tempo, bluesy, climbing |
| `weary` | sector 4-5, high debt | dragging tempo, flat notes |
| `hopeful` | slingshot executed, perfect dock | brighter, upward phrase |
| `tense` | barge within 200px, harpoon arming | staccato, dissonant |
| `sardonic` | exploit succeeded | jaunty, slightly mocking |
| `ambient` | idle flight, no threats | slow drift, barely there |
| `panic` | hull < 10% | stuttering, incomplete phrases |

Riff selection: weighted by current mood, with cooldown to prevent repeat. Mood derives from game state (hull, debt, barge proximity, recent events).

**(b) Player input — "play along"**

When Bax starts a riff, a subtle prompt appears: *"H + [direction]"*. Pressing H + directional key contributes a note. Correct note timing (within ±0.3s of the beat) earns a visual "+" and a brief Bax reaction. Wrong note: Bax pauses and gives a flat look, then resumes. Plays along for up to 8s before Bax takes it solo again.

**(c) Mechanical hook — harmonica restores hull**

Initiating a harmonica session (H key, min 4s before flight context blocks it) locks rotation input for the duration. Over 6 seconds, hull recovers +5 hp. This is the vulnerability tradeoff — you drift while Bax plays, but you heal a little. Cancellable by any flight input. Does not work in combat proximity (within 300px of active barge).

### 11.2 Bax reacts to skill

New event triggers for Bax voice lines:

- `close_call` — barge/debris passed within 30px without hitting. *"That one went right past your ear. Good LORD."*
- `skill_maneuver` — slingshot + velocity redirect combination executed within 2s. *"Look at you. Courier school told me you'd be useless. Courier school was wrong."*
- `long_fight_survived` — barge in pursuit > 45 seconds without capture. *"Right, he's given up a bit of his soul tonight. Fair play."*
- `first_tether_snap` — tether snapped for the first time in a run. *"See? SIDEWAYS. I told you sideways. Did it feel like sideways? It felt like sideways."*

### 11.3 Bax references past runs

`Bax` should read from `RunHistory` / stats data to occasionally inject run-specific lines:

- After a death: *"That's clone... [count]. Right, we're getting somewhere. Barely."*
- If player has died on same sector before: *"Sector three again. You do love sector three."*
- If player hasn't used slingshot yet in a run: *"You know the gravity wells aren't just decoration, yeah?"*
- On first shop visit of a fresh chapter: *"Back again. Same shop. Different debt bracket. Some things never change."*

Store a `bax_context` dict in `RunManager` with flags like `times_died_this_sector`, `last_sector_reached`, `exploits_used_run`, etc. `Bax` reads these on relevant events.

### 11.4 Bax has opinions on NPCs

Pre-load opinion lines per NPC key that fire once per chapter on first terminal entry:

| NPC | Bax's Opinion |
|-----|---------------|
| Gary | *"Gary. Right. Keep it short — he thinks short conversations mean you respect his time. You don't. But act like you do."* |
| Inspector Holt | *"Holt. Don't let him talk about compliance. He'll talk about compliance. He loves compliance the way I love a quiet sector — never actually gets one."* |
| NOVA SOMA AI | *"That's not a person, that's a debt collector wearing a friendly face. Every word it says is a legal document."* |
| Nervous Fence | *"Felix? Good bloke. Very twitchy. Don't mention the incident — he'll know which incident."* |
| Mira Voss | *"Mira. She fixed my left thruster once. Charged me twice. Worth every credit. Don't tell her I said that."* |
| KRESS | *"KRESS. I'll be honest — I don't know what KRESS wants. KRESS doesn't know what KRESS wants. Just let KRESS talk."* |
| Pirate | *"Right, this one's not here for conversation. Don't philosophise. Philosophising with pirates ends badly."* |

Fire once per NPC per chapter (not per encounter). Store fired flags in run context.

### 11.5 Harmonica riffs — the existing ones must be audible

**Explicit problem from planning:** the harmonica riffs from the last pass weren't noticeable. Before adding new content, fix the volume, timing, and distinctiveness of what exists.

Checklist:
- Volume: harmonica should sit at ~60% of the Bax-voice blip volume when ambient, 80% when mood-matched to action
- Attack: riffs start within 0.5s of the trigger, not delayed
- Duration: each riff completes a full phrase — no truncated endings
- The `mournful` riff at low hull should be unmissable — this is the signature moment

---

## Epic 12 — Replayability Systems

**May 2026 status (May 24 push):**
- 12.1 (run mutators): **PARTIAL** — full table of 10 mutators in `roguelite/mutators.py`. `MutatorRegistry` rolls a mutator at run-start (first run of each chapter has no mutator). Banner displayed in loadout draft above the columns. Effects wired for `debt_surge` (credit pickup x2 — slingshot/snap bonuses scale), `fragile_frame` (slingshot overdrive duration x2), `veteran_clone` (+50k starting debt), `no_shop` (suppresses shop appearances). Remaining mutators are banner-only flags (`cold_sector`, `system_glitch`, `slingshot_only`, `quiet_sector`, `novice_pass`).
- 12.2 (persistent unlocks): **COMPLETE (core)** — `MetaProgression._DEFAULTS` extended with `unlocks: list[str]` and `milestone_counters: dict`. `has_unlock()`, `add_unlock()`, `inc_milestone()`, `milestone()` methods. `EVT_UNLOCK_EARNED` emits when a new unlock is added (Bax reacts with a line). First wired milestone: 10 lifetime slingshots → `slingshot_only_mutator` unlock. Additional unlock check-points still to plumb in shop/loadout.
- 12.3 (sector hazard/opportunity rolls): **COMPLETE** — `SectorLayout` extended with `hazard_roll` and `opportunity_roll` fields. 5 hazards (gravity_tide, sensor_jamming, scan_infestation, asteroid_shower, comms_blackout) and 5 opportunities (wells_favorable, salvage_cache, friendly_signal, abandoned_station, weak_barge) defined in `procedural.py`. Sector 0 always rolls blank. Display: HUD shows the rolled hazard + opportunity in red/green respectively under the sector name, fading out over the first 8s of the sector. Effect plumbing for individual rolls is display-only for now.
- 12.4 (stats tracking): **COMPLETE** — `roguelite/stats_tracker.py` with `StatsTracker` class. Two layers: per-run dict (slingshots, snaps, kills, credits_earned, debt_added, best_slingshot_speed, npc_outcomes) and persistent career dict (runs_started/completed, lifetime totals, deepest sector per chapter, best single-run credits, NPC outcomes ledger keyed per-NPC). Persists to `data/saves/stats.json`. Subscribes to `EVT_RUN_START`, `EVT_RUN_END`, `EVT_SECTOR_CLEAR`, `EVT_SLINGSHOT`, `EVT_TETHER_SNAP`, `EVT_BARGE_KILLED`, `EVT_TERMINAL_CLOSE`, `EVT_DEBT_UPDATE`, `EVT_SHIP_DESTROYED` — no plumbing changes needed outside the tracker module. Public helpers `run_summary_lines()` and `career_summary_lines()` for HUD/cards.



### 12.1 Run mutators

One mutator per run, applied at run-start. The loadout draft shows the active mutator as a banner above the columns (*"THIS RUN: DOUBLE DEBT / DOUBLE REWARDS"*).

Mutator pool (10 total):

| Name | Effect |
|------|--------|
| DEBT SURGE | Interest rate ×3 — but credit pickups ×2 |
| COLD SECTOR | Every sector is Frozen Trail or Mine Strip |
| OPEN SEASON | Barges are more aggressive; barge kills pay ×3 |
| SYSTEM GLITCH | Gun malfunctions 3× more often; successful shots worth +50 cr each |
| SLINGSHOT ONLY | Jump timer won't reduce from sector time — only from slingshots |
| NO SHOP | Shops don't appear; all credits accumulate as end-of-run bonus |
| FRAGILE FRAME | Hull max -30; slingshot overdrive duration ×2 |
| VETERAN CLONE | Start with 50k debt; start with full hull and military torch |
| QUIET SECTOR | Barges don't spawn sectors 1-3; sector 4-5 spawn 2 |
| NOVICE PASS | First death of run free (no debt fee); only available on CASUAL difficulty |

Mutators are optional — player can skip by pressing a key. First run of each chapter has no mutator.

### 12.2 Persistent unlocks tied to milestones

Unlock tree stored in `data/saves/unlocks.json`. Milestones and rewards:

**Flight unlocks:**
- Clear sector 3 for the first time → unlock SCRAP DELTA-7 as guaranteed option in loadout draft
- Survive a barge tow (not immediate death) → jammer item appears in shop pool
- Execute 10 total slingshots across runs → SLINGSHOT ONLY mutator available
- Kill 5 pirate gunboats → new Bax voice line bank ("PIRATE HUNTER" lines)

**Terminal unlocks:**
- Exploit 3 different NPC types → "VULNERABILITY DATABASE" tab opens in Bax's Records
- Win 5 terminals without patience running out → TOLL AUTHORITY respects your signal — reduced fee
- Discover all exploit types for one NPC → that NPC's dossier entry in Bax's Records shows full map

**Meta unlocks:**
- Clear a chapter → cargo dossier card available in main menu
- Pay off 50k total debt across all runs → cosmetic: ship leaves amber exhaust trail instead of blue
- Clear sector 5 with hull > 70% → HARDCORE variant unlocked for that chapter

### 12.3 Sector hazard + opportunity rolls

Every sector rolls one dominant hazard and one dominant opportunity at load time.

**Hazard pool** (in addition to existing theme hazards):

| Hazard | Effect |
|--------|--------|
| GRAVITY TIDE | Wells shift direction every 30s |
| SENSOR JAMMING | Barge radar disabled this sector |
| SCAN PING INFESTATION | Union scanners fire every 12s instead of 30s |
| ASTEROID SHOWER | Debris count ×2; lasts 45s of sector |
| COMMUNICATION BLACKOUT | Terminal negotiation patience reduced 30% |

**Opportunity pool:**

| Opportunity | Effect |
|-------------|--------|
| GRAVITY WELLS FAVORABLE | Wells positioned near entry — slingshot within first 20s |
| SALVAGE CACHE | Extra canister cluster near sector center |
| FRIENDLY SIGNAL | An NPC ship will hail (hailer spawn guaranteed) |
| ABANDONED STATION | A dead station with a loot cache (+1200 cr, 1 free shot at unlocking) |
| WEAK BARGE | This sector's barge spawns at 50% HP |

Print hazard + opportunity in the sector intro card. Player can adapt strategy accordingly.

### 12.4 Stats tracking — two layers

**Layer 1 — Run summary** (shown on sector clear cards and death screen):
- Kills (barges + pirates)
- Slingshots executed
- Tether snaps
- Jumps made
- Terminal outcomes (exploit / release / impound / paradox counts)
- Credits earned / debt accrued
- Best single slingshot speed

**Layer 2 — Career stats** (Bax's Records Tab 2 — Run Highlights):
- Lifetime runs started / completed
- Total debt accrued (and paid off)
- Deepest sector reached (per chapter)
- Total slingshots / tether snaps / kills
- Best single-run credit recovery
- Lowest hull% run-clear
- Fastest sector 1 clear
- Longest no-damage streak (seconds)
- NPC outcomes ledger: per NPC, how many times you've exploited / released / impounded / paradoxed them

Persist in `data/saves/stats.json`, updated at every sector clear and run end.

---

## Epic 13 — World Aliveness + Theme Depth

### 13.1 Money system — fully reactive

**Audit decision:** every credit decision in the game should be visible, intentional, and feel like a trade-off. Run a pass to verify:

- **Debt counter** is always visible during flight, always current, never frozen
- **Every debt event** gets a `EVT_DEBT_UPDATE` with a source label that Bax or UI surfaces (*"NOVA SOMA: INTEREST ACCRUAL +47 cr"*)
- **Credit gains** are visible immediately with source — slingshot bonus, canister pickup, barge kill, perfect dock
- **Shop decisions** show before-and-after debt projection: *"Purchase JAMMER (-3200 cr) | Current debt: 84,200 → 87,400"*
- **Terminal outcomes** surface credit impact immediately: exploit outcome shows exact rerouted amount, impound outcome shows exact fine
- **Death penalty** is itemized on the death screen — player should understand exactly why they owe what they owe
- **Interest rate** should be explained diegetically somewhere early (Bax, tutorial, or a Nova Soma popup), not just visible as a number ticking up

Add `_last_debt_event_label` to the HUD renderer so the most recent debt change floats beside the debt counter for 2s.

### 13.2 More flight events — player has a choice in each

Current events mostly play out as flavor-text observations. Upgrade every event to include a player decision:

New events:

| Event | Choice | Outcome |
|-------|--------|---------|
| Drifting wreck with blinking light | Investigate (slow down, risk barge time) / Ignore | Investigate: 60% loot (+1400 cr canister), 40% ambush (pirate emerges) |
| KRESS prank call | Play along / Hang up | Play along: small credit reward, Bax entertained. Hang up: Bax disappointed, KRESS vows revenge (next KRESS call goes worse) |
| Abandoned escape pod | Dock and check / Leave it | Dock: 50% survivor (brief NPC encounter, +1000 cr reward), 50% booby-trap (15 hull damage) |
| Union recruitment ping | Respond / Ignore | Respond: fake-join, get insider tip on barge patrol route (barge delay +15s). Ignore: scan ping fired at you. |
| Scrap dealer broadcast | Respond / Ignore | Respond: brief mini-terminal, sell current canister for credits at a markup |

Each event pops via `EVT_COMMS_INTERCEPT` with Bax framing. Player response window: 8 seconds. Default (no input) = ignore.

### 13.3 Differentiate player ship from NPC ships

**Problem from planning:** at speed, the player ship blends with AI ships. Fix:

- Player ship always renders with a distinct **cyan edge glow** (1px cyan outline on hull polygon, very slight — not intrusive)
- Player exhaust is always blue-to-white (current). AI ships are orange/amber/red. Never use blue exhaust for NPC ships.
- Player has a constant dim cyan HUD circle at 28px radius (the velocity indicator ring) — AI ships have none
- In dense scenes, player ship gets a brief amber "YOU" label for 1.5s on sector load (disappears, never recurs)

### 13.4 "Dead Drift" theme — hit it over the head

The game's core emotional theme: **nothing you do ultimately matters to Nova Soma, but the moments you make matter to you.** Bax knows this. The universe doesn't care.

Specific beats to add or strengthen:

- **Sector naming:** all sector "formerly" tags should have a story. Every crossed-out name was once someone's home or livelihood. The rename is the joke. (*"OPTIMISED LOGISTICS THROUGHPUT ZONE, formerly the Widow's Crossing"* is the bar — that's good. Find any that fall short.)
- **Nova Soma's indifference:** at run end, even on a perfect clear, Nova Soma's response should be bureaucratic and perfunctory — no celebration, just a new assignment. Bax provides the actual acknowledgment.
- **Debt never ends:** the career stats should show total debt incurred across all runs, which will always be a shocking number. Bax should have a line when that number crosses milestones (*"You've paid for your own body six times over. Might be a record. Definitely a record for this sector."*)
- **Chapter endings:** every chapter ending should feel like a pyrrhic win — the cargo was delivered, Nova Soma got their cut, you're still in debt. The only reward is that you survived and Bax is still here.

### 13.5 Difficulty selector — main menu

Before the loadout draft, a one-screen difficulty selector:

```
NOVA SOMA COURIER RISK ASSESSMENT

  [  CASUAL  ]    Hull +30    Debt rate ×0.7    Barges: patient
  [STANDARD  ]    Standard    Standard          Standard
  [  IRONS   ]    Hull -20    Debt rate ×1.5    Barges: relentless

Select with ARROW KEYS. ENTER confirms.
```

Settings stored in `meta`. Difficulty tag shown in all run stats. No content locked behind difficulty — IRONS is pride mode only.

---

## Epic 14 — Corridor + Landing Upgrade

**May 2026 status (May 24 push, continued):**
- 14.1 (corridor hazards + boss room): **PARTIAL/COMPLETE** — three new hazard classes (`SteamVent`, `Tripwire`, `SecurityBeam`) added to `delivery/corridor/elements.py`. Wired into `_check_hazards()` in `base.py`. Distributed across chapters 1, 2, 3 as live samples — steam vents at choke points (telegraphed by pressure-gauge needle), tripwires that trigger a Bax alarm line, security beams that sweep ceiling-down cones (shadow zones safe). Collapsing-floor pattern already exists (`CollapsingPlatform`). Boss-room *structure* is already in place across all 4 chapters (final room with `BossRoomTrigger` + chapter NPC); content polish (Gary doing something absurd, Mycelium chamber control inversion, Tribunal stillness, Quantum observation deck) remains as a follow-up content pass.
- 14.2 (landing overhaul): **COMPLETE** — Beat 2 fully replaced. Old J-tap + SPACE-hold QTE deleted (`_resolve_j_align`, `_finish_beat2`, `_j_marker_pos`, `_J_ALIGN_TIMEOUT`, `_BURN_HOLD_S`, etc. all removed). New continuous speed-dock minigame: ~8s approach with W/S throttle, A/D pitch (auto-trim within ±20°, ABORT outside). Speed gauge has green sweet-spot band, amber idle zone, red overshoot zone. Distance bar tracks descent. Accuracy % displayed live. Overshoot count + idle accumulator drive scoring. New cockpit panel renders bezel + gauge + distance bar + accuracy readout + overshoot tally + artificial horizon strip with ±20° tolerance marks. Retro flames on the descending ship now scale with throttle (orange = nominal, red = overshooting). Same `EVT_DOCK_PERFECT` / `EVT_DOCK_ROUGH` events, same `_land_score` outputs to Beat 3.
- 14.3 (pilot give-up rule): **COMPLETE** — `_tick_approach()` in `antagonists/ai_ship.py` accumulates `_approach_far_t` when distance > 480px. After 8s sustained, `HAILER` and `TRAFFIC` ships transition to `ST_DEPART` and emit a one-shot `"Lost interest. Lucky."` Bax line. `PIRATE` ships skip the check entirely.

**Plus from Epic 11/12 carry-over (this push):**
- 11.2 emitters wired: `EVT_CLOSE_CALL` fires from RunManager update loop when any barge/debris/shower-rock departs from within 30px without an intervening hit (6s cooldown to avoid spam).
- 12.1 remaining mutator effects all plumbed: `cold_sector` overrides theme to FROZEN_TRAIL/MINE_STRIP via new `force_theme` arg on `generate_sector`; `system_glitch` triples gun malfunction rate via `Gun.malfunction_multiplier` class attribute + RunManager subscribes to `EVT_GUN_FIRE` to award +50cr per shot; `slingshot_only` blocks sector-time timer accumulation and bumps the timer by `_sector_dur/3` per slingshot; `quiet_sector` suppresses barge spawns in sectors 0-2 and doubles them in 3-4; `novice_pass` skips the first death's debt penalty (still increments clone count) with a Bax acknowledgement line.

### 14.1 Corridor hazards

**New hazards (in addition to existing obstacles):**

- **Steam vents:** floor or wall mounted. Visual: steam particle burst pre-telegraph (0.6s hiss, then eruption). Active for 1.8s, then 4s cool-down. Damage: 15 hull. Telegrpahed visually by a pressure gauge icon above the vent counting down. Can be shot to disable temporarily.
- **Collapsing floor tiles:** marked with a subtle crack texture. When stepped on, begin collapsing after 0.4s of weight — visible crumble animation. Fall into void = checkpoint respawn. Not trapped, just requires light-footedness or a running jump.
- **Tripwire:** thin cyan line across a corridor. Crossing triggers alarm: Bax *"Security alert — they know you're here"* + speeds up a patrolling guard for 15s. Wire can be avoided (jump over it) or disabled (shoot the mount points at each wall).
- **Rotating security beam:** a spotlight sweeping the floor. Shadow zones allow safe movement. Caught = 10 hull damage + 8s alarm state.

**Boss room for every chapter:**

The final room of every corridor (before cargo handover) is a 15-20 second set piece. Not a combat boss — a *moment*.

| Chapter | Boss Room | What happens |
|---------|-----------|-------------|
| Ch.1 | Gary's den | Gary is physically present, doing something absurd. Brief confrontation, cargo drops, Bax has a lot to say. |
| Ch.2 | The mycelium chamber | The shrooms are *in the walls*. Controls briefly invert. Researcher NPC panicking. |
| Ch.3 | The compliance tribunal | Three officials at a table. You have to physically walk past them while they read Form 7-B aloud. One wrong move triggers all three. |
| Ch.4 | The quantum observation deck | Opening the box is required to leave. What's inside is different every run. |

### 14.2 Landing sequence overhaul

**Decision (planning):** replace the current button-prompt QTE with a visual approach minigame.

Replace Beat 2 (alignment + retro burn) with a single **continuous approach sequence**:

- Ship is shown on a side-view vector illustration approaching the docking bay
- A green sweet-spot band on a horizontal gauge represents the ideal docking speed
- Player controls speed with W/S — too fast = overshoot (hull damage), too slow = dock master charges idle fee
- Angle is auto-corrected by docking clamps if within ±20 degrees; outside that = abort and re-approach
- Visual: the station grows in size as you approach. Actual parallax — objects in the dock get larger.
- The whole thing takes ~8s. Natural, physical, readable.

**Same scoring system** (perfect dock bonus, rough landing penalty), just tied to the speed gauge rather than QTE timing.

### 14.3 Pilot give-up rule

Any NPC ship in `ST_APPROACH` with `BEHAVIOR_HAILER` or `BEHAVIOR_TRAFFIC`:

- Every 2s, check if distance > 480px
- If distance > 480px for 8 consecutive seconds → transition to `ST_DEPART`
- Fire Bax line: *"Lost interest. Lucky."* (once, no repeat)

**Exception:** `BEHAVIOR_PIRATE` ships never give up, regardless of distance. Barges (existing system) never give up.

---

## Multi-Agent Coordination

**Problem:** multiple agents work this codebase. Without coordination, two agents can edit the same file simultaneously, producing conflicts or duplicated work.

**Solution: WORKING_ON.md claiming system.** See `/home/user/Dead-Drift/WORKING_ON.md`.

### Rules for all agents:

1. **Before touching a subsystem**, read `WORKING_ON.md`. If it's claimed, work on something else.
2. **Claim your subsystem** by adding an entry: `| subsystem | branch | timestamp |`
3. **Release your claim** by removing your entry when work is committed.
4. **Subsystem map** (what each file belongs to):

| Subsystem | Files |
|-----------|-------|
| renderer | `renderer/vector_renderer.py`, `renderer/cockpit_renderer.py`, `renderer/sci_fi_ui.py` |
| terminal | `terminal/terminal.py`, `terminal/npc_portraits.py`, `terminal/npcs/*` |
| npcs | `terminal/npcs/*` (individual NPC files — claim individually) |
| bax | `bax/bax.py`, `bax/vocabulary_vault.py`, `audio/audio_manager.py` (harmonica) |
| corridor | `delivery/corridor/*`, `delivery/platformer.py` |
| landing | `delivery/landing_sequence.py` |
| run_manager | `roguelite/run_manager.py` |
| meta | `roguelite/meta_progression.py`, `data/saves/stats.json`, `data/saves/unlocks.json` |
| settings | `config/settings.py` |
| ai_ships | `antagonists/ai_ship.py` |

### Definition of done — three filters

Before marking any item complete, verify all three:

1. **Named** — does this feature have a name the player would use to describe it?
2. **Felt** — can a stranger describe how it feels in one sentence after 30 seconds of play?
3. **Referenced** — does Bax or an NPC reference it, so it feels integrated with the world?

If a feature can't pass all three, it's implementation without expression. Finish it.

---

## What "award-quality" looks like

When this push is complete:

- **Every terminal** is fun to type in, looks like a real CRT, and every NPC is funny and mean in their own distinct way
- **Every string** in the game sounds like it was written by the same bitter author who loves this universe
- **Bax** plays harmonica you can hear, remembers your last run, has opinions about Gary, and panics with you under fire
- **Every scene** — shop, death, corridor, landing, terminal — reaches the visual quality of flight
- **A player's second run** feels different from their first because of the mutator, the sector rolls, and the persistent unlock they just got
- **The debt counter** ticking up feels like story, not just punishment
- **After clearing all four chapters**, there's still something to do: HARDCORE mode, hidden lore fragments, the Vulnerability Database to complete

That's the game.

---

*Last updated: May 2026 planning committee*  
*Next review: after Epic 9 + 11 are complete*
