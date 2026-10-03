# -*- coding: utf-8 -*-
"""data/raw altındaki tüm kitapçıkları toplu işler ve QA özeti üretir.

pipeline/fixes/<exam>_<yil>_<oturum>.json yamaları parse sonrası uygulanır:
    {
      "expected_counts": {"fen": 20},          # beklenen soru sayısı düzeltme
      "key_overrides": {"fen": {"7": "C"}},    # elle girilen cevaplar
      "drop_questions": [["fen", 7]],          # çıkarılacak hatalı kırpımlar
      "section_map": {"belirsiz": "fizik"}     # bölüm adı düzeltmeleri
    }

Kullanım:
    python -m pipeline.process_all [exam]   # ör: yks, meb, boşsa hepsi
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from osym_parser import parse_booklet, render_questions, save_json

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
FIXES = ROOT / "pipeline" / "fixes"

# %10 örnek kitapçık yayımlanan ÖSYM sınavları
SAMPLE_EXAMS = {"kpss", "ales", "dgs", "msu", "yds"}

DIR_RE = re.compile(r"^(\d{4})_([A-Za-z0-9_]+)$")


def load_fixes(exam: str, year: int, session: str) -> dict:
    f = FIXES / f"{exam}_{year}_{session}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}


def apply_fixes(res, fixes: dict):
    """Parse sonucuna manuel yamaları uygular."""
    if not fixes:
        return
    for sid, cnt in fixes.get("expected_counts", {}).items():
        res.expected_counts[sid] = cnt
        # taşan çapaları kırp (sonraki bölümün sızmış soruları vb.)
        res.questions = [q for q in res.questions
                         if not (q.section == sid and q.no > cnt)]
    for sid, entries in fixes.get("key_overrides", {}).items():
        tgt = res.answer_key.setdefault(sid, {})
        for no, letter in entries.items():
            tgt[int(no)] = letter
    smap = fixes.get("section_map", {})
    if smap:
        for q in res.questions:
            if q.section in smap:
                q.section = smap[q.section]
        res.sections = sorted({(q.section, q.section_name)
                               for q in res.questions}, key=lambda x: 0)
    for sid, no in fixes.get("drop_questions", []):
        res.questions = [q for q in res.questions
                         if not (q.section == sid and q.no == no)]
    res.warnings.append(f"yama uygulandı: {len(fixes)} anahtar")


def process_one(pdf: Path, exam: str, year: int, session: str, force=False):
    out = PROC / exam / str(year) / session
    if out.joinpath("questions.json").exists() and not force \
            and not (FIXES / f"{exam}_{year}_{session}.json").exists():
        return "skip", json.loads(out.joinpath("questions.json").read_text(encoding="utf-8"))["qa"]
    key_pdf = pdf.parent / "cevap_anahtari.pdf"
    try:
        res = parse_booklet(pdf, key_pdf=key_pdf)
        apply_fixes(res, load_fixes(exam, year, session))
        _attach(res)
        # boş kırpımlar soru listesinden düşülür; QA bunun üzerinden hesaplanır
        render_questions(pdf, res, out)
        if exam in SAMPLE_EXAMS:
            # %10 örneklerde talimattaki 'Bu testte N soru vardır' tam kitapçığa
            # aittir; fiili içerik hedeftir
            for sid in list(res.expected_counts):
                res.expected_counts[sid] = None
        save_json(res, out, meta={
            "exam": exam, "year": year, "session": session, "source_pdf": str(pdf)})
        return "ok", res.qa_report()
    except Exception as e:  # noqa: BLE001
        return "error", {"error": str(e)}


def _attach(res):
    from osym_parser import _attach_answers
    _attach_answers(res)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    exam_filter = args[0] if args else None
    force = "--force" in sys.argv
    report = {}
    for exam_dir in sorted(RAW.iterdir()):
        if not exam_dir.is_dir():
            continue
        if exam_filter and exam_dir.name != exam_filter:
            continue
        for sub in sorted(exam_dir.iterdir()):
            m = DIR_RE.match(sub.name)
            pdf = sub / "kitapcik.pdf"
            if not m or not pdf.exists():
                continue
            year, session = int(m.group(1)), m.group(2)
            status, qa = process_one(pdf, exam_dir.name, year, session, force)
            ok_count = sum(1 for v in qa.values() if isinstance(v, dict) and v.get("ok"))
            total_secs = len([v for v in qa.values() if isinstance(v, dict)])
            print(f"{exam_dir.name}/{sub.name}: {status} "
                  f"({ok_count}/{total_secs} bölüm tamam)"
                  + ("" if status != "error" else f" -> {qa.get('error')}"))
            report[f"{exam_dir.name}/{sub.name}"] = {"status": status, "qa": qa}

    out = ROOT / "data" / "qa" / "report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    # özet
    errs = [k for k, v in report.items() if v["status"] == "error"]
    partial = [k for k, v in report.items()
               if v["status"] == "ok" and isinstance(v["qa"], dict)
               and not all(x.get("ok") for x in v["qa"].values() if isinstance(x, dict))]
    print(f"\n=== ÖZET: {len(report)} kitapçık, {len(errs)} hata, "
          f"{len(partial)} kısmi ===")
    if errs:
        print("HATALAR:", *errs, sep="\n  ")
    if partial:
        print("KISMI:", *partial, sep="\n  ")


if __name__ == "__main__":
    main()
