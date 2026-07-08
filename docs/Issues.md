# DEAD DRIFT — Issues Push

**Status:** Spec locked — implementation pending  
**Last updated:** July 2026  
**Companion:** [`MakeTheTerminalFunAgain.md`](MakeTheTerminalFunAgain.md) (terminal overhaul — runs in parallel)  
**North star (active corridor work):** [`DELIVERY_V2_PUSH.md`](DELIVERY_V2_PUSH.md)

Do **not** implement from this doc until Chris greenlights the push. This is the agreed bug/design fix list from codebase audit + playtest.

---

## Locked design decisions (summary)

| Area | Decision |
|------|----------|
| Barge gunfire | Hits 1–2 → **retreat** (existing). Hit 3 → **destroyed** (kaboom). Other barges unaffected. |
| Barge kill feedback | Reuse **satellite explosion** VFX + SFX. Player **gun SFX already exists**. |
| Barge kill stat | New Bax/Records stat: **`404s_86ed`** (not generic `lifetime_kills`). |
| Pirates | **Ambient `BEHAVIOR_PIRATE` only** — shootable, killable, gun added. |
| Faction hailers | **Invincible, non-hostile** — Kress/Marrow/Sandra/terminal pirate skiffs stay hailer-only. |
| Pirate gun | **1/5 player gun damage**, **3s cooldown**, **400px** range, **muzzle flash + tracer**. |
| Pirate kill reward | **500 run credits** bounty + Bax stat entry (not terminal EXPLOIT payout). |
| Compliance crash | `ComplianceVessel` emits `EVT_AISHIP_DESTROYED` but handler reads `is_pirate` → **must fix**. |
| Paperwork popup keys | **F and G only** — **H removed** from pool; **H = harmonica only**. |
| Checkpoints | **Option A** (minimal fidelity — see below). |
| EncryptedDrive | **A+B+C+D+E** — see EncryptedDrive section. |

---

## P0 — Crashes & hard breaks

### I-1 ComplianceVessel destroy crash

**Symptom:** Shooting down a Compliance drone crashes the game.

```
AttributeError: 'ComplianceVessel' object has no attribute 'is_pirate'
```

**Location:** `antagonists/compliance_vessel.py` emits `EVT_AISHIP_DESTROYED`; `roguelite/run_manager.py` `_on_aiship_destroyed` assumes `AIShip`.

**Fix direction:** Guard handler and/or dedicated event for compliance kills. Handler must not assume `is_pirate`. Pirate kill Bax lines must not fire on compliance.

**Verify:** Destroy compliance drone in Ch5/6 flight — no exception; correct Bax line only.

---

### I-2 Chen / Bowen terminal crash (latent)

**Symptom:** First keystroke in Chen or Bowen climax terminal → `AttributeError` on `parsed.text`.

**Location:** `terminal/npcs/chen.py`, `terminal/npcs/bowen.py` — field is `parsed.raw` per `nlp_parser.py`.

**Fix direction:** Use `parsed.raw`; add headless open + one-turn test per NPC.

---

### I-3 Chen / Bowen dossier crash (latent)

**Symptom:** Opening dossier panel → unpack error (`get_path_progress` returns 4-tuples; UI expects 3).

**Fix direction:** Align tuple shape with `terminal.py` `_draw_dossier` or fix progress API when Gary-style terminals land (see MTTFA).

---

## P1 — Combat & destruction

### I-4 Barge: retreat + kill (third hit)

**Current:** `RepoBarge.take_hit()` — 2 disruption hits → retreat only. `take_damage()` / `EVT_BARGE_KILLED` exist but **never called**.

**Target behavior:**

| Hit | Effect |
|-----|--------|
| 1 | Slowdown + Bax “keep shooting” feedback (existing). |
| 2 | **Retreat** — barge leaves sector ~22s (existing `DISRUPTION_HITS = 2`). |
| 3 | **Destroyed** — kaboom, **`404s_86ed`** stat +1, satellite explosion VFX/SFX. |

**Scope:** Does **not** suppress future barge spawns in the sector unless existing spawn logic already does. Does **not** affect other barges on field.

**Verify:** Three hits on same barge in one engagement → retreat then destroy on third; stat increments; explosion plays.

---

### I-5 Ambient pirate: gun + kill bounty

**Current:** Pirates **ram only** (`ai_ship.py` `ST_ATTACK`). Ambient spawns use `BEHAVIOR_PIRATE`. Faction skiffs use `BEHAVIOR_HAILER` and are **invincible** — **unchanged**.

**Target behavior:**

- Pirate fires weak projectile: **damage = player_damage / 5**, **cooldown 3s**, **range 400px**.
- **Muzzle flash + tracer** on fire (visible at combat distance).
- On kill: **+500 run credits** to `_sector_credits`, Bax stat increment, small Bax combat line (not 9k exploit copy).
- Reuse **satellite explosion** on destroy.

**Out of scope:** Shooting faction hailer skiffs (Kress hauler, Sandra courier, Marrow relay, terminal-open pirate skiff).

**Verify:** Jump-terminal pirate skiff hailer still bolts when shot; ambient pirate can be killed for 500 cr.

---

### I-6 Pirate / compliance kill handler hygiene

**Related to I-1.** Ensure:

- Compliance kill does not route through pirate-only Bax lines.
- Stats distinguish **404s_86ed** (barge), **pirate bounties**, compliance kills (define whether compliance gets its own stat or shares pirate bounty — default: **compliance separate stat TBD in MTTFA if needed**; minimum is no crash).

---

## P2 — Ch3 paperwork (Sentient Paperwork)

### I-7 Remove H from popup key pool

**Root cause:** `core/game.py` binds **H** to harmonica heal before `run_manager.handle_key()` → cargo never sees H.

**Target:** `_POPUP_KEYS` in `cargo/paperwork.py` = **F and G only**. H remains harmonica-only globally in flight.

**Verify:** Paperwork popup never asks for H; F/G file correctly; H always starts harmonica session (when allowed).

---

## P3 — Checkpoints (Option A)

Partial resume is intentional at this tier — **not** full terminal/corridor fidelity.

### I-8 AI ships not restored

**Symptom:** Resume mid-sector → ambient/hailer/pirate ships gone; hail state lost.

**Location:** `roguelite/run_checkpoint.py` — `_entities_to_dict` saves barges/compliance/debris but **not `_ai_ships`**.

**Fix direction:** Serialize/deserialize `_ai_ships` (class, behavior, state, pos, vel, hull, hail flags).

**Verify:** Save with pirate + Sandra hailer present → resume → both still there.

---

### I-9 `well_hit_times` saved but discarded

**Symptom:** Gravity-well core damage cooldown resets after resume → extra hull damage.

**Location:** `build_checkpoint` writes `well_hit_times`; `restore_checkpoint` sets `rm._well_hit_times = {}` without loading.

**Fix direction:** Restore saved dict.

**Verify:** Take well damage, save, resume — cooldown still active.

---

### I-10 Dossier carousel chapter override stuck

**Symptom:** Cargo Dossiers → replay Ch3 → beat chapter → loadout is **Ch3 again** instead of natural next chapter.

**Location:** `_begin_run_from_carousel` sets `_chapter_override`; `_exit_interstitial` calls `start_run()` **without** `set_chapter_override(None)`.

**Fix direction:** Clear override after dossier replay delivery completes (or on interstitial exit when not chaining another dossier pick).

**Verify:** Carousel Ch3 replay → win → override cleared; CONTINUE campaign resumes Ch4+.

---

### I-11 Campaign-end interstitial on every delivery after first full clear

**Symptom:** After clearing all 6 chapters once, **any** delivery (including dossier replay) shows campaign-complete interstitial → main menu.

**Location:** `core/game.py` `_enter_interstitial`: `campaign_end = next_ch > 6 or meta.campaign_cleared_at_least_once`.

**Fix direction:** `campaign_end` only when **this delivery actually completes chapter 6** (or final chapter of run), not when `campaign_cleared_at_least_once` alone.

**Verify:** Full-clear player replays Ch2 from dossier → interstitial for Ch2→3, not “campaign complete.”

---

## P4 — EncryptedDrive (Ch5–6)

Cargo docstring promises trace, pings, and pursuit — partially wired. All five slices approved.

### I-12 A — Trace scales compliance spawn rate

**Current:** Spawn cooldown fixed by chapter (22s Ch5 / 14s Ch6); **`trace_level` ignored**.

**Target:** Scale spawn cooldown with `trace_level` (0→1). Example anchor: **22s at trace 0 → ~8s at trace 1.0** (Ch5); Ch6 proportionally harsher. Cap concurrent drones unchanged (1 Ch5 / 2 Ch6) unless playtest says otherwise.

**Verify:** Damage cargo to raise trace → measurably faster spawns.

---

### I-13 B — Trace drives audio pressure

**Current:** `cargo_alarm_level()` reads AcousticArchive / shroom only — not EncryptedDrive.

**Target:** Feed `trace_level` into `cargo_alarm_level()` so Ch5/6 audio modules react (tempo/filter/threat motif per `audio/chapter_5.py` / `chapter_6.py`).

**Verify:** High trace audibly tenser than clean run (Chris ear pass).

---

### I-14 C — Bax ping on trace spikes

**Current:** `_ping_t` increments; nothing consumes it.

**Target:** On **trace spike** (hull damage → `+0.25 trace`), emit Bax line + optional HUD tag (not periodic timer). Align with SOUNDTRACK_PLAN signposting pattern.

**Verify:** Take hull hit with drive aboard → Bax reacts once per spike; no spam on decay.

---

### I-15 D — EMP (Q key)

**Current:** `_emp_burst_available` armed in some paths; `grant_emp_burst()` underused.

**Target:** **One Q press** — stuns **all compliance vessels + all barges** for **5s** (existing stub behavior). Available when flagged (Ch6 after Ch5 clear / corridor gift — wire `grant_emp_burst()` on Ch5 corridor complete if not already).

**Verify:** Q with EMP available → stun; Q without → Bax decline; README documents Q on Ch6.

---

### I-16 E — Ch6 upload as corridor timer

**Current:** Server room “90s upload” is dialog text only.

**Target:** **Corridor timer pressure** in Ch6 server-room / upload beat — reuse time-pressure mutator pattern (`CorridorMutator` / room flag). Player must **hold route or survive** until timer clears; not a separate flight minigame.

**Verify:** Ch6 corridor upload room fails if timer expires; success reaches escape corridor.

---

## P5 — Polish & low (track, don’t block push)

| ID | Issue | Notes |
|----|--------|-------|
| I-17 | HUD speed orange at 500 px/s | Never triggers vs MAX 280 — retune threshold |
| I-18 | Kill stats incomplete | Wire 404s_86ed, pirate bounties; compliance stat as needed |
| I-19 | No destroy VFX for AI kills today | Address in I-5 / I-4 via satellite explosion |
| I-20 | `EVT_KILL_SCORED` dead event | Remove or wire — cleanup |
| I-21 | Meta debt not auto-saved mid-run | Optional follow-up; not Option A scope |
| I-22 | Terminal checkpoint drops conversation | Out of Option A scope — note in README |

---

## Implementation order (suggested)

1. **P0** crashes (I-1, I-2, I-3)  
2. **P2** paperwork H (I-7) — tiny, high player pain  
3. **P1** combat (I-4, I-5, I-6)  
4. **P3** checkpoints (I-8–I-11)  
5. **P4** EncryptedDrive (I-12–I-16)  
6. **P5** as time allows  

**Parallel track:** [`MakeTheTerminalFunAgain.md`](MakeTheTerminalFunAgain.md) — Chris locked **Option D** (money + coding framework + NPC parity together).

---

## Test plan (minimum)

| Area | Test |
|------|------|
| Compliance kill | No crash; no pirate Bax line |
| Barge 3-hit | Retreat on 2, destroy on 3; 404s_86ed |
| Pirate ambient | Gun fires; kill +500 cr; hailer skiff still invincible |
| Paperwork | F/G only; H = harmonica |
| Checkpoint A | AI ships + well_hit_times round-trip |
| Carousel | Override clear + campaign_end fix |
| EncryptedDrive | Trace → spawn + audio + spike ping; EMP Q; Ch6 corridor timer |

---

## Out of scope (this push)

- 3-jump campaign shortening (scrapped)  
- Full checkpoint fidelity (terminal mid-conversation, corridor room index)  
- Faction hailer destroyability  
- Delivery v2 I.4 graphics (separate north star)
