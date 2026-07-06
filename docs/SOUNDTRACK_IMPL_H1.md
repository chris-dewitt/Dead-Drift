# H.1 — Soundtrack Implementation (sub-plan)

**Parent:** `docs/ALIVENESS_PUSH.md` Phase H · **Companion:** `docs/SOUNDTRACK_PLAN.md` (v2)
**Status:** Mix audit landed (baseline trim). Accessibility layer specced, not built.
**Risk gate (ALIVENESS_PUSH "Risk gates"):** H.1 was flagged as a large audio task
that "may warrant a sub-plan doc." This is that doc.

---

## Why a sub-plan

The procedural soundtrack engine already exists and is substantial:
`audio/audio_manager.py` (~1.5k lines) performs the stems in real time —
tempo modulation, key/mode per chapter, pad swells, threat motif, master FX,
cargo degradation, radio, Bax hums, harmonica licks. H.1 is therefore **not**
"build the music system from scratch." It is the v2 *audit*: make the existing
system obey the SOUNDTRACK_PLAN v2 "less is more" pact and the first-class
accessibility requirements.

The audit splits into three slices of decreasing tractability-without-ears:

| Slice | What | Verifiable headless? | State |
|-------|------|----------------------|-------|
| 1. Baseline mix trim | One global music lever, quieter v2 default | partial (value sniff) | **done** |
| 2. Max-4-active-stems guard | Cap simultaneous musical stems | yes (counting) | **next** |
| 3. Accessibility signposting | Music subtitles + per-stem sliders + mute | UI — needs play | **specced** |

---

## Slice 1 — baseline mix trim (landed)

`AudioManager._music_target_vol` is the single global music lever. v1 sat at
`0.34`; the v2 pact ("the v2 default mix sits ~6 dB quieter… silence is a
stem") moves it to **`0.27`** — a conservative ~2 dB step, deliberately gentle
so music does not vanish under the engine drone. SFX and voice buses are
untouched (the pact is about the *music* sitting back, not the cockpit going
quiet).

**Why not the full 6 dB now:** the 6 dB figure in the plan is relative to the
jarring *v1* mix, and the per-scene `_vol_targets` already tame several
scenes. Slamming −6 dB globally, blind, risks an inaudible bed. The lever is
documented in-code so Chris can dial 0.27 → 0.20 on a play-pass if it still
reads as "too much."

**Play-verify checklist (Chris):**
- [ ] Sector-5 hot pursuit: is the bed present but not fatiguing?
- [ ] Terminal scene (`0.18` target): voices still sit on top cleanly?
- [ ] Delivery handoff: does the cargo theme still land on the tonic audibly?

## Slice 2 — max-4-active-stems guard (next concrete step)

Plan §2.5: "Max 4 active stems at any moment (was 5)." The musical stems are
{kick, snare/clap, hat, bass, pad/arp, harp/lick, guitar, slide}. In practice
flight runs drum+bass+arp (3) plus an occasional harp lick or guitar phrase,
so the engine *usually* honors the cap already. The guard makes it explicit:

- Add an active-stem accounting helper that counts channels with non-zero
  target volume among the musical set (exclude engine, ambient, tape-hum —
  those are bed, not stems).
- When a 5th would open, duck the lowest-priority active stem to zero first
  (priority order from §2.4: harp > pad > bass > drums for *removal*, i.e.
  garnish drops before backbone).
- Headless test: drive a scene transition and assert the count never exceeds 4.

This is safe to build blind because it is structural (counting + gating
existing channels), not a subjective level.

## Slice 3 — accessibility signposting (specced, needs a play-pass)

Plan §7.5 makes these first-class. They require UI work and a settings surface
that does not exist yet (`config/settings.py` has no audio block, there is no
options menu, no caption renderer). Building UI blind and marking it verified
would violate the push's "play-verify before checkbox" rule, so it is specced
here for a session that can run the window:

1. **Music subtitles.** New `EVT_MUSIC_CAPTION` emitted by `audio_manager` at
   the signature moments (§1.4): barge dread `[harmonica — distant, sour]`,
   slingshot `▲ KEY UP`, tether release `[bass walks down — release]`,
   decanting funeral, low-hull harmonica. Render through the same transient
   text path the D.6 scan-ack already uses (`vector_renderer`), gated behind a
   `MUSIC_CAPTIONS` setting (default on).
2. **Per-stem sliders.** Drums / Bass / Pad / Harp / SFX / Voice volume
   multipliers in a new audio settings block, applied as scalars on the
   matching channel groups in `_apply_band_volumes` / the SFX pool.
3. **Master mute.** A single toggle that zeroes `_master` (cache + restore),
   reachable from pause/options.

Players running music-off must not lose gameplay-critical information — the
threat motif's amber edge pulse (already a visual) and the scan-ack line cover
the load-bearing cues, so muting is safe once captions land.

---

## Checkbox policy for H.1

- Slice 1 shipped and is value-verifiable headlessly → counts toward H.1.
- Because the *audible* mix level and the accessibility UI need a real
  play-pass, **H.1 stays `[~]`** in `ALIVENESS_PUSH.md` until Chris runs the
  play-verify checklist above and Slice 3 lands in a windowed session.
