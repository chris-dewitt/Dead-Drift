# DEAD DRIFT — Improvement Plan

**Milestone:** Steam Next Fest  
**Audience:** Dead Drift implementation team  
**Scope:** Pre-Next-Fest polish pass — flight feel, sector variety, the Mario-courier corridor overhaul, terminal polish, and Bax fleshed out as a real asset.  
**Last status pass:** May 2026 (code review + checkbox audit)  
**Companion:** `docs/DOCUMENTATION_STATUS.md` — stale docs, team priorities, resolved decision log

> **How to read this doc.** Eight themed epics plus **Phase 0** (trust fixes). Checkbox legend: `[x]` done · `[~]` partial · `[ ]` not done. Items marked `[~]` have notes inline — read before re-implementing. Design forks (theme order, landing Beat 2, MAX_VELOCITY) are resolved; see `DOCUMENTATION_STATUS.md`.

---

## Completion summary (May 2026)

| Epic | Done | Partial | Open | Notes |
|------|------|---------|------|-------|
| **Phase 0** — Trust fixes | 5 | 0 | 0 | Shipped: controls/trust blockers closed |
| **1** — Code hygiene | 8 | 2 | 0 | All Epic 1 items shipped — font cache + NLTK lazy bootstrap closed; minor `[~]` items remain inline |
| **2** — Flight feel | 7 | 0 | 0 | Flight-feel pass complete |
| **3** — Sector variety | 3 | 3 | 0 | Themes drive hazards; collapsing well + debris cloud now also wired from `SectorLayout.hazards` |
| **4** — Corridor | 7 | 2 | 0 | Framework shipped; black wipe + `ENTERING:` caption + end-card stats + per-chapter corridor music live |
| **5** — Landing | 2 | 1 | 0 | Docking graphics shipped; end-card hook closed via Bax's Records |
| **6** — Terminal polish | 8 | 0 | 0 | Complete: keystrokes, portraits, backdrops, outcome beats, chips, dossier, market, and cargo dialogue |
| **7** — Bax | 2 | 1 | 1 | Hull-glow portrait + pitch tiers + reference past runs live; harmonica play-along open (see Epic 11) |
| **8** — Meta replay | 4 | 0 | 0 | Stepped death + Bax's Records (8.3) + cargo carousel (8.2) + HARDCORE variant (8.4) all shipped |
| **9** — Award push (see `NEXT_PUSH.md`) | 3 | 1 | 18 | 9.2 CRT visual overhaul + 9.3 popup gate + Nova Soma dossier parity shipped; 9.1 NPC cross-refs partial |

**Plus from `NEXT_PUSH.md` (this push, May 25 2026):**
- Playtest backlog closed: barge hit-stagger + harpoon flash visibility, two new union reps (Idealist Eddie + Corrupt Vinny), NPC keyword normalization (universal `fuck off` easter egg, Felix gossip path, Dray gripe + standardised BRIBE label, Krellborn extended threat keywords + harder filler).
- Epic 11.1c — Bax harmonica heal session shipped (H-key in flight, +5 hull over 6s, rotation lock, barge-proximity gate).
- Epic 13.1 — money source labels on every `EVT_DEBT_UPDATE` (HUD floater shows `+800 cr · SLINGSHOT`, etc.).
- Epic 10.4 — corridor decay layer (deep parallax, numbered/cracked panels, scratched Nova Soma branding, floor wear, pipe drips, per-room directional lighting).
- Epic 14.1 — boss-room set pieces (Gary's den / mycelium chamber / compliance tribunal / quantum observation deck).

**Rough overall:** ~78% complete · ~13% partial · ~9% not started (by checkbox count).

---

## Team priorities (Chris — May 2026)

Tracked here and in `docs/DOCUMENTATION_STATUS.md`. These override epic list order until closed.

| Priority | Epic / Phase | Checkbox |
|----------|--------------|----------|
| All NPC portraits incl. Inspector Holt | Phase 0 + Epic 6 | [x] |
| Thruster stops working (overheat trap) | Phase 0 + Epic 2 | [x] |
| ESC leaves the market | Phase 0 | [x] |
| Improve market graphics | Epic 6 / shop polish | [x] |
| Improve docking graphics | Epic 5 | [x] |
| Cargo-specific dialogue for all NPCs | Epic 6 / terminal polish | [x] |
| Terminal outcome reveal visual pass | Epic 6 / terminal polish | [x] |
| Terminal keyword chips reflect known exploits | Epic 6 / terminal polish | [x] |

---

## Phase 0 — Trust Fixes (do before Epic polish)

**Goal:** Remove bugs that make the game feel broken. Sourced from May 2026 playtest + code review.

### 0.1 Thruster overheat trap — [x]
`ship/modules/thruster.py`: heat rises while module is powered (not only while thrusting). At 100° → `force = 0` with **no recovery** while thruster stays active. `LifeSupport.heat_absorption` never applied in `SignalChain`. No HUD heat readout.

**Fix direction:** Wire heat absorption · heat only on thrust · cooldown while powered-but-idle · HUD bar + Bax first-overheat line.

**Shipped May 2026:** Thrusters now heat only while actually firing, life support shares heat absorption through `SignalChain`, overheated thrusters recover after cooling, HUD shows thruster heat, and Bax fires a first-overheat warning.

### 0.2 Shop ESC opens pause instead of leave — [x]
`core/game.py`: `_PAUSEABLE` includes `SHOP`; ESC hits `_pause_game()` before `ShopScreen.handle_key()`. Shop already maps ESC → leave.

**Fix direction:** Route shop ESC before pause handler, or exclude `SHOP` from pause-on-ESC.

**Shipped May 2026:** Shop ESC is routed to `ShopScreen.handle_key()` before pause handling.

### 0.3 Missing NPC portraits (Inspector Holt, Relay-7 Felix) — [x]
Previously, `terminal/npc_portraits.py` had no keys for Holt or Felix, so both fell through to `_unknown` (`?`).

**Fix direction:** Add keys, vector busts, backdrops matching existing CRT portrait pipeline.

**Shipped May 2026:** Inspector Holt and Relay-7 Felix now have portrait keys, procedural busts, and dedicated CRT backdrops.

### 0.4 Ice field thrust penalty unwired — [x]
`antagonists/ice_field.py`: `thrust_penalty` (30%) defined; only slick acceleration applied.

**Shipped May 2026:** Ice fields now apply the 30% thrust penalty to the ship for the next flight input tick while the ship is inside the zone.

### 0.5 Remove stale `SHOP_SECTORS` in `roguelite/shop.py` — [x]
Dead constant `{3, 6}`; live config is `settings.SHOP_SECTORS = {1, 3}`.

**Shipped May 2026:** Removed the stale local constant and pointed shop documentation at `config.settings.SHOP_SECTORS`.

---

## Locked design decisions (decisions log)

These are the directional answers backing this plan. Don't re-litigate — implement against them.

- **Format:** master Markdown spec (this doc) + a stack of GitHub issues, one issue per epic, linking back here for the per-item detail.
- **Granularity:** 8 themed epics.
- **Priority:** no labels — list order is the order.
- **Acceptance criteria:** self-scoped by the implementing dev.
- **Audience context:** team is fluent in the GDD — no preamble per ticket.
- **Code refs:** implementation-agnostic. Line numbers cited only when needed for disambiguation.
- **Stale `dead-drift/` directory:** confirmed safe to delete. **Done May 2026.**
- **Refactor depth:** keep `core/game.py` intact for now (no full state-controller refactor); land everything else.
- **Three-body gravity:** implement mutual attraction between wells.
- **NLTK bootstrap:** lazy, on first terminal open, with a splash.
- **Determinism:** thread RNG through `procedural.py` so seeded runs are possible later.
- **`MAX_VELOCITY` policy:** soft drag above cap, not a hard clamp. **Locked at 280 px/s** (May 2026). Slingshot overdrive cap = **420 px/s** (1.5×).
- **`PlayerShip.reset()`:** clear chain slots 2–5 on reset.
- **Sector variety:** wire all 5 existing hazards; add 6 new obstacle types; 8 themes in pool; each chapter has a curated set-piece signature. Do **not** overwhelm the player — the rule is "every sector feels different," not "every sector is hostile."
- **Slingshot reward:** all three — UI floater + credit bonus + 2-second over-cap overdrive window.
- **Tether snap feedback:** both diegetic (tether line glow) and discrete (SNAP CHARGE bar).
- **Tutorial reach:** extend to `clone_count ≤ 3`.
- **Death penalty scaling:** stepped (sectors 1–2 = current, 3–4 = 1.5×, 5 = 2×).
- **Cargo damage propagation:** frame baseline + shop dampener stacks on top.
- **Chapter replay:** cargo dossier carousel from main menu (visual cards, best run stats).
- **NLP exploit dossier:** subsection of a "Bax's Records" main-menu screen.
- **Adaptive final-sector difficulty:** hull% > 70 at sector 5 entry → spawn extra barge; otherwise default load.
- **Bax draft:** write ~12 lines per new context (~100 lines total). Drafted in `docs/BAX_VOICE.md`.
- **Bax voice expansion:** all modes — strict-match + darker panic + manic glee + corridor coach.
- **Bax portrait glow:** color gradient (hull-bar palette) + diegetic deterioration (eyes wide, scan glitch, antenna sparks).
- **Threat-level music layer:** add a low harmonica drone that fades in within 320 px of a barge (uses existing `EVT_BARGE_NEARBY`).
- **North-star metric:** each chapter feels mechanically distinct on first playthrough AND replay rate after campaign clear is non-zero.
- **Next Fest demo focus:** all four headline pillars must ship — corridor overhaul, sector variety, control feel, terminal & cockpit polish.

---

## Epic 1 — Code Hygiene & Performance Pass

**Goal:** Land every cheap, high-confidence code fix so subsequent work isn't built on rot. Pure infrastructure — no design risk.

### 1.1 Delete the stale `dead-drift/` directory — [x]
The `/dead-drift/` subtree is a ~3,500-LOC near-duplicate of the live root, including an older `main.py` whose NLTK bootstrap uses the broken pre-`punkt_tab` paths. Nothing in the live game imports it. **Delete the entire directory.** Pre-flight: run a project-wide grep for any string referencing the path (build scripts, CI configs, README links) and clear them before the rm.

### 1.2 Font caching helper — [x]
Originally 200+ `pygame.font.SysFont(...)` calls lived inside per-frame draw paths in `core/game.py` (with smaller pockets in `terminal/terminal.py`, `delivery/delivery_sequence.py`, `roguelite/shop.py`, `renderer/cockpit_renderer.py`, `roguelite/loadout_draft.py`, `delivery/platformer.py`, `delivery/obstacles.py`, `play.py`, `ship/hud.py`). Each call was a font lookup; at 60 FPS, this was hundreds of redundant constructions per second.

Land a single `Game._font(size: int, bold: bool = False, italic: bool = False)` helper that memoizes by `(size, bold, italic)`. Route every existing `pygame.font.SysFont("monospace", …)` through it. Keep the API tight — one helper, used everywhere.

**May 2026:** `core/text.py` `get_font()` + `install_font_patch()` exist; `roguelite/shop.py` has local cache. `core/game.py`, `delivery/delivery_sequence.py`, and others still call raw `SysFont` in draw paths.
**Phase 1 (May 25 2026):** `install_font_patch()` now called from `play.py` `main()` ahead of any `SysFont` lookups, so the patch covers every draw path — shipped.
**Phase 3 (May 25 2026):** Direct `get_font()` adoption swept across every
hot draw path. `core/game.py`, `delivery/{platformer,obstacles,delivery_sequence}.py`,
`delivery/corridor/{base,elements,chapter1..4}.py`, `terminal/{terminal,npc_portraits}.py`,
`renderer/{vector_renderer,sci_fi_ui,cockpit_renderer}.py`, `ship/hud.py`,
`roguelite/{loadout_draft,shop}.py`, and `play.py` all now call
`from core.text import get_font` instead of `pygame.font.SysFont("monospace", ...)`.
`core/text.get_font()` gained an `italic=` flag so the three italic
call-sites adopt it cleanly. `roguelite/shop.py`'s local
`_FONT_CACHE` dict is gone; the helper now defers to `get_font()`.
The legacy comment in `core/game.py:55` is the only remaining
`SysFont` mention in the production tree, and `tests/test_font_cache.py`
asserts no real call sites linger.

### 1.3 Event bus fixes — [x]
`core/event_bus.py` has two latent issues:
- `_listeners` is a `defaultdict(list)` — calling `bus.emit("never_subscribed")` creates a permanent empty-list entry. Use a plain `dict` with `.get(event, ())`.
- The dispatch loop iterates `_listeners[event]` directly. A callback that unsubscribes itself (or another listener) during dispatch will skip an entry. Snapshot the list before iterating.

### 1.4 Subscriber lifecycle helper — [x]
Every renderer / manager / Bax / audio system subscribes in `__init__` but never unsubscribes. Today that's latent because `Game` constructs once — but `RunManager.start_run` and `_dev_start_flight` both partially rebuild state and would cause double-fire if either ever spun up a fresh `RunManager` or `VectorRenderer`. Introduce a tiny `Subscriber` mixin (or context manager) that tracks owned subscriptions and exposes `unsubscribe_all()`. Adopt across all current `bus.subscribe(...)` callers.

**Phase 2 (May 25 2026):** `Subscriber` mixin added to `core/event_bus.py`. `Bax` and `CockpitRenderer` adopt it; all `bus.subscribe()` calls in those classes routed through `self.subscribe()` (43 calls in `Bax._wire_events`). Other subscribers can adopt as they're touched.

### 1.5 Procedural RNG threading (seeded-runs ready) — [x]
`roguelite/procedural.py:generate_sector` creates `rng = random.Random()` but then `_generate_gravity` uses module-level `random.randint`/`random.uniform`. The seeded `rng` is decorative. Thread it properly through every sub-helper so passing `generate_sector(index, difficulty, rng=...)` actually produces deterministic output. This unlocks daily/weekly seeded challenges later — no commitment to ship that feature now, just stop blocking it.

### 1.6 Gravity well spawn safety — [x]
`_generate_gravity` uses `(100, SCREEN_H - 100)` for y-bounds (should be `FLIGHT_H`), has no minimum well-to-well separation, and never checks distance from the ship's spawn point at `(SCREEN_W / 2, SCREEN_H / 2)`. On rare seeds the player materializes inside a force singularity. Fix:
- Use `FLIGHT_H` for y-bounds.
- Reject-sample well positions until each is ≥ 180 px from every other well.
- Reject-sample until each well is ≥ 220 px from the ship spawn.

### 1.7 `PlayerShip.reset()` chain rebuild — [x]
`reset()` does not touch `self.chain` beyond what it does today, so shop upgrades and ad-hoc installs in slots 2–5 silently persist across deaths and runs. Change behavior: on reset, **clear slots 2–5**. Keep slot 0 (LifeSupport) and slot 1 (Thruster) installed — these are baseline issue and are re-set by `apply_draft` anyway.

### 1.8 Squared-distance optimization — [x]
Replace `(a - b).length()` comparisons with `length_sq()` against `RANGE * RANGE` in:
- `run_manager._check_slingshot` (per-well, per-frame)
- `run_manager._check_proximity` (per-barge, per-frame)
- `physics/tether.py:Tether.update` (per-frame while tethered)
- `antagonists/repo_barge.py` distance checks against the ship

Don't bother below ~10 calls/frame paths; the rest aren't hot.

**May 2026:** Done in `run_manager` (slingshot, proximity), `physics/tether.py`, several antagonists. `repo_barge.py` ship-distance checks may still use `.length()`.
**Phase 1 (May 25 2026):** `repo_barge.py` `update()` + `_patrol()` ship-distance checks converted to `length_sq()` with squared constants — shipped.

### 1.9 Move `random` import to module top in `ship/loadout.py` — [x]

### 1.10 NLTK lazy bootstrap with splash — [x]
Today `main.py` blocks at startup downloading NLTK data with zero in-game feedback. Move the bootstrap behind a lazy load triggered on first terminal-open. While packages download, render an in-game splash overlay ("LINGUISTIC PROCESSOR INITIALIZING — STAND BY") with a brief Bax line: *"Right, give us a sec — the comms array's still warmin' up."* Boot to main menu instantly; defer the download.

**May 2026:** Shipped. `terminal/nlp_bootstrap.py` runs the four-package
download on a daemon thread; `main.py` no longer blocks at import (the
old `_bootstrap_nltk` is gone). `Game.__init__` calls
`nlp_bootstrap.start_in_background()` right after `pygame.init()` (only
if `already_present()` is False, so warm boots are zero-cost).
`Game._maybe_render_nlp_splash()` paints the green-amber `LINGUISTIC
PROCESSOR INITIALISING — STAND BY` card with the current package label,
a pending count, and a small spinner; first activation fires the
priority Bax line via `EVT_BAX_SPEAK`. The parser already degrades
gracefully so the player can still type while the bundle is in flight,
and the splash auto-clears once `is_ready()` flips. Tests cover the
public API, idempotent thread spawn, and the renderer wiring.

### 1.11 EpistemologicalShrooms passive growth bug — [x]
`cargo/epi_shrooms.py:update` grows `spore_level` purely on time (`+= dt * 0.018`), reaching max in ~55 seconds regardless of damage. The docstring claims damage drives it. Either:
- Remove time-based growth, make damage the sole driver, OR
- Keep time-based growth but document it explicitly as "pressure curve" — and ensure the doctring matches.

Pick one — devs's call. The current code lies about what it does, that's the only thing that matters.

**May 2026:** Resolved — dual driver (time pressure curve + damage) documented explicitly in `cargo/epi_shrooms.py` docstring.

---

## Epic 2 — Flight Feel & Physics

**Goal:** The ship feels heavier, more controllable, more like the GDD's "courier saddled with a rust-bucket" than a twitchy arcade craft. Slingshot becomes a satisfying skill move with real payoff. The three-body chaos the GDD promises actually exists.

### 2.1 Control tuning constants — [~]
In `config/settings.py`:
- `ROTATION_SPEED 200.0 → 240.0` (20% snappier turn rate)
- Reverse thrust multiplier (currently the hard-coded `0.4` in `ship/ship.py:_read_input`) → `0.6`
- `MAX_VELOCITY 440.0 → **280.0**` (locked May 2026 — death-spiral fix; was 380 in earlier plan draft)
- `THRUSTER_FORCE 205.0 → 175.0`

Net effect: less top-speed, slower acceleration, snappier rotation, stronger reverse — ship has weight but you have more say in where it points.

**May 2026:** Rotation 240, thrust 175, reverse 0.6, **MAX_VELOCITY 280** — all live in `settings.py`.

### 2.2 Soft drag above velocity cap (no more hard clamp) — [x]
The current hard clamp in `RigidBody2D.integrate` instantly drops speed back to `MAX_VELOCITY`. Replace with a soft-drag formula: when `speed > MAX_VELOCITY`, multiply velocity by `(1 - excess_pct * dt * decay_constant)` so the ship gently sheds excess speed over a half-second or so. Effect: slingshots and fuel-canister boosts can briefly punch through the cap without immediately being undone. See 2.4 for the slingshot interaction.

### 2.3 Three-body mutual attraction (the GDD promise) — [x]
`physics/gravity.py:ThreeBodySystem.update` is a `pass` with a TODO. Implement it. Each well exerts gravity on every other well at **~15% strength** of the player attraction, applied each tick. Wells drift slowly during a sector — not catastrophically — adding genuine variance to late-run sectors without becoming unfightable. Constraints:
- Cap relative well velocity at 30 px/s so they don't accelerate off-screen.
- Snap wells to a bounding box (margin from screen edges and the cockpit strip) — if a well would cross the boundary, bounce its velocity component.
- Wells never spawn inside each other (covered by 1.6); now they can't drift into each other either — a soft repulsion at < 80 px separation suffices.

### 2.4 Slingshot triple-reward (UI + credits + overdrive) — [x]
The slingshot is the game's signature skill move. Today it shaves 5s off the jump timer and emits `EVT_SLINGSHOT` for Bax. That's invisible. Make it pop:
- **UI floater:** when `EVT_SLINGSHOT` fires, draw a 1-second "FREE −5s" floater near the ship in slingshot-yellow. Pulsing chime.
- **Credit bonus:** +800 cr per clean slingshot. Reduce `meta.debt` via `pay_off`. Surface on the per-sector flash card (the card already has a `slingshots` field — show "+credits per slingshot" beside it).
- **Overdrive window:** for 2 seconds after slingshot, allow the ship's velocity cap to be **1.5×** `MAX_VELOCITY` (**420 px/s** at current tuning). Soft drag from 2.2 kicks in only above the overdrive cap. After 2 seconds, the cap returns to baseline and the drag pulls speed back down gracefully.

Stack visible: a clean slingshot = "yes you got the bonus" + "yes you get credits" + "yes the ship actually goes faster."

**May 2026:** Floater, +800 cr, 2s overdrive, and sector-flash credit breakdown are done. The clear card now shows slingshots as count x per-sling bonus = total recovered credits.

### 2.5 Tether-snap feedback (diegetic + discrete) — [x]
Currently the player has no sense of how close to `SNAP_VELOCITY` their lateral motion is — they just see the tether and hope.

- **Diegetic:** in `renderer/vector_renderer.py`, the tether line itself glows red → amber → green proportional to `lateral_speed / SNAP_VELOCITY`. At ≥ 1.0 it pulses bright green for one frame before the snap fires. Players learn the move visually.
- **Discrete:** small "SNAP CHARGE" bar drawn near the hull readout (HUD-tinted by hull-degradation rules), 0–100% fill matching lateral speed. Disappears when no tether is active.

Both. The diegetic version teaches, the discrete version confirms.

**May 2026:** Tether line color by snap charge — done. `SNAP CHARGE` HUD bar now appears only while a tether is active and fills from the same `lateral_speed / SNAP_VELOCITY` signal.

### 2.6 Adaptive final-sector difficulty — [x]
`run_manager._load_next_sector` always spawns an extra barge on sector 5 plus an immediate debris rock. Change to a hull-aware heuristic at sector-5 entry:
- `hull_pct > 0.7`: spawn the extra barge + extra debris (current behavior — earned punishment for healthy runs).
- `hull_pct ≤ 0.7`: spawn nothing extra — final sector ramps via barge intensity and timer pressure alone.

Result: runs that arrive at sector 5 fragile aren't curb-stomped; clean runs still get the gauntlet.

### 2.7 Tutorial reach — [x]
`TutorialManager` only constructs when `meta.clone_count == 1`. Bump to `meta.clone_count ≤ 3`. First-timers who die in 30 seconds will still see the hints on their second and third clones. (Don't add a main-menu "replay tutorial" option — keep it auto-driven so it doesn't bloat the menu.)

**May 2026:** `run_manager.py` uses `clone_count <= 3`. `tutorial.py` module docstring still says `== 1` (stale comment only).

---

## Epic 3 — Sector Variety & New Obstacles

**Goal:** Every sector in a run feels genuinely different. The Nova Soma corporate-renaming flavor text gets to mean something — when a sector says "OPTIMISED COMPLIANCE ZONE, formerly THE WIDOW'S CROSSING," the gameplay there is recognizable. Crucial constraint: **the player must not feel overwhelmed.** Variety, not density. Each sector picks one or two signature elements and leans into them.

### 3.1 Wire the five existing hazards — [x]
`SectorLayout.hazards` is generated each sector and read by `RunManager` (per-frame) and `VectorRenderer`:

- **`asteroid_field`** — `DEBRIS_COUNT × 1.6`, debris HP slightly higher (more shootable). Visual: denser dust haze, more drifting micro-particles in background.
- **`solar_flare`** — every ~22 seconds, a screen-edge solar flare warning pulses for 2 seconds, then a 4-second sweep across the sector. While the sweep is active: HUD scramble pulse (one second of glitch), gun fizzles 3× more often, Bax: *"Solar flare incoming. Yeah, ROMANTIC. Shield your eyes, the ship has none."*
- **`collapsing_gravity_well`** — one of the sector's wells has its `mass` ramp linearly from 800 → 3500 over the sector duration. Visual: the well's ring count grows, hue shifts toward red, rotation slows. Late in the sector this well is genuinely dangerous; early-game it's just spicy.
- **`debris_cloud`** — a slow horizontal drift of small non-damaging particles across the screen, persisting for the whole sector. Reduces visibility (chip away ~6% alpha from background star layer behind the cloud). Pure ambient — no damage. Sets a *mood*.
- **`toll_checkpoint`** — forces a mid-sector terminal pop at ~10 seconds in: a "TOLL AUTHORITY" gate that's a quick negotiation (uses existing terminal flow with a new NPC type — see 3.5 for the toll NPC sketch). Outcome impacts the rest of the sector: pay → free passage, talk down → free passage with grumbling, refuse / fail → barge spawns immediately on resume.

Lock: maximum **two hazards per sector**. The hazard count cap in `_pick_hazards` should be reduced from `1 + int(difficulty)` (currently scales up to 3) to **`min(2, 1 + (difficulty > 1.5))`** — i.e. one hazard at low difficulty, two at high. Difference-by-design, not chaos-by-default.

**May 2026:** Obstacle logic is theme-driven in `run_manager` for asteroid density / solar flare / toll, **plus** `_load_sector_obstacles` now also reads `sector.hazards` and instantiates `CollapsingGravityWell` and `DebrisCloud` when present. Both update each frame and the renderer pulls `run_mgr.debris_cloud` for the visibility overlay.

### 3.2 Six new obstacle classes — [~]

Wire as `antagonists/wreck.py`, `antagonists/dead_station.py`, `antagonists/trash_field.py`, `antagonists/mine_field.py`, `antagonists/ice_field.py`, `antagonists/comet_trail.py`. Each is a top-level renderable + collidable; each registers itself with the sector renderer and `RunManager` for per-frame update.

#### Space wrecks (`wreck.py`)
Three sub-types, each large enough to be a landmark (~120–200 px). Spawn 1 per sector at most when the sector theme is "Wreckage Belt" or "Industrial Graveyard" (see 3.3).
- **Blocker wreck** — pure obstacle. Vector outline of a dead freighter, broken hull plates. Collides for `DEBRIS_DAMAGE × 1.5`.
- **Explorable wreck** — has a 30 px navigable gap through the middle. Fly the gap and pick up 1 fuel canister or 1 hidden credit cache (+400 cr).
- **Interactive wreck** — has a single weak point (small bright vector circle). Shooting it 3 times triggers a side-encounter: 50/50 between a hidden NPC opening a brief comm ("courier — there's still someone alive in here, do you have med supplies?") and a payout (+1200 cr salvage rights).

Visual style: dim purple-grey vector outlines, **no fill**. The wreck reads as a silhouette; the gap on the explorable type glows faintly cyan.

#### Dead space stations (`dead_station.py`)
Larger than wrecks (~200–300 px). Usually static, but include a **rotating ring** sub-component that sweeps a 40-degree arc and collides for hull damage. Players must time their approach. One per sector max, ever. Spawn only on the "Industrial Graveyard" theme.

#### Trash fields (`trash_field.py`)
The trash sector. 30–50 small junk pieces drifting at low velocity. Each:
- Causes 2 hp chip damage on contact (light tap, not punishing).
- Can be shot — each kill grants +25 cr ("scrap salvage").
- 1 in 8 pieces is a "good salvage" piece (slightly larger, faint amber glow); shooting one grants +200 cr instead.

Pure flow-through experience: you can ignore the trash and eat chip damage, or weave through, or stop and farm. All three are legitimate strategies. Bax: *"Right, scrap sector. Don't laugh — last bloke I flew with retired on what he salvaged out 'ere. Briefly. Then he got murdered. By Local 404. ANYWAY."*

#### Mine fields (`mine_field.py`)
6–10 proximity mines per sector when present. Each mine:
- Inert until ship comes within 100 px.
- Then arms (visual: amber pulse, audible warning tick from `audio_manager`).
- Detonates 1.5 seconds later if the ship is still within 60 px. Deals `DEBRIS_DAMAGE × 2`.
- Can be safely defused by shooting it (bullet hit while armed = neutralize, +50 cr).

Teaches caution, rewards aggression.

#### Ice fields (`ice_field.py`)
A defined zone (about 300×200 px) where physics gets weird. While the ship is inside:
- Apparent thruster force reduced 30%.
- Drag is **negative** — ship slowly accelerates in the direction of current velocity (slick).
- Bax: *"Frozen comet trail — I can FEEL the ice on the hull. We're slidin' a bit. Steady on."*

Zone visualization: faint blue crystalline lattice overlay, slow-drifting ice motes. Spawn 1 zone in "Frozen Trail" themed sectors.

#### Frozen comet trails (`comet_trail.py`)
Linear streams of small ice fragments traveling perpendicular to the sector axis at moderate speed (180 px/s). 2–3 streams per sector when present, each a "lane" of ice that chip-damages the ship if hit. Players naturally weave between the lanes. Visual: streaming white-cyan trail with motion-blur tails.

**May 2026:** All six modules exist and spawn by theme. Wreck subtypes (blocker/explorable/interactive) — yes. Interactive wreck → hidden NPC comm — verify in `wreck.py` (payout path exists; full NPC comm may be partial). Ice **thrust penalty** shipped in Phase 0.4.

### 3.3 Eight sector themes — [x]

A theme is a coherent visual + obstacle + ambient mood preset. Pool of 8:

1. **Compliance Zone** — vanilla flight. 1–2 wells, baseline debris. Default if all else fails.
2. **Wreckage Belt** — 1–2 wrecks (mix of blocker / explorable / interactive), reduced debris count. Visual: drifting wreckage parallax in background.
3. **Industrial Graveyard** — 1 dead station with rotating ring, 1 wreck. No fuel canisters here (the place is picked over).
4. **Junk-Belt** — the trash sector. Trash field obstacle, no fuel canisters, no wrecks. Heavy use of brown-orange-amber palette in the background.
5. **Mine Strip** — mine field obstacle, very few debris rocks. Visual: amber warning beacons drifting in the background — abandoned hazard markers.
6. **Frozen Trail** — ice field + comet trails. Cyan palette shift. Bax explicitly notes the cold.
7. **Flare Corridor** — `solar_flare` hazard active. Sun-side parallax glow in the background. Visual: occasional orange flare bloom from off-screen.
8. **Toll Authority** — `toll_checkpoint` hazard. Visual: a corporate gate structure visible mid-sector (decorative). Otherwise mostly empty void — the encounter is the obstacle.

### 3.4 Chapter-tied signature themes — [x]

Each chapter draws 5 sectors from the 8-theme pool. Each chapter has a **signature set** so the chapters feel distinct in playthroughs and replays.

**Source of truth (May 2026 — Chris decision B):** `roguelite/procedural.py` → `_CHAPTER_THEMES`. Sector index 0 is always Compliance Zone.

| Sector | Ch.1 Acoustic Archive | Ch.2 Shrooms | Ch.3 Paperwork | Ch.4 Schrödinger VIP |
|--------|----------------------|--------------|----------------|----------------------|
| 1 | Compliance Zone | Compliance Zone | Compliance Zone | Compliance Zone |
| 2 | Wreckage Belt | Industrial Graveyard | Junk-Belt | Frozen Trail |
| 3 | Junk-Belt | Wreckage Belt | Toll Authority | Industrial Graveyard |
| 4 | Flare Corridor | Mine Strip | Flare Corridor | Wreckage Belt |
| 5 | Industrial Graveyard | Frozen Trail | Frozen Trail | Mine Strip |

Within a chapter, sector order is fixed (so a player on their nth Ch.1 run knows what's coming) but the layout within each themed sector is procedurally regenerated by Epic 1.5's seeded RNG.

### 3.5 New NPC: Toll Authority — [x]

For `toll_checkpoint` hazards in Epic 3.1. New NPC type in `terminal/npcs/toll_authority.py` (subclass `BaseNPC`). Personality: bored, jobs-worth, hates everyone but mostly hates Local 404 because they steal his quota. Patience meter is short. Outcomes:
- **Pay** (input contains a credit amount ≥ 1500): waved through. Lose the credits, gain free passage.
- **Sympathy** / **complain about Union**: 60% chance he waves you through grumbling (he hates the Union). 40% chance he gets bored and waves you through anyway.
- **Threaten / hostile**: immediate barge call. He notifies Local 404. Barge spawns on terminal close.

Brief — 20-second negotiation max. Keep him as a flavor break, not a chapter-anchoring NPC.

### 3.6 Sector intro card — [x]
When a sector loads (currently `EVT_SECTOR_START`), draw a 2-second sector-intro card in the upper-left:
- Sector theme name (e.g. "WRECKAGE BELT")
- Sector designation (existing — "POST-PROFITABILITY WASTE FIELD")
- Formerly designation (existing — "ST. ANN'S PASSAGE")
- One-line theme description ("derelicts drift here — fly with respect")

Fades out after 2 seconds. Reinforces the "every sector feels different" promise visually.

---

## Epic 4 — The Mario Corridor: Delivery Sequence Overhaul

**Goal:** This is the headline. Right now the delivery sequence is a flat platformer that exists. After this epic, the delivery is the **moment players look forward to** at the end of every chapter — a 2–3 minute set piece, fully themed, with branching paths, mini-encounters, Bax in your ear, secrets to find, and a destination "boss room" where the cargo handover happens. Each chapter gets its own bespoke corridor.

**See `docs/CORRIDOR_DESIGN.md` for the per-chapter design specs.** This epic is the structural framework that all four corridors share.

### 4.1 Restructure `delivery/` module — [x]

Today `delivery/delivery_sequence.py` (683 LOC), `delivery/platformer.py` (481), and `delivery/obstacles.py` (206) are tightly coupled and chapter-agnostic. Restructure:

- `delivery/corridor/__init__.py` — exposes `make_corridor(chapter: int) -> Corridor`.
- `delivery/corridor/base.py` — `Corridor` class: owns the scrolling camera, the courier sprite, checkpoint state, level tilemap, obstacle list, NPC list, secret list, music cue manager. Pure framework — no chapter-specific content.
- `delivery/corridor/chapter1_archive.py` — content & layout for the Acoustic Archive corridor.
- `delivery/corridor/chapter2_shrooms.py` — Mycorrhizal biolab corridor.
- `delivery/corridor/chapter3_paperwork.py` — Government Office corridor.
- `delivery/corridor/chapter4_vip.py` — Schrödinger Hotel corridor.
- `delivery/corridor/elements/` — reusable element classes: `Platform`, `MovingPlatform`, `CollapsingPlatform`, `Hazard`, `NPCEncounter`, `Collectible`, `Secret`, `Checkpoint`, `StealthZone`, `BossRoomTrigger`.

Each chapter file is data-heavy — define the level layout as a list of element constructors at module level, plus chapter-specific subclasses where needed (e.g. `Chapter1JukeboxHazard`).

### 4.2 Core mechanics (shared framework) — [~]

The Corridor must support every one of these as first-class concepts:

- **Scrolling 2D camera** — courier sprite stays roughly center-screen as the level scrolls.
- **Length:** 2–3 minutes of gameplay. ~3 distinct "rooms" or "phases" per chapter, with a brief load-transition between (no asset load — just a black wipe and a "ENTERING: <ROOM NAME>" caption).
- **Checkpoints** — 2 per corridor. On death (which can happen — see hazards), respawn at last checkpoint. No life count; corridor is unmissable, but failure means restart from checkpoint.
- **Branching paths** — at one or two points per corridor, the level forks. One path is faster, riskier; one is longer, safer. Both reach the same destination.
- **Collectibles** — credits scattered as visible "credit chips" along both paths. Risky path always has more.
- **Secrets** — 1–2 hidden secrets per corridor. Off the main path. Each grants either a chunk of credits (+2500 cr) or a piece of lore-scrap (one-line piece of text that surfaces in Bax's Records, see Epic 8).
- **NPC encounters** — 1–2 mid-corridor NPCs per chapter. Each opens a brief mini-terminal (10–15 second turn) — same engine as the full terminal but condensed. Outcome can: give a bonus, unlock a shortcut, or fail and trigger a hazard.
- **Stealth segments** — 1 per corridor. A sweeping security camera or drone patrol; courier must wait in shadows / behind cover (cover objects in the tilemap). Caught = damage + retreat to last checkpoint.
- **Bax voice-over** — Bax narrates contextually throughout. Coach-mode commentary on jumps, panic on stealth-near-misses, glee on secrets. Lines drafted in `docs/BAX_VOICE.md` under "corridor" contexts.
- **Boss room** — last 10–15 seconds of every corridor: small "act" before the cargo handover. The contact NPC is present (Gary for Ch.1, the lab tech for Ch.2, the dispatcher for Ch.3, the hotel concierge for Ch.4). Brief exchange, money changes hands, cargo drops.

**May 2026:** Scrolling camera, checkpoints, branching, collectibles, secrets, NPC encounters, stealth zones, Bax lines — largely shipped. Black wipe + `ENTERING: <ROOM NAME>` caption now drive the room transition (`_start_wipe_out` / `_do_room_transition` in `delivery/corridor/base.py`). Mini-terminal UX may still need a polish pass.

### 4.3 Visual style (hybrid) — [~]

Open brutalist — the moment the corridor begins, it should feel continuous with the flight scene (same palette, vector line art, void-black background, neon accents). As the courier progresses deeper into the station, the style **progressively shifts** to more colorful, layered, almost cartoony. By the boss room, the visual language is fully "corporate sci-fi hellscape illustration" — saturated, dense, exaggerated character art (still vector-based, no sprite assets).

Implementation: each room's render style is configurable; the `Corridor` framework supports a per-room palette + line-weight + saturation curve. Room 1 is brutalist (current flight aesthetic), Room 2 is mid-shift, Room 3 (boss room) is full saturation.

**May 2026:** Per-room palettes in chapter files — yes. Full saturation shift in boss rooms — partial.

### 4.4 Courier avatar — [x]

The courier currently in `delivery/platformer.py` is a basic colored rect. Replace with a vector-drawn courier figure:
- Standing pose: rough humanoid silhouette with a courier satchel slung across the body.
- Running pose: simple two-frame animation (left/right leg).
- Jumping pose: knees up.
- Hit pose: brief stumble + amber flash.
- Stealth pose: crouched silhouette.

Vector-only, brutalist line work, ~36 px tall. Color: cyan accent ("our courier"). Match the ship's signature cyan glow so visual identity carries from flight to corridor.

**May 2026:** `renderer/sci_fi_ui.draw_courier_sprite` used by corridor framework.

### 4.5 Cargo silhouette — [x]
The cargo being carried is visible on the courier's back/shoulder. Each chapter's cargo is rendered as a distinct silhouette:
- **Ch.1 (Archive):** a crate full of vinyl/data spools sticking out the top.
- **Ch.2 (Shrooms):** a glass jar with bioluminescent contents (subtle hue pulse).
- **Ch.3 (Paperwork):** a stack of forms, comically tall, swaying as the courier moves.
- **Ch.4 (Schrödinger VIP):** a sealed crate with a small "?" decal — alive AND dead.

When the courier is hit, the cargo silhouette flashes. When the cargo takes a "real" hit (large hazard), the cargo silhouette visibly tilts/breaks (Ch.1 vinyl cracks visible, Ch.2 jar gets a crack, etc.). This is the diegetic version of the cargo damage system.

**May 2026:** Per-chapter silhouettes in `corridor/base.py`. Hit flash — partial; crack-on-big-hit — verify per chapter.

### 4.6 Corridor music — [x]
Each chapter's corridor has a unique audio cue track that plays only during corridor execution. The track is a longer, melodic blues-jazz piece (procedurally generated using the existing `audio/synth.py` infrastructure) themed to that chapter:
- **Ch.1:** distorted vinyl-warm bassline + dirty harmonica
- **Ch.2:** sparse off-kilter percussion with reverb-drowned synths
- **Ch.3:** typewriter percussion + steady marching bass
- **Ch.4:** lush hotel-lobby jazz, occasionally glitching

Music swells on entry, ducks during NPC dialogue, peaks in the boss room.

**May 2026:** Shipped. New events `EVT_CORRIDOR_ENTER`,
`EVT_CORRIDOR_BOSS_ROOM`, and `EVT_CORRIDOR_EXIT` fire from
`delivery/corridor/base.py` (entry on `Corridor.__init__`, boss-room
trigger on first BossRoomTrigger pass — idempotent — and exit on
`_finish()`). `AudioManager` allocates `_CORR_SIG_CH` (channel 30) and
schedules each chapter's `signature_instrument()` at a per-chapter
cadence + base volume profile (Ch.1 vinyl-warm harmonica every ~3.4s @
0.42, Ch.2 sparse bowed-saw every ~5.0s @ 0.30, Ch.3 typewriter march
every ~1.6s @ 0.36, Ch.4 hotel-lobby jazz every ~4.0s @ 0.28). Corridor
intensity drives volume + cadence: 0.5 on entry, 1.0 in the boss room
(~1.6× louder, 0.65× cadence). Voice ducking handles the dialogue duck
via the existing `_music_gain()` path. Tests in
`tests/test_corridor_music.py`.

### 4.7 Corridor scoring — [~]
At corridor completion, show a brief end-card:
- Time elapsed.
- Collectibles found / total.
- Secrets found.
- Damage taken.
- Bonus credits earned.

Roll these into the chapter's run summary and into Bax's Records (Epic 8).

**May 2026:** Star rating (1–3) plus full end-card stats (time, damage taken, collectibles found / total, secrets, bonus credits) render at corridor end — see `_render_summary` in `delivery/corridor/base.py`. Lore scraps from `Secret` pickups now route through `EVT_LORE_FOUND` → `MetaProgression.add_lore_fragment` and surface in **Bax's Records → LORE FRAGMENTS** (Epic 8.3).

### 4.8 Corridor jump locomotion bug — [x]
Player playtest note: in the corridor, jump currently reads like a vertical up/down hop from the same spot, which can leave the courier with no practical way to get off or across from that location. Jump should preserve normal horizontal movement and allow the player to leave the takeoff position, clear gaps, and exit platforms naturally.

**May 2026 implementation:** Normal horizontal movement remains active while airborne, and `SPACE` now detaches the courier from ladders into jump movement instead of re-grabbing immediately.

### 4.9 Corridor ladder exit / control recovery bug — [x]
Player playtest note: ladder movement has the same stuck-in-place feel as the jump issue. The courier can climb up/down, but cannot reliably get off the ladder onto nearby platforms; when reaching the bottom, player control can be lost or fail to return cleanly.

**May 2026 implementation:** Ladder capture now requires climb intent unless already climbing, horizontal input steps off ladders, and bottom dismounts restore grounded control instead of repeatedly recapturing the player.

---

## Epic 5 — Landing Sequence Overhaul

**Goal:** The moment after flight where the ship docks with the station is currently a brief animation. Make it interactive, cinematic, fun — something the player engages with rather than waits through.

### 5.1 Three-beat hybrid sequence — [x]

After the final sector clears (post-`EVT_RUN_END(success=True)` and Bax's "we did it" line), trigger the landing sequence — between FLIGHT and DELIVERY states.

The sequence has three beats, each with one input moment, totaling ~15 seconds:

**Beat 1 — Approach (5s):** The station looms into view from the void. The ship is still under the player's nominal control (thrust/rotate), but a "DOCK GUIDANCE LOCK" indicator pulses: align the ship's nose with the dock entrance within a 30-degree cone. Once aligned, the magnetic guidance "locks" and the ship is auto-piloted into the cone (player input transitions out smoothly). Cinematic camera pulls back to a wider angle as the station fills more of the screen.

**Beat 2 — Alignment (4s):** Ship approaches the dock at moderate speed. Two input beats:
- **TAP J — ALIGN THRUSTERS:** A small UI overlay appears with a target marker that drifts slowly across a gauge. Player must tap `J` when the marker is centered. Hit window: 0.6 seconds. Miss: hull takes 5 hp chip damage; the dock master grumbles audibly.
- **HOLD SPACE — RETRO BURN:** A "BURN" prompt with a fill bar. Player holds SPACE for ~1.2 seconds to bleed off velocity. Release too early: bounce into the airlock walls (10 hp damage, comedic Bax line). Hold too long: ship overshoots, has to back up (3-second time penalty, Bax mutters).

**Beat 3 — Touchdown (6s):** Pure cutscene now — the ship enters the airlock proper. Dock clamps swing in (vector animation), magnetic locks engage with a satisfying low thunk (audio cue). Ground crew silhouettes in the background, going about their business. Camera holds on the ship for two seconds while Bax delivers a chapter-appropriate landing line. Fade to corridor start.

**May 2026:** J alignment gauge (tap **J**) + SPACE retro burn (~1.2s hold) — implemented per Chris decision A.

### 5.2 Performance scoring — [x]
- Both Beat 2 inputs hit perfectly: "PERFECT DOCK — courier rating +1" floater, +500 cr bonus.
- One hit, one miss: standard touchdown.
- Both missed: "ROUGH LANDING — dock fees deducted" -200 cr.

Surface this in the corridor end-card and Bax's Records.

**May 2026:** +500 / −200 cr and Bax events wired. Corridor end-card + Records — partial / blocked.

### 5.3 Station visual variety — [x]
Each chapter has a different station for the landing:
- **Ch.1:** Underground harbour — improvised cargo dock under a busy commercial structure.
- **Ch.2:** Sterile biolab outpost — clean white-blue facility on the edge of a planetary ring.
- **Ch.3:** Corporate compliance center — brutalist office building in low orbit. Visible Nova Soma logo.
- **Ch.4:** Luxury orbital hotel — gleaming spiral structure, well-lit, expensive-looking.

Each station is a vector illustration rendered procedurally — same constraints as the rest of the renderer (no sprite assets).

**May 2026:** Chapter-themed station names/colors plus distinct procedural station silhouettes are shipped: Ch.1 cargo harbour, Ch.2 biolab ring outpost, Ch.3 Nova Soma compliance slab, and Ch.4 luxury orbital hotel. Landing/beat-3 bay dressing also changes per chapter.

---

## Epic 6 — Terminal Polish

**Goal:** The terminal is mechanically great but visually & tactilely underweighted. Player input should feel weighty. NPC reactions should pop. Backdrops should breathe. Outcomes should land like a hammer.

### 6.1 Keystroke weight — [x]
On every printable keystroke in the terminal input:
- Soft click sound (low-pitched, distinct from typewriter blips that already play on NPC speech).
- 0.08-second amber pulse on the input line border.
- Tiny camera shake on the input box only (1 px offset for 1 frame).

On backspace:
- Higher-pitched click.
- Red pulse.

On ENTER (submit):
- Heavier click.
- Brief 0.2-second screen-edge amber bloom.

**May 2026:** Shipped. Printable keys, backspace, and ENTER now emit terminal-key events into `AudioManager`; the audio layer plays distinct low/high/heavy clicks, the input border pulses, ENTER blooms the screen edge, and the input box does a tiny 1px shake.

### 6.2 NPC portrait emotional swings — [x]
Today portrait disposition shifts are subtle. Crank them up:
- **Compliant / friendly:** portrait color saturates by 20%, brief soft glow, NPC may smile (cargo subroutines in `npc_portraits.py` per character).
- **Annoyed:** portrait dims 15%, scanlines get harsher, NPC visibly frowns or looks away.
- **Furious:** portrait shakes for 0.3 seconds on the trigger frame, color desaturates almost fully, scanlines tear violently, NPC's mouth becomes a thin line.
- **Exploited / paradox-frozen:** portrait freezes mid-blink, fragmenting glitch artifacts (the existing `_signal_overlay` glitch level can be cranked but isn't fully utilized).

Each NPC needs explicit per-disposition portrait variants — not just universal overlay treatment.

**May 2026:** Shipped. `draw_portrait` now receives explicit reaction/freeze hints from the terminal. Friendly/release states push the disposition into bright soft-glow variants, annoyed/furious states dim, frown, shake, and tear scanlines, and exploit/paradox/impound outcomes freeze or jitter the portrait with per-NPC accent overlays. Existing NPC-specific portrait disposition geometry is driven harder rather than replaced.

### 6.3 Ambient backdrop motion — [x]
Backdrops in `npc_portraits.py` are currently mostly static scenes. Each backdrop needs ≥ 2 ambient motion elements:
- Background NPCs walking past (silhouette at far distance).
- Flickering signs or readouts.
- Drifting steam / dust / data motes.
- Periodic camera microsway (1–2 px on a sine wave) — subtle, just enough to feel alive.

Constraint: nothing should be visually distracting from the focal NPC. Ambient = atmosphere, not focus competition.

**May 2026:** Shipped. Portrait backdrops now render through a subtle motion layer with per-NPC microsway, distant silhouette passersby, drifting dust/data motes, and small live readout flickers behind the bust.

### 6.4 Slim the keyword chip strip — [x]
`_SCAN_VOCAB` chips along the top of the terminal are currently dense — a wall of label text. Three changes:
- Show **max 4 chips at a time**. Cycle in/out as the player types.
- Chips representing already-discovered exploits (per VocabularyVault) render dim with a small "★" — they're known territory.
- Chips representing live possibilities render bright.

Result: the strip becomes a signal probe ("what's working right now?") rather than a cheat sheet ("here's everything").

**May 2026:** Shipped. `_live_scan` shows max 4 chips, RunManager passes Bax's `VocabularyVault` into terminals, discovered exploit paths render as dim chips with a small ★, and newly discovered backdoors are saved through the vault.

### 6.5 Outcome reveal beats — [x]
The final moment of every terminal — success or failure — needs a real beat:

- **EXPLOIT outcome:** screen fills with a brief data-stream cascade (vertical lines of garbage characters falling). Loud "GOT 'EM" stinger. NPC portrait freezes mid-expression. "TRANSACTION REROUTED — {amount} cr" overlays in big neon green for 1 second.
- **RELEASE outcome:** softer — portrait shifts to a resigned "fine, just go" expression, the comm channel visibly closes (terminal shrinks from screen), Bax delivers a satisfied line. "CHANNEL CLOSED — proceed" caption.
- **IMPOUND / failure:** harsh red overlay flash, klaxon chord, "TERMINAL TERMINATED" in bold red, portrait goes hostile-frozen. Cuts back to flight with a barge audibly spawning.
- **PARADOX outcome:** NPC visibly breaks. Glitch artifacts cascade across the portrait, dialogue cuts to static, screen flickers. "SYSTEM ERROR — proceed" caption. Bonus credits awarded.

Each outcome must feel distinct. Right now they all feel like "the terminal ended."

**May 2026:** Shipped. Terminal close now holds briefly for release, exploit, and impound outcomes; exploit gets a data-stream cascade and reroute caption, release gets a channel-close effect, impound/abort get a red terminal-failure flash, paradox crashes get their own corruption layer and `SYSTEM ERROR` caption, `AudioManager` plays distinct outcome stingers/klaxons, and portraits freeze or swing into outcome-specific expressions.

### 6.6 NLP exploit dossier (foreshadows Epic 8) — [x]
Add a footer in the terminal close screen: *"Bax filed your method. Review your dossier from the main menu."* This points players at the new Bax's Records screen (Epic 8.3) where their discovered exploits are catalogued.

**May 2026:** Verified. The terminal dossier panel shows the Bax footer after terminal close.

### 6.7 Black market graphics — [x]
Chris priority: make the mid-run market feel more like a place and less like a plain menu.

**May 2026:** Browse view now has physical stall dressing behind the vendor, item-specific hardware glyphs for each stock tag, affordability/readiness badges on selected cards, and render smoke coverage for the shop art helpers.

### 6.8 Cargo-specific NPC dialogue — [x]
Chris priority: every terminal NPC should react to what cargo the courier is carrying, not just generic run state.

Implementation direction:
- Extend terminal run context with cargo identity (`Acoustic Archive`, `Epistemological Shrooms`, `Sentient Paperwork`, `Schrodinger VIP`) plus cargo state where available.
- Add cargo-aware flavor lines for every existing NPC: Gary, Kress, Sandra, TK-9, Union Dispatcher, Insurance Adjuster / Morwenna, Toll Authority, Relay-7 Felix, Inspector Holt, Cargo Inspector, Pirate, and Underground DJ.
- Keep lines in each NPC's voice and mechanically harmless; cargo flavor should not change win/fail conditions unless a later design item explicitly calls for it.
- Include enough character/background texture in the new lines that cargo references feel authored rather than generic substitutions.

**May 2026:** Shipped. Terminal run context now includes cargo identity/integrity/state, and `BaseNPC` appends one authored cargo-specific flavor line per encounter for the full NPC roster.

---

## Epic 7 — Bax: Real Asset

**Goal:** Bax goes from "occasional commentator" to "the soul of the game." More lines, more contexts, more emotional range, a visible portrait that reacts to ship damage. Players should anticipate what Bax will say in the corridor the way they anticipate slingshots.

**See `docs/BAX_VOICE.md` for the full line bank, tone guide, and per-context drafts.**

### 7.1 Cockpit portrait hull-damage glow — [x]

Bax's portrait in the cockpit strip currently doesn't react visually to ship damage. Make it:

- **Color gradient mapped to hull%:** at 100–60% hull, ambient amber glow around the portrait. At 60–30%, glow shifts to orange + light pulse on each hull-damage event. At < 30%, glow becomes red + persistent flicker.
- **Diegetic deterioration on hits:** every `EVT_HULL_DAMAGE` event triggers a brief portrait reaction — eyes widen for 0.4 seconds, scanlines on the portrait glitch harder for 0.6 seconds, antenna sparks for 0.3 seconds. Repeated hits compound the glitch intensity (cooldown of 1.5 seconds before glitch resets).
- **At < 10% hull:** portrait holds a "panic" expression statically — eyes wide, mouth open, antenna fully sparking. Bax's voice pitch shifts subtly higher in the audio system (see 7.4).

**May 2026:** Shipped. `CockpitRenderer` subscribes to `EVT_HULL_DAMAGE`, drives an amber→orange→red ambient glow keyed on hull%, fires the eyes-widen / scanline-glitch / antenna-spark reaction with the 1.5s cooldown, and switches to a panic-glow flicker plus persistent antenna sparks under 10% hull. Voice pitch shift lives in 7.4 (`_play_voice_blip` reads hull% and selects from `BAX_PITCH_TIERS`).

### 7.2 New voice contexts (~100 lines drafted) — [x]

Twelve lines per context, drafted in `docs/BAX_VOICE.md`. Contexts:

- `sustained_fire` — player fires 5+ shots within 2 seconds. Manic-glee mode.
- `first_barge_kill_of_run` — first barge destroyed in the current run. Manic-glee.
- `first_kill_of_sector` — any obstacle destroyed in the current sector for the first time. Standard.
- `panic_under_10_hull` — hull falls below 10%. Vulnerable mode.
- `barge_destroyed` — every subsequent barge kill (not the first). Standard glee.
- `corridor_running` — passive coach mode during long stretches of corridor running.
- `corridor_jumping` — commentary on jumps (especially big jumps).
- `corridor_secret_found` — player triggers a hidden secret.
- `corridor_death` — player dies in the corridor (retries from checkpoint). Vulnerable mode.
- `dock_approach` — landing sequence Beat 1 starts.
- `dock_perfect` — both landing inputs hit cleanly.
- `dock_rough` — both landing inputs missed.

**May 2026:** Most lists in `bax/bax.py` with event wiring. **`first_kill_of_sector`** — flag set on barge kill, no dedicated line pool from `BAX_VOICE.md`.
**Phase 1 (May 25 2026):** `_FIRST_KILL_OF_SECTOR` 12-line pool added; `_on_barge_killed` now prioritizes run-first → sector-first → generic — shipped.

### 7.3 New voice modes — [x]

Bax's voice gets three explicit modes that nuance line selection:

- **Standard** — existing Cockney, sardonic-but-fond baseline. Used for ~60% of contexts.
- **Dark / Vulnerable** — drops the comedy register for genuinely raw moments (panic, corridor death, decanting). Lines are quieter, more direct. No quips, fewer self-references.
- **Manic Glee** — Bax visibly enjoys ship combat. Used for `sustained_fire`, `first_barge_kill_of_run`, `barge_destroyed`. Tone is unhinged-excited, lots of caps, lots of "OI MATE" energy. Pitch slightly higher.
- **Corridor Coach** — Bax in the player's ear during corridor runs. Less Cockney drift (he's focused), more direct commentary on the player's choices ("good jump — you saw that camera"). Pitch unchanged but cadence is faster.

Implementation: each line in the bank is tagged with mode. The `Bax` system picks lines weighted by current context's preferred mode.

**May 2026:** Modes described in `BAX_VOICE.md`; code uses context pools but not explicit per-line mode tags + pitch.
**Phase 2 (May 25 2026):** `_LINE_MODE` pool→mode dict in `bax/bax.py`. `speak()` emits `EVT_BAX_SPEAK` with mode payload. `AudioManager._play_voice_blip` applies effects per mode: `manic_glee` bumps the pitch tier up one, `dark_vulnerable` ducks volume to 0.72× — shipped.

### 7.4 Audio pitch shift — [x]
`audio_manager.py`'s Bax voice channel uses pre-built blips. Add a one-line pitch shift on the blip channel mapped to hull%: 100% hull = neutral pitch; < 30% = +5% pitch; < 10% = +12% pitch. Same effect Bax has when he's stressed in fiction — voice goes higher.

**Phase 1 (May 25 2026):** `audio/voices.py` now exposes `BAX_PITCH_TIERS = (1.0, 1.05, 1.12)` and `prebuild_bax_pitch_tiers()`. `AudioManager` prebuilds all three tiers and `_play_voice_blip` selects the right one based on hull% — shipped.

### 7.5 Bax line cycling without immediate repeats — [x]
Today `random.choice` can pick the same line twice in a row, which kills the illusion. Update `Bax._speak` to track the last 3 lines spoken per context and reject-sample to avoid repetition until those slots cycle out. Trivial change, large player-perceptible quality gain.

**May 2026:** `_no_repeat_pick()` used across contexts.

---

## Epic 8 — Meta-progression & Replay

**Goal:** The game gives players reasons to come back after their first campaign clear. Bax's Records becomes a curiosity hub. Chapter replay is a visual delight, not a checkbox.

### 8.1 Stepped death penalty — [x]
In `roguelite/meta_progression.py:apply_death_penalty`, scale `WRECKAGE_TOW_FEE` by sector reached at time of death:
- Sectors 1–2: current value (8000).
- Sectors 3–4: 1.5× (12,000).
- Sector 5: 2× (16,000).

`CLONE_FLUID_FEE` and `BASE_CLONE_DEBT` stay flat. Net effect: early deaths are recoverable; late deaths bite hard. Tracks the GDD's "the deeper you go, the more they own you" tone.

### 8.2 Cargo dossier carousel (chapter replay) — [x]

Replace the current "linear-list main menu" approach with a visual carousel:

- Main menu, after campaign clear, shows four "cargo dossier" cards in a horizontal carousel.
- Each card: vector illustration of that chapter's cargo, chapter title, "✓ Delivered" stamp, best run stats (fastest sector clears, total credits earned, secrets found, perfect docks).
- Selecting a card → loads directly into that chapter's loadout draft.

Cards for unfinished chapters render dimmed with a "??? — uncovered" stamp. Players see progress at a glance.

**May 2026:** Shipped. `renderer/cargo_carousel.py` paints a 5-card
horizontal carousel (focused card centred + flanking siblings scaled
+ alpha-faded). Each card draws the chapter cargo silhouette
(vinyl/biolab jar/forms/box-with-?), the `✓ DELIVERED` or
`??? UNCOVERED` stamp, deepest-sector / best-run-credits stats
pulled from `StatsTracker.career`, and the HARDCORE row when
applicable (Epic 8.4). Main-menu adds a `CARGO DOSSIERS` row that
unlocks after the first chapter clear. Key handler: `←/→` cycle,
`H` arms HARDCORE for the next run when unlocked, `ENTER` calls
new `RunManager.set_chapter_override()` and starts a fresh run on
the selected chapter, `ESC` returns to the main menu. Tests in
`tests/test_cargo_carousel.py`.

### 8.3 Bax's Records screen — [x]

New main-menu entry: **"BAX'S RECORDS"**. Opens a multi-tab interface:

- **Tab 1 — Clone Log:** clone count, total deaths, top causes of death (with the Bax-by-source quips spread across the page), debt history graph.
- **Tab 2 — Run Highlights:** total slingshots executed, total tether snaps, total barges destroyed, biggest single-run credit recovery, lowest hull% run-clear (badge), fastest sector clear.
- **Tab 3 — Vulnerability Database:** the NLP exploit dossier. Per-NPC entries showing which exploit keys the player has discovered (e.g. "GARY — BLEVINS ★ discovered Run 7"). Undiscovered exploits show as "???". Sourced from `VocabularyVault`.
- **Tab 4 — Lore Fragments:** scraps collected from corridor secrets (Epic 4.2). Each is a short paragraph — Bax's notes, fragments of Nova Soma internal memos, etc.

**May 2026:** Shipped. `renderer/records_screen.py` draws the manila-folder
file-cabinet view; `core/game.py` adds the `BAX'S RECORDS` row, a
`records` menu mode, and TAB / arrow / page-key handlers for navigation.
Tab 1 surfaces clone count, runs started/completed, deaths (estimated),
lifetime debt accrued / paid, and a chapter bar of deepest sector
reached. Tab 2 reads career + current-run rows from `StatsTracker`. Tab
3 lists every NPC from the `npc_logic` registry with their discovered
backdoors from `VocabularyVault` (undiscovered → `???`). Tab 4 paints
each lore scrap as a chapter-tagged card; pickup is wired through the
new `EVT_LORE_FOUND` event from corridor `Secret.try_collect`, which
`Game._on_lore_found` persists via `MetaProgression.add_lore_fragment`.
Smoke + persistence tests in `tests/test_bax_records.py`.

Aesthetically: file-cabinet metaphor. Each tab is a manila folder being pulled out. Diegetic, low-fi.

### 8.4 Chapter retry — hardcore variant (stretch) — [x]
*If time allows pre-Next-Fest:* unlock a "HARDCORE" toggle per chapter after first clear. Modifiers: tighter sector timers, more barges, only 1 checkpoint in corridor, no shop stops. Pure-pride mode. Best HARDCORE clear time per chapter shown in the cargo dossier card.

If time is short, defer to post-Next-Fest.

**May 2026:** Shipped. `MetaProgression` gains
`hardcore_unlocked: list[int]`, `hardcore_best_s: dict`,
`hardcore_active: bool`, plus
`unlock_hardcore_for_chapter() / is_hardcore_unlocked() /
set_hardcore_for_next_run() / clear_hardcore_flag() /
record_hardcore_clear() / hardcore_best_time()`. First clear of any
chapter unlocks its hardcore variant; the cargo dossier card surfaces
the unlock + best time and `H` arms the flag for the next run.
RunManager applies the modifiers when `is_hardcore_run()` is True:
`hardcore_sector_dur(20.0) → 14.0` (×0.7 timer), `_difficulty()`
gets +0.3, an extra patrolling barge spawns in every sector ≥2, and
the post-sector shop trigger is suppressed. `make_corridor(chapter,
hardcore=True)` strips all `Checkpoint` elements at construction time
so the player only respawns at room start. On `complete_chapter()`
delivery records the run's total flight time as the hardcore best
(if better) and clears the flag. Tests in
`tests/test_hardcore_mode.py`.

---

## Out of scope (for now)

Captured here so devs don't re-relitigate:

- Full `core/game.py` state-controller refactor (each `GameState` as its own class). Defer.
- Seeded daily/weekly challenges (Epic 1.5 sets the foundation, no commitment to ship the feature).
- Mutual gravity beyond wells — the player ship doesn't pull on wells, just feels their pull.
- Audio asset files / pre-recorded voice work — everything stays procedural.
- Hardcore variant in 8.4 — flagged as stretch.
- Main-menu replay-tutorial option.

---

## What "ship-ready for Next Fest" looks like

**May 2026 note:** Several bullets below are **already true** (slingshot weight, sector themes, corridor framework, stepped death). Others remain open — see checkbox summary above and Phase 0.

When this entire plan is implemented:

- **Code base** is one tree, fonts are cached, the event bus is hardened, wells don't spawn under the ship, and the slingshot has weight.
- **Every sector** in a 5-sector run feels distinct on first playthrough.
- **Every chapter's delivery corridor** is a memorable 2–3 minute set piece players talk about.
- **The landing** is a tense, interactive moment with risk and reward.
- **The terminal** lands like the centerpiece it's supposed to be — keystrokes punch, NPCs react, outcomes hit.
- **Bax** speaks ~100 new lines across the game, his portrait reacts to damage, he coaches you through corridors and panics with you under fire.
- **Players who finish the campaign** open Bax's Records, see their stats, find lore fragments they missed, and reload Chapter 2 because they remember how good the biolab corridor was.

That's the demo.

---

## Related docs

| Doc | Role |
|-----|------|
| `docs/DOCUMENTATION_STATUS.md` | Stale-doc tracker, resolved + open decisions |
| `docs/DECISION_BRIEFS.md` | **Pending** theme order + landing Beat 2 detail |
| `docs/CORRIDOR_DESIGN.md` | Per-chapter corridor content spec |
| `docs/BAX_VOICE.md` | Bax line bank + tone rules |
| `docs/SOUNDTRACK_PLAN.md` | Procedural audio spec (roadmap) |
| `README.md` | Full player + dev feature overview |
