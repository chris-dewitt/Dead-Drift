# Controls and HUD

Landscape, two thumbs. Every control area is at least 64 dp, nothing sits
under the system gesture edges, and everything respects safe areas.

## Flight (default: "Aim")

```
┌───────────────────────────────────────────────────────────┐
│ HULL ▮▮▮▮▯  CR 4,210  SECTOR 2/5  ⏱ 0:42      [≡ PAUSE]   │
│                                                           │
│                     (play space)                [K] [R]   │
│                                                           │
│  ( floating AIM stick )                 [FIRE]            │
│   anywhere in left half             [THRUST]  [RETRO]     │
│                                            [JUMP]*        │
└───────────────────────────────────────────────────────────┘
 * JUMP appears only when the gate is open (pulsing).
```

- **AIM stick (left thumb):** floats wherever you touch down. The stick
  direction sets a **target heading**. The ship turns toward it with limited
  angular acceleration, so it's still Newtonian: no instant snaps and no thrust from aiming.
- **THRUST (right thumb):** hold to fire the main engine. **RETRO** (60%
  reverse) sits next to it.
- **FIRE:** hold to shoot. A setting adds **auto-fire at the nearest target
  within the aim cone** for players who want one less button.
- **Slingshot cue:** a gravity well's capture arc glows when your trajectory
  would slingshot. It's a skill aid that stays readable on a small screen.
- **"Classic" option:** rotate-left and rotate-right buttons plus THRUST,
  for players who want the original's feel.
- **Tilt:** not used (it hurts in bed or on transit, and it's bad for accessibility).

**Haptics** (toggle): light tick on firing, a heavy pulse on hull hits, a long
buzz when tethered, a rising buzz on a clean slingshot.

## Dock

- **Beat 1, align:** the same AIM stick lines up the nose. Hold THRUST to fly
  the ring line for bonus credits.
- **Beat 2, land:** tap **ALIGN** when the gauge is centred, then **hold
  BURN** for ~1.2 s. A radial fill ring shows the hold, graded SILK, FIRM or ROUGH.

## Corridor (virtual buttons, per Chris)

```
┌───────────────────────────────────────────────────────────┐
│ CHIPS 42  ×3 CHAIN  ★★☆                       [≡ PAUSE]   │
│                                                           │
│                    (platformer view)                      │
│                                              [ACTION]     │
│ ( floating MOVE stick / d-pad )          [SPRINT] [JUMP]  │
└───────────────────────────────────────────────────────────┘
```

- **MOVE:** floating stick. Horizontal deflection sets the run speed (with momentum and skid). Up and down climb ladders.
- **JUMP:** hold for height, tap for a hop. Coyote time and jump buffering are slightly
  more generous than on desktop, to cover touch latency.
- **SPRINT:** hold, unlocked by sustained running, as in the original.
- **ACTION:** one context button that replaces TALK, DOWN and E. Its icon changes
  to talk, pipe, shortcut or ladder depending on what you're near.
- Power-ups (Mag-Boots, Hardhat, Stim Soles) work automatically. No new buttons.

## HUD on a phone

- **Top bar only** in flight: hull, credits, sector, timer. Everything else
  appears on demand (tether warning, cargo status).
- **Bax strip** becomes a **collapsible pill** in the top-left. The typewriter
  speech balloon expands for each line, then auto-collapses. Tap it to replay
  the last line. Bax never covers the bottom thumb zones.
- **Diegetic degradation (kept):** flicker below 60% hull, scramble below 30%.
  **Rule:** anything the player must act on (JUMP ready, terminal prompts,
  prices, the alarm) never scrambles. Decorative readouts do.
- Minimum body text is 14 sp equivalent at the 1280×720 base. The CRT font gets a
  "clean" alternative in settings.

## Settings and accessibility (all in for 1.0)

| Setting | Options |
|---------|---------|
| Button layout editor | Drag, resize (75–150%), and adjust opacity for every touch control |
| Handedness | Mirror the layouts (stick on the right) |
| Flight scheme | Aim (default) / Classic |
| Auto-fire | Off / Assist |
| Haptics | Off / Light / Full |
| CRT intensity | 0–100% |
| Screen shake | 0–100% |
| HUD degradation | Full / Reduced (keeps the effect, lowers the intensity) |
| Font | CRT / Clean |
| Terminal keyboard | CRT keyboard / System keyboard |
| Visual audio cues | On/off (the Ch1 bit-crush and alarms also show on screen) |
