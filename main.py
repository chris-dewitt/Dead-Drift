#!/usr/bin/env python3
"""
DEAD DRIFT
God is dead, but the Repo Men still want your thrusters.
"""

import nltk

def _bootstrap_nltk():
    """Download required NLTK data on first run."""
    packages = [
        ("punkt_tab",                    "tokenizers/punkt_tab"),
        ("punkt",                        "tokenizers/punkt"),
        ("averaged_perceptron_tagger",   "taggers/averaged_perceptron_tagger"),
        ("vader_lexicon",                "sentiment/vader_lexicon"),
    ]
    for pkg, path in packages:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(pkg, quiet=True)

if __name__ == "__main__":
    _bootstrap_nltk()

    from core.game import Game
    game = Game()
    game.run()
