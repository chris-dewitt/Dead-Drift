# DEAD DRIFT Roadmap

## Current Prototype Strengths

- Newtonian flight with no drag.
- Gravity wells and slingshot-style movement.
- Flight sandbox via `play.py`.
- Full prototype entry point via `main.py`.
- Repo barge chase, clamp, tether, and torch behavior.
- Debris and fuel canister systems.
- Bax cockpit dialogue hooks.
- Diegetic HUD degradation.
- Early NLP terminal and NPC logic.
- JSON-backed meta-progression for debt and clone count.

## Near-Term Priorities

### 1. Make the sandbox irresistible

The sandbox is the easiest way for someone to experience the game quickly. It should become the project's demo centerpiece.

Tasks:

- Add visible tether rendering.
- Add Bax cockpit strip to `play.py`.
- Add a simple start/help overlay.
- Add one screenshot or GIF to the README.
- Add a small "try this" flight challenge, such as snap a tether or slingshot around a gravity well.

### 2. Stabilize the full game loop

The full game should reliably move from loadout draft to flight to death/run-end screens.

Tasks:

- Confirm loadout draft path works from a fresh clone.
- Confirm the full game can enter flight without rendering errors.
- Add a basic main menu/title screen.
- Add clear handling for restart and quit states.
- Add smoke-test instructions.

### 3. Improve public repo presentation

Tasks:

- Add screenshots or GIFs.
- Add a short gameplay clip later if possible.
- Add a concise architecture diagram.
- Add a known-issues section.
- Add license once the intended sharing model is decided.

## Gameplay Roadmap

### Cargo Mechanics

- Implement AcousticArchive HUD/audio static near barges.
- Implement MycoShroom periodic control inversion.
- Implement TriplicateForm filing popups.
- Expand SchrodingerVIP state collapse and payout effects.

### Repo Barges

- Render tether line in flight scene.
- Add cooldown UI feedback after tether snap.
- Add barge personality/faction behavior.
- Wire Local 404 reputation into spawn and miss behavior.

### Bax

- Add sandbox cockpit strip.
- Add more contextual lines.
- Add bark cooldown tuning to reduce repetition.
- Eventually support generated or recorded voice lines.

### Terminal/NLP

- Trigger terminal encounters from flight sectors.
- Add encounter rewards and penalties.
- Persist discovered exploit terms.
- Give NPCs clearer personality-driven response patterns.

### Meta-Progression

- Expand debt ledger.
- Add run summaries.
- Add chapter completion rewards.
- Add unlocks tied to debt milestones or cargo completion.

## Technical Roadmap

### Code Quality

- Add smoke tests for importability and core math.
- Add type hints where missing.
- Add a simple CI workflow later.
- Split large renderer/game files only when they become hard to maintain.

### Packaging

- Add optional `Makefile` or task commands.
- Add `requirements-dev.txt` for test/lint tools.
- Consider PyInstaller packaging once the prototype stabilizes.

### Performance

- Profile vector rendering under heavy debris/barge conditions.
- Cache static star fields or reusable surfaces if needed.
- Keep the sandbox fast and low-friction.

## Backlog

- Audio system implementation.
- Title screen.
- Save slot selection.
- Tutorial prompts.
- Controller support.
- Difficulty settings.
- More sector archetypes.
- More cargo chapters.
- More NPC archetypes.
