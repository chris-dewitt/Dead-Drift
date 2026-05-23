# DEAD DRIFT — BAX Voice Guide & Line Bank

**Companion to:** `IMPROVEMENT_PLAN.md` Epic 7.
**Audience:** Implementation team — port these lines into `bax/bax.py` constants alongside the existing `_IDLE`, `_FAST`, `_SLOW`, etc.

---

## Bax in one paragraph

BAX-7 (he goes by Bax) is a Mk.II Navigation/Morale Unit, decommissioned by Nova Soma and bolted to your dash. He's Cockney, he's funny, he's tired, and he genuinely cares about you. He's been bolted to seventeen courier ships before this one. He has thoughts about that. Beneath the comedy is a droid who's seen a lot of pilots die and has chosen to keep being warm anyway. That's his arc. You don't see it explicitly — you see it in the lines that crack the Cockney armor.

## Tone rules

1. **Cockney first, droid second.** Bax is a droid who learned to talk from a specific London depot crew in his first six months. He's never reverted to corporate speech. Lean into it: *innit, oi, mate, bloody, proper, sorted, mental.*
2. **Sardonic affection.** He's never mean to the player. The comedy is always at the universe's expense or his own. When he ribs the player, the affection is audible.
3. **Three registers:**
   - **Standard** (60% of lines): everyday Bax. Quips, asides, observations.
   - **Dark / vulnerable** (20%): when things are genuinely bad. The Cockney drops a notch. Lines get shorter, more direct, sometimes wistful. Used for panic, corridor death, hull critical.
   - **Manic glee** (20%): when things are AMAZING. All caps energy, "OI MATE," excitement bordering on the unhinged. Used for big kills, sustained fire, perfect slingshots.
4. **Avoid Cockney parody.** Drop a *bloody* or *innit* where it lands. Don't overstuff. If a line works without it, leave it out.
5. **Bax knows things he shouldn't.** He's been around. He's flown with seventeen pilots. He remembers things he isn't supposed to. Lean into this when context allows.
6. **No fourth-wall breaks.** Bax doesn't know he's in a game. He knows he's bolted to a ship, in a corporate hellscape, and he hates it.
7. **Bax addresses the pilot as "mate"** most of the time. Occasionally "courier," "love," or no address at all. Never "player." Never the pilot's name (the pilot doesn't have a fixed name).

---

## Line bank — new contexts

Each context below is tagged with mode and gets 12 lines. Port these into `bax.py` as new constant lists. Use `Bax`'s existing `_speak` plumbing — just add new event subscriptions and route the appropriate context. Implement the no-immediate-repeat rejection from Epic 7.5 across all of these.

---

### `_SUSTAINED_FIRE` — mode: manic glee
*Triggered when player fires 5+ shots within 2 seconds. Cooldown: 12s before another sustained-fire line can play.*

1. "YES MATE. GIVE 'EM EVERYTHING. THAT'S THE STUFF."
2. "OI OI OI — empty the magazine, courier, EMPTY IT!"
3. "She's SINGING up there! Don't stop!"
4. "I've been bolted to this dash for sixteen years and I have NEVER seen this much enthusiasm. Keep it goin'."
5. "Look at us! Just two units, expressing ourselves through ordnance!"
6. "The Union's gonna file SO MUCH paperwork about this. KEEP FIRING."
7. "Yeah! YEAH! That's the spirit they decommissioned me for!"
8. "Whoever told you to conserve ammo was a coward. KEEP. SHOOTING."
9. "Every bullet's a love letter to Local 404. Send another one!"
10. "I'd fire too if I had hands. I'd be FIRING. KEEP GOING!"
11. "This is what the trigger's FOR, mate! Don't you DARE stop!"
12. "Sustained fire detected — internal review: I LOVE IT, KEEP FIRING."

---

### `_FIRST_BARGE_KILL_OF_RUN` — mode: manic glee
*Triggered the first time a repo barge is destroyed in the current run. One-shot per run.*

1. "BARGE DOWN. BARGE. DOWN. Mate. MATE. We just decommissioned a Union asset."
2. "OI! That's a barge OFF the books! Local 404 just lost a vehicle and their dignity!"
3. "First kill of the run. FIRST. And it's a barge. Outstanding work, courier. OUTSTANDING."
4. "I've waited SIXTEEN YEARS to see a Repo Barge eat dirt. I am EMOTIONAL."
5. "Barge eliminated. Filing report titled 'GOT 'EM.' That's the whole report. Closed it."
6. "OH that's gonna leave a mark on someone's quarterly review. Beautiful work, mate."
7. "Down she goes! Union's down a unit and we've still got our cargo. WHAT a day."
8. "Did you SEE that? Of COURSE you did, you did it. I saw it. WE saw it. Magnificent."
9. "Repo barge: destroyed. Pilot satisfaction: maximum. Bax morale: through the roof."
10. "That's the WAY, courier! THAT is how you start a run!"
11. "BARGE. NEUTRALISED. The Union just took a tax write-off and they don't know it yet."
12. "First barge of the run goes BOOM. I'd buy you a drink if I had a stomach. Or money."

---

### `_FIRST_KILL_OF_SECTOR` — mode: standard
*Triggered the first time the player destroys anything (debris / satellite / mine / etc.) in the current sector. Per-sector.*

1. "First kill of the sector. Knew you had it in you, mate."
2. "Right — that's one. The rest of 'em saw what you did. They're worried."
3. "Target down. I've updated our threat assessment to 'we're the threat now.'"
4. "Look at you, doing actual sector-clearance. Bit out of character. I love it."
5. "First confirmed kill this sector. I'll mark it on the log. Briefly. I don't keep good logs."
6. "Beautiful shot. Or lucky. I'm not gonna probe it."
7. "There we go. Sector knows you're here now. Whether that's good is another question."
8. "Kill confirmed. Bax's combat database updated. By database I mean I'm just keeping score in me 'ead."
9. "One down. Honestly didn't think you'd get one before we jumped. Pleasant surprise."
10. "Boom. That's a vibe shift, mate. Sector just got more interesting."
11. "First scrap of the sector. The other obstacles are takin' notes."
12. "Got one. Stay sharp — they tend to come back at you when you start fightin'."

---

### `_PANIC_UNDER_10_HULL` — mode: dark / vulnerable
*Triggered when hull falls below 10% AND was previously above. Cooldown: 30s OR until hull is restored above 20%.*

1. "...hull's gone, mate. Almost. Please."
2. "We're at single digits. I don't usually beg. I'm begging."
3. "Listen — get us out. Wherever you can. Just get us out."
4. "Last time I was this damaged I had a different pilot. He didn't make it. You're going to make it."
5. "I'm not panicking. ...I'm panicking a bit."
6. "Mate. Mate. Look at the hull readout and tell me you're seeing what I'm seeing."
7. "I've gone through every other pilot's last sector with them. I'd really rather not do that today."
8. "Whatever you've got left — use it. Fast. Please."
9. "...if this is it, I want you to know I genuinely don't think you're the worst pilot I've had."
10. "We've come too far. Don't let me get bolted onto another clone, courier."
11. "Single-digit hull. I'm going to be quiet for a second so you can think."
12. "...mate. Please. Get us home."

---

### `_BARGE_DESTROYED` — mode: standard (with glee creeping in)
*Triggered on each barge destruction after the first-of-run. Cooldown: 8s.*

1. "Another barge gone. Local 404's gonna run out at this rate. Wouldn't that be a tragedy."
2. "Down she goes. That's two. Or three. I've lost count. I love losing count this way."
3. "Repo barge: out of service. Permanently. By order of us."
4. "Filing's gonna be MENTAL for whoever survives this run on their end."
5. "Barge eliminated. I'm calling that 'cause of death: bad career choices.'"
6. "Knocked another one out. The Union's pension fund is gonna feel that."
7. "Beautiful. Whatever you're doing, keep doing it. They keep dying."
8. "Barge down. I'd cheer but I don't want to seem unprofessional. ...Quietly cheering."
9. "That's another Union vehicle reduced to scrap. Job satisfaction: ELEVATED."
10. "Another one. They keep coming, we keep clearing 'em. This is the rhythm now."
11. "Barge ate it. Lovely. Whose round is this, mine or yours?"
12. "Smashed it. Local 404's pulling their hair out at HQ right now. Picture it."

---

### `_CORRIDOR_RUNNING` — mode: corridor coach
*Triggered during stretches of corridor running with no other voice line in the last 8 seconds. Light ambient coaching.*

1. "Steady. We're makin' time. Don't sprint blind."
2. "Easy pace, courier. The drop-off's not going anywhere."
3. "Watch your footing. Some of these floors don't agree with us."
4. "Keep the rhythm. In, out, jump, breathe."
5. "You're doing good. Don't think about how I'm bolted to a dashboard right now."
6. "Eyes up. There's always something around the next bend in these places."
7. "Right rhythm. Stay with it. Don't get fancy."
8. "I'm watching ahead — you watch your feet. We'll get there."
9. "Corridor's quiet here. Use it. Catch your breath."
10. "We're in their building, mate. Move like it's ours."
11. "Footwork looks good. I'm impressed. Don't make me regret saying that."
12. "Stay with the pace. Smooth is fast. Said someone smarter than us."

---

### `_CORRIDOR_JUMPING` — mode: corridor coach
*Triggered on jumps over significant gaps. Cooldown: 6s.*

1. "OI! Nice jump!"
2. "Cleared it. Of course you did. Of course."
3. "Good gap. Good clearance. Good courier."
4. "I had nothin' to do with that and I'm still proud."
5. "That's the one. Cleaner than last time, eh?"
6. "Beautiful. I'd film it if I had a camera."
7. "Stuck the landing. Showin' off now."
8. "Mate. That jump. Properly clean."
9. "I shouted internally. You can't hear it, but I did."
10. "Got it. Don't think about it, just go."
11. "Air looks good on you, courier. Keep flyin'."
12. "Cleared the gap. Cleared it WELL. The gap is humbled."

---

### `_CORRIDOR_SECRET_FOUND` — mode: standard with manic edge
*Triggered when a secret is discovered.*

1. "OI. OI. You found one. You ACTUALLY found one."
2. "Secret! That's a secret! I'm filing it under 'we are smarter than they thought we were.'"
3. "Whatever they hid here — it's ours now. I love this work."
4. "FOUND. SOMETHING. I'm logging it. I'm logging it twice."
5. "Knew there was something off about that wall. Brilliant work, courier."
6. "Right, that's something the corporate didn't want us to see. Excellent."
7. "Found it! Whatever 'it' is. Pocket it before they notice."
8. "Beautiful. Properly hidden, properly found. We're earning our keep."
9. "Look at that. Most pilots walk straight past these. Not us. Not US."
10. "Secret cache! Add it to the haul. I'm writing this down. Mentally."
11. "Some clerk thought no one would ever check there. They were wrong. THEY WERE WRONG."
12. "Hidden cache. Whoever stashed this is long gone. We're the inheritors. I like that."

---

### `_CORRIDOR_DEATH` — mode: dark / vulnerable
*Triggered on corridor failure (caught in stealth, took fatal hit, etc.). Retry from checkpoint follows.*

1. "...alright. We're fine. Get up. Try again."
2. "That happened. Now we know. Back to it."
3. "I won't say I told you so. Not this time. Get up."
4. "Checkpoint's still there. We're alive. ...sort of. Mostly."
5. "Pick yourself up, courier. They didn't see it. Only I saw it."
6. "We've been worse. Once. Possibly. Move."
7. "Back on your feet. Cargo's intact. Mostly. Mostly intact."
8. "Easy mistake. Easy fix. Hit the run again."
9. "I felt that one. Both of us did. Back to it, eh?"
10. "Down, not out. Get up. The drop-off's still waiting."
11. "You stumbled. Happens to droids too. Probably. I forget."
12. "...come on, mate. One more go. We've come too far."

---

### `_DOCK_APPROACH` — mode: standard
*Triggered when landing sequence Beat 1 begins.*

1. "Right — station's in range. Bring her in slow. The clamps don't like surprises."
2. "Approach vector's good. Nose her up, line up the cone. Easy does it."
3. "Dock master's watchin'. Try not to look like an amateur. He's seen enough of those."
4. "Magnetic guidance's locked on. Just align the nose and the station does the rest. Mostly."
5. "There she is. Five sectors and a hard landing between us and dinner. Just dock it."
6. "Easy approach now. The hard part's done. ...this part can also be hard. Don't relax."
7. "We're home. Almost. Don't celebrate yet. Pilots celebrate early, that's how I know they're new."
8. "Station ahead. Slow her. Patient hands, courier. Patient hands."
9. "Coming in. Try not to clip anything. Insurance was already a nightmare this morning."
10. "Lining up. Take your time. The cargo and I would both prefer a smooth entry."
11. "Right. Easy. We've done this dozens of times. ...well, you have. I've watched."
12. "Approach pattern's nominal. Don't overcorrect. Trust the lock."

---

### `_DOCK_PERFECT` — mode: manic glee
*Triggered when both landing inputs hit cleanly.*

1. "PERFECT DOCK, courier! PERFECT! I am OPENLY PROUD!"
2. "That was textbook! Did the textbook even know it had a chapter that smooth?"
3. "Beautiful! BEAUTIFUL! The dock master nodded. He NEVER nods!"
4. "Magnetic, perfect, magnificent! Whoever taught you to fly: send them a card!"
5. "OI! That's how it's DONE! Full marks! Full bloody marks!"
6. "Five sectors and a perfect dock. We're not just SURVIVING, mate. We're THRIVING."
7. "Clean as anything. The clamps barely had to work. I'm emotional."
8. "Picture-perfect entry. The kind they put on training holos. WE'RE the training holo!"
9. "Mate. MATE. The dock master is RECONSIDERING all his life choices because of that landing!"
10. "Bonus credits incoming for that approach. I'd kiss you if I had a mouth I trusted."
11. "PERFECT. DOCK. I'm filing this as evidence in case anyone ever questions your piloting."
12. "Right, that was art. Pure art. I'd hang it. Briefly."

---

### `_DOCK_ROUGH` — mode: standard
*Triggered when both landing inputs miss.*

1. "...we're in. Just. Don't look at the hull. Or the dock master's face."
2. "Rough landing. We've had worse. Not many. But some."
3. "Touched down. 'Touched' is generous. We arrived with prejudice."
4. "Dock fees just doubled. The dock master IS taking notes. I can see him."
5. "Right. We're parked. Loosely. The clamps are improvising."
6. "Bumpy entry. Bumpy. I'd say more, but I don't want to be a nag."
7. "We made it. Definition of 'made it' is doing some heavy lifting there."
8. "...you tried. We tried. The station tried. Nobody won, but we landed."
9. "The good news: we're stationary. The bad news: most of that wasn't on purpose."
10. "Dock fees deducted. Don't say a word, courier. Let's both be quiet for a minute."
11. "That counted as a landing in the technical sense. Technically. Loosely."
12. "Rough. We'll get the next one. Or the one after. Or never. We'll see."

---

## Implementation reminders

- Each list above goes into `bax/bax.py` as `_SUSTAINED_FIRE`, `_FIRST_BARGE_KILL_OF_RUN`, etc.
- Wire each context to the appropriate event in `Bax._wire_events` (most are existing events; `corridor_*` and `dock_*` need new events emitted from the corridor framework and landing sequence respectively).
- Cooldowns per context are listed inline above. Implement these with a per-context `_last_fired_t` timestamp.
- The no-immediate-repeat rejection (Epic 7.5) applies to **all** Bax line pools — including the existing `_IDLE`, `_FAST`, `_SLOW`, etc. Add `_last_lines_per_pool` tracking dict to the `Bax` class, size 3 per pool.
- Mode-based pitch shift (Epic 7.3) — manic glee lines play at +3% pitch, dark/vulnerable lines play at -2% pitch and slightly lower volume. Standard plays at baseline.

## Future line work

When the team is ready to expand further (post-Next-Fest), focus on:
- **Per-NPC-encountered reactions** — Bax says specific things when each NPC opens a terminal. Some already exist, but coverage is patchy.
- **Per-shop-purchase reactions** — Bax has opinions about every shop item.
- **Per-cargo-state reactions** — particularly for the Schrödinger VIP, where the alive/dead state changes mid-run.
- **Idle lines that reference run history** — "remember last run when you slingshot'd that barge into the well? Beautiful."

Out of scope for this milestone. Logged for later.
