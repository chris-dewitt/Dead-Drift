# DEAD DRIFT — Soundtrack Master Plan (v2)

**Codename:** *HIGHWAY BLUES FROM THE EDGE OF THE HELIOSPHERE*
**Companion to:** `BAX_VOICE.md`, `RECORDING_BRIEF.md`, `README.md`
**Audience:** Dead Drift audio implementation team.
**Approach:** **Hybrid.** Recorded stems form the canvas. The procedural audio system in `audio/` is the interactive layer that performs them in real-time.

> **Read order.** Section 1 = the pitch. Section 1.5 = the four sci-fi film homages that anchor each chapter. Section 2 = the production rules ("the DEAD DRIFT SOUND"). Section 2.5 = the hybrid contract (recorded vs procedural). Sections 3–5 = album structure, per-chapter palette, per-sector dramatic curve. Sections 6–7 = the reactive systems that turn the score from playlist into performance. Section 7.5 = music subtitles & visual indicators (accessibility, first-class). Section 8 = implementation roadmap. Section 9 = falsifiable success metrics.

---

## Locked design decisions (v2 decisions log)

These are the directional answers backing this plan. Don't re-litigate — implement against them.

- **Hybrid approach.** Recorded stems (Chris-sourced or commissioned) form the backbone. The procedural system layers on top: tempo modulation, key modulation, pad swells, arp, threat motif drone, master FX, cargo-degradation effects, mix-bus automation. Graceful degradation: every recorded stem has a procedural fallback already in the codebase so the game stays playable as stems land incrementally. (Section 2.5.)
- **Cohesion-forward, but not genre-locked.** The signature backbone is highway-blues space-noir. Within that backbone, *each chapter explicitly honors a different great sci-fi film score* (Section 1.5). The cockpit is the constant; the films change.
- **Film homages (Ch1–4).** Ch 1 Acoustic Archive → **Blade Runner** (Vangelis). Ch 2 Mycorrhizal Payload → **Solaris** (Artemyev, 1972). Ch 3 Paperwork → **Brazil** (Michael Kamen, 1985). Ch 4 Schrödinger VIP → **2001: A Space Odyssey** (Ligeti). These are not pastiches. They are *nods*: we steal texture, voicing, and concept; we never copy melody.
- **Ch5–6 extensions (shipped Phase H).** Ch 5 The Edge → warm acoustic D Dorian, off-grid intimacy (`audio/chapter_5.py`). Ch 6 Compliance → cold A minor / fluorescent quantised clock (`audio/chapter_6.py`). No fourth-film homage locked — treat as original palette.
- **No vocals, except Bax humming.** Bax hums on every successful delivery (recurring signature, not precious rarity). 12-hum pool, mood-tagged, chosen by run context. Heard hums unlock in a main-menu jukebox. (Section 7.4.)
- **Diegetic-first.** Whenever music can come from a thing in the world — Bax's harmonica, a fuel canister chime, a Repo Barge's tow-warning siren, the cockpit radio — it does. Non-diegetic only for menus, decanting, and run-end stings.
- **The "less is more" pact.** The current procedural soundtrack reads as **jarring and overwhelming.** The v2 default mix sits ~6 dB quieter. Max 4 active stems at any moment (was 5). One full-bar mix-drop per sector minimum — silence is a stem. Every adaptive audio change must be *signposted* via subtitle, HUD line, Bax line, or visual cue. If it can't be signposted, it doesn't ship.
- **Accessibility is first-class.** Diegetic music cues get subtitles (`[harmonica — distant, sour]`) and visual indicators (threat motif → faint amber edge pulse; slingshot stinger → key-change icon on HUD). Per-stem volume sliders (Drums / Bass / Pad / Harp / SFX / Voice). Players running music-off do not lose gameplay-critical information. (Section 7.5.)
- **Tempo is gameplay.** The drum loop's *effective BPM* is driven by `flight_pressure`. 84 BPM clean drift → 124 BPM hot sector-5 pursuit. Tempo changes only on bar boundaries; never mid-bar. (Section 6.1.)
- **One key center per run, modulated per chapter.** A natural minor is the home key. Each chapter transposes (and re-modes — Dorian, Aeolian, Sus2, Locrian) but the modulation logic is shared. (Section 4.)
- **Stems, not tracks.** We never bake a finished 2-minute track. Eight stem categories (kick, snare/clap, hat, bass, pad, arp/lead, harp, guitar). The mixer is the composer. (Section 2.4.)
- **Cockpit radio is keeping.** Four procedurally-seeded stations, R-key toggle, including the deliberately-disgusting major-key propaganda station. This is the awards clip. (Section 7.1.)
- **Cargo-tied audio mechanics are kept, but signposted.** Bit-crush on damaged Acoustic Archive cargo is announced with an amber HUD line `[ ARCHIVE INTEGRITY 60% — SIGNAL LOSS ]` and a Bax line, so players read it as *cause* not as *bug*. Same pattern for the spore stereo-flip, the Paperwork freeze, and the Schrödinger blink. (Sections 4, 7.5.)
- **Tape-hum signature lives.** A single subliminal pink-noise + 60 Hz + tape-wow bed under everything. The glue. (Section 2.6.)
- **North-star metric:** a player who hears 15 seconds of *any* run clip with the visuals blanked can tell you (a) which chapter it is, (b) whether the player is in trouble, and (c) that it's Dead Drift.

---

## Section 1 — Sonic Identity (the pitch)

The award we're chasing is not "Best Soundtrack." The award we're chasing is **"Best Use of Audio,"** because we are not writing songs — we are writing a *cockpit*.

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
| **80s LinnDrum + walking sub-bass** | low end, locked | The job. The clock. The route. The rent. *Under* the cockpit floor. |

Everything else — acoustic guitar, slide, arpeggio, mood pads, cargo-specific instruments — is *garnish* on those three.

### 1.3 The forbidden palette

To stay cohesive — and to stay *uniquely* Dead Drift — these things never appear:

- **Orchestral strings.** No swelling violins. We are not Mass Effect.
- **Chiptune square leads.** We are not pixel-art.
- **Modern EDM drops.** No supersaws, no festival risers, no sidechain pumping. We are 1983, not 2018.
- **Choir "ah" pads.** Too on-the-nose for "space" — except in Chapter 4, where Ligeti's micropolyphonic choirs are *the point*. Chapter 4 has the only exception.
- **Major keys** for more than 8 bars. Even the win-screen is in modal mixolydian, not pure major. We are perpetually in debt; the music never resolves brightly.

### 1.4 The signature moments the score must own

If a streamer clips one of these, the score has to *be* the clip. Each one is implemented in Sections 6–7.

1. **The slingshot release.** Reverse-cymbal swell → pad swell up a perfect fifth → harmonica wail → drum fill → back into the groove one bar later. On-screen indicator: `▲ KEY UP` HUD pip.
2. **The barge proximity dread.** A low, detuned harmonica drone fades in at 320 px. A minor second. *Jaws* relationship, executed on a harp, sounding like a tired union foreman humming the wrong notes. Subtitle: `[harmonica — distant, sour]`.
3. **The tether snap release.** Snare flam, bass walks down a tritone, pad opens. Subtitle: `[bass walks down — release]`.
4. **The clone tank decanting.** Everything stops. One slide-blues note. 4-second silence. The receipt printer. Another slide note, a step lower. **The score is a funeral every time you die.**
5. **The delivery handoff.** Chapter-specific cargo theme finally resolves — *the only place in the entire game the music allows itself to land on the tonic.*

---

## Section 1.5 — The Sci-Fi Soundtrack Pantheon

Each chapter borrows the *texture, voicing, and concept* of a single great sci-fi film score. **We never copy melody.** We never re-orchestrate famous cues. We earn the kinship by understanding what each composer was *doing* — and applying the same logic to our cockpit.

### 1.5.1 Chapter 1 — *Blade Runner* (Vangelis, 1982)

**What we steal:**
- Detuned analog saw pads, washed in long reverb, breathing on a slow LFO.
- A single warm jazz-noir voice (in the film: Dick Morrissey's tenor sax; in us: Bax's harmonica) playing *over* the pad, not against it.
- Tempo-less ambient stretches between the "tracks."
- Vangelis's *texture trick*: every sustained note has a quiet, slow-moving second voice a perfect 5th below.

**What we don't:**
- The "Love Theme" sax melody. Don't quote it. Don't even *imply* it.
- The DX7 bell tone. Too on-the-nose for "Vangelis homage."

**Why this fits Acoustic Archive:** the chapter's cargo is smuggled music. The whole chapter has to feel like a record being played in a smoke-filled apartment. Vangelis *made that record*.

### 1.5.2 Chapter 2 — *Solaris* (Eduard Artemyev / Bach, 1972)

**What we steal:**
- Eerie organic-electronic dread. Bach's *Chorale Prelude in F minor* arranged for analog synth — that exact aesthetic.
- The slow, hovering, *almost-resolving* harmonic motion.
- The *Mirror-of-the-Ocean* trick: layered sustained chords where individual voices fade in and out asynchronously, so you can't tell when the chord changed.
- An organ-like sustained voice (in us: a comb-filtered triangle "bowed-saw" lead — Section 4.2).

**What we don't:**
- The actual Bach melody. Not even a quote.
- The "swooping" tape-modulated whistles. Too gimmicky for our scale.

**Why this fits Mycorrhizal Payload:** Solaris is the film about *consciousness-as-substance*. The cargo here is psychoactive fungal spores that warp the courier's perception. Same problem, same musical answer.

### 1.5.3 Chapter 3 — *Brazil* (Michael Kamen, 1985)

**What we steal:**
- A bureaucratic-comedy *march* feel — the score takes itself absolutely seriously while the world is collapsing in farce.
- Mechanical rhythmic ostinato (in the film: typewriters and machinery; in us: literal typewriter-as-snare).
- A repeated 4-bar melodic figure that *never develops*. The score is on a loop, like the protagonist's life.
- Kamen's *Aquarela do Brasil* trick: an unbearably catchy hook is reduced to fragments and forced through a militaristic filter. It hurts.

**What we don't:**
- The *Aquarela do Brasil* hook itself. Don't quote.
- Lush orchestration. We replace strings with the new-wave pad.

**Why this fits Paperwork:** the cargo is cursed bureaucratic documents. The chapter's mechanic is HUD popups demanding the player file forms. The score has to be the sound of a system that cannot be argued with.

### 1.5.4 Chapter 4 — *2001: A Space Odyssey* (Ligeti, 1968)

**What we steal:**
- Micropolyphonic tone clusters. Specifically the *Atmosphères* and *Requiem (Kyrie)* approach: dozens of voices on slightly different pitches, no rhythm, no melody, no tonal center — just a *cloud* of sustained sound that slowly shifts.
- The terror of *non-resolution*. Ligeti never gives you a chord change. He gives you a chord that slowly *becomes* a different chord without ever changing.
- The use of *silence as an instrument*. The film's most famous music cue is followed by 3 minutes of unaccompanied breathing. We do the same.
- Choir as texture, not as melody. The only chapter that uses voices — but only as wordless cluster tones, never as a "song."

**What we don't:**
- *Also Sprach Zarathustra*. Obviously. Don't even joke.
- The Strauss waltzes. We are not airy.
- Any kind of recognizable melody.

**Why this fits Schrödinger VIP:** Ligeti's micropolyphony is *literally the sound of quantum superposition* — a sustained state of being-multiple-things-at-once. Chapter 4 is about a passenger whose state collapses on observation. There is no closer musical analog in film history.

---

## Section 2 — The DEAD DRIFT SOUND (production rules)

Every stem (recorded or procedural) must obey these or it doesn't ship. This is the cohesion contract.

### 2.1 Key center & modal palette

- **Home key:** A natural minor (A, B, C, D, E, F, G).
- **Approved modes per chapter:** Ch1 Aeolian, Ch2 Dorian (the chapter wants a *flicker* of hope), Ch3 Sus2/Suspended (never resolves), Ch4 Aeolian with Ligeti-style chromatic clusters (functionally atonal in spots).
- **Approved tensions:** ♭7 (always), ♭6 (mood pads), 9 (arpeggio top voice), ♯4 (slingshot moments only — one bar, then resolve). **No major 7.**
- **Forbidden:** Lydian, Phrygian (Ch4 gets closest), pure major (except mixolydian for delivery success), blues ♭5 as a chord tone (only as a passing tone in licks).

### 2.2 Tuning & detuning

- All synth voices detuned ±4–9 cents in stacks of 2–3. *Never* in-tune. The cockpit is broken; the synths are broken.
- Recorded harmonica is **deliberately a hair flat** (–6 cents) against the synths. Bax has been gigging too long.
- Acoustic guitar is **slightly sharp** (+3 cents). It's the one optimistic voice in the room. It loses every argument.

### 2.3 Rhythm contract

- **Drum machine BPM range:** 78–128. Default 96.
- **Drum kit identity:** LinnDrum-style gated snare + tight kick + closed hat. No toms. Clap doubles snare only at high pressure.
- **Bass:** always walking (eighth notes at high pressure, quarters at mid, halves at low). Always plays root–♭7–5–root or root–5–♭7–octave. *Never syncopated.* The bass is the union, and the union shows up on time.
- **The "1" is always strong.** Players tapping their foot is a success metric.

### 2.4 Mix contract (the 4-stem rule)

At any frame, **no more than 4 stems** may be audible above –24 dBFS. The mixer enforces this with a stem-priority list:

1. Engine drone (always on, but stems-budget-exempt — it's the cockpit, not the music)
2. The currently-active *rhythm bed* (drums + bass, counted as one stem)
3. Pad **or** arp — never both at full
4. **One voice** — harmonica, guitar, slide, or vocal hum

When a 5th wants in, the lowest-priority current stem ducks 6 dB until the new voice finishes. The result: **the mix breathes.** This is the single biggest change from v1: we are taking content *out*, not putting more in.

### 2.5 Loop contract

- Every loop is **2 or 4 bars** at base tempo. Never odd lengths. Never 8 bars.
- Every loop must crossfade at the loop boundary (existing `new_wave_pad.build_new_wave_pad` already does this — port the pattern everywhere).
- Every loop must have a **silent variant** baked at the same length, so the mixer can drop to silence on the bar line without choking mid-phrase.
- **"Silence is a stem":** each sector must include at least one bar of full mix drop (everything except engine + tape hum). The mixer schedules these on the bar line, semi-randomized so they don't feel mechanical.

### 2.6 The tape-hum signature

A single, almost-subliminal layer under *everything* in the game: pink noise filtered to ~80 Hz–4 kHz at –32 dBFS, with a 60 Hz hum at –38 dBFS and a faint 7.5 ips tape-wow modulation. Plays in every scene — menu, flight, terminal, decanting. Players will not consciously hear it. They will hear its *absence* if you mute it. **This is what makes a soundtrack feel like a soundtrack and not a stack of sounds.**

---

## Section 2.5 — The Hybrid Contract

This is the most consequential v2 change. The procedural-only constraint is dropped. Recorded stems form the canvas; the procedural system in `audio/` performs them.

### 2.5.1 What gets recorded

These are the stems Chris sources (recorded by Chris, commissioned, or hired session musicians). Specifications and shot list in `docs/RECORDING_BRIEF.md`.

| Stem category | Why recorded, not procedural |
|---|---|
| **Harmonica licks** (30+ phrases) | Procedural harmonica reads as MIDI. Real harp breath, reed buzz, bend nuance — irreplaceable. |
| **Acoustic guitar phrases** (12+ fingerpicked arpeggios) | Karplus-Strong synthesis is competent but unmistakably synthetic. Real nylon-string with mic'd body resonance is the only way. |
| **Electric slide guitar one-shots** (12+ mournful sustains) | Slide tone *is* the chapter-2 Solaris voice. Has to be real. |
| **Bax hums** (12 wordless melodies, 4 bars each) | The emotional payload. Must be a real human voice. Cockney inflection — Chris or a voice talent. |
| **Drum hits** (kick, snare, gated-snare, clap, closed-hat, open-hat) | LinnDrum samples or modern LinnDrum-style one-shots. Single-hits, not loops — the mixer assembles loops. |
| **Walking sub-bass notes** (chromatic octave) | Recorded electric bass through a tube amp, one note per pitch. The mixer plays the walking line. |
| **Cockpit Foley** (knob clicks, leather creak, breath) | Cockpit room tone for the radio scene tuning sweep. Light pass. |

### 2.5.2 What stays procedural

These remain in `audio/synth.py` and friends. They are the *reactive* layer — they need to respond to game state in real-time, which recorded stems can't do.

| Stem | Why procedural |
|---|---|
| **Engine drones (5 tiers)** | Driven by ship speed. Must crossfade continuously and re-tune per chapter (Section 6.6). |
| **Detuned-saw pads (per chapter)** | Driven by `flight_pressure` for voicing width, by chapter key for transposition. |
| **Arpeggio top voice** | Locked to current chord progression, drops out under pressure. |
| **Threat motif drone** | Pitch-modulated by barge distance. Must be live. |
| **Tape hum bed** | Continuous, multi-layer, always running. |
| **Cockpit radio stations** | Procedural by design — different seeded composition every run. |
| **Master FX** (bit-crush, low-pass, tremolo, tape echo) | Apply to the mix output, can't be pre-baked. |
| **Cargo-degradation effects** | React to live cargo state. |
| **Sector pads & ambient beds** | Crossfaded by sector progression. |
| **One-shot SFX** (gun, hull, clang, snap, beep, canister) | Tightly coupled to events; pre-baked but synthesized for size + variety. |

### 2.5.3 Stem format & ingestion

- **Format:** 44.1 kHz, 24-bit WAV, mono unless stereo is essential (room mics on guitar; otherwise mono).
- **Source key:** A natural minor unless the stem is single-pitched (drum hits, single bass notes). Pitch-shifted to other chapter keys at boot via a 12-step chromatic pre-shift pass.
- **Source BPM (for tempo-locked stems):** 96 BPM. Time-stretched to 5 tempo tiers (84/96/108/120/128) at boot via a phase-vocoder pass. Cached in memory.
- **Length:** stems of equal length get loop-mixed; one-shots are one-shots.
- **Loudness:** every stem normalized to –14 LUFS reference before ingestion. The mixer applies dynamic gain per stem from there.
- **File layout:**
  ```
  assets/audio/stems/
    harmonica/      lick_01.wav … lick_30.wav
    guitar/         phrase_01.wav … phrase_12.wav
    slide/          note_01.wav … note_12.wav
    bax_hums/       hum_01.wav … hum_12.wav
    drums/          kick.wav  snare_gated.wav  clap.wav  hat_closed.wav  hat_open.wav
    bass/           bass_a1.wav … bass_g3.wav   (chromatic)
    foley/          knob_click.wav  leather.wav  breath.wav
  ```

### 2.5.4 Graceful degradation (the critical rule)

**Every recorded stem has a procedural fallback already in the codebase.** `audio/stem_loader.py` (new file, Section 8) implements:

1. Try to load `assets/audio/stems/<category>/<name>.wav`.
2. If present, ingest (resample, pitch-shift, tempo-stretch, cache).
3. If missing, fall back to the equivalent procedural function (`blues_licks.generate_lick(...)`, `guitar_phrases._fingerpicked_arpeggio(...)`, etc.).
4. Log which source served each stem on boot (`[audio] harmonica/lick_03: RECORDED`, `[audio] bax_hums/hum_07: PROCEDURAL FALLBACK`).

The game ships and plays through the whole campaign with zero recorded stems. Every stem Chris drops in is an immediate audible upgrade. **No "all-or-nothing" recording session pressure. No content-completeness blocker.**

### 2.5.5 The pre-shift / pre-stretch cache

Pitch-shifting a 30-stem harmonica library to 12 chromatic transpositions = 360 in-memory variants. Tempo-stretching to 5 tiers = 1800. That's ~50 MB at 24-bit, easily affordable but worth budgeting:

- Pre-shift *only* the keys we actually use per chapter (max 4 of the 12 chromatics).
- Pre-stretch *only* the rhythm-bed stems (drums, bass) — single-shot voices (harp, slide) are pitch-shifted live during playback (cheap).
- Total ingestion target: **<200 MB RAM, <8s boot time** on the Steam Deck baseline.

---

## Section 3 — Album Structure (the campaign as a record)

A 4-chapter campaign is a 4-side double album. The track listing the player experiences across a clean campaign:

### Side A — *Acoustic Archive* (Blade Runner homage)
1. **Cold Boot** *(menu)* — slide-blues notes over the tape-hum bed. No drums.
2. **Decant & Sign** *(loadout draft)* — pad + arp, no drums, very dry.
3. **Highway One** *(sectors 1–2)* — full bandstand. The signature.
4. **Roadside Confession** *(terminal encounter, sector 2)* — drums drop out. Pad alone + sparse harp.
5. **The Long Inhale** *(sectors 3–4)* — drums return, bass walks darker.
6. **Last Mile Before the Tunnel** *(sector 5)* — pressure peaks. Threat motif on harp.
7. **Smuggler's Welcome** *(delivery corridor)* — chapter cargo theme. Vinyl-warm, bass-heavy, harp solos. Per-chapter corridor palettes in `delivery/corridor/chapter*.py`.
8. **Sign Here, Please** *(delivery success)* — mixolydian for 12 s. **Bax hums.** Back to silence.

### Side B — *The Mycorrhizal Payload* (Solaris homage)
Same template. Modulated up a minor third (C minor). Bowed-saw lead replaces the sparse arp. Bach-via-synth chorale fragments in the pad voicing.

### Side C — *The Paperwork* (Brazil homage)
Same template. F♯ minor (tritone from Ch2 — most cursed key gets it). Typewriter snare. Quantize-locked, no swing. The 4-bar figure never develops.

### Side D — *The Schrödinger VIP* (2001 homage)
Same template. E natural minor with Ligeti-style chromatic chord clusters. **Bass and drums largely absent.** The longest silences in the game live here.

### Hidden side — *Decanting* (death)
- One slide-blues note, one printer, one breath, repeat. **The score 99% of players hear most.** Most haunting thing in the game.

---

## Section 4 — Per-Chapter Sonic Identity

Each chapter modulates the home key, adopts its film-homage texture, adds a *signature instrument*, and inflects the drum kit. The bandstand stays the same; the band's *attitude* changes.

### 4.1 Chapter 1 — Acoustic Archive *(Blade Runner)*
- **Home key:** A natural minor.
- **Mode:** Aeolian.
- **Signature instrument:** Distorted electric harmonica through a tube amp (same recorded harp stem, run through the procedural soft-clip saturator at +3 dB drive).
- **Kit inflection:** Snare gets +20% reverb. Hat slightly behind the beat (swing 54%).
- **Pad voicing:** Minor 7th, lush. Vangelis-detuned saws.
- **Cargo theme motif:** Descending A–G–E–D over bass walking up. Pulling-against-gravity feeling. Lives in delivery corridor only.
- **Cargo-tied mechanic (signposted):** When `AcousticArchive` cargo takes damage, the **entire mix is bit-crushed** progressively (4 → 8 → 12-bit). Signposted by:
  - HUD line in amber: `[ ARCHIVE INTEGRITY 60% — SIGNAL LOSS ]`
  - Bax line: *"Oi, the bangers are skippin'. Hold it steady."*
  - Subtitle: `[score quality — degrading]`
  - This is the chapter's signature trick *and* it reads as cause, not as a bug.

### 4.2 Chapter 2 — The Mycorrhizal Payload *(Solaris)*
- **Home key:** C natural minor (up a minor third).
- **Mode:** Dorian. The relative brightness makes inversions sound *wrong* against the bent slide, which is the point.
- **Signature instrument:** Recorded electric slide guitar — long, wet sustains, comb-filtered. The Artemyev-organ sound.
- **Kit inflection:** Snare swapped for a *rim shot + tape echo* that mistimes by 30–60 ms randomly. The drummer is high.
- **Pad voicing:** Layered sustained chords where individual voices fade in/out asynchronously (the *Mirror-of-the-Ocean* trick).
- **Cargo theme motif:** Two phrases that *almost* repeat but never line up — a canon with one voice 7 beats behind.
- **Cargo-tied mechanic (signposted):** When the spore mechanic inverts controls, the **stereo field inverts too** for the 4 s window. Signposted by:
  - HUD line: `[ SPATIAL INVERSION — 4S ]`
  - Bax line: *"Either I've inhaled somethin' or space is sideways now."*
  - Subtitle: `[stereo inverted]`
  - Visual indicator: brief L↔R arrow flash on the cockpit strip.

### 4.3 Chapter 3 — The Paperwork *(Brazil)*
- **Home key:** F♯ natural minor.
- **Mode:** Suspended seconds (sus2). Never resolves. Like a form that won't process.
- **Signature instrument:** Mechanical typewriter rhythm overlay. Pitched at kick frequency, dead center, plays the current drum pattern but as typewriter clacks. The drummer *is* a typewriter.
- **Kit inflection:** Snare replaced by a manila-folder slap. Hi-hat replaced by a stapler. Dead-straight — no swing, no human feel. *The bureaucracy is on the beat.*
- **Pad voicing:** Sus2 stacks. Brazil-style oppressive-march texture.
- **Cargo theme motif:** Eighth-note ostinato on E, repeating 47 bars before any chord change. The DMV line, scored.
- **Cargo-tied mechanic (signposted):** Every `TriplicateForm` popup **freezes the music on a single sustained chord** until the player files. Signposted by:
  - HUD line: `[ FORM 27-B SUBSECTION 9 — AWAITING SIGNATURE ]`
  - Bax line: *"By order of the bloody Union, mate."*
  - Subtitle: `[score paused — paperwork pending]`

### 4.4 Chapter 4 — The Schrödinger VIP *(2001 / Ligeti)*
- **Home key:** E natural minor with Ligeti-style chromatic clusters.
- **Mode:** Aeolian as anchor; chord clusters that *function* atonally over the top.
- **Signature instrument:** **Silence**, and a wordless choral cluster (procedural — additive sine stack of 12 voices, each detuned in a quarter-tone grid around an E centroid). The only chapter that uses voice-as-pad.
- **Kit inflection:** Half-time feel. Brushes instead of sticks. Every 4th measure the kick *doesn't* hit.
- **Pad voicing:** Micropolyphonic clusters. The chord *becomes* a different chord without ever changing.
- **Cargo theme motif:** A two-note interval — minor second — looping in the upper register. The wave-function collapse motif.
- **Cargo-tied mechanic (signposted):** When the VIP is observed alive → single warm pad chord ~1 s. Observed dead → complete mix silence ~1 s. The mix *blinks*. Signposted by:
  - HUD readout (top-right of VIP cargo widget): `[ STATE: ALIVE ]` or `[ STATE: ¿? ]`
  - Bax line on each collapse: *"Don't open the box… ah, you opened it."*
  - Subtitle: `[Ligeti choir — alive]` / `[silence — collapsed]`

### 4.5 Risk note on Ch4

Locrian-style clusters are easy to get wrong — they can sound like a bug. Mitigation: every Ch4 cluster is **anchored to a sustained E in the sub-bass**, so the listener always has a tonal floor even when the upper register is functionally atonal. If playtest reads it as broken, the fallback is natural-minor-with-chromatic-passing-tones (still Ligeti-adjacent, less unstable). The fallback is wired into the chapter loader from day one.

### 4.6 Chapter 5 — The Edge *(shipped)*
- **Home key:** D Dorian.
- **Signature instrument:** Acoustic guitar + soft harmonica — the quiet chapter.
- **Implementation:** `audio/chapter_5.py`; dock receiver voice **Fitz** (warm, off-grid grit).

### 4.7 Chapter 6 — Compliance *(shipped)*
- **Home key:** A natural minor / B Phrygian inflections.
- **Signature instrument:** Fluorescent compliance chime + quantised clock kit — clinical, no swing.
- **Implementation:** `audio/chapter_6.py`; dock receiver voice **Bowen** (smooth, institutional).

---

## Open work (soundtrack v2 audit)

Baseline mix trim landed (`_music_target_vol` 0.34 → 0.27 in `audio/audio_manager.py`). Still pending Chris play-verify:

1. **Max-4-active-stems guard** — enforce Section 2.4 in code
2. **Accessibility UI** — music subtitles, per-stem volume sliders, master mute (Section 7.5)
3. **Audible play-pass** — confirm quieter default reads as intentional, not broken

---

## Section 5 — Per-Sector Dramatic Curve

Within a single chapter run, the 5 sectors form a dramatic arc. The score implements that arc through layer activation, not new compositions.

| Sector | Mood label | Tempo | Active stems | Threat motif | Notes |
|---|---|---|---|---|---|
| **1** | *Pull out of port* | 84 BPM | drums (soft), bass, pad | off | Player is settling in. Harp every 10–14 s. The score is warm. |
| **2** | *Open road* | 96 BPM | drums, bass, pad, harp | off | Signature bandstand. Guitar phrase every 8–16 s. |
| **3** | *First trouble* | 102 BPM | drums (gated harder), bass, pad (narrower voicing), harp | **on** at proximity | Threat motif pre-arms — heard once at sector entry before any barge spawns. |
| **4** | *Run* | 112 BPM | drums (full intensity), bass (walking ♭7s), pad (low only) | active | Arpeggio drops. The high register is gone. **Score has lost its top voice.** |
| **5** | *Final mile* | 124 BPM | drums (clap doubled), bass, pad (octave drop), harp (distressed wail) | constant low drone | Slingshot bonuses pay *double* musically — full reverse-cymbal swell + key change up a whole step for 8 bars. |

After sector 5: tempo snaps back to 96 for the delivery corridor (chapter-specific theme takes over). The snap is part of the reward — the player's nervous system comes down.

---

## Section 6 — Adaptive / Interactive Systems

This is where Dead Drift's audio stops being a soundtrack and starts being an instrument.

### 6.1 `flight_pressure` — the central driver

A 0..1 scalar, updated every frame in `AudioManager.update()`. Drives tempo, kit intensity, bass density, pad voicing.

```
flight_pressure = clamp01(
    0.20 * normalize(speed, 0, MAX_VELOCITY)
  + 0.30 * (1.0 - hull_pct)
  + 0.25 * barge_threat            # 0 if no barge in range, 1.0 at tether-active
  + 0.10 * sector_index / SECTORS_PER_RUN
  + 0.15 * cargo_alarm             # chapter-specific 0..1
)
```

> **Weights are first-pass.** These are educated guesses, not playtest data. They will be tuned. Source of truth: `config/audio_tuning.py` (new file in 8.1) so designers can iterate without touching the mixer.

Mappings:
- **Drum BPM:** `lerp(84, 124, flight_pressure)` — re-pitched at bar boundaries only. **Tempo never changes mid-bar.**
- **Kit intensity:** `lerp(0.6, 1.0, flight_pressure)`. Snare clap doubles above 0.75.
- **Bass density:** `< 0.4` → half notes; `0.4–0.75` → quarters; `> 0.75` → eighths.
- **Pad voicing width:** `< 0.5` → 4-voice spread; `≥ 0.5` → root + ♭7 only (pad *closes in* on the player).
- **Arp gate:** `> 0.7` → arp drops out.
- **Harp tension:** `> 0.6` → harp pitch-bends downward 20 cents over its phrase. Bax is *strained*.

### 6.2 Threat motif (auto-cued, signposted)

A two-note motif in the synth engine as `barge_motif()`. Minor second on the harp at –9 cents.

- Plays *once* the first time a barge enters 600 px in any sector ("you see it before you hear it close"). Subtitle: `[harmonica — distant, sour]`. Visual: faint amber edge pulse for 0.4 s.
- Plays *as a drone* (looping low octave at –24 dBFS) whenever a barge is within 320 px (existing `EVT_BARGE_NEARBY`). Subtitle: `[harmonica drone — close]`.
- **Resolves up to the minor 3rd** the moment the barge is destroyed or out of range for >3 s. Subtitle: `[motif resolves — clear]`. Visual: amber edge pulse releases.

### 6.3 Slingshot stinger (signposted)

Already partially in the system as `slingshot_whoosh`. Expand to a *musical* event:
- Trigger on `EVT_SLINGSHOT`.
- On next bar boundary: pitch the pad up a perfect fifth for 4 bars.
- One harmonica lick on top (high-register `cocky` mood pool).
- Reverse-cymbal swell on the *previous* bar (pre-roll).
- Return to base key at bar 5.
- **Signposted:** HUD pip `▲ KEY UP` for the 4-bar window. Subtitle: `[pad swells — key up]`.

### 6.4 Tether snap musical resolution (signposted)

- Trigger on `EVT_TETHER_SNAP`.
- On next sub-beat: snare flam (existing kit, two hits 30 ms apart).
- Bass walks down a tritone over the next 2 beats.
- Pad opens to a full 5-voice spread for 2 bars.
- Returns to normal at bar 3.
- **Signposted:** HUD pip `▼ RELEASE`. Subtitle: `[bass walks down — release]`.

### 6.5 Hull-state mix degradation (signposted)

Single hull-driven master DSP chain.

| Hull % | DSP effect | Signpost |
|---|---|---|
| 100–60% | Clean. Tape hum only. | — |
| 60–30% | Bit-crush 10 bits. Drums +2 dB transient boost. | HUD: `[ COCKPIT SPEAKER — DEGRADED ]`. Bax: *"Speaker's gone tinny."* |
| 30–0% | Bit-crush 6 bits + low-pass 2 kHz + 3.5 Hz tremolo. Harp drops out. | HUD: `[ COCKPIT SPEAKER — FAILING ]`. Bax: *"Can hardly hear meself think."* |

`MasterFX.process(stereo)` runs on the mixed output once per buffer. Skippable in `--no-fx` debug mode.

### 6.6 Engine drone as harmonic content

Currently 5-tier SFX. **Promote to a music stem.** Each tier tuned to a chord tone in the current key:

| Tier | Speed | Frequency (Ch1) | Role in A minor |
|---|---|---|---|
| 0 | drift | 55 Hz | root (A) |
| 1 | cruise | 65.4 Hz | ♭3 (C) |
| 2 | thrust | 73.4 Hz | 4 (D) |
| 3 | fast | 82.4 Hz | 5 (E) |
| 4 | redline | 98 Hz | ♭7 (G) |

Player accelerates → engine *plays the scale*. Full-throttle ship = dominant chord. Drifting ship = tonic. **The player is the bassist.** When the chapter modulates key, the engine tier roots transpose with it.

### 6.7 Per-sector cargo audio degradation

`cargo_degradation: float` (0..1) on the AudioManager. Applied at master, gated by chapter:
- 0.0 → clean.
- 0.5 → 10-bit crush + 200 ms slap delay at 18% wet.
- 1.0 → 6-bit crush + 600 ms tape-echo at 32% wet + 80 Hz hum bumped to –22 dBFS.

Only Ch1 (Acoustic Archive) uses this fully. Always signposted per Section 4.

---

## Section 7 — Diegetic & Hidden Systems (the "awards" stuff)

The unique hooks. This is what jurors and streamers screenshot.

### 7.1 The cockpit radio

Fifth audio scene: **`SCENE_RADIO`** — toggled mid-flight with **R**. When active:
- The bandstand ducks 12 dB.
- 4-second "tuning" sweep (white noise filtered 200 Hz → 8 kHz).
- A station plays — procedurally seeded per run from one of:

| Station | Style | Signpost |
|---|---|---|
| **Pirate blues** | Harmonica + guitar duet, no drums. Sounds *better* than the score, in a way that makes the silence after worse. | Subtitle banner: `[radio: PIRATE BLUES 88.7 — unlicensed]` |
| **State propaganda** | Spoken-word voice blip stream over a major-key pad. *The only place in the game that uses pure major.* Disgusting on purpose. | Subtitle banner: `[radio: COMPLIANCE CHANNEL ONE — state]`. Bax: *"Off. Off. Turn it off."* |
| **Union solidarity broadcast** | Drum + bass only, no melody. A workers' march. Repo barge proximity instantly cuts it off. | Subtitle banner: `[radio: LOCAL 404 NIGHTSIDE — union]`. Auto-cuts on barge proximity. |
| **Dead air** | Static + a heartbeat. Subliminal kick at 56 BPM. >60 s linger → Bax line. | Subtitle banner: `[radio: dead air]` |

The radio is a *toy*. It rewards exploration. Streamers will clip the propaganda station for free marketing.

### 7.2 Antagonist signatures

Each major antagonist class gets a sonic ID at spawn. The score *plays* the enemy before drawing it.

| Antagonist | Signature | Trigger |
|---|---|---|
| Repo Barge (standard) | Two-note minor 2nd on detuned harp | Within 600 px (one-shot) + within 320 px (drone) |
| Repo Barge (TORCH state) | Add a *slow clap* on the off-beat | TORCH state entered |
| Union Dispatcher (terminal NPC) | Tritone sub on the pad on terminal open | EVT_TERMINAL_OPEN with dispatcher |
| Insurance Adjuster (terminal NPC) | A single 880 Hz sine — perfectly in tune, the *only* in-tune thing in the game | EVT_TERMINAL_OPEN with adjuster |
| Schrödinger VIP (cargo) | Silence + a single high E5 every 40 s | While cargo onboard |
| Clone tank (death) | Slide-blues note + receipt printer | EVT_SHIP_DESTROYED |

### 7.3 Bax-driven musical reactions

The harp lick pool expands to **30 recorded patterns** (Section 8 + RECORDING_BRIEF). Each tagged with a mood: `cocky`, `weary`, `panic`, `delighted`, `lonely`, `sarcastic`. When Bax speaks, the *next* lick is filtered by the mood of his line. The harp becomes the continuation of his voice.

| Event | Next-lick mood |
|---|---|
| Slingshot achieved | `delighted` |
| Tether snap | `cocky` |
| Hull critical | `panic` |
| Idle (>25 s no speech) | `lonely` or `weary` |
| Module unbolted | `weary` |
| Fuel canister grabbed | `cocky` |
| Barge nearby | `sarcastic` |

### 7.4 The Bax Hum (recurring signature) ★

**Bax hums on every successful delivery.** Not once per campaign — every time.

- **12-hum pool**, each 4 bars, wordless melody in A natural minor (transposed to chapter key at playback).
- **Mood-tagged**, chosen by run context:
  - *Triumphant* hums for clean runs (hull > 80%, no tether hits in last sector).
  - *Weary* hums for survival runs (hull < 30% on delivery).
  - *Wry* hums for runs with >2 deaths in the same chapter.
  - *Tender* hums for first-time chapter completions.
- **Played over the delivery success screen** (12 s window). Pad drops to support; everything else stops.
- **Signposted:** subtitle bottom of screen: `[Bax hums — 'Lonesome Beacon' (4/12)]` — gives the hum a *title* (each of the 12 has one) and the player's progress through the set.
- **Jukebox unlock:** main-menu screen "BAX'S RECORDS" lists all 12. Heard ones playable. Unheard ones show: `???`. *Achievement: hear all 12.*

The 12 hums and their titles:
1. *Cold Boot Lullaby* — triumphant
2. *Lonesome Beacon* — tender
3. *The Foreman's Lament* — weary
4. *Crooked Antenna Waltz* — wry
5. *Two Stops to Tomorrow* — triumphant
6. *Sign Here, Press Hard* — wry
7. *Tank Number Eleven* — weary
8. *Half-Tank Hymn* — tender
9. *Pinned by Gravity* — weary
10. *Highway Blues for a Dead Quarter* — triumphant
11. *The Last Honest Foreman* — tender
12. *Closing Time at the Heliosphere* — wry

This is the emotional payload. This is the moment a player goes "oh." This is the clip that goes on Twitter.

### 7.5 Decanting silence

Make this the most musically composed moment in the game.

- One slide-blues note, 1.6 s. Subtitle: `[slide guitar — a single note]`.
- 3 s of silence except tape hum.
- Receipt printer SFX (new `decanting_printer()` in `synth.py`). Subtitle: `[printer ticks]`.
- 4 s of silence.
- One slide-blues note, a whole step *lower*. Subtitle: `[slide guitar — lower]`.
- Hold until ENTER.

**The silence is the music.** Don't crowd it.

### 7.6 Main-menu listening room

Idle at the main menu >2 minutes → visual fades to a slow-rotating starfield, audio enters **long-form mode**: pad extends to 90-second composition (Am–F–G–Em–Dm–G–C–E7, then home), with a single harmonica solo over the back half. No drums, no bass. Just void and harp.

Free 90-second soundtrack sample for anyone walking past the Next Fest booth with the game idling.

---

## Section 7.5 — Music Subtitles & Visual Indicators (Accessibility, First-Class)

Every diegetic music cue and every adaptive audio change has a subtitle and (where appropriate) a visual indicator. Players with audio off do not lose information.

### 7.5.1 The subtitle channel

- New event: `EVT_MUSIC_SUBTITLE(text: str, duration_s: float, color: str = "amber")`.
- New renderer: `renderer/music_subtitle_renderer.py`. Renders bottom of screen, *distinct from* Bax cockpit speech:
  - Bax speech: typewriter, white-amber, mixed case, in the cockpit strip.
  - Music subtitles: instant-display, bracketed, dim amber-grey, *italic*, mid-screen lower-third.
  - Visual differentiation matters — players must learn the two channels at a glance.
- Toggleable in settings (`music_subtitles: bool = True`). Off by default for streamers' clean-shot mode? **No — on by default.** Accessibility is the default.

### 7.5.2 Subtitle catalog (canonical)

| Cue | Subtitle text |
|---|---|
| Threat motif arrival (one-shot) | `[harmonica — distant, sour]` |
| Threat motif drone (sustained) | `[harmonica drone — close]` |
| Threat motif resolves | `[motif resolves — clear]` |
| Slingshot stinger | `[pad swells — key up]` |
| Tether snap release | `[bass walks down — release]` |
| Hull 60–30% | `[cockpit speaker — degraded]` |
| Hull <30% | `[cockpit speaker — failing]` |
| Cargo degradation (Ch1) | `[score quality — degrading]` |
| Spore stereo invert (Ch2) | `[stereo inverted]` |
| Paperwork freeze (Ch3) | `[score paused — paperwork pending]` |
| Schrödinger collapse alive (Ch4) | `[Ligeti choir — alive]` |
| Schrödinger collapse dead (Ch4) | `[silence — collapsed]` |
| Bax hum (delivery success) | `[Bax hums — '<title>' (n/12)]` |
| Cockpit radio station | `[radio: <STATION NAME> — <category>]` |
| Decanting slide (high) | `[slide guitar — a single note]` |
| Decanting printer | `[printer ticks]` |
| Decanting slide (low) | `[slide guitar — lower]` |
| Main-menu listening room enters | `[long-form mode]` |

### 7.5.3 Visual indicators (HUD)

Three new persistent HUD elements (small, never obtrusive):

| Indicator | Position | Triggered by |
|---|---|---|
| **▲ KEY UP** pip | Top-center, 4-bar duration | Slingshot stinger |
| **▼ RELEASE** pip | Top-center, 2-bar duration | Tether snap |
| **Threat-motif amber pulse** | Screen-edge vignette, 0.4 s, low alpha | Barge motif fires |
| **`[ COCKPIT SPEAKER — n ]`** readout | Existing HUD widgets | Hull state changes |
| **`[ ARCHIVE INTEGRITY n% ]`** widget | Cargo HUD slot | Acoustic Archive damage |

### 7.5.4 Per-stem volume sliders

Settings menu, **6 independent sliders**:

1. **Drums** (kick / snare / hat / clap, grouped)
2. **Bass**
3. **Pad / Arp**
4. **Harmonica & Guitar** (the "voice" stems)
5. **SFX** (gun, hull, clang, snap, beep, canister, etc.)
6. **Bax Voice** (cockpit speech blips + hum)

Each slider 0–100%, separate from master. A player who hates the drum machine can solo it out without losing the score. A player playing late at night can keep the harp and pad and kill the drums. **This is the maturity move.**

### 7.5.5 Optional "quiet mode" preset

Single toggle in settings: **Quiet Mode**. When on:
- All stem volumes capped at 60%.
- Tape hum muted.
- Master FX disabled (no bit-crush, no tremolo).
- Threat motif uses the visual indicator only (no audio).

For players who want to play with podcasts on, or in shared spaces, or who just don't want score-mood-driven gameplay.

---

## Section 8 — Implementation Roadmap (mapped to code)

All work lives under `audio/` and `renderer/`. Existing files referenced; new files noted. No content removed without replacement.

### 8.0 Foundation: stem ingestion (must land first)

**8.0.1 `audio/stem_loader.py` — new file.**
- `load_stem(category: str, name: str) -> Sound` with WAV-first / procedural-fallback logic (Section 2.5.4).
- Pre-shift and pre-stretch caches.
- Boot-time log: each stem reports `RECORDED` or `PROCEDURAL FALLBACK`.

**8.0.2 `assets/audio/stems/` directory layout.**
- Create empty subdirs with `.gitkeep` so the structure ships on day one (Section 2.5.3).

**8.0.3 `audio/pitch_shift.py` — new file.**
- Phase-vocoder pitch-shift (numpy + scipy).
- Chromatic pre-shift cache up to 4 keys per stem (chapter-keyed).

**8.0.4 `audio/time_stretch.py` — new file.**
- Phase-vocoder time-stretch.
- Pre-stretch to 5 tempo tiers for rhythm-bed stems.

### 8.1 Foundations: reactive layer

**8.1.1 `config/audio_tuning.py` — new file.**
- All weights for `flight_pressure`, tempo curves, intensity curves, mood threshold tuning. Single source of truth for designer iteration (no mixer code changes required for tuning).

**8.1.2 `audio/synth.py` — tape-hum bed.**
- New `tape_hum_bed(duration=8.0)`. New channel `_HUM_CH`. Loops at –32 dBFS in every scene. (Section 2.6.)

**8.1.3 `audio/audio_manager.py` — `flight_pressure` driver.**
- `self._pressure: float`, `update_pressure(...)` called once per frame from `Game.update()`. (Section 6.1.)

**8.1.4 `audio/audio_manager.py` — tempo-driven rhythm bed.**
- Pre-build 5 drum loops at 84/96/108/120/128 BPM and crossfade at bar boundaries.
- Same for bass.
- New helper: `_select_tempo_tier(pressure)`.

**8.1.5 `audio/audio_manager.py` — 4-stem mix budget enforcer.**
- `_enforce_stem_budget()` per frame. Tracks active stems by priority; ducks lowest below threshold. (Section 2.4.)

**8.1.6 `audio/master_fx.py` — new file.**
- Master DSP chain: bit-crush, low-pass, tremolo, slap delay, tape echo, soft clip.
- Hooked via `pygame.mixer.set_post_mix(...)`.
- Hull-driven and cargo-driven (Sections 6.5, 6.7).
- Pre-allocate working arrays (no per-buffer allocation).

### 8.2 Identity & cohesion

**8.2.1 `audio/synth.py` — chapter-keyed engine drones.**
- `engine_drone(tier)` → `engine_drone(tier, root_freq)`. (Section 6.6.)

**8.2.2 `audio/blues_licks.py` — expand to 30 patterns, tag moods.**
- `_LICK_MOODS: list[str]` parallel to `_LICK_PATTERNS`.
- New `generate_lick(mood: str | None = None)`.
- Recorded versions per RECORDING_BRIEF, procedural fallback persists. (Section 7.3.)

**8.2.3 `audio/new_wave_pad.py` — chapter-keyed pad.**
- `mode` argument supports `dorian`, `locrian`, `sus2`, `aeolian`.
- `voicing_width: float = 1.0` for pressure-driven closing.
- Chapter root parameter. (Sections 4, 6.1.)

**8.2.4 `audio/bax_hum.py` — new file.**
- 12 hummed melody specs. Recorded preferred (RECORDING_BRIEF.md); procedural fallback (triangle voice + breath noise + slight vibrato).
- `play_hum(context: RunContext) -> str` returns the hum title for subtitle.
- Persistence: `meta.bax_hums_heard: set[int]`. Jukebox UI in main menu. (Section 7.4.)

### 8.3 Reactive systems

**8.3.1 `audio/synth.py` — `slingshot_stinger()`.**
- Reverse-cymbal swell, pre-baked. Triggered next bar after `EVT_SLINGSHOT`. (Section 6.3.)

**8.3.2 `audio/audio_manager.py` — pad-key modulation on slingshot.**
- `_temp_modulation: tuple[float, int] | None` — `(semitones_up, bars_remaining)`.
- Pre-bake all 12 chromatic pad transpositions at boot. (Section 6.3.)

**8.3.3 `audio/audio_manager.py` — tether snap musical resolution.**
- On `EVT_TETHER_SNAP`: schedule one-bar bass interruption + pad opening. (Section 6.4.)

**8.3.4 `audio/synth.py` — `barge_motif()` minor-2nd harp drone.**
- Looping low-amplitude. Plays on `EVT_BARGE_NEARBY`. Resolves on proximity clear. (Section 6.2.)

### 8.4 Diegetic systems

**8.4.1 `audio/radio_stations.py` — new file.**
- 4 procedurally-generated 30 s pieces.
- New `SCENE_RADIO`. New input binding **R** in flight to toggle. (Section 7.1.)

**8.4.2 `audio/synth.py` — `decanting_printer()`.**
- Receipt printer SFX. Used in choreographed decanting sequence.

**8.4.3 `audio/audio_manager.py` — `SCENE_DECANTING` choreography.**
- Replace current loop with explicit scripted sequence in Section 7.5.

**8.4.4 `audio/audio_manager.py` — main-menu long-form mode.**
- Idle timer in `set_scene(SCENE_MENU)`. After 120 s → `long_form_menu_pad()` (new 90 s composition). (Section 7.6.)

### 8.5 Per-chapter inflection

Each chapter ships a small `audio/chapter_<n>.py`:
- Home key root frequency.
- Mode.
- Kit inflection function (post-processes the drum loop).
- Signature instrument (function returning Sound).
- Cargo damage hook (`cargo_alarm(state)` callback).
- HUD subtitle/visual signpost wiring.

`Game._enter_chapter(n)` calls `audio.load_chapter(n)`. (Section 4.)

### 8.6 Accessibility & subtitles

**8.6.1 `core/event_bus.py` — new event.**
- `EVT_MUSIC_SUBTITLE(text: str, duration_s: float, color: str = "amber")`.

**8.6.2 `renderer/music_subtitle_renderer.py` — new file.**
- Bottom-third overlay, italicized, dim amber-grey. Distinct from cockpit speech. (Section 7.5.1.)

**8.6.3 `ship/hud.py` — add KEY UP / RELEASE pips & threat-motif edge pulse.**
- Three new persistent HUD elements (Section 7.5.3).

**8.6.4 Settings menu — 6 per-stem sliders + Quiet Mode toggle.**
- Wire each slider to a stem-group volume scalar in AudioManager. (Sections 7.5.4–7.5.5.)

### 8.7 Order of operations

Implementation difficulty (no calendar estimates per CLAUDE.md):

1. **8.0** (stem ingestion + graceful degradation) — must be first, unblocks everything.
2. **8.6** (subtitle/visual indicator infrastructure) — second, because every later section depends on it for signposting.
3. **8.1** (reactive foundations) — biggest invasive change to `audio_manager.py`; additive but touches the main loop.
4. **8.2** (cohesion — chapter-keyed engine + pad + licks) — small parameterizations.
5. **8.3** (reactive systems — net-new event subscribers).
6. **8.4** (diegetic systems — net-new modules, low risk to existing flow).
7. **8.5** (per-chapter inflection — touches `core/game.py` chapter loading; mildly invasive, well-isolated).
8. **8.2.4 Bax hums** — ship last, after the bandstand is polished. The emotional payload lands on a finished stage.

### 8.8 Risk register

| Risk | Mitigation |
|---|---|
| Phase-vocoder pitch-shift/stretch CPU at boot | Pre-shift only chapter-active keys (≤4) + only stretch rhythm bed. Total budget <8s boot on Steam Deck. |
| Master FX CPU per buffer | Pre-allocate working arrays. Profile on Steam Deck baseline. `--no-fx` debug flag. |
| Ch4 Ligeti clusters sound "broken" | Anchor every cluster to a sub-bass E. Fallback to natural-minor-with-chromatic-passing-tones wired in from day one. |
| Bax hum tracks feel repetitive in long sessions | 12-hum pool, mood-gated selection by run context, never play same hum twice in 3 deliveries. |
| Subtitle clutter during peak action | Subtitle queue de-dupes and rate-limits (max 1 new subtitle per 1.5 s during high pressure). |
| Recorded stems missing on first builds | Graceful degradation means game ships and plays through full campaign with zero recorded stems. Every stem drop = audible upgrade, never a blocker. |

---

## Section 9 — How we know it's working (success metrics)

If, by Next Fest, the following are true, the soundtrack ships at award-contender quality. Each metric below is **falsifiable** — measurable, not vibes.

| Metric | How we measure | Pass threshold |
|---|---|---|
| **Chapter identifiable from audio alone** | Internal blind test: 5 returning playtesters listen to 15 s of muted-visual run clips, identify chapter. | ≥80% correct. |
| **Threat motif read as warning** | Playtest observation log: do players react to the motif arrival before seeing the barge? | ≥3 of 5 players do, by their 3rd run. |
| **Slingshot stinger feels like a reward** | Post-playtest survey, single Likert: "When you nailed a slingshot, did the music feel like it rewarded you?" 1–5. | Mean ≥4.0. |
| **Bax hum noticed** | Survey: "Did Bax hum to you after deliveries?" yes/no. | ≥80% yes. |
| **Bax hum collected** | `meta.bax_hums_heard` average count across save files. | ≥4/12 after Next Fest weekend. |
| **Players engage cockpit radio** | Telemetry: count `R` key presses per session. | ≥1.5 mean per session. |
| **Mix is not overwhelming** (the v1 problem) | Survey: "Did the music feel too busy or overwhelming at any point?" yes/no. | <20% yes. |
| **Subtitles don't clutter** | Survey: "Did the music subtitles feel intrusive?" yes/no. | <15% yes (with default-on settings). |
| **Audio CPU budget** | Profile on Steam Deck baseline. | <8% frame time. |
| **No two consecutive runs sound identical** to a paying-attention player | Internal A/A test: same chapter, same outcome, different RNG. Do players notice the variation? | ≥3 of 5 players cite at least one audible difference. |

If those are all true, we are not shipping a soundtrack. We are shipping **a cockpit you don't want to leave.**

— end —
