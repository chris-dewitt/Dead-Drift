# DEAD DRIFT

> *5 sectors. crushing debt. one rusted ship.*

A 2D Newtonian physics roguelite for PC. You are a space courier saddled with crushing clone debt. Each **chapter** is a 5-sector gauntlet through hostile space. Unionized repo men hunt your cargo. Gravity wells warp your trajectory. Your only ally is **Bax** — a sarcastic Cockney droid bolted to your dashboard. If you die, you wake up in a clone tank, deeper in debt than before.

**Tone:** tense, darkly comic, lo-fi cyberpunk. Cowboy Bebop meets Papers Please meets the worst Tuesday you've ever had.

**Active dev roadmap:** [`docs/DELIVERY_V2_PUSH.md`](docs/DELIVERY_V2_PUSH.md) (corridor/delivery overhaul, phases I.1→I.5)

---

## Quick Start

```bash
pip install pygame-ce numpy nltk
python main.py        # full game (recommended)
python play.py        # flight sandbox — no NLTK, boots fast
python test_stage.py  # dev — jump to a specific screen/sector
python audio_dev.py   # dev — tune procedural audio
pytest tests/         # 350 regression tests
```

**First launch:** `main.py` boots the menu instantly. Terminal NLP data loads on a background thread; if you open a terminal before it lands you'll see a brief `LINGUISTIC PROCESSOR INITIALISING — STAND BY` splash and the parser falls back to regex tokenisation. Sandbox flight without NLTK: `play.py`.

**Saves:** Three campaign slots under `data/saves/`. Mid-run checkpoints autosave every **25 seconds** in flight and on sector/shop transitions.

---

## Campaign Structure

| Layer | What happens |
|-------|----------------|
| **Main menu** | Resume run (checkpoint), continue campaign, new game, load slot, quit |
| **Loadout draft** | Pick ship frame, thruster tier, chapter cargo |
| **5 sectors** | Newtonian flight → clear timer → **J** opens jump terminal → advance |
| **Shop stops** | After **sectors 2 and 4** (black market upgrades) |
| **Win a chapter** | Clear sector 5 → interactive **dock** → **corridor platformer** → payout |
| **Interstitial** | Chapter bridge → next chapter loadout or campaign complete |
| **Death** | Decanting invoice → **ENTER** → menu; **retry same sector** on next run start |

Six chapters, six cargo types. Each cargo adds a unique mid-flight or corridor mechanic.

| Chapter | Cargo | Mechanic |
|---------|-------|---------|
| **Ch.1** | Acoustic Archive | Cargo damage → audio bit-crush degrades |
| **Ch.2** | Mycorrhizal Payload | Spore leak → periodic control inversion |
| **Ch.3** | The Paperwork | Filing popups fire mid-flight under fire |
| **Ch.4** | Schrödinger VIP | Observation collapses payout (alive/dead) |
| **Ch.5** | Encrypted Drive (The Edge) | Chen's drive picked up in-corridor; damage spikes trace → Compliance vessels hunt you |
| **Ch.6** | Encrypted Drive (Compliance) | Carry the drive into Nova Soma — 90-second server-room upload while alarms scream |

---

## Core Mechanics

### Newtonian flight
- No drag, no auto-decel — real momentum
- Gravity wells; slingshot for timer shave, credits, and brief overdrive (cap **420 px/s** after a clean slingshot; baseline cap **280 px/s**)
- Sector **themes** (8 types): wrecks, mines, ice, trash, flares, toll checkpoints, etc.
- Repo **Barge** state machine: patrol → chase → aim → intercept → clamp → torch (unbolt modules)
- **Tether:** spring force toward barge; snap with lateral velocity
- **Design lock:** Repo barges = **Local 404 Union only**; barge intercept comm = **Gary**. Pirates, DJs, and other factions use **different ship hulls** — not barges.
- Gun, debris, fuel canisters, satellites, hazards wired per theme

### Hotwired signal chain
- 6 module slots; power flows left-to-right
- Thrusters only fire when powered and not overheated
- LifeSupport + Thruster baseline; barges can unbolt modules in TORCH state

### NLP terminals
- Between sectors (**J** after 20s timer), mid-sector **toll**, **barge intercept**, optional **K** call to Kress
- Type natural language; VADER sentiment, intent, paradox, SQL-style exploit detection
- 13+ NPC types with distinct win paths; persistent exploit vault
- Procedural CRT **portraits** for all terminal NPCs
- Keyword/bribe schema enforced by `tests/test_npc_schema_b1.py` — see [`docs/NPC_SCHEMA.md`](docs/NPC_SCHEMA.md)

### Bax
- Cockpit strip: vector portrait, typewriter speech
- Reacts to speed, hull, tether, slingshot, shop, corridor, dock, combat, cargo
- Procedural voice blips + contextual line banks — see [`docs/BAX_VOICE.md`](docs/BAX_VOICE.md)
- At critical hull, plays harmonica licks; on delivery success, may hum (unlock **BAX'S TAPES** jukebox after clearing all 6 chapters)

### Diegetic HUD
- Degrades with hull: flicker below 60%, scramble below 30%

### Meta-progression
- Persistent **debt**, **clone count**, completed chapters (0–6)
- Stepped death fees by sector reached
- Run success clears a debt chunk; delivery payout by corridor performance

---

## Controls

| Key | Action |
|-----|--------|
| W / Up | Thrust forward |
| S / Down | Reverse thrust (60%) |
| A / Left | Rotate CCW |
| D / Right | Rotate CW |
| Space | Fire gun |
| J | Jump terminal / leave shop (browse phase) |
| K | Call Kress (once per sector, optional) |
| R | Cycle cockpit radio stations |
| P | Pause |
| ESC | Pause in-flight; **abort** terminal (−20 hull); shop leave |

**Delivery (dock):** Beat 1 — A/D/W/S align nose · Beat 2 — **J** when gauge centred, then **hold SPACE** ~1.2s for retro burn

**Corridor (on foot):** A/D or ←/→ move (momentum + skid) · SPACE/W jump — **hold for height**, tap for a hop · **hold SHIFT to sprint** (earned after sustained run) · S/↓ + W climb ladders · E talk/shortcuts · DOWN at warp pipes

**Menus:** ↑↓ navigate · ENTER confirm · ESC back / quit where noted

---

## Delivery sequence (chapter win)

1. **Approach** — align ship nose to docking bay (~5s)
2. **Land** — tap **J** to align thrusters, then hold **SPACE** ~1.2s for retro burn
3. **Touchdown** — clamp cutscene; dock quality affects credits
4. **Corridor** — 2–3 min themed platformer (**6–7 rooms** per chapter, mid-room checkpoints, branching paths, secrets, NPCs, stealth)
   - **Style stars** from chip collection %, secrets found, and hits taken — not speed
   - **Chip chains** — pickups within ~1.5s build a ×1→×5 multiplier
   - **End tally** — DKC/SMW-style score screen before payout
   - **Power-ups** (corridor-scoped): Mag-Boots, Union Hardhat, Stim Soles from ?-blocks
   - **Ch6 chase room** — one auto-scroll Compliance sweep (campaign's only pressure room)
5. **Result** — payout card, debt adjustment, chapter stamp

Corridor code lives in `delivery/corridor/` (`base.py`, per-chapter files, `rooms_v2.py` recipes). Active work: [`docs/DELIVERY_V2_PUSH.md`](docs/DELIVERY_V2_PUSH.md).

---

## Black market (shop)

- Appears after sectors **2** and **4**
- Spend run credits on hull, thrust boost, jammer, intel, cargo stabilizer, ammo, etc.
- Purchases increase meta debt (you're buying on credit)
- Intro typewriter vendor line → browse → **J** or **ESC** to leave

---

## Audio

100% **procedural** — no shipped `.wav`/`.ogg`. numpy → pygame synthesis.

- Engine tiers, drums, bass, pad, harmonica licks, guitar phrases
- BPM scales with flight pressure; barge proximity motif
- Scene mixing: menu, flight, terminal, shop, delivery, decanting, radio
- Per-chapter inflection modules (`audio/chapter_1.py` … `chapter_6.py`)

Spec → [`docs/SOUNDTRACK_PLAN.md`](docs/SOUNDTRACK_PLAN.md) · Recording stems → [`docs/RECORDING_BRIEF.md`](docs/RECORDING_BRIEF.md)

**Open polish:** soundtrack v2 accessibility layer (music subtitles, per-stem sliders) — mix audit landed; UI pending Chris play-verify.

---

## NPC cast (terminals)

| Name | Role |
|------|------|
| GARY | Local 404 field agent |
| TK-9 | Compliance droid |
| DISPATCHER | Union collections |
| KRESS | Employer / intel (also **K** key mid-flight) |
| MORWENNA | Insurance adjuster |
| Sandra | Rival courier |
| KRELLBORN | Outer Belt pirate |
| MARROW | Underground DJ ally |
| TOLL AUTHORITY | Mid-sector toll booth |
| RELAY-7 FELIX | Nervous fence |
| INSPECTOR HOLT | STA cargo inspection |
| EDMUND | Local 404 idealist rep |
| VINCE | Local 404 corrupt rep |

---

## Tech stack

- Python 3 + **pygame-ce** + **numpy** + **nltk** (VADER, tokenization)
- All graphics: procedural `pygame.draw` — no sprite pipeline
- Architecture: `core/game.py` state loop, global `EventBus`, `RunManager` sector lifecycle
- Tests: `tests/` (350 tests — saves, checkpoints, corridor I.1–I.3b, terminal NPCs, voices)

---

## Development

| Path | Purpose |
|------|---------|
| `config/settings.py` | Flight tuning constants — edit here first |
| `delivery/corridor/base.py` | Corridor feel + reward tunables (I.1/I.2 blocks at top) |
| `docs/DELIVERY_V2_PUSH.md` | **North star** — active push checklist |
| `docs/BAX_VOICE.md` | Bax line bank + tone guide |
| `docs/NPC_SCHEMA.md` | Terminal NPC keyword/bribe floors |
| `docs/SOUNDTRACK_PLAN.md` | Audio design spec |
| `docs/RECORDING_BRIEF.md` | Stem recording shot list |
| `WORKING_ON.md` | Multi-agent file claims |
| `CLAUDE.md` | Agent pointer (rules for AI coders) |

**Git identity:** Chris-dewitt / chnodewi@unc.edu

**Physics rule:** Never multiply force by `dt` at the call site — `RigidBody2D.integrate(dt)` handles that. (Corridor platformer uses hand-rolled kinematics, not RigidBody2D.)

---

## Deferred / out of scope

- Harmonica **play-along** — high effort, low immediate value
- HARDCORE mode, daily seeded challenges — infrastructure exists, content deferred
- Steam release prep, tutorial overhaul

Prior push docs (Improvement Plan, Aliveness, corridor design notes, etc.) were removed July 2026. Git history preserves them — see [`docs/archive/README.md`](docs/archive/README.md).
