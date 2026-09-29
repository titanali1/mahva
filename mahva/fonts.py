"""Font discovery across Linux / macOS / Windows.

Fonts are looked up by family name with sensible fallbacks; the bundled
Vazirmatn family (SIL OFL) always works, even on a bare container without any
system fonts installed.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

FONT_EXTENSIONS = (".ttf", ".otf", ".ttc", ".otc")

WEIGHTS = ("thin", "extralight", "light", "regular", "medium", "semibold", "bold", "extrabold", "black")

# Persian-first fallback chain: the first family that exists on this machine wins.
FALLBACK_CHAINS: dict[str, list[str]] = {
    "fa": ["Vazirmatn", "Vazir", "IRANSansX", "IRANSans", "Sahel", "Shabnam", "Estedad",
           "NotoNaskhArabic", "NotoSansArabic", "Tahoma", "Arial", "DejaVuSans", "FreeSans"],
    "ar": ["Vazirmatn", "NotoNaskhArabic", "NotoSansArabic", "Amiri", "Tahoma", "Arial",
           "DejaVuSans"],
    "en": ["Inter", "DejaVuSans", "Arial", "Helvetica", "LiberationSans", "NotoSans", "Tahoma"],
}

BUNDLED_FAMILY = "Vazirmatn"


def _font_dirs() -> list[Path]:
    dirs: list[Path] = []
    here = Path(__file__).resolve().parent.parent
    dirs.append(here / "assets" / "fonts")          # repository bundle
    dirs.append(Path(os.environ.get("MAHVA_FONTS", "")) if os.environ.get("MAHVA_FONTS") else Path("/nonexistent"))
    if sys.platform == "win32":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        dirs.append(windir / "Fonts")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    elif sys.platform == "darwin":
        dirs += [Path("/System/Library/Fonts"), Path("/Library/Fonts"),
                 Path.home() / "Library" / "Fonts"]
    else:
        dirs += [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"),
                 Path.home() / ".fonts", Path.home() / ".local" / "share" / "fonts",
                 Path("/usr/share/fonts/truetype")]
    return [d for d in dirs if d and d.exists()]


def _normalize(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


@lru_cache(maxsize=1)
def _font_index() -> dict[str, str]:
    """Map normalized file stem -> absolute path."""
    index: dict[str, str] = {}
    for directory in _font_dirs():
        for path in sorted(directory.rglob("*")):
            if path.suffix.lower() in FONT_EXTENSIONS and path.is_file():
                index.setdefault(_normalize(path.stem), str(path))
    return index


@lru_cache(maxsize=1)
def available_families() -> list[str]:
    families: set[str] = set()
    for stem in _font_index():
        base = stem
        for weight in WEIGHTS:
            if base.endswith(weight):
                base = base[: -len(weight)]
                break
        for style in ("italic", "oblique"):
            if base.endswith(style):
                base = base[: -len(style)]
        if base:
            families.add(base)
    return sorted(families)


def _candidate_names(family: str, language: str = "fa") -> list[str]:
    names: list[str] = []
    if family:
        names.append(family)
    names += FALLBACK_CHAINS.get(language, FALLBACK_CHAINS["fa"])
    names += [BUNDLED_FAMILY, "DejaVuSans"]
    seen: set[str] = set()
    ordered: list[str] = []
    for n in names:
        key = _normalize(n)
        if key and key not in seen:
            seen.add(key)
            ordered.append(n)
    return ordered


def resolve_font_path(family: str | None, weight: str = "regular", language: str = "fa") -> tuple[str, int]:
    """Return ``(path, face_index)`` for the best matching font file."""
    index = _font_index()
    weight = weight.lower()
    generic = {"bold", "black"} if weight in ("bold", "black", "extrabold") else {"regular"}
    if weight in ("light", "thin", "extralight"):
        generic = {"light", "regular"}

    for candidate in _candidate_names(family or "", language):
        base = _normalize(candidate)
        # 1. exact family + requested weight
        for suffix in ([weight, "regular", "book", "normal", ""] if weight else [""]):
            key = base + suffix
            if key in index:
                return index[key], 0
        # 2. family + any matching numeric face (DejaVuSans-Bold etc.)
        matches = [(k, v) for k, v in index.items() if k.startswith(base)]
        if matches:
            for want in ([weight, "bold", "black"] if weight in ("bold", "black", "extrabold") else [weight, "regular", "medium"]):
                for k, v in matches:
                    if k.endswith(want) or want in k:
                        return v, 0
            k, v = sorted(matches)[0]
            return v, 0
    # 3. absolute last resort: any font at all
    for key in ("dejavusans", "arial", "liberationsans", "notosans", "freesans"):
        if key in index:
            return index[key], 0
    if index:
        return sorted(index.items())[0][1], 0
    raise RuntimeError(
        "هیچ فونتی روی این سیستم پیدا نشد. فونت Vazirmatn را در assets/fonts بگذارید."
    )


def font_dirs() -> list[str]:
    return [str(d) for d in _font_dirs()]
