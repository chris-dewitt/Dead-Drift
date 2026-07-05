# DEAD DRIFT

> *5 sectors. crushing debt. one rusted ship.*

A 2D Newtonian physics roguelite for PC. You are a space courier saddled with crushing clone debt. Each **chapter** is a 5-sector gauntlet through hostile space. Unionized repo men hunt your cargo. Gravity wells warp your trajectory. Your only ally is **Bax** — a sarcastic Cockney droid bolted to your dashboard. If you die, you wake up in a clone tank, deeper in debt than before.

**Tone:** tense, darkly comic, lo-fi cyberpunk. Cowboy Bebop meets Papers Please meets the worst Tuesday you've ever had.

**Docs:** Active roadmap → [`docs/ALIVENESS_PUSH.md`](docs/ALIVENESS_PUSH.md) · Historical epics → [`docs/IMPROVEMENT_PLAN.md`](docs/IMPROVEMENT_PLAN.md)

---

## Quick Start

```bash
pip install pygame-ce numpy nltk
python main.py        # full game (recommended)
python play.py        # flight sandbox — no NLTK, boots fast
python test_stage.py  # dev — jump to a specific screen/sector
python audio_dev.py   # dev — tune procedural audio
```

**First launch:** `main.py` boots the menu instantly. The terminal NLP
data is fetched on a background thread; if you open a terminal before
it lands you'll see a brief `LINGUISTIC PROCESSOR INITIALISING — STAND
BY` splash and the parser falls back to regex tokenisation in the
meantime. Sandbox flight without NLTK at all: `play.py`.

**Saves:** Three campaign slots under `data/saves/`. Mid-run checkpoints autosave every **25 seconds** in flight and on sector/shop transitions. Legacy `data/run_history.json` migrates into slot 1 on first launch.

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
| **Ch.5** | Encrypted Drive (The Edge) | Chen's drive picked up in-corridor; damage spikes its trace level → Compliance vessels hunt you |
| **Ch.6** | Encrypted Drive (Compliance) | Carry the drive into Nova Soma — 90-second server-room upload while alarms scream |

---

## Core Mechanics

### Newtonian flight
- No drag, no auto-decel — real momentum
- Gravity wells; slingshot for timer shave, credits, and brief overdrive (cap **420 px/s** after a clean slingshot; baseline cap **280 px/s**)
- Sector **themes** (8 types): wrecks, mines, ice, trash, flares, toll checkpoints, etc.
- Repo **Barge** state machine: patrol → chase → aim → intercept → clamp → torch (unbolt modules)
- **Tether:** spring force toward barge; snap with lateral velocity
- **Design lock (May 2026):** Repo barges = **Local 404 Union only**; barge intercept comm = **Gary**. Pirates, DJs, and other factions use **different ship hulls** — not barges. See `docs/IMPROVEMENT_PLAN.md` Phase 0.7–0.9.
- Gun, debris, fuel canisters, satellites, hazards wired per theme

### Hotwired signal chain
- 6 module slots; power flows left-to-right
- Thrusters only fire when powered and not overheated
- LifeSupport + Thruster baseline; barges can unbolt modules in TORCH state

### NLP terminals
- Between sectors (**J** after 20s timer), mid-sector **toll**, **barge intercept**, optional **K** call to Kress
- Type natural language; VADER sentiment, intent, paradox, SQL-style exploit detection
- 11 NPC types with distinct win paths; persistent exploit vault
- Procedural CRT **portraits** for all terminal NPCs, including Inspector Holt and Relay-7 Felix

### Bax
- Cockpit strip: vector portrait, typewriter speech
- Reacts to speed, hull, tether, slingshot, shop, corridor, dock, combat, cargo
- Procedural voice blips + contextual line banks

### Diegetic HUD
- Degrades with hull: flicker below 60%, scramble below 30%

### Meta-progression
- Persistent **debt**, **clone count**, completed chapters
- Stepped death fees by sector reached
- Run success clears a debt chunk; delivery payout by performance

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

**Delivery (dock):** Beat 1 — A/D/W/S align nose · Beat 2 — **J** when gauge centred, then **hold SPACE** ~1.2s for retro burn · Corridor — platformer keys

**Menus:** ↑↓ navigate · ENTER confirm · ESC back / quit where noted

---

## Black market (shop)

- Appears after sectors **2** and **4**
- Spend run credits (debt recovered this run) on hull, thrust boost, jammer, intel, cargo stabilizer, ammo, etc.
- Purchases increase meta debt (you're buying on credit)
- Intro typewriter vendor line → browse → **J** or **ESC** to leave

---

## Delivery sequence (chapter win)

1. **Approach** — align ship nose to docking bay (~5s)
2. **Land** — tap **J** to align thrusters, then hold **SPACE** ~1.2s for retro burn (dock scoring)
3. **Touchdown** — clamp cutscene; perfect/rough dock affects credits
4. **Corridor** — 2–3 min themed platformer (branching paths, secrets, NPCs, stealth)
5. **Result** — payout card, debt adjustment, chapter stamp

---

## Audio

100% **procedural** — no shipped `.wav`/`.ogg`. numpy → pygame synthesis.

- Engine tiers, drums, bass, pad, harmonica licks, guitar phrases
- BPM scales with flight pressure; barge proximity motif
- Scene mixing: menu, flight, terminal, shop, delivery, decanting, radio
- Per-chapter inflection modules (`audio/chapter_1.py` … `chapter_6.py`)

Spec + implementation status → [`docs/SOUNDTRACK_PLAN.md`](docs/SOUNDTRACK_PLAN.md)

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
| EDMUND | Local 404 idealist rep (Union charter true-believer) |
| VINCE | Local 404 corrupt rep (skims impounds, takes bribes) |

---

## Tech stack

- Python 3 + **pygame-ce** + **numpy** + **nltk** (VADER, tokenization)
- All graphics: procedural `pygame.draw` — no sprite pipeline
- Architecture: `core/game.py` state loop, global `EventBus`, `RunManager` sector lifecycle
- Tests: `tests/` (saves, checkpoints, terminal NPCs, voices)

---

## Development

| Path | Purpose |
|------|---------|
| `config/settings.py` | Tuning constants — edit here first |
| `docs/ALIVENESS_PUSH.md` | **Active north star** — push/phase roadmap (currently Phase C+) |
| `docs/IMPROVEMENT_PLAN.md` | Historical epic checklist (complete May 2026) |
| `docs/CORRIDOR_DESIGN.md` | Delivery corridor specs |
| `docs/BAX_VOICE.md` | Bax line bank |
| `docs/CLAUDE_ARCHIVED.md` | Historical agent/GDD excerpt |
| `docs/DEAD_DRIFT_GDD_ARCHIVED.md` | Original pitch GDD |

**Git identity:** Chris-dewitt / chnodewi@unc.edu

---

## Known issues / open polish

See **`docs/ALIVENESS_PUSH.md`** for the active backlog (Phases D–H).

Harmonica **play-along** (Epic 11.1b) remains deferred — high effort, low immediate value.

(Market + docking graphics, Bax's Records, NLTK bootstrap, font cache, corridor music,
cargo carousel, HARDCORE, harmonica heal, money source labels, corridor decay,
boss-room set pieces, union reps, NPC keyword normalization, barge feel, string audit
(Epic 9.4), Phase 0 trust fixes, and Phase C gameplay mechanics all shipped May 2026 —
see `docs/DOCUMENTATION_STATUS.md`.)
