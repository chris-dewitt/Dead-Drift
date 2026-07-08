# NPC SCHEMA — keywords, bribes, exploits

**Maintained by:** `tests/test_npc_schema_b1.py` (regenerates this table on demand).
**Last audit:** May 25 2026

---

## Schema baseline

Every terminal NPC must meet:

| Field | Target |
|-------|--------|
| **Keyword count** | ≥ 15 distinct accepted pickup words across all paths |
| **Exploit count** | ≥ 3 distinct win paths |
| **Bribe label** | If a bribe path exists, the dossier `_current_path` must read `BRIBE [<amount> cr]` once a credit amount is mentioned (mirrors `terminal/npcs/dray.py`) |
| **Universal escape** | `fuck off` releases — handled in `BaseNPC.respond` (do not advertise) |
| **Cross-references** | At least 1 line mentioning another character (Bax / Gary / Sandra / Felix / Marrow / Nova Soma) |

---

## Audit (May 25 2026)

| NPC | Keywords | Exploits | Bribe format | Status |
|------|----------|----------|--------------|--------|
| `gary`                  |  58 | 6 | `BRIBE (no $)` → standardised in this PR | ✅ |
| `synthetic_droid` (TK-9) |  17 | 6 | no bribe path (paradox / SQL) | ✅ |
| `union_dispatcher`      |  24 | 6 | `BRIBE (no $)` → standardised in this PR | ✅ |
| `kress`                 |  14 | 3 | grease-favour path, not credits | **fixed in this PR — 14 → 22 keywords** |
| `insurance_adjuster` (MORWENNA) | 161 | 6 | claims/legal path, not credits | ✅ |
| `sandra`                | 133 | 5 | no bribe path (won't take them) | ✅ |
| `pirate` (KRELLBORN)    | 106 | 5 | `BRIBE (no $)` — bribes laughed off by design | ✅ |
| `underground_dj` (MARROW) | 114 | 5 | no bribe path (favours / vinyl trade) | ✅ |
| `toll_authority`        |  14 | 4 | `BRIBE (no $)` → standardised in this PR | **fixed in this PR — 14 → 19 keywords** |
| `nervous_fence` (FELIX) | 130 | 9 | `BRIBE (no $)` → standardised in this PR | ✅ |
| `cargo_inspector` (HOLT) |  67 | 5 | `BRIBE (no $)` → standardised in this PR | ✅ |
| `dray`                  | 102 | 3 | **`BRIBE [X cr]` (reference impl)** | ✅ |
| `nova_soma_collections` |  87 | 4 | no bribe path (debt/policy) | ✅ |
| `mira_voss`             |  67 | 4 | repair-service path, not bribe | ✅ |
| `idealist_rep` (EDDIE)  |  49 | 3 | bribes BACKFIRE by design — label kept as warning | ✅ |
| `corrupt_rep` (VINCE)   |  42 | 3 | `BRIBE (no $)` → standardised in this PR | ✅ |

**Audit numbers** above are pulled live by the headless probe in `tests/test_npc_schema_b1.py::test_audit_matches_schema_doc`. If a refactor moves a keyword list, the test re-counts; if the count drops below the baseline, the test fails with a pointer to this file.

---

## BRIBE label standardisation

Per the dray reference implementation, when a player offers a specific credit amount on any NPC that accepts bribes, `_current_path` is set to the literal string `f"BRIBE [{amount} cr]"`. This:

1. Surfaces the actual price in the dossier chip strip the moment it lands.
2. Lets the keyword-chip renderer show a comparable `BRIBE [3000 cr]` vs `BRIBE [1500 cr]` across all bribeable NPCs.
3. Distinguishes "offered a bribe but no amount" (path stays `BRIBE`) from "offered + accepted at X cr" (path becomes `BRIBE [X cr]`).

NPCs touched in this PR for label standardisation:
`gary`, `union_dispatcher`, `pirate`, `toll_authority`, `nervous_fence`, `cargo_inspector`, `idealist_rep`, `corrupt_rep`.

NPCs intentionally exempt:
`synthetic_droid`, `insurance_adjuster`, `sandra`, `underground_dj`, `dray` (already standard), `nova_soma_collections`, `mira_voss`.

---

## Cross-reference web

Every NPC mentions at least one other by name. Currently shipped (auto-discovered via name-grep in `tests/test_npc_schema_b1.py`):

| NPC | References on file |
|-----|-------------------|
| `gary` | Blevins, Sandra, Kress, Morwenna, TK-9, Marrow |
| `synthetic_droid` | Gary, Holt, Blevins |
| `union_dispatcher` | Gary, Blevins, Sandra |
| `kress` | Sandra, Marrow, Felix, Gary |
| `insurance_adjuster` | Gary, Sandra, Felix |
| `sandra` | Gary, Marrow, Holt |
| `pirate` | Kress, Marrow, Sandra, Local 404 |
| `underground_dj` | Gary (recordings), Sandra, Felix |
| `toll_authority` | Gary, Blevins, Local 404 |
| `nervous_fence` | Gary, Kress, Sandra, Morwenna, Marrow, Holt, Dray, TK-9 |
| `cargo_inspector` | Gary, Felix, Morwenna |
| `dray` | Gary, Mira, Felix, Sandra |
| `nova_soma_collections` | Gary, Holt, Sandra, Marrow, Felix |
| `mira_voss` | Gary, Sandra, Felix, Kress |
| `idealist_rep` | Gary, Blevins, Sandra, Felix, Bax |
| `corrupt_rep` | Krellborn, Gary, Eddie, Felix |

---

## Bribe negotiation flow (B.8)

When a bribeable NPC's bribe path triggers without a specific amount, the NPC asks for a number (turn 1). The player offers an amount (turn 2). The NPC either accepts, counters with a higher number, or refuses in character (turn 3). The current implementations are heterogeneous; the negotiation contract is locked here so future polish passes have a shared spec:

1. **Turn 1 — Bribe verb only.** Path = `BRIBE`. NPC asks for a figure.
2. **Turn 2 — Amount mentioned.** Path = `BRIBE [<amount> cr]`. NPC compares to their personal floor.
3. **Turn 3a — Floor met → RELEASE / EXPLOIT.**
4. **Turn 3b — Below floor → counter-offer or refuse.** NPC names their floor or speaks in character (*"I don't take bribes from Union men"* / *"Add another zero"*).

Reference implementations:
* `gary` — three-attempt bribe with disposition-driven softening.
* `dray` — single-shot, fast accept at 500+ cr.
* `corrupt_rep` — small bribes accepted; large bribes trigger the SHAKEDOWN flag.
