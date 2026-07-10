"""
Terminal economy — Make The Terminal Fun Again, Phase J.1.

The terminal used to *lie about money*: NPCs said "two thousand credits, on
your tab" in prose while no code moved a single number. This module makes it
honest.

`TerminalEconomy` is a thin, injectable adapter the run manager hands to each
`Terminal`. NPCs never touch the wallet directly — instead they **stage a
transaction** (see `BaseNPC.stage_transaction`) when they author a priced
line, and the Terminal applies it here. Injection keeps this unit-testable
without spinning up a whole RunManager.

Locked economy rules (docs/MakeTheTerminalFunAgain.md §Locked economy):

    Kress intel / contraband ....... deduct run credits AND add meta debt
    Bribe (Gary/Felix/Holt/…) ...... deduct run credits AND add meta debt
    Mira paid repair (≥700cr) ...... deduct run credits ONLY (off-books medic)
    Terminal win — EXPLOIT ......... +5,000  (was 9,000)
    Terminal win — RELEASE ......... +2,500
    Insufficient funds ............. no charge; caller runs the counter-offer
"""
from __future__ import annotations

# Locked payout values (supersede the old hardcoded 9000).
EXPLOIT_PAYOUT = 5000
RELEASE_PAYOUT = 2500

# Contraband gameplay effects (J.1.4 hull/stim wiring).
EFFECT_REPAIR_25 = "repair25"   # Kress contraband hull patch
EFFECT_REPAIR_45 = "repair45"   # Mira medbay patch
EFFECT_STIM      = "stim"       # Kress stims → +1 harmonica heal charge


class TerminalEconomy:
    """Per-terminal wallet + ship adapter.

    Built by the run manager with small callables closing over its state so
    the money/ship logic stays in one place and this stays testable.
    """

    def __init__(self, *, get_credits, deduct_credits, add_debt,
                 repair, grant_harmonica):
        self._get_credits    = get_credits      # () -> int
        self._deduct_credits = deduct_credits   # (int) -> None
        self._add_debt       = add_debt         # (int, str) -> None
        self._repair         = repair           # (float) -> None
        self._grant_harmonica = grant_harmonica  # () -> None

    # -- wallet ---------------------------------------------------------
    def credits(self) -> int:
        return int(self._get_credits())

    def can_afford(self, amount: int) -> bool:
        return self.credits() >= int(amount)

    def charge(self, amount: int, *, dual_ledger: bool = True,
               label: str = "TERMINAL") -> bool:
        """Deduct `amount` run credits; if `dual_ledger`, also add it to meta
        debt (the "tab"). Returns False without touching anything when the
        player can't afford it — the caller runs the counter-offer path."""
        amount = int(amount)
        if amount <= 0 or not self.can_afford(amount):
            return False
        self._deduct_credits(amount)
        if dual_ledger:
            self._add_debt(amount, label)
        return True

    # -- gameplay effects ----------------------------------------------
    def apply_effect(self, effect: str | None) -> None:
        if effect == EFFECT_REPAIR_25:
            self._repair(25.0)
        elif effect == EFFECT_REPAIR_45:
            self._repair(45.0)
        elif effect == EFFECT_STIM:
            self._grant_harmonica()
