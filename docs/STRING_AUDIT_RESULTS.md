# DEAD DRIFT — String Audit Results (Epic 9.4)

**Date:** May 25 2026  
**Scope:** Full game-wide pass per `NEXT_PUSH.md` §9.4  
**Tool:** `tools/string_audit_scan.py` (72 production `.py` files under `core/`, `roguelite/`, `terminal/npcs/`, `delivery/`, `ship/`, `bax/`, `renderer/`)

---

## Summary

| Metric | Result |
|--------|--------|
| Files scanned | 72 |
| Generic/placeholder flags | 18 |
| Intentional in-character flags | 17 (TK-9 `ERROR:` exploit lines) |
| True bland strings fixed this pass | 0 critical — copy already at bar |
| Propaganda / sector flavor | Already expanded (loadout ticker 17 lines, procedural formerly-names 36 entries) |

**Verdict:** The string audit **passes**. Player-facing copy is overwhelmingly in-universe, darkly comic, and consistent with the Bax / Nova Soma tone benchmark. No customer-service FAQ strings remain in hot paths.

---

## Scan methodology

1. Regex extract quoted strings 6–100 chars from gameplay modules.
2. Flag matches against generic patterns: `Error`, `Success`, `Failed`, `Loading`, `Please wait`, `Press X to`, `Click`, bare `OK`.
3. Manual review of all flags — distinguish intentional diegetic text from real gaps.

---

## Findings by category

### Intentional (no change)

| Location | Notes |
|----------|--------|
| `terminal/npcs/synthetic_droid.py` | 17× `ERROR:` lines — SQL/paradox exploit flavor for TK-9. **Keep.** |
| `delivery/corridor/chapter1_archive.py` | "Loading dock" in level comment string — background art label, not UI. **Keep.** |

### Already at quality bar (sampled)

| Surface | Status |
|---------|--------|
| NPC keyword responses (11 types) | Epic 9.1 parity sweep complete — cross-NPC refs, dark humor, 15+ keywords each |
| Shop vendor intros | 8 lines — corridor dead-zone flavor, Union references |
| Bax line banks | `bax/bax.py` + `docs/BAX_VOICE.md` — context-tagged, no generic filler |
| Sector designations | `procedural.py` — 12 corporate names + 36 "formerly" human names |
| Decanting screen | Rotating Nova Soma taglines, itemized invoice, "ACCEPT CHARGES (non-optional)" |
| Tutorial hints | `roguelite/tutorial.py` — Bax-voiced, mechanic-specific |
| HUD labels | Diegetic degradation copy in `ship/hud.py` |
| Terminal boot splash | Per-NPC encryption labels, signal meter, session timer |

### Minor drift (acceptable / deferred)

| Item | Notes |
|------|--------|
| `NEXT_PUSH.md` items 19–21 | Sector-5 capstones, death highlight reel, emotional theme polish — tracked in **Phase D–F** of `ALIVENESS_PUSH.md`, not string defects |
| Harmonica play-along UI | Epic 11.1b deferred — no strings to audit yet |

---

## Tone benchmark check

Target: *"GENUINE NOVA SOMA® PARTS IN EVERY CLONE"* (`loadout_draft.py` propaganda ticker).

Random sample passes:
- *"STATISTICALLY YOU WILL BE A CLONE BY DAY'S END. PLAN ACCORDINGLY."*
- *"Your debt is visible from orbit. I mean that literally. The creditors have a telescope."* (Kress)
- *"NON-COMPLIANCE: hull integrity penalty | Subsection 9, Union Charter | NON-NEGOTIABLE"* (HUD barge warning)

---

## Re-run instructions

```bash
python tools/string_audit_scan.py
```

After any new UI/NPC copy lands, re-scan and update this file if flags > 0 outside TK-9 `ERROR:` lines.

---

## Epic 9.4 status

**[x] COMPLETE** — May 25 2026. Full pass run; no blocking bland strings. Active work continues under `docs/ALIVENESS_PUSH.md` Phase D+.
