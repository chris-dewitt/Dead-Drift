# -*- mode: python ; coding: utf-8 -*-
#
# dead_drift.spec — PyInstaller build spec.
#
# Prerequisites:
#   pip install pyinstaller
#   python tools/bundle_nltk.py      # populate assets/nltk_data/ first
#
# Build:
#   python tools/build.py            # recommended (handles pre-checks)
#   -- or --
#   pyinstaller dead_drift.spec
#
# Output: dist/Dead Drift/
#
# Notes on user data:
#   Save files (data/saves/) are written relative to the working directory
#   at launch time. On Windows, double-clicking the exe sets CWD to the
#   install folder, which is writable in a typical Steam / extracted-zip
#   install. For a future Steam release, migrate to %APPDATA%/Dead Drift/.

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

_HERE = os.path.dirname(os.path.abspath(SPEC))  # noqa: F821 — PyInstaller injects SPEC

# ── Data files bundled into the build ──────────────────────────────────────
datas = [
    # Fonts — required; game falls back to SysFont if missing but renders
    # with wrong metrics.
    (os.path.join(_HERE, "assets", "fonts"), os.path.join("assets", "fonts")),
    # Pre-fetched NLTK packages — populated by tools/bundle_nltk.py.
    # The bootstrap will fall back to a network download if this dir is
    # absent, so the build still works without it (just needs internet on
    # first launch).
    (os.path.join(_HERE, "assets", "nltk_data"), os.path.join("assets", "nltk_data")),
]

# ── Hidden imports ─────────────────────────────────────────────────────────
# PyInstaller's static analysis misses dynamic imports inside try/except
# blocks and NLTK's lazy-loading internals.
hidden_imports = [
    # NLTK core
    "nltk",
    "nltk.tokenize",
    "nltk.tokenize.punkt",
    "nltk.tokenize.destructive",
    "nltk.sentiment",
    "nltk.sentiment.vader",
    "nltk.tag",
    "nltk.tag.perceptron",
    "nltk.tag.sequential",
    "nltk.corpus",
    "nltk.corpus.reader",
    "nltk.corpus.reader.util",
    "nltk.data",
    # numpy internals vary by version; collect the submodules that numpy
    # itself uses internally so the frozen build doesn't crash on import.
    "numpy.core._multiarray_umath",
    "numpy.core._multiarray_tests",
    "numpy.lib.stride_tricks",
    # pygame-ce mixer internals
    "pygame.mixer",
    "pygame.font",
    "pygame.draw",
    "pygame.transform",
]

# Collect all nltk submodules to avoid subtle runtime AttributeErrors.
hidden_imports += collect_submodules("nltk")

# ── Analysis ───────────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(_HERE, "main.py")],
    pathex=[_HERE],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Dev / test deps not needed at runtime.
        "pytest",
        "py",
        "_pytest",
        "IPython",
        "ipykernel",
        "notebook",
        "matplotlib",
        "PIL",
        "tkinter",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # --onedir: binaries live alongside the exe
    name="Dead Drift",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,         # UPX can corrupt pygame / numpy DLLs — leave off
    console=False,     # no console window (windowed game)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",  # add when icon art is ready
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Dead Drift",  # output folder: dist/Dead Drift/
)
