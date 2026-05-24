# DEAD DRIFT — Agent pointer

**May 2026:** The old combined session doc + GDD that lived here is archived. Do **not** use it as current spec.

| Doc | Use for |
|-----|---------|
| [README.md](README.md) | Player quick start, controls, feature overview |
| [docs/IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md) | Implementation master plan (checkboxes, Phase 0) |
| [docs/DOCUMENTATION_STATUS.md](docs/DOCUMENTATION_STATUS.md) | Stale-doc tracker, open design decisions |
| [docs/CLAUDE_ARCHIVED.md](docs/CLAUDE_ARCHIVED.md) | Historical session/GDD excerpt (out of date) |
| [docs/DEAD_DRIFT_GDD_ARCHIVED.md](docs/DEAD_DRIFT_GDD_ARCHIVED.md) | Original pitch GDD (historical) |

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

## Physics rule (still true)

Never multiply force by `dt` at the call site — `RigidBody2D.integrate(dt)` handles that.

---

## Tuning constant (locked May 2026)

**`MAX_VELOCITY = 280` px/s** — see `config/settings.py`. Slingshot overdrive cap = **420** px/s (1.5×).
