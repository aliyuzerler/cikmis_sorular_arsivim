# -*- coding: utf-8 -*-
"""YKS (2018-2026) TYT/AYT/YDT soru kitapçıklarını ÖSYM'den indirir.

Her duyuru sayfasından dokuman.osym.gov.tr PDF bağlantıları ayıklanır.
Kullanım:  python -m pipeline.downloaders.yks [--year 2024] [--dry]
"""
import argparse
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "yks"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
}

ANNOUNCEMENTS = {
    2018: "https://www.osym.gov.tr/2018yks-tyt-ayt-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari",
    2019: "https://www.osym.gov.tr/2019yks-tyt-ayt-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari",
    2020: "https://www.osym.gov.tr/2020yks-tyt-ayt-ve-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari",
    2021: "https://www.osym.gov.tr/2021yks-tyt-ayt-ve-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari",
    2022: "https://www.osym.gov.tr/2022yks-tyt-ayt-ve-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari",
    2023: "https://www.osym.gov.tr/2023yks-tyt-ayt-ve-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari",
    2024: "https://www.osym.gov.tr/2024yks-tyt-ayt-ve-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari",
    2025: "https://www.osym.gov.tr/2025yks-tyt-ayt-ve-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari",
    2026: "https://www.osym.gov.tr/2026yks-tyt-ayt-ve-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari",
}

PDF_RE = re.compile(r'https?://dokuman\.osym\.gov\.tr/[^\s"\'<>]+?\.pdf', re.I)

# ydt dil kodları: kısaltmalar + tam adlar
LANG_RE = re.compile(
    r"ydt[_\-]?(alm|almanca|arp|arapça|arapca|fra|fransizca|frn|ing|ingilizce"
    r"|rus|rusca)", re.I)
LANG_NORM = {"alm": "alm", "almanca": "alm", "arp": "arp", "arapça": "arp",
             "arapca": "arp", "fra": "fra", "fransizca": "fra", "frn": "fra",
             "ing": "ing", "ingilizce": "ing", "rus": "rus", "rusca": "rus"}


def session_for(url: str) -> str | None:
    u = url.lower()
    if "_grm_" in u:
        return None  # mazeret/ek sınav kitapçıkları, ana arşive dahil değil
    stem = Path(u).stem.lower()
    m = LANG_RE.search(u)
    if m:
        return f"ydt_{LANG_NORM[m.group(1).lower()]}"
    if "tyt" in stem or "_tyt" in u:
        return "tyt"
    if "ayt" in stem or "_ayt" in u:
        return "ayt"
    if "ydt" in stem:
        return "ydt"
    return None


def extract_links(html: str) -> list[str]:
    return sorted(set(PDF_RE.findall(html)))


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=120)
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            print(f"  !! hata {r.status_code} / PDF değil: {url}")
            return False
        dest.write_bytes(r.content)
        print(f"  ✓ {dest.name} ({len(r.content) / 1e6:.1f} MB)")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  !! {url}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    years = [args.year] if args.year else sorted(ANNOUNCEMENTS)
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {}

    for year in years:
        url = ANNOUNCEMENTS[year]
        print(f"{year}: {url}")
        try:
            html = requests.get(url, headers=HEADERS, timeout=60).text
        except Exception as e:  # noqa: BLE001
            print(f"  !! duyuru sayfası alınamadı: {e}")
            continue
        links = extract_links(html)
        if not links:
            print("  !! PDF bağlantısı bulunamadı")
            continue
        for link in links:
            sess = session_for(link)
            if not sess:
                continue
            dest = RAW / f"{year}_{sess}" / "kitapcik.pdf"
            if dest.exists() and dest.stat().st_size > 100_000:
                print(f"  - mevcut: {year}_{sess}")
                manifest[f"{year}_{sess}"] = link
                continue
            print(f"  -> {sess}: {link}")
            if not args.dry and download(link, dest):
                manifest[f"{year}_{sess}"] = link

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                             encoding="utf-8")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    sys.exit(main())
