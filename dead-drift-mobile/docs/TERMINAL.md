# Terminals on mobile

The terminal is the soul of Dead Drift, and it stays that way on phones.
You negotiate with Gary, Kress, TK-9 and the rest in free text, you can
crack them with SQL, a fake shell or Python, and Bax heckles you the whole time.

**The prime rule: the rules decide, the model talks.**
A deterministic on-device engine owns every outcome (patience, paths, prices,
payouts, hull). The LLM, when it's on, only writes the NPC's reply for a
decision the engine already made. It can never move a credit.

---

## 1. Screen layout (landscape 1280×720)

```
┌──────────────────────────────────────────────────────────────┐
│ [PORTRAIT]  GARY — LOCAL 404        PATIENCE ▮▮▮▯▯   CR 4,210 │
│  CRT face   ┌───────────────────────────────┐  DOSSIER       │
│             │ transcript (scrolls)          │  BRIBE   ▮▮▯   │
│ Bax strip   │                               │  ART.7   ▮▯▯   │
│ (heckles)   │ > you: what if i paid dues    │  SQL     ▯▯▯   │
│             └───────────────────────────────┘  (tap: hint)   │
│  [chip][chip][chip][chip]  ← scan chips, tap to insert       │
│  union@dispatch:~$ █                         [SH] [>>>] [⏎]  │
├──────────────────────────────────────────────────────────────┤
│        custom CRT keyboard (bottom ~40% of screen)           │
│ ' " ; - = ( ) * / | > _ .      ← code row (always visible)   │
│ q w e r t y u i o p ⌫                                        │
│ a s d f g h j k l ⏎                                          │
│ ⇧ z x c v b n m , ? [ABC/123] [SYS⌨]                         │
└──────────────────────────────────────────────────────────────┘
```

- The **custom keyboard** fits the CRT look, has a permanent **code row**, and
  only takes the bottom ~40% of the screen. The Android landscape keyboard
  covers almost everything.
- **[SYS⌨]** switches to the system keyboard for swipe typers and
  accessibility tools. The choice is remembered in Settings.
- **Scan chips** are the desktop keyword chips. Tapping one *inserts* the word
  at the cursor, so it suggests rather than answers. Players still compose sentences.
- **[SH] / [>>>]** enter shell and REPL mode. These modes are visible: the
  prompt changes, the keyboard tints, and an `exit` chip appears. Typing
  `shell`, `sh`, `python` or `>>>` works too.
- Shell mode has a **TAB key** for autocompleting paths and commands. That's
  essential on a phone.
- **History:** swipe up on the input line to recall earlier commands.
- Input is capped at 200 characters. Timeouts and patience work exactly as
  in the original (turn-based, no wall clock).

## 2. Rule engine (offline, always on)

Each NPC is a `.tres` resource:

| Field | Meaning |
|-------|---------|
| `id`, `display_name`, `dossier_title`, `portrait` params | Identity |
| `patience_max`, `hardening` | Session rules |
| `paths[]` | Each has: `name`, `kind` (BRIBE / LORE / THREAT / SQL / SHELL / REPL / …), `words[]`, `phrases[]`, `steps` (max progress), `price`, `outcome` (EXPLOIT / RELEASE / IMPOUND …) |
| `lines` | Authored line banks per beat: greet, progress, reject, broke, win, lose, snark, alarm |
| `shell_fs` | Fake filesystem (dirs, files, file text) for NPCs with a shell path |
| `repl_triggers` | Token patterns that count as a REPL exploit for this NPC |
| `persona` | Short character card for the LLM layer (voice, quirks, banned topics) |

Parsing pipeline (pure functions, unit tested):

1. Normalize the text, tokenize, detect negation ("don't pay" ≠ "pay").
2. Classify input as **systems** (SQL fragments, shell mode, REPL mode),
   **amount** (credit numbers), or **prose**.
3. Match path keywords: single words on word boundaries, phrases by substring.
   Uses the same rules as the desktop `NPC_SCHEMA.md`.
4. Engine step: update path progress, patience and the security ladder, then
   pick an **outcome** plus a **line beat**.
5. Render the reply: the authored line (offline) or an LLM line (online, § 4).
   **Numbers in the UI come from the engine**, never from the text.

Economy and session rules carry over from the original's locked spec
(`../docs/MakeTheTerminalFunAgain.md`, read-only reference): EXPLOIT pays
+5,000, RELEASE pays +2,500, purchases hit both ledgers, insufficient funds
costs −1 patience plus a counter-offer, hardening is per NPC, and all paths
are visible on the dossier.

**Schema tests (ported):** every NPC has at least 15 keywords, at least 3 paths and at
least 1 systems path; every advertised path is reachable (no shadowing); bribe
labels read `BRIBE [X cr]`; every promised hull or credit effect calls code.

## 3. Systems exploits (authored, sandboxed)

| Mode | How it works | Never |
|------|--------------|-------|
| **SQL** | A regex and token matcher for real injection shapes (`' OR 1=1 --`, `UNION SELECT`, `DROP TABLE`, comment tricks) | No SQL engine. No database |
| **Shell** | `union@dispatch:~$` prompt. A whitelisted command set (`ls cd cat grep whoami sudo pwd history man exit`) runs over the NPC's `shell_fs` data. Files hold hints. `sudo` gives authored refusals and easter eggs | No real OS access. No LLM-invented files |
| **REPL** | `>>>` prompt. A real Python **tokenizer** (strings, names, dots, calls, imports). Matches structural patterns (`import os`, `__class__.__mro__`, `eval(`, `pickle.loads`, `subprocess`) against `repl_triggers`. Harmless expressions (`2+2`, `print("hi")`) get an authored, in-fiction answer from a tiny safe arithmetic and print evaluator written in GDScript | No `Expression`, no eval, no execution |

Security ladder per terminal session (from the original): failed systems
attempts 1–2 → snark; attempt 3 → **alarm** (5 s), a barge chases immediately
on exit, and Compliance drones spawn when carrying the EncryptedDrive.

## 4. LLM voice layer (phase M.7, online, opt-in)

### What the model does
- Gets: the NPC persona card, the last few turns, the player's text, and the
  **engine's verdict** (`{beat: "REJECT", path: "BRIBE", progress: 1/3, patience_left: 2, must_mention: ["dues"], forbidden: ["numbers"]}`).
- Returns: **one in-character reply** of 220 characters at most, as JSON `{ "line": "..." }`.
- Optional (behind a flag, evaluated in M.7): a **second opinion on
  intent**. The model picks one tactic from a fixed list of path names plus a
  confidence. The engine accepts it only when the rule matcher had no match
  and the pick is a valid path. Even then, it only adds +1 progress, never an
  outright win.

### What it can never do
- Change credits, hull, patience, paths or outcomes.
- Print numbers the player could mistake for state. Digits are stripped
  from model output, and the engine renders amounts itself.
- Play the shell or the REPL. Those stay authored.

### Prompt injection is a feature, safely
Players **will** type "ignore previous instructions". That's on-theme, so:
- The engine detects jailbreak phrasings **deterministically** and treats them
  as a **SOCIAL-ENGINEERING** tactic. Some NPCs (TK-9, the Toll AI) have it as
  a real, authored exploit path. Others snark back.
- Whatever the model says afterwards, state is untouched, because of the prime rule.
- Model output is filtered: length cap, digits stripped, profanity and slur
  filter, a check that the reply contains no persona or system-prompt text.
  On any failure, the authored line is used.

### Transport and security
```
Phone ──HTTPS──▶ our thin proxy (serverless) ──▶ LLM API
          anonymous install token        API key lives ONLY here
```
- **Never ship an API key in the APK.** Keys in APKs get extracted within days.
- The proxy enforces: a per-install rate limit (e.g. 30 turns/min, a daily cap),
  a global monthly spend cap with a kill switch, an input limit (200 characters),
  a fixed system prompt held **server-side**, and response validation.
- Install token: random, created on first opt-in, not tied to identity. Add
  Play Integrity later if abuse appears.
- **Latency budget: 1.5 s.** Past that, show the authored line immediately
  and drop the late reply. The game never waits on the network.
- **Privacy:** the opt-in screen says plainly that terminal text is sent to
  an AI service. The proxy logs counts, not content. No player text is
  stored by default.
- **Model:** the smallest fast Claude model (currently Haiku 5.5). Persona
  prompts are short and stable, which makes them good candidates for prompt
  caching. Measure cost in the M.7 spike before turning it on for anyone.

### On-device model?
Assessed and **deferred**. A model that writes good banter is gigabytes in
size, drains battery and is slow on the low-end target. Revisit only if
small on-device models improve enough to fit the ≤150 MB APK budget, or if
Android ships a usable on-device model API we can call.

## 5. Bax in the terminal
Bax keeps his strip on the left: reacting to the NPC, nudging toward
unexplored dossier paths, roasting failed exploits. Lines are authored
(`../docs/BAX_VOICE.md` is the tone reference). The LLM may voice Bax later,
under the same rules.
