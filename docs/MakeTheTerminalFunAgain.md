# MAKE THE TERMINAL FUN AGAIN

**Status:** Spec locked — implementation pending  
**Last updated:** July 2026  
**Companion:** [`Issues.md`](Issues.md) (combat, checkpoints, EncryptedDrive, paperwork)  
**Push mode:** **Option D** — money/hull wiring, coding-exploit framework, and NPC contract parity **in parallel**.

Do **not** implement from this doc until Chris greenlights the push.

---

## Problem statement

The terminal is the soul of Dead Drift — NLP roguelike negotiation, satirical corporate dystopia, Bax as co-pilot. Today it **lies about money**, **lies about hull heals**, **crashes on Ch5/6 NPCs**, **shows Kress as one line of hint text**, and treats **lore wins as cheap RELEASE** instead of earned **EXPLOIT** moments.

This push makes terminals **honest**, **parity-clean**, and **fun for players who think in shells, SQL, and Python** — without dumbing down the prose paths for everyone else.

---

## Locked economy rules

### Run credits vs meta debt

| Transaction type | Run credits (`_sector_credits`) | Meta debt (`meta.add_debt`) |
|------------------|--------------------------------|-----------------------------|
| **Kress intel** (priced lines in dialogue) | Deduct at success | **Also** add same amount to meta debt (“tab”) |
| **Kress contraband** (jammer, hull, stims) | Deduct at success | **Also** add to meta debt |
| **Bribe** (Gary, Felix, Holt, etc.) | Deduct at close via `bribe_cost()` | **Also** add via existing bribe path |
| **Mira paid repair (≥700 cr)** | Deduct at success | **No** meta debt (off-books medic) |
| **Terminal win — EXPLOIT** | **+5,000** (`pay_off` + sector credits) | Reduces debt (existing `pay_off`) |
| **Terminal win — RELEASE** (non-exploit) | **+2,500** | Reduces debt |
| **Insufficient funds** | See failure rules below | No charge |

**Rationale:** Chris locked **lower terminal rewards** — exploit flat **5k** (was 9k). Release stays **2.5k**. Purchases must hit **both** ledgers where table says “both.”

### Insufficient funds

When player triggers a paid path but **`sector_credits < price`**:

1. **−1 patience**  
2. **Counter-offer** NPC line (e.g. “Got {credits} on you — I need {price}. Work something else.”)  
3. **No** silent success; **no** free intel

Do **not** impound on first broke offer unless patience already exhausted.

### Lore wins → EXPLOIT

All former “lore exploit” paths (Kress Connie/Volkov/regular, Gary hidden paths, etc.) → **`NPCOutcome.EXPLOIT`** with:

- **Cyan exploit cascade** VFX (not gold RELEASE banner)  
- **+5,000** credit package  
- **`EVT_NLP_EXPLOIT`** for vault/Records  
- Outcome banner **must not** hardcode “9,000 CR” — use dynamic amount or “TRANSACTION REROUTED”

### Outcome banner

Replace hardcoded `TRANSACTION REROUTED - 9,000 CR` with **actual payout** or neutral copy.

---

## Locked UX / session rules

| Rule | Decision |
|------|----------|
| **Patience** | Keep current turn-based system (no wall-clock timer). |
| **Dossier paths** | Show **all win paths** on bars (hidden paths were **bugs** — fix Gary/Sandra/etc.). |
| **Path hardening** | **Per NPC only** — winning “BRIBE” on Holt must not block Felix “BRIBE”. Same NPC replay can still harden. |
| **Chen / Bowen / Lost Frequency** | **Full Gary-tier** terminals (portrait, scan, dossier, schema tests). |
| **Terminal length** | No forced timer. |

---

## Coding exploit framework (REAL)

Every terminal gets **≥1 systems path**. Three layers:

### 1. SQL (real fragments)

**Current:** `nlp_parser._SQL_PATTERN` matches `DROP TABLE`, `SELECT`, etc.

**Target:** **Expand regex materially** — include `OR 1=1`, `--` comments, `' UNION`, common injection shapes. Still pattern-based (not a full SQL engine).

**NPCs with SQL today:** TK-9, Morwenna, Nova Soma (partial). Extend per NPC in roster table below.

### 2. Fake shell (Linux-style)

**Target:** **Big swing** — terminal can enter **SHELL MODE** for applicable NPCs:

- Prompt e.g. `union@dispatch:~$` or `tk9:/var/manifest$`  
- **Whitelist commands only** — real subprocess-style parsing, **no** actual OS shell  
- Examples: `ls`, `cat`, `grep`, `cd` (fake dirs), `whoami`, `sudo` (fail or easter egg)  
- Output is **hand-authored** per NPC (files reveal exploit hints)

Toggle: explicit command (`shell`, `sh`, `debug`, NPC-specific) **or** UI button — pick at implementation; doc requires **visible shell UX**, not hidden keyword only.

### 3. Python REPL mode

**Target:** **REPL toggle** (`>>>` prompt) for applicable NPCs:

- **Real Python subset** — safe eval sandbox OR pattern match on dangerous tokens (`import os`, `__class__`, `eval`, pickle)  
- Success = EXPLOIT path for that NPC’s one systems route  
- Fail = snark path (see security ladder)

**Chris locked REAL REAL REAL** — not fake synonyms. Implementation must accept actual syntax; sandbox is engineering detail.

### Security ladder (failed systems attempts)

Per **terminal session** (counter **resets each open**):

| Attempt | Result |
|---------|--------|
| 1–2 | NPC **snark + CONTINUE** (patience unchanged unless design says otherwise) |
| 3 | **Security alert** — see below |

### Security alert (3rd failed systems attempt)

1. **5-second alarm** — audio + HUD flash + Bax line  
2. **Repo barge immediate chase** (`_spawn_barge(immediate_chase=True)`)  
3. If cargo is **EncryptedDrive** → **also spawn Compliance drone** (respect cap)  
4. Terminal may **force close** (IMPOUND or abort) — implementation choice; minimum is alarm + spawns

---

## Hull & gameplay promises (grep checklist)

**Rule:** Any NPC dialogue that promises **hull repair**, **patch**, **stims**, or measurable buff must **call code**. Run **`grep`** on `terminal/npcs/*.py` for: `hull`, `repair`, `patch`, `heal`, `stim`, `integrity` before ship.

### Locked fixes

| Source | Promise | Implementation |
|--------|---------|----------------|
| **Mira Voss** | Paid/intel/cargo/tech patch | Already `ship.repair(45)` — verify **700 cr run credit** deduct at success |
| **Kress contraband** | “So is your hull” | **`ship.repair(25)`** + dual ledger charge per contraband price in line |
| **Kress contraband stims** | Bax “enthusiastic” | **Actual gameplay effect** (define: e.g. +1 harmonica heal charge, 30s reduced harm cooldown, or +Bax voice mode — implementer picks one visible effect and documents in commit) |

### Audit deliverable

Before closing MTTFA, attach **grep checklist table** to PR: every matching line → wired or rewritten.

---

## NPC contract v1 (every roster terminal)

Each NPC in `terminal/npc_logic.py` factory + schema tests must pass:

| # | Requirement |
|---|-------------|
| C1 | **`get_path_progress()`** — 3-tuple rows `(name, cur, max)` for dossier bars |
| C2 | **`exploits()`** — every key reachable OR removed; ≥3 for schema NPCs |
| C3 | **Portrait** in `npc_portraits.py` |
| C4 | **Dossier title** in `_NPC_DOSSIER_TITLE` |
| C5 | **Scan vocab** + **known labels** aligned with vault keys |
| C6 | **Courier quips** — lookup uses **`name.upper()`** |
| C7 | **≥1 systems path** (SQL, shell, or REPL — one per NPC) |
| C8 | **Payments** follow economy table |
| C9 | **No `parsed.text`** — use `parsed.raw` |
| C10 | **`EVT_NLP_EXPLOIT`** uses stable vault key; Records/Vulnerability tab resolves |

### Kress parity (priority poster child)

- Add **`get_path_progress()`** rows: VOLKOV, CONNIE, INTEL, CONTRABAND, REGULAR×3, MARROW SELL-OUT, BRIBE if any  
- Fix hint fallback delimiter (`/` → ` · `) or remove fallback for Kress entirely  
- Fix scan known-labels: INTEL vs CONTRABAND not both → `"regular"`  
- Intel/contraband: **charge both ledgers**; contraband hull **+25**; stims **gameplay effect**  
- Lore paths → **EXPLOIT + 5k + cascade**

### Tier-2 NPCs (Ch5/6 + Marrow dead)

| NPC | Notes |
|-----|-------|
| **Chen** | Fix crash; Gary-tier tables; systems path TBD (suggest: shell `ls /chen/workshop`) |
| **Bowen** | Fix crash; Gary-tier; systems path TBD (suggest: SQL or REPL compliance DB) |
| **Lost Frequency** | Full terminal when Marrow dead; portrait; one systems path (e.g. `grep marrow raid` shell) |

---

## Known bugs to close (from audit)

| ID | Issue | Fix |
|----|--------|-----|
| T-1 | Dossier clips >5–7 paths | Scroll or compress rows |
| T-2 | Morwenna SQL bar hardcoded 0 | Track `_sql_hit` in progress |
| T-3 | Edmund `filibuster` in exploits, no logic | Implement or remove |
| T-4 | Felix `rapport` missing from dossier | Add bar row |
| T-5 | Dray `snitched` exploit not in dict | Add or stop emitting |
| T-6 | Vault keys `type(npc).__name__` vs Records snake_case | Unified `_NPC_VAULT_KEYS` registry |
| T-7 | Outcome banner 9k hardcode | Dynamic 5k/2.5k |
| T-8 | MUTTER quips case mismatch Gary/Sandra | Uppercase lookup |
| T-9 | Schema doc references missing test | Fix doc or add test |
| T-10 | `chen`, `bowen`, `lost_frequency` excluded from schema tests | Add to `test_npc_schema_b1.py` |

---

## Roster work table (fill during implementation)

| NPC | Systems path type | Shell / SQL / REPL hook | Payment notes |
|-----|-------------------|-------------------------|---------------|
| Gary | TBD | e.g. shell `cat article7.txt` | Bribe dual ledger |
| TK-9 | SQL + shell | Expand SQL; shell `/var/log` | — |
| Dispatcher | TBD | shell forms directory | Marrow betrayal = EXPLOIT |
| Kress | SQL or shell | Intel marketplace | Dual ledger all paid paths |
| Morwenna | SQL | CLAIM-7 inject | — |
| Sandra | TBD | — | — |
| Krellborn / pirate | TBD | — | — |
| Marrow / Lost Frequency | TBD | radio freq shell | — |
| Felix | TBD | — | Bribe |
| Holt | TBD | — | Bribe |
| Toll Authority | TBD | shell permits | — |
| Nova Soma | SQL + REPL | Classic injection + bot crash | — |
| Mira Voss | TBD | tech terms OR shell medbay | Run credits only |
| Dray | TBD | — | — |
| Edmund / Vince | TBD | Union charter shell | — |
| Chen | TBD | workshop shell | Climax |
| Bowen | TBD | compliance REPL | Climax |

*Implementation fills “TBD” with one concrete path each before PR merge.*

---

## Parallel workstreams (Option D)

```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ Stream 1: MONEY     │  │ Stream 2: SYSTEMS   │  │ Stream 3: PARITY    │
│ Dual ledger         │  │ Shell UI            │  │ Kress dossier       │
│ 5k / 2.5k payouts   │  │ REPL toggle         │  │ Chen/Bowen/Lost F.  │
│ Hull grep + wire    │  │ SQL regex expand    │  │ Contract tests      │
│ Counter-offer broke │  │ Security ladder     │  │ Vault key registry  │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
           │                          │                          │
           └──────────────────────────┴──────────────────────────┘
                              Integration PR
                         (one branch or coordinated 3)
```

**Merge gate:** No NPC ships until Stream 1 payment rules pass tests for that NPC. No systems path ships without security ladder tests.

---

## Test plan (minimum)

| Test | Asserts |
|------|---------|
| `test_terminal_economy_*` | EXPLOIT +5000, RELEASE +2500, broke offer −patience + counter-offer |
| `test_kress_intel_charges` | Run credits down + meta debt up on priced intel |
| `test_kress_contraband_hull` | repair(25) on hull line |
| `test_mira_repair_charges` | 700 cr deducted, repair applied |
| `test_systems_security_*` | 3rd fail spawns barge (+ compliance if drive) |
| `test_npc_contract_*` | Parametrize roster: progress tuples, portrait key, no parsed.text |
| `test_kress_dossier_rows` | get_path_progress non-empty |
| `test_sql_parser_*` | Expanded patterns match real injection strings |
| `test_shell_whitelist_*` | Only allowed commands return output |
| `test_repl_exploit_*` | Valid python path triggers EXPLOIT on designated NPC |

---

## Explicit non-goals (this push)

- Rewriting all NPC dialogue from scratch  
- Removing patience system  
- Making faction hailer skiffs hostile or killable  
- 3-sector campaign  
- Full terminal mid-conversation checkpoint resume  

---

## Success criteria (Chris play-verify)

1. **Kress dossier** looks like Gary’s — multiple progress bars, not one slash line.  
2. **Buying intel** moves numbers on **both** run credits and debt HUD.  
3. **Connie path** feels like a **heist** — cascade + 5k, not a polite goodbye + 2.5k.  
4. **At least one NPC** makes a technical player grin (shell or REPL win).  
5. **Third dumb hack attempt** → alarm, Bax, barge bearing down.  
6. **Chen and Bowen** climax terminals don’t crash on first input.  
7. **Grep checklist** — zero promising hull/stim lines without code.

---

## Reference: current exploit payout code

Today (`run_manager._close_terminal`):

- `outcome == "exploit"` → **9000** (changing to **5000**)  
- `outcome == "release"` and no bribe → **2500** (unchanged)  
- Bribe → `add_debt(bribe_paid)` + sector credit deduct  

This doc supersedes that **9000** value everywhere in design talk.
