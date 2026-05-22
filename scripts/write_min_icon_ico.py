#!/usr/bin/env python3

"""Emit a trivial multi-resolution BMP-style ``desktop/build/icon.ico`` (stdlib only)."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


def _pixel_bgra(r: int, g: int, b: int, a: int = 255) -> bytes:

    return bytes((b % 256, g % 256, r % 256, a % 256))


def dib_for_square(edge: int) -> bytes:

    bpp = 32

    xor_size = edge * edge * 4

    stride_and = ((edge + 31) // 32) * 4

    mask_size = stride_and * edge

    header = struct.pack(
        "<IiiHHIIIIII",
        40,
        edge,
        edge * 2,
        1,
        bpp,
        0,
        xor_size,
        0,
        0,
        0,
        0,
    )

    cx_f = (edge - 1) * 0.5

    cy_f = cx_f

    inner_r = max(edge // 6, 1)

    mid_r = max(edge // 3, inner_r + 1)

    ring_r = mid_r + max(4, edge // 32)

    pixels = bytearray()

    for y in reversed(range(edge)):
        fy = float(y)

        dy = fy - cy_f

        dy_sq = dy * dy

        row_buf = bytearray()

        for x in range(edge):
            fx = float(x)

            dx = fx - cx_f

            dist_sq = dx * dx + dy_sq

            if dist_sq < inner_r * inner_r:
                px = _pixel_bgra(255, 255, 255)

            elif dist_sq < mid_r * mid_r:
                px = _pixel_bgra(22, 111, 198)

            elif dist_sq < ring_r * ring_r:
                px = _pixel_bgra(240, 240, 255)

            else:
                px = _pixel_bgra(12, 80, 140)

            row_buf.extend(px)

        pixels.extend(row_buf)

    and_plane = bytes([0xFF]) * mask_size

    return header + pixels + and_plane


def bake_ico(path: Path, sizes: tuple[int, ...]) -> None:

    blobs = [dib_for_square(edge) for edge in sizes]

    hdr = struct.pack("<HHH", 0, 1, len(blobs))

    offset = len(hdr) + 16 * len(blobs)

    entries = bytearray()

    for edge, dib in zip(sizes, blobs):
        w_byte = edge if edge < 256 else 0

        entries.extend(
            struct.pack(
                "<BBBBHHII",
                w_byte,
                w_byte,
                0,
                0,
                1,
                32,
                len(dib),
                offset,
            )
        )

        offset += len(dib)

    blob = hdr + entries + b"".join(blobs)

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_bytes(blob)


def main() -> None:

    ap = argparse.ArgumentParser()

    default = Path("desktop/build/icon.ico")

    ap.add_argument("--path", type=Path, default=default)

    args = ap.parse_args()

    bake_ico(args.path, sizes=(256, 128, 64, 48, 32, 16))

    print(args.path.resolve(), args.path.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
