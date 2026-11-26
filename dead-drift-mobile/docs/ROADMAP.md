# THE MOBILE PUSH — Roadmap

**Started:** November 26 2026
**Status:** pre-production. Docs locked, M.0 next.
**North star for all agents working in `dead-drift-mobile/`.**

Each phase ends with a playable APK on a real device. One PR per phase
(split a large phase into sub-PRs if needed). Tick boxes here only.

---

## M.0 — Foundation
- [ ] Godot 4.x stable pinned. `project.godot`: 1280×720, `canvas_items` + `expand`, `sensor_landscape`, `gl_compatibility`
- [ ] Folder layout per ARCHITECTURE.md. Autoload stubs (`Events`, `Settings`, `SaveService`, `MetaState`, `RunState`)
- [ ] GUT installed (vendored, pinned). One passing test
- [ ] CI: headless test run and a debug APK export on push. Secret scan (gitleaks)
- [ ] `.gitignore` covers keystores, `export_presets` credentials and `.godot/`
- [ ] Hello-world APK runs on Chris's phone

## M.1 — Flight core
- [ ] `ShipBody` fixed-tick Newtonian integration (forces accumulated, `dt` only in `integrate`)
- [ ] Gravity wells, slingshot detection, overdrive cap
- [ ] Gun, debris, fuel canisters. One sector theme (wrecks)
- [ ] Barge state machine: patrol → chase → aim → intercept → clamp → torch. Tether spring and snap
- [ ] Tuning pass at 1280-wide (MAX_VELOCITY, overdrive)

## M.2 — Touch controls and HUD
- [ ] Floating AIM stick, THRUST, RETRO, FIRE, JUMP. Classic scheme option
- [ ] Safe-area anchoring. Top-bar HUD. Collapsible Bax pill (placeholder lines)
- [ ] Haptics service with the toggle
- [ ] CRT post shader with an intensity setting. Diegetic flicker/scramble with the "never scramble actionable text" rule
- [ ] Device test: latency feels good, no accidental gesture-edge triggers

## M.3 — Run loop and saves
- [ ] Menu → loadout draft → 5 sectors → chapter-complete stub → death invoice
- [ ] Meta state: debt, clones, stepped death fees
- [ ] JSON saves: schema-validated, atomic writes, 3 slots, autosave (25 s, transitions, app pause)
- [ ] Kill the app mid-sector and resume into pause at the same spot (device test)
- [ ] Save-fuzz tests: corrupt, oversized or hostile JSON loads a fresh state without crashing

## M.4 — Terminal core (offline)
- [ ] TerminalScreen layout. CRT keyboard with code row. System-keyboard toggle. Scan chips insert text
- [ ] Rule engine: normalize, negation, path matching, patience, hardening, outcomes. Economy rules (EXPLOIT 5k / RELEASE 2.5k / dual ledger / broke counter-offer)
- [ ] NPC `.tres` schema and a validator. Schema tests (≥15 keywords, ≥3 paths, ≥1 systems path, reachability, bribe label)
- [ ] Shell mode (whitelist commands over `shell_fs`, TAB complete, history). SQL matcher. REPL tokenizer plus pattern triggers (no eval, ever)
- [ ] Security ladder: alarm on the 3rd failed attempt, barge chase on exit
- [ ] Port **Gary**, **TK-9**, **Kress**. Jump terminal and toll wired into the loop

## M.5 — Delivery
- [ ] Dock: align beat (ring line bonus) and land beat (ALIGN + hold BURN, graded)
- [ ] Corridor controller (coyote, buffer, variable jump, sprint, ladders, ACTION context button)
- [ ] Room system plus Ch1 rooms (6–7), checkpoints, chip chains, stars, tally screen
- [ ] Payout card and debt adjustment

## M.6 — Full loop systems
- [ ] Shops (after sectors 2 and 4, dual-ledger display)
- [ ] Kress call (K), barge intercept comms with Gary, toll terminals mid-sector
- [ ] All 8 sector themes
- [ ] Cargo mechanics: Ch1 (with visual twin), Ch2 (telegraphed inversion), Ch3 clipboard, Ch4 hold-to-peek, Ch5 trace, Ch6 upload and chase room

## M.7 — LLM voice layer (opt-in)
- [ ] Spike: cost and latency per turn with the smallest fast Claude model. Go/no-go with Chris (set a budget cap)
- [ ] Serverless proxy: key server-side only, install tokens, rate limits, spend cap and kill switch, fixed server-side prompt, response validation, no content logging
- [ ] Client: 1.5 s budget with authored fallback, output filter (length, digits, leak check), opt-in screen with privacy text, Settings toggle
- [ ] Deterministic jailbreak detector, plus a SOCIAL-ENGINEERING path on TK-9 and the Toll AI
- [ ] Red-team pass: 50+ injection attempts. Confirm zero state changes from model output

## M.8 — Full roster and campaign
- [ ] All remaining NPCs ported in the CONTENT.md order, all passing schema tests
- [ ] Chapters 2–6 corridors. Full campaign playable start to finish
- [ ] Bax full line banks, harmonica heal, BAX'S TAPES unlock

## M.9 — Audio
- [ ] Offline render tool plus the procedural asset set
- [ ] Bus layout and DSP (hull low-pass, Ch1 crush, tape hum)
- [ ] Music director with 4 stem slots per chapter and placeholders. Recorded stems drop in whenever they're ready
- [ ] Visual and haptic twins for all critical cues

## M.10 — Polish and performance
- [ ] Performance budget met on the low-end device (frame time, start time, APK size, battery)
- [ ] Button layout editor, handedness mirror, all accessibility settings
- [ ] Full playthrough on 2+ devices (16:9 and 20:9)
- [ ] Distribution decisions revisited with Chris (monetization, analytics, store listing)
