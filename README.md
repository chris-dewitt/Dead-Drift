# DEAD DRIFT

**DEAD DRIFT** is a 2D Newtonian physics roguelite built with Python and Pygame.

You are a broke space courier trapped in a clone-debt contract. Each run sends you through hostile sectors full of gravity wells, debris, fuel canisters, and unionized repo barges trying to harpoon your ship and repossess your cargo. Your only real ally is Bax, a sarcastic dashboard droid who talks you through the disaster.

Tone: lo-fi cyberpunk, dark comedy, physics chaos, and desperate space trucking.

## Current Status

This is an in-progress playable prototype. The repo currently includes:

- A full game entry point with roguelite run structure.
- A lightweight flight sandbox for quickly testing movement, gravity, debris, fuel pickups, and repo barge behavior.
- Newtonian movement with no drag or automatic braking.
- Gravity wells and slingshot-style movement.
- Electromagnetic tether mechanics for repo barges.
- A six-slot signal-chain module system.
- Diegetic HUD degradation as hull integrity falls.
- Bax event-driven cockpit dialogue.
- Early NLP terminal interrogation systems using NLTK and VADER.
- JSON-backed meta-progression for clone debt and run state.

The fastest way to try the project is the sandbox:

```bash
python play.py
```

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/chris-dewitt/Dead-Drift.git
cd Dead-Drift
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the flight sandbox

```bash
python play.py
```

The sandbox boots quickly and does not require the full NLP/game loop.

### 5. Run the full prototype

```bash
python main.py
```

The full prototype downloads required NLTK data on first run.

## Controls

| Key | Action |
|---|---|
| W / Up | Thrust forward |
| S / Down | Reverse thrust |
| A / Left | Rotate counter-clockwise |
| D / Right | Rotate clockwise |
| J | Jump to next sector when ready |
| N | Spawn repo barge in sandbox mode |
| R | Reset ship in sandbox mode |
| ESC / Q | Quit |

## Gameplay Systems

### Newtonian Flight

The ship has real momentum. There is no drag and no automatic braking. Rotation changes where thrust points, but existing velocity remains until another force changes it.

### Gravity Wells

Gravity wells bend the ship's path and create slingshot opportunities. Skilled flight means using gravity instead of fighting it.

### Repo Barges and Tethers

Repo barges chase the player and fire electromagnetic tethers. The player can snap a tether by building enough lateral velocity across the tether line.

### Signal Chain

The ship has a six-slot signal chain. Modules consume or provide power. Damage and repo actions can unbolt modules, changing which systems remain active.

### Bax

Bax is the cockpit droid: sarcastic, anxious, and weirdly loyal. He reacts to hull damage, speed, tether events, fuel pickups, barge proximity, and other run events.

### NLP Terminal

The prototype includes an early text-based interrogation system powered by NLTK tokenization, VADER sentiment, simple intent logic, contradiction detection, and exploit detection.

## Project Structure

```text
Dead-Drift/
├── main.py                  # Full game entry point
├── play.py                  # Lightweight flight sandbox
├── requirements.txt         # Python dependencies
├── config/                  # Settings and constants
├── core/                    # Game loop, state manager, event bus
├── physics/                 # Vector math, rigid bodies, gravity, tether mechanics
├── ship/                    # Player ship, HUD, signal chain, modules
├── renderer/                # Vector scene, cockpit, HUD, terminal rendering
├── bax/                     # Bax dialogue and vocabulary systems
├── roguelite/               # Run manager, procedural sectors, loadout draft, meta-progression
├── antagonists/             # Repo barges, debris, fuel canisters
├── cargo/                   # Chapter cargo mechanics
├── terminal/                # NLP terminal and NPC logic
└── docs/                    # Design notes and roadmap
```

## Documentation

- [Game Design](docs/GAME_DESIGN.md)
- [Roadmap](docs/ROADMAP.md)

## Development Notes

This project is intentionally built with procedural/vector rendering rather than sprites. Most visual elements are drawn directly with Pygame primitives to keep the aesthetic stark, readable, and easy to iterate on.

## Known Limitations

- The game is still a prototype.
- Audio is stubbed and not yet fully implemented.
- Some cargo chapter mechanics are planned but incomplete.
- The full game path is more experimental than the sandbox path.
- There is not yet a packaged release build.

## License

No formal license has been selected yet.

## Author

Built by Chris DeWitt as a creative Python/game-systems project focused on physics, procedural rendering, roguelite structure, and strange little machines with attitude.
