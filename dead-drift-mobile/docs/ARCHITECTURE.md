# Architecture

## Engine: Godot 4 (GDScript)

- Pin the **latest stable Godot 4.x** in `project.godot` at M.0. Don't upgrade mid-phase.
- **GDScript only.** Add native or GDExtension code only if profiling proves we need it.
- Android export uses the Gradle build template. Target the current Play API level, with minimum API 26 and arm64-v8a.
- Tests use **GUT** (Godot Unit Test), run headless in CI.

Why not stay on pygame-ce? On Android it's fragile: slow cold start,
touch latency, audio glitches, no real export pipeline. Godot gives us
batching, a GPU-backed canvas, audio buses with DSP effects, input
handling with safe areas, and one-click APK/AAB export.

## Display

| Setting | Value |
|---------|-------|
| Base viewport | 1280×720 |
| Stretch mode | `canvas_items`, aspect `expand` |
| Orientation | `sensor_landscape` (menus and terminals too) |
| Safe area | Every HUD and button anchor respects `DisplayServer.get_display_safe_area()` (notches, rounded corners) |
| Frame rate | 60 fps target. Physics runs at a fixed 60 Hz tick |
| Renderer | `gl_compatibility` (widest device support). Revisit `mobile` only if we need it |

Look: vector line art plus a CRT post shader (scanlines, slight barrel
distortion, chromatic fringe) that's cheap enough for low-end GPUs. A setting
can lower its intensity.

## Project layout (planned)

```
dead-drift-mobile/
  project.godot
  game/
    core/          # autoloads: GameState, RunState, MetaState, SaveService, Events, Settings
    flight/        # ShipBody, GravityWell, Barge, Tether, sector themes, hazards
    delivery/      # dock sequence, corridor platformer, rooms
    terminal/      # TerminalScreen, keyboard, rule engine, shell, repl, llm client
    npcs/          # one .tres resource per NPC (data, not code)
    bax/           # Bax strip, line banks, voice blips
    ui/            # menus, HUD, touch controls, settings
    audio/         # buses, music director, sfx
    content/       # chapters, sectors, shop items, cargo definitions (data)
  assets/          # art, fonts, audio (pre-rendered), shaders
  tests/           # GUT tests (NPC schema, economy, shell, repl, saves)
  tools/           # offline scripts (audio pre-render, data validators)
  docs/
```

**Data over code:** NPCs, sectors, shop items, cargo and corridor rooms are
resources or data files. Adding an NPC should mean writing data plus lines,
not a new script.

## Physics (flight)

- A custom `ShipBody` with semi-implicit Euler on a fixed tick. We don't use
  Godot's `RigidBody2D`, because hand-rolled physics keeps flight
  deterministic and tunable.
- Same rule as the original: **forces are accumulated, and only `integrate(dt)`
  applies `dt`.** Callers never multiply forces by `dt`.
- Starting tuning (from the original): `MAX_VELOCITY` 280 px/s, slingshot
  overdrive 420 px/s. Retune for the 1280-wide viewport during M.1.
- No drag. Gravity wells use an inverse-square force with a softening radius.

The corridor platformer uses its own kinematic controller (coyote time, jump
buffer, variable jump height), separate from flight physics.

## State and saves

- Autoloads: `MetaState` (debt, clones, chapters done), `RunState` (current run),
  `Settings`, `SaveService`, `Events` (signal bus).
- Saves are **JSON only**, written to `user://saves/slot_N.json` with a
  `schema_version` and a checksum for **corruption detection** (not
  anti-cheat). The write is atomic: write a temp file, then rename.
- **Autosave triggers:** every 25 s in flight, on every screen transition, and
  on `NOTIFICATION_APPLICATION_PAUSED` / `FOCUS_OUT` (incoming call, app switch).
  Resuming puts you back in the exact sector, in pause.
- Three campaign slots, as in the original.

## Performance budget (low-end target ≈3 GB RAM, mid-2020 GPU)

| Budget | Target |
|--------|--------|
| Frame time | ≤ 16.6 ms (≤ 8 ms of script) |
| APK size | ≤ 150 MB (no on-device LLM) |
| Cold start to menu | ≤ 3 s |
| Draw calls in flight | ≤ 150 |
| Battery | 30 min of play ≤ 8% on the test device |

## Security baseline

The project rule is "keep security in mind". These items apply from M.0:

1. **No secrets in the repo or the APK.** That covers API keys, keystores and
   signing passwords. The LLM key lives only on our proxy server (TERMINAL.md § LLM).
   Add a CI secret scan (gitleaks or similar) at M.0.
2. **Never run player text as code.** Don't use Godot's `Expression` class,
   `str_to_var` or `bytes_to_var_with_objects` on player input or save files.
   The shell and REPL are pure data matchers.
3. **Saves are untrusted input.** Parse JSON, validate every field against a
   schema, clamp numbers, and drop unknown keys. A malformed save loads a
   fresh state with a warning. It never crashes the game.
4. **Minimal permissions.** None at all until M.7. Then only `INTERNET`. No
   storage, location or contacts permissions, ever.
5. **Network.** Use HTTPS only (no cleartext traffic). Verify certificates
   (Godot default; never disable it). Cap the response size and enforce timeouts.
6. **Privacy.** Terminal text sent to the LLM is disclosed in-game. The LLM
   layer is opt-in, with a toggle. The proxy doesn't keep player text by default.
7. **Dependencies.** Pin the versions of Godot and every addon. Vendor addons
   into the repo, reviewed. No runtime plugin downloads.
8. **Release signing.** Keep the keystore outside the repo with a backup.
   Supply passwords to CI through encrypted secrets only.
