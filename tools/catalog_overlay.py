#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backup (mirror) stream servers and extra Persian channels for TakhtLive.

Why this file exists
--------------------
Live IPTV streams fail regularly: one CDN goes down, an origin rate-limits a
whole country, or a single edge node returns 403. Every channel listed in
`app/src/main/assets/channels.json` may therefore carry an optional
`mirrors` array with alternative servers of the *same* channel. The players
(Android/ExoPlayer and Windows/hls.js) try the main `url` first and then walk
through `mirrors` before they give up and show an error, so a channel keeps
working even when the primary server is unavailable.

This module owns that data so the catalog can be regenerated safely:

    python3 tools/catalog_overlay.py          # patch the bundled catalog
    python3 tools/sync_windows_assets.py      # copy it to the Windows app

`tools/curate_channels.py` also calls :func:`apply` at the end of its build so
a full re-curation keeps the mirrors and the extra channels.

All URLs below are public HLS endpoints taken from the upstream playlists in
`tools/curate_channels.py` (iptv-org/iptv, Samhouston010/persian-tv,
itsyebekhe/nexa, AdeelWajid/iptv_validated_list). Only servers that are known
to host the same channel are used as a mirror.
"""

from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET = os.path.join(ROOT, "app", "src", "main", "assets", "channels.json")

#: Date of the last manual curation of the data in this file.
UPDATED = "2026-10-26"

#: Catalog format version: 4 adds the optional `mirrors` array.
VERSION = 4

#: Alternative servers per channel id (the primary server stays `url`).
MIRRORS = {
    # ------------------------------------------------------------ پرشیانا گروپ
    "persiana-music": [
        "https://itthls.wns.live/hls/stream.m3u8",
    ],
    "persiana-medical": [
        "https://tfnhls.wns.live/hls/stream.m3u8",
    ],
    "persiana-travel": [
        "https://mardomhls.wns.live/hls/stream.m3u8",
    ],
    # ------------------------------------------------------------------ خبری
    "bbc-persian": [
        "https://vs-hls-pushb-ww-live.akamaized.net/x=4/i=urn:bbc:pips:service:bbc_persian_tv/pc_hd_abr_v2.m3u8",
        "https://vs-hls-pushb-ww-live.akamaized.net/x=4/i=urn:bbc:pips:service:bbc_persian_tv/mobile_wifi_main_hd_abr_v2.m3u8",
    ],
    "iran-international": [
        "https://dev-live.livetvstream.co.uk/LS-63503-4/index.m3u8",
    ],
    "voa-persian": [
        "https://voaphls.wns.live/hls/stream.m3u8",
    ],
    "press-tv": [
        "https://live.presstv.co.uk/hls/presstv.m3u8",
    ],
    "kalemeh-tv": [
        "https://klmhls.wns.live/hls/stream.m3u8",
    ],
    "al-alam": [
        "https://live2.alalam.ir/alalam.m3u8",
    ],
    # ------------------------------------------------------------------ موزیک
    "pmc": [
        "https://pmcrohls.wns.live/hls/stream.m3u8",
    ],
    "navahang": [
        "https://navahanghls.wns.live/hls/stream.m3u8",
    ],
    # ------------------------------------------------------------------ ورزشی
    "varzesh-tv": [
        "https://ncdn.telewebion.net/varzesh/live/playlist.m3u8",
    ],
}

#: Persian channels that were missing from the very first curated catalog.
#: They are inserted at the top of their section so they show up on the home
#: screen right away. Keep the four existing sections - no new top level group.
NEW_CHANNELS = [
    # ------------------------------------------------------------------ خبری
    {
        "id": "zed-tv",
        "name": "ضد تی‌وی",
        "nameEn": "Zed TV",
        "nameAr": "زد تي في",
        "category": "news",
        "logo": "",
        "url": "https://zedhls.wns.live/hls/stream.m3u8",
        "mirrors": [
            "https://zedhls.wns.live/hls/stream.m3u8",
        ],
        "quality": "HD",
    },
    {
        "id": "iran-farda",
        "name": "ایران فردا",
        "nameEn": "Iran e Farda",
        "nameAr": "إيران فردا",
        "category": "news",
        "logo": "",
        "url": "https://iranefardalive.com/stream/live.m3u8",
        "quality": "SD",
    },
    {
        "id": "iran-press",
        "name": "ایران پرس",
        "nameEn": "Iran Press",
        "nameAr": "إيران برس",
        "category": "news",
        "logo": "",
        "url": "https://live.presstv.ir/hls/presstv_5_482/index.m3u8",
        "quality": "SD",
    },
    {
        "id": "irinn-news",
        "name": "شبکه خبر (ایرین‌نیوز)",
        "nameEn": "IRINN News",
        "nameAr": "قناة الأخبار الإيرانية",
        "category": "news",
        "logo": "",
        "url": "https://ncdn.telewebion.ir/irinn2/live/playlist.m3u8",
        "mirrors": [
            "https://ncdn.telewebion.net/irinn2/live/playlist.m3u8",
        ],
        "quality": "HD",
    },
    # ------------------------------------------------------------ پرشیانا گروپ
    {
        "id": "persiana-emirates",
        "name": "پرشیانا امارات",
        "nameEn": "Persiana Emirates",
        "nameAr": "برشيانا الإمارات",
        "category": "persiana",
        "logo": "",
        "url": "https://pemirateshls.persiana.live/hls/stream.m3u8",
        "quality": "HD",
    },
    {
        "id": "ava-series",
        "name": "آوا سریال",
        "nameEn": "AVA Series",
        "nameAr": "آفا سيريز",
        "category": "persiana",
        "logo": "",
        "url": "https://avaserieshls.wns.live/hls/stream.m3u8",
        "quality": "HD",
    },
    {
        "id": "cafe-film",
        "name": "کافه فیلم",
        "nameEn": "Cafe Film",
        "nameAr": "كافيه فيلم",
        "category": "persiana",
        "logo": "",
        "url": "https://cafefhls.wns.live/hls/stream.m3u8",
        "quality": "HD",
    },
    {
        "id": "afra-film",
        "name": "افرا فیلم",
        "nameEn": "Afra Film",
        "nameAr": "أفرا فيلم",
        "category": "persiana",
        "logo": "",
        "url": "https://afrafhls.wns.live/hls/stream.m3u8",
        "mirrors": [
            "https://afrashls.wns.live/hls/stream.m3u8",
        ],
        "quality": "HD",
    },
    {
        "id": "classic-tv",
        "name": "کلاسیک تی‌وی",
        "nameEn": "Classic TV",
        "nameAr": "كلاسيك تي في",
        "category": "persiana",
        "logo": "",
        "url": "https://clshls.wns.live/hls/stream.m3u8",
        "quality": "HD",
    },
    {
        "id": "khalij-tv",
        "name": "خلیج تی‌وی",
        "nameEn": "Khalij TV",
        "nameAr": "خليج تي في",
        "category": "persiana",
        "logo": "",
        "url": "https://khalijhls.wns.live/hls/stream.m3u8",
        "quality": "HD",
    },
    # ------------------------------------------------------------------ موزیک
    {
        "id": "tapesh-tv",
        "name": "تپش",
        "nameEn": "Tapesh TV",
        "nameAr": "تابش",
        "category": "music",
        "logo": "",
        "url": "https://hls.tapeshtv.live/hls/stream.m3u8",
        "quality": "HD",
    },
    # ------------------------------------------------------------------ ورزشی
    {
        "id": "telewebion-sport-1",
        "name": "تلوبیون اسپرت ۱",
        "nameEn": "Telewebion Sport 1",
        "nameAr": "تليوبيون سبورت ١",
        "category": "sports",
        "logo": "",
        "url": "https://ncdn.telewebion.ir/sport1/live/playlist.m3u8",
        "mirrors": [
            "https://ncdn.telewebion.net/sport1/live/playlist.m3u8",
        ],
        "quality": "HD",
    },
    {
        "id": "telewebion-sport-2",
        "name": "تلوبیون اسپرت ۲",
        "nameEn": "Telewebion Sport 2",
        "nameAr": "تليوبيون سبورت ٢",
        "category": "sports",
        "logo": "",
        "url": "https://ncdn.telewebion.ir/sport2/live/playlist.m3u8",
        "mirrors": [
            "https://ncdn.telewebion.net/sport2/live/playlist.m3u8",
        ],
        "quality": "HD",
    },
    {
        "id": "telewebion-sport-3",
        "name": "تلوبیون اسپرت ۳",
        "nameEn": "Telewebion Sport 3",
        "nameAr": "تليوبيون سبورت ٣",
        "category": "sports",
        "logo": "",
        "url": "https://ncdn.telewebion.ir/sport3/live/playlist.m3u8",
        "mirrors": [
            "https://ncdn.telewebion.net/sport3/live/playlist.m3u8",
        ],
        "quality": "HD",
    },
]

#: Channels that were removed from the catalog (kept here so a rebuild from the
#: upstream playlists does not bring them back).
REMOVE_IDS = {"ava-tv"}

#: Small text fixes for the existing sections (the four ids never change).
CATEGORY_UPDATES = {
    "persiana": {
        "subtitle": "کانال‌های پرشیانا و سرگرمی فارسی",
        "subtitleEn": "Persiana group and Persian entertainment channels",
        "subtitleAr": "قنوات برشيانا والترفيه الفارسي",
    },
    "news": {
        "subtitle": "شبکه‌های خبری ایران و جهان",
        "subtitleEn": "Iranian and international news channels",
        "subtitleAr": "قنوات الأخبار الإيرانية والعالمية",
    },
}

NOTE = (
    "Channel list curated from iptv-org/iptv, Samhouston010/persian-tv, "
    "itsyebekhe/nexa and AdeelWajid/iptv_validated_list. Channels with "
    "'mirrors' are played from a backup server automatically when the main "
    "server fails."
)

SOURCES = [
    "https://github.com/iptv-org/iptv",
    "https://github.com/Samhouston010/persian-tv",
    "https://github.com/shayanline/iptv-iran",
    "https://github.com/itsyebekhe/nexa",
    "https://github.com/AdeelWajid/iptv_validated_list",
]


def _clean_mirrors(channel: dict) -> list:
    """Drops empty entries, the primary url itself and duplicates."""
    primary = (channel.get("url") or "").strip()
    cleaned = []
    for url in channel.get("mirrors") or []:
        url = (url or "").strip()
        if not url or url == primary or url in cleaned:
            continue
        cleaned.append(url)
    return cleaned


def apply(doc: dict) -> dict:
    """Applies mirrors, new channels and text updates to a parsed catalog."""
    categories = doc.get("categories") or []
    known = {c.get("id") for c in categories}

    # ------------------------------------------------------------- sections
    for category in categories:
        for key, value in CATEGORY_UPDATES.get(category.get("id"), {}).items():
            category[key] = value

    # ------------------------------------------------------------- channels
    existing = [c for c in (doc.get("channels") or []) if c.get("id") not in REMOVE_IDS]
    existing_ids = {c.get("id") for c in existing}
    extras = [dict(c) for c in NEW_CHANNELS if c.get("id") not in existing_ids]
    for channel in extras:
        if channel.get("category") not in known:
            raise SystemExit("unknown section for %s" % channel.get("id"))

    # New channels go to the top of their own section so they are on the home
    # screen without scrolling; the previous order is otherwise preserved.
    ordered = []
    for category in categories:
        cid = category.get("id")
        ordered.extend(c for c in extras if c.get("category") == cid)
    ordered.extend(existing)
    for channel in extras:
        if channel not in ordered:  # safety net, should not happen
            ordered.insert(0, channel)

    # -------------------------------------------------------------- mirrors
    for channel in ordered:
        channel["mirrors"] = _clean_mirrors(channel)
        if not channel["mirrors"]:
            channel.pop("mirrors")
    for channel in ordered:
        extra = MIRRORS.get(channel.get("id"))
        if not extra:
            continue
        merged = _clean_mirrors(
            {"url": channel.get("url"), "mirrors": (channel.get("mirrors") or []) + list(extra)}
        )
        if merged:
            channel["mirrors"] = merged
        else:
            channel.pop("mirrors", None)

    doc["channels"] = ordered
    doc["version"] = VERSION
    doc["updated"] = UPDATED
    doc["note"] = NOTE
    doc["sources"] = SOURCES
    return doc


def apply_file(path: str = ASSET) -> dict:
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    doc = apply(doc)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return doc


def main() -> None:
    doc = apply_file()
    channels = doc["channels"]
    mirrors = sum(1 for c in channels if c.get("mirrors"))
    print("wrote %s" % ASSET)
    print("channels: %d | with backup server: %d" % (len(channels), mirrors))
    for category in doc["categories"]:
        count = sum(1 for c in channels if c["category"] == category["id"])
        print("  %-9s %s (%d)" % (category["id"], category["title"], count))


if __name__ == "__main__":
    main()
