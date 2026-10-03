# -*- coding: utf-8 -*-
"""ÖSYM duyuru sayfalarından soru kitapçığı PDF'lerini indiren genel modül.

Eski sayfalarda (2010-2013) PDF'ler 'eskidosyalar/NNN.pdf' biçiminde numaralıdır
ve test adı bağlantı metninde taşınır; yeni sayfalarda URL'den anlaşılır.

Kullanım:
    python -m pipeline.downloaders.osym_general ygs_lys [--dry]
"""
import argparse
import html as htmllib
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
}
PDF_RE = re.compile(r'https?://dokuman\.osym\.gov\.tr/[^"\'<>]+?\.pdf', re.I)
A_RE = re.compile(
    r'<a[^>]+href="(https?://dokuman\.osym\.gov\.tr/[^"]+?\.pdf)"[^>]*>(.*?)</a>',
    re.S | re.I)
URL_FIX = lambda u: u.strip().replace(" ", "%20")  # noqa: E731

BASE = "https://www.osym.gov.tr/"

ANNOUNCEMENTS = {
    "ygs_lys": {
        "2010_ygs": BASE + "2010osys-ygs-sorulari-ve-cevaplari-20260511102204378",
        "2011_ygs": BASE + "2011osys-ygs-sorulari-ve-cevaplari",
        "2012_ygs": BASE + "2012ygs-soru-kitapcigi-ve-cevap-anahtari",
        "2013_ygs": BASE + "2013ygs-soru-kitapcigi-ve-cevap-anahtari",
        "2010_lys": BASE + "2010osys-lys-soru-kitapciklari-ve-cevap-anahtarlari",
        "2011_lys": BASE + "2011osys-lys-soru-kitapciklari-ve-cevap-anahtarlari",
        "2012_lys": BASE + "2012osys-lys-soru-kitapciklari-ve-cevap-anahtarlari",
        "2013_lys": BASE + "2013osys-lys-soru-kitapciklari-ve-cevap-anahtarlari",
        "2017_lys": BASE + "2017-lys-soru-kitapciklari-ve-cevap-anahtarlari",
    },
}

# Yeni sayfalarda URL'den oturum (2017 LYS test bazlı PDF'ler)
LYS_RE = re.compile(r"lys[-_\s]*(\d)", re.I)
SUBTEST_URL = [
    (re.compile(r"biyoloji", re.I), "biyoloji"),
    (re.compile(r"kimya", re.I), "kimya"),
    (re.compile(r"fizik", re.I), "fizik"),
    (re.compile(r"tarih", re.I), "tarih"),
    (re.compile(r"felsefe", re.I), "felsefe"),
    (re.compile(r"cografya2", re.I), "cografya2"),
    (re.compile(r"cografya", re.I), "cografya1"),
    (re.compile(r"turkdiliedebiyat|turkdili|edebiyat", re.I), "edebiyat"),
    (re.compile(r"geometri", re.I), "geometri"),
    (re.compile(r"almanca", re.I), "alm"),
    (re.compile(r"fransizca", re.I), "fra"),
    (re.compile(r"ingilizce", re.I), "ing"),
    (re.compile(r"matematik", re.I), None),
]

# Eski sayfalarda bağlantı metninden (test adı) oturum / anahtar eşlemesi.
# (regex, session, tur)  tur: 'kitap' | 'key'  — sıra önemli!
LINK_TEXT_MAP = [
    (re.compile(r"ön kapak|iç kapak|arka kapak|genel açıklama|menü", re.I), None, None),
    # 2010 LYS-5: 'X Testi Soruları' / 'X Testi Cevap Anahtarı' ayrı
    (re.compile(r"almanca testi sorular", re.I), "lys5_alm", "kitap"),
    (re.compile(r"fransızca testi sorular", re.I), "lys5_fra", "kitap"),
    (re.compile(r"ingilizce testi sorular", re.I), "lys5_ing", "kitap"),
    (re.compile(r"almanca testi cevap", re.I), "lys5_alm", "key"),
    (re.compile(r"fransızca testi cevap", re.I), "lys5_fra", "key"),
    (re.compile(r"ingilizce testi cevap", re.I), "lys5_ing", "key"),
    (re.compile(r"yabancı dil.*\(almanca\)|yabancı dil testi \(alm", re.I), "lys5_alm", "kitap"),
    (re.compile(r"yabancı dil.*\(fransızca\)", re.I), "lys5_fra", "kitap"),
    (re.compile(r"yabancı dil.*\(ingilizce\)", re.I), "lys5_ing", "kitap"),
    (re.compile(r"yabancı dil", re.I), "lys5_yabanci_dil", "kitap"),
    (re.compile(r"geometri testi", re.I), "lys1_geometri", "kitap"),
    (re.compile(r"temel matematik testi", re.I), "ygs_matematik", "kitap"),
    (re.compile(r"matematik testi", re.I), "lys1_matematik", "kitap"),
    (re.compile(r"fizik testi", re.I), "lys2_fizik", "kitap"),
    (re.compile(r"kimya testi", re.I), "lys2_kimya", "kitap"),
    (re.compile(r"biyoloji testi", re.I), "lys2_biyoloji", "kitap"),
    (re.compile(r"türk dili", re.I), "lys3_edebiyat", "kitap"),
    (re.compile(r"coğrafya-1", re.I), "lys3_cografya1", "kitap"),
    (re.compile(r"tarih testi", re.I), "lys4_tarih", "kitap"),
    (re.compile(r"coğrafya-2", re.I), "lys4_cografya2", "kitap"),
    (re.compile(r"felsefe", re.I), "lys4_felsefe", "kitap"),
    # YGS 2010: test parçaları + genel anahtar
    (re.compile(r"türkçe testi", re.I), "ygs_turkce", "kitap"),
    (re.compile(r"sosyal bilimler testi", re.I), "ygs_sosyal", "kitap"),
    (re.compile(r"fen bilimleri testi", re.I), "ygs_fen", "kitap"),
    (re.compile(r"soru kitapçığı", re.I), "ygs", "kitap"),
    (re.compile(r"cevap anahtarı", re.I), "__ALL__", "key"),
]

SKIP_RE = re.compile(r"yasakli|izinli|kilavuz|tabela|basvuru", re.I)


def session_from_text(text: str):
    """Eski sayfa bağlantı metni -> (session, tur)."""
    for pat, sess, kind in LINK_TEXT_MAP:
        if pat.search(text):
            return sess, kind
    return None, None


def session_from_url(url: str) -> str | None:
    if SKIP_RE.search(url):
        return None
    u = URL_FIX(url)
    m = LYS_RE.search(u)
    if m:
        n = m.group(1)
        for pat, sub in SUBTEST_URL:
            if pat.search(u):
                return f"lys{n}" + (f"_{sub}" if sub else "")
        return f"lys{n}"
    if re.search(r"ygs", u, re.I):
        return "ygs"
    return None


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=120)
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            print(f"  !! hata {r.status_code} / PDF değil: {url}")
            return False
        dest.write_bytes(r.content)
        print(f"  ✓ {dest.parent.name}/{dest.name} ({len(r.content) / 1e6:.1f} MB)")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  !! {url}: {e}")
        return False


def handle_page(label: str, url: str, raw: Path, manifest: dict, dry: bool):
    year = label.split("_")[0]
    html_txt = requests.get(url, headers=HEADERS, timeout=60).text

    pairs = []  # (url, text)
    for href, inner in A_RE.findall(html_txt):
        text = " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", inner)).split())
        if SKIP_RE.search(href):
            continue
        pairs.append((URL_FIX(href), text))
    if not pairs:  # yeni sayfa: URL'den oturum çıkar
        pairs = [(URL_FIX(u), "") for u in sorted(set(PDF_RE.findall(html_txt)))
                 if not SKIP_RE.search(u)]

    kitaps, keys = [], []
    for link, text in pairs:
        if text:
            sess, kind = session_from_text(text)
        else:
            sess, kind = session_from_url(link), "kitap"
        if sess is None and kind is None:
            continue  # kapak/menü gibi parçalar
        if kind == "key":
            keys.append((sess, link))
            continue
        kitaps.append((sess, link))

    # aynı URL iki oturuma denk geldiyse (mat+geom birleşik kitapçık) lys1'e
    # indir; oturum bazında tek dosya bırak
    by_url = {}
    for sess, link in kitaps:
        by_url.setdefault(link, []).append(sess)
    final, seen_sess = [], set()
    for sess, link in kitaps:
        owners = by_url[link]
        if len(owners) > 1 and "lys1_matematik" in owners \
                and "lys1_geometri" in owners:
            sess = "lys1"
        if sess in seen_sess:
            continue
        seen_sess.add(sess)
        final.append((sess, link))
    kitaps = final

    for sess, link in kitaps:
        dest = raw / f"{year}_{sess}" / "kitapcik.pdf"
        if dest.exists() and dest.stat().st_size > 100_000:
            print(f"  - mevcut: {year}_{sess}")
        else:
            print(f"  -> {sess}: {link}")
            if not dry and not download(link, dest):
                continue
        manifest[f"{year}_{sess}"] = link

    for sess, link in keys:
        if sess == "__ALL__":
            # yılın tüm oturumlarına anahtar olarak koy
            targets = [p for p in raw.glob(f"{year}_*/cevap_anahtari.pdf")]
            folders = [d for d in raw.glob(f"{year}_*") if d.is_dir()]
            for d in folders:
                dest = d / "cevap_anahtari.pdf"
                if not dest.exists():
                    print(f"  -> anahtar({d.name}): {link}")
                    if not dry:
                        download(link, dest)
        else:
            dest = raw / f"{year}_{sess}" / "cevap_anahtari.pdf"
            if not dest.exists():
                print(f"  -> anahtar({sess}): {link}")
                if not dry:
                    download(link, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("group", choices=sorted(ANNOUNCEMENTS))
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    raw = ROOT / "data" / "raw" / args.group
    manifest_path = raw / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {}

    for label, url in ANNOUNCEMENTS[args.group].items():
        print(f"{label}: {url}")
        try:
            handle_page(label, url, raw, manifest, args.dry)
        except Exception as e:  # noqa: BLE001
            print(f"  !! {e}")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                             encoding="utf-8")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    sys.exit(main())
