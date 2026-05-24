# DEAD DRIFT — Open design decisions (detail briefs)

**May 2026** — Chris requested full information before choosing. **No code or plan changes for these items until you reply.**

Resolved elsewhere (see `DOCUMENTATION_STATUS.md`): CLAUDE → B, GDD → A, MAX_VELOCITY → 280, SOUNDTRACK status section → yes, README → full.

---

## Decision 3 — Chapter theme order (Epic 3.4)

### What this controls

Each campaign **chapter** (1–4) is a 5-sector run. Sector **index** 0–4 maps to a fixed **theme** from an 8-theme pool. The theme decides:

- Which **obstacle spawner** runs (`run_manager._load_next_sector` theme branch)
- Whether a **mid-sector toll terminal** fires (~10s in)
- Whether **solar flare** logic runs
- **Fuel canister** presence (some themes clear canisters)
- Sector **intro card** label + one-line description

Sector index 0 is **always** Compliance Zone (orientation sector) regardless of list position.

**Code path:** `roguelite/procedural.py` → `_CHAPTER_THEMES` + `_pick_theme()`.

---

### Side-by-side: plan vs code (all four chapters)

Player-facing sector numbers are **index + 1**.

#### Chapter 1 — Acoustic Archive

| Sector | IMPROVEMENT_PLAN §3.4 | Live code (`procedural.py`) | Same? |
|--------|----------------------|----------------------------|-------|
| 1 | Compliance Zone | Compliance Zone | ✓ |
| 2 | Wreckage Belt | Wreckage Belt | ✓ |
| 3 | Junk-Belt | Junk-Belt | ✓ |
| 4 | Flare Corridor | Flare Corridor | ✓ |
| 5 | **Toll Authority** | **Industrial Graveyard** | ✗ |

**If you switch sector 5 to Toll Authority (plan):**
- Mid-sector **Toll Authority NPC terminal** at ~10s (pay / sympathy / threaten)
- Mostly empty void + gate flavor; **no** dead station ring hazard
- Fits “bureaucratic run ends on a checkpoint” tone

**If you keep Industrial Graveyard (code):**
- **Dead station** with rotating damage ring + **1 wreck**
- **No fuel canisters** in sector
- Higher kinetic difficulty; **no** extra NLP stop before jump terminal
- Stronger “final sector gauntlet” before delivery

---

#### Chapter 2 — Epistemological Shrooms

| Sector | IMPROVEMENT_PLAN §3.4 | Live code | Same? |
|--------|----------------------|-----------|-------|
| 1 | Compliance Zone | Compliance Zone | ✓ |
| 2 | Industrial Graveyard | Industrial Graveyard | ✓ |
| 3 | Wreckage Belt | Wreckage Belt | ✓ |
| 4 | Mine Strip | Mine Strip | ✓ |
| 5 | **Toll Authority** | **Frozen Trail** | ✗ |

**If sector 5 → Toll Authority (plan):**
- Toll NPC mid-sector; paperwork-adjacent friction
- Avoids stacking **ice physics** (slick drift + broken thrust penalty) on top of **cargo control inversion**

**If sector 5 → Frozen Trail (code):**
- **Ice field** (slick acceleration; 30% thrust penalty **defined but not wired** — Phase 0.4)
- **Comet trail** lanes
- Synergizes with shroom cargo chaos on sector 5
- **No** toll terminal

---

#### Chapter 3 — Sentient Paperwork

| Sector | IMPROVEMENT_PLAN §3.4 | Live code | Same? |
|--------|----------------------|-----------|-------|
| 1 | Compliance Zone | Compliance Zone | ✓ |
| 2 | **Toll Authority** | **Junk-Belt** | ✗ |
| 3 | **Toll Authority** (2nd toll) | **Toll Authority** | partial |
| 4 | Flare Corridor | Flare Corridor | ✓ |
| 5 | Junk-Belt | **Frozen Trail** | ✗ |

**Plan intent:** Two toll stops — “paperwork chapter = double bureaucracy.”

**Live code:** One toll (sector 3), sector 2 is trash-field farming, sector 5 is ice/comet.

**If you match plan (Toll + Toll + …):**
- **Two** mid-sector NLP breaks in one run (sectors 2 and 3)
- ~20–40s total terminal time before sector jumps
- Strong thematic joke; risk of “terminal fatigue” if jumps also require J-terminal

**If you match code:**
- One toll; sector 2 **trash field** (chip damage / scrap credits)
- Sector 5 **Frozen Trail** instead of Junk-Belt finale

**Hybrid options (you’d need to specify):**
- Toll at sectors **2 and 4** (not 2 and 3) — spread bureaucracy
- Toll only sector 3 but **rename/flavor** sector 2 as “pre-clearance junk audit” (keep Junk-Belt gameplay, add Bax line)
- Double toll but **second is shorter** NPC variant (would need new design)

---

#### Chapter 4 — Schrödinger VIP

| Sector | IMPROVEMENT_PLAN §3.4 | Live code | Same? |
|--------|----------------------|-----------|-------|
| 1 | Compliance Zone | Compliance Zone | ✓ |
| 2 | Frozen Trail | Frozen Trail | ✓ |
| 3 | Industrial Graveyard | Industrial Graveyard | ✓ |
| 4 | Wreckage Belt | Wreckage Belt | ✓ |
| 5 | Mine Strip | Mine Strip | ✓ |

**Chapter 4 matches exactly.** No fork for this chapter.

---

### Summary of divergences only

| Chapter | Sectors that differ | Count |
|---------|---------------------|-------|
| 1 | 5 | 1 |
| 2 | 5 | 1 |
| 3 | 2, 3, 5 | 3 |
| 4 | — | 0 |

---

### Your options (pick one direction per reply)

| Option | What happens |
|--------|----------------|
| **A — Match plan** | Edit `_CHAPTER_THEMES` in `procedural.py` to IMPROVEMENT_PLAN §3.4 exactly (incl. Ch.3 double Toll) |
| **B — Match code** | Edit IMPROVEMENT_PLAN §3.4 to describe live `_CHAPTER_THEMES` |
| **C — Hybrid** | You specify sector-by-sector list for any chapter (we update code + plan together) |

**Reply format example:** `Themes: C — Ch1 s5 keep Industrial, Ch2 s5 Frozen, Ch3 s2 Junk s3 Toll s5 Frozen`

---

## Decision 4 — Landing Beat 2 (Epic 5.1)

### What Beat 2 is

After **Beat 1** (5s nose alignment toward bay), Beat 2 is the **descent to the landing pad**. Beat 3 is clamp cutscene → corridor.

Beat 2 feeds **dock scoring** (with Beat 1 approach score):

- **3 scoring buckets:** approach alignment, “J hit”, “burn done”
- **≥2 hits** → `EVT_DOCK_PERFECT` (+500 cr)
- **0 hits** → `EVT_DOCK_ROUGH` (−200 cr)

---

### IMPROVEMENT_PLAN spec (original)

Two **separate** input challenges (~4s total):

1. **TAP J — ALIGN THRUSTERS**
   - Drifting marker on a gauge; tap J when centered
   - Hit window: **0.6s**
   - Miss: **5 hull** chip damage + dock master grumble

2. **HOLD SPACE — RETRO BURN**
   - Fill bar ~**1.2s** hold
   - Release early: bounce off airlock walls (**10 hull**), Bax line
   - Hold too long: overshoot, **3s** time penalty

**Player fantasy:** Two distinct skill checks — timing (J) then sustained burn control (SPACE).

---

### Live implementation (`delivery/delivery_sequence.py`)

**Single continuous minigame — physics descent, ~up to 9s:**

| Parameter | Value |
|-----------|--------|
| Gravity | 28 px/s² downward |
| Retro (SPACE held) | 65 px/s² upward |
| Initial descent | 8 px/s |
| Max descent cap | 110 px/s |
| Auto-timeout | 9s → force touchdown |

**Input:** Hold **SPACE** only. **J does nothing** in Beat 2.

**UI (already fairly polished):**
- Landing bay chamber (gantry, crew, hazard stripes, pulsing pad)
- **VSI** (vertical speed) with green/yellow/red zones
- **Altitude** bar
- Retro flame VFX when SPACE held
- On-screen: `BEAT 2 · TOUCH DOWN · HOLD SPACE FOR RETROS`

**Scoring at touchdown** (impact velocity `vy`):

| Impact vy | Landing grade | Legacy flags set |
|-----------|---------------|----------------|
| ≤ 40 px/s | Smooth (2) | `_burn_done = True` |
| ≤ 75 px/s | OK (1) | `_j_hit = True` |
| > 75 px/s | Rough (0) | both False |

**Important:** `_j_hit` and `_burn_done` are **both derived from the same impact velocity**, not from separate J and SPACE challenges. The J-gauge minigame **does not exist** in code — only legacy field names remain.

**Perfect dock math today:**
- Approach aligned (≥1) + smooth landing → 2 hits → perfect (+500)
- You can “fail J” conceptually but still get perfect if approach + landing vy are good

---

### Comparison table

| Aspect | Plan (J + SPACE) | Live (SPACE physics) |
|--------|------------------|----------------------|
| Inputs | J tap + SPACE hold | SPACE hold only |
| Skill type | Timing + hold duration | Continuous throttle vs gravity |
| Failure on miss | Hull chip / time penalty | Rough landing score only |
| Duration | ~4s scripted | Variable, max 9s |
| Scoring dimensions | 2 independent | 1 physics outcome → 2 correlated flags |
| Visual polish | Not specified in detail | Substantial bay art + VSI/ALT |
| Bax lines | Dock master grumble | Smooth/rough landing lines |

---

### Your options

| Option | Work involved | Player feel |
|--------|---------------|-------------|
| **A — Restore plan** | Add J gauge phase **before or during** descent; separate `_j_hit` from `_burn_done`; possible hull chips on miss | Two sharp skill checks; more arcade |
| **B — Keep live, update plan** | Doc only; optionally rename `_j_hit` → `_land_ok` for clarity | One physics landing; sim-cockpit |
| **C — Hybrid** | e.g. J gauge **once** at start of Beat 2 (thruster align), then existing SPACE descent; or SPACE fill-bar **target** instead of raw physics | You must specify sequence |

**Graphics priority (your item 5):** Both options can get prettier bay/station art; **B** already has more HUD than plan described. **A** needs new gauge UI assets (procedural).

**Reply format example:** `Landing: C — J gauge at Beat 2 start, then keep SPACE physics for descent`

---

## Do not implement until Chris replies

Items 3 and 4 remain **open** in `IMPROVEMENT_PLAN.md` §3.4 and §5.1 until you choose A/B/C (or hybrid spec).
