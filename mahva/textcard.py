"""Render scene cards (backgrounds + text overlays) with Pillow.

The renderer outputs perfect still frames; motion (Ken Burns, cross-fades,
fades) is added later by ffmpeg.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import fonts as fontlib
from . import shaping
from .schema import Project, Scene
from .themes import Theme, get_theme


def _hex_to_rgb(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        return None
    try:
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


@lru_cache(maxsize=256)
def _load_font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.truetype(path, size)


@dataclass
class Block:
    kind: str          # kicker | title | subtitle | body | bullet | footer
    text: str
    weight: str
    color: tuple[int, int, int]
    size: float        # relative multiplier of the base size
    gap_before: float  # in em
    line_spacing: float
    max_width: float = 1.0


BLOCK_STYLE = {
    "kicker":   dict(weight="bold", size=0.58, gap_before=0.0, line_spacing=1.30),
    "title":    dict(weight="bold", size=1.00, gap_before=0.45, line_spacing=1.34),
    "subtitle": dict(weight="medium", size=0.74, gap_before=0.50, line_spacing=1.58),
    "body":     dict(weight="regular", size=0.62, gap_before=0.72, line_spacing=1.72),
    "bullet":   dict(weight="regular", size=0.62, gap_before=0.30, line_spacing=1.60),
    "footer":   dict(weight="medium", size=0.42, gap_before=0.0, line_spacing=1.4),
}


class CardRenderer:
    """Builds the still layers for one scene."""

    def __init__(self, project: Project, footer: bool = True, show_numbers: bool = True):
        self.project = project
        self.footer = footer
        self.show_numbers = show_numbers
        self.rtl = project.rtl
        self.language = project.language or ("fa" if project.rtl else "en")
        self.W = int(project.width)
        self.H = int(project.height)
        self.SS = 1 if max(self.W, self.H) > 2200 else 2
        self._font_cache: dict[tuple[str, str, int], tuple[str, int]] = {}

    # ---------------------------------------------------------------- fonts
    def _font(self, weight: str, px: int) -> ImageFont.FreeTypeFont:
        key = (self.project.font_family or "Vazirmatn", weight, px)
        if key not in self._font_cache:
            weight = weight if weight in fontlib.WEIGHTS else "regular"
            path, index = fontlib.resolve_font_path(self.project.font_family, weight, self.language)
            self._font_cache[key] = (path, index)
        path, index = self._font_cache[key]
        return _load_font(path, max(6, int(px)), index)

    # ------------------------------------------------------------- wrapping
    def _wrap(self, text: str, font: ImageFont.FreeTypeFont, max_width: float) -> list[str]:
        lines: list[str] = []
        for raw_para in text.split("\n"):
            para = " ".join(raw_para.split())
            if not para:
                if lines:
                    lines.append("")
                continue
            words = para.split(" ")
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if font.getlength(shaping.shape(candidate, self.rtl)) <= max_width or not current:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
                # hard-break words that are wider than the line
                while font.getlength(shaping.shape(current, self.rtl)) > max_width and len(current) > 2:
                    overflow = current
                    cut = len(overflow)
                    while cut > 2 and font.getlength(shaping.shape(overflow[:cut], self.rtl)) > max_width:
                        cut -= 1
                    lines.append(overflow[:cut])
                    current = overflow[cut:]
            if current:
                lines.append(current)
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return lines

    # -------------------------------------------------------------- blocks
    def _blocks(self, scene: Scene, index: int, total: int) -> list[Block]:
        theme = get_theme(scene.theme or self.project.theme)
        accent = _hex_to_rgb(scene.accent) or theme.accent
        blocks: list[Block] = []

        title = scene.title
        if not title and index == 0 and self.project.title.strip():
            # the opening card carries the video title
            title = self.project.title.strip()
        if self.show_numbers and total > 1 and title:
            blocks.append(Block("kicker", f"قسمت {index + 1} از {total}" if self.rtl
                                else f"Part {index + 1} of {total}",
                                **BLOCK_STYLE["kicker"], color=accent))
        if title:
            blocks.append(Block("title", title, **BLOCK_STYLE["title"], color=theme.text))
        if scene.subtitle:
            blocks.append(Block("subtitle", scene.subtitle, **BLOCK_STYLE["subtitle"], color=theme.text))
        if scene.body:
            blocks.append(Block("body", scene.body, **BLOCK_STYLE["body"], color=theme.muted))
        for bullet in scene.bullet_points:
            marker = "•  " if self.rtl else "•  "
            blocks.append(Block("bullet", f"{marker}{bullet}", **BLOCK_STYLE["bullet"], color=theme.muted))
        return blocks

    def _fit(self, blocks: list[Block], max_width: float, avail_height: float,
             base_px: float, scale: float = 1.0):
        """Wrap text and shrink the font until everything fits."""
        for _ in range(16):
            rendered = []
            total = 0.0
            for block in blocks:
                px = base_px * block.size * scale
                font = self._font(block.weight, px)
                width = max_width * block.max_width
                lines = self._wrap(block.text, font, width)
                line_h = (font.getmetrics()[0] + font.getmetrics()[1]) * block.line_spacing
                gap = base_px * block.size * block.gap_before * scale
                height = len(lines) * line_h + gap
                rendered.append((block, font, lines, line_h, gap, height))
                total += height
            if total <= avail_height or scale < 0.42:
                return rendered, total
            shrink = max(0.55, min(0.96, avail_height / total))
            scale = scale * shrink
        return rendered, total

    # ----------------------------------------------------------- text layer
    def text_overlay(self, scene: Scene, index: int = 0, total: int = 1,
                     layout: str = "plain", image_path: str | None = None,
                     with_shadow: bool | None = None) -> Image.Image:
        theme = get_theme(scene.theme or self.project.theme)
        accent = _hex_to_rgb(scene.accent) or theme.accent
        rtl = self.rtl
        ss = self.SS
        W, H = self.W * ss, self.H * ss
        if with_shadow is None:
            with_shadow = bool(image_path)

        blocks = self._blocks(scene, index, total)
        if layout == "title":
            # cover cards: no kicker/body clutter, larger type
            blocks = [b for b in blocks if b.kind in ("kicker", "title", "subtitle")]

        margin_x = W * (0.085 if layout != "overlay" else 0.075)
        top_margin = H * 0.10
        bottom_margin = H * (0.16 if layout in ("overlay", "split") else 0.12)
        if self.footer:
            bottom_margin = max(bottom_margin, H * 0.115)
        avail_h = H - top_margin - bottom_margin
        max_width = W - 2 * margin_x

        base_px = H * (0.058 if layout == "title" else 0.052)
        if layout == "title":
            top_margin, bottom_margin = H * 0.16, H * 0.16
            avail_h = H - top_margin - bottom_margin
        rendered, total_h = self._fit(blocks, max_width, avail_h, base_px)

        image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # vertical placement
        valign = "center" if layout in ("title",) else ("bottom" if layout in ("overlay", "split") else "center")
        if valign == "bottom":
            y = H - bottom_margin - total_h
        elif valign == "center":
            y = top_margin + max(0.0, (avail_h - total_h) / 2)
        else:
            y = top_margin

        x_text = (W - margin_x) if rtl else margin_x
        anchor = "ra" if rtl else "la"

        for block, font, lines, line_h, gap, _height in rendered:
            y += gap
            if block.kind == "title":
                self._draw_title_accent(draw, image, x_text, y, margin_x, W, H, accent, font, rtl, ss)
            for i, line in enumerate(lines):
                if line:
                    visual = shaping.shape(line, rtl)
                    if with_shadow:
                        off = max(1, int(0.0022 * H))
                        shadow = (0, 0, 0, 165) if not theme.light else (255, 255, 255, 200)
                        draw.text((x_text + (off if not rtl else -off), y + off), visual,
                                  font=font, fill=shadow, anchor=anchor)
                    draw.text((x_text, y), visual, font=font, fill=block.color + (255,), anchor=anchor)
                y += line_h

        if self.footer and total > 1:
            self._draw_footer(draw, W, H, index, total, theme, accent, margin_x, ss)

        if image_path:
            luma = image_luminance(image_path)
            scrim = self.scrim(theme, layout, light=theme.light, luma=luma, size=(W, H))
            image = Image.alpha_composite(scrim, image)

        if ss != 1:
            image = image.resize((self.W, self.H), Image.LANCZOS)
        return image

    def _draw_title_accent(self, draw: ImageDraw.ImageDraw, image: Image.Image, x_text: float,
                           y: float, margin_x: float, W: int, H: int, accent, font, rtl: bool, ss: int) -> None:
        bar_w = max(3, int(0.008 * W))
        bar_h = int(font.size * 1.05) if hasattr(font, "size") else int(H * 0.05)
        offset = int(0.028 * W)
        x = (x_text + offset) if rtl else (x_text - offset)
        draw.rounded_rectangle(
            [x - bar_w, y + bar_h * 0.05, x, y + bar_h],
            radius=bar_w // 2, fill=accent + (235,),
        )

    def _draw_footer(self, draw: ImageDraw.ImageDraw, W: int, H: int, index: int, total: int,
                     theme: Theme, accent, margin_x: float, ss: int) -> None:
        font = self._font("medium", H * 0.024)
        title = (self.project.title or "").strip()
        if title:
            visual = shaping.shape(title[:70], self.rtl)
            x = (W - margin_x) if self.rtl else margin_x
            draw.text((x, H * 0.945), visual, font=font, fill=theme.muted + (215,),
                      anchor="ra" if self.rtl else "la")
        # progress bar
        y = H - max(4, int(0.006 * H))
        bar_h = max(3, int(0.005 * H))
        draw.rectangle([0, y, W, y + bar_h], fill=theme.muted + (70,))
        done = int(W * (index + 1) / max(1, total))
        draw.rectangle([0, y, done, y + bar_h], fill=accent + (225,))

    def scrim(self, theme: Theme, layout: str, light: bool = False,
              luma: float | None = None, size: tuple[int, int] | None = None) -> Image.Image:
        """Gradient that keeps the text readable over photos.

        The strength adapts to the picture: a bright photo behind white text gets
        a much heavier veil than a dark one (and vice-versa for light themes).
        """
        W, H = size or (self.W, self.H)
        strength = theme.scrim / 255.0
        base_alpha = 0.0
        if luma is not None:
            if light:   # dark text -> the picture must not be dark
                boost = _clamp(1.0 + max(0.0, 118.0 - luma) / 100.0, 0.9, 1.9)
                base_alpha = _clamp((110.0 - luma) / 130.0, 0.0, 0.55)
            else:       # light text -> the picture must not be bright
                boost = _clamp(1.0 + max(0.0, luma - 110.0) / 90.0, 0.9, 1.85)
                base_alpha = _clamp((luma - 115.0) / 120.0, 0.0, 0.60)
        else:
            boost = 1.0
        strength = min(1.0, strength * boost)

        color = (255, 255, 255) if light else (0, 0, 0)
        grad = Image.new("L", (1, H))
        for y in range(H):
            t = y / max(1, H - 1)
            # two smooth sweeps that meet in the middle: smoke from the top,
            # a heavier veil towards the bottom where the text sits
            a_top = 0.45 * (1.0 - t / 0.55) ** 1.7 if t < 0.55 else 0.0
            a_bottom = 0.95 * ((t - 0.45) / 0.55) ** 1.35 if t > 0.45 else 0.0
            alpha = base_alpha + (1.0 - base_alpha) * max(a_top, a_bottom)
            grad.putpixel((0, y), int(_clamp(alpha * strength, 0.0, 1.0) * 255))
        mask = grad.resize((W, H))
        scrim = Image.new("RGBA", (W, H), color + (0,))
        scrim.putalpha(mask)
        return scrim

    # ---------------------------------------------------------- backgrounds
    def background(self, theme: Theme, seed: int = 0) -> Image.Image:
        W, H = self.W, self.H
        grad = Image.new("L", (1, 256))
        for i in range(256):
            t = i / 255.0
            grad.putpixel((0, i), int(255 * t))
        mask = grad.resize((W, H), Image.BILINEAR)

        top, bottom = theme.bg_top, theme.bg_bottom
        base = Image.new("RGB", (W, H), top)
        base = Image.composite(Image.new("RGB", (W, H), bottom), base, mask)

        # soft accent glow in one corner (deterministic per scene)
        rng = _Lcg(seed * 7919 + 13)
        glow_size = int(max(W, H) * 0.95)
        glow = Image.new("L", (glow_size, glow_size), 0)
        gd = ImageDraw.Draw(glow)
        gd.ellipse([0, 0, glow_size, glow_size], fill=90)
        glow = glow.filter(ImageFilter.GaussianBlur(glow_size * 0.22))
        layer = Image.new("RGB", (glow_size, glow_size), theme.accent)
        gx = int(-glow_size * 0.35) + int(rng.next() * W * 0.7)
        gy = int(-glow_size * 0.30) + int(rng.next() * H * 0.5)
        base.paste(layer, (gx, gy), glow.point(lambda v: int(v * 0.30)))

        # vignette + film grain so flat areas don't look dead
        vig = Image.new("L", (W, H), 0)
        vd = ImageDraw.Draw(vig)
        vd.ellipse([-W * 0.35, -H * 0.35, W * 1.35, H * 1.35], fill=255)
        vig = vig.filter(ImageFilter.GaussianBlur(min(W, H) * 0.12))
        base = Image.composite(base, Image.new("RGB", (W, H), tuple(int(c * 0.55) for c in theme.bg_bottom)), vig)

        try:
            noise = Image.effect_noise((W, H), 14).convert("L")
            base = Image.blend(base, Image.merge("RGB", (noise, noise, noise)), 0.035)
        except Exception:
            pass
        return base

    # ------------------------------------------------------------ compose
    def compose(self, scene: Scene, index: int = 0, total: int = 1, layout: str | None = None) -> Image.Image:
        """Full still frame: background/photo + scrim + text (mirrors the video)."""
        theme = get_theme(scene.theme or self.project.theme)
        layout = layout or scene.layout_resolved or "plain"
        W, H = self.W, self.H

        if scene.image and Path(scene.image).exists():
            photo = load_image(scene.image)
            if layout == "split":
                top_h = W and (H * 0.56)
                top_h = int(round(top_h / 2) * 2)
                base = self.background(theme, seed=index + 1).convert("RGB")
                base.paste(cover(photo, W, top_h), (0, 0))
            else:
                base = cover(photo, W, H)
            base = Image.alpha_composite(base.convert("RGBA"), self.scrim(theme, layout, theme.light))
        else:
            base = self.background(theme, seed=index + 1).convert("RGBA")

        overlay = self.text_overlay(scene, index, total, layout=layout,
                                    image_path=scene.image if scene.image else None)
        return Image.alpha_composite(base, overlay).convert("RGB")


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@lru_cache(maxsize=64)
def image_luminance(path: str | Path) -> float:
    """Average perceived brightness (0-255) of an image, for scrim decisions."""
    try:
        img = load_image(path).convert("L")
        img.thumbnail((64, 64))
        histogram = img.histogram()
        total = sum(histogram) or 1
        return sum(i * count for i, count in enumerate(histogram)) / total
    except Exception:
        return 128.0


def load_image(path: str | Path) -> Image.Image:
    """Open an image, honour EXIF rotation and convert to RGB."""
    from PIL import ImageOps

    img = Image.open(path)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode not in ("RGB", "L"):
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (0, 0, 0))
            rgba = img.convert("RGBA")
            background.paste(rgba, mask=rgba.split()[-1])
            return background
        return img.convert("RGB")
    return img.convert("RGB")


def cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """Scale + center-crop, mimicking ffmpeg's force_original_aspect_ratio=increase."""
    src_w, src_h = img.size
    if src_w <= 0 or src_h <= 0:
        return Image.new("RGB", (w, h), (0, 0, 0))
    scale = max(w / src_w, h / src_h)
    new_size = (max(1, int(round(src_w * scale))), max(1, int(round(src_h * scale))))
    resized = img.resize(new_size, Image.LANCZOS)
    left = (resized.width - w) // 2
    top = (resized.height - h) // 2
    return resized.crop((left, top, left + w, top + h))


class _Lcg:
    """Tiny deterministic RNG (keeps previews reproducible)."""

    def __init__(self, seed: int):
        self.state = (seed * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)

    def next(self) -> float:
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        return ((self.state >> 33) % 100000) / 100000.0


def render_preview(project: Project, scene: Scene, index: int = 0, total: int | None = None,
                   path: str | Path | None = None) -> Path:
    """Render a single still card (used by the web UI and the CLI preview mode)."""
    total = total if total is not None else len(project.scenes)
    renderer = CardRenderer(project)
    layout = scene.layout_resolved or "plain"
    img = renderer.compose(scene, index, total, layout=layout)
    out = Path(path) if path else Path("preview.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
