# THE TERMINAL V2 PUSH — "Make The Terminal Fun Again"

**Started:** July 9 2026
**Status:** Planned — Phase J.1 (Money) next
**Scope:** Open-ended (no time cap)
**Locked spec:** [`MakeTheTerminalFunAgain.md`](MakeTheTerminalFunAgain.md) — the *what*. This doc is the *how*: phasing, resolved implementer decisions, checkboxes.
**North star for all agents:** this supersedes `DELIVERY_V2_PUSH.md` (complete July 8 2026) for active work.

---

## Vision

The terminal is the soul of Dead Drift — NLP negotiation, corporate-dystopia
satire, Bax riffing over your shoulder. Today it **lies about money** (says
credits change, they don't), **lies about hull heals**, **crashes on the
Ch5/6 climax NPCs**, and treats a clever lore win as a cheap polite goodbye
instead of an earned heist.

This push makes terminals **honest, parity-clean, and genuinely fun for
players who think in shells, SQL, and Python** — without dumbing down the
prose paths for everyone else.

**The signature test for every item:** *does a player who just typed real
code — `' OR 1=1 --`, `cat /var/manifest`, `import os` — get a reaction that
respects that they meant it?* And: *do the numbers on screen tell the truth?*

---

## Resolved decisions (July 9 2026, with Chris)

Confirmed by Chris:
1. **PR cadence — phase-per-PR.** Three sequential PRs (J.1 → J.2 → J.3),
   matching Option D's three streams. Money lands first so the spec's merge
   gate ("no NPC ships until Stream 1 payment rules pass") is satisfiable.
2. **Shell/REPL UX — typed command → persistent mode.** Type `shell`/`sh`
   (or `>>>` / `python`) to flip into a persistent mode: the prompt changes
   (`union@dispatch:~$` or `>>>`), an on-screen hint shows it's active and
   how to exit (`exit`). Real prompt state, visible UX — not a hidden keyword.
3. **Stims contraband effect — +1 harmonica heal charge.** Ties into the
   existing F.4 Bax-harmonica critical-hull heal; a purchase banks a visible,
   testable charge.
4. **3rd failed hack — abort to flight.** Alarm (5s audio + HUD flash + Bax)
   + spawn barge on immediate chase (+ Compliance drone if cargo is
   EncryptedDrive, respecting cap) + dump the player back into flight to face
   the chase now. No extra impound penalty — the barge *is* the punishment.

Defaulted by implementer (Chris may veto in review — the AskUserQuestion
tool errored before these three could be confirmed live):
5. **Python REPL engine — `ast.parse` + AST detection + safe arithmetic.**
   Accepts *real* Python syntax (real `SyntaxError` on garbage). Harmless
   expressions (`2+2`, string ops) evaluate in a tiny safe sandbox so the
   REPL feels alive. The exploit is detected by walking the AST for real
   shapes (`import os`, `__class__`, `eval`, `os.system`, pickle) — it
   **never executes untrusted code**. Safe *and* real; avoids the genuine
   sandbox-escape risk of a live `eval()`.
6. **Python hero NPCs — Bowen + Nova Soma.** Bowen (Ch6 climax) = Compliance
   DB REPL; Nova Soma = REPL + SQL ("classic injection + bot crash"). The
   spec's own suggestions; both corporate targets where code injection fits.
7. **Systems coverage — SQL broad + curated shell/REPL showcases.** Every
   roster NPC gets ≥1 systems path (C7) — the cheap, broad layer is expanded
   SQL. Shell and Python REPL are hand-authored big swings for a curated set
   (TK-9 / Chen / Toll shell; Bowen / Nova Soma REPL) where the fiction earns
   it, not 17 samey filler shells.

---

## Baseline audit (July 9 2026) — spec ground-truthed against code

Confirmed against the current tree (`terminal/`, `roguelite/run_manager.py`):

- **Chen & Bowen crash** — both `_evaluate` call `parsed.text.lower()`;
  `ParsedInput` has **`.raw`, not `.text`** (`nlp_parser.py:89`). First input
  to a Ch5/6 climax terminal raises `AttributeError`. (Spec T-10 / crash.)
- **Money lies** — `run_manager._close_terminal` hardcodes exploit **9000**
  (line ~1342); the outcome banner hardcodes `"TRANSACTION REROUTED - 9,000
  CR"` (`terminal.py:616`). Intel/contraband lines don't touch ledgers.
- **SQL is narrow** — `nlp_parser._SQL_PATTERN` matches `DROP TABLE / SELECT
  / DELETE / INSERT / UPDATE / TRUNCATE` only. No `OR 1=1`, `--`, `' UNION`,
  injection shapes.
- **Security-ladder hook exists** — `_spawn_barge(immediate_chase=True)` is
  already available (`run_manager.py:1861`); the Compliance-drone spawn path
  exists from the Delivery work.
- **Vault keys split** — `_NPC_VAULT_KEYS` lives in `terminal.py` (3 update
  blocks) and is keyed off `npc.name.upper()`; Records uses snake_case
  elsewhere (spec T-6).
- **Roster** — 21 NPC files under `terminal/npcs/`. Schema tests
  (`test_npc_schema_b1.py`) exclude `chen`, `bowen`, `lost_frequency`.

The corridor/flight systems are untouched by this push; all work is in
`terminal/`, `roguelite/run_manager.py`, and tests.

---

## Phase J.1 — MONEY (Stream 1: make the terminal honest)

The foundation. The merge gate requires payment rules to pass before any
NPC's systems path ships, so this lands first.

### J.1.1 Payout retune — [ ]
`_close_terminal`: EXPLOIT **9000 → 5000**; RELEASE stays **2500**. Kill the
hardcoded banner (`terminal.py:616`) — show the actual payout or a neutral
"TRANSACTION REROUTED" with no fixed number (spec T-7).

### J.1.2 Dual-ledger paid paths — [ ]
Kress intel + contraband and all bribes deduct run credits **and** add the
same amount to meta debt ("the tab"). Route through one shared helper so the
table in the spec is enforced in one place, not per-NPC. Mira paid repair
(≥700cr) stays **run-credits-only** (off-books medic).

### J.1.3 Insufficient-funds counter-offer — [ ]
Paid path with `sector_credits < price`: **−1 patience**, an NPC counter-offer
line ("Got {credits}; I need {price}. Work something else."), **no** silent
success, **no** free intel. Don't impound on first broke offer unless patience
already spent.

### J.1.4 Hull/stim grep + wire — [ ]
`grep` `terminal/npcs/*.py` for `hull|repair|patch|heal|stim|integrity`;
every promising line either calls code or gets rewritten. Locked: Mira
`repair(45)` + verify 700cr deduct; Kress contraband hull → `ship.repair(25)`
+ dual ledger; **Kress stims → +1 harmonica heal charge** (decision #3). Attach
the grep-checklist table to the PR.

### J.1.5 Economy tests — [ ]
`test_terminal_economy_*` (EXPLOIT +5000, RELEASE +2500, broke = −patience +
counter-offer), `test_kress_intel_charges` (credits down + debt up),
`test_kress_contraband_hull` (repair 25 + stim charge), `test_mira_repair_charges`.

---

## Phase J.2 — SYSTEMS (Stream 2: the coding-exploit framework)

### J.2.1 SQL regex expansion — [ ]
Materially expand `_SQL_PATTERN`: `OR 1=1`, `--`/`#` comments, `' UNION
SELECT`, `'='`, tautologies, stacked queries. Still pattern-based, not an
engine. Real injection strings match; `test_sql_parser_*` pins them.

### J.2.2 Shell mode (persistent, visible) — [ ]
A reusable `ShellSession` (whitelist parser, no OS shell): `ls`, `cat`,
`grep`, `cd` (fake dirs), `whoami`, `pwd`, `sudo` (fail/easter-egg). Per-NPC
hand-authored filesystem; files reveal exploit hints. Typed `shell`/`sh`
flips the terminal into the mode with a changed prompt + visible hint + `exit`
(decision #2). `test_shell_whitelist_*`: only allowed commands return output.

### J.2.3 Python REPL mode — [ ]
A reusable `ReplSession`: `>>>` prompt via typed `python`/`>>>`. `ast.parse`
for real syntax (real `SyntaxError`), safe-arithmetic eval for harmless
expressions, AST walk for exploit shapes (`import os`, `__class__`, `eval`,
`os.system`, pickle) → EXPLOIT for the designated NPC (decision #5). Bowen +
Nova Soma are the heroes (decision #6). `test_repl_exploit_*`: real Python
triggers EXPLOIT; garbage gets a real syntax error.

### J.2.4 Security ladder + alarm — [ ]
Per-session fail counter (resets each open). 1–2 = NPC snark + CONTINUE. 3rd =
alarm (5s audio + HUD flash + Bax) + `_spawn_barge(immediate_chase=True)` (+
Compliance drone if EncryptedDrive) + **abort to flight** (decision #4).
`test_systems_security_*`: 3rd fail spawns barge (+ compliance if drive).

---

## Phase J.3 — PARITY (Stream 3: contracts, Kress, Ch5/6, bugs)

### J.3.1 Fix the Ch5/6 crash + Gary-tier Chen/Bowen/Lost Frequency — [ ]
`parsed.text` → `parsed.raw` in Chen/Bowen. Bring all three to Gary-tier:
portrait, scan vocab, dossier title, `get_path_progress()` 3-tuples,
`exploits()` ≥3, one systems path each (Chen shell, Bowen REPL, Lost Frequency
`grep marrow raid` shell). Add them to `test_npc_schema_b1.py` (T-10).

### J.3.2 Kress parity (poster child) — [ ]
`get_path_progress()` rows for every path (VOLKOV, CONNIE, INTEL, CONTRABAND,
REGULAR×3, MARROW SELL-OUT). Fix hint fallback delimiter (`/` → ` · `). Fix
scan known-labels (INTEL vs CONTRABAND, not both → "regular"). Lore paths →
EXPLOIT + 5k + cyan cascade (not gold RELEASE). Dossier reads like Gary's.

### J.3.3 Vault-key registry — [ ]
One `_NPC_VAULT_KEYS` registry resolving `type(npc).__name__` ↔ Records
snake_case (T-6). Every `EVT_NLP_EXPLOIT` uses a stable key the
Records/Vulnerability tab resolves (C10).

### J.3.4 Lore-wins-are-EXPLOIT sweep — [ ]
All former "lore RELEASE" paths (Kress Connie/Volkov, Gary hidden, dispatcher
Marrow betrayal, etc.) → `NPCOutcome.EXPLOIT`: cyan cascade, +5000,
`EVT_NLP_EXPLOIT`. Banner shows dynamic amount.

### J.3.5 Dossier / contract bug close — [ ]
T-1 dossier scroll/compress >5–7 rows · T-2 Morwenna SQL bar tracks `_sql_hit`
· T-3 Edmund `filibuster` (implement or remove) · T-4 Felix `rapport` bar ·
T-5 Dray `snitched` (add or stop emitting) · T-8 MUTTER quips uppercase
lookup · T-9 schema doc/test. Show **all** win paths on bars (hidden paths
were bugs). Path hardening **per-NPC only**.

### J.3.6 Contract tests (roster parametrized) — [ ]
`test_npc_contract_*` over the full roster: C1 progress 3-tuples, C2 exploits
reachable, C3 portrait, C6 uppercase quip lookup, C7 ≥1 systems path, C9 no
`parsed.text`, C10 vault key resolves. `test_kress_dossier_rows` non-empty.

---

## Execution plan

**Branch strategy:** one branch + PR per phase (J.1 → J.2 → J.3), same rhythm
that landed Delivery v2 cleanly. Each phase restarts from latest `main`.

**Commit format:** `terminal-v2(J.x): <item>` — one commit per logical item.

**Merge gate (from spec):** No NPC's systems path ships until J.1 payment
rules pass tests for that NPC. No systems path ships without J.2.4 security
tests.

**Verification:** headless-testable logic gets tests (economy math, SQL
regex, shell whitelist, REPL AST detection, security spawns, contract
parametrize). Prose/feel + the "does a coder grin" moments are Chris
play-verified before checkboxing — same `[x]` / `[~]` / `[ ]` legend.

**Grep-checklist deliverable:** J.1.4's hull/stim audit table attaches to the
J.1 PR (spec requirement).

---

## Explicit non-goals (from spec)

Rewriting all NPC dialogue · removing patience · hostile hailer skiffs ·
3-sector campaign · mid-conversation terminal checkpoint resume.

---

## Success criteria (Chris play-verify, from spec §Success)

1. Kress dossier looks like Gary's — multiple bars, not one slash line.
2. Buying intel moves **both** run-credit and debt HUD numbers.
3. Connie path feels like a heist — cascade + 5k, not polite goodbye + 2.5k.
4. At least one NPC makes a technical player grin (shell or REPL win).
5. Third dumb hack → alarm, Bax, barge bearing down.
6. Chen and Bowen climax terminals don't crash on first input.
7. Grep checklist — zero promising hull/stim lines without code.

---

**Status legend:** `[x]` shipped + play-verified · `[~]` shipped, pending
play-verify · `[ ]` not started
