#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds every TakhtLive icon from the master artwork.

Source of truth:  brand/takhtlive-mark.png  (1024x1024, square logo artwork)

Generated:
  Android
    app/src/main/res/mipmap-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/ic_launcher.png       rounded square
    app/src/main/res/mipmap-{...}/ic_launcher_round.png                           circle
    app/src/main/res/mipmap-{...}/ic_launcher_full.png                            full bleed (adaptive)
  Windows
    windows/assets/icon-{512,256,192}.png
    windows/build/icon.ico                       (256/128/64/48/32/16, PNG compressed)
  In-app brand assets
    app/src/main/res/drawable-nodpi/ic_launcher_foreground.png    adaptive icon foreground
    app/src/main/res/drawable-nodpi/ic_brand_logo.png              256px badge for the UI
    windows/assets/brand-256.png                                   badge for the UI
    windows/assets/channel-placeholder.png                        missing-logo placeholder
    windows/assets/favicon-32.png                                  window icon
  Documentation
    docs/logo.png                                (README header)

Only the standard library is used (zlib for PNG), so it runs anywhere Python 3 does.

Usage:  python3 tools/make_logo_assets.py
"""
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "brand", "takhtlive-mark.png")
RES = os.path.join(ROOT, "app", "src", "main", "res")
WINDOWS = os.path.join(ROOT, "windows")
DOCS = os.path.join(ROOT, "docs")

DENSITIES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
ADAPTIVE = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
FOREGROUND_RATIO = 0.66      # artwork size inside the adaptive icon safe zone
ICO_SIZES = (256, 128, 64, 48, 32, 16)
CORNER_RATIO = 0.235        # rounded square radius, relative to the icon size
SUPERSAMPLE = 3             # mask anti-aliasing


# --------------------------------------------------------------------- PNG io

def decode_png(path):
    """Decodes an 8/16 bit PNG (grey, RGB, palette, with or without alpha) to RGBA."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s is not a PNG file" % path)

    pos, idat, palette, trns = 8, bytearray(), None, None
    width = height = depth = color_type = None
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, color_type = struct.unpack(">IIBB", chunk[:10])
            if depth not in (8, 16):
                raise ValueError("unsupported bit depth %d" % depth)
            if chunk[12] != 0:
                raise ValueError("interlaced PNGs are not supported")
        elif tag == b"PLTE":
            palette = chunk
        elif tag == b"tRNS":
            trns = chunk
        elif tag == b"IDAT":
            idat += chunk
        elif tag == b"IEND":
            break
        pos += 12 + length

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    sample_bytes = depth // 8
    bpp = channels * sample_bytes
    stride = width * bpp
    raw = zlib.decompress(bytes(idat))

    out = bytearray(width * height * 4)
    previous = bytearray(stride)
    offset = 0
    for y in range(height):
        filter_type = raw[offset]
        offset += 1
        line = bytearray(raw[offset:offset + stride])
        offset += stride
        if filter_type == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                up = previous[i]
                up_left = previous[i - bpp] if i >= bpp else 0
                p = left + up - up_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
                predictor = left if (pa <= pb and pa <= pc) else (up if pb <= pc else up_left)
                line[i] = (line[i] + predictor) & 0xFF

        row = y * width * 4
        for x in range(width):
            base = x * bpp
            if color_type == 6:
                r, g, b, a = (line[base], line[base + sample_bytes],
                              line[base + 2 * sample_bytes], line[base + 3 * sample_bytes])
            elif color_type == 2:
                r, g, b = (line[base], line[base + sample_bytes], line[base + 2 * sample_bytes])
                a = 255
            elif color_type == 0:
                r = g = b = line[base]
                a = 255
            elif color_type == 4:
                r = g = b = line[base]
                a = line[base + sample_bytes]
            else:  # palette
                index = line[base]
                r, g, b = palette[index * 3], palette[index * 3 + 1], palette[index * 3 + 2]
                a = trns[index] if trns is not None and index < len(trns) else 255
            out[row + x * 4:row + x * 4 + 4] = bytes((r, g, b, a))
        previous = line

    return width, height, out


def encode_png(path, width, height, pixels):
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)  # filter type 0
        raw += pixels[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    blob = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(blob)
    return len(blob)


def write_ico(path, images):
    """images: list of (size, png_bytes) - stored PNG compressed, largest first."""
    count = len(images)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries, blobs = bytearray(), bytearray()
    for size, blob in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        blobs += blob
        offset += len(blob)
    with open(path, "wb") as fh:
        fh.write(header + bytes(entries) + bytes(blobs))
    return 6 + 16 * count + len(blobs)


# ----------------------------------------------------------------- image math

def resize(width, height, pixels, new_width, new_height):
    """Area averaging resample (good for downscaling)."""
    if (width, height) == (new_width, new_height):
        return new_width, new_height, bytearray(pixels)
    out = bytearray(new_width * new_height * 4)
    scale_x = width / new_width
    scale_y = height / new_height

    for dy in range(new_height):
        y0, y1 = dy * scale_y, (dy + 1) * scale_y
        sy0, sy1 = int(y0), min(int(y1 - 1e-9) + 1, height)
        for dx in range(new_width):
            x0, x1 = dx * scale_x, (dx + 1) * scale_x
            sx0, sx1 = int(x0), min(int(x1 - 1e-9) + 1, width)
            r = g = b = a = 0.0
            total = 0.0
            for sy in range(sy0, sy1):
                wy = min(y1, sy + 1) - max(y0, sy)
                if wy <= 0:
                    continue
                row = sy * width * 4
                for sx in range(sx0, sx1):
                    wx = min(x1, sx + 1) - max(x0, sx)
                    if wx <= 0:
                        continue
                    weight = wx * wy
                    base = row + sx * 4
                    alpha = pixels[base + 3] / 255.0
                    r += pixels[base] * weight * alpha
                    g += pixels[base + 1] * weight * alpha
                    b += pixels[base + 2] * weight * alpha
                    a += pixels[base + 3] * weight
                    total += weight
            if total <= 0:
                continue
            alpha_avg = a / total
            base = (dy * new_width + dx) * 4
            if alpha_avg > 0:
                coverage = a / 255.0 / total if alpha_avg > 0 else 0
                coverage = max(coverage, 1e-9)
                out[base] = min(255, int(round(r / (total * coverage))))
                out[base + 1] = min(255, int(round(g / (total * coverage))))
                out[base + 2] = min(255, int(round(b / (total * coverage))))
            out[base + 3] = min(255, int(round(alpha_avg)))
    return new_width, new_height, out


def apply_mask(width, height, pixels, inside, supersample=SUPERSAMPLE):
    """Multiplies the alpha channel with an anti-aliased coverage mask."""
    out = bytearray(pixels)
    step = 1.0 / (supersample + 1)
    offsets = [step * (i + 1) - 0.5 for i in range(supersample + 1)]
    for y in range(height):
        row = y * width * 4
        for x in range(width):
            hits = 0
            for oy in offsets:
                for ox in offsets:
                    if inside(x + 0.5 + ox, y + 0.5 + oy):
                        hits += 1
            if hits == 0:
                out[row + x * 4 + 3] = 0
            elif hits < len(offsets) ** 2:
                coverage = hits / float(len(offsets) ** 2)
                out[row + x * 4 + 3] = int(round(out[row + x * 4 + 3] * coverage))
    return out


def rounded_square_inside(size, radius):
    limit = size - 1

    def inside(x, y):
        if x < 0 or y < 0 or x > limit or y > limit:
            return False
        cx = min(max(x, radius), limit - radius)
        cy = min(max(y, radius), limit - radius)
        dx, dy = x - cx, y - cy
        if dx == 0 and dy == 0:
            return True
        return dx * dx + dy * dy <= radius * radius

    return inside


def circle_inside(size):
    limit = size - 1
    centre = limit / 2.0
    radius = centre

    def inside(x, y):
        dx, dy = x - centre, y - centre
        return dx * dx + dy * dy <= radius * radius

    return inside


# ----------------------------------------------------------------------- main

def _rounded_rect_inside(x, y, x0, y0, x1, y1, radius):
    if x < x0 or y < y0 or x > x1 or y > y1:
        return False
    cx = min(max(x, x0 + radius), x1 - radius)
    cy = min(max(y, y0 + radius), y1 - radius)
    dx, dy = x - cx, y - cy
    if dx == 0 and dy == 0:
        return True
    return dx * dx + dy * dy <= radius * radius


def _distance_to_segment(x, y, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / length_sq))
    px, py = x0 + t * dx, y0 + t * dy
    return ((x - px) ** 2 + (y - py) ** 2) ** 0.5


def channel_placeholder(size=256):
    """Neutral grey TV tile used when a channel logo cannot be loaded."""
    tile = (_rounded_rect_inside, 0.0, 0.0, float(size - 1), float(size - 1), size * 0.22)
    body_out = (_rounded_rect_inside, size * 0.20, size * 0.30, size * 0.80, size * 0.68, size * 0.07)
    body_in = (_rounded_rect_inside, size * 0.255, size * 0.355, size * 0.745, size * 0.625, size * 0.045)
    stand = (size * 0.36, size * 0.75, size * 0.64, size * 0.75)
    antennas = [
        (size * 0.50, size * 0.31, size * 0.36, size * 0.17),
        (size * 0.50, size * 0.31, size * 0.64, size * 0.17),
    ]
    stroke = size * 0.045
    tile_color = (28, 27, 43)
    glyph_color = (185, 180, 208)

    pixels = bytearray(size * size * 4)
    samples = 3
    step = 1.0 / (samples + 1)
    offsets = [step * (i + 1) - 0.5 for i in range(samples + 1)]
    for y in range(size):
        for x in range(size):
            tile_hits = glyph_hits = 0
            for oy in offsets:
                for ox in offsets:
                    sx, sy = x + 0.5 + ox, y + 0.5 + oy
                    if not _rounded_rect_inside(sx, sy, 0.0, 0.0, size - 1, size - 1, size * 0.22):
                        continue
                    tile_hits += 1
                    if (_rounded_rect_inside(sx, sy, *body_out[1:]) and
                            not _rounded_rect_inside(sx, sy, *body_in[1:])):
                        glyph_hits += 1
                    elif _distance_to_segment(sx, sy, *stand) <= stroke / 2:
                        glyph_hits += 1
                    elif any(_distance_to_segment(sx, sy, *line) <= stroke / 2 for line in antennas):
                        glyph_hits += 1
            total = float((samples + 1) ** 2)
            base = (y * size + x) * 4
            if tile_hits == 0:
                continue
            tile_alpha = tile_hits / total
            glyph_alpha = min(1.0, glyph_hits / tile_hits) if tile_hits else 0.0
            r = tile_color[0] * (1 - glyph_alpha) + glyph_color[0] * glyph_alpha
            g = tile_color[1] * (1 - glyph_alpha) + glyph_color[1] * glyph_alpha
            b = tile_color[2] * (1 - glyph_alpha) + glyph_color[2] * glyph_alpha
            pixels[base] = int(round(r))
            pixels[base + 1] = int(round(g))
            pixels[base + 2] = int(round(b))
            pixels[base + 3] = int(round(tile_alpha * 255))
    return pixels


def paste_centered(canvas_size, mark_size, mark):
    canvas = bytearray(canvas_size * canvas_size * 4)
    offset = (canvas_size - mark_size) // 2
    for y in range(mark_size):
        src = y * mark_size * 4
        dst = ((y + offset) * canvas_size + offset) * 4
        canvas[dst:dst + mark_size * 4] = mark[src:src + mark_size * 4]
    return canvas


def build():
    if not os.path.exists(SOURCE):
        sys.exit("missing master artwork: %s" % SOURCE)
    width, height, source = decode_png(SOURCE)
    if width != height:
        sys.exit("the artwork must be square (got %dx%d)" % (width, height))

    written = []

    def emit(path, size, pixels):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        written.append((path, encode_png(path, size, size, pixels)))

    # ---------------------------------------------------------------- Android
    for density, size in DENSITIES.items():
        folder = os.path.join(RES, "mipmap-%s" % density)
        _, _, scaled = resize(width, height, source, size, size)
        rounded = apply_mask(size, size, scaled, rounded_square_inside(size, size * CORNER_RATIO))
        emit(os.path.join(folder, "ic_launcher.png"), size, rounded)
        circular = apply_mask(size, size, scaled, circle_inside(size))
        emit(os.path.join(folder, "ic_launcher_round.png"), size, circular)

    # full bleed artwork used as the adaptive icon background
    for density, size in ADAPTIVE.items():
        folder = os.path.join(RES, "mipmap-%s" % density)
        _, _, scaled = resize(width, height, source, size, size)
        emit(os.path.join(folder, "ic_launcher_full.png"), size, scaled)

    # adaptive icon foreground: the artwork shrunk into the safe zone so that no
    # launcher mask can clip it (36dp bleed on a 108dp canvas)
    canvas = ADAPTIVE["xxxhdpi"]
    mark_size = int(round(canvas * FOREGROUND_RATIO))
    _, _, mark = resize(width, height, source, mark_size, mark_size)
    emit(os.path.join(RES, "drawable-nodpi", "ic_launcher_foreground.png"),
         canvas, paste_centered(canvas, mark_size, mark))

    # in-app badge: circular crop, transparent outside the circle
    _, _, badge = resize(width, height, source, 256, 256)
    badge = apply_mask(256, 256, badge, circle_inside(256))
    emit(os.path.join(RES, "drawable-nodpi", "ic_brand_logo.png"), 256, badge)
    emit(os.path.join(WINDOWS, "assets", "brand-256.png"), 256, badge)

    # neutral channel placeholder (used when a channel logo cannot be loaded)
    emit(os.path.join(WINDOWS, "assets", "channel-placeholder.png"), 256, channel_placeholder(256))

    _, _, favicon = resize(width, height, source, 64, 64)
    favicon = apply_mask(64, 64, favicon, circle_inside(64), supersample=4)
    emit(os.path.join(WINDOWS, "assets", "favicon-64.png"), 64, favicon)

    # ----------------------------------------------------------------- Windows
    for size in (512, 256, 192):
        _, _, scaled = resize(width, height, source, size, size)
        rounded = apply_mask(size, size, scaled, rounded_square_inside(size, size * CORNER_RATIO))
        emit(os.path.join(WINDOWS, "assets", "icon-%d.png" % size), size, rounded)

    ico_images = []
    for size in ICO_SIZES:
        _, _, scaled = resize(width, height, source, size, size)
        rounded = apply_mask(size, size, scaled, rounded_square_inside(size, size * CORNER_RATIO))
        ico_images.append((size, _png_bytes(size, rounded)))
    ico_path = os.path.join(WINDOWS, "build", "icon.ico")
    os.makedirs(os.path.dirname(ico_path), exist_ok=True)
    written.append((ico_path, write_ico(ico_path, ico_images)))

    # ------------------------------------------------------------------- docs
    _, _, scaled = resize(width, height, source, 512, 512)
    emit(os.path.join(DOCS, "logo.png"), 512, scaled)

    print("built %d icon files from %s (%dx%d)" % (len(written), os.path.relpath(SOURCE, ROOT), width, height))
    for path, size in written:
        print("  %-64s %7d bytes" % (os.path.relpath(path, ROOT), size))


def _png_bytes(size, pixels):
    path = os.path.join(ROOT, ".icon-tmp.png")
    encode_png(path, size, size, pixels)
    with open(path, "rb") as fh:
        blob = fh.read()
    os.remove(path)
    return blob


if __name__ == "__main__":
    build()
