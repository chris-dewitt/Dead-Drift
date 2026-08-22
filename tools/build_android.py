#!/usr/bin/env python3
"""
tools/build_android.py — Dead Drift Play-store APK / AAB wrapper.

Requires a host with the Android SDK + NDK (Buildozer downloads them
on first run). This environment does not ship a finished binary; it
produces a store-ready package when run on a build machine.

Usage:
    python tools/build_android.py           # debug APK
    python tools/build_android.py --release # release AAB (Play upload)
    python tools/build_android.py --apk     # release APK (sideload)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(cmd: list[str], *, label: str) -> None:
    print(f"\n{'─'*60}\n  {label}\n{'─'*60}")
    result = subprocess.run(cmd, cwd=_REPO)
    if result.returncode != 0:
        print(f"\n[android] FAILED: {label} (exit {result.returncode})")
        sys.exit(result.returncode)


def main() -> None:
    ap = argparse.ArgumentParser(description="Dead Drift Android builder")
    ap.add_argument("--release", action="store_true",
                    help="buildozer android release (AAB)")
    ap.add_argument("--apk", action="store_true",
                    help="buildozer android release with APK output")
    args = ap.parse_args()

    print("[android] Checking buildozer…")
    if shutil.which("buildozer") is None:
        print("[android] ERROR: buildozer not on PATH.")
        print("  pip install buildozer Cython")
        print("  Also install Android SDK/NDK deps — see docs/MOBILE_ANDROID.md")
        sys.exit(1)

    _run([sys.executable, os.path.join(_REPO, "tools", "make_android_icon.py")],
         label="Generate store icon")

    icon = os.path.join(_REPO, "assets", "android", "icon.png")
    if not os.path.isfile(icon):
        print(f"[android] ERROR: icon missing at {icon}")
        sys.exit(1)

    if args.release or args.apk:
        target = ["buildozer", "android", "release"]
        label = "Buildozer release"
    else:
        target = ["buildozer", "android", "debug"]
        label = "Buildozer debug APK"
    _run(target, label=label)

    bin_dir = os.path.join(_REPO, "bin")
    print(f"\n{'─'*60}")
    if os.path.isdir(bin_dir):
        artifacts = sorted(os.listdir(bin_dir))
        print("  ANDROID BUILD OUTPUT")
        for name in artifacts:
            path = os.path.join(bin_dir, name)
            size = os.path.getsize(path) / (1024 * 1024)
            print(f"  {name}  ({size:.1f} MB)")
        print(f"  dir: {bin_dir}")
    else:
        print("  BUILD WARNING: bin/ not created — check buildozer log.")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
