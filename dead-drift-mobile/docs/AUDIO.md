# Audio

**Goal:** keep the original's lo-fi, tape-hum, procedural feel without
running heavy numpy-style synthesis on a phone CPU. Leave clean slots
for Chris's recorded soundtrack whenever it's ready (no rush).

## Approach: pre-rendered procedural palette plus light runtime DSP

1. **Offline render.** A tool in `tools/` (outside the game build) produces
   OGG one-shots and loops from procedural recipes modeled on the original:
   engine hum layers, thruster noise, gun blips, barge clamp, tether creak,
   terminal keyclicks, the CRT whine, Bax voice-blip phoneme sets. They're
   rendered once and shipped as small assets.
2. **Runtime DSP on Godot audio buses** (cheap, built in):
   - `Master` → `Music`, `SFX`, `Voice`, `UI`
   - Hull damage → a low-pass sweep on `Music`
   - Ch1 bit-crush → a distortion/bit-reduce effect on `Music` + `SFX`, driven by cargo damage
   - Tape-hum signature → a quiet looping bed on `Music`, always present
3. **Small runtime generators only where needed:** Bax voice blips (pitch and
   rate varied per line) via `AudioStreamGenerator` with a tiny buffer. Profile
   this in M.9 and fall back to pre-rendered blips if it costs more than 1 ms per frame.

## Music director (stem-ready)

- Each chapter defines **4 stem slots**, following the original's mix
  contract (see `../docs/SOUNDTRACK_PLAN.md`, reference only): e.g. bed, pulse,
  lead, tension.
- The director fades stems in and out by game state: calm flight, barge
  chase, terminal, corridor, alarm.
- **Until recordings exist:** procedural placeholder loops fill every slot.
  When a recorded stem lands in `assets/audio/stems/chN/`, it replaces the
  placeholder with no code change.
- **Graceful degradation:** a missing stem falls back to the placeholder. It
  never plays silence or crashes.

## Mobile-specific rules

- **Respect the device:** pause all audio on app pause, and duck under other
  apps' audio focus where Godot supports it.
- **Muted players:** every gameplay-critical sound has a visual or haptic twin
  (alarm, tether, JUMP ready, Ch1 crush). See the "Visual audio cues" setting.
- **Size budget:** ≤ 40 MB audio in the APK. Music OGG at ~96 kbps, SFX mono.
- **Headphones vs speaker:** the default mix is tuned for phone speakers (cut
  sub-bass, lift mids). Add an optional "headphones" EQ preset.
