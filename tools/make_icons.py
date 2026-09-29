#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generates the Mahva launcher icons (PNG) without any third-party library.

Usage:  python3 tools/make_icons.py
"""
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "app", "src", "main", "res")

DENSITIES = {
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}

# Diagonal gradient (top-left -> bottom-right)
COLOR_A = (124, 77, 255)     # #7C4DFF
COLOR_B = (26, 128, 246)     # #1A80F6
SS = 3                       # supersampling factor


def write_png(path, width, height, pixels):
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)  # filter type 0
        raw += pixels[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    blob = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as fh:
        fh.write(blob)


def inside_rounded_rect(x, y, size, radius):
    if x < 0 or y < 0 or x > size - 1 or y > size - 1:
        return False
    cx = min(max(x, radius), size - 1 - radius)
    cy = min(max(y, radius), size - 1 - radius)
    dx = x - cx
    dy = y - cy
    return dx * dx + dy * dy <= radius * radius


def inside_circle(x, y, size):
    r = size / 2.0
    dx = x - r + 0.5
    dy = y - r + 0.5
    return dx * dx + dy * dy <= r * r


def in_triangle(x, y, cx, cy, scale):
    # Play triangle pointing to the right.
    pts = [
        (cx - 0.075 * scale, cy - 0.125 * scale),
        (cx - 0.075 * scale, cy + 0.125 * scale),
        (cx + 0.135 * scale, cy),
    ]
    (x1, y1), (x2, y2), (x3, y3) = pts
    d1 = (x - x2) * (y1 - y2) - (x1 - x2) * (y - y2)
    d2 = (x - x3) * (y2 - y3) - (x2 - x3) * (y - y3)
    d3 = (x - x1) * (y3 - y1) - (x3 - x1) * (y - y1)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def render(size, round_icon):
    big = size * SS
    radius = big * (0.5 if round_icon else 0.235)
    center = big / 2.0
    ring_r = big * 0.305
    ring_w = big * 0.030
    pixels = bytearray(big * big * 4)

    for y in range(big):
        for x in range(big):
            if round_icon:
                inside = inside_circle(x, y, big)
            else:
                inside = inside_rounded_rect(x, y, big, radius)
            if not inside:
                continue

            t = (x + y) / (2.0 * big)
            r = int(COLOR_A[0] + (COLOR_B[0] - COLOR_A[0]) * t)
            g = int(COLOR_A[1] + (COLOR_B[1] - COLOR_A[1]) * t)
            b = int(COLOR_A[2] + (COLOR_B[2] - COLOR_A[2]) * t)

            dx = x - center
            dy = y - center
            dist = (dx * dx + dy * dy) ** 0.5

            # Broadcast ring
            if abs(dist - ring_r) <= ring_w / 2.0:
                a = 0.90
                r = int(r * (1 - a) + 255 * a)
                g = int(g * (1 - a) + 255 * a)
                b = int(b * (1 - a) + 255 * a)

            # Play glyph
            if in_triangle(x, y, center, center, big):
                a = 1.0
                r = int(r * (1 - a) + 255 * a)
                g = int(g * (1 - a) + 255 * a)
                b = int(b * (1 - a) + 255 * a)

            i = (y * big + x) * 4
            pixels[i] = r
            pixels[i + 1] = g
            pixels[i + 2] = b
            pixels[i + 3] = 255

    # Box-downsample (anti-aliasing) into RGBA
    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            rs = gs = bs = as_ = 0
            for sy in range(SS):
                for sx in range(SS):
                    i = ((y * SS + sy) * big + (x * SS + sx)) * 4
                    a = pixels[i + 3]
                    rs += pixels[i] * a
                    gs += pixels[i + 1] * a
                    bs += pixels[i + 2] * a
                    as_ += a
            n = SS * SS
            o = (y * size + x) * 4
            if as_ == 0:
                out[o] = out[o + 1] = out[o + 2] = out[o + 3] = 0
            else:
                out[o] = min(255, rs // as_)
                out[o + 1] = min(255, gs // as_)
                out[o + 2] = min(255, bs // as_)
                out[o + 3] = as_ // n
    return out


def main():
    for density, size in DENSITIES.items():
        folder = os.path.join(RES, "mipmap-" + density)
        os.makedirs(folder, exist_ok=True)
        write_png(os.path.join(folder, "ic_launcher.png"), size, size, render(size, False))
        write_png(os.path.join(folder, "ic_launcher_round.png"), size, size, render(size, True))
        print("wrote", folder)


if __name__ == "__main__":
    main()
