"""Persian/Arabic text shaping and RTL line wrapping.

Pillow on a bare Linux box is usually built without libraqm, so ``direction``
and ``font features`` are unavailable.  We therefore shape the text ourselves
(``arabic-reshaper`` for the presentation forms + ``python-bidi`` for the
bidirectional reordering) and draw the already-visual string.
"""
from __future__ import annotations

import re
from functools import lru_cache

import arabic_reshaper
from bidi.algorithm import get_display

RTL_RANGES = (
    (0x0590, 0x05FF),   # Hebrew
    (0x0600, 0x06FF),   # Arabic
    (0x0700, 0x074F),   # Syriac
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB1D, 0xFB4F),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)

# Characters that must not be turned into their joined presentation forms.
_NO_BREAK = "\u200c"  # ZWNJ

_RESHApER_CONFIG = {
    "delete_harakat": False,
    "support_ligatures": True,
    "use_unshaped_instead_of_isolated": True,
}

_ANSI_RE = re.compile(r"[\u202a-\u202e\u2066-\u2069]")


@lru_cache(maxsize=4096)
def _reshape(text: str) -> str:
    try:
        return arabic_reshaper.reshape(text, configuration=_RESHApER_CONFIG)
    except Exception:  # pragma: no cover - defensive
        try:
            return arabic_reshaper.reshape(text)
        except Exception:
            return text


@lru_cache(maxsize=4096)
def shape(text: str, rtl: bool = True) -> str:
    """Return a *visual* (ready-to-draw) string."""
    if not text:
        return ""
    clean = _ANSI_RE.sub("", text)
    reshaped = _reshape(clean) if _has_arabic(clean) else clean
    try:
        return get_display(reshaped, base_dir="R" if rtl else "L")
    except Exception:  # pragma: no cover - defensive
        return reshaped


def _has_arabic(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        for lo, hi in RTL_RANGES:
            if lo <= code <= hi:
                return True
    return False


def is_rtl_text(text: str) -> bool:
    rtl = 0
    latin = 0
    for ch in text:
        code = ord(ch)
        if any(lo <= code <= hi for lo, hi in RTL_RANGES):
            rtl += 1
        elif ch.isalpha() and code < 0x590:
            latin += 1
    return rtl >= latin


def visual_lines(lines: list[str], rtl: bool = True) -> list[str]:
    return [shape(line, rtl=rtl) for line in lines]
