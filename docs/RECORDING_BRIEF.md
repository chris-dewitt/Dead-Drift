# DEAD DRIFT — Recording Brief

**Companion to:** `SOUNDTRACK_PLAN.md` (Section 2.5).
**Audience:** Chris (recording engineer / performer / producer), session musicians, voice talent.
**Purpose:** Exact shot list and technical specs for every stem the procedural audio system will ingest. Take this into a recording session.

> **The graceful-degradation guarantee.** Every stem in this brief has a procedural fallback in the codebase. **No stem is a blocker.** Record what you can, when you can. Each finished stem is an immediate audible upgrade to the live game.

---

## 0. Universal session specs

These apply to every stem unless overridden below.

| Spec | Value |
|---|---|
| Sample rate | 44.1 kHz |
| Bit depth | 24-bit |
| Format | WAV, uncompressed |
| Channels | Mono unless stereo is noted (room mics, ambience) |
| Loudness | Normalize to –14 LUFS reference, true-peak –1.0 dBTP |
| Source key | A natural minor (mixer pitch-shifts to other chapter keys) |
| Source BPM (rhythm-locked stems) | 96 BPM |
| Click track | Yes for rhythm-locked stems; metronome with 1-bar pre-roll |
| Naming | `<category>/<role>_<NN>.wav` (zero-padded, two-digit) |
| Silence padding | 50 ms head, 200 ms tail. No DC offset. |

**File layout (final):**
```
assets/audio/stems/
  harmonica/      lick_01.wav … lick_30.wav
  guitar/         phrase_01.wav … phrase_12.wav
  slide/          note_01.wav … note_12.wav
  bax_hums/       hum_01.wav … hum_12.wav   (+ <slug>.txt with title)
  drums/          kick.wav  snare_gated.wav  clap.wav  hat_closed.wav  hat_open.wav
  bass/           bass_a1.wav … bass_g3.wav
  foley/          knob_click.wav  leather.wav  breath.wav
```

---

## 1. Harmonica licks (30 phrases) — **highest priority**

**Why first:** the harmonica is Bax's instrument. It is the single most identifiable voice in the game. Procedural harp reads as MIDI. A real harp with reed buzz and breath is the difference between "indie" and "award contender."

**Instrument:** A natural-minor diatonic harmonica (10-hole "blues harp" in key of A). Hohner Marine Band, Lee Oskar, or equivalent.

**Tuning:** Tune the **whole harp –6 cents flat** against A=440 before recording. (If your harp can't be re-tuned, the mixer will detune in software; record at concert pitch and we'll handle it.)

**Mic:** Bullet mic (Shure 520DX "Green Bullet") through a small tube amp, mic'd at the cab with an SM57. If a bullet isn't available, an SM58 on-axis at the harp works — slightly less character but ships.

**Performance notes:**
- Breath should be audible. *Reed buzz is a feature.* Don't gate it out.
- Stay in 1st position (A minor pentatonic + ♭5 as passing tone).
- No vibrato wider than a half-step. Slow vibrato preferred.
- Bends: where indicated, push the bend *into* the target note, hold ~80 ms, release.

**Each lick:**
- 1.5 to 3.0 s long.
- Starts and ends on a chord tone of A minor (root, ♭3, 5).
- Ends with a fade-to-zero of ~60 ms (handled in editing if not in performance).

### 1.1 Lick shot list — 30 phrases, 6 moods × 5 each

The procedural fallback already defines 10 lick patterns in `audio/blues_licks.py` (`_LICK_PATTERNS`) — those are the *shape* reference. The new 30-phrase pool expands the mood vocabulary.

| # | Mood tag | Description |
|---|---|---|
| 01–05 | `cocky` | Up-tempo, ascending runs, ending on the ♭7 or octave. Punctuated. Smug. |
| 06–10 | `weary` | Slow, descending, breathy. Long sustained notes. End on the 5. |
| 11–15 | `panic` | Short, choppy, high register. Bent notes. End unresolved. |
| 16–20 | `delighted` | Bright, syncopated, double-time. Major-third "blue note" pass. End up an octave from start. |
| 21–25 | `lonely` | Single sustained notes with slow bends. 4+ seconds total. Almost no rhythm. |
| 26–30 | `sarcastic` | A two-note "wah-wah" reply phrase. Like a comedian's rim shot. Less than 1 second. |

> **Tag every file.** Sidecar `lick_NN.json`:
> ```json
> { "mood": "weary", "duration_s": 2.4, "key": "Am" }
> ```

---

## 2. Acoustic guitar phrases (12 fingerpicked arpeggios)

**Why recorded:** Karplus-Strong synthesis is competent but unmistakably synthetic. Real nylon-string with mic'd body resonance is the difference.

**Instrument:** Nylon-string classical guitar, **tuned standard but +3 cents sharp** against A=440. (The guitar is the optimistic voice in the room. It loses every argument. Slightly sharp = slightly hopeful.)

**Mic:** Two mics — small-diaphragm condenser (KM84, Oktava 012) at the 12th fret, ~20 cm out, on-axis. Optional second condenser at the body to capture body resonance. Mono mix-down acceptable; stereo room mix preferred.

**Performance notes:**
- Fingerpicked, no plectrum.
- Let strings ring. No palm-muting.
- Subtle string-squeak on position changes is a feature.
- Use the same 4-chord progression as the in-game progression: **Am – F – G – Em** (or transpositions).

**Each phrase:**
- 2.0 to 3.5 s long.
- One bar in 4/4 at 96 BPM (so loops cleanly with the drum machine).
- Last note ring-out trailed at –40 dB by end of file.

### 2.1 Guitar phrase shot list — 12 patterns

| # | Pattern | Notes |
|---|---|---|
| 01 | Am descending arpeggio | A4–E4–C4–A3 fingerpicked |
| 02 | Am ascending arpeggio | A3–C4–E4–A4 |
| 03 | F-major broken chord | F3–C4–A3–F4 |
| 04 | G-major broken chord | G3–D4–B3–G4 |
| 05 | Em descending arpeggio | E4–B3–G3–E3 |
| 06 | Am → F walking transition | quarter-note walk down the bass while chord rings |
| 07 | F → G walking transition | quarter-note walk up |
| 08 | G → Em walking transition | quarter-note walk down |
| 09 | Am with hammer-on (3rd) | C → C♯ hammer-on for the 6/8 blues lean |
| 10 | Am with pull-off (♭7) | G pull-off to E |
| 11 | Sustained Am chord, slow rake | one slow arpeggio over 3 s |
| 12 | "Outro" — Am with last note allowed to feed back ~4 s | for the long sustained tag |

---

## 3. Electric slide guitar one-shots (12 mournful sustains)

**Why recorded:** Slide tone *is* the Chapter 2 Solaris signature instrument. Synth wineglass approximations don't carry the same weight.

**Instrument:** Steel-bodied resonator or hollowbody electric. Open D tuning (D–A–D–F♯–A–D), capo not used. Glass slide.

**Mic:** SM57 on the amp at the cone edge, plus a room mic at 2 m for ambience. Stereo recommended; mono acceptable.

**Performance notes:**
- Long sustains — 2.0 to 4.0 s each note.
- *Slide into* every note from a half-step below. The slide is the attack.
- Vibrato on the sustain, but very slow (~3 Hz, half-step depth max).
- Let the note die naturally. No fade-out in the take.

### 3.1 Slide note shot list — 12 pitches

The mournful slide notes power the decanting screen and Chapter 2's signature voice.

| # | Slide from → to | Duration |
|---|---|---|
| 01 | G3 → A3 | 1.6 s |
| 02 | A3 → C4 | 1.8 s |
| 03 | C4 → D4 | 2.0 s |
| 04 | D4 → E4 | 2.2 s |
| 05 | E4 → G4 | 2.4 s |
| 06 | G4 → A4 | 2.6 s |
| 07 | E3 → G3 (low lonesome) | 3.0 s |
| 08 | D3 → E3 | 3.2 s |
| 09 | A2 → C3 (very low growl) | 3.5 s |
| 10 | C5 → D5 (high cry) | 2.8 s |
| 11 | D5 → E5 (highest, almost feedback) | 3.2 s |
| 12 | Hold E4, slow bend down to D4 over 4 s (the closing slide) | 4.0 s |

---

## 4. Bax Hums (12 wordless melodies) — **the emotional payload**

**Why this is the most important recording session.** Section 7.4 of the master plan. Every successful delivery plays one of these. This is the moment a player goes "oh." This is the clip that goes on Twitter. **Bias toward warmth and slight rasp over polish.** Bax has been gigging too long.

**Voice talent:** Chris, or a session voice with a Cockney inflection. Male voice, baritone (~A2–E4 range). Smoker's-edge timbre is welcome.

**Performance notes:**
- **Hum, do not sing.** Mouth closed. Through-the-nose tone.
- 4 bars, ~10 seconds each at 96 BPM (the mixer time-stretches per chapter tempo).
- In A natural minor. The mixer transposes to other chapter keys at runtime.
- Small breath before each hum is *welcome and audible.* Don't edit it out.
- Subtle vibrato OK on sustained notes; don't oversell it.
- Background air noise / room tone is a feature, not a flaw. Record in a small, slightly-resonant space (not a treated booth).

**Mic:** Large-diaphragm condenser (U87, TLM 103, or any modern LDC) at ~25 cm, slightly off-axis to reduce plosives. Pop filter optional — we want a little breath to come through.

### 4.1 Hum shot list — 12 melodies

Each hum has a working title (used in the subtitle: `[Bax hums — '<title>' (n/12)]`). Melodies are *guides*; performer should bend toward feel. The mood tag drives which contexts trigger which hum.

| # | Title | Mood | Melody (degrees in Am) | Notes |
|---|---|---|---|---|
| 01 | *Cold Boot Lullaby* | triumphant | 1–♭3–5–♭7–5–♭3–1 | Open, ascending, ends warm on the root |
| 02 | *Lonesome Beacon* | tender | 5–4–♭3–2–1, hold | Slow, descending, last note held 4 s |
| 03 | *The Foreman's Lament* | weary | 1–♭7–♭6–5, repeat down an octave | Heavy, defeated |
| 04 | *Crooked Antenna Waltz* | wry | 1–5–♭3–5–1 in 3/4 feel | Lilting, slightly drunk |
| 05 | *Two Stops to Tomorrow* | triumphant | 5–♭7–1 (up the octave) | Short, punchy, ends bright |
| 06 | *Sign Here, Press Hard* | wry | 1–1–♭3–1–5–1, ostinato | Sardonic, deadpan |
| 07 | *Tank Number Eleven* | weary | ♭6–5–4–♭3 then long hold on ♭3 | The most defeated of the set |
| 08 | *Half-Tank Hymn* | tender | 1–2–♭3–4–♭3–2–1 | Hymn-like, soft, almost a prayer |
| 09 | *Pinned by Gravity* | weary | 5–4–♭3 (slow), then 1–♭7 (fast), hold 1 | Two-tempo phrase |
| 10 | *Highway Blues for a Dead Quarter* | triumphant | 1–♭3–4–♭5–5–♭7–1 | The full blues scale, finally |
| 11 | *The Last Honest Foreman* | tender | 4–♭3–1, hold; 5–♭3–1, hold | Two sub-phrases with breath between |
| 12 | *Closing Time at the Heliosphere* | wry | 1–♭7–♭6–5–4–♭3–2–1 | A complete descending scale — the album closer |

> **Each hum also gets a one-line "title card" string** that the jukebox UI displays. Provide one alongside the file. Examples:
> - *Cold Boot Lullaby* — "first morning of a long route."
> - *Closing Time at the Heliosphere* — "last lights off the back of the ship."

---

## 5. Drum hits — **6 single-shot samples**

**Why recorded:** LinnDrum tone is iconic and the procedural version is close but never *exactly* right. A pack of high-quality one-shots is small, cheap, and immediately upgrades the mix.

**Source:** Authentic LinnDrum / Linn LM-1 samples (commercial sample packs exist), or live-recorded equivalents through an analog console. **No modern processed samples** — we want 1983 punch, not 2018 sheen.

| File | Description | Notes |
|---|---|---|
| `drums/kick.wav` | LinnDrum kick | Punchy, ~70 Hz fundamental, very short decay |
| `drums/snare_gated.wav` | Gated reverb snare | The Phil Collins snare. ~250 ms reverb tail with a hard gate |
| `drums/clap.wav` | LinnDrum clap | Three slap layers, ~80 ms total |
| `drums/hat_closed.wav` | Closed hi-hat | Tight, ~30 ms |
| `drums/hat_open.wav` | Open hi-hat | Splashy, ~400 ms decay |
| `drums/typewriter_snare.wav` | **Chapter 3 only** — typewriter key slap | Recorded from an actual mechanical typewriter, EQ'd to snare frequency range |

---

## 6. Walking bass notes — **chromatic octave**

**Why recorded:** The walking bass is the union; it shows up on time. Synth bass is fine in the meantime, but a real Fender Precision through a tube amp is the gold-standard.

**Instrument:** Fender Precision or Jazz bass, flatwound strings preferred. Through an Ampeg or Fender tube amp. DI also captured separately.

**Mic:** SM57 on the cab + DI. Mono.

**Performance notes:**
- One note per file. ~1.5 s each. Slight finger-pluck attack.
- Tuning: standard A=440 (no detuning — the mixer handles transposition).
- Sustain ring-out natural to ~–40 dB.

### 6.1 Bass note shot list — 13 notes (A1 to A2, chromatic + low E)

| File | Pitch | Hz |
|---|---|---|
| `bass/bass_e1.wav` | E1 | 41.2 |
| `bass/bass_f1.wav` | F1 | 43.6 |
| `bass/bass_fs1.wav` | F♯1 | 46.2 |
| `bass/bass_g1.wav` | G1 | 49.0 |
| `bass/bass_gs1.wav` | G♯1 | 51.9 |
| `bass/bass_a1.wav` | A1 | 55.0 |
| `bass/bass_as1.wav` | A♯1 | 58.3 |
| `bass/bass_b1.wav` | B1 | 61.7 |
| `bass/bass_c2.wav` | C2 | 65.4 |
| `bass/bass_cs2.wav` | C♯2 | 69.3 |
| `bass/bass_d2.wav` | D2 | 73.4 |
| `bass/bass_ds2.wav` | D♯2 | 77.8 |
| `bass/bass_e2.wav` | E2 | 82.4 |

---

## 7. Cockpit Foley — **3 light atmosphere stems**

**Why recorded:** The radio scene's tuning sweep + the cockpit room tone needs *something* tangible. These are short and cheap.

| File | Description | Length |
|---|---|---|
| `foley/knob_click.wav` | Mechanical knob detent — pots, switches, anything with a satisfying small click | 80 ms |
| `foley/leather.wav` | Leather chair / pilot seat creak | 600 ms |
| `foley/breath.wav` | A single quiet exhale (the cockpit, ambient) | 1.2 s, low amplitude |

---

## 8. Session priority order

If recording time is constrained, this is the order that gives the most-audible game in the fewest sessions.

1. **Bax Hums (Section 4)** — 12 takes, ~30 minutes. Emotional payload. **Most important.**
2. **Harmonica licks 01–10** (the "core 10" — 2 of each mood). Replaces the current 10 procedural patterns with recorded versions. Immediate identity shift.
3. **Drum hits (Section 5)** — single afternoon, or buy a LinnDrum sample pack.
4. **Slide notes 01–06** — the most-used pitches in the decanting screen + Ch2 signature.
5. **Acoustic guitar phrases 01–06** — replaces the most-frequent procedural phrase patterns.
6. **Bass notes E1–A2** — covers the Ch1 + Ch2 walking-bass range. Other notes can wait.
7. **Harmonica licks 11–30** — full mood library.
8. **Slide notes 07–12, guitar phrases 07–12, remaining bass notes** — completeness pass.
9. **Cockpit Foley** — last; fully optional for first ship.

Each stage above is independently shippable. The game gets better with each one. Nothing blocks anything.

---

## 9. Delivery & versioning

- Place finished WAVs in `assets/audio/stems/<category>/<filename>` and open a PR.
- The `stem_loader.py` boot log will report `RECORDED` next to any stem it finds on disk.
- A failed recording can be replaced at any time by overwriting the file — no code change needed.
- Tag stems by mood/title via the sidecar `.json` or `.txt` files specified above so the mixer's mood-filter pipeline picks them up.

— end —
