# DEAD DRIFT — Claude Working Instructions & Game Design Document

---

## REPO & SESSION RULES

**Target repo:** https://github.com/chris-dewitt/Dead-Drift  
Push target: `main` branch of `chris-dewitt/Dead-Drift`

The remote `dead-drift-origin` points to Dead-Drift but **session auth only
covers `chris-dewitt/chris-dewitt`** via the local proxy. Direct push to
Dead-Drift will fail with auth error. Always commit to `origin` (the proxy),
then tell the user to run the sync command below from their machine:

```powershell
cd C:\Users\DELL\Documents\GitHub\Dead-Drift
git fetch https://github.com/chris-dewitt/chris-dewitt claude/dead-drift-gdd-4SbVa
git merge FETCH_HEAD --allow-unrelated-histories -X theirs -m "Sync from dev branch"
git push origin main
```

### Git Identity — Always Use This
```
git config user.name "Chris-dewitt"
git config user.email "chnodewi@unc.edu"
```
Run this at the start of every session. **Never commit as Claude. Never add
co-author lines.** Chris is the only author on this repo.

---

## QUICK START
```bash
cd dead-drift
pip install pygame-ce numpy nltk
python main.py        # full game (needs NLTK data)
python play.py        # flight sandbox — no NLTK, boots in seconds
```

---

## PART 1 — GAME DESIGN DOCUMENT

### Executive Summary
**DEAD DRIFT** is a 2D Newtonian physics roguelite for PC.

You are a space courier saddled with crushing clone debt. Each run is a
5-sector gauntlet through hostile space. Unionized repo men (Repo Barges) hunt
your cargo. Gravity wells warp your trajectory. Your only ally is **Bax**, a
sarcastic Cockney droid bolted to your dashboard. If you die, you wake up in a
clone tank — deeper in debt than before.

**Tone:** tense, darkly comic, lo-fi cyberpunk. Cowboy Bebop meets Papers Please
meets the worst Tuesday you've ever had.

---

### Core Mechanic 1 — Newtonian Physics (No Drag)

The ship obeys real momentum. There is no auto-deceleration.

- `RigidBody2D` accumulates forces each frame, integrates via symplectic Euler.
- `Vec2` provides 2D vector math (add, scale, normalize, length, dot).
- Force is applied as Newtons; `integrate(dt)` converts to velocity delta.
- **Rule:** never multiply force by `dt` at the call site — integrate already does that.
- Gravity wells apply `F = G * mass / dist²` attraction every frame.
- `ThreeBodySystem` holds multiple `GravityWell` objects and calls them all.

**Slingshot mechanic:** approach a well at low speed, swing around, exit fast.
If the ship exits a well's range faster than `SLINGSHOT_SPEED` within 2.5s of
proximity, it earns a `SLINGSHOT_BONUS` reduction on the sector jump timer and
Bax reacts.

---

### Core Mechanic 2 — Electromagnetic Tether (Repo Barge)

When a Repo Barge catches you, it fires a magnetic harpoon.

- `Tether` applies a spring force toward the barge each frame.
- **Snap condition:** lateral velocity ≥ `SNAP_VELOCITY` — perpendicular to the
  tether line. Drift hard sideways to snap it.
- After snap, there's a grace period before the barge can re-tether.
- Bax calls out tether hits and snaps in real-time.

---

### Core Mechanic 3 — Hotwired Signal Chain

Power flows left-to-right through 6 module slots.

- Modules with `power_output > 0` add to the budget; consumers draw from it.
- `get_active("propulsion")` returns thruster modules that are currently powered.
- The chain can be sabotaged: Repo Barge TORCH state unbolts modules.
- Loadout draft at run start lets player pick frame, one upgrade module, and cargo.

**Module pool** (in `roguelite/loadout_draft.py`):
- `Thruster` (x3 variants) — always in the pool
- `LifeSupport` — available as upgrade, but must NOT replace slot-1 Thruster

---

### Core Mechanic 4 — NLP Terminal Interrogations

Between sectors (or mid-flight if triggered), the player enters a text terminal
to interrogate or deceive an NPC.

**Pipeline:**
1. NLTK tokenize + VADER sentiment → emotional read
2. Intent classifier → `["demand", "bargain", "threaten", "confuse", "flatter"]`
3. Paradox detector → if input is self-contradictory, NPC freezes
4. SQL/code injection detector → "exploits" NPCs with tech-vulnerable personalities
5. NPC personality modifies response based on Union Loyalty, Greed, etc.

**VocabularyVault** stores discovered exploit keys per NPC type (JSON-persisted).
**Bax** calls out newly discovered exploits: `"FILED THAT. {key} works on their lot."`

NPC types: `repo_dispatcher`, `fence`, `insurance_adjuster`, `union_rep`

---

### Core Mechanic 5 — Diegetic HUD

The HUD degrades as hull integrity drops.

- At full hull: crisp amber/green readouts.
- Below 60%: flicker, scanline noise.
- Below 30%: some displays go dark.
- The HUD is drawn procedurally in `ship/hud.py`; `HUDRenderer` wraps it for
  the main game loop.

---

## PART 2 — ROGUELITE STRUCTURE

### Run Structure
- 5 sectors per run (`SECTORS_PER_RUN = 5`)
- Each sector: 20s minimum flight timer, then `J` to jump
- Sector difficulty scales: `1.0 + (sector_index / SECTORS_PER_RUN)`
- Ambush sectors spawn a barge immediately on entry
- Shop stops at sector indices `{1, 3}` (after sectors 2 and 4)
- Completing all 5 sectors = run success → delivery sequence → `meta.clear_debt_chunk()`

### Meta-Progression (JSON-persisted in `save/meta.json`)
- `debt` — running total owed to clone corp
- `clone_count` — how many times you've died
- `chapters_completed` — set of completed chapter numbers
- `npc_reputation` — dict of NPC-type → rep score
- `death_penalty`: adds `CLONE_FLUID_FEE + WRECKAGE_TOW_FEE + BASE_CLONE_DEBT`
- `clear_debt_chunk()`: reduces debt by 10% on run success

### Decanting Screen
Shown on death. Lists fees, current debt, clone number. Press ENTER to start
next run.

### Loadout Draft
Three picks at run start:
1. **Frame** — affects hull max and mass modifier
2. **Module** — upgrade installed at slot 1 of the signal chain
3. **Cargo** — chapter-specific payload (see narrative chapters below)

---

## PART 3 — NARRATIVE & CARGO CHAPTERS

### The World
The setting is a near-future solar system run by creditor corporations.
Clone debt is hereditary and compound. The Union of Repo Men, Local 404, is
the muscle. Your courier licence is your only leverage.

### Bax
**Full name:** BAX-7 (self-styled "Bax")  
**Model:** Mk.II Navigation/Morale Unit, decommissioned, now bolted to your dash  
**Voice:** Cockney, irreverent, genuinely fond of you despite everything  
**Function:** navigator, mechanic, running commentary, event-driven one-liners

Bax speaks when:
- Idle (every 18–28s, ambient quips)
- Speed > 380 m/s (excitement)
- Speed < 25 m/s (impatience)
- Hull damage > 15 (alarm)
- Hull critical (panic)
- Tether hit / snap
- Module unbolted
- NLP exploit found
- Slingshot achieved
- Barge nearby
- Fuel canister grabbed

### Chapter 1 — The Acoustic Archive
**Cargo:** `AcousticArchive` — a library of illegal music  
**Mechanic:** proximity to barges degrades audio fidelity (visual static on HUD)  
**Bax:** "Oi, that's got some bangers on it. Don't let 'em nick it."

### Chapter 2 — The Mycorrhizal Payload
**Cargo:** `MycoShroom` — psychoactive fungal spores  
**Mechanic:** periodic physics inversion (controls flip for 4s)  
**Bax:** "I've inhaled somethin'. Either that or space is sideways now."

### Chapter 3 — The Paperwork
**Cargo:** `TriplicateForm` — cursed bureaucratic documents  
**Mechanic:** random HUD popups demanding the player press keys to "file forms"  
**Bax:** "Form 27-B, subsection 9. By ORDER of the bloody Union, mate."

### Chapter 4 — The Schrödinger VIP
**Cargo:** `SchrodingerVIP` — passenger who may or may not be alive  
**Mechanic:** observation collapses state (random alive/dead) — affects payout  
**VIP.update():** called every frame; scrambles status if `ship.speed > 200`  
**Bax:** "Don't open the box. I mean it. Actually, maybe open the box."

---

## PART 4 — ART & AUDIO BIBLE

### Visual Style
- **Background:** `VOID = (4, 4, 8)` — near-black, not pure black
- **Palette:** amber `(255, 176, 0)`, terminal green `(0, 255, 128)`, red warning
  `(255, 50, 50)`, dead grey `(80, 80, 100)`
- **Aesthetic:** brutalist vector lines, stark high-contrast neon against pitch-black
  space. No sprites. No textures. All `pygame.draw` calls.
- **Gravity wells:** 5 concentric hue-cycling rings (~14s full cycle), slowly
  rotating 8-fold radial spokes, layered core glow
- **Ship:** neon cyan glow halo (width=4) under white outline (width=2)
- **Trail:** chromatic smear — blue → purple → red per ghost dot as speed increases
- **Exhaust plume:** 3 layers (outer glow / mid / white core), hue shifts blue →
  magenta as hull drops
- **Stars:** three tiers — dim static field, mid-bright, neon accents (cyan/magenta/amber)
- **Debris rocks:** dim purple fill, irregular polygon, 5–7 points, tumbling
- **Fuel canisters:** pulsing diamond with hue-cycling glow
- **Proximity alarm:** red edge vignette rectangles pulsing via sin wave when barge
  within 340px
- **Slingshot flash:** SRCALPHA yellow/white overlay that fades over 0.4s

### Cockpit Strip (bottom 80px)
- Amber top border line
- **Right side:** Bax vector portrait
  - Asymmetric polygon head (wider at top)
  - CRT scan lines every 3px
  - LED eyes — glow cyan when speaking, dim otherwise
  - Wavy mouth animation while speaking
  - Crooked antenna, shoulder mounts
- **Left/centre:** speech text, typewriter effect at 30 chars/sec, blinking cursor
  while typing, 4s hold then clears
- Driven entirely by `EVT_BAX_SPEAK` events

### Audio (STUBBED — not yet implemented)
- **Engine hum:** pitched to thrust level
- **Tether clang:** metallic impact on harpoon hit
- **Snap crack:** snap mechanic
- **Bax voice:** text-to-speech or short clips
- **Ambient:** distant radio static between sectors
- **Death sting:** descending synth chord

---

## PART 5 — TECHNICAL REFERENCE

### Architecture
```
dead-drift/
├── main.py                  # entry point (full game)
├── play.py                  # flight sandbox demo (no NLTK)
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
│   ├── hud_renderer.py      # wraps ship/hud.py for game.py
│   └── terminal_renderer.py # NLP terminal display
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
│   ├── repo_barge.py        # PATROL→CHASE→CLAMP→TORCH state machine
│   ├── debris.py            # tumbling irregular polygon rocks
│   └── fuel_canister.py     # pulsing diamond fuel pickups
├── cargo/                   # 4 cargo types (one per chapter)
│   ├── acoustic_archive.py
│   ├── myco_shroom.py
│   ├── triplicate_form.py
│   └── schrödinger_vip.py
└── terminal/                # NLP terminal + NPC logic
    ├── terminal.py
    └── npc_logic.py
```

### Key Event Bus Constants (core/event_bus.py)
| Constant | Trigger |
|---|---|
| `EVT_SHIP_DESTROYED` | hull hits 0 |
| `EVT_HULL_DAMAGE` | any damage taken |
| `EVT_HULL_CRITICAL` | hull < 30 |
| `EVT_TETHER_HIT` | barge harpoon connects |
| `EVT_TETHER_SNAP` | lateral velocity snaps tether |
| `EVT_MODULE_UNBOLTED` | TORCH state removes module |
| `EVT_BAX_SPEAK` | Bax has a line |
| `EVT_NLP_EXPLOIT` | terminal NLP exploit found |
| `EVT_SLINGSHOT` | slingshot bonus triggered |
| `EVT_BARGE_NEARBY` | barge within 320px |
| `EVT_CANISTER_GRAB` | fuel canister picked up |
| `EVT_SECTOR_CLEAR` | J-jump confirmed |
| `EVT_RUN_END` | 5 sectors cleared or aborted |

### Controls
| Key | Action |
|---|---|
| W / Up | Thrust forward |
| S / Down | Reverse thrust (40%) |
| A / Left | Rotate CCW |
| D / Right | Rotate CW |
| J | Jump to next sector (after 20s timer) |
| N | Spawn repo barge (play.py only) |
| R | Reset ship (play.py only) |
| ESC / Q | Quit |

### Important Physics Rules
- **Never** multiply force by `dt` at the call site — `integrate(dt)` does it
- `apply_thrust(force)` not `apply_thrust(force * dt)`
- Gravity: `F = G * mass / dist²`, applied every frame before integrate
- Tether snap: check lateral velocity (dot product with tether-perpendicular)

---

## PART 6 — CURRENT STATE & TODO

### Working
- ✅ Flight physics — thrust, gravity wells, wrapping, tether snap
- ✅ Loadout draft → FLIGHT state transition
- ✅ Sector timer HUD + J-to-jump (5 sectors)
- ✅ Psychedelic vector renderer: hue-cycling wells, chromatic trail, exhaust plume
- ✅ Starfield with neon accent tier
- ✅ Debris field (7 tumbling rocks, collision damage)
- ✅ Fuel canisters (3, pulsing diamond, thruster boost on grab)
- ✅ Slingshot detection + Bax reaction + EVT_SLINGSHOT
- ✅ Proximity alarm (barge within 320px, red vignette pulse)
- ✅ Bax cockpit strip: vector portrait, typewriter speech, ambient + contextual lines
- ✅ RepoBarge PATROL→CHASE→CLAMP→TORCH state machine
- ✅ NLP terminal (NLTK + VADER + intent + paradox + exploit detection)
- ✅ Meta-progression (debt, clone count, JSON save)
- ✅ Decanting screen (death fees, clone number)
- ✅ SchrodingerVIP scramble mechanic wired

### Not Yet Done
- 🔲 Terminal trigger from FLIGHT state (NPC encounter mid-run)
- 🔲 Main menu / title screen
- 🔲 AcousticArchive HUD static effect
- 🔲 MycoShroom physics inversion
- 🔲 TriplicateForm HUD popup interrupts
- 🔲 Bax cockpit strip in play.py sandbox
- 🔲 Audio (entire system stubbed)
- 🔲 Barge tether visible in renderer
