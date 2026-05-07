# DEAD DRIFT Game Design

## Executive Summary

**DEAD DRIFT** is a 2D Newtonian physics roguelite for PC.

The player is a space courier saddled with crushing clone debt. Each run is a 10-sector gauntlet through hostile space. Unionized repo men hunt the player's cargo. Gravity wells warp the flight path. The player's only ally is **Bax**, a sarcastic Cockney droid bolted to the dashboard. Death means waking up in a clone tank, deeper in debt than before.

**Tone:** tense, darkly comic, lo-fi cyberpunk. Cowboy Bebop meets Papers Please meets the worst Tuesday imaginable.

## Core Pillars

1. **Momentum is the enemy and the tool.** There is no drag and no auto-deceleration.
2. **Debt is the roguelite pressure system.** Death increases clone debt; successful runs reduce it.
3. **Every system is diegetic.** The HUD, Bax, cargo, terminal, and ship modules exist inside the fiction.
4. **The ship is fragile and improvised.** Modules can be powered, damaged, unbolted, and lost.
5. **The world is bureaucratic, predatory, and funny.** Repo agents, insurance adjusters, and union dispatchers are as dangerous as asteroids.

## Core Mechanic 1: Newtonian Physics

The ship obeys real momentum. There is no automatic braking.

- `RigidBody2D` accumulates forces each frame and integrates via symplectic Euler.
- `Vec2` provides 2D vector math for addition, scaling, normalization, length, and dot products.
- Force is applied as Newtons; `integrate(dt)` converts accumulated force into velocity delta.
- Gravity wells apply inverse-square attraction every frame.
- Multiple gravity wells can be composed through `ThreeBodySystem`.

### Slingshot Mechanic

Approach a gravity well at low speed, swing around it, and exit fast. If the ship exits a well's range above the configured slingshot speed within the proximity window, the player earns a jump timer bonus and Bax reacts.

## Core Mechanic 2: Electromagnetic Tether

When a Repo Barge catches the player, it fires a magnetic harpoon.

- `Tether` applies a spring force toward the barge each frame.
- The snap condition is based on lateral velocity perpendicular to the tether line.
- After a snap, the player has a grace period before the barge can re-tether.
- Bax calls out tether hits and snaps in real time.

## Core Mechanic 3: Hotwired Signal Chain

Power flows left to right through six module slots.

- Power-producing modules add to the budget.
- Consumer modules draw from the available budget.
- `get_active("propulsion")` returns currently powered propulsion modules.
- The chain can be sabotaged by repo barge torch behavior.
- The loadout draft lets the player pick a frame, one upgrade module, and cargo.

## Core Mechanic 4: NLP Terminal Interrogations

Between sectors, or during special encounters, the player can enter a text terminal to interrogate, deceive, bargain with, or exploit an NPC.

Pipeline:

1. NLTK tokenization and VADER sentiment create an emotional read.
2. Intent classification maps player input to categories such as demand, bargain, threaten, confuse, and flatter.
3. Paradox detection catches self-contradictory input.
4. SQL/code-injection detection can exploit tech-vulnerable personalities.
5. NPC personality traits modify the response.

NPC types include repo dispatchers, fences, insurance adjusters, and union representatives.

## Core Mechanic 5: Diegetic HUD

The HUD degrades as hull integrity falls.

- At full hull: crisp amber/green readouts.
- Below 60%: flicker and scanline noise.
- Below 30%: displays may fail or scramble.
- HUD rendering is procedural and built from vector-style Pygame drawing.

## Roguelite Structure

- 10 sectors per run.
- Each sector has a minimum flight timer before jump is available.
- Sector difficulty scales across the run.
- Ambush sectors can spawn a barge immediately.
- Completing all sectors reduces debt.
- Dying triggers clone-debt penalties and a decanting screen.

## Narrative Setup

The setting is a near-future solar system controlled by creditor corporations. Clone debt is hereditary and compound. The Union of Repo Men, Local 404, provides enforcement muscle. The courier license is the player's only leverage.

## Bax

Bax is a decommissioned Mk.II Navigation/Morale Unit bolted to the dashboard. He is irreverent, anxious, Cockney, and genuinely fond of the player despite pretending otherwise.

Bax reacts to:

- Idle flight time
- High speed
- Low speed
- Hull damage
- Critical hull state
- Tether hit and snap events
- Module unbolting
- NLP exploit discovery
- Slingshots
- Barge proximity
- Fuel canister pickups

## Cargo Chapters

### Chapter 1: The Acoustic Archive

Illegal music archive. Barge proximity degrades audio fidelity and visual HUD stability.

### Chapter 2: The Mycorrhizal Payload

Psychoactive fungal spores. Planned mechanic: periodic physics inversion.

### Chapter 3: The Paperwork

Cursed bureaucratic documents. Planned mechanic: pop-up filing interruptions.

### Chapter 4: The Schrödinger VIP

A passenger who may or may not be alive. Observation collapses state and affects payout.

## Visual Bible

- Background: near-black void, not pure black.
- Palette: amber, terminal green, warning red, dead grey, neon blue.
- Style: brutalist vector lines against pitch-black space.
- Gravity wells: concentric hue-cycling rings and radial spokes.
- Ship: neon cyan glow under white vector outline.
- Trail: chromatic smear that intensifies with speed.
- Exhaust: layered glow with hue shifting as hull drops.
- Debris: irregular dim-purple tumbling polygons.
- Fuel canisters: pulsing diamonds with hue-cycling glow.
- Proximity alarm: red edge vignette when barge is near.

## Audio Direction

Audio is currently stubbed. Planned sound design includes:

- Engine hum pitched to thrust level.
- Metallic tether clang.
- Snap crack on tether break.
- Bax voice or text-to-speech.
- Ambient radio static.
- Death sting.

## Technical Architecture

```text
Dead-Drift/
├── main.py                  # Full game entry point
├── play.py                  # Flight sandbox demo
├── config/settings.py       # Constants and tuning values
├── core/                    # Game loop, state routing, event bus
├── physics/                 # Vec2, RigidBody2D, gravity, tether
├── ship/                    # PlayerShip, HUD, signal chain, modules
├── renderer/                # Scene, cockpit, HUD, terminal renderers
├── bax/                     # Bax dialogue and vocabulary systems
├── roguelite/               # Run manager, draft, procedural sectors, meta-progression
├── antagonists/             # Repo barges, debris, fuel canisters
├── cargo/                   # Cargo mechanics
└── terminal/                # NLP terminal and NPC logic
```

## Important Physics Rules

- Do not multiply force by `dt` at the call site; integration handles `dt`.
- Use `apply_thrust(force)`, not `apply_thrust(force * dt)`.
- Gravity applies every frame before integration.
- Tether snap checks lateral velocity relative to the tether line.
