#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuilds `docs/CHANNELS.md` from `app/src/main/assets/channels.json`.

Run after changing the catalog:

    python3 tools/catalog_overlay.py
    python3 tools/make_channels_doc.py
"""

from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET = os.path.join(ROOT, "app", "src", "main", "assets", "channels.json")
DOC = os.path.join(ROOT, "docs", "CHANNELS.md")

TITLES_EN = {
    "persiana": "Persiana Group",
    "news": "News",
    "music": "Music",
    "sports": "Sports",
}


def main() -> None:
    with open(ASSET, encoding="utf-8") as handle:
        doc = json.load(handle)
    channels = doc["channels"]
    mirrored = [c for c in channels if c.get("mirrors")]

    lines = [
        "# فهرست کانال‌ها — TakhtLive",
        "",
        "این فایل به‌صورت خودکار از `app/src/main/assets/channels.json` ساخته می‌شود "
        "(`python3 tools/make_channels_doc.py`).",
        "",
        "مجموع: **%d کانال** در 4 بخش — **%d کانال** دارای سرور پشتیبان (mirror)"
        % (len(channels), len(mirrored)),
        "",
        "> اگر سرور اصلی یک کانال از کار بیفتد، پخش‌کننده به‌صورت خودکار سرورهای "
        "پشتیبان همان کانال را امتحان می‌کند؛ کانال فقط وقتی خطا نشان می‌دهد که "
        "همهٔ سرورها در دسترس نباشند.",
        "",
    ]

    for category in doc["categories"]:
        items = [c for c in channels if c["category"] == category["id"]]
        title_en = TITLES_EN.get(category["id"], category.get("titleEn", ""))
        lines.append(
            "## %s %s / %s (%d)" % (category["emoji"], category["title"], title_en, len(items))
        )
        lines.append("")
        lines.append("| # | کانال | English | کیفیت | سرور پشتیبان | آدرس پخش |")
        lines.append("|---|---|---|---|---|---|")
        for index, channel in enumerate(items, start=1):
            mirrors = channel.get("mirrors") or []
            backup = str(len(mirrors)) if mirrors else "—"
            lines.append(
                "| %d | %s | %s | %s | %s | `%s` |"
                % (
                    index,
                    channel["name"],
                    channel.get("nameEn", ""),
                    channel.get("quality", "HD"),
                    backup,
                    channel["url"],
                )
            )
        lines.append("")

    with open(DOC, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    print("wrote %s" % DOC)
    print("channels: %d | with backup server: %d" % (len(channels), len(mirrored)))


if __name__ == "__main__":
    main()
