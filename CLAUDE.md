# DEAD DRIFT — Agent pointer

Read this first. Do **not** use deleted or git-archived docs as current spec.

| Doc | Use for |
|-----|---------|
| **[docs/DELIVERY_V2_PUSH.md](docs/DELIVERY_V2_PUSH.md)** | **North star** — corridor/delivery overhaul (I.4 next) |
| **[docs/Issues.md](docs/Issues.md)** | **Locked spec** — combat, checkpoints, EncryptedDrive, paperwork |
| **[docs/MakeTheTerminalFunAgain.md](docs/MakeTheTerminalFunAgain.md)** | **Locked spec** — terminal economy, coding exploits, NPC parity |
| [README.md](README.md) | Player quick start, controls, feature overview |
| [WORKING_ON.md](WORKING_ON.md) | File-claim coordination before editing subsystems |
| [docs/BAX_VOICE.md](docs/BAX_VOICE.md) | Bax line bank + tone guide |
| [docs/NPC_SCHEMA.md](docs/NPC_SCHEMA.md) | Terminal NPC keyword/bribe floors (enforced by tests) |
| [docs/SOUNDTRACK_PLAN.md](docs/SOUNDTRACK_PLAN.md) | Audio design spec |
| [docs/RECORDING_BRIEF.md](docs/RECORDING_BRIEF.md) | Stem recording shot list |

Prior roadmaps (Improvement Plan, Aliveness push, corridor design notes, documentation status tracker, etc.) were **removed July 2026**. Git history has the old files. See [docs/archive/README.md](docs/archive/README.md).

---

## Git identity — always use this

```
git config user.name "Chris-dewitt"
git config user.email "chnodewi@unc.edu"
```

Never commit as Claude. Never add co-author lines.

---

## Repo sync (Dead-Drift remote)

**Target repo:** https://github.com/chris-dewitt/Dead-Drift

Push to `origin` from cloud sessions; user syncs to Dead-Drift from their machine:

```powershell
cd C:\Users\DELL\Documents\GitHub\Dead-Drift
git fetch https://github.com/chris-dewitt/chris-dewitt <branch-name>
git merge FETCH_HEAD --allow-unrelated-histories -X theirs -m "Sync from dev branch"
git push origin main
```

---

## Physics rule (flight only)

Never multiply force by `dt` at the call site — `RigidBody2D.integrate(dt)` handles that.

Corridor platformer kinematics in `delivery/corridor/base.py` are hand-rolled — the dt rule does not apply there.

---

## Tuning constants

| Constant | Value | Where |
|----------|-------|-------|
| `MAX_VELOCITY` | 280 px/s | `config/settings.py` |
| Slingshot overdrive cap | 420 px/s (1.5×) | `config/settings.py` |
| Corridor feel + reward | coyote, buffer, chains, star thresholds | top of `delivery/corridor/base.py` |

---

## Current push status (July 2026)

| Push | Doc | Status |
|------|-----|--------|
| Delivery v2 | `DELIVERY_V2_PUSH.md` | I.1–I.3b shipped `[~]`; **I.4** next |
| Issues + Terminal | `Issues.md` + `MakeTheTerminalFunAgain.md` | **Spec locked** — implement when Chris greenlights |

Update checkboxes in active push docs only. Do not recreate deleted roadmaps.
