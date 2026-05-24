# DEAD DRIFT — Bax Hums Implementation Plan

**Author:** Dead Drift audio team
**Status:** Spec — ready to build
**Parent:** `SOUNDTRACK_PLAN.md` Section 7.4
**Related commits already on `claude/improve-game-mechanics-RkgJV`:** `d88b37e` (mix tuning), `22f9a16` (mood-tagged licks + NPC signatures)

---

## Goal

> *"Once per campaign, on the first delivery success of a run, Bax hums. Not sings. Hums. Four bars. A wordless melody in A natural minor, descending A–G–E–D–C–A. It plays once over the delivery success screen, then is never heard again in that run."* — Plan §7.4

Ship 8 of these hums. Persist which ones the player has heard. After campaign clear, unlock a main-menu **jukebox** screen where the player can replay any heard hum.

This is the **emotional payload** piece of the audio overhaul — the moment the plan describes as "the clip that goes on Twitter." Treat it accordingly: ship 8 *distinct* hums, not 8 variations.

---

## Scope (in / out)

**In scope**
- 8 procedurally-generated hummed melodies (`audio/bax_hum.py`).
- Save persistence: `bax_hums_heard: list[int]` keyed by index 0–7.
- Trigger: first `EVT_DELIVERY_DONE` per run; picks an unheard hum; marks heard.
- Audio: plays over delivery-success screen on a dedicated channel.
- Main-menu jukebox screen unlocked when `len(meta.chapters_completed) >= 4`.

**Out of scope**
- Hums playing during in-game cinematics, decanting, or any other moment.
- Achievement system for "hear all 8" (the plan suggests it; defer).
- Localization of the jukebox UI labels.

---

## Sonic specification

Per Plan §7.4 + §2 (the *Dead Drift Sound* rules):

| Attribute | Value |
|---|---|
| Length | 4 bars at 84 BPM (~11.4 s including release tail) |
| Key center | A natural minor, root = 220.0 Hz |
| Melodic shape | All 8 melodies are **descending** as their primary motion. Variation comes from rhythmic feel, ornaments, and which scale tones they pass through. |
| Voice | Triangle wave + breath noise + slight vibrato (4 Hz, ±10 cents). |
| Tuning | Triangle voice detuned **−6 cents** vs concert pitch — same as the harmonica. Bax has been gigging too long. |
| Dynamics | Slow attack (~120 ms), long release (~600 ms). No staccato. |
| Mix | Same channel rules as `_BAX_V_CH = 7` for voice character, but **route through its own channel** so it isn't ducked by the voice-duck logic (see "Channels" below). |
| Range | A3 to A4. No higher; the plan calls it a *hum*, not a melody. |
| Stereo | Mono. (Hums are intimate — mono keeps them in the cockpit, not the cathedral.) |

### The 8 melodies

All in A natural minor (A B C D E F G). Use scale degrees so transposition stays trivial.

| # | Title (dev shorthand) | Sequence (scale degrees) | Mood |
|---|---|---|---|
| 0 | *Standard Issue* | 1–♭7–5–4–♭3–1 (A–G–E–D–C–A) | weary — the plan's canonical example |
| 1 | *Long Way Home* | 1–♭7–♭6–5–4–1 (A–G–F–E–D–A) | lonely |
| 2 | *Two Step Drift* | 1–5–♭3–2–1, repeat with passing ♭7 | cocky, low energy |
| 3 | *Quarter to Three* | 1–♭3–2–1–♭7–1 (loops back) | sarcastic |
| 4 | *Receipt Tape* | 1–1–♭7–♭7–5–5–4–1 (paired notes) | weary |
| 5 | *Empty Cab* | 1–♭3–5–♭3–1 (slow climb, slow fall) | lonely |
| 6 | *Last Lap* | ♭3–2–1–♭7–♭6–5 (descending modal) | weary |
| 7 | *Sign Here Please* | 1–2–♭3–2–1, repeat then settle on 1 | content / first-clear |

Hum 7 is the **campaign-clear** hum — reserve it for when `complete_chapter(4)` is called (see "Trigger logic" below). The first six firings of `EVT_DELIVERY_DONE` (in any combination of chapters 1–4 across runs) draw from hums 0–6 in order of first-availability.

---

## Files to create or modify

| File | Action | Purpose |
|---|---|---|
| `audio/bax_hum.py` | **new** | 8 hummed melodies, prebuild-all helper |
| `audio/audio_manager.py` | modify | new channel, new SFX entry, `play_bax_hum(idx)` API, `EVT_DELIVERY_DONE` extension |
| `core/event_bus.py` | modify (optional) | optionally add `EVT_BAX_HUM` for renderer to subtitle the hum |
| `roguelite/meta_progression.py` | modify | add `bax_hums_heard: list[int]` to `_DEFAULTS`, getter, setter |
| `core/game.py` | modify | main-menu jukebox: new `_menu_mode = "jukebox"`, row in `_main_menu_rows`, key handler, renderer |
| `renderer/sci_fi_ui.py` | modify | `draw_jukebox_screen()` helper (the visual style is "vinyl album spread" — see UI section) |

---

## Implementation steps

### Step 1 — `audio/bax_hum.py` (new, ~180 LOC)

Model the file on `audio/voices.py` and `audio/blues_licks.py`. Same imports, same `_to_sound` discipline.

```python
"""
Dead Drift — Bax hums.
8 wordless humming melodies, 4 bars each at 84 BPM, in A natural minor.
Plan §7.4 — the emotional payload.  Each is a Sound; prebuild all at boot.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr, _t

# --- Scale & timing ---------------------------------------------------------
_ROOT_FREQ   = 220.0    # A3
_DETUNE_CENT = -6.0     # Bax-flat — see plan §2.2
_BPM         = 84.0
_BEAT_S      = 60.0 / _BPM
_BAR_S       = _BEAT_S * 4

def _semitone(n: int) -> float:
    """Hz for `n` semitones above A3, detuned −6 cents."""
    return _ROOT_FREQ * (2.0 ** ((n + _DETUNE_CENT / 100.0) / 12.0))

# Scale degree → semitones above root in A natural minor
_DEGREE_MAP = {
    "1": 0, "2": 2, "b3": 3, "4": 5, "5": 7, "b6": 8, "b7": 10, "8": 12,
}

# --- Voice synth ------------------------------------------------------------
def _hum_voice(freq: float, duration: float, amp: float = 0.30) -> np.ndarray:
    """Triangle voice + breath noise + slight vibrato.  Plan §7.4."""
    t = _t(duration)
    vib = 1.0 + 0.006 * np.sin(_2PI * 4.0 * t)     # 4 Hz vibrato, ±10 cents
    phase = np.cumsum(_2PI * freq * vib / SAMPLE_RATE)
    # Triangle from a low-passed saw
    saw = 2.0 * (phase / _2PI - np.floor(0.5 + phase / _2PI))
    tri = 1.0 - 2.0 * np.abs(saw)
    # Breath layer — band-passed noise that follows the envelope
    noise = np.random.uniform(-1.0, 1.0, len(t)).astype(np.float32) * 0.05
    # 120 ms attack, 600 ms release (plan §7.4)
    wave = (tri * 0.92 + noise) * amp
    return _adsr(wave, attack=0.12, decay=0.10, sustain=0.85, release=0.6)

# --- Melody assembly --------------------------------------------------------
def _render_melody(notes: list[tuple[str, float]]) -> pygame.mixer.Sound:
    """
    notes: list of (scale_degree, beats) tuples.  Total beats should sum to 16
    (4 bars at 4/4).  Each note runs for its assigned beats with a slight
    legato overlap into the next.
    """
    total_dur = sum(n[1] for n in notes) * _BEAT_S + 0.6   # +tail
    out = np.zeros(int(SAMPLE_RATE * total_dur), dtype=np.float32)
    pos_s = 0.0
    for deg, beats in notes:
        freq = _semitone(_DEGREE_MAP[deg])
        dur  = beats * _BEAT_S * 1.08    # 8% legato bleed
        v    = _hum_voice(freq, dur)
        n    = int(pos_s * SAMPLE_RATE)
        end  = min(n + len(v), len(out))
        out[n:end] += v[:end - n]
        pos_s += beats * _BEAT_S
    return _to_sound(out.clip(-1.0, 1.0))

# --- The 8 hums -------------------------------------------------------------
_HUMS: list[list[tuple[str, float]]] = [
    # 0 — Standard Issue: A G E D C A, two beats each (the plan's canonical)
    [("1", 2), ("b7", 2), ("5", 2), ("4", 2), ("b3", 2), ("1", 6)],
    # 1 — Long Way Home: descending through b6
    [("1", 2), ("b7", 1.5), ("b6", 1.5), ("5", 2), ("4", 3), ("1", 6)],
    # 2 — Two Step Drift: low-energy pair
    [("1", 1), ("5", 1), ("b3", 1), ("2", 1), ("1", 2),
     ("1", 1), ("5", 1), ("b3", 1), ("b7", 1), ("1", 5)],
    # 3 — Quarter to Three: arch shape that loops back
    [("1", 2), ("b3", 2), ("2", 2), ("1", 2), ("b7", 2), ("1", 6)],
    # 4 — Receipt Tape: paired notes (matches the printer rhythm in decanting)
    [("1", 1), ("1", 1), ("b7", 1), ("b7", 1),
     ("5", 1), ("5", 1), ("4", 2), ("1", 8)],
    # 5 — Empty Cab: slow climb and fall
    [("1", 3), ("b3", 3), ("5", 4), ("b3", 3), ("1", 3)],
    # 6 — Last Lap: modal descending
    [("b3", 2), ("2", 2), ("1", 2), ("b7", 2), ("b6", 2), ("5", 6)],
    # 7 — Sign Here Please: campaign-clear hum, settles content
    [("1", 1), ("2", 1), ("b3", 2), ("2", 1), ("1", 3),
     ("1", 1), ("2", 1), ("b3", 2), ("1", 4)],
]

def build_hum(idx: int) -> pygame.mixer.Sound:
    if not 0 <= idx < len(_HUMS):
        raise IndexError(idx)
    return _render_melody(_HUMS[idx])

def prebuild_all_hums() -> list[pygame.mixer.Sound]:
    return [build_hum(i) for i in range(len(_HUMS))]

def hum_count() -> int:
    return len(_HUMS)

def hum_title(idx: int) -> str:
    return [
        "STANDARD ISSUE", "LONG WAY HOME", "TWO STEP DRIFT", "QUARTER TO THREE",
        "RECEIPT TAPE", "EMPTY CAB", "LAST LAP", "SIGN HERE PLEASE",
    ][idx]
```

**Acceptance for Step 1:** boot a Python REPL, `import audio.bax_hum; sound = audio.bax_hum.build_hum(0); sound.play()` produces 11–12 seconds of clean descending hum, no glitches, no clipping.

---

### Step 2 — wire into `AudioManager`

In `audio/audio_manager.py`:

```python
# Channel layout addition (near the top):
_HUM_VOICE_CH = 29   # dedicated channel for Bax hums

# In __init__:
self._hum_voice_ch: pygame.mixer.Channel | None = None
self._bax_hums: list[pygame.mixer.Sound] = []

# In _build, after the voices section:
print("[audio] generating Bax hums…", flush=True)
from audio.bax_hum import prebuild_all_hums
self._bax_hums = prebuild_all_hums()

# In _start_loops, after _barge_ch setup:
self._hum_voice_ch = pygame.mixer.Channel(_HUM_VOICE_CH)
self._hum_voice_ch.set_volume(self._master * 0.62)   # prominent but not peak

# New public method:
def play_bax_hum(self, idx: int) -> None:
    """Play one of the 8 prebuilt Bax hums on its dedicated channel.
    Ducks the bandstand briefly so the hum sits clean over the success screen.
    """
    if not 0 <= idx < len(self._bax_hums) or self._hum_voice_ch is None:
        return
    # Duck the bandstand for the hum's duration (~12s).  Set targets to
    # 25% of current so drums/bass/arp are still there as bed but the hum is
    # the foreground.
    self._vol_targets = {k: v * 0.25 for k, v in self._vol_targets.items()}
    self._hum_voice_ch.stop()
    self._hum_voice_ch.set_volume(self._master * 0.62)
    self._hum_voice_ch.play(self._bax_hums[idx])
    # The success screen sits on-screen for ~5 s, then we exit to interstitial;
    # exiting calls set_scene(INTERSTITIAL) which resets _vol_targets anyway.
```

**Do not** subscribe `EVT_DELIVERY_DONE` to a hum-playing handler here. The trigger logic lives upstream so it can consult `meta` for the "first time this run" check.

---

### Step 3 — extend `MetaProgression` for hum persistence

In `roguelite/meta_progression.py`:

```python
_DEFAULTS = {
    "debt":               150000,
    "clone_count":        1,
    "chapters_completed": [],
    "bax_level":          1,
    "reputation":         {},
    "bax_hums_heard":     [],     # NEW — list of int indices, 0..7
}

# Methods to add at the end of the class:
def mark_hum_heard(self, idx: int) -> bool:
    """Record that the player has heard hum `idx`.  Returns True if newly heard."""
    heard = self._data["bax_hums_heard"]
    if idx in heard:
        return False
    heard.append(idx)
    self.save()
    return True

@property
def bax_hums_heard(self) -> list[int]:
    return list(self._data["bax_hums_heard"])

@property
def campaign_cleared_at_least_once(self) -> bool:
    return len(self._data["chapters_completed"]) >= 4
```

`SaveManager` reads/writes `MetaProgression` via its standard JSON round-trip — no changes needed there; the new key flows through `{**defaults, **loaded}`.

**Migration:** existing save files don't have `bax_hums_heard`. The `{**defaults, **loaded}` merge in `MetaProgression.load()` handles this — the key defaults to `[]` when missing. Verified safe.

---

### Step 4 — Trigger logic in `core/game.py`

The trigger needs to:
1. Fire only on the **first** `EVT_DELIVERY_DONE` of a run (not on chapter-end-loop repeats).
2. Pick an unheard hum (or hum 7 if the player is on their campaign-clear run).
3. Call `meta.mark_hum_heard(idx)` and `audio.play_bax_hum(idx)`.

Location: add a new method to `Game` and subscribe it in `_subscribe_events()` (or wherever bus subs live for `Game`).

```python
# Game.__init__ — add state:
self._hum_played_this_run: bool = False

# New subscriber:
def _on_delivery_done(self, **_):
    if self._hum_played_this_run:
        return
    self._hum_played_this_run = True

    # Pick which hum to play
    heard = set(self.meta.bax_hums_heard)
    # Hum 7 is reserved for the moment the player completes Chapter 4.
    is_final_chapter = (self.run_mgr.current_chapter == 4) if self.run_mgr else False
    if is_final_chapter and 7 not in heard:
        idx = 7
    else:
        unheard = [i for i in range(8) if i not in heard and i != 7]
        if not unheard:
            # Player has heard everything — replay a random non-7 hum
            idx = random.randrange(7)
        else:
            idx = unheard[0]   # in order

    self.meta.mark_hum_heard(idx)
    if self.audio:
        self.audio.play_bax_hum(idx)

# Reset _hum_played_this_run when a new run starts:
def _on_run_start(self, **_):
    self._hum_played_this_run = False
```

Wire `EVT_DELIVERY_DONE` and `EVT_RUN_START` subscriptions on `Game`.

**Important — chapter index source:** Game tracks the current chapter via `self.run_mgr.current_chapter` (verify the exact attribute name in `roguelite/run_manager.py`). If it's named differently, use whatever the canonical accessor is. The test for "is this the campaign-clear delivery" is "is the player on Chapter 4 *and* has just completed it" — `complete_chapter(4)` is called elsewhere in the existing flow; the hum should fire **before** that call, otherwise hum 7 only plays on chapter clears that have already been recorded.

**Edge cases to handle:**
- Player skips delivery via dev console → `EVT_DELIVERY_DONE` still fires? Verify. If yes, fine. If not, no hum — acceptable.
- Player dies during delivery → `EVT_DELIVERY_DONE` does NOT fire (it's emitted only on success). Confirmed by reading `delivery/corridor/base.py:652` and `delivery/platformer.py:232`.
- Player completes Ch.4 but already heard hum 7 from a previous campaign → falls to the `unheard` branch; if all heard, picks a random replay.

---

### Step 5 — Main-menu jukebox screen

Add a new menu mode `"jukebox"` to `core/game.py`.

**Entry condition:** show the "JUKEBOX" row in the main menu only when `self.meta.campaign_cleared_at_least_once` is true.

```python
# In _main_menu_rows, after QUIT:
if self.meta.campaign_cleared_at_least_once:
    rows.insert(-1, ("JUKEBOX", True, "jukebox"))   # before QUIT

# In _menu_activate:
elif action == "jukebox":
    self._menu_mode = "jukebox"
    self._jukebox_cursor = 0
```

State:
```python
# Game.__init__:
self._jukebox_cursor = 0   # which hum is selected
```

Keys (in a new `_handle_jukebox_key`):
- `UP` / `DOWN` — move cursor through the 8 hums (greyed if not heard).
- `ENTER` / `SPACE` — play selected hum (if heard).
- `ESC` — back to main menu.

```python
def _handle_jukebox_key(self, event: pygame.event.Event) -> None:
    if event.key == pygame.K_ESCAPE:
        self._menu_mode = "main"
        return
    if event.key in (pygame.K_UP, pygame.K_w):
        self._jukebox_cursor = (self._jukebox_cursor - 1) % 8
    elif event.key in (pygame.K_DOWN, pygame.K_s):
        self._jukebox_cursor = (self._jukebox_cursor + 1) % 8
    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
        heard = set(self.meta.bax_hums_heard)
        if self._jukebox_cursor in heard and self.audio:
            self.audio.play_bax_hum(self._jukebox_cursor)
```

Route the key from `_handle_main_menu_key` based on `self._menu_mode == "jukebox"`. (Pattern matches existing `pick_new` / `pick_load` routing.)

---

### Step 6 — Jukebox renderer

Add `draw_jukebox_screen(surf, meta, cursor, t)` to `renderer/sci_fi_ui.py`.

**Visual treatment:**
- Background: same `VOID` dark blue as menu.
- Title: "BAX'S TAPES" in amber, top-center, 38pt monospace bold.
- Subtitle: "EIGHT HUMS. CLONE TANK B-SIDES." in dim cyan.
- Center column: 8 rows, each:
  - Row index (01–08) in dim grey.
  - Hum title (e.g., "STANDARD ISSUE") in amber if heard, dead-grey if not.
  - Padlock glyph for unheard rows; a small vinyl-circle glyph for heard rows.
  - Selected row gets a left-edge amber chevron + light scanline overlay (1-pixel inverted text band, cycling every 1.5 s).
- Footer hint: "[↑/↓] PICK  [ENTER] PLAY  [ESC] BACK".

The visual is *not* a music-player UI. It's a **clipboard** Bax keeps. Adopt the diegetic clipboard style already used in the loadout screen.

Sketch:
```python
def draw_jukebox_screen(surf: pygame.Surface, meta, cursor: int, t: float) -> None:
    from audio.bax_hum import hum_count, hum_title
    cx = surf.get_width() // 2
    # Title block
    _draw_text(surf, "BAX'S TAPES", (cx, 100), 38, S.AMBER, center=True)
    _draw_text(surf, "EIGHT HUMS. CLONE TANK B-SIDES.", (cx, 150), 18,
               (110, 200, 200), center=True)
    heard = set(meta.bax_hums_heard)
    row_y = 220
    for i in range(hum_count()):
        is_sel    = i == cursor
        was_heard = i in heard
        color     = S.AMBER if was_heard else S.DEAD_GREY
        prefix    = f"{i+1:02d}  "
        glyph     = "○" if was_heard else "✕"   # vinyl vs locked
        title     = hum_title(i) if was_heard else "■■■■■■■■■■"
        line      = f"{prefix}{glyph}  {title}"
        if is_sel:
            pygame.draw.rect(surf, (40, 40, 70),
                             (cx - 220, row_y - 4, 440, 30))
            _draw_text(surf, "›", (cx - 215, row_y), 24, S.AMBER)
        _draw_text(surf, line, (cx - 180, row_y), 20, color)
        row_y += 36
    _draw_text(surf, "[↑/↓] PICK   [ENTER] PLAY   [ESC] BACK",
               (cx, surf.get_height() - 60), 16, (90, 90, 120), center=True)
```

Wire into `_render_main_menu` to call `draw_jukebox_screen` when `self._menu_mode == "jukebox"`.

---

## Channels & mix budget

The hum plays on a **new dedicated channel** `_HUM_VOICE_CH = 29` so it isn't ducked by `_voice_duck` (which is for Bax's *speaking* voice). The hum is meant to *be* the foreground for its 12 seconds — the band ducks under it via the `_vol_targets *= 0.25` line in `play_bax_hum`.

Initial volume: `master * 0.62`. This is slightly louder than the harp (`0.55`) but quieter than full master — the hum should feel intimate and close, not anthemic.

The hum's release tail (~600 ms) carries past the delivery-success screen into the interstitial; that's fine — set_scene(INTERSTITIAL) will fade the band back up and the hum will tail off naturally.

---

## Verification

### Unit-level

1. `python -c "from audio.bax_hum import prebuild_all_hums; print(len(prebuild_all_hums()))"` prints `8`.
2. `python -c "from audio.bax_hum import build_hum; s = build_hum(0); print(s.get_length())"` prints ~11.4.
3. Each hum's audio buffer is finite, non-NaN, peak ≤ 1.0 — add a `tests/test_bax_hum.py` mirroring `tests/test_voices.py` if you want CI cover.

### Integration

4. Boot the game. Start a fresh save. Complete one delivery (any chapter).
5. Confirm a hum plays over the delivery-success screen.
6. Open the save file (`data/saves/slot_N/meta.json`). Confirm `"bax_hums_heard": [0]`.
7. Complete a second delivery in the same run — *no hum* (already played this run).
8. Die. Start new run. Complete delivery. Hear hum **1** (next in order).
9. Repeat through all 6 base hums (0–6). On the run that clears Chapter 4, hear hum **7**.
10. Return to main menu — "JUKEBOX" row now appears.
11. Open jukebox. Confirm 8 rows; heard ones are amber-titled, unheard show `■■■■■■■■■■`. Cursor up/down works. ENTER plays the selected hum. ESC returns to main menu.

### Sound check (subjective, but mandatory)

12. Hum sounds like *humming*, not like the harmonica.
13. Mix: hum is clearly foreground; drums/bass/arp are present but ducked.
14. Hum 0 (the canonical one) audibly descends through A–G–E–D–C–A. If you can't pick out the notes, the synth's brightness needs raising or the legato needs shortening.
15. Hum 7 feels different from 0–6 — settled, content. If it doesn't, the rhythm needs reworking (more even, less descending).

---

## Risk / what could go wrong

- **Hum buffer too short.** If `_render_melody` rounds total duration short, the last note clips. Add a guard: `total_dur = max(11.0, ...)`.
- **Bass voice clashes with hum's root.** The hum sits in the A3–A4 register (220–440 Hz); the walking bass currently in flight scenes lives around 55–110 Hz. No clash expected, but during delivery the bass goes higher — verify by ear. If there's mud, transpose hums up an octave (root = 440 Hz instead of 220 Hz) — keep the *intervals* identical.
- **Trigger fires before chapter-completion sequence.** If `complete_chapter()` is called before `_on_delivery_done` (because of `EVT_DELIVERY_DONE` listener order), hum 7 logic breaks. Test by adding a print to `complete_chapter` and confirming the order. If wrong, gate hum 7 on a slightly later signal — e.g., the player pressing ENTER to leave the success screen.
- **Save corruption from interrupted writes.** `meta.save()` writes inline (no atomic temp-rename). If the game crashes mid-write, the save loses the entry. Acceptable for now — the hum simply replays. Don't add atomic-write machinery for this feature alone.
- **Player on linux/ALSA hearing a click at end of hum.** The release envelope is 600 ms; if you hear a click, raise to 800 ms.

---

## Definition of done

- [ ] `audio/bax_hum.py` exists, prebuilds 8 hums, all audibly distinct.
- [ ] `AudioManager.play_bax_hum(idx)` plays hum over a ducked bandstand.
- [ ] `MetaProgression` persists `bax_hums_heard`, migration safe.
- [ ] First delivery success per run triggers an unheard hum.
- [ ] Chapter 4 completion specifically plays hum 7.
- [ ] Jukebox menu row appears post-campaign-clear.
- [ ] Jukebox screen lists 8 hums, gates unheard, plays heard, ESC returns.
- [ ] Tests pass: `python -m pytest tests/ -x -q`.
- [ ] Hand-test: complete-clear playthrough hears 4 distinct hums in one campaign.

---

## Estimated scope

- `audio/bax_hum.py`: ~180 LOC, 1 sitting.
- `audio_manager.py` integration: ~30 LOC, trivial.
- `meta_progression.py`: ~15 LOC, trivial.
- `game.py` trigger + jukebox: ~80 LOC + 1 new menu mode.
- `sci_fi_ui.py` renderer: ~50 LOC.
- Total: ~350 LOC of new code, ~50 LOC of integration edits.

One focused dev session if no surprises in `run_manager.current_chapter` or the menu-routing pattern.

---

## After this lands

The plan's §7.4 closes with: *"Achievement: hear all 8."* That's a follow-up issue — wire `meta.bax_hums_heard` length 8 into the achievement / Steam stat layer when that layer exists. Out of scope for this work.
