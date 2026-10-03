# -*- coding: utf-8 -*-
"""MEB LGS (2018-2025) soru kitapçıklarını indirir.

Kaynaklar: ODSGM/meb.gov.tr/cdn.eba.gov.tr resmî PDF'leri (A kitapçığı,
cevap anahtarlı).

Kullanım:  python -m pipeline.downloaders.meb [--year 2024] [--dry]
"""
import argparse
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "lgs"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
}

# (yıl, oturum) -> [sözel PDF, sayısal PDF]
BOOKLETS = {
    (2018, "sozel"): "https://odsgm.meb.gov.tr/meb_iys_dosyalar/2018_06/03153730_SYZEL_BYLYM_A_kitapYY.pdf",
    (2018, "sayisal"): "https://odsgm.meb.gov.tr/meb_iys_dosyalar/2018_06/03153730_SAYISAL_BYLYM_A_kitapYY.pdf",
    (2019, "sozel"): "https://www.meb.gov.tr/meb_iys_dosyalar/2019_06/02125953_2019_SOZEL_BOLUM.pdf",
    (2019, "sayisal"): "https://www.meb.gov.tr/meb_iys_dosyalar/2019_06/02130019_2019_SAYISAL_BOLUM.pdf",
    (2020, "sozel"): "https://www.meb.gov.tr/meb_iys_dosyalar/2020_06/21195531_2020_sozel_bolum_a.pdf",
    (2020, "sayisal"): "https://www.meb.gov.tr/meb_iys_dosyalar/2020_06/21195513_2020_sayisal_bolum_a.pdf",
    (2021, "sozel"): "https://cdn.eba.gov.tr/icerik/lgs/2021_SOZEL_BOLUM_A_.pdf",
    (2021, "sayisal"): "https://cdn.eba.gov.tr/icerik/lgs/2021_SAYISAL_BOLUM_A_.pdf",
    (2022, "sozel"): "https://cdn.eba.gov.tr/icerik/lgs/2022_sozel_bolum_a_kitapcigi_ve_cevap_anahtari.pdf",
    (2022, "sayisal"): "https://cdn.eba.gov.tr/icerik/lgs/2022_sayisal_bolum_a_kitapcigi_ve_cevap_anahtari.pdf",
    (2023, "sozel"): "https://msyo.meb.k12.tr/meb_iys_dosyalar/61/02/727852/dosyalar/2023_06/05095005_2023-LGS-SOZEL-KITAPCIGI.pdf",
    (2023, "sayisal"): "https://msyo.meb.k12.tr/meb_iys_dosyalar/61/02/727852/dosyalar/2023_06/05095020_2023-LGS-SAYISAL-KITAPCIGI.pdf",
    (2024, "sozel"): "https://msyo.meb.k12.tr/meb_iys_dosyalar/61/02/727852/dosyalar/2024_06/03121642_2024sozelakitapcik.pdf",
    (2024, "sayisal"): "https://msyo.meb.k12.tr/meb_iys_dosyalar/61/02/727852/dosyalar/2024_06/03121642_2024sayisalakitapcik.pdf",
    (2025, "sozel"): "https://hasanunlukahramanoo.meb.k12.tr/meb_iys_dosyalar/79/01/976865/dosyalar/2025_10/28084845_2025sozel.pdf",
    (2025, "sayisal"): "https://hasanunlukahramanoo.meb.k12.tr/meb_iys_dosyalar/79/01/976865/dosyalar/2025_10/28084928_2025sayi.pdf",
}


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=120)
        ct = r.headers.get("Content-Type", "")
        if r.status_code != 200 or (not r.content.startswith(b"%PDF")
                                    and "pdf" not in ct.lower()):
            print(f"  !! hata {r.status_code} / PDF değil ({ct}): {url}")
            return False
        dest.write_bytes(r.content)
        print(f"  ✓ {dest.parent.name} ({len(r.content) / 1e6:.1f} MB)")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  !! {url}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {}

    items = [(k, v) for k, v in BOOKLETS.items()
             if args.year is None or k[0] == args.year]
    for (year, sess), url in sorted(items):
        dest = RAW / f"{year}_{sess}" / "kitapcik.pdf"
        if dest.exists() and dest.stat().st_size > 100_000:
            print(f"  - mevcut: {year}_{sess}")
            manifest[f"{year}_{sess}"] = url
            continue
        print(f"  -> {year}_{sess}: {url}")
        if not args.dry and download(url, dest):
            manifest[f"{year}_{sess}"] = url

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                             encoding="utf-8")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    sys.exit(main())
