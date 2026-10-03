# -*- coding: utf-8 -*-
"""ygs_lys kitapçıklarında klasör adı ↔ içerik uyuşmasını doğrular.

ÖSYM'nin 2013 sayfasında bağlantı metinleri ile PDF içerikleri kaymıştır
('Fizik Testi' PDF'i aslında Geometri içerebilir). Bu script her tek-testlik
kitapçığın baskın bölümüne bakar; uyuşmazlıkta raw klasörünü yeniden
adlandırır ve bayat işlem çıktısını siler.

Kullanım:  python -m pipeline.verify_sessions [--dry]
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from osym_parser import parse_booklet

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ygs_lys"
PROC = ROOT / "data" / "processed" / "ygs_lys"

# bölüm kimliği -> klasör oturum adı
SECTION_TO_SESSION = {
    "geometri": "lys1_geometri",
    "matematik": "lys1_matematik",
    "fizik": "lys2_fizik",
    "kimya": "lys2_kimya",
    "biyoloji": "lys2_biyoloji",
    "edebiyat": "lys3_edebiyat",
    "cografya1": "lys3_cografya1",
    "tarih": "lys4_tarih",
    "cografya2": "lys4_cografya2",
    "felsefe": "lys4_felsefe",
    "almanca": "lys5_alm",
    "fransizca": "lys5_fra",
    "ingilizce": "lys5_ing",
}


def dominant_section(res) -> tuple | None:
    """En çok soruya sahip bölüm (tek-test kitaplıkları için güvenilir)."""
    counts = {}
    for q in res.questions:
        counts[q.section] = counts.get(q.section, 0) + 1
    if not counts:
        return None
    sid = max(counts, key=counts.get)
    return sid, counts[sid]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    renames = []
    for sub in sorted(RAW.iterdir()):
        pdf = sub / "kitapcik.pdf"
        if not sub.name[:4].isdigit() or not pdf.exists():
            continue
        year = sub.name[:4]
        cur_session = sub.name[5:]
        # QA'sı zaten tam olan kitapçıkları koru
        done = PROC / year / cur_session / "questions.json"
        if done.exists():
            try:
                qa = json.loads(done.read_text(encoding="utf-8")).get("qa", {})
                if qa and all(v.get("ok") for v in qa.values() if isinstance(v, dict)):
                    continue
            except Exception:  # noqa: BLE001
                pass
        try:
            res = parse_booklet(pdf)
        except Exception as e:  # noqa: BLE001
            print(f"!! {sub.name}: {e}")
            continue
        dom = dominant_section(res)
        if not dom or dom[1] < 10:
            continue
        sid, cnt = dom
        want = SECTION_TO_SESSION.get(sid)
        if want and want != cur_session:
            renames.append((sub.name, f"{year}_{want}", cnt))

    if not renames:
        print("uyuşmazlık yok")
        return

    # döngüsel zincirler (A->B, B->A) için iki fazlı taşıma. Gerçek çatışma
    # yalnızca hedef, taşınmayan bir klasörse (zincir dışıysa) vardır.
    move_set = {old for old, _, _ in renames}
    moves = [(RAW / old, RAW / new, cnt) for old, new, cnt in renames]
    skipped = []
    for src, dst, _ in moves:
        if dst.exists() and dst.name not in move_set:
            skipped.append(src.name)

    tmp_moved = []
    for src, dst, cnt in moves:
        if src.name in skipped:
            print(f"!! hedef taşınmıyor, atlandı: {dst.name}")
            continue
        tmp = src.with_name(src.name + ".__tmp__")
        if not args.dry:
            src.rename(tmp)
        tmp_moved.append((tmp, dst, cnt))
    if not args.dry:
        for tmp, dst, cnt in tmp_moved:
            tmp.rename(dst)
            stale = PROC / dst.name[:4] / dst.name[5:]
            if stale.exists():
                shutil.rmtree(stale)
    for _, dst, cnt in tmp_moved:
        print(f"✓ {dst.name} (baskın bölüm {cnt} soru)")
    if args.dry:
        print(f"\n{len(tmp_moved)} klasör yeniden adlandırılacak (--dry)")


if __name__ == "__main__":
    main()
