# DEAD DRIFT — Claude Working Instructions

## The Only Repo That Matters
All Dead Drift changes go here, full stop:
**https://github.com/chris-dewitt/Dead-Drift**

Push target: `main` branch of `chris-dewitt/Dead-Drift`

This project lives in a subfolder of a separate repo during dev sessions.
When you commit and push, use the `dead-drift-origin` remote if available,
or give the user sync instructions to pull from the dev branch into Dead-Drift.

---

## Git Identity — Always Use This
```
git config user.name "Chris-dewitt"
git config user.email "chnodewi@unc.edu"
```
Run this at the start of every session. Never commit as Claude.
Never add co-author lines. Chris is the only author on this repo.

---

## Project
**DEAD DRIFT** — 2D Newtonian physics roguelite, Python + pygame-ce.
Space courier. Unionized repo men want your cargo. Cockney droid on your dash.

Run the game:
```
cd dead-drift
pip install pygame-ce numpy
python main.py        # full game
python play.py        # quick flight sandbox (no NLTK needed)
```

---

## Architecture At a Glance

```
dead-drift/
├── main.py                  # entry point (full game)
├── play.py                  # flight sandbox demo
├── config/settings.py       # all constants — edit here first
├── core/
│   ├── game.py              # main loop, state routing
│   ├── state_manager.py     # GameState enum + history stack
│   └── event_bus.py         # global pub/sub (EVT_* constants)
├── physics/
│   ├── body.py              # Vec2 + RigidBody2D (symplectic Euler)
│   ├── gravity.py           # GravityWell + ThreeBodySystem
│   └── tether.py            # EM harpoon spring + snap mechanic
├── ship/
│   ├── ship.py              # PlayerShip — input, chain, wrapping
│   ├── hud.py               # diegetic HUD (degrades with hull)
│   ├── loadout.py           # SignalChain — 6-slot power routing
│   └── modules/             # Thruster, LifeSupport, BaseModule
├── renderer/
│   ├── vector_renderer.py   # flight scene (stars, wells, ship, exhaust)
│   ├── cockpit_renderer.py  # bottom strip — Bax portrait + speech
│   └── hud_renderer.py      # wraps ship/hud.py for game.py
├── bax/
│   ├── bax.py               # Cockney droid — events + ambient chatter
│   ├── mixologist.py        # fuel brew recipes → FuelMix
│   └── vocabulary_vault.py  # persistent NLP knowledge base
├── roguelite/
│   ├── run_manager.py       # sector progression, barge spawning
│   ├── loadout_draft.py     # run-start draft UI (frame/module/cargo)
│   ├── procedural.py        # generate_sector()
│   └── meta_progression.py  # JSON-persisted debt + clone count
├── antagonists/
│   └── repo_barge.py        # PATROL→CHASE→CLAMP→TORCH state machine
├── cargo/                   # 4 cargo types (one per chapter)
└── terminal/                # NLP terminal + NPC logic
```

---

## Key Design Rules

**Physics** — true Newtonian, no drag. Forces accumulate each frame,
`integrate(dt)` resets the accumulator. Never multiply force by dt at
the call site — integrate already does that.

**Signal Chain** — power routes left-to-right through 6 slots. Budget
comes from modules with `power_output > 0`, or 10W baseline.
`get_active("propulsion")` is how ship.py finds thrusters.

**Event Bus** — systems talk through `bus.emit()` / `bus.subscribe()`.
Don't import between systems directly if an event will do.

**Renderer** — all geometry is procedural pygame.draw calls. No sprites.
Keep it sparse, vector-art, neon. VOID background (4,4,8), amber + green palette.

**Cockpit strip** — bottom 80px (`COCKPIT_H`). Bax portrait on the right.
Speech text typewriters in from the left. `EVT_BAX_SPEAK` drives it.

---

## Controls (Flight)
| Key | Action |
|-----|--------|
| W / Up | Thrust forward |
| S / Down | Reverse thrust (40%) |
| A / Left | Rotate CCW |
| D / Right | Rotate CW |
| J | Jump to next sector (after 20s timer) |
| N | Spawn repo barge (play.py only) |
| R | Reset ship (play.py only) |
| ESC / Q | Quit |

---

## Current State (as of last session)
- ✅ Flight physics working — thrust, gravity wells, tether snap
- ✅ Loadout draft → FLIGHT state transition
- ✅ Sector timer HUD + J-to-jump
- ✅ Vector renderer: starfield, gravity well rings, ship trail, exhaust, tether line
- ✅ Prograde/retrograde velocity indicators
- ✅ Bax cockpit strip: portrait, speech, ambient + contextual one-liners
- ✅ RepoBarge PATROL→CHASE→CLAMP→TORCH working
- 🔲 Terminal phase not yet triggered from flight
- 🔲 Main menu screen
- 🔲 Bax lines not displayed in play.py (no cockpit there)
- 🔲 Audio (stubbed out)
