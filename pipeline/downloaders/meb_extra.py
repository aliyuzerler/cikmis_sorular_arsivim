# -*- coding: utf-8 -*-
"""MEB/ÖDSGM ek sınav kitapçıkları: Açık Öğretim Kurumları dönem sınavları.

Not: Ehliyet (MTSK) sınavı e-sınava geçtiği için soru kitapçığı PDF
yayımlanmıyor; özel güvenlik görevlisi sınavı kitaplıkları EGM'de
(egm.gov.tr/ozelguvenlik) barındırılıyor, ÖDSGM açık erişimde değil.

Kullanım:  python -m pipeline.downloaders.meb_extra [--dry]
"""
import argparse
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "aol"
RAW_ADALET = ROOT / "data" / "raw" / "adalet"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
}

# (yıl, oturum) -> PDF (soru kitapçığı + cevap anahtarı aynı dosyada)
BOOKLETS = {
    (2024, "oturum_1"): "https://odsgm.meb.gov.tr/meb_iys_dosyalar/2024_12/25115028_1_oturum_21_aralik_2024t.pdf",
    (2024, "oturum_2"): "https://odsgm.meb.gov.tr/meb_iys_dosyalar/2024_12/25115028_2_oturum_21_aralik_2024t.pdf",
    (2024, "oturum_3"): "https://odsgm.meb.gov.tr/meb_iys_dosyalar/2024_12/25115028_3_oturum_22_aralik_2024t.pdf",
    (2025, "lise_oturum_1"): "https://cdn.eba.gov.tr/yardimcikaynaklar/2025/12/acikogretim/lise/1_OTURUM_20_ARALIK_2025.pdf",
    (2025, "lise_oturum_2"): "https://cdn.eba.gov.tr/yardimcikaynaklar/2025/12/acikogretim/lise/2_OTURUM_20_ARALIK_2025_T.pdf",
    (2025, "lise_oturum_3"): "https://cdn.eba.gov.tr/yardimcikaynaklar/2025/12/acikogretim/lise/3_OTURUM_21_ARALIK_2025.pdf",
    (2025, "ortaokul_oturum_1"): "https://cdn.eba.gov.tr/yardimcikaynaklar/2025/12/acikogretim/ortaokul/1_OTURUM_AOO_20_ARALIK_2025.pdf",
    (2025, "ortaokul_oturum_2"): "https://cdn.eba.gov.tr/yardimcikaynaklar/2025/12/acikogretim/ortaokul/2_OTURUM_AOO_20_ARALIK_2025.pdf",
}

# Adalet Bakanlığı Personeli Görevde Yükselme ve Unvan Değişikliği
# Yazılı Sınavı (30 Kasım 2025) — 10 kademe grubu × A/B kitapçık
ADALET = {
    (2025, f"gorev_{i:02d}_{kod}"): [
        f"https://cdn.eba.gov.tr/yardimcikaynaklar/2025/11/adalet/gorev/"
        f"{i}_GRUP_{kod}_A.pdf",
        f"https://cdn.eba.gov.tr/yardimcikaynaklar/2025/11/adalet/gorev/"
        f"{i}_GRUP_{kod}_B.pdf",
    ]
    for i, kod in [
        (1, "SUBE_MUDURU"), (2, "BILGI_ISLEM_MUDURU"),
        (3, "ADLI_DESTEKveMAGDUR_HIZMETLERI_MUDURU"), (4, "YAZI_ISLERI_MUDURU"),
        (5, "ADLI_DESTEKveMAGDUR_HIZMETLERI_MUDUR_YRD"), (6, "SEF"),
        (7, "KORUMAveGUVENLIK_SEFI"), (8, "ZABIT_KATIBI"), (9, "MUBASIR"),
        (10, "MEMUR"),
    ]
}


def download_set(items, base: Path, tag: str):
    manifest_path = base / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {}
    for (year, sess), urls in items:
        for k, url in enumerate(urls, 1):
            sess_i = sess if len(urls) == 1 else f"{sess}_{chr(64 + k)}"
            dest = base / f"{year}_{sess_i}" / "kitapcik.pdf"
            if dest.exists() and dest.stat().st_size > 100_000:
                print(f"  - mevcut: {year}_{sess_i}")
                manifest[f"{year}_{sess_i}"] = url
                continue
            print(f"  -> {year}_{sess_i}")
            if args.dry:
                continue
            try:
                r = requests.get(url, headers=HEADERS, timeout=120)
                if r.status_code != 200 or not r.content.startswith(b"%PDF"):
                    print(f"    !! hata {r.status_code} / PDF değil")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.content)
                print(f"    ✓ ({len(r.content) / 1e6:.1f} MB)")
                manifest[f"{year}_{sess_i}"] = url
            except Exception as e:  # noqa: BLE001
                print(f"    !! {e}")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                             encoding="utf-8")
    print(f"manifest: {manifest_path}")




# ---- AÖL sınav arşivi (aio.meb.gov.tr + aol.meb.gov.tr) ----
ARCHIVE_PAGES = [
    ("ortaokul", "https://aio.meb.gov.tr/www/acik-ogretim-ortaokulu-sinav-arsivi/icerik/20"),
    ("lise", "https://aol.meb.gov.tr/www/sinav-arsivi/icerik/15"),
]


def _archive_items():
    """Arşiv sayfalarındaki tüm sınav PDF'lerini (yıl, oturum, url) listeler."""
    import re as _re
    import requests as _rq
    out = []
    for okul, page in ARCHIVE_PAGES:
        try:
            html = _rq.get(page, headers=HEADERS, timeout=60).text
        except Exception as e:  # noqa: BLE001
            print(f"!! arşiv sayfası okunamadı ({okul}): {e}")
            continue
        paths = sorted(set(_re.findall(
            r"(?:https?://[a-z0-9.]+\.meb\.gov\.tr|https?://cdn\.eba\.gov\.tr)?"
            r"(/meb_iys_dosyalar/[^\"']+?\.pdf)",
            html)))
        for path in paths:
            if "kilavuz" in path.lower():
                continue
            from urllib.parse import unquote
            fname = unquote(path.rsplit("/", 1)[-1]).lower()
            fname = (fname.replace("ı", "i").replace("ö", "o")
                     .replace("ü", "u").replace("ç", "c").replace("ş", "s")
                     .replace("ğ", "g"))
            # yıl: dosya adındaki son yıl (ay adıyla birlikte en güvenilir)
            years = _re.findall(r"20\d\d", fname)
            ym = _re.search(r"_donem[ _]?(\d)", fname)
            ot = _re.search(r"(\d)_oturum", fname)
            if not (ym and ot):
                continue
            year = years[-1] if years else None
            if year is None:
                continue
            donem = ym.group(1)
            host = "https://aio.meb.gov.tr" if okul == "ortaokul" \
                else "https://aol.meb.gov.tr"
            out.append((int(year), f"{okul}_donem{donem}_oturum{ot.group(1)}",
                        host + path if path.startswith("/") else path))
    return out


def download_aol_archive(dry=False):
    items = _archive_items()
    seen = set()
    uniq = []
    for year, sess, url in items:
        if (year, sess) in seen:
            continue
        seen.add((year, sess))
        uniq.append((year, sess, url))
    print(f"AÖL arşiv: {len(uniq)} kitapçık bulundu")
    download_set((((y, s), [u]) for y, s, u in sorted(uniq)), RAW, "aol")


def main():
    global args
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    download_set(BOOKLETS.items(), RAW, "aol")
    download_set(ADALET.items(), RAW_ADALET, "adalet")
    download_aol_archive(args.dry)


if __name__ == "__main__":
    sys.exit(main())
