# Claude Notes for DEAD DRIFT

This file is a lightweight contributor note for AI-assisted development sessions.

## Project Summary

**DEAD DRIFT** is a Python/Pygame 2D Newtonian physics roguelite about a space courier trying to survive clone debt, repo barges, gravity wells, and hostile bureaucracy.

Primary public docs:

- `README.md` — project overview and setup instructions.
- `docs/GAME_DESIGN.md` — game design and systems overview.
- `docs/ROADMAP.md` — current priorities and planned improvements.

## Development Principles

- Keep the sandbox path fast and easy to run with `python play.py`.
- Keep the full prototype path runnable with `python main.py`.
- Preserve the lo-fi vector aesthetic; most visuals should remain procedural Pygame drawing rather than sprite-heavy assets.
- Do not multiply force by `dt` at the call site; physics integration handles timestep scaling.
- Prefer small, readable gameplay systems over large rewrites.
- Keep Bax event-driven and contextual.
- Avoid committing generated files, local save data, or audio assets.

## Quick Commands

```bash
pip install -r requirements.txt
python play.py
python main.py
```

## Current High-Value Tasks

- Add visible tether rendering.
- Add Bax cockpit strip to sandbox mode.
- Add a main menu/title screen.
- Add screenshots or a GIF to the README.
- Wire terminal encounters into flight sectors.
- Implement planned cargo chapter mechanics.
