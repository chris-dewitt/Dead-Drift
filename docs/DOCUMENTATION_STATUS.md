# DEAD DRIFT — Documentation Status

**Last reviewed:** May 2026  
**Maintainer:** Chris / Dead Drift team  
**Purpose:** Track which docs are accurate, which are stale, and which decisions still need a human call.  
**Rule:** Factual drift is recorded here. **Do not resolve “Decision needed” items without Chris’s answer.**

---

## Team-tracked priorities (from Chris — May 2026)

These came from the May 2026 planning session. They are **not** inferred — they are the current player-facing priorities until Chris changes them.

| # | Priority | Status in code (May 2026) |
|---|----------|---------------------------|
| 1 | **All NPCs have detailed portraits**, including Inspector Holt | **Open** — Holt and Relay-7 Felix render `?` placeholder (`terminal/npc_portraits.py` missing from `_NAME_TO_KEY`) |
| 2 | **Thruster appears broken** — works for a while, then stops | **Open (bug)** — overheat with no recovery while thruster stays powered; `LifeSupport.heat_absorption` not wired |
| 3 | **ESC leaves the market** | **Open (bug)** — `GameState.SHOP` is pauseable; ESC opens pause menu before `ShopScreen.handle_key()` runs |
| 4 | **Improve market graphics** | **Open (polish)** — procedural shop exists; graphics pass not started |
| 5 | **Improve docking graphics** | **Open (polish)** — interactive dock sequence exists; visual/cinematic pass not started |

Implementation tracking for these also lives in `docs/IMPROVEMENT_PLAN.md` under **Phase 0 — Trust Fixes** and the relevant epics (5, 6).

---

## Per-document status

### `docs/IMPROVEMENT_PLAN.md`

| Field | Value |
|-------|--------|
| **Role** | Master pre–Steam Next Fest implementation spec (8 epics) |
| **Accuracy** | **Partially stale** — many epics are further along than the prose implies; completion checkboxes added May 2026 |
| **Action taken** | Checkboxes + completion summary added May 2026 |
| **Decision needed** | None for the doc itself — use this as the live task list |

---

### `docs/CORRIDOR_DESIGN.md`

| Field | Value |
|-------|--------|
| **Role** | Per-chapter corridor level design (companion to IMPROVEMENT_PLAN Epic 4) |
| **Accuracy** | **Mostly current** — `delivery/corridor/chapter*.py` implements rooms, branching, NPCs, secrets per spec |
| **Known gaps vs design** | Black-wipe **“ENTERING: &lt;ROOM NAME&gt;”** caption not implemented; corridor end-card (time / collectibles / secrets) partial (stars only) |
| **Decision needed** | None unless Chris wants to change corridor scope |

---

### `docs/BAX_VOICE.md`

| Field | Value |
|-------|--------|
| **Role** | Tone guide + line bank for Epic 7 |
| **Accuracy** | **Mostly current as a writing spec** — most contexts ported to `bax/bax.py` |
| **Known gaps** | `first_kill_of_sector` sets a flag but has no dedicated line list from this doc; mode-based pitch (manic/dark) not fully wired in audio |
| **Decision needed** | None unless Chris wants to cut or expand line contexts |

---

### `docs/SOUNDTRACK_PLAN.md`

| Field | Value |
|-------|--------|
| **Role** | Procedural audio identity + reactive systems spec |
| **Accuracy** | **Aspirational / roadmap** — `audio/` is real and substantial (stems, barge motif, BPM tiers), but not every moment in Section 6–7 matches spec yet |
| **Decision needed** | **Chris:** Should this doc get an explicit **“Implementation status”** section (maintained alongside code), or stay spec-only with status tracked only in `IMPROVEMENT_PLAN.md`? |

---

### `CLAUDE.md` (repo root)

| Field | Value |
|-------|--------|
| **Role** | Agent working instructions + embedded GDD excerpt |
| **Accuracy** | **Very stale** — factual mismatches with live code include: |
| | • “Audio stubbed” — **false** (`audio/audio_manager.py` is fully procedural) |
| | • “Not Yet Done: main menu, terminal from flight, docking, shop” — **false** (all exist) |
| | • “Barge tether not drawn” — **false** (tether drawn in `vector_renderer.py`) |
| | • Cargo names (`MycoShroom`, `TriplicateForm`) — renamed in code |
| | • Controls omit P pause, shop, delivery, save slots |
| **Decision needed** | **Chris — pick one:** |
| | **A)** Rewrite `CLAUDE.md` in place to match current code (keep as agent + team quick reference) |
| | **B)** Archive to `docs/CLAUDE_ARCHIVED.md` and point agents at `README.md` + `docs/IMPROVEMENT_PLAN.md` |
| | **C)** Split: short agent rules file + link out to GDD/README (you define what stays in the short file) |

---

### `DEAD_DRIFT_GDD.md` (repo root)

| Field | Value |
|-------|--------|
| **Role** | Original approved-for-production GDD |
| **Accuracy** | **Stale as implementation spec** — e.g. “10-sector gauntlet” vs live 5-sector / 4-chapter structure; old cargo names; “fully voiced Bax” |
| **Decision needed** | **Chris — pick one:** |
| | **A)** Archive as historical pitch (`docs/DEAD_DRIFT_GDD_ARCHIVED.md`) — no longer edited |
| | **B)** Update in place to match shipped game (large editorial pass) |
| | **C)** Leave as-is but add a one-line banner at top: *“Historical — see README + IMPROVEMENT_PLAN for current spec”* |

---

### `README.md` (repo root)

| Field | Value |
|-------|--------|
| **Role** | Player + dev quick start |
| **Accuracy** | **Mostly current** for boot/saves/death/pause |
| **Known omissions** | Shop stops, 4-chapter campaign, delivery corridor, mid-sector toll (K key, barge intercept terminals), procedural audio, `test_stage.py` |
| **Decision needed** | **Chris:** Minimal patch (add missing features + controls) **or** full player-facing feature list before Steam page work? |

---

### `roguelite/tutorial.py` module docstring

| Field | Value |
|-------|--------|
| **Accuracy** | **Stale line** — says `clone_count == 1`; `run_manager.py` uses `clone_count <= 3` |
| **Decision needed** | None — safe to fix docstring when next touching that file (no design fork) |

---

### `roguelite/shop.py` line 12 — `SHOP_SECTORS = {3, 6}`

| Field | Value |
|-------|--------|
| **Accuracy** | **Wrong / dead code** — live config is `config/settings.py` → `{1, 3}` |
| **Decision needed** | None — delete or comment when fixing shop (no design fork) |

---

## Design drift — needs Chris (source of truth)

These are places where **the plan and the code disagree**. The agent should not pick a winner without your input.

### Chapter theme order (Epic 3.4)

`docs/IMPROVEMENT_PLAN.md` §3.4 says:

- **Chapter 1 sector 5:** Toll Authority  
- **Chapter 3 sectors 3–4:** Toll Authority twice  

Live code in `roguelite/procedural.py` `_CHAPTER_THEMES`:

- **Chapter 1 sector 5:** Industrial Graveyard (not Toll Authority)  
- **Chapter 3:** one Toll Authority (sector 3), not two in a row  

**Decision needed — Chris:** Should we **change code to match the plan**, **change the plan to match code**, or **revise both** (e.g. Ch.3 “paperwork” gets two toll stops but at different indices)?

### Landing Beat 2 (Epic 5.1)

Plan specifies **TAP J alignment gauge** + **HOLD SPACE retro burn**.  
Live `delivery/delivery_sequence.py` Beat 2 is **SPACE-only physics descent** (no J gauge).

**Decision needed — Chris:** Restore J gauge per plan, keep SPACE-only and update plan, or hybrid?

### `MAX_VELOCITY` (Epic 2.1)

Plan locked **380 px/s**. Live `config/settings.py` has **280 px/s** (comment: “death-spiral fix”).

**Decision needed — Chris:** Revert toward 380, keep 280 and update locked decision, or tune elsewhere?

---

## How to use this file

1. Before a doc edit sprint, scan **Decision needed** rows — resolve with Chris first.  
2. After shipping a priority item, update the **Team-tracked priorities** status column.  
3. When `IMPROVEMENT_PLAN` checkboxes move, no need to duplicate here unless the doc itself goes stale again.
