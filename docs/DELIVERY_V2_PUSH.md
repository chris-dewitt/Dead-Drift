# THE DELIVERY V2 PUSH

**Started:** July 6 2026
**Status:** I.1–I.4 shipped (`[~]` pending play-verify) — I.5 (chain juice) next
**Scope:** Open-ended (no time cap)
**North star for all agents:** this is the only active push doc. The Aliveness push (A–H) completed July 2026; prior roadmaps were removed — see `docs/archive/README.md`.

---

## Vision

The flight game earns its fun through physics — momentum, risk, mastery. The
delivery corridor is currently a ~30-second interlude with none of that: a
constant-speed walk, one fixed jump, and a star rating that *punishes* the
player for exploring the secrets and lore that are its best content.

This push makes the corridor the second half of the game instead of the
epilogue: a **2–3 minute, early-90s-console platformer level** the player
doesn't want to end. Think SMW / DKC: chunky outlined tiles, generous
feedback, coin-trails that teach routes, a tally screen that makes you want
one more run.

**The signature test for every item:** *would a player ever say "let me just
do one more delivery" for its own sake?* If an item doesn't push toward that,
it's cut.

**Theme keyword:** *arcade*. The flight is a simulation; the corridor is an
arcade cabinet inside it. Changing phases should feel like changing TV
channels in 1993 — same era, different show.

---

## Resolved decisions (July 6 2026, with Chris)

1. **Scoring — style over speed.** Stars come from collection % + secrets
   found + hits avoided. Par time becomes a small credit bonus
   ("UNION PUNCTUALITY BONUS"), never the rating. Exploring IS the game.
2. **Length — 2–3 minutes.** 6–8 rooms per chapter with mid-level
   checkpoints. Delivery becomes co-equal with flight.
3. **Art — full 16-bit pastiche.** Outlined tiles, dithered gradients,
   sprite poses, period HUD, iris wipes. The 400×360 internal canvas with
   nearest-neighbor upscale stays — it's period-correct (SNES was 256×224).
4. **Scope — corridor first, then chain.** Phases I.1–I.4 are the corridor.
   I.5 then juices APPROACH / LAND / RESULT so the whole delivery chain ends
   on the same high.

---

## Baseline audit (July 6 2026)

What exists and is good — build on it, don't rebuild:

- `delivery/corridor/` (~5k lines): per-chapter themed corridors, Room
  system with branch/converge high–low paths, rich element vocabulary
  (moving/collapsing platforms, ladders, beams, vents, tripwires, stealth
  zones, NPC encounters, collectibles, secrets, lore rooms, NPC shortcuts,
  checkpoints, boss rooms with actors), cargo-driven mutators, per-room
  palettes, 3-layer parallax base, `draw_mario_brick_platform` helper.

What holds it back:

- ~2,700 px of world per chapter at fixed 220 px/s → ~30 s runs.
- No movement feel: constant walk speed, fixed-height jump, no momentum,
  no coyote time, no jump buffering, no sprint.
- Stars are time-based (3★ = under 18 s) — anti-exploration.
- Sparse reward feedback: no pickup pop, no chains, no tally.
- Ch5/ch6 corridors are the leanest (274/312 lines vs 763 for ch3).
- `delivery/platformer.py` + `delivery/obstacles.py` are dead code
  (pre-corridor system; nothing imports them but each other).

---

## Phase I.1 — Feel (movement & moment-to-moment)

The four constants that separate stiff from Nintendo. Everything else in
this push lands harder if I.1 lands first.

### I.1.1 Momentum movement — [~]
Ground acceleration/deceleration with a skid state (reverse at speed →
skid dust + short slide). Air control slightly weaker than ground. Walk cap
stays ~220 px/s; **sprint** (hold SHIFT / X) ramps toward ~320 px/s after
sustained running (P-speed style — speed is earned, not toggled).

### I.1.2 Jump feel — [~]
Variable jump height (release early → cut vertical velocity), coyote time
(~0.10 s), jump buffering (~0.12 s). Constants live in one tunable block at
the top of `corridor/base.py` with comments — Chris will play-tune these.

### I.1.3 Squash, stretch & poses — [~]
Courier sprite gains: land squash, jump stretch, skid pose, fall pose,
victory pose. Dust puffs on landing/skid/sprint-start. (Procedural — extend
`draw_courier_sprite` with pose params; no image assets.)

### I.1.4 Movement audio hooks — [~]
Jump / land / skid / sprint-lock blips through `audio_manager`, quantized
to the corridor music where the engine already supports it.

### I.1.5 Dead code removal — [x]
Delete `delivery/platformer.py` and `delivery/obstacles.py`.

*Note: corridor kinematics are hand-rolled (not `RigidBody2D`) — the
flight-physics dt rule doesn't apply here; keep platformer integration
local and simple.*

**I.1 ship note (July 6):** all five items landed on one branch;
I.1.1–I.1.4 are `[~]` until the feel passes a windowed play-test. The
tunable block sits at the top of `delivery/corridor/base.py`. 14 new
regression tests in `tests/test_corridor_feel_i1.py`; suite 300 passed.
Play-check list: does walk→sprint ramp feel earned? Held vs tapped jump
read clearly? Skid turn feel snappy or slippery? Land thud/squash sell
weight? Dial the constants block, not the code.

---

## Phase I.2 — Reward loop (scoring & feedback)

### I.2.1 Style scoring + tally screen — [~]
Stars from: chip collection % / secrets found / hits taken. Par time pays a
small credit bonus only. End-of-corridor **tally screen** in the DKC/SMW
tradition: chips tick up with sound, secrets stamp in, stars burst on one at
a time, Bax reacts to the grade.

### I.2.2 Chip language — [~]
Redesign chip placement as *communication*: arcs over gaps teach jump
timing, lines mark safe routes, rings halo secrets. Pickup pop: sparkle +
floating "+200" + blip that rises in pitch per chain.

### I.2.3 Chip chains — [~]
Chips collected within ~1.5 s of each other build a ×1→×5 chain multiplier.
Chain meter in HUD; breaking the chain drops the pitch back down. Makes
greed lines and risky routes self-rewarding.

### I.2.4 Room-clear flourish — [~]
Door iris + room name stamp + per-room mini-tally chip count
("7/9 — two still in there, mate").

### I.2.5 Completion feeds meta — [~]
100% chips + all secrets in a chapter corridor → permanent dossier stamp
("COURIER'S PRIDE") on that chapter's carousel card.

**I.2 ship note (July 7):** all five items landed on one branch; `[~]`
until the tally/chain feel passes a windowed play-test. Reward tunables
(chain window, star thresholds, punctuality bonus) sit in the I.2 block
at the top of `delivery/corridor/base.py`. 18 new regression tests in
`tests/test_corridor_reward_i2.py`; suite 321 passed. Chip *placement*
redesign (arcs over real gaps, greed lines) deliberately waits for the
I.3 room expansion — the `chip_arc`/`chip_line` helpers are ready.
Play-check list: chain window too tight/loose at 1.5s? Chip blip pitch
climb satisfying? Tally pacing — too slow to sit through, or skipped
instinctively? 75%/40% star thresholds fair for how you actually play?

---

## Phase I.3 — Levels (length, variety, set pieces)

### I.3.1 6–8 rooms per chapter — [~]
Target 2–3 min clear (full-clear with secrets ~4 min). Extend existing
chapters with new rooms rather than rebuilding — current rooms keep their
identity; boss rooms stay the finale. Checkpoints every 2–3 rooms.

### I.3.2 New element vocabulary — [~]
Springs/bounce pads, conveyor belts, breakable blocks (sprint-through),
hidden ?-blocks, warp pipes (the corporate pipes finally pay off —
shortcuts + secret sub-rooms), timed lift rides.

### I.3.3 Power-ups — [~] *(risk gate cleared July 7: all three approved)*
Temporary, corridor-scoped, era-flavored: **Mag-Boots** (chip magnet),
**Union Hardhat** (absorbs one hit, Mario-style de-power instead of raw
damage), **Stim Soles** (speed + jump boost). Spawn from ?-blocks.

### I.3.4 One chase set piece — [~] *(risk gate cleared July 7: ch6 approved; systems shipped, room lands in I.3b)*
A single auto-scroll pressure room in a late chapter (ch6 Compliance sweep
is the natural home). Max one per campaign — pressure is the spice, not
the meal.

### I.3.5 Ch5/ch6 parity + hit rebalance — [~]
Bring The Edge and Compliance corridors to full room-count/secret parity
with ch1–4. `MAX_HITS` scales with length (5 for 6+ rooms); checkpoints
restore one.

**I.3a ship note (July 7):** the systems half landed: Spring /
ConveyorBelt / BreakableBlock (sprint-through, scatters chips) /
QuestionBlock (chips or power-up) / WarpPipe (DOWN to warp) / TimedLift;
all three power-ups (Mag-Boots magnet, Hardhat hit-eater, Stim Soles
speed+jump); chase-room camera (Room(auto_scroll=px/s), sweep wall
crush); max-hits 5 on 6+-room corridors; checkpoints patch one hit.
Spring launches are exempt from jump-cut gravity. First taste placed in
ch1 room 2 (spring to catwalk, hardhat ?-block, chip arc, crate).
18 new tests in tests/test_corridor_levels_i3.py; suite 339 passed.
I.3.1 room expansion + ch5/6 parity + the actual ch6 chase room are
I.3b — the content pass.

**I.3b ship note (July 8):** the content pass landed. All six chapters
are now 6–7 rooms via parameterized recipes in
`delivery/corridor/rooms_v2.py` (spring_yard, conveyor_gallery,
crate_warren, lift_shaft, pipe_junction, chase_sweep) themed per
chapter and slotted between the original rooms and each boss finale.
Ch5/ch6 got the parity boost (7 rooms each); ch6's COMPLIANCE SWEEP is
the campaign's one auto-scroll room, penultimate slot. Two real bugs
fixed en route: ch3's A.6 one-way walls spanned floor-to-ceiling and
soft-locked the chapter (now waist-high, full-jump hops them), and
walls no longer zero momentum on contact (you run in place and pop
over mid-jump instead of dying flat). A scripted sprint+full-jump bot
traverses every chapter end-to-end in CI (27–42s bot time → 2–3 min
human pace). 11 new tests in tests/test_corridor_content_i3b.py;
suite 350 passed. Play-check: room variety pacing, chase room panic
level, pipe-skip tradeoff, lore-secret hit rate.

---

## Phase I.4 — 16-bit pastiche (graphics)

### I.4.1 Tile vocabulary — [~]
Extend `draw_mario_brick_platform` into a per-chapter tile set: brick,
girder, glass, fungus shelf, filing cabinet, chrome. Chunky black outlines,
2-tone dither gradients, fat highlights. All procedural.

### I.4.2 Parallax upgrade — [~]
3 → 4 layers with per-chapter skyline silhouettes and animated mid-layer
props (fans, signage, drips, passing trams).

### I.4.3 Sprite sheet feel — [~]
Courier: 4-frame run cycle + the I.1.3 poses. Boss actors and corridor NPCs
get idle bob + blink so nothing stands statue-still.

### I.4.4 Period HUD & transitions — [~]
Chunky counters (chips, chain, hits-as-helmets), room name plate on entry,
iris-wipe between rooms. Everything drawn on the 400×360 canvas so the
upscale keeps it honest.

### I.4.5 Palette discipline — [~]
Per-room palettes capped ~16 visible colors for the era look. Light audit
script; skip the tooling if it turns fiddly (risk gate).

**I.4 ship note (July 8):** renderer/tiles.py carries the six-style
tile vocabulary (brick/fungus/cabinet/chrome/girder/glass — one per
chapter, keyed by the palette's `tile_style`; unknown styles fall back
to brick). Platforms, moving platforms, and lifts all draw through it:
chunky 2px outlines, checkerboard dither, fat top highlight. Default
bg gained a deep skyline silhouette layer (0.08× parallax, lit
windows) and rotating wall-fan props. Room transitions are now a hard
iris wipe centred on the courier. HUD is a boxed period strip with the
hit budget as gold helmets that scar out when spent. Honest scope
notes: I.4.3's courier poses/cadence shipped back in I.1 (this phase
verified NPC/boss set pieces already animate); I.4.5 is manual
discipline via the tile system's fixed tone ramps — the audit script
was skipped per the risk gate. 6 new tests; suite 356 passed.
Screenshots of all six chapter styles sent to Chris for the visual
play-verify.

---

## Phase I.5 — Chain juice (APPROACH / LAND / RESULT)

### I.5.1 Approach rings — [~]
Optional ring line through the approach; clean line ticks small credits.

### I.5.2 Landing grade — [~]
Touchdown graded on descent rate + pad centering: SILK / FIRM / ROUGH
plate stamp, small bonus, existing Bax landing lines wired to grade.

### I.5.3 RESULT card v2 — [~]
Payout card rebuilt in the I.2.1 tally style so the whole delivery chain
ends on the same arcade high.

**I.5 ship note (July 8):** all three landed in `delivery/delivery_sequence.py`.
I.5.1 — five pre-placed rings drift toward the ship during APPROACH
(Star-Fox style); each clean pass pays 150cr with a ping, a flawless
line adds 400cr + a Bax line, and the approach now holds open until the
ring line resolves (magnetic lock still ends Beat 1 once aligned AND
rings done). I.5.2 — `_finish_dock` tags the existing perfect/mid/rough
envelope as SILK/FIRM/ROUGH with a plate stamp that settles onto the
Beat-3 dock and shows the ±bonus; Bax's landing lines already wired.
I.5.3 — RESULT card rebuilt as a staged tally: rows stamp in on a
schedule (rings → landing grade → corridor stars → cargo), payout
counts up, balance lands last; ring credits fold into the payout.
Ring/grade tunables (`_RING_SPEED/_RADIUS/_CREDIT/_LINE_BONUS`) sit by
the approach constants. 12 new tests in `tests/test_delivery_chain_i5.py`
(ring line math, miss case, lock-hold, SILK/FIRM/ROUGH matrix, stamp +
tally render, ring credits fold in, all-chapters chain). Suite 368
passed. **This closes the Delivery v2 push (I.1–I.5).** Play-check:
ring spacing/forgiveness, grade thresholds, tally pacing at 6.5s hold.

---

## Execution Plan

**Branch strategy:** one branch + PR per phase (the Aliveness push's
single-branch approach made review heavy; PR-per-phase matches how #70/#75
landed cleanly).

**Commit format:** `delivery-v2(I.x): <item>` — one commit per logical item,
phase summary commit on close.

**Verification:**
- Headless-testable logic gets tests: physics windows (coyote/buffer),
  chain math, scoring, new element collisions, corridor construction for
  all six chapters.
- Feel and graphics are play-verified by Chris before checkboxing —
  same `[x]` / `[~]` / `[ ]` legend as the Aliveness push.
- Tunable constants (I.1) land in one commented block for play-tuning.

**Risk gates (revisit before starting):**
- I.3.3 power-ups — confirm the three picks and de-power rule.
- I.3.4 chase room — prototype early, cut without ceremony if it fights
  the explore-first scoring.
- I.4.5 palette audit tooling — manual discipline is fine if the script
  gets fiddly.

---

**Status legend:**
- `[x]` shipped + play-verified
- `[~]` shipped but partial / failed play-verify
- `[ ]` not started
