#!/usr/bin/env python3
"""
DEAD DRIFT
God is dead, but the Repo Men still want your thrusters.
"""

# Epic 1.10 — the NLTK bootstrap is no longer blocking. The Game spins up
# a background thread for it as soon as pygame is initialised; the
# terminal layer falls back to regex tokenisation while the download is
# in flight, and a splash overlay handles the gap on the first opening.

if __name__ == "__main__":
    from core.game import Game
    Game().run()
