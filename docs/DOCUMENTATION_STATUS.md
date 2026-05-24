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

---

## Team-tracked priorities (from Chris — May 2026)

| # | Priority | Status in code (May 2026) |
|---|----------|---------------------------|
| 1 | **All NPCs have detailed portraits**, including Inspector Holt | **Open** — Holt and Relay-7 Felix render `?` placeholder |
| 2 | **Thruster appears broken** — works for a while, then stops | **Open (bug)** — overheat trap; heat absorption not wired |
| 3 | **ESC leaves the market** | **Open (bug)** — ESC opens pause before shop leave handler |
| 4 | **Improve market graphics** | **Open (polish)** |
| 5 | **Improve docking graphics** | **Open (polish)** |

Tracked in `docs/IMPROVEMENT_PLAN.md` → **Phase 0**.

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
