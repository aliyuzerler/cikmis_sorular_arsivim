# -*- coding: utf-8 -*-
"""LGS cevap anahtarlarını bölüm boylarına göre parçalayıp fixes/ yamaları
üretir.

LGS bölüm soru sayıları sabittir: sözel = Türkçe 20, İnkılap 10, Din 10,
Yabancı Dil 10 (2018 dahil); sayısal = Matematik 20, Fen 20. Anahtar
sayfasındaki tüm 'N. X' girişleri okuma sırasına göre bu boyutlarda
parçalanır ve pipeline/fixes/meb_<yil>_<oturum>.json olarak yazılır.

Kullanım:  python -m pipeline.fix_lgs
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from osym_parser import page_words, _key_segments, ANSWER_LINE, ANSWER_IPTAL

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "lgs"
FIXES = ROOT / "pipeline" / "fixes"

SOZEL_ORDER = [("turkce", 20), ("inkilap", 10), ("din", 10), ("yabanci_dil", 10)]
SAYISAL_ORDER = [("matematik", 20), ("fen", 20)]


def key_entries(pdf: Path) -> list[tuple[int, int, str]]:
    """Anahtar sayfasındaki (no, sıra_index, harf) girişlerini sayfa sırasıyla
    döner. Kolonlu düzenlerde (y, x) okuma sırası: x-bandı, sonra y."""
    doc = pymupdf.open(str(pdf))
    for pi in range(len(doc) - 1, -1, -1):
        words = page_words(doc[pi], y_top=15)
        segs = _key_segments(words)
        entries = []
        for s in segs:
            t = s["text"].strip()
            am = ANSWER_LINE.match(t)
            if am:
                entries.append((int(am.group(1)), am.group(2),
                                s["y0"], s["x0"]))
                continue
            im = ANSWER_IPTAL.match(t)
            if im:
                entries.append((int(im.group(1)), "", s["y0"], s["x0"]))
        if len(entries) >= 30:
            # kolon sayısını tahmin et: x küme sayısı
            xs = sorted({round(x // 40) for _, _, _, x in entries})
            if len(xs) >= 4:  # yatay düzen: kolonlar yan yana
                entries.sort(key=lambda e: (e[3], e[2]))
            else:  # dikey düzen: üstten alta
                entries.sort(key=lambda e: (e[2], e[3]))
            return [(no, letter, i) for i, (no, letter, _, _)
                    in enumerate(entries)]
    return []


def main():
    FIXES.mkdir(exist_ok=True)
    made = 0
    for sub in sorted(RAW.iterdir()):
        m = re.match(r"^(\d{4})_(sozel|sayisal)$", sub.name)
        pdf = sub / "kitapcik.pdf"
        if not m or not pdf.exists():
            continue
        year, kind = int(m.group(1)), m.group(2)
        order = SOZEL_ORDER if kind == "sozel" else SAYISAL_ORDER
        entries = key_entries(pdf)
        total = sum(n for _, n in order)
        if len(entries) < total:
            print(f"!! {sub.name}: anahtar girişi yetersiz "
                  f"({len(entries)}/{total})")
            continue
        overrides, idx = {}, 0
        for sid, cnt in order:
            tgt = overrides.setdefault(sid, {})
            for no in range(1, cnt + 1):
                if idx < len(entries):
                    tgt[str(no)] = entries[idx][1]
                    idx += 1
        fixes = {
            "expected_counts": {sid: cnt for sid, cnt in order},
            "key_overrides": overrides,
        }
        out = FIXES / f"lgs_{year}_{kind}.json"
        out.write_text(json.dumps(fixes, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        made += 1
        print(f"✓ {out.name} ({len(entries)} giriş)")
    print(f"{made} yama üretildi")


if __name__ == "__main__":
    main()
