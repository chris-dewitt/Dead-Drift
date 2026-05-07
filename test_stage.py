#!/usr/bin/env python3
"""
DEAD DRIFT — Dev Stage Launcher
Run:  python test_stage.py
Lets you boot directly into any game state without going through main.py.
"""
import sys
import os

_MENU = [
    ("1", "Main Menu",            "menu",      0),
    ("2", "Loadout Draft",        "loadout",   0),
    ("3", "Flight  —  Sector 1",  "flight",    0),
    ("4", "Flight  —  Sector 2",  "flight",    1),
    ("5", "Flight  —  Sector 3",  "flight",    2),
    ("6", "Flight  —  Sector 4",  "flight",    3),
    ("7", "Flight  —  Sector 5",  "flight",    4),
    ("8", "Decanting Screen",     "decanting", 0),
    ("0", "Quit",                 "quit",      0),
]


def _print_menu():
    print()
    print("╔══════════════════════════════════╗")
    print("║   DEAD DRIFT  —  STAGE LAUNCHER  ║")
    print("╚══════════════════════════════════╝")
    print()
    for key, label, _, _ in _MENU:
        print(f"   [{key}]  {label}")
    print()


def _launch(mode: str, sector: int):
    # Flight and loadout don't need NLTK; terminal/full game does.
    # Skip bootstrapping for the fast paths so dev iteration is quick.
    if mode not in ("flight", "menu", "loadout", "decanting"):
        try:
            import nltk
            for pkg, path in [
                ("punkt_tab",                "tokenizers/punkt_tab"),
                ("punkt",                    "tokenizers/punkt"),
                ("averaged_perceptron_tagger","taggers/averaged_perceptron_tagger"),
                ("vader_lexicon",             "sentiment/vader_lexicon"),
            ]:
                try:
                    nltk.data.find(path)
                except LookupError:
                    nltk.download(pkg, quiet=True)
        except ImportError:
            print("  [warn] nltk not available — terminal NPC features disabled")

    from core.game import Game
    from core.state_manager import GameState

    _STATE = {
        "menu":      GameState.MAIN_MENU,
        "loadout":   GameState.LOADOUT_DRAFT,
        "flight":    GameState.FLIGHT,
        "decanting": GameState.DECANTING,
    }

    game = Game()
    game.run(start_state=_STATE[mode], start_sector=sector)


def main():
    _print_menu()
    while True:
        try:
            choice = input("   → ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            sys.exit(0)

        for key, label, mode, sector in _MENU:
            if choice == key:
                if mode == "quit":
                    print("bye")
                    sys.exit(0)
                print(f"\n   Launching: {label}\n")
                _launch(mode, sector)
                # After game closes, show menu again
                _print_menu()
                break
        else:
            print("   invalid — try again")


if __name__ == "__main__":
    main()
