from __future__ import annotations
import random
from dataclasses import dataclass


@dataclass
class FuelMix:
    name:         str
    description:  str
    force_mult:   float    # thruster force multiplier
    duration:     float    # seconds
    side_effect:  str      # flavor / system impact description


# Ingredient pools — sourced from engine coolant and alien flora
_COOLANTS   = ["green coolant", "blue coolant", "residual plasma", "reactor runoff"]
_FLORA      = ["starweed", "void-lichen", "neon cactus extract", "quantum spore dust"]

# Known stable recipes
_RECIPES: dict[frozenset, FuelMix] = {
    frozenset({"green coolant", "starweed"}): FuelMix(
        name        = "The Mellow Drift",
        description = "Smooth burn, extended glide. Almost legal.",
        force_mult  = 1.3,
        duration    = 12.0,
        side_effect = "HUD gains faint green tint for duration.",
    ),
    frozenset({"blue coolant", "void-lichen"}): FuelMix(
        name        = "Void-Slick No. 7",
        description = "Dangerous. Thruster burns cobalt blue. Bax disapproves.",
        force_mult  = 1.9,
        duration    = 6.0,
        side_effect = "Heat generation doubles. Hull takes 5 damage on ignition.",
    ),
    frozenset({"residual plasma", "quantum spore dust"}): FuelMix(
        name        = "The Schrödinger Blend",
        description = "Physics engine briefly confused about your position.",
        force_mult  = 2.4,
        duration    = 4.0,
        side_effect = "Ship blinks between two positions every 0.5s for duration.",
    ),
    frozenset({"reactor runoff", "neon cactus extract"}): FuelMix(
        name        = "Bad Decision Juice",
        description = "Bax refuses to acknowledge he made this.",
        force_mult  = 3.0,
        duration    = 3.0,
        side_effect = "30% chance of instant thruster failure on mixing.",
    ),
}


class Mixologist:
    """
    Bax's remnant bartender subroutines.
    Brews volatile concoctions from engine coolant and alien flora.
    """

    def __init__(self):
        self._unlocked_recipes: set[frozenset] = set()
        # Start with the basic recipe
        self._unlocked_recipes.add(frozenset({"green coolant", "starweed"}))

    def brew(self, ingredient_a: str, ingredient_b: str) -> FuelMix | None:
        key = frozenset({ingredient_a.lower(), ingredient_b.lower()})

        if key not in self._unlocked_recipes:
            return None   # recipe not known yet

        mix = _RECIPES.get(key)
        if mix is None:
            return self._improvised_mix(ingredient_a, ingredient_b)

        # Bad Decision Juice failure chance
        if mix.name == "Bad Decision Juice" and random.random() < 0.3:
            return FuelMix(
                name        = "Catastrophic Failure",
                description = "Bax: 'I TOLD YOU MATE.'",
                force_mult  = 0.0,
                duration    = 8.0,
                side_effect = "Thruster offline for 8 seconds.",
            )

        return mix

    def unlock_recipe(self, ingredient_a: str, ingredient_b: str):
        self._unlocked_recipes.add(frozenset({ingredient_a, ingredient_b}))

    def level_up(self):
        """Unlock all recipes — called when Bax's subroutines level up."""
        for key in _RECIPES:
            self._unlocked_recipes.add(key)

    @property
    def known_recipes(self) -> list[str]:
        return [_RECIPES[k].name for k in self._unlocked_recipes if k in _RECIPES]

    def _improvised_mix(self, a: str, b: str) -> FuelMix:
        return FuelMix(
            name        = f"Mystery Blend ({a[:4]}+{b[:4]})",
            description = "Bax has no idea what this will do. Neither does the physics engine.",
            force_mult  = random.uniform(0.5, 2.5),
            duration    = random.uniform(2.0, 10.0),
            side_effect = "Random HUD glitch.",
        )
