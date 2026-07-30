#!/usr/bin/env python3
"""Fetch the free Poly Haven assets this project uses.

Plain Python, not a Blender script - run it with `python3 scripts/fetch_polyhaven.py`
from the project root.

Poly Haven is CC0 and needs no account, no key and no payment. The paid
membership is a donation to the artists and buys no extra access.

`assets/` is gitignored, so a fresh clone has none of this. Running this script
restores everything except the Envato items, which are licensed per-account and
have to be downloaded through a logged-in browser. See docs/assets.md.

Everything is fetched at 2K. 4K sets across a full interior thrash 16 GB of
unified memory, and at the camera distances in this scene the difference is not
visible.
"""

import json
import os
import sys
import urllib.request

API = "https://api.polyhaven.com"
HEADERS = {"User-Agent": "OvalOfficeBlender/1.0 (+https://github.com/Konadu-Akwasi-Akuoko/oval-office-blender)"}
RESOLUTION = "2k"
OUT = "assets/polyhaven"

# Chosen by the research fan-out, which inspected the preview renders and
# rejected poor matches rather than taking the top search hit.
WANTED = {
    "textures": [
        ("herringbone_parquet", "floor"),
        ("dark_wood", "Resolute desk, mahogany chest"),
        ("velour_velvet", "sofas"),
        ("dirty_carpet", "rug weave base"),
        ("beige_wall_001", "plaster"),
    ],
    "hdris": [("symmetrical_garden_02", "daylight through the south windows")],
    "models": [("vintage_grandfather_clock_01", "tall case clock")],
}

MAPS = ("Diffuse", "nor_gl", "Rough", "AO", "Displacement", "arm", "rough_ao")


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS)) as r:
        return json.load(r)


def download(url, path):
    if os.path.exists(path):
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS)) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def fetch(kind, slug):
    files = get_json(f"{API}/files/{slug}")
    total, count = 0, 0

    if kind == "hdris":
        url = files["hdri"][RESOLUTION]["hdr"]["url"]
        total += download(url, f"{OUT}/hdri/{slug}_{RESOLUTION}.hdr")
        count += 1

    elif kind == "models":
        blend = files.get("blend", {}).get(RESOLUTION, {}).get("blend")
        if not blend:
            return 0, 0
        total += download(blend["url"], f"{OUT}/models/{slug}/{slug}_{RESOLUTION}.blend")
        count += 1
        # Blend files reference their textures by relative path, so the includes
        # must land alongside or the model opens with pink materials.
        for name, inc in blend.get("include", {}).items():
            total += download(inc["url"], f"{OUT}/models/{slug}/{name}")
            count += 1

    else:
        for m in MAPS:
            entry = files.get(m, {}).get(RESOLUTION, {})
            src = entry.get("jpg") or entry.get("png") or entry.get("exr")
            if src:
                ext = os.path.splitext(src["url"])[1]
                total += download(src["url"], f"{OUT}/textures/{slug}/{slug}_{m}_{RESOLUTION}{ext}")
                count += 1

    return total, count


def main():
    grand = 0
    for kind, items in WANTED.items():
        for slug, purpose in items:
            size, count = fetch(kind, slug)
            grand += size
            state = "cached" if size == 0 else f"{size / 1024 / 1024:.1f} MB"
            print(f"  {slug:<32} {count:>2} files  {state:>10}   {purpose}")
    print(f"\nDownloaded {grand / 1024 / 1024:.1f} MB into {OUT}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
