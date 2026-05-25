#!/usr/bin/env python3
"""Epic 9.4 — scan player-facing strings for bland/generic copy."""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ["core", "roguelite", "terminal/npcs", "delivery", "ship", "bax", "renderer"]
SKIP = {"test_", "__pycache__", "ARCHIVED"}

GENERIC_PATTERNS = [
    re.compile(r"^(Error|Success|Failed|Loading|Please wait|Warning)\b", re.I),
    re.compile(r"^Press [A-Z] to", re.I),
    re.compile(r"^Click ", re.I),
    re.compile(r"^OK$", re.I),
]

def main() -> int:
    files: list[Path] = []
    for d in SCAN_DIRS:
        p = ROOT / d
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(p.rglob("*.py"))

    flags: list[tuple[str, str, str]] = []
    string_re = re.compile(r'["\']([^"\']{6,100})["\']')

    for fp in sorted(set(files)):
        if any(s in str(fp) for s in SKIP):
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in string_re.finditer(text):
            s = m.group(1)
            if s.startswith("_") or "\\n" in s and len(s) > 80:
                continue
            for pat in GENERIC_PATTERNS:
                if pat.search(s.strip()):
                    flags.append((str(fp.relative_to(ROOT)), "GENERIC", s[:90]))
                    break
            if "TODO" in s or "FIXME" in s or "placeholder" in s.lower():
                flags.append((str(fp.relative_to(ROOT)), "PLACEHOLDER", s[:90]))

    print(f"Scanned {len(files)} files — {len(flags)} generic/placeholder flags")
    for row in flags[:60]:
        print(f"  {row[0]} | {row[1]} | {row[2]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
