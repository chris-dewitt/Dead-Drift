# Dead Drift — Android slice

Landscape-only Play Store build. Cut-down loop: **flight + delivery tunnels**.
No terminals. Phone and tablet share one APK; the game letterboxes a 1600×900
logical frame onto the device.

## Player loop

1. Menu (tap rows / CONFIRM)
2. Loadout + difficulty (dashboard arrows + CONFIRM)
3. Five flight sectors — drag-thrust, tap FIRE, JUMP when the gate opens
4. Dock approach (same stick) → corridor (stick + JUMP / SPRINT / TALK / DOWN)
5. Payout → next chapter

Barges still hunt. Mid-flight comms are skipped; an intercept goes straight
to the aim / harpoon beat. Shops are skipped. Saves land in app-private storage.

## Controls

| Overlay | Action |
|---------|--------|
| Left-half **drag** | Thrust + rotate (analog). Corridor: run / climb |
| **FIRE** | Hold to shoot |
| **JUMP** | Advance sector (when ready) / corridor jump |
| **SPRINT** | Hold to charge corridor sprint |
| **TALK** / **DOWN** | Corridor interact / warp pipe |
| **PAUSE** | Pause / back |
| **FILE** | Chapter 3 paperwork popup |

Desktop preview (no device):

```bash
DEAD_DRIFT_MOBILE=1 python main.py
```

## Build a store package

Host needs Java, Buildozer, and the Android SDK/NDK (Buildozer fetches the
SDK on first run).

```bash
pip install buildozer Cython
python tools/build_android.py            # debug APK → bin/
python tools/build_android.py --release  # Play upload (AAB)
```

Package id: `org.chrisdewitt.deaddrift`  
Version: `0.9.0` in `buildozer.spec`  
Icon: `assets/android/icon.png` (regenerate with `python tools/make_android_icon.py`)

Requirements are **pygame-ce + numpy only** — NLTK is not shipped.

## Orientation

`sensorLandscape` — both landscape directions, never portrait.

## Signing

`buildozer android release` prompts for a keystore. Keep the keystore off-repo.
Upload the `.aab` in Play Console → Production / Internal testing.
