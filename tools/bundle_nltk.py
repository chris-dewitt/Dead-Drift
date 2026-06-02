"""
tools/bundle_nltk.py — build-time NLTK data downloader.

Run this once before packaging (PyInstaller, zip, etc.) to pre-fetch
all NLTK packages the game needs into  assets/nltk_data/.  The game
reads from that directory first, so end-users never need a network
connection to use the terminal NLP layer.

Usage:
    python tools/bundle_nltk.py

Output:
    assets/nltk_data/
        tokenizers/punkt_tab/
        tokenizers/punkt/
        taggers/averaged_perceptron_tagger/
        sentiment/vader_lexicon/

Safe to re-run; already-present packages are skipped.
"""
from __future__ import annotations

import sys
import os
import zipfile

# Ensure repo root is on path so relative imports work when invoked directly.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from pathlib import Path

_BUNDLE_DIR = Path(_REPO_ROOT) / "assets" / "nltk_data"

_PACKAGES: tuple[tuple[str, str], ...] = (
    ("punkt_tab",                  "tokenizers/punkt_tab"),
    ("punkt",                      "tokenizers/punkt"),
    ("averaged_perceptron_tagger", "taggers/averaged_perceptron_tagger"),
    ("vader_lexicon",              "sentiment/vader_lexicon"),
)


def bundle() -> None:
    try:
        import nltk
    except ImportError:
        print("[bundle_nltk] ERROR: nltk not installed — run: pip install nltk")
        sys.exit(1)

    _BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    # Prepend our bundle dir so nltk.data.find checks it first.
    bundle_str = str(_BUNDLE_DIR)
    if bundle_str not in nltk.data.path:
        nltk.data.path.insert(0, bundle_str)

    all_ok = True
    for pkg, data_path in _PACKAGES:
        try:
            nltk.data.find(data_path)
            print(f"[bundle_nltk] {pkg:<36} already present — skip")
        except LookupError:
            print(f"[bundle_nltk] {pkg:<36} downloading …", end=" ", flush=True)
            ok = nltk.download(pkg, download_dir=str(_BUNDLE_DIR), quiet=True)
            if ok:
                # NLTK sometimes only writes a .zip without extracting it.
                # Extract so nltk.data.find can locate the directory form.
                _extract_if_zip_only(_BUNDLE_DIR, data_path)
                print("done")
            else:
                print("FAILED")
                all_ok = False
        except Exception as exc:
            print(f"[bundle_nltk] {pkg:<36} ERROR: {exc}")
            all_ok = False

    if all_ok:
        print(f"\n[bundle_nltk] All packages present in {_BUNDLE_DIR}")
    else:
        print("\n[bundle_nltk] Some packages failed — check network and retry.")
        sys.exit(1)


def _extract_if_zip_only(bundle_dir: Path, data_path: str) -> None:
    """If NLTK only wrote a .zip for data_path, extract it in-place."""
    target = bundle_dir / data_path
    if target.exists():
        return  # directory form already present
    zip_path = bundle_dir / (data_path + ".zip")
    if not zip_path.exists():
        # Check parent dir for the zip (e.g. tokenizers/punkt.zip).
        zip_path = target.parent / (target.name + ".zip")
    if zip_path.is_file():
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(str(target.parent))


if __name__ == "__main__":
    bundle()
