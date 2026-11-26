# Content: loop, chapters, systems

The full loop from the original, everything back (Chris Q8), same pacing
(Q9). Mechanics are rebuilt for touch. Lore and characters stay the same.

## Run loop

| Layer | Mobile version |
|-------|----------------|
| Main menu | Resume (checkpoint) / Continue / New / Load slot. Tap targets |
| Loadout draft | Swipe cards: ship frame → thruster tier → cargo |
| 5 sectors | Flight → clear timer → JUMP opens the jump terminal → next sector |
| Mid-sector | Toll terminals, barge intercepts (Gary's comm **is back**), optional Kress call (K button) |
| Shops | After sectors 2 and 4. A black-market vendor with a card grid. Buying adds to meta debt |
| Chapter win | Dock (2 beats) → corridor (6–7 rooms, 2–3 min) → tally → payout |
| Death | Decanting invoice → menu. Retry the same sector next run |
| Meta | Debt, clone count, chapters 0–6, stepped death fees. Same rules as the original (Q20) |

**Interruption safety:** autosave on app pause, and resume into pause. A
terminal mid-conversation resumes with the full transcript.

## Chapters and cargo

| Ch | Cargo | Mobile treatment |
|----|-------|------------------|
| 1 | Acoustic Archive | Damage bit-crushes the audio, as in the original. **Plus a visual twin:** the HUD gets matching static and glitch bands, because many phone players play muted |
| 2 | Mycorrhizal Payload | Spore leak inverts controls. **Telegraphed:** a 1.5 s spore ring pulses around the AIM stick before the inversion, and the stick turns green while inverted. Inverting a touch stick with no warning feels like a bug, not a challenge |
| 3 | The Paperwork | **Redesigned (Q10).** See below |
| 4 | Schrödinger VIP | **Redesigned (Q10).** See below |
| 5 | Encrypted Drive (The Edge) | Pick it up in the corridor. Damage spikes the trace meter (a top-bar gauge). Compliance vessels hunt at thresholds. Works on touch as is |
| 6 | Encrypted Drive (Compliance) | 90 s server-room upload under alarms, plus the single auto-scroll chase room. Haptic pulse on each alarm wave |

### Ch3 — The Paperwork (redesign)

On desktop, filing popups interrupted flight. On a phone a modal popup
under fire is miserable. New design: **the clipboard.**
- Forms slide into a **slim clipboard panel on the right edge** (~22% width).
  Flight continues and the thrust and fire buttons shift left while it's open.
- Each form is **one gesture**: swipe to stamp APPROVED or DENIED, **trace**
  a signature squiggle, or tap a checkbox. You read a short, absurd field
  ("Reason for continued existence: ___") and pick the right stamp.
- A form ignored too long gets "escalated": a fine to meta debt plus a Bax
  line. Wrong stamps give small penalties, and the funniest ones give Bax lines.
- Rhythm: no more than one form at a time, and none while a barge is clamped
  or tethered.

### Ch4 — Schrödinger VIP (redesign)

On desktop, observation collapsed the payout. On mobile, observation is **a
deliberate touch act.**
- The VIP pod is a **sealed box icon** on the HUD. **Press and hold** it to
  peek. The camera dims, the box opens, and you see ALIVE or DEAD. That
  collapses the state and fixes the payout.
- Not peeking keeps the superposition bonus (a higher potential payout at
  delivery, risk unknown). Events tempt you to peek: the pod rattles, Bax
  begs, "MEDICAL ALERT?" flashes. Each one is a choice.
- Damage while unobserved shifts the hidden odds, and haptics hint at
  them (a weaker heartbeat buzz). Feel versus look is the mobile twist.

## Terminals and NPCs

Full roster, including Gary, TK-9, the Union Dispatcher, Kress, Morwenna,
Sandra, Krellborn, Marrow, the Toll Authority, Felix, Holt, Dray, Nova Soma
Collections, Mira Voss, Eddie, Vince, Chen, Bowen and the Lost Frequency.
Each is ported as data per TERMINAL.md and must pass the schema tests.
Lines are re-edited for phone-length reading (two short sentences at most per
beat). Their voices stay the same.

**Port order** (most important to the loop first): Gary → TK-9 → Kress →
Toll Authority → Union Dispatcher → Felix → Holt → the rest → Chen, Bowen,
Lost Frequency (Ch5/6).

## Shops

- Card grid of 6–8 items: hull, thrust boost, jammer, intel, cargo stabilizer,
  ammo, and so on. Tap to inspect, long-press to buy. Haptic plus a cash-register blip.
- Shows **both** ledgers: run credits spent **and** debt added. Honest numbers.

## Corridor

Same design as the original (themed rooms, mid-room checkpoints, branches,
secrets, NPC talk spots, stealth, ?-block power-ups, chip chains ×1→×5, style
stars, and an end tally screen). Rooms are rebuilt in Godot TileMap layers with
**touch-aware level design**: slightly wider platforms, no pixel-perfect
jumps, and more generous ledge grabs.

## Bax

Same character. Lines come from the tone reference in `../docs/BAX_VOICE.md`
and get re-recorded or re-authored for mobile. Harmonica at critical hull and
the post-campaign BAX'S TAPES jukebox both come back.
