from __future__ import annotations


_CARGO_KEYS = ("archive", "shrooms", "paperwork", "vip")


def cargo_key_from_context(ctx: dict | None) -> str | None:
    """Return a normalized cargo key for terminal dialogue flavor."""
    if not ctx:
        return None

    text = " ".join(
        str(ctx.get(key, ""))
        for key in ("cargo_type", "cargo_name", "cargo_label", "cargo_state")
    ).lower()

    if "acoustic" in text or "archive" in text:
        return "archive"
    if "shroom" in text or "spore" in text or "epistemological" in text:
        return "shrooms"
    if "paperwork" in text or "form" in text or "telepathic" in text:
        return "paperwork"
    if "schrodinger" in text or "schroedinger" in text or "vip" in text:
        return "vip"
    if ctx.get("cargo_state") in {"alive", "deceased", "unobserved"}:
        return "vip"

    return None


def cargo_line_for(npc_name: str, ctx: dict | None) -> str | None:
    """Cargo-specific NPC flavor, keyed by the NPC display name."""
    cargo_key = cargo_key_from_context(ctx)
    if cargo_key not in _CARGO_KEYS:
        return None

    npc_key = _normalize_npc_name(npc_name)
    return _NPC_CARGO_LINES.get(npc_key, {}).get(cargo_key)


def _normalize_npc_name(npc_name: str) -> str:
    normalized = " ".join(str(npc_name).upper().replace("_", " ").split())
    return _NPC_ALIASES.get(normalized, normalized)


_NPC_ALIASES = {
    "CARGO INSPECTOR": "INSPECTOR HOLT",
    "INSPECTOR": "INSPECTOR HOLT",
    "FELIX": "RELAY-7 FELIX",
    "RELAY 7 FELIX": "RELAY-7 FELIX",
    "SYNTHETIC DROID": "TK-9",
    "UNION DISPATCHER": "DISPATCHER",
    "PIRATE": "KRELLBORN",
    "UNDERGROUND DJ": "MARROW",
    "INSURANCE ADJUSTER": "MORWENNA",
}


_NPC_CARGO_LINES: dict[str, dict[str, str]] = {
    "GARY": {
        "archive": (
            "And that Acoustic Archive on your manifest? Keep it quiet; I used to "
            "play sax at depot before Blevins turned music into a write-up."
        ),
        "shrooms": (
            "Those epistemological shrooms are pinging my scanner funny; last spore "
            "case made a trainee argue with his own reflection for six hours."
        ),
        "paperwork": (
            "Sentient paperwork in the hold? Mate, my office still has forms that "
            "whisper my divorce back at me."
        ),
        "vip": (
            "That Schrodinger VIP box is on the watch list; Local 404 says not to "
            "observe it, which is exactly the kind of instruction that ruins my night."
        ),
    },
    "KRESS": {
        "archive": (
            "Acoustic Archive, yes? I moved one crate like that through Ceres; half "
            "the miners cried and the other half tried to steal it."
        ),
        "shrooms": (
            "Epistemological shrooms. Very expensive, very illegal, very bad for men "
            "who already ask too many questions about reality."
        ),
        "paperwork": (
            "Sentient Paperwork is not joke cargo. I once forged a form that forged "
            "me back. We are still legally cousins."
        ),
        "vip": (
            "Schrodinger VIP. Old rich people love becoming physics problem, then "
            "billing the courier for interpretation."
        ),
    },
    "SANDRA": {
        "archive": (
            "The Acoustic Archive is delicate. I carried one once with zero static, "
            "zero clamp marks, and a delivery receipt you could frame."
        ),
        "shrooms": (
            "Epistemological Shrooms on your mass profile. Charming. Try not to let "
            "the cargo philosophize your steering into a wall."
        ),
        "paperwork": (
            "Sentient Paperwork. Of course. Even your cargo found a way to be late, "
            "combative, and badly filed."
        ),
        "vip": (
            "A Schrodinger VIP. I delivered a non-quantum dignitary once. They were "
            "still somehow less decisive than your passenger."
        ),
    },
    "TK-9": {
        "archive": (
            "MANIFEST NOTE: Acoustic Archive detected. Copyright enforcement dormant. "
            "Loyalty subroutine: I hope the old songs survive."
        ),
        "shrooms": (
            "MANIFEST NOTE: Epistemological Shrooms detected. Reality confidence "
            "lowered to 61 percent. Compliance remains mandatory."
        ),
        "paperwork": (
            "MANIFEST NOTE: Sentient Paperwork detected. This unit is experiencing "
            "sympathy for documents. Error. Continue compliance."
        ),
        "vip": (
            "MANIFEST NOTE: Schrodinger VIP detected. Passenger status cannot be "
            "verified. Loyalty subroutine: maybe let them sleep."
        ),
    },
    "DISPATCHER": {
        "archive": (
            "Your Acoustic Archive generates three cultural-property forms, two "
            "contraband forms, and one form about why those forms disagree."
        ),
        "shrooms": (
            "Epistemological Shrooms require a perception hazard addendum. I filed "
            "one in '42 and I still cannot prove I stopped filing it."
        ),
        "paperwork": (
            "Sentient Paperwork is the only cargo category that files back. I find "
            "that personally threatening."
        ),
        "vip": (
            "A Schrodinger VIP creates an ownership state problem, a passenger state "
            "problem, and seventeen forms about observation liability."
        ),
    },
    "MORWENNA": {
        "archive": (
            "The Acoustic Archive is excluded under cultural-loss unless you can "
            "prove the blues were damaged after policy inception."
        ),
        "shrooms": (
            "Epistemological Shrooms are excluded under intoxication, biohazard, "
            "and one clause Gerald added after the ceiling incident."
        ),
        "paperwork": (
            "Sentient Paperwork is not covered if it signs its own denial. CLAIM-7 "
            "has opinions on this. I dislike them."
        ),
        "vip": (
            "Schrodinger VIP transit is governed by Clause 14-Q. It is not a good "
            "clause. It is merely the clause I have."
        ),
    },
    "TOLL AUTHORITY": {
        "archive": (
            "Acoustic Archive cargo gets no cultural discount. Last 'heritage' crate "
            "held six stolen harmonicas and a tax problem."
        ),
        "shrooms": (
            "Epistemological Shrooms do not waive the toll, even if they convince "
            "you the toll is a social construct. Fifteen hundred."
        ),
        "paperwork": (
            "Sentient Paperwork still pays transit levy. If it wants an exemption, "
            "it can queue like everybody else."
        ),
        "vip": (
            "VIP passenger, quantum or otherwise, does not qualify for diplomatic "
            "toll relief unless they are paying my mortgage."
        ),
    },
    "RELAY-7 FELIX": {
        "archive": (
            "Is that the Acoustic Archive? I know collectors. Respectful collectors. "
            "Mostly. We could maybe both benefit."
        ),
        "shrooms": (
            "Those Shrooms make relay maps disagree with themselves. I can still "
            "route you, I just need the map to stop looking back at me."
        ),
        "paperwork": (
            "Sentient Paperwork? Great. Great. If it asks, Felix is spelled with one "
            "x and no outstanding warrants."
        ),
        "vip": (
            "Schrodinger VIP cargo makes buyers nervous. Also sellers. Also me. I am "
            "already nervous, so that is saying something."
        ),
    },
    "INSPECTOR HOLT": {
        "archive": (
            "Acoustic Archive cargo requires an audio-material declaration, even if "
            "the music is historically priceless and emotionally inconvenient."
        ),
        "shrooms": (
            "Epistemological Shrooms require biohazard, psychoactive, and ontological "
            "classification codes. In that order, please."
        ),
        "paperwork": (
            "Sentient Paperwork may not complete its own declaration. I learned that "
            "during the Stapleford hearing."
        ),
        "vip": (
            "Schrodinger VIP manifests require passenger, parcel, and uncertainty "
            "classifications. I have separate boxes for all three."
        ),
    },
    "KRELLBORN": {
        "archive": (
            "Acoustic Archive in the hold. Old songs sell high past the gate; old "
            "songs also start fights. Both interest me."
        ),
        "shrooms": (
            "Epistemological Shrooms. Belt crews pay well for cargo that makes the "
            "walls confess. Dangerous thing to advertise."
        ),
        "paperwork": (
            "Sentient Paperwork is poor loot unless it can sign ransom notes. Can "
            "yours do that, courier?"
        ),
        "vip": (
            "A Schrodinger VIP is either ransom, corpse, or nothing at all. I like "
            "cargo with options."
        ),
    },
    "MARROW": {
        "archive": (
            "That Acoustic Archive is not cargo, pilot. That is memory with a handle. "
            "Get it through and I will play the sky clean for an hour."
        ),
        "shrooms": (
            "Epistemological Shrooms on the line. If the broadcast starts answering "
            "questions I did not ask, I am blaming your hold."
        ),
        "paperwork": (
            "Sentient Paperwork, huh? I once dated a permit clerk. Same energy, more "
            "paper cuts."
        ),
        "vip": (
            "Schrodinger VIP in transit. I will not ask if they are alive. Bad radio, "
            "worse manners."
        ),
    },
}
