# DEAD DRIFT: MOBILE — Agent pointer

You are inside `dead-drift-mobile/`, a **separate, Android-only game**. Treat
this directory as its own repo.

1. **Never import from, edit or depend on the parent Dead Drift game.** Read it
   for lore and tone only. Don't touch `../mobile/` (the old slice) either.
2. **North star:** [docs/ROADMAP.md](docs/ROADMAP.md). Update checkboxes there.
3. **Locked decisions:** [docs/DECISIONS.md](docs/DECISIONS.md). Don't
   re-litigate them; raise a question instead.
4. **Terminal rule:** *the rules decide, the model talks.* No LLM output may
   change game state, credits, hull or outcomes. See [docs/TERMINAL.md](docs/TERMINAL.md).
5. **Security:** no secrets in the repo or the APK, no `Expression`/eval on
   player text, JSON-only saves. See ARCHITECTURE.md § Security baseline.

## Git identity — always use this

```
git config user.name "Chris-dewitt"
git config user.email "chnodewi@unc.edu"
```

Never commit as Claude. Never add co-author lines.
