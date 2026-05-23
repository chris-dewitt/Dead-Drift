# DEAD DRIFT — Soundtrack Master Plan

**Codename:** *HIGHWAY BLUES FROM THE EDGE OF THE HELIOSPHERE*
**Companion to:** `IMPROVEMENT_PLAN.md`, `CORRIDOR_DESIGN.md`, `BAX_VOICE.md`
**Audience:** Dead Drift implementation team. Read after the master plan.
**Constraint:** 100% procedural. Zero asset files. Everything is `numpy` → `pygame.sndarray.make_sound`. The score generates itself, fresh, every boot.

> **How to read this doc.** Eight sections, top-to-bottom. Section 1 is the pitch — the sonic identity we're chasing. Sections 2–5 define the language, the album-arc, the per-chapter palettes, and the per-sector dramatic curve. Sections 6–7 are the reactive systems that turn the score from a *playlist* into a *performance*. Section 8 is the implementation roadmap mapped to existing files in `audio/`.

---

## Locked design decisions (decisions log)

These are the directional answers backing this plan. Don't re-litigate — implement against them.

- **Genre:** *Highway-blues space-noir.* Not chiptune. Not Vangelis-pure. Not Hotline-Miami synthwave. The signature is **a Cockney harmonica and a Korg Polysix in the same cockpit, in a long-haul truck the size of a city block, on a road that's mostly dark.** Vangelis × Ry Cooder × Mark Lanegan × Tangerine Dream × Daft Punk's *Tron*. Closest single-track reference: Cooder's *Paris, Texas* main theme played by Vangelis's *Blade Runner* rig with a drum machine in the next room.
- **Procedural-only:** non-negotiable. No `.wav`/`.ogg` files ever ship. We win awards by *generating* the score, not by licensing one. Every loop is built at boot from `numpy`; that's also our marketing story.
- **No vocals, ever.** Bax sings *one* hook (Section 7.4) and that's it. Wordless score otherwise. The cockpit chatter is the lyric.
- **Diegetic-first.** Whenever music can come from a thing in the world — Bax's harmonica, a fuel canister chime, a Repo Barge's tow-warning siren, the cockpit radio — it does. Non-diegetic only for menus, decanting, and run-end stings.
- **One key center per run, modulated per chapter.** A natural minor is the home key. Every chapter transposes the same modal palette to a new root (Section 4). Aural continuity across a campaign without each chapter feeling like the same song.
- **Tempo is gameplay.** BPM is not fixed at 96. The drum loop's playback rate is *driven by sector pressure* (Section 6.1). A clean drift is 84 BPM. A hot pursuit at sector 5 with a barge tethered is 124 BPM. Same loop, same key, different urgency.
- **Stems, not tracks.** We never bake a 2-minute finished track. We bake **8 stems** — kick, snare/clap, hat, bass, pad, arp, harp, guitar — and the mixer is the composer. Award-jury angle: "the soundtrack is a real-time composition, not a playlist."
- **Cohesion override:** every new stem must obey the *Dead Drift Sound* rules in Section 2. If it doesn't, it doesn't ship. Variety is earned by recombination, not by genre hopping.
- **Bax owns the harmonica.** It is *his* instrument, diegetically, and the score reflects that. When Bax goes quiet (panic, hull-critical), the harmonica drops out of the mix. When Bax sasses, a lick punctuates the line. The audio system already has a Bax voice channel; the harp becomes a second voice for him.
- **Threat motif:** every antagonist has a two-note signature embedded into the score (Section 7.2). Hearing it without seeing the barge is the warning.
- **Mix budget:** 5 active stems max at any moment. We're not Hans Zimmer. Crowding the mid-range is the single most common amateur-soundtrack mistake; we will not make it.
- **North-star metric:** a player who hears 15 seconds of *any* run clip with the visuals blanked can tell you (a) which chapter it is, (b) whether the player is in trouble, and (c) that it's Dead Drift.

---

## Section 1 — Sonic Identity (the pitch)

The award we're chasing is not "Best Music." The award we're chasing is **"Best Use of Audio,"** because we are not writing songs — we are writing a *cockpit*.

### 1.1 The world the music lives in

DEAD DRIFT takes place in a solar system where:
- Every courier is in catastrophic debt to a clone corporation.
- The repo men are a union.
- The only place that still feels like *yours* is the inside of your ship.

The music has to sound like **the last private room in the universe.** Lonely, lived-in, slightly broken, defiant. A worker's score, not a hero's score. Closer to Tom Waits than to John Williams. Closer to a long-haul trucker's CB chatter than to a starfleet bridge.

### 1.2 The signature instrument trinity

Three instruments carry 80% of the identity. Each owns a sonic register and a narrative function.

| Instrument | Register | Owner / narrative role |
|---|---|---|
| **Harmonica (diegetic)** | high mids, breathy | Bax. Loneliness, sass, blue-collar fatigue. *In* the cockpit. |
| **Polysix-style detuned-saw pad** | low mids, washed | The void outside. The endless drift. *Through* the cockpit window. |
| **80s LinnDrum machine + walking sub-bass** | low end, locked | The job. The clock. The route. The fact that the rent is due. *Under* the cockpit floor. |

Everything else (acoustic guitar phrases, slide notes, arpeggio top voice, sector mood pads) is **garnish on those three.** No new genre lanes.

### 1.3 The forbidden palette

To stay cohesive — and to stay *uniquely* Dead Drift — these things never appear in the score:

- **Orchestral strings.** No swelling violins. We are not Mass Effect.
- **Chiptune square leads.** We are not pixel-art. We are vector-line neon.
- **Modern EDM drops.** No supersaws, no festival risers, no sidechain pumping. We are 1983, not 2018.
- **Choir / "ah" pads.** Too on-the-nose for "space."
- **Major keys** for more than 8 bars at a stretch. Even the win-screen is in modal mixolydian, not pure major. *We are perpetually in debt; the music never resolves brightly.*

### 1.4 The signature *moments* the score must own

If a streamer clips one of these moments, the score has to *be* the clip. Each one is implemented in Sections 6–7.

1. **The slingshot release.** Reverse-cymbal swell → pad swell up a perfect fifth → harmonica wail → drum fill → back into the groove one bar later.
2. **The barge proximity dread.** A low, *detuned* harmonica drone fades in at 320 px. Two notes. A minor second. Specifically the *Jaws* relationship, executed on a harp, sounding like a tired union foreman humming the wrong notes to himself.
3. **The tether snap.** Snare gets a flam, the bass walks down a tritone, the pad opens up. Three frames of relief written into the score itself.
4. **The clone tank decanting.** Everything stops. One slide-blues note. A 4-second silence. The receipt printer. The next slide-blues note, a step lower. **The score is a funeral every time you die.**
5. **The delivery handoff.** Chapter-specific cargo theme finally resolves — *the only place in the entire game the music allows itself to land on the tonic.*

---

## Section 2 — The DEAD DRIFT SOUND (production rules)

Every procedural stem must obey these or it doesn't ship. This is the cohesion contract.

### 2.1 Key center & modal palette

- **Home key:** A natural minor (A, B, C, D, E, F, G).
- **Approved modes:** Aeolian (default), Dorian (cargo themes that want hope), Mixolydian (delivery success only), Locrian (chapter 4 Schrödinger VIP only).
- **Approved tensions:** ♭7 (always), ♭6 (mood pads), 9 (arpeggio top voice), ♯4 (slingshot moments — one bar, then resolve). **No major 7.** No.
- **Forbidden:** Lydian, Phrygian (chapter 4 is the closest we get), pure major, blues scale ♭5 used as a chord tone (only as a passing tone in licks).

### 2.2 Tuning & detuning

- All synth voices are detuned ±4–9 cents in stacks of 2–3. *Never* in-tune. The cockpit is broken; the synths are broken.
- The harmonica is **deliberately a hair flat** (–6 cents) against the synths. This is the cockney/blue-collar signal. Bax has been gigging too long.
- The acoustic guitar is **slightly sharp** (+3 cents). It's the one optimistic voice in the room. It loses every argument.

### 2.3 Rhythm contract

- **Drum machine BPM range:** 78–128. Default 96. Modulated by `flight_pressure` (Section 6.1).
- **Drum kit identity:** LinnDrum-flavored gated snare + tight kick + closed hat. No toms (we don't have room in the mix). Clap doubles snare only at high pressure.
- **Bass:** always walking (eighth notes), always plays root–♭7–5–root or root–5–♭7–octave. *Never syncopated.* The bass is the union, and the union shows up on time.
- **The "1" is always strong.** The downbeat is sacred. Players who tap their foot are the goal.

### 2.4 Mix contract (the 5-stem rule)

At any frame, no more than 5 stems may be audible above –24 dBFS. The audio manager enforces this with a stem-priority list:

1. Engine drone (always on)
2. Drums (if active)
3. Bass (if active)
4. Pad / arp (one or the other, never both at full)
5. **One voice** — harmonica, guitar, slide, or vocal stem — chosen by scene

When a 6th wants in, the lowest-priority current stem ducks 6 dB until the new voice finishes. The result: **the mix breathes.** Crowded soundtracks are amateur soundtracks.

### 2.5 Loop contract

- Every loop is **2 or 4 bars** at base tempo. Never odd lengths. Never 8 bars (gets boring fast at 60 FPS gameplay).
- Every loop must crossfade at the loop boundary (existing `new_wave_pad.build_new_wave_pad` already does this — port the pattern to drum/bass).
- Every loop must have a **silent variant** baked at the same length, so the mixer can drop to silence on the bar line without choking the loop mid-phrase.

### 2.6 The "tape hum" signature

A single, almost-subliminal layer underneath *everything* in the game: pink noise filtered to ~80 Hz–4 kHz at –32 dBFS, with a 60 Hz hum (–38 dBFS) and a faint 7.5 ips tape-wow modulation. **This is the glue.** It plays during the menu, during flight, during the terminal, during the decanting screen. Players will not consciously hear it. They will hear its *absence* if you mute it. This is what makes a soundtrack feel like a soundtrack and not a stack of sounds.

---

## Section 3 — Album Structure (the campaign as a record)

A 4-chapter campaign is a 4-side double album. Treat it like one. The track listing the player experiences across a clean campaign run looks like this:

### Side A — *Acoustic Archive*
1. **Cold Boot** *(menu)* — slide-blues notes over the tape-hum bed. No drums.
2. **Decant & Sign** *(loadout draft)* — pad + arp, no drums, very dry.
3. **Highway One** *(sectors 1–2)* — full bandstand. The signature.
4. **Roadside Confession** *(terminal encounter, sector 2)* — drums drop out. Pad alone + sparse harp.
5. **The Long Inhale** *(sectors 3–4)* — drums return, bass walks darker.
6. **Last Mile Before the Tunnel** *(sector 5)* — pressure peaks. Threat motif on harp.
7. **Smuggler's Welcome** *(delivery corridor)* — chapter-specific cargo theme — *vinyl-warm, bass-heavy, harp solos.* (See `CORRIDOR_DESIGN.md`.)
8. **Sign Here, Please** *(delivery success screen)* — the only mixolydian moment in the chapter. 12 seconds. Then back to silence.

### Side B — *The Mycorrhizal Payload* (Chapter 2)
Same template. Modulated up a minor third. Arp gets weirder, pad gets wet (Section 4.2).

### Side C — *The Paperwork* (Chapter 3)
Same template. Drum machine gets *quantize-stuttered* once per minute — the bureaucracy glitching the groove (Section 4.3).

### Side D — *The Schrödinger VIP* (Chapter 4)
Same template. Locrian mode. The bassist has stopped showing up to work. *The longest silence in the game lives here.*

### Hidden side — *Decanting* (death)
- One slide-blues note, one printer, one breath, repeat. **This is the score every run ends with for 99% of players.** It must be the most haunting thing in the game.

---

## Section 4 — Per-Chapter Sonic Identity

Each chapter modulates the home key, adds a *signature instrument*, and inflects the drum kit and pad voicing. The bandstand stays the same; the band's *attitude* changes.

### 4.1 Chapter 1 — Acoustic Archive
**Home key:** A natural minor (default).
**Signature instrument:** Distorted electric harmonica through a tube amp. (Same harp synth, run through a soft-clip saturator at +3 dB drive.)
**Kit inflection:** Snare gets +20% reverb. Hi-hat slightly behind the beat (swing 54%).
**Pad voicing:** Minor 7th, lush. The most "music store" chapter — appropriate, it's a record-shop run.
**Cargo theme motif:** Descending A–G–E–D over the bass walking up. A *pulling against gravity* feeling. Lives in the delivery corridor only (see `CORRIDOR_DESIGN.md` ch.1).
**Sonic event tied to cargo damage:** Audio fidelity literal degradation — when the `AcousticArchive` cargo takes damage, the **entire mix is bit-crushed** progressively (4 → 8 → 12-bit reduction). The score *becomes* the cargo. *This is the chapter's signature trick.*

### 4.2 Chapter 2 — The Mycorrhizal Payload
**Home key:** C natural minor (up a minor third).
**Signature instrument:** Bowed-saw lead — a slow-attack triangle through a comb filter, sounds like a wet wineglass. Used sparingly, only when spore_level > 0.5.
**Kit inflection:** Snare swapped for a *rim shot + tape echo* that mistimes by 30–60 ms randomly. The drummer is high.
**Pad voicing:** Dorian — the relative brightness makes the inversions sound *wrong* against the bent harp, which is the point.
**Cargo theme motif:** Two phrases that *almost* repeat but never line up, like a canon with one voice 7 beats behind the other.
**Sonic event tied to cargo mechanic:** When the spore mechanic inverts controls, the **stereo field inverts too** for the 4-second window. L→R, R→L. Bax says "either that or space is sideways now." The music says it too.

### 4.3 Chapter 3 — The Paperwork
**Home key:** F♯ natural minor (tritone from chapter 2 — deliberate; this chapter is *paperwork*, the most cursed key gets it).
**Signature instrument:** Mechanical typewriter rhythm overlay. Pitched at the kick frequency, panned dead center, plays the actual current drum pattern but as typewriter clacks. The drummer *is* a typewriter.
**Kit inflection:** Snare replaced by a manila-folder slap. Hi-hat replaced by a stapler. Played dead-straight — no swing, no human feel. *The bureaucracy is on the beat.*
**Pad voicing:** Suspended seconds (sus2) — never resolves, like a form that won't process.
**Cargo theme motif:** Eighth-note ostinato on E, repeating, *for 47 bars before any chord change.* The score is the line at the DMV.
**Sonic event tied to cargo mechanic:** Every time a `TriplicateForm` popup interrupts gameplay, the music **freezes on a single sustained chord** until the player files. The score literally pauses for paperwork.

### 4.4 Chapter 4 — The Schrödinger VIP
**Home key:** E Locrian (the diminished mode — the only chapter that uses it).
**Signature instrument:** **Silence.** This chapter's signature is the *removal* of stems. The bass is gone. The drummer is half-present. The harmonica plays one note per 40 seconds.
**Kit inflection:** Half-time feel. Brushes instead of sticks. Every 4th measure the kick *doesn't* hit.
**Pad voicing:** Locrian — the only properly *unstable* mode in Western music. Sounds like the universe is unsure if it should exist.
**Cargo theme motif:** A two-note interval — minor second — looping in the upper register. Specifically the **wave-function collapse motif:** every time the VIP's state is "observed" (`speed > 200`), the motif inverts to its tritone substitute mid-phrase. The player can't predict which note will play next. *The music is the cargo.*
**Sonic event tied to cargo mechanic:** When the VIP is observed alive, a single warm pad chord plays for ~1s. When observed dead, complete mix silence for the same duration. The mix *blinks*. By sector 4, the player learns to dread the silence.

---

## Section 5 — Per-Sector Dramatic Curve

Within a single chapter run, the 5 sectors form a dramatic arc. The score implements that arc through layer activation, not new compositions.

| Sector | Mood label | Tempo | Active stems | Threat motif | Notes |
|---|---|---|---|---|---|
| **1** | *Pull out of port* | 84 BPM | drums (soft), bass, pad, arp | off | Player is settling in. Harp every 10–14 s. The score is warm. |
| **2** | *Open road* | 96 BPM (default) | drums, bass, pad, arp, harp | off | The signature bandstand. Guitar phrase every 8–16 s. |
| **3** | *First trouble* | 102 BPM | drums (gated harder), bass, pad (narrower voicing), harp | **on** at proximity | Threat motif pre-arms — heard once at sector entry before any barge spawns. |
| **4** | *Run* | 112 BPM | drums (full intensity), bass (walking ♭7s), pad (low only), no arp | active | Arpeggio drops out. The high register is gone. **The score has lost its top voice.** |
| **5** | *Final mile* | 124 BPM | drums (clap doubled), bass, pad (octave drop), harp (high distressed wail) | constant low drone | Last mile. Slingshot bonuses pay *double* musically — full reverse-cymbal swell + key change up a whole step for 8 bars. |

After sector 5: tempo *snaps* back to 96 for the delivery corridor (chapter-specific theme takes over). This snap is part of the reward — the player's nervous system gets to come down.

---

## Section 6 — Adaptive / Interactive Systems

The above is the *score on paper*. This section is **the performer.** This is where Dead Drift's audio system stops being a soundtrack and starts being an instrument.

### 6.1 `flight_pressure` — the central driver

Define a 0..1 scalar called `flight_pressure`, updated every frame in `AudioManager.update()`. It is the **single number that drives tempo, kit intensity, bass density, and pad voicing.**

```
flight_pressure = clamp01(
    0.20 * normalize(speed, 0, MAX_VELOCITY)
  + 0.30 * (1.0 - hull_pct)
  + 0.25 * barge_threat            # 0 if no barge in range, 1.0 at tether-active
  + 0.10 * sector_index / SECTORS_PER_RUN
  + 0.15 * cargo_alarm             # chapter-specific 0..1 (Section 4)
)
```

Mappings:

- **Drum BPM:** `lerp(84, 124, flight_pressure)` — but only re-pitched at bar boundaries. *Tempo never changes mid-bar.*
- **Kit intensity:** `lerp(0.6, 1.0, flight_pressure)` — passed to `build_drum_loop(intensity=…)`. Snare clap doubles above 0.75.
- **Bass density:** `flight_pressure < 0.4` → half notes; `0.4–0.75` → quarters; `> 0.75` → eighths.
- **Pad voicing width:** `flight_pressure < 0.5` → 4-voice spread; `≥ 0.5` → root + ♭7 only (the pad *closes in* on the player).
- **Arp gate:** `flight_pressure > 0.7` → arp drops out. The top voice is what you lose when you're in trouble.
- **Harp tension:** `flight_pressure > 0.6` → harp pitch-bends downward 20 cents over its phrase. Bax is *strained*.

### 6.2 Threat motif (auto-cued)

A short two-note motif lives in the synth engine as `barge_motif()`. It is:
- A minor second (e.g., A–B♭) played on the harp at –9 cents.
- Plays *once* the first time a barge enters 600 px in any sector ("you see it before you hear it close").
- Plays *as a drone* (looping low octave at –24 dBFS) whenever a barge is within 320 px (existing `EVT_BARGE_NEARBY`).
- **Resolves up to the minor 3rd** the moment the barge is destroyed or out of range for >3 s. *The resolution is the reward.* Players will learn this without being told.

### 6.3 Slingshot stinger

Already partially in the system as `slingshot_whoosh`. Expand to a *musical* event:
- Trigger on `EVT_SLINGSHOT`.
- On the next bar boundary: pitch the pad up a perfect fifth for 4 bars.
- One harmonica lick on top (pick from `_LICK_PATTERNS` 1, 7, or 9 — the high-register runs).
- One reverse-cymbal swell on the *previous* bar (pre-roll). Implement as a 1.5 s noise burst with `np.linspace(0, 1, n)` envelope.
- Return to base key at bar 5. The key change *is* the reward.

### 6.4 Tether snap musical resolution

Already partially in the system as `tether_snap`. Expand:
- Trigger on `EVT_TETHER_SNAP`.
- On the next sub-beat: snare flam (existing kit, two hits 30 ms apart).
- The bass *walks down a tritone* over the next 2 beats (interrupt current bass pattern).
- Pad opens to a full 5-voice spread for 2 bars.
- Returns to normal pattern at bar 3.
- **This is the only musical "victory cue" outside the delivery sequence.** It should feel like an exhalation.

### 6.5 Hull-state mix degradation

A single hull-driven master DSP chain. Three thresholds:

| Hull % | DSP effect |
|---|---|
| 100–60% | Clean. Tape hum only. |
| 60–30% | Bit-crush at 10 bits. Drums get a +2 dB transient boost. *The mix gets edgier.* |
| 30–0% | Bit-crush at 6 bits + low-pass at 2 kHz + 3.5 Hz tremolo on the master. *The cockpit speaker is broken.* The harp drops out entirely. Bax sounds further away. |

Implement as a single `MasterFX.process(stereo)` that runs on the mixed output once per buffer. Skippable in `--no-fx` debug mode.

### 6.6 Engine drone as harmonic content (not just SFX)

The 5-tier engine drone is *currently* a sound effect. **Promote it to a music stem.** Tune each tier to a chord tone in the current key:

| Tier | Speed | Frequency | Role in key (A minor) |
|---|---|---|---|
| 0 | drift | 55 Hz | root (A) |
| 1 | cruise | 65.4 Hz | ♭3 (C) |
| 2 | thrust | 73.4 Hz | 4 (D) |
| 3 | fast | 82.4 Hz | 5 (E) |
| 4 | redline | 98 Hz | ♭7 (G) |

As the player accelerates, the engine *plays the scale.* The full-throttle ship is the dominant chord. The drifting ship is the tonic. **The player is the bassist.** When the chapter modulates key (Section 4), the engine tier roots transpose with it.

### 6.7 Per-sector cargo audio degradation

For chapters with cargo damage feedback (currently only Acoustic Archive — Section 4.1), expose a `cargo_degradation: float` (0..1) on the AudioManager. Applied at master:
- 0.0 → clean.
- 0.5 → 10-bit crush + 200 ms slap delay at 18% wet.
- 1.0 → 6-bit crush + 600 ms tape-echo at 32% wet + 80 Hz hum bumped to –22 dBFS.

The score becomes *physically damaged.* Players will hear what their cargo sounds like dying.

---

## Section 7 — Diegetic & Hidden Systems (the "awards" stuff)

This is what jurors and streamers screenshot. The unique hooks.

### 7.1 The cockpit radio (random station seeds)

Add a fifth audio scene: **`SCENE_RADIO`** — togglable mid-flight with the **R** key (currently unused in main game). When active:
- The bandstand ducks 12 dB.
- A 4-second "tuning" sweep (white noise filtered from 200 Hz → 8 kHz).
- A "station" plays — a procedurally-generated 30-second piece in one of these styles, randomly seeded per run:
  - **Pirate blues:** harmonica + guitar duet, no drums. Sounds *better* than the score, in a way that makes the silence after worse.
  - **State propaganda:** spoken-word voice blip stream (we already have voices) over a major-key pad. *The only place in the game that uses major.* Disgusting on purpose.
  - **Union solidarity broadcast:** drum + bass only, no melody. A workers' march. Repo barge proximity instantly cuts it off — *the union doesn't broadcast where the foreman can hear.*
  - **Dead air:** static + a heartbeat. Subliminal kick at 56 BPM. Players who linger here for >60 s get an EVT_BAX_SPEAK reaction.

The radio is a *toy*. It rewards exploration. Streamers will clip the propaganda station for free marketing.

### 7.2 Antagonist signatures

Each major antagonist class gets a sonic ID assigned at spawn. The score *plays* the enemy before drawing it.

| Antagonist | Signature | Trigger |
|---|---|---|
| Repo Barge (standard) | Two-note minor 2nd on detuned harp | Within 600 px (one-shot) + within 320 px (drone) |
| Repo Barge (TORCH state) | Add a *slow clap* on the off-beat | TORCH state entered |
| Union Dispatcher (terminal NPC) | Tritone sub on the pad on terminal open | EVT_TERMINAL_OPEN with dispatcher NPC |
| Insurance Adjuster (terminal NPC) | A single 880 Hz sine tone — perfectly in tune, the *only* in-tune thing in the game | EVT_TERMINAL_OPEN with adjuster NPC |
| Schrödinger VIP (cargo, ch.4) | Silence + a single high E5 every 40 seconds | While cargo onboard |
| Clone tank (death) | Slide-blues note + receipt printer | EVT_SHIP_DESTROYED |

### 7.3 Bax-driven musical reactions

Bax already triggers on a dozen events. Expand the harp lick pool from 10 to **30 patterns**, and *tag each pattern with a mood*: `cocky`, `weary`, `panic`, `delighted`, `lonely`, `sarcastic`. When Bax speaks, the *next* lick is filtered by the mood of his line. The harp becomes a continuation of his voice — like a comedian's rim shot, but a sad one.

Approximate mood-to-event table:

| Event | Mood filter for the next harp lick |
|---|---|
| Slingshot achieved | `delighted` |
| Tether snap | `cocky` |
| Hull critical | `panic` |
| Idle (>25 s no speech) | `lonely` or `weary` |
| Module unbolted | `weary` |
| Fuel canister grabbed | `cocky` |
| Barge nearby | `sarcastic` |

### 7.4 The one and only vocal hook

**Once per campaign**, on the *first delivery success of a run*, Bax hums. Not sings. Hums. Four bars. A wordless melody in A natural minor, descending A–G–E–D–C–A. It plays once over the delivery success screen, then is never heard again *in that run.* The next run, a different hum (we ship 8). Players who clear all 4 chapters in one session will have heard 4 of the 8.

The full set unlocks as a **menu jukebox** after first campaign clear (see `meta.chapters_completed`). The player can replay any hum they've heard. *Achievement: hear all 8.*

This is the emotional payload. This is the moment a player goes "oh." This is the clip that goes on Twitter.

### 7.5 Decanting silence

The decanting screen currently plays sparse slide notes. Make this **the most musically composed moment in the game.**

- One slide-blues note, 1.6 s.
- 3 s of silence except tape hum.
- Receipt printer SFX (procedural — implement as `decanting_printer()` in `synth.py` — small kick drum + 6 quick high-frequency clicks).
- 4 s of silence.
- One slide-blues note a whole step *lower* than the first.
- Hold until the player presses ENTER.

This is the funeral. Don't crowd it. **The silence is the music.**

### 7.6 The main-menu listening room

When the player idles at the main menu for >2 minutes, the visual fades to a slow-rotating starfield and the audio enters **"long-form" mode** — the new-wave pad extends to a 90-second composition (chord progression: Am–F–G–Em–Dm–G–C–E7, then home), with a single harmonica solo over the back half. No drums. No bass. Just the void and the harp.

This is a screensaver. It's also a free 90-second soundtrack sample for anyone who walks past the booth at Steam Next Fest with the game idling.

---

## Section 8 — Implementation Roadmap (mapped to existing code)

All work lives under `audio/`. Existing files referenced. New files noted. No content removed.

### 8.1 Foundations (must land first)

**8.1.1 `audio/synth.py` — tape-hum bed.**
New function: `tape_hum_bed(duration=8.0)` — pink noise + 60 Hz hum + tape-wow LFO. Looped on a new channel `_HUM_CH = 27` at –32 dBFS. Plays in every scene. *Section 2.6.*

**8.1.2 `audio/audio_manager.py` — `flight_pressure` driver.**
Add `self._pressure: float = 0.0` and `update_pressure(speed, hull_pct, barge_threat, sector_index, cargo_alarm)` called once per frame from `Game.update()`. *Section 6.1.*

**8.1.3 `audio/audio_manager.py` — tempo-driven drum re-build.**
Currently `_drum_loop` is built once at boot. Pre-build **5 drum loops** at 84/96/108/120/128 BPM and crossfade between them based on `flight_pressure` *at bar boundaries only*. New helper: `_select_drum_tier(pressure)`. Same for bass. *Section 6.1.*

**8.1.4 `audio/audio_manager.py` — 5-stem mix budget enforcer.**
New method `_enforce_stem_budget()` called once per frame. Tracks active stems by priority; ducks lowest-priority below threshold. *Section 2.4.*

**8.1.5 `audio/master_fx.py` — new file.**
Master DSP chain: bit-crush, low-pass, tremolo, slap delay, tape echo, soft clip. Apply post-mix via `pygame.mixer.set_post_mix(...)`. Hull-driven and cargo-driven. *Sections 6.5, 6.7.*

### 8.2 Identity & cohesion

**8.2.1 `audio/synth.py` — chapter-keyed engine drones.**
Refactor `engine_drone(tier)` to `engine_drone(tier, root_freq)`. Game-side: pass the chapter's root frequency. *Section 6.6.*

**8.2.2 `audio/blues_licks.py` — expand pool to 30 patterns, tag moods.**
Add `_LICK_MOODS: list[str]` parallel to `_LICK_PATTERNS`. New public `generate_lick(mood: str | None = None)`. *Section 7.3.*

**8.2.3 `audio/new_wave_pad.py` — chapter-keyed pad.**
Add `mode` argument support for `dorian`, `locrian`, `sus2`. Add `voicing_width: float = 1.0` to allow the pad to "close in" under high pressure. Add chapter root parameter. *Sections 4, 6.1.*

**8.2.4 `audio/voices.py` — `bax_hum.py` (new file).**
8 hummed melodies, 4 bars each, in A minor. Triangle voice + breath noise + slight vibrato. Persistence in `meta.json`: `bax_hums_heard: list[int]`. *Section 7.4.*

### 8.3 Reactive systems

**8.3.1 `audio/synth.py` — `slingshot_stinger()`.**
Reverse-cymbal swell as a pre-baked Sound. Triggered on next bar boundary after `EVT_SLINGSHOT`. *Section 6.3.*

**8.3.2 `audio/audio_manager.py` — pad-key modulation on slingshot.**
Add `_temp_modulation: tuple[float, int] | None = None` — `(semitones_up, bars_remaining)`. Apply by re-pitching the pad channel's `set_volume` and replacing the pad sound with a re-baked version. (Pre-bake all 12 chromatic transpositions at boot.) *Section 6.3.*

**8.3.3 `audio/audio_manager.py` — tether snap musical resolution.**
On `EVT_TETHER_SNAP`: schedule a one-bar bass interruption + pad opening. *Section 6.4.*

**8.3.4 `audio/synth.py` — `barge_motif()` minor-2nd harp drone.**
New looping low-amplitude sound. Plays on `EVT_BARGE_NEARBY`. *Section 6.2.*

### 8.4 Diegetic systems

**8.4.1 `audio/radio_stations.py` — new file.**
4 procedurally-generated 30 s pieces. Each is a function returning a Sound. New scene `SCENE_RADIO`. New input binding **R** in flight to toggle. *Section 7.1.*

**8.4.2 `audio/synth.py` — `decanting_printer()`.**
Receipt printer SFX. Used in the choreographed decanting sequence. *Section 7.5.*

**8.4.3 `audio/audio_manager.py` — `SCENE_DECANTING` choreography.**
Replace the current "slide every 4–5 s" loop with the explicit scripted sequence in Section 7.5. *Section 7.5.*

**8.4.4 `audio/audio_manager.py` — main-menu long-form mode.**
Idle timer in `set_scene(SCENE_MENU)`. After 120 s, swap to `long_form_menu_pad()` (new — 90 s composition). On any keypress, swap back. *Section 7.6.*

### 8.5 Per-chapter inflection

Each chapter ships with a small `audio/chapter_<n>.py` module that registers:
- Home key root frequency.
- Mode (aeolian / dorian / locrian / etc.).
- Kit inflection function (post-processes the drum loop).
- Signature instrument (function returning Sound).
- Cargo damage hook (a `cargo_alarm(state)` callback).

The game's `Game._enter_chapter(n)` calls `audio.load_chapter(n)`. *Section 4.*

### 8.6 Order of operations

Implementation-difficulty notes (no calendar estimates — see CLAUDE.md guidance):

1. **8.1.1 → 8.1.2 → 8.1.3 → 8.1.4 → 8.1.5** (foundations — most changes are additive to `audio_manager.py` and one new file).
2. **8.2.1 → 8.2.2 → 8.2.3** (cohesion — small refactors to existing synth functions, accept new params).
3. **8.3.x** (reactive systems — net-new methods on AudioManager, all event-bus subscribers).
4. **8.4.x** (diegetic systems — net-new modules, low risk to existing flow).
5. **8.5** (chapter inflection — touches `core/game.py` chapter loading; mildly invasive, but well-isolated).
6. **8.2.4** (bax hums — emotional payload, ship last so it lands on a polished bandstand).

Risks: master FX (8.1.5) requires careful CPU profiling — the existing system is comfortable at 60 FPS, but the post-mix DSP chain must not allocate per-buffer. Pre-allocate working arrays. Bit-crush and tape-echo are cheap; tremolo is trivial; slap delay needs a ring buffer.

---

## Section 9 — How we know it's working

If, by Next Fest, the following are true, the soundtrack ships at award-contender quality:

- A muted 15-second clip of any run is identifiable to chapter by a returning player. (Section 4.)
- Players describe the score with at least one of: "lonely," "noir," "blue-collar," "cockpit," "highway." Not: "synthwave," "chiptune," "cinematic." (Section 1.)
- At least one streamer clips: the threat motif arrival, the slingshot key change, the decanting silence, or a Bax hum, *unprompted, with the music as the visible reason for the clip.* (Sections 6.2, 6.3, 7.5, 7.4.)
- The `bax_hums_heard` set is non-empty in >40% of player save files after the Next Fest weekend. (Section 7.4.)
- No two consecutive runs sound identical to a player paying attention. (Sections 6, 7.1.)
- The audio CPU budget stays under 8% of frame time on the reference rig (Steam Deck baseline). (Section 8.6 risk.)

If those are all true, we are not shipping a soundtrack. We are shipping **a cockpit you don't want to leave.**

— end —
