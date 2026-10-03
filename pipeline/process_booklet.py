# -*- coding: utf-8 -*-
"""Tek kitapçığı işleyen CLI.

Kullanım:
    python pipeline/process_booklet.py <pdf> <out_dir> --exam yks --year 2024 --session tyt
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from osym_parser import (BookletResult, parse_booklet, render_questions,
                         save_json)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out_dir")
    ap.add_argument("--exam", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--session", required=True, help="tyt / ayt / lys-mat ...")
    args = ap.parse_args()

    res = parse_booklet(args.pdf)
    render_questions(args.pdf, res, args.out_dir)
    save_json(res, args.out_dir, meta={
        "exam": args.exam, "year": args.year, "session": args.session,
        "source_pdf": str(args.pdf),
    })

    print(json.dumps(res.qa_report(), ensure_ascii=False, indent=2))
    if res.warnings:
        print("UYARILAR:")
        for w in res.warnings:
            print(" -", w)


if __name__ == "__main__":
    main()
