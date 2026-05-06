#!/usr/bin/env python3
"""
DEAD DRIFT
God is dead, but the Repo Men still want your thrusters.
"""

import nltk

def _bootstrap_nltk():
    """Download required NLTK data on first run."""
    for pkg in ("punkt", "averaged_perceptron_tagger", "vader_lexicon"):
        try:
            nltk.data.find(f"tokenizers/{pkg}" if pkg == "punkt" else f"sentiment/{pkg}" if "vader" in pkg else f"taggers/{pkg}")
        except LookupError:
            nltk.download(pkg, quiet=True)

if __name__ == "__main__":
    _bootstrap_nltk()

    from core.game import Game
    game = Game()
    game.run()
