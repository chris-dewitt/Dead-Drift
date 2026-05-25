# THE ALIVENESS PUSH

**Branch:** `rhubarb/aliveness-push`
**Started:** May 25 2026
**Status:** Planning
**Scope:** Open-ended (no time cap)

---

## Vision

Dead Drift already has the bones: physics, NPCs, Bax, corridors, landing, meta-progression. This push is about making the world feel **lived in.** Every system gets the same treatment: it should reflect that there are other people in this universe, the player has a history, and the choices they make echo across runs.

The signature test for every item in this push: *does it make a returning player notice something they wouldn't have caught the first time?* If yes, it ships. If no, it's polish for polish's sake and we cut it.

**Theme keyword:** *witnessed*. The player should feel witnessed by the world — by Gary, by Bax, by the Union scanner, by the corridor lore. The universe notices them. That's what makes a run feel real.

---

## Sequence Strategy

**Bugs first, then features.** Land a clean baseline before stacking new systems on top. The eight phases below are roughly sequential — earlier phases unblock later ones.

| Phase | Theme | Order |
|-------|-------|-------|
| A | Foundation: cursor merge + critical bugs | 1 |
| B | NPC schema overhaul + new characters | 2 |
| C | Gameplay mechanics | 3 |
| D | Graphics & visual feedback | 4 |
| E | Story & world | 5 |
| F | Bax depth | 6 |
| G | Landing & corridor | 7 |
| H | Audio & soundtrack | 8 |

---

## Phase A — Foundation (Bugs + Cursor Sync)

### A.1 Merge cursor branches into main — [ ]
Bring `cursor/playtest-doc-updates-e5ad`, `cursor/improvement-plan-spec-52e5`, `cursor/soundtrack-master-plan-c565`, and `cursor/improvement-plan-doc-update-e5ad` into `main` so the cursor-only playtest findings + soundtrack plan are the new shared baseline. Resolve doc conflicts in favor of the most recent factual content; my Phase 1/2 status work and the cursor branch design locks should both survive.

### A.2 Shroom control inversion (Phase 0.6) — [ ]
Ch.2 cargo periodic control inversion not firing in play. Reproduce, trace `cargo.update` → `controls_inverted` → `_read_input`, confirm overlay + Bax line. See cursor branch 0.6 spec.

### A.3 Barge intercept = Gary / Union only (Phase 0.7) — [ ]
`run_manager.open_barge_terminal()` randomly assigns pirate/synthetic/insurance — wrong. Lock to Gary (or the new Union reps in B.6). Move pirate/DJ/fence to non-barge comm channels.

### A.4 Dock visuals = Union Local 404 + Gary (Phase 0.8) — [ ]
Landing Beat 2 dock master = Gary (or chapter-appropriate Union contact). Union amber palette, Local 404 signage, repo bay markers in background.

### A.5 Non-Union NPCs get distinct ship hulls (Phase 0.9) — [ ]
Pirates / Marrow / Kress / Sandra need their own in-flight silhouettes — not repo barges, not the courier wedge. Currently they're terminal-only.

### A.6 Ch.3 Paperwork corridor broken (Phase 0.10) — [ ]
Clerk dialog modal + no pause in DELIVERY locks input. Repro and fix per cursor branch spec.

### A.7 Harpoon visibility audit — [ ]
Player has never seen a harpoon in play. Audit `physics/tether.py` render path; confirm projectile + tether line thickness/contrast; add muzzle flash on barge; verify AIM warning beam is visible.

### A.8 Barge slowdown on bullet hit — [ ]
`RepoBarge.take_hit()` — apply brief velocity damp or speed clamp on each non-disruption hit so player can land follow-up shots. Currently hits don't slow them.

### A.9 Cockpit portrait glow verification (Epic 7.1) — [ ]
Doc claims healthy/warning/critical/panic glow tiers shipped, but flagged suspect by audit. Play-verify all 4 tiers visible; fix if not.

### A.10 NLTK lazy bootstrap (Epic 1.10) — [ ]
Move startup NLTK download to first-terminal-open trigger. Splash overlay + Bax line during wait. Boot to main menu instantly.

---

## Phase B — NPC Foundation

### B.1 NPC keyword/bribe schema — [ ]
Standardize every NPC:
- **Keywords:** minimum 15 accepted pickup words per NPC
- **Bribes:** consistent `BRIBE [X cr]` format (no vague verbs)
- **Exploits:** comparable count and difficulty across NPCs
- Build a single audit table in `docs/NPC_SCHEMA.md` showing current vs target

### B.2 Universal cheat code easter egg — [ ]
`fuck off` (case-insensitive) works on every NPC as guaranteed pass/escape. **Easter egg only:** never advertised in keyword hints, tutorial, README, docs, or in-game text. Players discover organically.

### B.3 Felix expansion — [ ]
Add to 15+ keyword baseline. `gossip` either works or is removed from any hint. Re-audit exploits.

### B.4 Krellborn rework — [ ]
Scarier tone. Keyword audit to 15+ baseline. Distinct pirate voice character — currently doesn't land as a threat.

### B.5 Dray rework — [ ]
- New portrait (current one is weak)
- Expanded lore/background
- `gripe` either works or is removed
- `bribed` → `BRIBE [X cr]` standardized format
- Push to 15+ keywords

### B.6 Two new Union barge riders — [ ]
Replace Gary monoculture in late sectors:
- **Idealist Union Rep** — true-believer, quotes Union charter unironically, talks "shared prosperity" while clamping your hull. Earnest, irritating to negotiate with.
- **Corrupt Union Rep** — crooked, organized crime ties, takes bribes but might rob you anyway. Different cynicism from Gary's.

Each needs: portrait, dialogue tree, 15+ keywords, exploits, bribe paths.

### B.7 NPC cross-references — [ ]
Characters mention each other in dialogue. Marrow plays unauthorized Gary training videos on her pirate station. Kress mutters about Sandra's "perfect record." Builds a web through casual mention.

### B.8 Bribe negotiation mini-game — [ ]
Bribes become 2–3 turn negotiations. Cheap NPCs accept low. Greedy ones counter-offer. Some refuse in character (*"I don't take bribes from Union men"* / *"…add another zero"*).

---

## Phase C — Gameplay Mechanics

### C.1 Speed-scaled collision damage — [ ]
Impact damage multiplies with relative velocity at moment of collision. Rewards speed management near obstacles; punishes throttle-mashing.

### C.2 Slingshot chains — [ ]
Successive slingshots within ~3s stack a multiplier (1.5× → 2.0× → 2.5×). Skilled players chain wells. High skill ceiling on existing mechanic.

### C.3 Sector escalation timer — [ ]
Every 30s in a sector, something escalates: another barge spawns, gravity wells intensify, scanner pings more often. Visible escalation cue. Forces forward momentum.

### C.4 Gravity well orbital bonus — [ ]
Orbit a well at the right velocity band for 3+ seconds → automatic slingshot multiplier. Rewards precision flying over brute force.

### C.5 Barge detection cone — [ ]
Visible amber sweep cone in `PATROL` state showing barge FOV. Functional (telegraphs detection range) and atmospheric.

### C.6 Debt timer with teeth — [ ]
Debt should *threaten*, not just tick. Every 500cr milestone closes off a skip option, adds a penalty event, or triggers a Bax line. Pick the cheapest version that lands.

### C.7 Cargo damage as cumulative penalty — [ ]
Every hit damages cargo by a percentage; on delivery, paid only for % surviving. Creates "deliver clean vs fast" tradeoff.

---

## Phase D — Graphics & Visual Feedback

### D.1 Progressive hull damage on ship sprite — [ ]
60% → cracks. 30% → sparks venting from thruster nozzle. 10% → broken antenna, atmosphere leak particles. Hull state readable at a glance without HUD.

### D.2 Barge spotlight cone — [ ]
Repo barge in PATROL casts swinging amber light cone. Atmospheric + functional (telegraphs C.5 detection range).

### D.3 Velocity chromatic aberration — [ ]
Subtle RGB split on screen edges at high speed; obvious at overdrive. Reinforces physical sensation of going too fast.

### D.4 Cockpit viewport cracks — [ ]
Heavy hits crack the cockpit window itself. Cracks expand with damage; repaired on next dock. Literal HP indicator framing player view.

### D.5 Per-theme skyboxes — [ ]
Each procedural sector theme gets a distinct background. Wreckage Belt = hull debris parallax. Frozen Trail = ice crystals. Flare Corridor = solar flares. Currently all sectors visually blur together.

### D.6 Scan pulse render — [ ]
`EVT_SCAN_PING` already fires — wire renderer. Expanding ring from off-screen point; if it touches you, brief UI ack: `[UNION PASSIVE SCAN — IDENTITY LOGGED]`.

### D.7 Alien sighting render — [ ]
`EVT_ALIEN_SIGHTING` already fires — wire renderer. Strange silhouette crosses sector at far edge. Bax has zero context: silence, or a single confused line. Builds intrigue across runs.

### D.8 Solar wind events — [ ]
Random pulses visibly push everything in one direction for ~5s. Subtle handling effect. Bax: *"Brace — flare's pushin'."*

### D.9 Debris wake physics — [ ]
Ship passing through debris field displaces chunks; they bounce off each other for a few seconds. Every run through a field looks different. Pure kinetic satisfaction.

---

## Phase E — Story & World

### E.1 Gary and Sandra history — [ ]
They were partners before Sandra became "gold standard." Gary resents her success. Sandra feels guilty. Fragments across Gary and Sandra terminal interactions + Bax gossip. Gives both characters texture beyond function.

### E.2 The debt-trap reveal — [ ]
Across runs, Bax progressively reveals that Nova Soma's interest rate is mathematically impossible to pay off. The system is built to perpetuate, not collect. Drip-feed via intercepted comms and Bax's darkening commentary. Cross-run state: tracked in `data/saves/lore_progress.json`.

### E.3 Kress owes you — [ ]
After a player successfully exploits Kress in a terminal, on a future run he tips you off (scrambled comms, deniable) about a barge patrol route. No fanfare. Payoff for players who've stuck around.

### E.4 Local 404 internal schism — [ ]
The new idealist (B.6) and corrupt (B.6) reps clash with each other. Play them right (specific keyword paths) → they pull each other off your case. Internal politics with mechanical consequence.

### E.5 Persistent NPC death — [ ]
First time you really screw an NPC (sell Marrow's broadcast location, leave Mira Voss for dead, etc.), they're gone from your runs forever. Replaced by a colder slot or silent gap. Persistence layer in `data/saves/npc_state.json`.
**Risk:** Changes meta-contract. Needs clear in-game warning when an irreversible choice is about to fire.

---

## Phase F — Bax Depth

### F.1 Silence breaker — [ ]
No notable event for 20+ seconds → Bax hums a fragment, makes an unprompted observation, or asks a rhetorical question. Stops quiet from feeling like dead air.

### F.2 Cargo opinions — [ ]
Bax has a take on every cargo type, said once per run on first mention. Biohazard: *"If that canister pops, I'm disconnecting."* Shrooms: delighted. Pharmaceutical: suspicious. One line per cargo, max cost to ship.

### F.3 Near-miss scaling commentary — [ ]
Bax reaction scales with how close the miss was. 40px: mild. 10px: alarmed. <5px: silence, then *"…don't do that again."* Proportional reactions make moments feel witnessed.

### F.4 Bax's harmonica — [ ]
At <10% hull, Bax plays a few notes on a procedural harmonica. Becomes the signature "you're about to die" sound. Delivers on the literal README pitch.

### F.5 Bax learns the player — [ ]
Tracks consistent behavior across runs (always bribe, always brute, always exploit). Develops opinions: *"You always go for the bribe. Wonder if you'll ever try somethin' different."* Stored in `data/saves/bax_observations.json`.

### F.6 Run-count NPC recognition — [ ]
After 3+ runs Gary recognizes the player. *"Oh. You again."* After 10: *"Look, you're just part of my quarterly projections now."* Quiet escalation per NPC.

### F.7 Sector theme entry commentary — [ ]
On first entry to each procedural theme, Bax has one observation. Frozen Trail: *"Instruments go funny out 'ere. It's the ice crystals. Or ghosts."* Junk Belt: *"I've got sentimental attachment to this trash. Don't ask."*

---

## Phase G — Landing & Corridor

### G.1 Gary at the dock — [ ]
Landing Beat 2 receiving officer = Gary (per Phase A.4). Sheepish, sighing, clipboard. *"Right. You made it. Again."* Ties the loop closed.

### G.2 Dock Control radio clearance — [ ]
Audio during approach: distorted Dock Control voice. Either clears you or flags an "account irregularity" that tightens the landing window. The Union watches even at the dock.

### G.3 Cargo offload glimpse — [ ]
2-second animation after touchdown: dock workers moving cargo. Cargo type visibly legible (hazmat for biohazard, careful handling for fragile). Delivery becomes tangible.

### G.4 Landing damage echo — [ ]
Dock with critical hull → sequence shows it: sparks, smoke, leaking atmosphere, dock crew physically backing away. Cinematic moment of "you barely made it."

### G.5 Per-chapter dock wind-down Bax — [ ]
Bax shifts tone in landing. Reflective. *"Sector four. Three left. You're gettin' good at this. ...Or unlucky."* Pacing change between flight and corridor.

### G.6 Corridor lore rooms — [ ]
One dead-zone room per chapter. No enemies. Wall notes, slumped body at a terminal, Nova Soma memo. Optional context for players who slow down.

### G.7 NPC corridor shortcuts — [ ]
One room per chapter has a side route cracked by a known NPC for a fee. 200cr skips a hard section. Kress's smells like engine oil. Marrow's leaves a flyer.

### G.8 Bax's corridor unease — [ ]
Bax is a ship system; the corridor is wrong for him. Coaching lines carry unease: *"Right, the good news is I can still reach you. Bad news is I don't like how."* Different register from flight.

### G.9 Cargo-affects-corridor mutators — [ ]
Hauling shrooms → walls visibly breathe/warp. Biohazard → periodic decon flashes blind player. Paperwork → misleading signs + dead-end doors. Cargo becomes corridor mutator.
**Risk:** Each cargo needs corridor overlay design + impl. Substantial.

### G.10 Corridor time-pressure variant — [ ]
Mutator or specific runs: visible threat (gas seeping in, station failing, dock closing). Trades explorer pacing for adrenaline. Forces secret-skip decisions.

---

## Phase H — Audio & Soundtrack

### H.1 Soundtrack implementation — [ ]
Build the music system from the cursor branch SOUNDTRACK_PLAN. Hybrid model: ambient pads + sci-fi film homages + recurring Bax hum motif. Accessibility-first (mixable, mutable, captioned cues).
**Risk:** Large audio engineering task. May warrant a sub-plan doc.

### H.2 Bax harmonica synth — [ ]
Procedural harmonica voice in `audio/synth.py` or `audio/voices.py`. Used by F.4. 2–4 phrases, each ~1.5s, bluesy in feel.

### H.3 Per-chapter music verification — [ ]
Doc says corridor music is partial. Verify each chapter has its track playing; fill gaps.

### H.4 NPC voice expansion — [ ]
New union reps from B.6 each need a voice profile in `audio/voices.py` distinct from Gary.

---

## Out of Scope (deferred)

- Epic 8.4 — Hardcore mode (post-this-push)
- Daily/weekly seeded challenges (infrastructure exists, content design deferred)
- Steam release prep
- Tutorial overhaul (current tutorial framework holds)

---

## Execution Plan

**Branch strategy:** single branch `rhubarb/aliveness-push` off the post-A.1 main.

**Commit strategy:**
- One commit per logical item, message format: `aliveness(X.Y): <item>`
- Per-phase summary commit when the phase closes
- Push after each commit so the branch stays live

**Tracking:**
- This document holds the canonical checkbox state
- `WORKING_ON.md` gets a row when a phase starts, removed when it closes
- `docs/DOCUMENTATION_STATUS.md` updated when each phase ships

**Verification:**
- Play-verify every visible item before checkboxing it (no doc-only ships)
- Each phase ends with a sync to local for Chris play-verify
- Items that fail play-verify get a `[~]` and a follow-up note

**Risk gates (revisit before starting):**
- E.5 (Persistent NPC death) — confirm UX before building persistence layer
- G.9 (Cargo corridor mutators) — confirm scope before building per-cargo overlays
- H.1 (Soundtrack implementation) — may need sub-plan; flag before starting

---

## Open Questions (for Chris, anytime)

- E.5 — what's the *first* irreversible choice we want to ship? (Marrow betrayal feels obvious.)
- G.9 — should we ship one cargo's corridor mutator first (proof of concept) before designing all three?
- H.1 — does the soundtrack push warrant pausing other phases, or interleave?
- Phase ordering — A → B → C confirmed; should D/E/F/G/H run strict-sequential or are some parallelizable?

---

**Status legend:**
- `[x]` shipped + play-verified
- `[~]` shipped but partial / failed play-verify
- `[ ]` not started
