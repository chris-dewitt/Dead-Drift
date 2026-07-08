# Archived documentation

**July 2026:** The active doc surface was reduced to a small set agents and devs actually read.

## What was removed (git history preserves full text)

| Former file | Why it went |
|-------------|-------------|
| `ALIVENESS_PUSH.md` | Push complete (A–H, July 2026) |
| `IMPROVEMENT_PLAN.md` | Epics 1–14 complete (May 2026) |
| `NEXT_PUSH.md` | Superseded by Aliveness, then Delivery v2 |
| `DOCUMENTATION_STATUS.md` | Stale tracker — replaced by README + CLAUDE |
| `CORRIDOR_DESIGN.md` | Superseded by code + Delivery v2 push |
| `PLAYTEST_FEEDBACK.md` | May 2026 items resolved in Aliveness Phase A |
| `SESSION_STATUS_MAY2026.md` | One-off session snapshot |
| `DECISION_BRIEFS.md` | Resolved design forks |
| `STRING_AUDIT_RESULTS.md` | Epic 9.4 complete |
| `BAX_HUMS_IMPL.md` | Shipped (`audio/bax_hum.py`) |
| `SOUNDTRACK_IMPL_H1.md` | Folded into SOUNDTRACK_PLAN open-work note |
| `CLAUDE_ARCHIVED.md` | Old agent/GDD excerpt |
| `DEAD_DRIFT_GDD_ARCHIVED.md` | Original pitch GDD |

## Current docs (use these)

- [`README.md`](../../README.md) — player + dev overview
- [`CLAUDE.md`](../../CLAUDE.md) — agent pointer
- [`DELIVERY_V2_PUSH.md`](../DELIVERY_V2_PUSH.md) — active roadmap
- [`BAX_VOICE.md`](../BAX_VOICE.md) — Bax lines
- [`NPC_SCHEMA.md`](../NPC_SCHEMA.md) — terminal NPC schema
- [`SOUNDTRACK_PLAN.md`](../SOUNDTRACK_PLAN.md) — audio spec
- [`RECORDING_BRIEF.md`](../RECORDING_BRIEF.md) — recording stems
- [`WORKING_ON.md`](../../WORKING_ON.md) — agent file claims

To recover a deleted file: `git log -- docs/FILENAME.md` then `git show <commit>:docs/FILENAME.md`.
