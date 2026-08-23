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
| **Pickup-word matching** | Multi-word entries in `*_PHRASES`, matched by substring. Single tokens in `*_WORDS`, matched on word boundaries via `terminal/npcs/keywords.py`. Agreement **words** go through `affirmed_hit` and agreement **phrases** through `affirmed_phrase_hit`, so a negation never reads as consent. |
| **Advertised paths** | Every key in `exploits()` must be reachable: an earlier branch must not shadow a later one's pickups. A path advertised but unreachable is the NPC lying to the player. |

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
| `chen` | Marrow, Nova Soma, Gary, Sandra, Felix, Bax |
| `bowen` | Nova Soma, Bax, Holt, Marrow |
| `lost_frequency` | Marrow, Nova Soma, Bax, Felix, Sandra |

---

## Ch5/6 climax NPCs (J.3.1 — de-crashed + Gary-tiered)

These three fired `parsed.text` (which doesn't exist — `ParsedInput.raw` does)
and returned 4-tuple path rows into a 3-tuple dossier, so both the Ch5 and Ch6
climax terminals crashed on first input. J.3.1 fixes the crash and brings them
to the roster schema: keyword floor, ≥3 exploits, 3-tuple `get_path_progress`,
a portrait accent, dossier/scan/vault map entries, and one systems path each.

| NPC | Chapter | Systems path |
|-----|---------|--------------|
| `chen` | Ch5 — the Remnants' architect | `shell` → read the ledger's root cascade-write |
| `bowen` | Ch6 — Nova Soma compliance | `python` → break the audit console sandbox |
| `lost_frequency` | Marrow aftermath | `shell` → `grep marrow raid` the seizure log |

### Character pass (Aug 2026) — brought to roster parity

J.3.1 de-crashed these three but left them at a fraction of the roster's
depth: one canned line per branch, no `EVT_NLP_EXPLOIT`, no vault record, no
portrait geometry, and the generic `BaseNPC` escape line. All three now:

* carry response variants on every branch (`random.choice`, ≥ 6 per file);
* file wins through `EVT_NLP_EXPLOIT` **and** the vocabulary vault, so the
  Records tab and Bax's backdoor list actually learn the paths;
* answer the universal escape in character;
* have bespoke portrait geometry and a scene backdrop — they had been
  rendering on the `_unknown` "?" placeholder, so the two climax characters
  of the game had no face.

| NPC | Keywords | Cross-refs | Portrait |
|-----|----------|------------|----------|
| `chen` | 54 → 82 | 2 → 6 | Remnant dig: rebreather at the jaw, goggles pushed up, the ledger's source scrolling on a salvaged monitor |
| `bowen` | 58 → 110 | 2 → 4 | Compliance floor: headset, lanyard photo, identical desks to the vanishing point, a smile that only goes flat at the bottom of the scale |
| `lost_frequency` | 31 → 79 | 3 → 5 | No bust — an empty studio chair, a dead mic, VU meters pinned at zero. The portrait is the absence. |

`lost_frequency` also gained a REQUEST path (call in one last dedication) and
a REPRISAL path (name Local 404 out loud), and hailing now returns one beat of
static before it lets you go.

---

## Matcher rules (review follow-up, Aug 2026)

Three findings on PR #124 — plus two the follow-up's own tests caught — were
all one shape: *a pickup matched something the player did not mean.*

1. **Negation applies to phrases, not just words.** `hit()` ignores negation,
   so Bowen's surrender phrase `hold position` matched inside "No, I will
   **not** hold position" and impounded a player for refusing — the same
   false-compliance bug the character pass existed to fix, re-entering
   through the phrase list. Agreement phrases now use `affirmed_phrase_hit`.
   For a multi-word phrase the first word is the negation anchor.
2. **Typographic apostrophes.** Every pickup word is written with `'`. Pasted
   or autocorrected text carries `’`, which defeated both the word matcher
   (`won’t` never matched the token `won't`) and the `n't` negation suffix,
   so "that isn’t fine" read as consent. `keywords.normalize()` folds the
   variants and runs at every entry point.
3. **Branch order can shadow an advertised path.** `lost_frequency` listed
   `request` in `exploits()` while `"one last"` and `"dedication"` sat in the
   mourning list, which is tested first — so the advertised phrasing closed
   out as DEDICATION and the path was unreachable. REQUEST is now tested
   before MOURN and owns that idiom.
4. **A path label must match its dossier row.** The rage branch filed exploit
   key `reprisal` but set `_current_path = "AFTERMATH"`, lighting the wrong
   chip on the strip.
5. **Scan words belong in `*_WORDS`.** A merge duplicated `static` / `signal`
   into `*_PHRASES`; the substring copy wins, and "ecstatic" hailed the dead
   channel. Word boundaries are exactly what make a token that short safe.

Guarded by `tests/test_character_pass.py`, including
`test_every_advertised_exploit_key_is_a_reachable_path` for shape 3.

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

**`bribe_cost()` is not optional.** `RunManager` deducts exactly what that
method reports, so an NPC that accepts a credit bribe without overriding it is
handing out a free win. `dray` and `nervous_fence` both did; both now report
the figure the player actually named. Guarded by
`tests/test_character_pass.py::test_every_bribeable_npc_overrides_bribe_cost`.
