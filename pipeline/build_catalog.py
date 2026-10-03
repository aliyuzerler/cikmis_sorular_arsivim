# -*- coding: utf-8 -*-
"""data/processed altındaki tüm işlenmiş kitapçıklardan uygulama kataloğu
(data/index.json) üretir.

Kullanım:  python pipeline/build_catalog.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

EXAM_NAMES = {
    "yks": "YKS (TYT / AYT / YDT)",
    "ygs_lys": "YGS / LYS",
    "ales": "ALES",
    "kpss": "KPSS",
    "dgs": "DGS",
    "msu": "MSÜ",
    "yds": "YDS / YÖKDİL",
    "lgs": "LGS",
    "aol": "Açık Öğretim Lisesi",
    "guvenlik": "Güvenlik Görevlisi",
    "adalet": "Adalet Bakanlığı Görevde Yükselme",
}

# sınav -> (kaynak, kategori çipi sırası)
EXAM_SOURCE = {
    "yks": "osym",
    "ygs_lys": "osym",
    "ales": "osym",
    "kpss": "osym",
    "dgs": "osym",
    "msu": "osym",
    "yds": "osym",
    "lgs": "meb",
    "aol": "meb",
    "guvenlik": "meb",
    "adalet": "meb",
}

# %10 örnek kitapçık yayımlanan ÖSYM sınavları
SAMPLE_EXAMS = {"kpss", "ales", "dgs", "msu", "yds"}

SOURCE_NAMES = {"osym": "ÖSYM", "meb": "MEB"}

SESSION_NAMES = {
    "tyt": "TYT - Temel Yeterlilik Testi",
    "ayt": "AYT - Alan Yeterlilik Testleri",
    "ydt": "YDT - Yabancı Dil Testi",
    "mat": "Matematik",
    "fen": "Fen Bilimleri",
    "turkce": "Türkçe",
    "sosyal": "Sosyal Bilimler",
    "gygk": "Genel Yetenek - Genel Kültür",
    "gkgy": "Genel Kültür - Genel Yetenek",
    "egitim": "Eğitim Bilimleri",
    "oabt": "ÖABT",
    "yds": "YDS",
    "yokdil": "YÖKDİL",
    "sayisal": "Sayısal",
    "sozel": "Sözel",
    "esit_agirlik": "Eşit Ağırlık",
    "dil": "Dil",
    # KPSS %10 oturumları
    "lisans": "Lisans - GY-GK ve Eğitim Bilimleri",
    "a_alan": "A Grubu - Alan Bilgisi",
    "ortaogretim": "Ortaöğretim",
    "onlisans": "Ön Lisans",
    "dhbt": "DHBT - Din Hizmetleri Alan Bilgisi",
    # ALES dönemleri
    "ales_1": "ALES /1",
    "ales_2": "ALES /2",
    "ales_3": "ALES /3",
    # YDS oturumları
    "yds_1": "YDS /1",
    "yds_2": "YDS /2",
    "eyds": "e-YDS",
    # diğerleri
    "msu": "MSÜ",
    "dgs": "DGS",
}


def main():
    catalog = []
    for qfile in sorted(PROCESSED.glob("*/*/*/questions.json")):
        parts = qfile.relative_to(PROCESSED).parts  # exam/year/session
        exam, year, session = parts[0], int(parts[1]), parts[2]
        data = json.loads(qfile.read_text(encoding="utf-8"))
        qs = data.get("questions", [])
        if not qs:
            continue
        sec_counts = {}
        for q in qs:
            sc = sec_counts.setdefault(q["section"], {
                "id": q["section"], "name": q.get("section_name", q["section"]),
                "count": 0})
            sc["count"] += 1
        qa_ok = all(v.get("ok") for v in data.get("qa", {}).values()) if data.get("qa") else False
        with_answers = sum(1 for q in qs if q.get("answer"))
        catalog.append({
            "id": f"{exam}_{year}_{session}",
            "exam": exam,
            "examName": EXAM_NAMES.get(exam, exam.upper()),
            "source": EXAM_SOURCE.get(exam, "osym"),
            "sourceName": SOURCE_NAMES.get(EXAM_SOURCE.get(exam, "osym"), "ÖSYM"),
            "year": year,
            "session": session,
            "sessionName": SESSION_NAMES.get(session, session)
                           + (" (%10 örnek)" if exam in SAMPLE_EXAMS else ""),
            "path": f"/data/processed/{exam}/{year}/{session}",
            "total": len(qs),
            "withAnswers": with_answers,
            "sections": sorted(sec_counts.values(), key=lambda s: qs.index(
                next(q for q in qs if q["section"] == s["id"]))),
            "qaOk": qa_ok,
        })

    out = ROOT / "data" / "index.json"
    out.write_text(json.dumps(catalog, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"{len(catalog)} test kataloğa eklendi -> {out}")


if __name__ == "__main__":
    main()
