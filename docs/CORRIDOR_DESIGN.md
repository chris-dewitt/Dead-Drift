# DEAD DRIFT — Delivery Corridor Design

**Companion to:** `IMPROVEMENT_PLAN.md` Epic 4.
**Audience:** Implementation team. Read after the master plan.

This document defines the per-chapter content for the four delivery corridors. The framework lives in `delivery/corridor/base.py` (per Epic 4.1). Each chapter file consumes that framework and lays out its own level.

> **Style note for level designers.** Each corridor is 2–3 minutes of gameplay split into three rooms with a black-wipe transition between them. Branching paths converge at room transitions. Secrets are off the main path — visible but unreachable from the obvious route, requiring detour or backtrack. Boss room is always the final 10–15 seconds of Room 3.

---

## Universal Element Vocabulary

These are the reusable element classes in `delivery/corridor/elements/`. Every chapter uses them; chapter-specific subclasses extend them.

| Element | Purpose |
|---|---|
| `Platform` | Static ground tile. Walkable. |
| `MovingPlatform` | Patrols along a defined path. Walkable on top. |
| `CollapsingPlatform` | Stable until stepped on; collapses 0.6s after first contact. Respawns 4s later. |
| `Hazard` | Static damage zone (spikes, exposed wire, etc.). Damages courier on contact. |
| `MovingHazard` | Patrol along defined path. Wider damage zone. |
| `OneWayWall` | Wall that blocks one direction only. Useful for forcing flow. |
| `Ladder` | Vertical traversal (`UP` / `DOWN` keys). |
| `NPCEncounter` | Triggers a mini-terminal (~10–15 second turn) when courier enters trigger zone. |
| `Collectible` | Credit chip. Touch to collect. |
| `Secret` | Off-path collectible. Grants credits OR lore fragment. |
| `Checkpoint` | Banner element. Courier passing it sets respawn point. |
| `StealthZone` | Defines a zone with a patrolling sweep (camera / drone / light cone). Detection = damage + retreat to last checkpoint. |
| `BossRoomTrigger` | Entry to the final room. Locks the camera, triggers boss-room music swell. |

---

## Chapter 1 — Acoustic Archive

**Theme:** Smuggler's tunnel under a record shop / unlicensed broadcast hideout.
**Mood:** Underground, warm, gritty. Bass-heavy. People here love music and hate the corp.
**Music:** Distorted vinyl-warm bassline + dirty harmonica wails. Volume swells in Room 3.
**Visual palette:** Brutalist neon in Room 1 → mid-shift in Room 2 → cartoony saturated in Room 3. Reds, oranges, deep purples. Warm.
**Length target:** ~2:15.

### Room 1 — "DOCK ACCESS — SUB-LEVEL 3"
Visual: industrial loading bay. Cargo cranes overhead. Cracked concrete platforms. Brutalist style.

- Entry: courier drops in from the airlock above (small fall animation, ~30 px).
- Three jumps across `Platform` gaps over a `Hazard` floor (exposed cable sparking).
- One `MovingPlatform` segment — patrols horizontally over a wider gap.
- 4× `Collectible` chips along the main path. 1× `Collectible` chip on a higher platform (small detour jump).
- **Checkpoint** at the end of the room.

### Room 2 — "EMPLOYEE CORRIDOR" (the branching room)
Visual: tighter hallway. Posters on the walls (illegal band names — flavor only). Style mid-shift, more color.

- Immediately after the checkpoint, the path forks vertically: high (`Ladder` up) or low (continue forward).
- **High path (riskier, faster):** runs along an upper catwalk with two `MovingHazard` swinging cargo hooks. 1× `Secret` at the far end — small offshoot platform with a hidden lore fragment ("Notes on Gary — he played sax at the depot, you know. Stopped after his wife died. Doesn't talk about it.").
- **Low path (longer, safer):** runs through a maintenance crawlspace. Two `CollapsingPlatform` jumps at the start, then straight running. 3× `Collectible` chips guaranteed.
- Paths converge at a `Ladder` taking the courier up to Room 3.

**NPC Encounter — KENJI THE DJ (mid-Room 2):**
- Located on the low path only. The high path skips this encounter (and its bonus).
- Kenji is a wiry teenager broadcasting illegal music from a hidden booth. Brief 10-second mini-terminal:
  - **Greet / friendly:** Kenji is delighted. Gives the courier a +400 cr "DJ's appreciation" tip and a piece of lore ("MARROW says hi. Says you owe him a favor still.").
  - **Brusque / ignore:** Kenji shrugs, courier moves on. Nothing lost, nothing gained.
- Mechanically a flavor stop. The reward is small but the flavor is large.

### Room 3 — "THE BACK ROOM" (boss room)
Visual: full cartoony saturation. Smoky underground club. Record sleeves on the walls. Soft red and amber light. Small crowd silhouettes nodding to inaudible music.

- Courier enters via a doorway from above. Music peaks.
- Gary (yes, the repo man — but here he's off duty and looking sheepish) is standing behind a counter. The cargo handover is between him and the courier.
- Brief exchange: Gary's portrait dialogue ("you'll forget this happened, courier"), the cargo silhouette transfers from the courier's back to Gary's hands, the count of credits earned this run pops onto screen.
- 8-second sequence. End of corridor.

**Bax lines (sample, see `BAX_VOICE.md`):**
- Entry to corridor: *"Right. We're in the tunnels. Music industry's gone underground. Literally. Don't get crushed by anything."*
- High path on Room 2: *"Catwalk? You're showin' off. I respect it."*
- Kenji encounter: *"Oh — that's the kid Marrow mentioned. Be nice. Or don't. I'm not your conscience."*
- Boss room entry: *"There's Gary. Off-duty Gary. He's gonna pretend he doesn't know us. Play along."*

---

## Chapter 2 — Mycorrhizal Payload

**Theme:** Bioluminescent biolab corridor in a research station. Walls breathe. Reality flickers.
**Mood:** Beautiful, unsettling, slightly hallucinatory. The cargo is changing the world around it.
**Music:** Sparse off-kilter percussion (atonal taps and clicks) with reverb-drowned synth pads. Music occasionally inverts (plays backward for 2 beats) during spore-flicker hazards.
**Visual palette:** Cool — blues, greens, violet. Bioluminescent yellow-green accents. Brutalist Room 1 → organic curving lines in Room 2 → fully alive saturated wall textures in Room 3.
**Length target:** ~2:30.

### Room 1 — "DECONTAMINATION CHAMBER"
Visual: sterile white-blue lab corridor. Clean. Brutalist precision.

- Entry: courier walks in through an airlock door (animation).
- Three `Platform` segments with `Hazard` UV decontamination beams between them. The beams toggle on/off in 1.5-second cycles. Time your runs.
- 1× `NPCEncounter` mid-room: **DR. VALERIA**, a sympathetic biolab technician. Brief mini-terminal:
  - **Therapy / compassion intent:** Valeria opens a shortcut — a secondary door that skips half of Room 2. Bax: *"She just opened a door for us. Don't ask. Just walk."*
  - **Threaten / hostile:** she calls security. A `StealthZone` activates in Room 2 (extra sweeping drone added).
- Checkpoint after the encounter.

### Room 2 — "GROWTH GALLERY" (the spore room)
Visual: walls and floor visibly breathe — a slow 4-second pulse. Bioluminescent fungi everywhere. Organic curves replace straight lines.

- Spore flicker zones — three areas where, if the courier passes through, controls briefly invert (~1.5 seconds, like the in-flight Shroom mechanic). Visual: dense visible spore cloud, faint yellow glow. Player can time their entry to minimize exposure.
- Two `MovingHazard` lab drones patrol along set paths. Don't touch.
- **Branching:**
  - **Main path:** straight through the gallery, dodging spore zones.
  - **Detour:** climb a `Ladder` up into the ceiling vents. Less spore exposure but longer route + 1× `Secret` (a lore fragment: *"Memo: subject 4-A reported sensing 'a friend' inside the spore cloud. Recommended therapy. Subject was decommissioned next quarter."*).
- If Valeria's shortcut from Room 1 is active, half of this room is skipped — the courier emerges past the spore zones directly.

### Room 3 — "RECEIVING LAB" (boss room)
Visual: full saturation. The lab is alive — walls visibly breathe, equipment is overgrown with luminescent fungi, the receiving researcher's coat is dotted with spore stains.

- The receiving NPC: a lab tech who is clearly not okay. They've been around the cargo too long. Their dialogue is fragmented and beautiful (drafted in their NPC file when added).
- Cargo transfer animation: jar passes between hands, briefly glows brighter, both characters flinch.
- 10-second sequence. End of corridor.

**Bax lines:**
- Entry: *"Biolab. Cabin smells funny. Don't breathe through your nose. Or your mouth. Just hold your breath the whole time, mate."*
- First spore zone passed: *"Right, controls just went sideways. Sit with it. We've done this before."*
- Valeria encounter: *"She's kind. Don't be weird about it. Just be a person. Briefly."*
- Boss room entry: *"...the tech in there isn't okay. Be gentle. Hand over the jar. Don't make it weirder."*

---

## Chapter 3 — The Paperwork

**Theme:** Fluorescent-lit government office. Towers of paperwork. Bureaucracy weaponized.
**Mood:** Comically oppressive. Kafka-by-way-of-Office-Space. Everything is too bright. Everything has a form.
**Music:** Typewriter percussion (metronomic typing sounds as the beat) + steady marching bass. Music quickens during stamp-wielding clerk encounters.
**Visual palette:** Beige, gray, fluorescent green, oppressive white. Brutalist office furniture. Style shifts toward cartoony exaggeration in Room 3 (forms grow comically large, clerks become caricatures).
**Length target:** ~2:45 — longest corridor because the comedy needs room to breathe.

### Room 1 — "INTAKE FLOOR" (the form-filing room)
Visual: open-plan government office. Rows of empty desks. Fluorescent lights buzzing audibly.

- Entry: courier enters through a turnstile (small animation, costs 1 second).
- The floor is divided by `OneWayWall` cubicles that force the courier through a specific zigzag.
- Three mandatory `NPCEncounter` clerks — each is a brief stamp-wielding mini-terminal:
  - **CLERK 1 — Margaret:** wants Form 27-B. Player types "27-B" or "form 27-B" → waved through. Anything else: courier is sent to the back of a queue (5-second delay). After delay, automatic pass.
  - **CLERK 2 — Howard:** wants the courier's "purpose of visit." Any non-empty input → waved through. Howard doesn't actually read it.
  - **CLERK 3 — Brenda (the difficult one):** wants the player to argue Union Bylaw 12-F is invalid. Input must include the word "void" or "null" or "expired" → bonus credit (+600 cr) plus a fast-track stamp. Anything else: standard 5-second delay.
- 5× `Collectible` chips spread across the desk row.
- Checkpoint at the office exit.

### Room 2 — "FILE ROOM 4" (the platforming room)
Visual: towering vertical shelves of paperwork stretching impossibly high. Style starts brutalist, shifts to absurd as the cabinets grow taller than makes sense.

- Vertical traversal — the courier must climb. `CollapsingPlatform` stacks of paper (file boxes) that crumble if stood on too long.
- `MovingPlatform` filing-cart segments (a literal filing cart on rails — surprisingly fast).
- 2× `Secret`:
  - One off-path file box contains lore fragment: *"Form NS-19B (opt-out from clone debt). Application: REJECTED. Reason: applicant currently deceased. See Nova Soma Clause 9, Section F."*
  - One hidden floor below a `CollapsingPlatform` contains +1500 cr (a discarded petty-cash envelope).
- Branching: standard high path (faster, riskier collapsing platforms) vs. low path (longer, safer ladder climb).

### Room 3 — "EXECUTIVE PROCESSING" (boss room)
Visual: opulent corner office. Mahogany desk. Window overlooking nothing in particular. Visible Nova Soma "Employee of the Quarter" plaques on the wall. Style fully saturated cartoony.

- The receiving NPC: Union Dispatcher (existing NPC). His office. He's surprised to see a courier physically present.
- Brief negotiation — same NPC dialogue engine as existing terminal, but with the visual context of his office (desk between the courier and him, secretary visible in background).
- Cargo handover: the paperwork is literally so heavy the courier visibly buckles handing it over. Comedic.
- 12-second sequence.

**Bax lines:**
- Entry: *"Office. Real office. With fluorescents. They want forms. Just give 'em forms. Don't make it weird."*
- First clerk encounter: *"Margaret. Form 27-B. Just say the form number, mate. It's a one-word answer. Don't get poetic on me."*
- File room entry: *"Up we go. There are receipts up there from before the Republic. The Republic. Climb."*
- Boss room entry: *"That's the Dispatcher. In his actual office. We've never been in an actual office before. Be respectful or whatever."*

---

## Chapter 4 — Schrödinger Hotel

**Theme:** Luxury orbital hotel. Quantum doors. Bellhops who may or may not exist. The cargo itself is contagious to reality.
**Mood:** Eerie, opulent, dreamlike. Like waking up at 4 AM in a five-star hotel and not being sure if you're still asleep.
**Music:** Lush hotel-lobby jazz, occasionally glitching for 2-3 seconds (skipping records, frequency shifts) when the player observes a quantum element.
**Visual palette:** Gold, ivory, deep purple, soft pink. Expensive. Brutalist Room 1 (service corridor) → mid-shift Room 2 (guest hallway) → fully painted-style Room 3 (penthouse).
**Length target:** ~2:30.

### Room 1 — "STAFF ENTRANCE — DO NOT BE SEEN"
Visual: service corridor. Industrial pipes overhead but with carpet on the floor. The contrast is the joke.

- **Major mechanic: stealth.** A `StealthZone` covers the whole room. A bellhop patrols on a set path, light cone visible.
- Hide behind `Platform` cover (laundry carts, room service trays).
- Caught: courier is "escorted out" (5 hp damage + retreat to checkpoint). The bellhop's animation when catching you is comedically polite — he just gestures to the exit.
- 2× `Secret`:
  - Hidden behind a service door: lore fragment about the hotel's clientele (*"Guest in room 1408 has been here for forty-three years and never opened the curtains. Doesn't tip."*).
  - In a cleaning supply closet: +800 cr "guest left this for housekeeping."
- Checkpoint at the elevator.

### Room 2 — "GUEST FLOOR — 47" (the quantum room)
Visual: long hallway. Identical doors on both sides. Style mid-shift.

- **Major mechanic: quantum doors.** Five doors. Two are real. Three are not. The player chooses which to enter.
- A door that "isn't real" passes the courier through with no effect (visually flickers, "wasn't there after all" moment).
- A door that **is** real opens to a small room — randomly one of:
  - 1× `Secret` (lore fragment or credits).
  - A patrolling bellhop (back to Room 1's stealth dynamic for 5 seconds).
  - A direct shortcut forward.
- The courier can ignore doors entirely and just walk the corridor — there's a `Hazard` strip of vacuum-cleaner robots zigzagging across the floor. Manageable but distracting.
- **NPC Encounter — MX. DELL:** a hotel concierge (literally appears from nowhere mid-room). They ask "Sir / madam, is the package... live?" — referencing the VIP. Player input determines outcome:
  - **"Yes" / "Alive":** Concierge gives directions, +200 cr "concierge tip."
  - **"No" / "Dead":** Concierge's expression flickers (briefly becomes their portrait's "annoyed" variant), they walk away. Nothing lost.
  - **"Both" / paradox:** Concierge briefly fragments into the existing portrait glitch system. Bax: *"You broke the concierge. ...Anyway. Keep moving."* +500 cr "philosophical compliment" award.

### Room 3 — "PENTHOUSE SUITE" (boss room)
Visual: full painted-style saturation. Wall-sized window over the planet below. Plush furniture. Fireplace burning (in space, somehow). The Schrödinger VIP's actual room.

- The receiving NPC: **MORWENNA** (existing insurance adjuster, repurposed here as the VIP's representative — they're paying for delivery and assessing the VIP's state).
- Brief exchange — Morwenna asks "is the passenger alive or deceased?" — the existing `SchrodingerVIP.state_for_terminal()` informs the outcome.
- If the VIP's state is `unobserved`, Morwenna opens the box themselves. State collapses now. Outcome ledger captures the moment.
- Final dialogue: a small philosophical exchange about whether observation can be ethical. 12-second sequence.

**Bax lines:**
- Entry: *"Hotel. Luxury one. Don't touch anything. They charge for breathing."*
- First bellhop sighting: *"Hide. HIDE. He'll be VERY polite about it and that's worse somehow."*
- Quantum doors: *"Pick a door, mate. Or don't. They're not all real anyway. ...I don't know which are which. I don't think I'm supposed to know."*
- Concierge encounter: *"Mx. Dell. Don't lie. Or do. Lie creatively, see what happens."*
- Boss room entry: *"Penthouse. Morwenna's waiting. Don't make her open the box. ...Actually, do. I want to see."*

---

## Per-Chapter Difficulty Profile

| Chapter | Platforming difficulty | Combat difficulty | Stealth difficulty | NPC density |
|---|---|---|---|---|
| 1 — Acoustic Archive | medium | none | none | medium (Kenji) |
| 2 — Mycorrhizal Payload | medium (inversions) | none | low (Valeria branch only) | medium (Valeria + boss) |
| 3 — Paperwork | high (vertical) | none | none | high (3 clerks + boss) |
| 4 — Schrödinger Hotel | low | none | high (Room 1 + 2 patrols) | medium (Concierge + boss) |

No combat in corridors. The flight scenes are where ship combat happens. The corridor is about traversal, stealth, conversation, and atmosphere. This is deliberate — it lets the corridor be its own thing.

---

## Known issues (May 2026 playtest + code review)

| Chapter | Issue | Status |
|---------|--------|--------|
| **Ch.3 Paperwork** | **Input lock at ladder / documents** — clerk `_CorridorDialog` modal; ESC/pause don't work in `DELIVERY` state | Open — Chris repro May 2026 |
| **Ch.3 Paperwork** | `OneWayWall` cubicle zigzag (Room 1) — walls drawn but **collision not wired** in `base.py` | Open — Phase 0.10 |
| **Ch.3 Paperwork** | Clerk "5-second delay" penalties are text-only | Open |
| **Ch.3 Paperwork** | Only 1 checkpoint (Room 1 exit); File Room 4 has none | Open |

Chris playtest: document chapter corridor reported broken. See `docs/IMPROVEMENT_PLAN.md` Epic 4.8.

---

## Implementation Notes for the Team

- **Build the framework first** (`base.py` + element classes). Get one trivial test corridor working end-to-end before content-loading any of the four chapters.
- **Implement Chapter 1 second** — it has the gentlest mechanics (no stealth, no quantum, just platforming + one NPC). Polish this corridor to a shine; it sets the bar for the others.
- **Then 3 → 2 → 4.** Save the most ambitious (Schrödinger Hotel with its quantum doors) for last so the framework has been battle-tested.
- **Music tracks** can be procedurally generated using `audio/synth.py` patterns — same approach the existing sector pads use. Each chapter gets a unique seed + tempo profile.
- **The cargo silhouette deteriorates progressively** as the courier takes damage — render the cargo as a separate vector overlay on the courier sprite, updating its damage state from the existing cargo integrity property.
- **Camera scroll uses parallax** — backgrounds drift at 0.3× courier speed, foreground at 1.0×, far-background ambient elements at 0.1×. Standard side-scroller technique.

---

## What to playtest first

When each corridor is content-complete, prioritize this playtest order:

1. **Time-to-complete** — is each corridor 2–3 minutes? Too long is worse than too short.
2. **Jump locomotion** — can the player jump from a location and move off/across from it, rather than only bobbing up and down in place?
3. **Ladder exits** — can the player leave ladders onto nearby platforms, and does control return immediately at the bottom?
4. **Branching path balance** — are players actually picking the high path, or always defaulting to safe?
5. **Secret discoverability** — how many runs before a player finds at least one secret per corridor?
6. **NPC encounter pacing** — does the mini-terminal feel like a beat or an interruption?
7. **Boss room arrival** — does it feel earned? Are players ready for "the moment" by the time they enter?

Tune from there.
