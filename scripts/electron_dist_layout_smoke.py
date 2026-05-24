#!/usr/bin/env python3
"""Electron dist layout smoke (Track G / Phase 4 packaging precursor).

Fails when vite outputs under ``desktop/out/{main,preload,renderer}`` are incomplete.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _prefer_unpacked(candidates: list[Path], *, prefer: str) -> Path | None:
    if not candidates:
        return None
    pref = (prefer or "auto").strip().lower()

    def _first_matching(substring: str) -> Path | None:
        lowered = substring.lower()
        for p in candidates:
            if lowered in p.name.lower():
                return p
        return None

    if pref == "win":
        return _first_matching("win") or candidates[0]
    if pref == "linux":
        return _first_matching("linux") or candidates[0]
    if pref == "darwin" or pref == "mac":
        return _first_matching("mac") or candidates[0]

    if sys.platform.startswith("win"):
        return _first_matching("win") or candidates[0]
    if sys.platform == "darwin":
        return _first_matching("mac") or _first_matching("darwin") or candidates[0]
    return _first_matching("linux") or candidates[0]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("desktop", nargs="?", type=Path, default=Path("desktop"))
    p.add_argument(
        "--require-unpacked-resources",
        action="store_true",
        help="Require extracted resources under dist-installer/*unpacked/",
    )
    p.add_argument(
        "--prefer-unpacked",
        choices=("auto", "win", "linux", "darwin", "mac"),
        default="auto",
        help=("When multiple *unpacked directories exist under dist-installer (e.g. cache), pick the best match instead of lexical sort."),
    )
    ns = p.parse_args(argv)
    desktop = ns.desktop.resolve()
    trio = [
        desktop / "out" / "main" / "index.js",
        desktop / "out" / "preload" / "index.js",
        desktop / "out" / "renderer" / "index.html",
    ]
    missing = [path for path in trio if not path.is_file()]
    if missing:
        print("FAIL electron-dist-smoke missing vite artifacts:")
        for path in missing:
            print(" ", path)
        return 1
    print(f"PASS electron-dist-smoke vite ({desktop})")

    instal = desktop / "dist-installer"
    candidates = sorted(instal.glob("*unpacked")) if instal.is_dir() else []
    unpacked = _prefer_unpacked(candidates, prefer=ns.prefer_unpacked) if candidates else None

    if ns.require_unpacked_resources:
        if not unpacked or not (unpacked / "resources").is_dir():
            print("FAIL unpacked resources missing under dist-installer")
            if candidates:
                print(" candidates:", *[c.name for c in candidates])
            return 1
        print(f"PASS unpacked {unpacked.name}")
    elif unpacked:
        print(f"INFO unpacked present: {unpacked.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
