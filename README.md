# DEAD DRIFT

> *5 sectors. crushing debt. one rusted ship.*

A 2D Newtonian physics roguelite for PC. You are a space courier saddled with crushing clone debt. Each run is a 5-sector gauntlet through hostile space. Unionized repo men hunt your cargo. Gravity wells warp your trajectory. Your only ally is **Bax** — a sarcastic Cockney droid bolted to your dashboard. If you die, you wake up in a clone tank, deeper in debt than before.

**Tone:** tense, darkly comic, lo-fi cyberpunk. Cowboy Bebop meets Papers Please meets the worst Tuesday you've ever had.

---

## Quick Start

```bash
pip install pygame-ce numpy nltk
python main.py        # full game (recommended)
python test_stage.py  # dev only — jump to a specific screen/sector
```

**Testing tips:** Use `python main.py` for the real flow (main menu → loadout → run). Use `test_stage.py` when you need to reproduce one screen without playing from the title. Campaign progress lives in `data/saves/` (three slots); your old `data/run_history.json` is migrated into slot 1 on first launch.

**Save slots (main menu):** **RESUME RUN** when a mid-run checkpoint exists (`slot_XX_run.json`); otherwise **CONTINUE** starts a new contract on that campaign. **NEW GAME** / **LOAD GAME** manage the three campaign slots. Checkpoints autosave every **25 seconds** in flight and on sector/shop transitions.

**Death:** Clone invoice screen → **ENTER** puts you back **in the same sector** (fresh hull, same cargo contract) — not the main menu.

**Pause (in-run):** **P** (or **ESC** outside terminals). **SAVE & RETURN TO MENU** writes campaign + mid-run checkpoint.

---

## Core Mechanics

**Newtonian Physics** — No drag, no auto-decel. Real momentum. Gravity wells slingshot you if you swing close at speed. Approach fast, exit faster, shave time off your jump timer.

**Electromagnetic Tether** — Repo Barges fire magnetic harpoons. A spring force drags you toward the barge. Snap it by building enough lateral (sideways) velocity. Drift hard.

**Hotwired Signal Chain** — Power flows through 6 module slots left-to-right. Thrusters only fire if they're drawing enough power. Barges can unbolt your modules mid-flight.

**NLP Terminal Interrogations** — Between sectors, you're patched into a text terminal with an NPC gatekeeper. Type anything. The game reads your sentiment, detects intent (demand, bargain, threaten, confuse, flatter), and checks for paradoxes and exploit patterns. Each NPC has a patience meter. Run it out and the connection dies.

**Diegetic HUD** — The display degrades as hull drops. Below 60%: flicker. Below 30%: panels go dark.

---

## Controls

| Key | Action |
|---|---|
| W / Up | Thrust forward |
| S / Down | Reverse thrust |
| A / Left | Rotate CCW |
| D / Right | Rotate CW |
| Space | Fire gun |
| J | Jump to next sector (after 20s timer) |
| P | Pause (resume / save & menu) |
| ESC | Pause in-flight; abort terminal connection while interrogating |

---

## Run Structure

- 5 sectors per run
- Each sector: 20s minimum flight timer, then J to jump
- Pressing J opens an NPC terminal — talk your way through to advance
- Death → Decanting screen → clone fees stacked onto your debt → try again
- Clear all 5 sectors → debt reduced, run logged

## Meta-Progression

Debt and clone count persist across runs in `save/meta.json`. Die enough times and the numbers get ugly. The clone corp is not rooting for you.

---

## Cast

**Bax** — BAX-7, Mk.II Navigation/Morale Unit, decommissioned, now zip-tied to your dashboard. Cockney, irreverent, and genuinely fond of you despite everything. Reacts in real-time to speed, damage, tether hits, slingshotting, and more.

**KRESS** — Your employer. Furious. Insulting. Technically still paying you.

**Local 404** — Union of Repo Men. They will come for what you carry.

---

## Tech Stack

- Python + pygame-ce
- NLTK + VADER for terminal NLP
- All rendering is procedural `pygame.draw` calls — no sprites, no textures
