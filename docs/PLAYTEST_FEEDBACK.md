# DEAD DRIFT — Player Feedback Backlog

**Source:** Playtest session, May 25 2026
**Status:** Captured — NOT yet scheduled or implemented

---

## Combat / Barges

### Barge hit reaction
When the player hits a barge with a bullet, the barge should **slow down**
briefly so the player has a window to land another shot. Currently they keep
moving at full speed after the hit, making sustained fire frustrating.

### Harpoons must be visible
Player has never actually seen a harpoon during play. Either the visual is
too subtle, gets culled, or fires too fast to register. Need to:
- Audit the harpoon render path (`physics/tether.py` + renderer)
- Make sure the projectile + tether line are drawn with enough thickness /
  contrast / length to be obvious
- Possibly add a brief tracer / muzzle flash from the barge when it fires
- Verify the AIM warning beam is also visible (the precursor to the harpoon)

### Too many Garys — add 2 new union reps to barge rotation
Every barge ride being Gary is getting repetitive by the late sectors.
Add two new NPC riders to the pool:

1. **Idealist Union Rep** — true believer who thinks the megacorps are
   actually a force for good. Quotes the Union charter unironically. Talks
   about "shared prosperity" while clamping your hull. Probably annoying
   to negotiate with because he's earnest.

2. **Corrupt Union Rep** — crooked, possible ties to organized crime.
   Skims off the top, willing to take bribes but also might just rob you
   outright. Different vibe from Gary's bureaucratic cynicism.

Both need: portrait, dialogue tree, keywords, exploits, bribe paths if applicable.

---

## NPC Keywords / Negotiations — systemic issue

The codeword/keyword situation across NPCs is **inconsistent and often
impossible to guess.** Need a full evaluation pass.

### Goals
- Every NPC should have a **firm baseline number** of accepted pickup
  words, and that number should be **HIGH** (not 4–6, more like 15+).
  Player should rarely feel stuck guessing.
- All NPCs that accept bribes should use a **consistent format** showing
  the dollar amount they require, e.g. `BRIBE [200 cr]` not vague verbs.
- All keyword/exploit difficulty should be **comparable** across NPCs —
  no NPC should be wildly harder than the others to navigate.
- **Universal cheat code:** `fuck off` (or `FUCK OFF`) should work on
  every single NPC as a guaranteed escape / pass. Goofy panic button,
  in-character for the game's tone.

### Specific NPC issues

**Felix**
- Very hard to figure out how to get past him.
- Not enough keywords in the pool.
- `gossip` doesn't work — should it? Either add it or remove from any hints
  that suggest it.

**Krellborn**
- Needs to feel scarier. Currently doesn't land as a threatening pirate.
- Audit his keywords — same impossibility problem.

**Dray**
- Portrait is weak — needs a redo.
- Background / lore is thin — needs more substance.
- `gripe` doesn't work — same problem as Felix's gossip.
- `bribed` is not English — should be `bribe` (verb) or `BRIBE [X cr]`
  in the formatted style.
- Generally needs more content (dialogue, exploits, hooks).

---

## Resolved / Answered During Session

- **Debris cloud damage** — Confirmed NON-damaging. The damage the player
  took was from another source (asteroid, satellite, harpoon, gravity well).
  Debris cloud only reduces visibility (~6% alpha overlay).

---

## Implementation Notes (when this gets picked up)

1. The barge hit-slowdown is a small physics tweak in `RepoBarge.take_hit()`
   — apply a velocity damp or brief speed clamp.
2. New barge riders go in `terminal/npcs/` alongside Gary. They need to be
   added to the barge intercept rotation in `roguelite/run_manager.py` or
   wherever Gary is currently selected.
3. NPC keyword audit is best done as a spreadsheet pass: list every NPC,
   their current keyword count, bribe amount/format, exploit count. Then
   normalize.
4. Bribe format standardization: search for all bribe-related strings, pick
   one format (`BRIBE [X cr]` recommended), apply everywhere.
