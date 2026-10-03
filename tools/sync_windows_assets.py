#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Syncs the shared assets (channel list and fonts) from the Android app into the
Windows app folder, so both versions always ship the same channels.

Icons are NOT generated here: they are derived from the master artwork by
tools/make_logo_assets.py (run that one when brand/takhtlive-mark.png changes).

Usage:  python3 tools/sync_windows_assets.py
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_RES = os.path.join(ROOT, "app", "src", "main", "res")
ANDROID_ASSETS = os.path.join(ROOT, "app", "src", "main", "assets")
WINDOWS = os.path.join(ROOT, "windows")

copy_plan = [
    (os.path.join(ANDROID_ASSETS, "channels.json"),
     os.path.join(WINDOWS, "assets", "channels.json")),
    (os.path.join(ANDROID_RES, "font", "vazirmatn_regular.ttf"),
     os.path.join(WINDOWS, "assets", "fonts", "vazirmatn_regular.ttf")),
    (os.path.join(ANDROID_RES, "font", "vazirmatn_medium.ttf"),
     os.path.join(WINDOWS, "assets", "fonts", "vazirmatn_medium.ttf")),
    (os.path.join(ANDROID_RES, "font", "vazirmatn_bold.ttf"),
     os.path.join(WINDOWS, "assets", "fonts", "vazirmatn_bold.ttf")),
]

# produced by tools/make_logo_assets.py from brand/takhtlive-mark.png
icon_files = [
    os.path.join(WINDOWS, "assets", "icon-512.png"),
    os.path.join(WINDOWS, "assets", "icon-256.png"),
    os.path.join(WINDOWS, "assets", "icon-192.png"),
    os.path.join(WINDOWS, "assets", "brand-256.png"),
    os.path.join(WINDOWS, "assets", "favicon-64.png"),
    os.path.join(WINDOWS, "build", "icon.ico"),
]


def copy_assets():
    for src, dst in copy_plan:
        if not os.path.exists(src):
            sys.exit("missing source asset: %s" % src)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        print("copied %s -> %s" % (os.path.relpath(src, ROOT), os.path.relpath(dst, ROOT)))


def check_icons():
    missing = [path for path in icon_files if not os.path.exists(path)]
    if missing:
        sys.exit("missing icon files (run tools/make_logo_assets.py):\n  "
                 + "\n  ".join(os.path.relpath(p, ROOT) for p in missing))
    print("icons ok (%d files, from brand/takhtlive-mark.png)" % len(icon_files))


def main():
    copy_assets()
    check_icons()


if __name__ == "__main__":
    main()
