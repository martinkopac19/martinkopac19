#!/usr/bin/env python3
"""Stiahne vsetky fotky z verejneho alba na rajce.idnes.cz (rajce.net).

Pouzitie:
    python3 rajce_download.py <URL alba> [-o priecinok] [--png] [--thumbs]

Priklad:
    python3 rajce_download.py https://www.rajce.idnes.cz/album/zKYw5qA7tOXZmhcK -o fotky

Funguje s beznou instalaciou Pythonu 3 (bez dalsich kniznic).
Prepinac --png navyse prekonvertuje stiahnute JPEG-y na PNG - vyzaduje Pillow
(pip install pillow). Pozor: PNG z JPEG-u nezvysi kvalitu, len nafukne velkost,
takze ho pouzi len ak PNG naozaj potrebujes.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def build_opener() -> urllib.request.OpenerDirector:
    """Opener s cookies - zdielacie odkazy (/album/<hash>) nastavuju session cookie."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", UA), ("Accept-Language", "cs,sk;q=0.9")]
    return opener


def fetch(opener, url: str) -> tuple[str, str]:
    """Vrati (text stranky, finalna URL po presmerovaniach)."""
    with opener.open(url, timeout=60) as resp:
        raw = resp.read()
        final_url = resp.geturl()
    charset = "utf-8"
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:4000], re.I)
    if m:
        charset = m.group(1).decode("ascii", "ignore")
    return raw.decode(charset, "replace"), final_url


def parse_album(html: str, page_url: str) -> tuple[str, list[dict]]:
    """Zo stranky alba vytiahne zakladnu URL uloziska a zoznam fotiek."""
    storage = ""
    m = re.search(r'var\s+storage\s*=\s*"([^"]+)"', html)
    if m:
        storage = m.group(1)

    photos: list[dict] = []
    m = re.search(r'var\s+photos\s*=\s*(\[.*?\]);\s*\n', html, re.S)
    if m:
        try:
            photos = json.loads(m.group(1))
        except json.JSONDecodeError:
            photos = []

    if not photos:
        # Zalozny postup: povytahuj mena suborov priamo z HTML.
        names = re.findall(r'/(?:images|thumb)/([^"\'?\s/]+\.(?:jpe?g|png|gif|mp4))',
                           html, re.I)
        seen: set[str] = set()
        for name in names:
            if name.lower() not in seen:
                seen.add(name.lower())
                photos.append({"fileName": name})

    if not storage:
        m = re.search(r'https?://[^"\']+?\.rajce\.idnes\.cz/[^"\']*?/(?=images/)', html)
        storage = m.group(0) if m else page_url.rstrip("/") + "/"

    return storage, photos


def download(opener, url: str, dest: str) -> bool:
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  = uz existuje: {os.path.basename(dest)}")
        return True
    try:
        with opener.open(url, timeout=120) as resp, open(dest, "wb") as out:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"  ! zlyhalo {os.path.basename(dest)}: {exc}")
        if os.path.exists(dest):
            os.remove(dest)
        return False
    print(f"  + {os.path.basename(dest)} ({os.path.getsize(dest) // 1024} kB)")
    return True


def to_png(path: str) -> None:
    try:
        from PIL import Image
    except ImportError:
        print("  ! Pillow nie je nainstalovane (pip install pillow) - PNG preskocene")
        raise SystemExit(2)
    target = os.path.splitext(path)[0] + ".png"
    if os.path.exists(target):
        return
    with Image.open(path) as img:
        img.convert("RGB").save(target, "PNG", optimize=True)
    print(f"  > {os.path.basename(target)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stiahne fotky z alba na rajce.idnes.cz")
    ap.add_argument("url", help="URL alba")
    ap.add_argument("-o", "--out", default="rajce_fotky", help="cielovy priecinok")
    ap.add_argument("--png", action="store_true", help="prekonvertovat na PNG (vyzaduje Pillow)")
    ap.add_argument("--thumbs", action="store_true", help="stiahnut nahlady namiesto originalov")
    args = ap.parse_args()

    opener = build_opener()
    print(f"Nacitavam album: {args.url}")
    try:
        html, final_url = fetch(opener, args.url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"Album sa nepodarilo nacitat: {exc}", file=sys.stderr)
        return 1

    storage, photos = parse_album(html, final_url)
    if not photos:
        print("V stranke sa nenasli ziadne fotky - je album verejny? "
              "Skus otvorit URL v prehliadaci.", file=sys.stderr)
        return 1

    sub = "thumb" if args.thumbs else "images"
    base = urllib.parse.urljoin(storage if storage.endswith("/") else storage + "/", sub + "/")
    os.makedirs(args.out, exist_ok=True)
    print(f"Najdenych fotiek: {len(photos)}")
    print(f"Ulozisko: {base}")
    print(f"Ukladam do: {os.path.abspath(args.out)}")

    ok = 0
    for i, photo in enumerate(photos, 1):
        name = photo.get("fileName") or photo.get("filename")
        if not name:
            continue
        print(f"[{i}/{len(photos)}]", end=" ")
        dest = os.path.join(args.out, name)
        if download(opener, base + urllib.parse.quote(name), dest):
            ok += 1
            if args.png and re.search(r"\.jpe?g$", name, re.I):
                to_png(dest)

    print(f"\nHotovo: {ok}/{len(photos)} suborov v {os.path.abspath(args.out)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
