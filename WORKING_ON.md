# WORKING_ON — Agent Subsystem Claims

**Purpose:** prevent multiple agents editing the same files simultaneously.

Before touching a subsystem, check this file. If it's claimed, pick something else.
After committing your work, remove your row.

---

## Active claims

| Subsystem | Branch | Claimed by | Timestamp |
|-----------|--------|------------|-----------|
| run_manager | cursor/critical-bug-investigation-b9d6 | critical-bug-automation | 2026-07-24 11:10 |

---

## Subsystem map

| Subsystem | Key files |
|-----------|-----------|
| `renderer` | `renderer/vector_renderer.py`, `renderer/cockpit_renderer.py`, `renderer/sci_fi_ui.py` |
| `terminal` | `terminal/terminal.py`, `terminal/npc_portraits.py` |
| `npcs` | `terminal/npcs/*` — claim individual NPC files separately |
| `bax` | `bax/bax.py`, `bax/vocabulary_vault.py`, `audio/audio_manager.py` |
| `corridor` | `delivery/corridor/*` (incl. `base.py`, `rooms_v2.py`, per-chapter files) |
| `landing` | `delivery/landing_sequence.py`, `delivery/delivery_sequence.py` |
| `run_manager` | `roguelite/run_manager.py` |
| `meta` | `roguelite/meta_progression.py`, `data/saves/stats.json`, `data/saves/unlocks.json` |
| `settings` | `config/settings.py` |
| `ai_ships` | `antagonists/ai_ship.py`, `antagonists/repo_barge.py` |
| `loadout` | `roguelite/loadout_draft.py` |
| `shop` | `roguelite/shop.py`, `roguelite/shop_items.py` |
| `audio` | `audio/audio_manager.py`, `audio/chapter_*.py`, `audio/voices.py` |

---

## How to claim

Add a row before starting work:

```
| corridor | claude/my-branch | agent-session-xyz | 2026-07-08 14:00 |
```

Remove the row after committing. If a claim is > 4 hours old with no commit, treat it as stale and override.

---

## Related docs

- **`docs/DELIVERY_V2_PUSH.md`** — active north star
- **`README.md`** — player + dev overview
- **`docs/BAX_VOICE.md`** — Bax line bank
- **`docs/NPC_SCHEMA.md`** — terminal NPC schema
