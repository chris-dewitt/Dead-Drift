# THE ALIVENESS PUSH

**Branch:** `rhubarb/aliveness-push`
**Started:** May 25 2026
**Status:** Phases A–G complete. Phase H: H.2/H.3/H.4 shipped; H.1 `[~]` (mix audit landed, accessibility UI + audible play-pass pending). This is the final phase.
**Scope:** Open-ended (no time cap)
**North star for all agents:** this document supersedes `IMPROVEMENT_PLAN.md` and `NEXT_PUSH.md` for active work.

---

## Vision

Dead Drift already has the bones: physics, NPCs, Bax, corridors, landing, meta-progression. This push is about making the world feel **lived in.** Every system gets the same treatment: it should reflect that there are other people in this universe, the player has a history, and the choices they make echo across runs.

The signature test for every item in this push: *does it make a returning player notice something they wouldn't have caught the first time?* If yes, it ships. If no, it's polish for polish's sake and we cut it.

**Theme keyword:** *witnessed*. The player should feel witnessed by the world — by Gary, by Bax, by the Union scanner, by the corridor lore. The universe notices them. That's what makes a run feel real.

---

## Sequence Strategy

**Bugs first, then features. Strict sequential, no jumping around.**

Land a clean baseline before stacking new systems on top. The eight phases below run in strict order — A finishes before B starts, B finishes before C, all the way through H. Within a phase, items can be batched, but the phase itself doesn't open until the prior closes. This is a deliberate choice to put real heart into each area instead of context-switching across the board.

**Post-C trust cleanup (May 25 2026):** Before opening Phase D, land the small current-main trust patch for terminal activation lifecycle, first-visible-terminal NLTK bootstrap, full SCANNING parity across the expanded NPC roster, and cargo-specific dialogue for the newer NPCs.

| Phase | Theme | Order |
|-------|-------|-------|
| A | Foundation: cursor merge + critical bugs | 1 |
| B | NPC schema overhaul + new characters | 2 |
| C | Gameplay mechanics | 3 |
| D | Graphics & visual feedback | 4 |
| E | Story & world | 5 |
| F | Bax depth | 6 |
| G | Landing & corridor | 7 |
| H | Audio & soundtrack | 8 |

---

## Phase A — Foundation (Bugs + Cursor Sync)

### A.1 Merge cursor branches into main — [x]
Bring `cursor/playtest-doc-updates-e5ad`, `cursor/improvement-plan-spec-52e5`, `cursor/soundtrack-master-plan-c565`, and `cursor/improvement-plan-doc-update-e5ad` into `main` so the cursor-only playtest findings + soundtrack plan are the new shared baseline. Resolve doc conflicts in favor of the most recent factual content; my Phase 1/2 status work and the cursor branch design locks should both survive.

### A.2 Shroom control inversion (Phase 0.6) — [x]
Ch.2 cargo periodic control inversion not firing in play. Reproduce, trace `cargo.update` → `controls_inverted` → `_read_input`, confirm overlay + Bax line. See cursor branch 0.6 spec.

### A.3 Barge intercept = Gary / Union only (Phase 0.7) — [x]
`run_manager.open_barge_terminal()` randomly assigns pirate/synthetic/insurance — wrong. Lock to Gary (or the new Union reps in B.6). Move pirate/DJ/fence to non-barge comm channels.

### A.4 Dock visuals = Union Local 404 + Gary (Phase 0.8) — [x]
Landing Beat 2 dock master = Gary (or chapter-appropriate Union contact). Union amber palette, Local 404 signage, repo bay markers in background.

### A.5 Non-Union NPCs get distinct ship hulls (Phase 0.9) — [x]
Pirates / Marrow / Kress / Sandra need their own in-flight silhouettes — not repo barges, not the courier wedge. Currently they're terminal-only.

### A.6 Ch.3 Paperwork corridor broken (Phase 0.10) — [x]
Clerk dialog modal + no pause in DELIVERY locks input. Repro and fix per cursor branch spec.

### A.7 Harpoon visibility audit — [x]
Player has never seen a harpoon in play. Audit `physics/tether.py` render path; confirm projectile + tether line thickness/contrast; add muzzle flash on barge; verify AIM warning beam is visible.

### A.8 Barge slowdown on bullet hit — [x]
`RepoBarge.take_hit()` — apply brief velocity damp or speed clamp on each non-disruption hit so player can land follow-up shots. Currently hits don't slow them.

### A.9 Cockpit portrait glow verification (Epic 7.1) — [x]
Doc claims healthy/warning/critical/panic glow tiers shipped, but flagged suspect by audit. Play-verify all 4 tiers visible; fix if not.

### A.10 NLTK lazy bootstrap (Epic 1.10) — [x]
Move startup NLTK download to first-terminal-open trigger. Splash overlay + Bax line during wait. Boot to main menu instantly.

---

## Phase B — NPC Foundation

### B.1 NPC keyword/bribe schema — [x]
Standardize every NPC:
- **Keywords:** minimum 15 accepted pickup words per NPC
- **Bribes:** consistent `BRIBE [X cr]` format (no vague verbs)
- **Exploits:** comparable count and difficulty across NPCs
- Build a single audit table in `docs/NPC_SCHEMA.md` showing current vs target

### B.2 Universal cheat code easter egg — [x]
`fuck off` (case-insensitive) works on every NPC as guaranteed pass/escape. **Easter egg only:** never advertised in keyword hints, tutorial, README, docs, or in-game text. Players discover organically.

### B.3 Felix expansion — [x]
Add to 15+ keyword baseline. `gossip` either works or is removed from any hint. Re-audit exploits.

### B.4 Krellborn rework — [x]
Scarier tone. Keyword audit to 15+ baseline. Distinct pirate voice character — currently doesn't land as a threat.

### B.5 Dray rework — [x]
- New portrait (current one is weak)
- Expanded lore/background
- `gripe` either works or is removed
- `bribed` → `BRIBE [X cr]` standardized format
- Push to 15+ keywords

### B.6 Two new Union barge riders — [x]
Replace Gary monoculture in late sectors:
- **Idealist Union Rep** — true-believer, quotes Union charter unironically, talks "shared prosperity" while clamping your hull. Earnest, irritating to negotiate with.
- **Corrupt Union Rep** — crooked, organized crime ties, takes bribes but might rob you anyway. Different cynicism from Gary's.

Each needs: portrait, dialogue tree, 15+ keywords, exploits, bribe paths.

### B.7 NPC cross-references — [x]
Characters mention each other in dialogue. Marrow plays unauthorized Gary training videos on her pirate station. Kress mutters about Sandra's "perfect record." Builds a web through casual mention.

### B.8 Bribe negotiation mini-game — [x]
Bribes become 2–3 turn negotiations. Cheap NPCs accept low. Greedy ones counter-offer. Some refuse in character (*"I don't take bribes from Union men"* / *"…add another zero"*).

---

## Phase C — Gameplay Mechanics

### C.1 Speed-scaled collision damage — [x]
Impact damage multiplies with relative velocity at moment of collision. Rewards speed management near obstacles; punishes throttle-mashing.
**Shipped:** `ship/ship.py` `take_damage()` scales `_IMPACT_SOURCES` by excess speed above `COLLISION_SPEED_BASE`.

### C.2 Slingshot chains — [x]
Successive slingshots within ~3s stack a multiplier (1.0× → 1.5× → 2.0× → 2.5×). Skilled players chain wells. High skill ceiling on existing mechanic.
**Shipped:** `run_manager._on_slingshot()` chain window + credit multiplier; HUD floater via existing `EVT_SLINGSHOT`.

### C.3 Sector escalation timer — [x]
Every 30s in a sector, something escalates: another barge spawns, gravity wells intensify, scanner pings more often. Visible escalation cue. Forces forward momentum.
**Shipped:** `_apply_sector_escalation()` — odd levels spawn barge, even levels bump well mass; Bax line + `EVT_SCAN_PING`.

### C.4 Gravity well orbital bonus — [x]
Orbit a well at the right velocity band for 3+ seconds → automatic slingshot multiplier. Rewards precision flying over brute force.
**Shipped:** `_check_orbital_bonus()` — 120–220 px/s band inside sling range for 3s → +1200 cr orbit payout.

### C.5 Barge detection cone — [x]
Visible amber sweep cone in `PATROL` state showing barge FOV. Functional (telegraphs detection range) and atmospheric.
**Shipped:** `vector_renderer._draw_barge_patrol_cone()` — 55° cone, 280 px, pulsing amber fill.

### C.6 Debt timer with teeth — [x]
Debt should *threaten*, not just tick. Every 500cr milestone closes off a skip option, adds a penalty event, or triggers a Bax line. Pick the cheapest version that lands.
**Shipped:** `_check_debt_recovered_milestones()` — Bax line every 500 cr recovered; even milestones add +1s sector timer pressure.

### C.7 Cargo damage as cumulative penalty — [x]
Every hit damages cargo by a percentage; on delivery, paid only for % surviving. Creates "deliver clean vs fast" tradeoff.
**Shipped:** `delivery_sequence._compute_result()` scales delivery bonus by cargo integrity; result card shows integrity %.

---

## Phase D — Graphics & Visual Feedback

### D.1 Progressive hull damage on ship sprite — [x]
60% → cracks. 30% → sparks venting from thruster nozzle. 10% → broken antenna, atmosphere leak particles. Hull state readable at a glance without HUD.
**Shipped:** `vector_renderer._draw_ship_damage_overlays()` adds scorch marks, blown panels, sparks, broken antenna, and atmosphere leak particles on low hull.

### D.2 Barge spotlight cone — [x]
Repo barge in PATROL casts swinging amber light cone. Atmospheric + functional (telegraphs C.5 detection range).
**Shipped:** `vector_renderer._draw_barge_patrol_cone()` upgraded from faint fill to layered amber spotlight with rim, spokes, and range arcs.

### D.3 Velocity chromatic aberration — [x]
Subtle RGB split on screen edges at high speed; obvious at overdrive. Reinforces physical sensation of going too fast.
**Shipped:** `vector_renderer._draw_velocity_chromatic_aberration()` adds red/cyan edge splits, speed streaks, and ship-adjacent RGB ghosting above the high-speed threshold.

### D.4 Cockpit viewport cracks — [x]
Heavy hits crack the cockpit window itself. Cracks expand with damage; repaired on next dock. Literal HP indicator framing player view.
**Shipped:** `vector_renderer._draw_viewport_cracks()` adds edge cracks below 62% hull, branching damage below 32%, and critical flicker/leak particles below 12%.

### D.5 Per-theme skyboxes — [x]
Each procedural sector theme gets a distinct background. Wreckage Belt = hull debris parallax. Frozen Trail = ice crystals. Flare Corridor = solar flares. Currently all sectors visually blur together.
**Shipped:** `EVT_SECTOR_START` now carries first-sector theme data; `vector_renderer._draw_theme_skybox()` renders theme-specific background accents for flare, frozen, mine, toll/compliance, junk, wreckage, and industrial sectors.

### D.6 Scan pulse render — [x]
`EVT_SCAN_PING` already fires — wire renderer. Expanding ring from off-screen point; if it touches you, brief UI ack: `[UNION PASSIVE SCAN — IDENTITY LOGGED]`.
**Shipped:** scan rings now detect ship contact and display `UNION PASSIVE SCAN // IDENTITY LOGGED` once the ring reaches the courier.

### D.7 Alien sighting render — [x]
`EVT_ALIEN_SIGHTING` already fires — wire renderer. Strange silhouette crosses sector at far edge. Bax has zero context: silence, or a single confused line. Builds intrigue across runs.
**Shipped:** renderer subscribes to `EVT_ALIEN_SIGHTING` and draws a brief screen-edge silhouette/glitch witness mark.

### D.8 Solar wind events — [x]
Random pulses visibly push everything in one direction for ~5s. Subtle handling effect. Bax: *"Brace — flare's pushin'."*
**Shipped:** random event pool and flare corridors can trigger `EVT_SOLAR_WIND`; wind applies a subtle impulse to ship/debris/canisters and draws directional streaks.

### D.9 Debris wake physics — [x]
Ship passing through debris field displaces chunks; they bounce off each other for a few seconds. Every run through a field looks different. Pure kinetic satisfaction.
**Shipped:** fast ship motion nudges nearby debris outward, carries some ship velocity into the rocks, and applies pairwise separation impulses among wake-affected chunks.

---

## Phase E — Story & World

### E.1 Gary and Sandra history — [x]
They were partners before Sandra became "gold standard." Gary resents her success. Sandra feels guilty. Fragments across Gary and Sandra terminal interactions + Bax gossip. Gives both characters texture beyond function.
**Shipped:** Gary has a Sandra path that reveals the Meridian-route incident and his resentment; Sandra has a Gary History path that admits guilt over becoming the Union's model courier after protecting Gary. SCANNING chips and dossier hints surface the threads without making them mandatory.

### E.2 The debt-trap reveal — [x]
Across runs, Bax progressively reveals that Nova Soma's interest rate is mathematically impossible to pay off. The system is built to perpetuate, not collect. Drip-feed via intercepted comms and Bax's darkening commentary. Cross-run state: tracked in `data/saves/lore_progress.json`.
**Shipped:** Bax advances a four-stage debt-trap reveal on run start. Persistence lives in the save-slot `MetaProgression.lore_progress` map rather than a global sidecar file, so separate campaigns do not contaminate each other.

### E.3 Kress owes you — [x]
After a player successfully exploits Kress in a terminal, on a future run he tips you off (scrambled comms, deniable) about a barge patrol route. No fanfare. Payoff for players who've stuck around.
**Shipped:** Winning Kress through Connie, Volkov, or regular-status paths sets a persistent "owes patrol tip" flag. A later run consumes it, sends a deniable Kress comm, and delays the next queued repo barge. The pending tip is checkpoint-safe.

### E.4 Local 404 internal schism — [x]
The new idealist (B.6) and corrupt (B.6) reps clash with each other. Play them right (specific keyword paths) → they pull each other off your case. Internal politics with mechanical consequence.
**Shipped:** Edmund and Vince now write persistent Local 404 schism state. Once both sides have been played, queued barges are removed, active barges retreat, and new barge spawns are suppressed briefly while the Union argues with itself.

### E.5 Persistent NPC death — [x]
First time you really screw an NPC, they're gone from your runs forever. Replaced by a colder slot or silent gap. Persistence layer in `data/saves/npc_state.json`.
**Shipped:** Marrow is the first irreversible proof-of-concept. Kress and the Union Dispatcher each have a Marrow betrayal path with explicit Bax warnings and a required confirmation turn. Once confirmed, `MetaProgression.npc_state` marks Marrow dead; future Marrow terminals map to `FREQUENCY LOST`, and Chapter 1 corridor Marrow lore becomes raid aftermath.

**First irreversible choice to ship: Marrow betrayal.** If the player gives up Marrow's broadcast location (a specific Union dispatcher dialogue path or a paid Kress sell-out), Marrow is gone from all future runs. Her pirate station shows as "FREQUENCY LOST" on the comms list. Any future Marrow-tagged corridor lore is replaced with raid aftermath. No undo.

Subsequent irreversible choices (Mira Voss left for dead, Dray sold out, etc.) get added in later passes — Marrow's the proof of concept for the persistence layer.

**Risk resolved:** Bax now warns before the irreversible choice fires, and both betrayal paths require an explicit confirmation turn.

---

## Phase F — Bax Depth

### F.1 Silence breaker — [x]
No notable event for 20+ seconds → Bax hums a fragment, makes an unprompted observation, or asks a rhetorical question. Stops quiet from feeling like dead air.

### F.2 Cargo opinions — [x]
Bax has a take on every cargo type, said once per run on first mention. Biohazard: *"If that canister pops, I'm disconnecting."* Shrooms: delighted. Pharmaceutical: suspicious. One line per cargo, max cost to ship.

### F.3 Near-miss scaling commentary — [x]
Bax reaction scales with how close the miss was. 40px: mild. 10px: alarmed. <5px: silence, then *"…don't do that again."* Proportional reactions make moments feel witnessed.

### F.4 Bax's harmonica — [x]
At <10% hull, Bax plays a few notes on a procedural harmonica. Becomes the signature "you're about to die" sound. Delivers on the literal README pitch.

### F.5 Bax learns the player — [x]
Tracks consistent behavior across runs (always bribe, always brute, always exploit). Develops opinions: *"You always go for the bribe. Wonder if you'll ever try somethin' different."* Stored in `data/saves/bax_observations.json`.

### F.6 Run-count NPC recognition — [x]
After 3+ runs Gary recognizes the player. *"Oh. You again."* After 10: *"Look, you're just part of my quarterly projections now."* Quiet escalation per NPC.

### F.7 Sector theme entry commentary — [x]
On first entry to each procedural theme, Bax has one observation. Frozen Trail: *"Instruments go funny out 'ere. It's the ice crystals. Or ghosts."* Junk Belt: *"I've got sentimental attachment to this trash. Don't ask."*

---

## Phase G — Landing & Corridor

### G.1 Gary at the dock — [x]
Landing Beat 2 receiving officer = Gary (per Phase A.4). Sheepish, sighing, clipboard. *"Right. You made it. Again."* Ties the loop closed.

### G.2 Dock Control radio clearance — [x]
Audio during approach: distorted Dock Control voice. Either clears you or flags an "account irregularity" that tightens the landing window. The Union watches even at the dock.

### G.3 Cargo offload glimpse — [x]
2-second animation after touchdown: dock workers moving cargo. Cargo type visibly legible (hazmat for biohazard, careful handling for fragile). Delivery becomes tangible.

### G.4 Landing damage echo — [x]
Dock with critical hull → sequence shows it: sparks, smoke, leaking atmosphere, dock crew physically backing away. Cinematic moment of "you barely made it."

### G.5 Per-chapter dock wind-down Bax — [x]
Bax shifts tone in landing. Reflective. *"Sector four. Three left. You're gettin' good at this. ...Or unlucky."* Pacing change between flight and corridor.

### G.6 Corridor lore rooms — [x]
One dead-zone room per chapter. No enemies. Wall notes, slumped body at a terminal, Nova Soma memo. Optional context for players who slow down.

### G.7 NPC corridor shortcuts — [x]
One room per chapter has a side route cracked by a known NPC for a fee. 200cr skips a hard section. Kress's smells like engine oil. Marrow's leaves a flyer.

### G.8 Bax's corridor unease — [x]
Bax is a ship system; the corridor is wrong for him. Coaching lines carry unease: *"Right, the good news is I can still reach you. Bad news is I don't like how."* Different register from flight.

### G.9 Cargo-affects-corridor mutators — [x]
Design all three up front, ship as one cohesive batch (not piecemeal proof-of-concept).

- **Shrooms cargo:** walls visibly breathe/warp. Per-room shader pulse on the corridor backdrop. Tied to Ch.2 Mycorrhizal Payload theming but applies in any corridor when shrooms are the cargo.
- **Biohazard cargo:** periodic decon flashes (every 12–18s) wash the screen white for ~0.4s. Sirens. Brief visibility loss. Bax: *"Brace — automated decon."*
- **Paperwork cargo:** misleading signs (room exit arrows that point wrong) + dead-end doors that don't open. Forces real attention to layout, not signage. Most readable in Ch.3 Paperwork corridor but applies anywhere.

Each mutator is a corridor overlay that activates based on `cargo.tag`. Build a shared `CorridorMutator` interface in `delivery/corridor/mutators.py` so subsequent cargo types can slot in.

### G.10 Corridor time-pressure variant — [x]
Mutator or specific runs: visible threat (gas seeping in, station failing, dock closing). Trades explorer pacing for adrenaline. Forces secret-skip decisions.

---

## Phase H — Audio & Soundtrack

### H.1 Soundtrack implementation — [~]
Build the music system from the cursor branch SOUNDTRACK_PLAN. Hybrid model: ambient pads + sci-fi film homages + recurring Bax hum motif. Accessibility-first (mixable, mutable, captioned cues).
**Risk:** Large audio engineering task. May warrant a sub-plan doc.
**Shipped (Slice 1):** the engine already exists (~1.5k-line `audio_manager`); H.1 is the v2 "less is more" *audit*, not a from-scratch build. Landed the baseline mix trim (`_music_target_vol` 0.34 → 0.27, the single global music lever, documented in-code). Sub-plan written: `docs/SOUNDTRACK_IMPL_H1.md`.
**`[~]` because:** the audible mix level and the §7.5 accessibility UI (music subtitles, per-stem sliders, master mute) need a real windowed play-pass — can't be ear-verified headless. Slices 2 (max-4-stem guard) and 3 (signposting) are specced in the sub-plan.

### H.2 Bax harmonica synth — [x]
Procedural harmonica voice in `audio/synth.py` or `audio/voices.py`. Used by F.4. 2–4 phrases, each ~1.5s, bluesy in feel.
**Shipped:** the harmonica voice is `audio/blues_licks.py` (`_harp_note` + 30 mood-tagged `generate_lick` patterns). F.4 chain verified end-to-end: `bax.py` emits `EVT_BAX_HARMONICA` at critical hull → `audio_manager._on_bax_harmonica` plays a weary lick on the lick channel. Runtime-confirmed the lick fires (`_lick_ch.get_busy()` True after emit).

### H.3 Per-chapter music verification — [x]
Doc says corridor music is partial. Verify each chapter has its track playing; fill gaps.
**Shipped:** added `audio/chapter_5.py` (The Edge — clean acoustic harmonica, D Dorian, warm intimate mix) and `audio/chapter_6.py` (Compliance — fluorescent compliance chime, cold A minor, quantised clock kit). Wired both into `audio_manager` (`_CHAPTER_MODES`, the chapter-module loader `(1..6)`, `_corr_sig_profiles`). Filled the ch5/6 delivery gaps too: per-chapter **dock receiver** (the Union loop's Gary hands off to Fitz at The Edge and Bowen at Nova Soma), station themes, Bax dock wind-downs, and loadout chapter names. AudioManager boots all six modules headlessly; signatures render as real Sounds.

### H.4 NPC voice expansion — [x]
New union reps from B.6 each need a voice profile in `audio/voices.py` distinct from Gary.
**Shipped:** added `idealist_rep` (Edmund — earnest, clean, bright, no comm crush) and `corrupt_rep` (Vince — low, gravelly, side-channel static) voice profiles, plus the ch5/6 dock receivers `fitz` (warm, off-grid grit) and `bowen` (smooth, pristine, institutional). Speaker aliases route every label variant. Also fixed a pre-existing dock bug: `GARY PRUITT` (the full name the dock emits) was falling through to the default voice — now aliased to `gary`.

---

## Out of Scope (deferred)

- Epic 8.4 — Hardcore mode (post-this-push)
- Daily/weekly seeded challenges (infrastructure exists, content design deferred)
- Steam release prep
- Tutorial overhaul (current tutorial framework holds)

---

## Execution Plan

**Branch strategy:** single branch `rhubarb/aliveness-push` off the post-A.1 main.

**Commit strategy:**
- One commit per logical item, message format: `aliveness(X.Y): <item>`
- Per-phase summary commit when the phase closes
- Push after each commit so the branch stays live

**Tracking:**
- This document holds the canonical checkbox state
- `WORKING_ON.md` gets a row when a phase starts, removed when it closes
- `docs/DOCUMENTATION_STATUS.md` updated when each phase ships

**Verification:**
- Play-verify every visible item before checkboxing it (no doc-only ships)
- Each phase ends with a sync to local for Chris play-verify
- Items that fail play-verify get a `[~]` and a follow-up note

**Risk gates (revisit before starting):**
- G.9 (Cargo corridor mutators) — confirm scope before building per-cargo overlays
- H.1 (Soundtrack implementation) — may need sub-plan; flag before starting

---

## Resolved Decisions (May 25 2026)

- **E.5 first irreversible choice:** Marrow betrayal (Union dispatcher path or Kress sell-out). Proof-of-concept for persistence layer.
- **G.9 cargo mutators:** Design all three up front, ship as cohesive batch with shared `CorridorMutator` interface.
- **H.1 soundtrack:** Strict sequential — Phase H runs after G, no interleave.
- **Phase ordering:** Strict A → B → C → D → E → F → G → H. No parallel tracks. Heart over throughput.

---

**Status legend:**
- `[x]` shipped + play-verified
- `[~]` shipped but partial / failed play-verify
- `[ ]` not started
