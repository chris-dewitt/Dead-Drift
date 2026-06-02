"""
tools/build.py — Dead Drift release build script.

Steps:
  1. Verify dependencies (PyInstaller, pygame-ce, numpy, nltk)
  2. Run tools/bundle_nltk.py to populate assets/nltk_data/
  3. Run PyInstaller with dead_drift.spec
  4. Report output path and sanity-check the executable exists

Usage:
    python tools/build.py [--skip-nltk] [--clean]

Options:
    --skip-nltk   Skip NLTK bundling (use when assets/nltk_data/ is already
                  populated and you want a faster rebuild)
    --clean       Delete dist/ and build/ before building
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC      = os.path.join(_REPO_ROOT, "dead_drift.spec")
_DIST_DIR  = os.path.join(_REPO_ROOT, "dist", "Dead Drift")


def _run(cmd: list[str], *, label: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"{'─'*60}")
    result = subprocess.run(cmd, cwd=_REPO_ROOT)
    if result.returncode != 0:
        print(f"\n[build] FAILED: {label} (exit {result.returncode})")
        sys.exit(result.returncode)


def _check_dep(module: str, install_hint: str) -> None:
    try:
        __import__(module)
    except ImportError:
        print(f"[build] ERROR: '{module}' not found. Install with: {install_hint}")
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Dead Drift release builder")
    ap.add_argument("--skip-nltk", action="store_true",
                    help="Skip NLTK bundle step (assets/nltk_data/ already populated)")
    ap.add_argument("--clean", action="store_true",
                    help="Delete dist/ and build/ before building")
    args = ap.parse_args()

    # ── Dependency checks ─────────────────────────────────────────────────
    print("[build] Checking dependencies…")
    _check_dep("PyInstaller", "pip install pyinstaller")
    _check_dep("pygame",      "pip install pygame-ce")
    _check_dep("numpy",       "pip install numpy")
    _check_dep("nltk",        "pip install nltk")
    print("[build] Dependencies OK")

    # ── Optional clean ─────────────────────────────────────────────────────
    if args.clean:
        for d in (os.path.join(_REPO_ROOT, "dist"),
                  os.path.join(_REPO_ROOT, "build")):
            if os.path.isdir(d):
                print(f"[build] Removing {d}")
                shutil.rmtree(d)

    # ── NLTK bundle ────────────────────────────────────────────────────────
    if not args.skip_nltk:
        _run(
            [sys.executable, os.path.join(_REPO_ROOT, "tools", "bundle_nltk.py")],
            label="Step 1/2 — Bundle NLTK data",
        )
    else:
        print("[build] --skip-nltk: skipping NLTK bundle step")

    # ── PyInstaller ────────────────────────────────────────────────────────
    _run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", _SPEC],
        label="Step 2/2 — PyInstaller",
    )

    # ── Verify output ──────────────────────────────────────────────────────
    exe_name = "Dead Drift.exe" if sys.platform == "win32" else "Dead Drift"
    exe_path = os.path.join(_DIST_DIR, exe_name)

    print(f"\n{'─'*60}")
    if os.path.isfile(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"  BUILD SUCCESS")
        print(f"  Executable : {exe_path}")
        print(f"  Size       : {size_mb:.1f} MB")
        print(f"  Output dir : {_DIST_DIR}")
    else:
        print(f"  BUILD WARNING: expected executable not found at:")
        print(f"  {exe_path}")
        print(f"  Check dist/ for actual output.")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
