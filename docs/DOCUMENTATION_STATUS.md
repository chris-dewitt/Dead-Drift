# DEAD DRIFT — Documentation Status

**Last reviewed:** May 2026  
**Maintainer:** Chris / Dead Drift team  
**Purpose:** Track which docs are accurate, which are stale, and which decisions have been made.  
**Rule:** Factual drift is recorded here. **Do not reopen resolved design forks unless Chris asks.**

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
| 8 | Phase 1/2 sweep (May 25 2026) | Epics 1.2, 1.4, 1.8, 7.2, 7.3, 7.4 shipped on `rhubarb/phase-1-2-implementation` | Done |
| 9 | Post-review sweep (May 25 2026) | Epic 8.3 Bax's Records + lore-fragment persistence; doc drift cleared on 3.1, 4.2, 4.7, 7.1 | Done |
| 10 | Replay/audio sweep (May 25 2026) | Epics 4.6, 8.2, 8.4 shipped; Epic 8 fully closed | Done |
| 11 | Polish + playtest sweep (May 25 2026) | Barge hit-stagger, harpoon flash, two new union reps (Eddie/Vinny), NPC keyword normalisation, harmonica heal, money source labels, corridor decay layer, boss-room set pieces | Done |
| 12 | Repo barges = Gary / Union only | **Locked** — Phase 0.7; in-flight barges always Gary or new union reps, never pirates | Locked |
| 13 | Dock Union / Gary identity | **Locked** — Epic 5.4; landing dock = Gary as receiving officer | Locked |
| 14 | Non-Union faction ship silhouettes | **Locked** — Epic 3.7; pirates/DJs/Kress/Sandra need own hull art | Locked |

---

## Team-tracked priorities (from Chris — May 2026)

| # | Priority | Status in code (May 2026) |
|---|----------|---------------------------|
| 1 | **All NPCs have detailed portraits**, including Inspector Holt | **Fixed** — Holt and Relay-7 Felix have procedural busts and CRT backdrops |
| 2 | **Thruster appears broken** — works for a while, then stops | **Fixed** — heat only rises on thrust, life support absorbs heat, HUD shows heat |
| 3 | **ESC leaves the market** | **Fixed** — shop ESC routes to `ShopScreen` before pause handling |
| 4 | **Improve market graphics** | **Fixed** — shop browse view has stall dressing, item glyphs, and purchase-state badges |
| 5 | **Improve docking graphics** | **Fixed** — chapter-specific station silhouettes and bay dressing are procedural |
| 6 | **Cargo-specific dialogue for all NPCs** | **Fixed** — terminal run context carries cargo identity; every NPC has cargo flavor |
| 7 | **Terminal outcome reveal visual pass** | **Fixed** — release/exploit/impound/paradox have holds, stingers, portrait freezes, captions |
| 8 | **NLP exploit dossier footer** | **Fixed** — terminal close shows Bax's filed-method footer in the dossier panel |
| 9 | **Terminal keyword chips reflect known exploits** | **Fixed** — terminals receive Bax's vault; discovered paths render as dim ★ chips |
| 10 | **Shroom control inversion (Ch.2 cargo)** | **Open (bug)** — playtest: inversion not felt in-flight; code exists, wiring unverified |
| 11 | **Barge intercept = Gary / Union only** | **Fixed** — `open_barge_terminal()` now routes to Gary/Eddie/Vinny only (cursor sweep) |
| 12 | **Dock Union identity (Gary, Local 404)** | **Open (polish)** — generic dock crew; Gary not at landing; locked as Epic 5.4 target |
| 13 | **Non-Union NPCs → distinct ship hulls** | **Open** — pirates/DJs/etc. terminal-only; only player + barge + alien in flight |
| 14 | **Ch.3 Paperwork corridor** | **Open (bug)** — `OneWayWall` never used for collision; clerk dialog modal locks all input |

---

## Live playtest log (Chris)

Add rows as you play; agents update Phase 0 / epics from here.

| Date | Finding | Doc / phase |
|------|---------|-------------|
| May 2026 | Epistemological Shrooms — periodic control inversion not working in flight | Phase 0.6 |
| May 2026 | Repo barges should always be Gary — **only Union** on barges; no pirates on barge comm | Phase 0.7 |
| May 2026 | Update the docks — Union / Gary identity at landing | Phase 0.8, Epic 5.4 |
| May 2026 | Pirates, radio DJs, etc. need **different spaceship types** (not barges) | Phase 0.9, Epic 3.7 |
| May 2026 | **Ch.3 document / Paperwork corridor** — problem in delivery corridor (see Phase 0.10) | Phase 0.10 |
| May 2026 | **Ch.3 repro detail:** at ladder / documents → all keys dead (incl. ESC/pause). Clerk dialog modal lock | Phase 0.10 |

---

## Per-document status

| Doc | Role | Accuracy |
|-----|------|----------|
| `docs/IMPROVEMENT_PLAN.md` | Master implementation plan + checkboxes | Current (all Phase 0 + Epics 1–14 swept May 2026) |
| `docs/ALIVENESS_PUSH.md` | Next push plan (60+ items, 8 phases) | Current (May 25 2026) |
| `docs/DECISION_BRIEFS.md` | Historical decision briefs §3–§4 | Current — resolved May 2026 |
| `docs/CORRIDOR_DESIGN.md` | Corridor level design | Mostly current |
| `docs/BAX_VOICE.md` | Bax line bank | Current as writing spec |
| `docs/SOUNDTRACK_PLAN.md` | Audio spec + implementation status | Current (v2 May 2026) |
| `docs/BAX_HUMS_IMPL.md` | Bax-hums implementation handoff plan | Historical — shipped May 2026 |
| `docs/NEXT_PUSH.md` | Previous push priority stack (Epic 9–14) | Historical — superseded by ALIVENESS_PUSH.md |
| `docs/SESSION_STATUS_MAY2026.md` | Phase 1/2 implementation report | Current |
| `docs/PLAYTEST_FEEDBACK.md` | Player feedback backlog | Current (May 25 2026) |
| `CLAUDE.md` | Agent pointer | Current |
| `WORKING_ON.md` | Agent subsystem claim coordination | Current |
| `docs/CLAUDE_ARCHIVED.md` | Old agent/GDD excerpt | Historical only |
| `docs/DEAD_DRIFT_GDD_ARCHIVED.md` | Original pitch GDD | Historical only |
| `README.md` | Player + dev overview | Full pass May 2026 |

---

## Minor drift (fix when touching code)

| Item | Issue |
|------|--------|
| `roguelite/shop.py` line 12 | Dead `SHOP_SECTORS = {3, 6}`; live `{1, 3}` in `settings.py` |
| `delivery/corridor/base.py` | `OneWayWall` imported but never wired for collision — Ch.3 cubicle zigzag non-functional |

---

## How to use this file

1. Treat **DECISION_BRIEFS.md** as historical unless Chris explicitly reopens a fork.  
2. After future Phase/Epic work ships, update the **Team-tracked priorities** table when doc accuracy changes.  
3. When IMPROVEMENT_PLAN checkboxes move, update here only if doc accuracy changes.
