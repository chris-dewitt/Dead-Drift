# Decisions log

**Locked:** November 26 2026, with Chris (answers to the pre-production questionnaire).
Change a locked item only with Chris's sign-off, and record the change here.

---

## Chris's answers

| # | Question | Answer | What it means for the build |
|---|----------|--------|-----------------------------|
| 1 | Rebuild or extend? | **New game, mobile only.** The original game stays untouched. | New directory `dead-drift-mobile/`, ready to split into its own repo. |
| 2 | Platforms | **Android only** | Build for Android first. No iOS-driven compromises. |
| 3 | Engine | **Open to anything** | **Godot 4** (see ARCHITECTURE.md). |
| 4 | Shared code? | **Completely separate**, up to a new repo | Nothing shared at runtime. Content gets re-authored, not imported. |
| 5 | Terminals on mobile? | **Yes** | Terminals are in, and they're a pillar. Input style picked below (D-1). |
| 6 | NLP stack | **LLM-ish, open to what works best** | Rule engine plus an optional LLM voice layer (D-2). |
| 7 | Coding exploits (shell/SQL/REPL)? | **Hell yes** | All three, with input designed for mobile (D-3). |
| 8 | Shops, Kress, barge comms | **All back** | The full loop, not a slice. |
| 9 | Session length (5 sectors → dock → 2–3 min corridor) | **Keep it** | Same pacing. Autosave covers interruptions. |
| 10 | Ch3 paperwork / Ch4 observation | **Redesign for mobile** | See CONTENT.md. |
| 11 | All 6 chapters at launch | **Yes** | The full campaign is the 1.0 target. |
| 12 | Flight controls | **Open, whatever works best on Android** | Aim stick plus thrust button by default (D-4). |
| 13 | Corridor controls | **Virtual buttons** | Floating left stick plus right-side buttons. No gamepad work is planned. |
| 14 | Orientation | **Landscape only** | `sensorLandscape`, including menus and terminals. |
| 15 | Accessibility (remap, resize, left-handed, haptics) | **Yes** | All four go in the settings menu. |
| 16 | UI | **Redesign for phones, keep the spirit** | A new phone-first layout with the same CRT and diegetic look. |
| 17 | HUD degradation (flicker/scramble) | **Keep** | Keep it, but tune for small screens. Text you need to act on never scrambles. |
| 18 | Audio | **Best for mobile, keep the vibe.** The soundtrack is still in progress. | A pre-rendered procedural palette plus empty stem slots (AUDIO.md). |
| 19 | Desktop ↔ mobile save sync | **Not yet** | Local saves only. |
| 20 | Debt/clone meta-progression | **Same as the original** | Same rules. |
| 21–24 | Monetization, analytics, release, devices | **Deferred** ("not worried about distribution yet") | Nothing gets wired in. The defaults below apply until Chris decides. |
| 25 | Docs | **New docs in a new directory or repo** | This folder. |

## Calls I made where Chris said "whatever works best"

| ID | Decision | Why |
|----|----------|-----|
| D-1 | **Terminal input is a hybrid.** A custom CRT keyboard with a code row, tappable keyword chips that insert text, and a toggle to switch to the system keyboard. | Free typing stays the soul of the terminal. Chips make it playable one-handed. The landscape system keyboard covers the whole screen. |
| D-2 | **The rules decide, the model talks.** An on-device rule engine owns every outcome. An LLM (optional, online) only writes NPC dialogue for an outcome the engine already chose. | Keeps the "numbers tell the truth" rule from the PC terminal push. Prompt injection can't break the economy. The game works offline. |
| D-3 | **Shell and REPL are authored and sandboxed, never real.** The shell runs a fake filesystem from data files. The REPL tokenizes real Python syntax and matches patterns. Nothing is ever evaluated. | "REAL syntax" without real execution. Never let the LLM play shell or REPL. |
| D-4 | **Flight uses an aim stick plus a THRUST button by default**, with a "classic" option (rotate buttons). | Newtonian flight needs separate heading and thrust. Twin-thumb fits landscape phones. |
| D-5 | **Godot 4, GDScript.** | Free, strong Android export, good 2D, fast iteration. C# on Android is still the less mature path. |
| D-6 | **Base viewport is 1280×720**, with an expanding aspect ratio for wider (20:9) phones. | Wider phones get more horizontal play space instead of black bars. |

## Defaults until distribution is decided (Q21–24)

- **No ads, IAP, analytics or crash SDKs.** The only permission is `INTERNET`, and only once the LLM layer ships.
- **Minimum is API 26 (Android 8)**, arm64 only to start. Test on one low-end phone (≈3 GB RAM).
- The keystore never enters the repo. Store a backup somewhere Chris controls.

## Design pillars

1. **Thumb-first, not shrunk-down.** Every screen is designed for two thumbs on a 6" landscape phone.
2. **The terminal is the soul.** It gets as much design effort as flight does.
3. **Honest numbers.** Credits, hull and debt shown on screen always come from game state, never from dialogue text.
4. **Interruptible.** A phone call or app switch never costs a run. Autosave on pause, resume exactly.
5. **Same spirit.** Bax, Gary, the Local 404, clone debt, lo-fi CRT. Darkly comic, never generic.

## Open questions (answer when ready, nothing is blocked yet)

1. **Working title:** "Dead Drift: Mobile", or a new name (it's a separate game)?
2. **LLM hosting budget:** what monthly cap is OK during testing? (The LLM layer is phase M.7, so this isn't urgent.)
3. **Separate GitHub repo:** create it now (Chris has to make it, since this session can't), or stay in a subdirectory until M.3?
4. **Content changes:** is the mobile campaign allowed to change story beats, or only mechanics?
