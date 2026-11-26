# DEAD DRIFT: MOBILE (working title)

> *Same debt. Same rusted ship. Now it fits in your pocket.*

A **new, Android-only game** based on Dead Drift and built for phones from the
ground up. It is **not** a port of the PC game and **not** a replacement for
the existing `mobile/` slice. It shares tone, characters and core ideas with
the original, but no code.

**Status:** pre-production. Design docs only, no code yet.

---

## The separation rule

- Nothing in this directory imports, links to or edits the original game
  (`../` anything). Reading the original for reference is fine. Depending on
  it at runtime or build time is not.
- This directory is laid out so it can move to its own repository with
  `git subtree split --prefix=dead-drift-mobile` whenever we're ready. Treat it
  as a separate repo from day one: its own README, CLAUDE.md, docs and
  (later) CI.
- The original game's docs (`../docs/*`) stay the source for **lore, tone and
  characters**. Mobile docs here are the source for **everything mechanical**.

## Doc index

| Doc | Covers |
|-----|--------|
| [docs/DECISIONS.md](docs/DECISIONS.md) | Chris's answers, design pillars, open questions |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Engine (Godot 4), project layout, screens, saves, performance, security baseline |
| [docs/TERMINAL.md](docs/TERMINAL.md) | Mobile terminals: input, rule engine, shell/REPL, LLM voice layer |
| [docs/CONTROLS_AND_HUD.md](docs/CONTROLS_AND_HUD.md) | Touch layouts for flight, dock and corridor; HUD for phones; accessibility |
| [docs/CONTENT.md](docs/CONTENT.md) | Run loop, chapters, cargo mechanic redesigns, shops, Kress, intercepts |
| [docs/AUDIO.md](docs/AUDIO.md) | Mobile audio plan: pre-rendered procedural palette and stem slots |
| [docs/ROADMAP.md](docs/ROADMAP.md) | **North star.** Phased push (M.0 → M.10) with checkboxes |
