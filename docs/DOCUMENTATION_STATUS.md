# DEAD DRIFT — Documentation Status

**Last reviewed:** May 2026  
**Maintainer:** Chris / Dead Drift team  
**Purpose:** Track which docs are accurate, which are stale, and which decisions still need a human call.  
**Rule:** Factual drift is recorded here. **Do not resolve open design forks without Chris’s answer.**

---

## Chris decisions log (May 2026)

| # | Topic | Decision | Status |
|---|--------|----------|--------|
| 1 | `CLAUDE.md` | **B** — archived to `docs/CLAUDE_ARCHIVED.md`; root file is agent pointer | Done |
| 2 | `DEAD_DRIFT_GDD.md` | **A** — archived to `docs/DEAD_DRIFT_GDD_ARCHIVED.md` | Done |
| 3 | Chapter theme order | **B** — IMPROVEMENT_PLAN §3.4 matches `procedural.py` | Done |
| 4 | Landing Beat 2 | **A** — J gauge + SPACE hold bar in `delivery_sequence.py` | Done |
| 5 | `MAX_VELOCITY` | **280 px/s** — overdrive cap **420 px/s** | Done |
| 6 | `SOUNDTRACK_PLAN.md` | Implementation status section | Done |
| 7 | `README.md` | Full feature list | Done |
| 8 | Repo barges = Gary / Union only | **Locked** — Phase 0.7 | Done (doc) |
| 9 | Dock Union / Gary identity | **Locked** — Epic 5.4 | Done (doc) |
| 10 | Non-Union faction ship silhouettes | **Locked** — Epic 3.7 | Done (doc) |

---

## Team-tracked priorities (from Chris — May 2026)

| # | Priority | Status in code (May 2026) |
|---|----------|---------------------------|
| 1 | **All NPCs have detailed portraits**, including Inspector Holt | **Open** — Holt and Relay-7 Felix render `?` placeholder |
| 2 | **Thruster appears broken** — works for a while, then stops | **Open (bug)** — overheat trap; heat absorption not wired |
| 3 | **ESC leaves the market** | **Open (bug)** — ESC opens pause before shop leave handler |
| 4 | **Improve market graphics** | **Open (polish)** |
| 5 | **Improve docking graphics** | **Open (polish)** |
| 6 | **Shroom control inversion (Ch.2 cargo)** | **Open (bug)** — playtest: inversion not felt in-flight; code exists, wiring unverified |
| 7 | **Barge intercept = Gary / Union only** | **Open (design violation)** — `open_barge_terminal()` randomizes Gary ~30%; pirates can appear on barge comm |
| 8 | **Dock Union identity (Gary, Local 404)** | **Open (polish)** — generic dock crew; Gary not at landing per corridor spec |
| 9 | **Non-Union NPCs → distinct ship hulls** | **Open** — pirates/DJs/etc. terminal-only; only player + barge + alien in flight |

Tracked in `docs/IMPROVEMENT_PLAN.md` → **Phase 0**.

---

## Live playtest log (Chris)

Add rows as you play; agents update Phase 0 / epics from here.

| Date | Finding | Doc / phase |
|------|---------|-------------|
| May 2026 | Epistemological Shrooms — periodic control inversion not working in flight | Phase 0.6 |
| May 2026 | Repo barges should always be Gary — **only Union** on barges; no pirates on barge comm | Phase 0.7 |
| May 2026 | Update the docks — Union / Gary identity at landing | Phase 0.8, Epic 5.4 |
| May 2026 | Pirates, radio DJs, etc. need **different spaceship types** (not barges) | Phase 0.9, Epic 3.7 |

---

## Per-document status

| Doc | Role | Accuracy |
|-----|------|----------|
| `docs/IMPROVEMENT_PLAN.md` | Master implementation plan + checkboxes | Current (May 2026 pass) |
| `docs/DECISION_BRIEFS.md` | Open forks §3–§4 detail | Current — pending Chris |
| `docs/CORRIDOR_DESIGN.md` | Corridor level design | Mostly current |
| `docs/BAX_VOICE.md` | Bax line bank | Current as writing spec |
| `docs/SOUNDTRACK_PLAN.md` | Audio spec + **implementation status** | Current |
| `CLAUDE.md` | Agent pointer | Current (replaces stale monolith) |
| `docs/CLAUDE_ARCHIVED.md` | Old agent/GDD excerpt | Historical only |
| `docs/DEAD_DRIFT_GDD_ARCHIVED.md` | Original pitch GDD | Historical only |
| `README.md` | Player + dev overview | Full pass May 2026 |

---

## Open decisions — do not implement until Chris replies

**All design forks resolved May 2026.** Historical detail: [DECISION_BRIEFS.md](DECISION_BRIEFS.md) (superseded options kept for record).

---

## Minor drift (no design fork — fix when touching code)

| Item | Issue |
|------|--------|
| `roguelite/tutorial.py` docstring | Says `clone_count == 1`; live code uses `<= 3` |
| `roguelite/shop.py` line 12 | Dead `SHOP_SECTORS = {3, 6}`; live `{1, 3}` in `settings.py` |

---

## How to use this file

1. Resolve open items in **DECISION_BRIEFS.md** before changing themes or landing Beat 2.  
2. After Phase 0 ships, update the **Team-tracked priorities** table.  
3. When IMPROVEMENT_PLAN checkboxes move, update here only if doc accuracy changes.
