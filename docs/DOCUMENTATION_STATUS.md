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
| 8 | Phase 1/2 sweep (May 25 2026) | Epics 1.2, 1.4, 1.8, 7.2, 7.3, 7.4 shipped on `rhubarb/phase-1-2-implementation`; checkboxes flipped in `IMPROVEMENT_PLAN.md` | Done |
| 9 | Post-review sweep (May 25 2026) | **Epic 8.3 Bax's Records** screen + lore-fragment persistence shipped. Doc drift cleared: 3.1 hazard wiring, 4.2 black wipe / `ENTERING:` caption, 4.7 corridor end-card stats, and 7.1 cockpit hull-glow flipped to `[x]` after verifying live code. | Done |
| 10 | Replay/audio sweep (May 25 2026) | **Epic 4.6** per-chapter corridor music shipped (`EVT_CORRIDOR_ENTER/BOSS_ROOM/EXIT` + `_CORR_SIG_CH` + per-chapter intervals/volumes). **Epic 8.2** cargo dossier carousel shipped (`renderer/cargo_carousel.py`, `RunManager.set_chapter_override`). **Epic 8.4** HARDCORE chapter variant shipped (timer ×0.7, +0.3 difficulty, extra barge per sector ≥2, no shops, 1-checkpoint corridor, hardcore best-time per chapter). Epic 8 fully closed. | Done |
| 11 | Polish + playtest sweep (May 25 2026) | **Playtest backlog** closed: barge hit-stagger + harpoon flash visibility (`antagonists/repo_barge.py`, `renderer/vector_renderer.py`); two new union reps (Idealist Eddie / Corrupt Vinny) wired into the barge intercept rotation, with portraits + Bax opinions; NPC keyword normalization (universal `fuck off` easter egg in `BaseNPC.respond`, Felix gossip path, Dray gripe + standardised `BRIBE [X cr]` label, Krellborn extended threat keywords + harder filler). **Epic 11.1c** harmonica heal session (`H` key in flight). **Epic 13.1** money source labels on `EVT_DEBT_UPDATE` + HUD floater. **Epic 10.4** corridor decay layer (deep parallax, cracked numbered panels, scratched Nova Soma branding, floor wear, pipe drips, per-room directional lighting). **Epic 14.1** boss-room set pieces per chapter. | Done |

---

## Team-tracked priorities (from Chris — May 2026)

| # | Priority | Status in code (May 2026) |
|---|----------|---------------------------|
| 1 | **All NPCs have detailed portraits**, including Inspector Holt | **Fixed** — Holt and Relay-7 Felix have procedural busts and CRT backdrops |
| 2 | **Thruster appears broken** — works for a while, then stops | **Fixed** — heat only rises on thrust, life support absorbs heat, HUD shows heat |
| 3 | **ESC leaves the market** | **Fixed** — shop ESC routes to `ShopScreen` before pause handling |
| 4 | **Improve market graphics** | **Fixed** — shop browse view has stall dressing, item glyphs, and purchase-state badges |
| 5 | **Improve docking graphics** | **Fixed** — chapter-specific station silhouettes and bay dressing are procedural |
| 6 | **Cargo-specific dialogue for all NPCs** | **Fixed** — terminal run context carries cargo identity and every NPC has authored cargo-specific flavor |
| 7 | **Terminal outcome reveal visual pass** | **Fixed** — release/exploit/impound/paradox outcomes now have visual holds, stingers, portrait freezes, and distinct captions |
| 8 | **NLP exploit dossier footer** | **Fixed** — terminal close shows Bax's filed-method footer in the dossier panel |
| 9 | **Terminal keyword chips reflect known exploits** | **Fixed** — terminals receive Bax's vault and discovered paths render as dim ★ chips |

Phase 0 trust fixes plus the full Epic 6 terminal polish set are tracked as shipped in `docs/IMPROVEMENT_PLAN.md`.

---

## Per-document status

| Doc | Role | Accuracy |
|-----|------|----------|
| `docs/IMPROVEMENT_PLAN.md` | Master implementation plan + checkboxes | Current (Phase 0 + Phase 1/2 shipped May 2026) |
| `docs/DECISION_BRIEFS.md` | Historical decision briefs §3–§4 | Current — resolved May 2026 |
| `docs/CORRIDOR_DESIGN.md` | Corridor level design | Mostly current |
| `docs/BAX_VOICE.md` | Bax line bank | Current as writing spec |
| `docs/SOUNDTRACK_PLAN.md` | Audio spec + **implementation status** | Current |
| `docs/BAX_HUMS_IMPL.md` | Bax-hums implementation handoff plan | Historical — feature shipped May 2026 (commit `42a66d3`) |
| `docs/NEXT_PUSH.md` | Active push priority stack + design decisions | Current |
| `docs/SESSION_STATUS_MAY2026.md` | Phase 1/2 implementation report | Current (May 25 2026) |
| `docs/PLAYTEST_FEEDBACK.md` | Player feedback backlog (not yet scheduled) | Current (May 25 2026) |
| `CLAUDE.md` | Agent pointer | Current (replaces stale monolith) |
| `WORKING_ON.md` | Agent subsystem claim coordination | Current |
| `docs/CLAUDE_ARCHIVED.md` | Old agent/GDD excerpt | Historical only |
| `docs/DEAD_DRIFT_GDD_ARCHIVED.md` | Original pitch GDD | Historical only |
| `README.md` | Player + dev overview | Full pass May 2026 |

---

## Design decisions — resolved

**All design forks resolved May 2026.** Historical detail: [DECISION_BRIEFS.md](DECISION_BRIEFS.md) (superseded options kept for record).

---

## Minor drift (no design fork — fix when touching code)

*(none currently tracked — the `roguelite/tutorial.py` docstring drift was
fixed in the same commit that landed this row update.)*

---

## How to use this file

1. Treat **DECISION_BRIEFS.md** as historical unless Chris explicitly reopens a fork.  
2. After future Phase/Epic work ships, update the **Team-tracked priorities** table when doc accuracy changes.  
3. When IMPROVEMENT_PLAN checkboxes move, update here only if doc accuracy changes.
