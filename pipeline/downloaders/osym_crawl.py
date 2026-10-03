# -*- coding: utf-8 -*-
"""ÖSYM duyuru menülerini tarayıp 'Temel Soru Kitapçığı' PDF'lerini indirir.

KPSS ve ALES için menü sayfalarından tüm yılların duyuruları otomatik
bulunur; YDS/MSÜ/DGS için duyuru adresleri EXTRA_URLS ile verilir.
Her duyurudan dokuman.osym.gov.tr PDF bağlantıları çıkarılır; oturum adı
duyuru adresinden (slug) türetilir.

Kullanım:
    python -m pipeline.downloaders.osym_crawl [kpss ales yds msu dgs] [--dry]
"""
import argparse
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
A_RE = re.compile(r'href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
URL_FIX = lambda u: u.strip().replace(" ", "%20")  # noqa: E731

BASE = "https://www.osym.gov.tr"

MENU_PAGES = {
    "kpss": BASE + "/SinavGrubu/Menu/344",
    "ales": BASE + "/SinavGrubu/Menu/392",
    "msu": BASE + "/SinavGrubu/Menu/1559",
}

_K = lambda slug: BASE + "/" + slug  # noqa: E731

EXTRA_URLS = {
    "kpss": [
        # 2026
        _K("2026-kpss-a-grubu-alan-bilgisi-1-oturum-2-oturum-ve-3-oturum-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2026-kpss-lisansgenel-yetenek-genel-kultur-temel-soru-kitapcigi-ve-cevap-anahtari-10"),
        # 2025
        _K("2025kpss-a-grubu-alan-bilgisi-1-oturum-2-oturum-ve-3-oturum-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2025kpss-a-grubu-sinavi-genel-yetenekgenel-kultur-temel-soru-kitapcigi-ve-cevap-anahtari-10"),
        # 2024
        _K("2024kpss-din-hizmetleri-alan-bilgisi-dhbt-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2024kpss-ortaogretim-temel-soru-kitapcigi-ve-cevap-anahtari-10"),
        _K("2024kpss-on-lisans-temel-soru-kitapcigi-ve-cevap-anahtari-10"),
        _K("2024kpss-lisans-ogretmenlik-alan-bilgisi-testi-oabt-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2024kpss-a-grubu-alan-bilgisi-1-oturum-2-oturum-ve-3-oturum-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2024kpss-lisans-genel-yetenekgenel-kultur-ve-egitim-bilimleri-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        # 2023
        _K("2023kpss-lisans-ogretmenlik-alan-bilgisi-testi-oabt-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2023kpss-a-grubu-alan-bilgisi-1-oturum-2-oturum-ve-3-oturum-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2023kpss-a-grubu-ve-ogretmenlik-sinavigenel-yetenekgenel-kultur-ve-egitim-bilimleri-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        # 2022
        _K("2022kpss-din-hizmetleri-alan-bilgisi-dhbt-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2022kpss-ortaogretim-temel-soru-kitapcigi-ve-cevap-anahtari-10"),
        _K("2022kpss-on-lisans-temel-soru-kitapcigi-ve-cevap-anahtari-10"),
        _K("2022kpss-lisans-ogretmenlik-alan-bilgisi-testi-oabt-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2022kpss-a-grubu-alan-bilgisi-1-oturum-2-oturum-ve-3-oturum-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2022kpss-lisans-genel-yetenekgenel-kultur-ve-egitim-bilimleri-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2022kpss-lisans-genel-yetenekgenel-kultur-ve-egitim-bilimleri-temel-soru-kitapciklari-ve-cevap-anahtarlari-10-20260508155709736"),
        # 2021
        _K("2021kpss-ogretmenlik-alan-bilgisi-testi-oabt-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2021kpss-a-grubu-alan-bilgisi-1-oturum-2-oturum-ve-3-oturum-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2021kpss-lisans-genel-yetenekgenel-kultur-ve-egitim-bilimleri-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        # 2018
        _K("2018kpss-din-hizmetleri-alan-bilgisi-dhbt-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2018kpss-on-lisans-temel-soru-kitapcigi-ve-cevap-anahtari-10"),
        _K("2018kpss-ortaogretim-temel-soru-kitapcigi-ve-cevap-anahtari-10"),
        _K("2018kpss-ogretmenlik-alan-bilgisi-testi-oabt-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2018kpss-lisans-alan-bilgisi-1-oturum-2-oturum-ve-3-oturum-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
        _K("2018kpss-lisans-genel-yetenekgenel-kultur-ve-egitim-bilimleri-temel-soru-kitapciklari-ve-cevap-anahtarlari-10"),
    ],
    "ales": [
        _K("2025ales1-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi"),
        _K("2025ales3-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi"),
        _K("2026ales1-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi"),
        _K("2026-ales2-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi"),
        _K("2023ales2-sinavi-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi"),
    ],
    "yds": [
        BASE + "/2026yds1-temel-soru-kitapciklari-ve-cevap-anahtarlari-yayimlandi",
        BASE + "/2026yds2-temel-soru-kitapciklari-ve-cevap-anahtarlari-yayimlandi",
        BASE + "/2025yds1-temel-soru-kitapciklari-ve-cevap-anahtarlari-yayimlandi",
        BASE + "/TR,33675/2025-yds2-temel-soru-kitapciklari-ve-cevap-anahtarlari",
        BASE + "/2025ydsingilizce-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
        BASE + "/2024yds2-temel-soru-kitapciklari-ve-cevap-anahtarlari-yayimlandi",
        BASE + "/2026yokdil1-temel-soru-kitapciklari-ve-cevap-anahtarlari-yayimlandi",
        BASE + "/2026yokdil2-temel-soru-kitapciklari-ve-cevap-anahtarlari-yayimlandi",
        BASE + "/2025yokdil1-temel-soru-kitapciklari-ve-cevap-anahtarlari-yayimlandi",
        BASE + "/2025yokdil2-temel-soru-kitapciklari-ve-cevap-anahtarlari-yayimlandi",
    ],
    "msu": [
        BASE + "/2026msu-sinavi-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
        BASE + "/2025msu-sinavi-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
        BASE + "/2024msu-sinavi-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
        BASE + "/2023msu-sinavi-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
        BASE + "/2022msu-sinavi-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
    ],
    "dgs": [
        BASE + "/2026dgs-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
        BASE + "/2025dgs-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
        BASE + "/2024dgs-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
        BASE + "/2023dgs-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
        BASE + "/2022dgs-temel-soru-kitapcigi-ve-cevap-anahtari-yayimlandi",
    ],
}


def session_for(exam: str, slug: str) -> str | None:
    """Duyuru adresinden oturum kimliği türetir."""
    s = slug.lower()
    if exam == "kpss":
        if "dhbt" in s:
            return "dhbt"
        if "oabt" in s or "alan-bilgisi-testi" in s:
            return "oabt"
        if "ortaogretim" in s:
            return "ortaogretim"
        if "on-lisans" in s:
            return "onlisans"
        if "alan-bilgisi" in s:
            return "a_alan"
        if "genel-yetenek" in s:
            return "lisans"
        return None
    if exam == "ales":
        m = re.search(r"ales[-_]?([123])", s)
        return f"ales_{m.group(1)}" if m else "ales_2"
    if exam == "yds":
        if re.search(r"yds[-_]?1", s):
            return "yds_1"
        if re.search(r"yds[-_]?2", s):
            return "yds_2"
        for tr, code in [("ingilizce", "ing"), ("almanca", "alm"),
                         ("fransizca", "fra"), ("rusca", "rus"),
                         ("arapca", "arp")]:
            if tr in s:
                return f"yds_{code}"
        if "eyds" in s.replace("-", ""):
            return "eyds"
        return None
    if exam in ("msu", "dgs"):
        return exam
    return None


def discover_announcements(exam: str) -> list[str]:
    urls = list(EXTRA_URLS.get(exam, []))
    menu = MENU_PAGES.get(exam)
    if menu:
        try:
            html = requests.get(menu, headers=HEADERS, timeout=90).text
            for href, _ in A_RE.findall(html):
                if "temel-soru-kitapcig" not in href.lower():
                    continue
                if href.startswith("/"):
                    href = BASE + href
                elif not href.startswith("http"):
                    continue
                href = href.rstrip("/")
                if href not in urls:
                    urls.append(href)
        except Exception as e:  # noqa: BLE001
            print(f"!! menü okunamadı: {e}")
    return sorted(set(urls))


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=120)
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            print(f"    !! hata {r.status_code} / PDF değil: {url}")
            return False
        dest.write_bytes(r.content)
        print(f"    ✓ {dest.parent.name}/{dest.name} ({len(r.content)/1e6:.1f} MB)")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"    !! {url}: {e}")
        return False


EXAM_TOKEN = {"kpss": "KPSS", "ales": "ALES", "yds": "YDS",
              "msu": "MSÜ", "dgs": "DGS"}

# PDF dosya adından konu/ad soneki ('bedenegitimi06082023.pdf' -> 'bedenegitimi')
SUBJ_RE = re.compile(r"([a-zçğıöşüA-ZÇĞİÖŞÜ]{4,20})\d", re.I)


def subject_from_url(url: str) -> str | None:
    name = url.rstrip("/").rsplit("/", 1)[-1].lower()
    m = SUBJ_RE.search(name)
    return m.group(1).lower() if m else None


def process_exam(exam: str, dry: bool):
    raw = ROOT / "data" / "raw" / exam
    manifest_path = raw / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {}

    announcements = discover_announcements(exam)
    token = EXAM_TOKEN.get(exam, exam.upper())
    print(f"{exam}: {len(announcements)} duyuru")
    for ann in announcements:
        slug = ann.rstrip("/").rsplit("/", 1)[-1]
        m = re.match(r"^(\d{4})", slug)
        if not m:
            continue
        year = m.group(1)
        sess = session_for(exam, slug)
        if not sess:
            print(f"  ? oturum çözülemedi, atlandı: {slug[:60]}")
            continue
        try:
            r = requests.get(ann, headers=HEADERS, timeout=90)
        except Exception as e:  # noqa: BLE001
            print(f"  !! duyuru okunamadı {slug[:50]}: {e}")
            continue
        # doğrulama: var olmayan duyurular anasayfaya yönlendiriliyor.
        # Kanonik adres ya 'temel-soru' içerir ya /TR,<id>/ biçimine döner.
        canon = "temel-soru" in r.url.lower() or re.search(
            r"/TR,\d+/", r.url) is not None
        if r.status_code != 200 or not canon or token not in r.text:
            print(f"  x geçersiz duyuru (yönlendirme/içerik yok): {slug[:60]}")
            continue
        html = r.text
        links = [URL_FIX(u) for u in sorted(set(PDF_RE.findall(html)))
                 if not re.search(r"yasakli|izinli|kilavuz|tabela|basvuru|"
                                  r"formu|merkezleri|kılavuz|rehber|kontenjan|"
                                  r"genel-bilgiler|adres", u, re.I)]
        if not links:
            print(f"  - PDF yok: {slug[:60]}")
            continue
        seen_suffix = set()
        for i, link in enumerate(links, 1):
            subj = subject_from_url(link)
            suffix = subj if (subj and subj not in seen_suffix) else str(i)
            seen_suffix.add(suffix)
            sess_i = sess if len(links) == 1 else f"{sess}_{suffix}"
            dest = raw / f"{year}_{sess_i}" / "kitapcik.pdf"
            if dest.exists() and dest.stat().st_size > 50_000:
                print(f"  - mevcut: {year}_{sess_i}")
                manifest[f"{year}_{sess_i}"] = link
                continue
            print(f"  -> {year}_{sess_i}: {link}")
            if not dry and download(link, dest):
                manifest[f"{year}_{sess_i}"] = link

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                             encoding="utf-8")
    print(f"manifest: {manifest_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exams", nargs="*",
                    default=["kpss", "ales", "yds", "msu", "dgs"])
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    for exam in args.exams:
        process_exam(exam, args.dry)


if __name__ == "__main__":
    sys.exit(main())
