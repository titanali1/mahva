#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Syncs the shared assets (channel list, fonts, app icon) from the Android app
into the Windows app folder, so both versions always ship the same channels.

Usage:  python3 tools/sync_windows_assets.py
"""
import os
import shutil
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_RES = os.path.join(ROOT, "app", "src", "main", "res")
ANDROID_ASSETS = os.path.join(ROOT, "app", "src", "main", "assets")
WINDOWS = os.path.join(ROOT, "windows")

copy_plan = [
    (os.path.join(ANDROID_ASSETS, "channels.json"), os.path.join(WINDOWS, "assets", "channels.json")),
    (os.path.join(ANDROID_RES, "font", "vazirmatn_regular.ttf"), os.path.join(WINDOWS, "assets", "fonts", "vazirmatn_regular.ttf")),
    (os.path.join(ANDROID_RES, "font", "vazirmatn_medium.ttf"), os.path.join(WINDOWS, "assets", "fonts", "vazirmatn_medium.ttf")),
    (os.path.join(ANDROID_RES, "font", "vazirmatn_bold.ttf"), os.path.join(WINDOWS, "assets", "fonts", "vazirmatn_bold.ttf")),
    (os.path.join(ANDROID_RES, "mipmap-xxxhdpi", "ic_launcher.png"), os.path.join(WINDOWS, "assets", "icon-192.png")),
]


def copy_assets():
    for src, dst in copy_plan:
        if not os.path.exists(src):
            sys.exit("missing source asset: %s" % src)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        print("copied %s -> %s" % (os.path.relpath(src, ROOT), os.path.relpath(dst, ROOT)))


# --------------------------------------------------------------------------- icon

DENSITIES = [256, 128, 64, 48, 32, 16]
COLOR_A = (124, 77, 255)
COLOR_B = (26, 128, 246)


def _inside_rounded(x, y, size, radius):
    if x < 0 or y < 0 or x > size - 1 or y > size - 1:
        return False
    cx = min(max(x, radius), size - 1 - radius)
    cy = min(max(y, radius), size - 1 - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius


def _in_triangle(x, y, cx, cy, scale):
    pts = [(cx - 0.075 * scale, cy - 0.125 * scale),
           (cx - 0.075 * scale, cy + 0.125 * scale),
           (cx + 0.135 * scale, cy)]
    (x1, y1), (x2, y2), (x3, y3) = pts
    d1 = (x - x2) * (y1 - y2) - (x1 - x2) * (y - y2)
    d2 = (x - x3) * (y2 - y3) - (x2 - x3) * (y - y3)
    d3 = (x - x1) * (y3 - y1) - (x3 - x1) * (y - y1)
    return not (((d1 < 0) or (d2 < 0) or (d3 < 0)) and ((d1 > 0) or (d2 > 0) or (d3 > 0)))


def render_icon(size, ss=3):
    import zlib
    big = size * ss
    radius = big * 0.235
    center = big / 2.0
    ring_r, ring_w = big * 0.305, big * 0.030
    px = bytearray(big * big * 4)
    for y in range(big):
        for x in range(big):
            if not _inside_rounded(x, y, big, radius):
                continue
            t = (x + y) / (2.0 * big)
            r = int(COLOR_A[0] + (COLOR_B[0] - COLOR_A[0]) * t)
            g = int(COLOR_A[1] + (COLOR_B[1] - COLOR_A[1]) * t)
            b = int(COLOR_A[2] + (COLOR_B[2] - COLOR_A[2]) * t)
            dist = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
            if abs(dist - ring_r) <= ring_w / 2.0 or _in_triangle(x, y, center, center, big):
                a = 0.95
                r = int(r * (1 - a) + 255 * a)
                g = int(g * (1 - a) + 255 * a)
                b = int(b * (1 - a) + 255 * a)
            i = (y * big + x) * 4
            px[i], px[i + 1], px[i + 2], px[i + 3] = r, g, b, 255

    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            rs = gs = bs = total_a = 0
            for sy in range(ss):
                for sx in range(ss):
                    i = ((y * ss + sy) * big + (x * ss + sx)) * 4
                    a = px[i + 3]
                    rs += px[i] * a
                    gs += px[i + 1] * a
                    bs += px[i + 2] * a
                    total_a += a
            o = (y * size + x) * 4
            n = ss * ss
            if total_a == 0:
                out[o] = out[o + 1] = out[o + 2] = out[o + 3] = 0
            else:
                out[o] = min(255, rs // total_a)
                out[o + 1] = min(255, gs // total_a)
                out[o + 2] = min(255, bs // total_a)
                out[o + 3] = total_a // n
    return bytes(out)


def png_bytes(size, rgba):
    import zlib
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        raw += rgba[y * size * 4:(y + 1) * size * 4]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def build_ico(path):
    """Writes a multi-resolution .ico with PNG-compressed entries (Windows 11 ready)."""
    images = [(s, png_bytes(s, render_icon(s))) for s in DENSITIES]
    header = struct.pack("<HHH", 0, 1, len(images))
    entries, payload = b"", b""
    offset = 6 + 16 * len(images)
    for size, data in images:
        entries += struct.pack("<BBBBHHII", 0 if size >= 256 else size,
                               0 if size >= 256 else size, 0, 0, 1, 32,
                               len(data), offset)
        offset += len(data)
        payload += data
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(header + entries + payload)
    print("wrote %s (%d sizes: %s)" % (os.path.relpath(path, ROOT), len(images), DENSITIES))


def main():
    copy_assets()
    build_ico(os.path.join(WINDOWS, "build", "icon.ico"))
    # a 256x256 png for the in-app / window icon
    png = png_bytes(256, render_icon(256))
    with open(os.path.join(WINDOWS, "assets", "icon-256.png"), "wb") as fh:
        fh.write(png)
    print("wrote windows/assets/icon-256.png")


if __name__ == "__main__":
    main()
