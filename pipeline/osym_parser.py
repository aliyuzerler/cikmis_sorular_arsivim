# -*- coding: utf-8 -*-
"""
ÖSYM soru kitapçığı ayrıştırıcı.

Kitapçık PDF'ini:
  1) sütun yapısı tespiti (sayfa bazlı + belge geneli gutter fallback),
  2) soru numarası çapaları ile soru blokları,
  3) test (bölüm) başlıkları takibi,
  4) son sayfadaki cevap anahtarı ayrıştırma (kolon bazlı),
  5) her soru için yüksek DPI görsel kırpma
adımlarından geçirir.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import pymupdf
from PIL import Image

# ---------------------------------------------------------------- regexler

QNUM = re.compile(r"^(\d{1,3})\.$")
# "1. Bu testte 40 soru vardır." / "2. Cevaplarınızı ..." talimat satırları
BOILERPLATE = re.compile(
    r"^(bu\s+testte|cevaplar|bu\s+kitapç|bu\s+testler|adaylar|soru\s+kitapç)", re.I
)
# Test başlığı: "TÜRKÇE TESTİ", "TÜRK DİLİ ve EDEBİYATI-SOSYAL BİLİMLER-1 TESTİ"...
SECTION_HEADER = re.compile(r"^(.+?)\s*TEST[İI]$")
# Satır sonunda başlık: "2024-TYT/TÜR TÜRKÇE TESTİ" gibi ön ekli durumlarda
SECTION_HEADER_SUFFIX = re.compile(r"([A-ZÇĞİÖŞÜ0-9\s]{2,40}TEST[İI])\s*$")
# Bölüm bitiş/yönlendirme satırları — TAM SATIR eşleşmesi ister; soru metni
# içindeki "bitti", "geçiniz" kelimelerine takılmamak için.
END_MARKER = re.compile(
    r"(?:[A-ZÇĞİÖŞÜ0-9\s]*TEST[İI]?\s*B[İI]TT[İI]"
    r"|B[İI]TT[İI]"
    r"|D[İI]ĞER\s+SAYFAYA\s+GEÇ[İI]N[İI]Z"
    r"|[A-ZÇĞİÖŞÜ0-9\s]+TEST[İI]NE\s+GEÇ[İI]N[İI]Z)\.?", re.I)


def _is_end_line(text: str) -> bool:
    t = text.strip()
    return len(t) <= 40 and END_MARKER.fullmatch(t) is not None
# Cevap anahtarı satırı: "12.   C"
ANSWER_LINE = re.compile(r"^(\d{1,3})\.\s*([A-E])$")
# "Bu testte 40 soru vardır" / "... toplam 25 soru vardır" -> beklenen soru
# sayısı. 'vardır' şartı soru metinlerindeki 'toplam 8 sorudan...' gibi
# ifadelere takılmayı önler.
EXPECTED_COUNT = re.compile(
    r"(?:bu\s+testte\s+|\btoplams*\s+)(\d{1,3})\s+soru(?:su)?\s+vardır", re.I)
# İptal edilmiş soru: "7.   İPTAL"
ANSWER_IPTAL = re.compile(r"^(\d{1,3})\.\s*(?:İPTAL|IPTAL)\.?$", re.I)
# Soru metni içindeki numaralı satır/sütun referansları ("2. satırında ...")
FALSE_ANCHOR = re.compile(
    r"^(satır|sütun|sıra|adım|aşama|basamak|kademe|bölüm|durum|seçenek|aralık)\b", re.I)

ZOOM = 2.8  # ~200 DPI


# ---------------------------------------------------------------- veri modeli

@dataclass
class Question:
    section: str          # bölüm kimliği ("turkce", "sosyal", ...)
    section_name: str     # "TÜRKÇE TESTİ"
    no: int               # bölüm içi soru numarası
    page: int             # 0-tabanlı sayfa indeksi
    bbox: tuple           # PDF koordinatlarında (x0, y0, x1, y1)
    img: str = ""         # çıktı dosya adı
    answer: str = ""      # A-E


@dataclass
class BookletResult:
    questions: list = field(default_factory=list)
    answer_key: dict = field(default_factory=dict)     # {section: {no: 'A'}}
    expected_counts: dict = field(default_factory=dict)  # {section_id: N}
    sections: list = field(default_factory=list)        # [(id, name)]
    warnings: list = field(default_factory=list)

    def qa_report(self) -> dict:
        rep = {}
        for sid, name in self.sections:
            got = sum(1 for q in self.questions if q.section == sid)
            exp = self.expected_counts.get(sid)
            key = len(self.answer_key.get(sid, {}))
            rep[sid] = {"name": name, "questions_found": got,
                        "expected": exp, "answer_key_entries": key,
                        "ok": (exp is None or got == exp) and (key == 0 or got == key)}
        return rep


SECTION_ID_MAP = {
    "TÜRKÇE": "turkce",
    "SOSYAL BİLİMLER": "sosyal",
    "TEMEL MATEMATİK": "matematik",
    "MATEMATİK": "matematik",
    "FEN BİLİMLERİ": "fen",
    "GEOMETRİ": "geometri",
    "FİZİK": "fizik",
    "KİMYA": "kimya",
    "BİYOLOJİ": "biyoloji",
    "TARİH": "tarih",
    "COĞRAFYA": "cografya",
    "FELSEFE": "felsefe",
    "DİN KÜLTÜRÜ": "din",
    "İNGİLİZCE": "ingilizce",
    "EDEBİYAT": "edebiyat",
    "GENEL YETENEK": "genel_yetenek",
    "GENEL KÜLTÜR": "genel_kultur",
    "EĞİTİM BİLİMLERİ": "egitim",
    "SAYISAL": "sayisal",
    "SÖZEL": "sozel",
    "EŞİT AĞIRLIK": "esit_agirlik",
    "YABANCI DİL": "yabanci_dil",
    # KPSS DHBT
    "DİN HİZMETLERİ ALAN BİLGİSİ": "din_hizmetleri",
    # AYT birleşik testleri
    "TÜRK DİLİ VE EDEBİYATI-SOSYAL BİLİMLER-1": "edebiyat_sosyal_1",
    "TÜRK DİLİ VE EDEBİYATI - SOSYAL BİLİMLER - 1": "edebiyat_sosyal_1",
    "SOSYAL BİLİMLER-2": "sosyal_2",
    "SOSYAL BİLİMLER - 2": "sosyal_2",
    # LYS testleri
    "TÜRK DİLİ VE EDEBİYATI": "edebiyat",
    "COĞRAFYA-1": "cografya1",
    "COĞRAFYA-2": "cografya2",
    "FELSEFE GRUBU": "felsefe",
    # LGS (MEB) dersleri
    "T.C. İNKILAP TARİHİ VE ATATÜRKÇÜLÜK": "inkilap",
    "İNKILAP TARİHİ VE ATATÜRKÇÜLÜK": "inkilap",
    "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": "din",
    "MATEMATİK": "matematik",
    # LYS5 dil testleri (2013 gibi eski kitapçıklarda tek ad)
    "ALMANCA": "almanca",
    "FRANSIZCA": "fransizca",
    # LYS4 birleşik ad (2013: 'Felsefe Grubu ile Din Kültürü ve Ahlak Bilgisi')
    "FELSEFE GRUBU İLE DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": "felsefe",
}


def _norm_upper(s: str) -> str:
    """Büyük harfe çevirip Türkçe karakterleri ASCII'ye katlar (İ→I, Ş→S...)."""
    return (s.upper()
            .replace("İ", "I").replace("Ş", "S").replace("Ğ", "G")
            .replace("Ü", "U").replace("Ö", "O").replace("Ç", "C"))


def _canon(s: str) -> str:
    """Ad karşılaştırması için kurallı biçim: ASCII-fold + tire/boşluk
    sadeleşme + yan yana tekrar eden kelimelerin silinmesi (satır birle-
    şimlerinden kaynaklanan 'VE VE' gibi çiftler)."""
    out = re.sub(r"[\s\-]+", " ", _norm_upper(s)).strip()
    words = out.split()
    dedup = [w for i, w in enumerate(words) if i == 0 or w != words[i - 1]]
    return " ".join(dedup)


def section_id_from_name(name: str) -> str:
    """'TÜRKÇE TESTİ' -> 'turkce'; bilinmeyense slug'lanır."""
    m = SECTION_HEADER.match(name.strip())
    core = m.group(1).strip() if m else name.strip()
    core_n = _canon(core)
    for k, v in SECTION_ID_MAP.items():
        if _canon(k) == core_n:
            return v
    # "-1" / "-2" son ekleri (AYT TARİH-1 gibi) kimliğe eklenir
    base = re.sub(r"\s*-\s*\d+$", "", core_n)
    for k, v in SECTION_ID_MAP.items():
        if _canon(k) == base:
            suffix = re.search(r"-(\d+)$", core_n.replace(" ", ""))
            return v + (suffix.group(1) if suffix else "")
    slug = re.sub(r"[^a-z0-9]+", "_",
                  core_n.lower().replace("ı", "i").replace("ş", "s")).strip("_")
    return slug or "test"


# "2. Cevaplarınızı, cevap kâğıdının X Testi için ayrılan kısmına
# işaretleyiniz." -> bölüm adı X (bölüm başlangıcının en güvenilir işareti)
CEVAP_KAGIDI_NAME = re.compile(
    r"cevap\s*kâğıdının\s+(.+?)\s+test[İi]\s+için", re.I)


def extract_section_name(text: str) -> str | None:
    """Satırdan test adını çıkarır.

    '2024-TYTY/TÜR TÜRKÇE TESTİ' -> 'TÜRKÇE TESTİ' (bilinen adlar öncelikli).
    MEB/LGS'de başlıklar TESTİ'sizdir ve kitapçık tipi harfli olabilir
    ('MATEMATİK A', 'FEN BİLİMLERİ B'): bilinen ders adı + opsiyonel tek
    harf biçimi de tanınır.
    """
    t = " ".join(text.split())
    tn = _canon(t)
    for known in sorted(SECTION_ID_MAP, key=len, reverse=True):
        if tn.endswith(_canon(known + " TESTİ")):
            return known + " TESTİ"
    # '... FİZİK TESTİ CEVAP ANAHTARI' biçimi: sondan ayıkla, yeniden dene
    stripped = re.sub(r"\s*CEVAP\s*ANAHTARI\s*$", "", t, flags=re.I)
    if stripped != t:
        for known in sorted(SECTION_ID_MAP, key=len, reverse=True):
            if _canon(stripped).endswith(_canon(known + " TESTİ")):
                return known + " TESTİ"
        t = stripped
        tn = _canon(t)
    if (t.endswith("TESTİ") or t.endswith("TESTI")) and len(t) >= 10:
        if sum(1 for c in t if c.isupper()) >= 4 and len(t) <= 60:
            return t
    # bilinen ders adı + opsiyonel kitapçık tipi harfi ('MATEMATİK A')
    core = re.sub(r"\s+[ABCE]$", "", tn)
    for known in sorted(SECTION_ID_MAP, key=len, reverse=True):
        kn = _canon(known)
        if core == kn and len(core) >= 6:
            return known + " TESTİ"
    return None


def _match_section_contains(text: str) -> str | None:
    """Satır İÇİNDE bilinen bir test adı geçiyorsa kurallı adını döner.

    Tam genişlik başlık satırları koşu başlığını ('2019-TYT/FEN') da
    içerdiğinden endswith yerine contains kullanılır.
    """
    tn = _canon(text)
    for known in sorted(SECTION_ID_MAP, key=len, reverse=True):
        if len(known) < 6:
            continue
        if _canon(known + " TESTİ") in tn or _canon(known) == tn:
            return known + " TESTİ"
    # '2024-DHBT-1 Din Hizmetleri Alan Bilgisi Testi' gibi önekli adlar
    for known in sorted(SECTION_ID_MAP, key=len, reverse=True):
        if len(known) < 6:
            continue
        if _canon(known) + " testi" in tn:
            return known + " TESTİ"
    return None


# ---------------------------------------------------------------- kelime çıkar

def page_words(page, y_top=40.0, y_bottom_margin=30.0):
    """Filigran/diyagonal telif yazısı ayıklanmış kelimeler.

    rawdict üzerinden, satırın font büyüklüğü ve yazma yönü ile kurulur;
    büyük (size>12) veya döndürülmüş (dir!=(1,0)) parçalar atılır.
    Dönen değer pymupdf 'words' düzeni: (x0, y0, x1, y1, word, bno, lno, wno)
    """
    out = []
    for bno, b in enumerate(page.get_text("rawdict")["blocks"]):
        if b.get("type", 0) != 0:
            continue
        for lno, line in enumerate(b.get("lines", [])):
            spans = line.get("spans", [])
            if not spans:
                continue
            if any(s.get("size", 9) > 15.5 or tuple(s.get("dir", (1, 0))) != (1, 0)
                   for s in spans):
                continue
            wno = 0
            cur_chars, cur_bbox = [], None
            for sp in spans:
                for ch in sp.get("chars", []):
                    cbox = ch["bbox"]
                    if ch["c"].isspace():
                        if cur_chars:
                            out.append((cur_bbox[0], cur_bbox[1], cur_bbox[2],
                                        cur_bbox[3], "".join(cur_chars),
                                        bno, lno, wno))
                            wno += 1
                            cur_chars, cur_bbox = [], None
                        continue
                    if cur_bbox is None:
                        cur_bbox = list(cbox)
                    else:
                        cur_bbox[0] = min(cur_bbox[0], cbox[0])
                        cur_bbox[1] = min(cur_bbox[1], cbox[1])
                        cur_bbox[2] = max(cur_bbox[2], cbox[2])
                        cur_bbox[3] = max(cur_bbox[3], cbox[3])
                    cur_chars.append(ch["c"])
            if cur_chars:
                out.append((cur_bbox[0], cur_bbox[1], cur_bbox[2], cur_bbox[3],
                            "".join(cur_chars), bno, lno, wno))
    return [w for w in out
            if y_top < w[1] and w[3] < page.rect.y1 - y_bottom_margin
            and (w[2] - w[0]) < 90]


def _lines_from_words(words):
    """Kelimeleri (block,line) grubuna göre satırlara toplar (anahtar
    sayfalarının tablo düzeni için doğru yöntem)."""
    lines = {}
    for w in words:
        key = (w[5], w[6])  # block_no, line_no
        lines.setdefault(key, []).append(w)
    out = []
    for key, ws in lines.items():
        ws.sort(key=lambda w: w[0])
        out.append({"text": " ".join(w[4] for w in ws),
                    "x0": min(w[0] for w in ws), "y0": min(w[1] for w in ws),
                    "x1": max(w[2] for w in ws), "y1": max(w[3] for w in ws),
                    "block": key[0], "line": key[1], "words": ws})
    out.sort(key=lambda l: (l["y0"], l["x0"]))
    return out


def _join_wrapped_headers(lines):
    """Alt alta bölünmüş başlık satırlarını birleştirir.

    'T.C. İNKILAP TARİHİ VE' + 'ATATÜRKÇÜLÜK A' gibi; üç satıra bölünme
    ('...Edebiyatı-Sosyal Bilimler-1' + 'TESTİ') de desteklenir. Yalnız
    birleşimi bir bilinen test adına tam oturan, kendisi başlık olmayan
    kısa satırlar birleştirilir (soru metinleri etkilenmez).
    """
    if len(lines) < 2:
        return lines
    out = []
    i = 0
    while i < len(lines):
        a = lines[i]
        ta = a["text"].strip()
        merged_any = False
        # aynı başlık 2-3 satıra bölünmüş olabilir: art arda birleştir
        while (i + 1 < len(lines) and len(ta) < 35
               and not ta.endswith(("TESTİ", "TESTI"))
               and extract_section_name(ta) is None):
            b = lines[i + 1]
            merged = extract_section_name(ta + " " + b["text"].strip())
            if not merged:
                break
            nl = dict(a)
            nl["text"] = ta + " " + b["text"].strip()
            nl["y1"] = max(a["y1"], b["y1"])
            nl["words"] = a["words"] + b["words"]
            a = nl
            ta = nl["text"]
            i += 1
            merged_any = True
        out.append(a)
        i += 1 if not merged_any else 0
    return out


def _is_page_number(line) -> bool:
    """Alt kenardaki yalnız-sayı (sayfa numarası) satırı mı?"""
    t = line["text"].strip()
    return line["y0"] > 700 and re.fullmatch(r"\d{1,3}", t) is not None


def _visual_lines(words):
    """Kolon içi kelimeleri görsel satırlara toplar (y-bant, ~4pt).

    Eski ÖSYM PDF'lerinde aynı görsel satır farklı metin bloklarına
    dağılmış olabildiğinden blok bilgisine güvenilmez. Yalnız tek kolonun
    kelimelerine uygulanmalıdır.
    """
    out = []
    for row_words in _visual_rows(words):
        ws = sorted(row_words, key=lambda w: w[0])
        out.append({"text": " ".join(w[4] for w in ws),
                    "x0": ws[0][0], "y0": min(w[1] for w in ws),
                    "x1": ws[-1][2], "y1": max(w[3] for w in ws),
                    "block": -1, "line": -1, "words": ws})
    out.sort(key=lambda l: (l["y0"], l["x0"]))
    return out


def _is_answer_key_page(page) -> bool:
    words = page_words(page, y_top=15)
    segs = _key_segments(words)
    hits = sum(1 for s in segs if ANSWER_LINE.match(s["text"].strip()))
    return hits >= 10


# ---------------------------------------------------------------- sütunlar

def find_gutter(words, page_rect):
    """Orta bantta kelime geçişini minimize eden x; yeterince temizse döner."""
    if not words:
        return None
    W = page_rect.x1
    best_x, best_cross = None, None
    for x in range(int(0.30 * W), int(0.70 * W), 3):
        cross = sum(1 for w in words if w[0] < x < w[2])
        if best_cross is None or cross < best_cross:
            best_x, best_cross = x, cross
    if best_cross is not None and best_cross <= max(3, 0.02 * len(words)):
        return float(best_x)
    return None


def columns_for(gutter, words, page_rect):
    if gutter is None:
        return [(page_rect.x0, page_rect.x1)]
    lo = min(w[0] for w in words) if words else page_rect.x0
    hi = max(w[2] for w in words) if words else page_rect.x1
    return [(lo, gutter), (gutter, hi)]


# ---------------------------------------------------------------- ana parse

def parse_booklet(pdf_path, key_pdf=None) -> BookletResult:
    doc = pymupdf.open(str(pdf_path))
    res = BookletResult()

    answer_pages = {i for i in range(len(doc)) if _is_answer_key_page(doc[i])}

    # 1. geçiş: sayfa kelimeleri + sayfa bazlı gutter; belge geneli medyan
    page_data = {}
    gutters = []
    for pi in range(len(doc)):
        if pi == 0 or pi in answer_pages:
            continue
        page = doc[pi]
        words = page_words(page)
        page_data[pi] = (page, words)
        g = find_gutter(words, page.rect)
        if g is not None:
            gutters.append(g)
    gutters.sort()
    doc_gutter = gutters[len(gutters) // 2] if gutters else None

    cur_sid, cur_name = None, None
    expected_next = {}  # bölüm -> sıradaki beklenen soru no

    for pi in sorted(page_data):
        page, words = page_data[pi]
        # ÖSYM kitapçıklarında kolon geometrisi tutarlıdır: belge geneli
        # medyan gutter güvenilirdir; saparak yanlış ölçen sayfalar ona
        # göre düzeltilir.
        if doc_gutter is not None:
            g = find_gutter(words, page.rect)
            gutter = g if g is not None and abs(g - doc_gutter) <= 20 else doc_gutter
        else:
            gutter = find_gutter(words, page.rect)
        columns = columns_for(gutter, words, page.rect)

        # kolon bazlı görsel satırlar (eski PDF'lerde satırlar bloklara
        # dağılmış olabilir; kolon içinde y-bant ile birleştirilir).
        # Hibrit: blok yapısı sağlamsa blok tabanlı satırlar (YKS 2018+
        # için hassas), parçalanmışsa (kelime başına düşen satır ~1 ise,
        # 2010-2013 eski PDF'ler) görsel y-bant satırları kullanılır.
        col_data = []
        for (cx0, cx1) in columns:
            col_words = [w for w in words
                         if cx0 - 4 <= w[0] < cx1 + 4]
            blk = _lines_from_words(col_words)
            avg_wpl = len(col_words) / max(1, len(blk))
            if avg_wpl < 2.2:
                lines = _visual_lines(col_words)
            else:
                lines = blk
            lines = [l for l in lines if not _is_page_number(l)]
            lines.sort(key=lambda l: l["y0"])
            lines = _join_wrapped_headers(lines)
            col_data.append((cx0, cx1, lines))
        all_lines = [l for (_, _, ls) in col_data for l in ls]

        # tam genişlik başlıklar: kolon sınırını kesen bölüm adlarını onar.
        # MEB/LGS'de başlıklar ortalanmıştır ve iki kolona bölünebilir
        # ('T.C. İNKILAP TARİHİ VE' | 'ATATÜRKÇÜLÜK'); sol parça bilinen bir
        # adın önekiyse sağ kolondaki aynı satırla birleştirilir.
        if len(col_data) == 2:
            left_lines, right_lines = col_data[0][2], col_data[1][2]
            for la in left_lines:
                ta = la["text"].strip()
                tan = _norm_upper(ta)
                if len(tan) < 3 or extract_section_name(ta):
                    continue
                for known in SECTION_ID_MAP:
                    kn = _norm_upper(known)
                    if not kn.startswith(tan):
                        continue
                    for lb in right_lines:
                        if abs(lb["y0"] - la["y0"]) > 8:
                            continue
                        joined = extract_section_name(ta + " " + lb["text"].strip())
                        if joined:
                            la["text"] = ta + " " + lb["text"].strip()
                            la["words"] = la["words"] + lb["words"]
                            lb["text"] = ""  # sağ parça artık içerik değil
                            break
                    if extract_section_name(la["text"]):
                        break

        # bölüm başlıkları: tam genişlik satırlarda ara (kolon bölünmesi
        # başlığı iki parçaya bilese de y-bant onları aynı satırda birleşti-
        # rir); dikey bölünmeler ardışık satır çifti birleştirilerek denenir
        full_lines = [l for l in _visual_lines(words) if not _is_page_number(l)]
        full_lines.sort(key=lambda l: (l["y0"], l["x0"]))
        for i, ln in enumerate(full_lines):
            if ln["y0"] >= 120:
                break
            t = ln["text"].strip()
            if _is_end_line(t):
                continue
            name = _match_section_contains(t)
            if not name and i + 1 < len(full_lines) \
                    and abs(full_lines[i + 1]["y0"] - ln["y1"]) < 15:
                nxt = full_lines[i + 1]["text"].strip()
                if not _is_end_line(nxt) and len(nxt) < 35:
                    name = _match_section_contains(t + " " + nxt)
            if name:
                cur_name = name
                cur_sid = section_id_from_name(cur_name)
                expected_next[cur_sid] = 1
                if (cur_sid, cur_name) not in res.sections:
                    res.sections.append((cur_sid, cur_name))
                break  # sayfa başına ilk başlık yeter

        for (col_x0, col_x1, col_lines) in col_data:
            if not col_lines:
                continue

            # kolon alt sınırı: varsa END_MARKER satırı, yoksa son içerik satırı
            end_ys = [l["y0"] for l in col_lines
                      if _is_end_line(l["text"])]
            if end_ys:
                cut_y = min(end_ys) - 2
                col_lines = [l for l in col_lines if l["y0"] < cut_y]
                if not col_lines:
                    continue
                cut_y = min(cut_y, max(l["y1"] for l in col_lines) + 4)
            else:
                cut_y = max(l["y1"] for l in col_lines) + 4

            # bölüm olayları: 'cevap kâğıdının X Testi' talimatı ve kolon
            # içindeki TESTİ başlıkları (sayfa ortası bölüm geçişleri dahil)
            switch_ys = []   # önceki bölümün sorularının bittiği y
            header_lines = set()
            for ln in col_lines:
                t = ln["text"].strip()
                m = CEVAP_KAGIDI_NAME.search(t)
                if m:
                    name = m.group(1).strip()
                    sid = section_id_from_name(name)
                    if sid != cur_sid:
                        cur_name, cur_sid = name, sid
                        expected_next[cur_sid] = 1
                        if (cur_sid, cur_name) not in res.sections:
                            res.sections.append((cur_sid, cur_name))
                        switch_ys.append(ln["y0"])
                    header_lines.add(id(ln))
                    continue
                if not _is_end_line(t):
                    name2 = extract_section_name(t)
                    if name2:
                        sid2 = section_id_from_name(name2)
                        if sid2 != cur_sid:
                            # aynı bölümün parça başlığı mı? ('FEN' +
                            # 'BİLİMLERİ TESTİ') — geçiş sayma
                            cn1 = _canon(cur_name or "")
                            cn2 = _canon(name2)
                            same = cn1 and (cn1 in cn2 or cn2 in cn1)
                            if not same:
                                cur_name, cur_sid = name2, sid2
                                expected_next[cur_sid] = 1
                                if (cur_sid, cur_name) not in res.sections:
                                    res.sections.append((cur_sid, cur_name))
                                switch_ys.append(ln["y0"])
                        header_lines.add(id(ln))

            anchors = []
            # kolon çapası: soru numaralı satırların en solu. Başlıklar
            # (ortalanmış) cax'ı sağa çekebildiğinden konum SORULARDAN
            # türetilir; satır içi referanslar her zaman daha sağdadır.
            qnum_xs = [l["words"][0][0] for l in col_lines
                       if QNUM.match(l["words"][0][4]) and id(l) not in header_lines]
            if qnum_xs:
                col_anchor_x = min(qnum_xs)
            else:
                # çapa yoksa: başlık hariç uzun satırların en sol x'i.
                # Kelime tamamlamalı (cloze) sorularda tüm satırlar tek
                # kelimelik olabildiğinden boşsa tüm satırlara düş.
                cax_lines = [l for l in col_lines
                             if len(l["words"]) >= 3 and id(l) not in header_lines]
                if not cax_lines:
                    cax_lines = [l for l in col_lines if id(l) not in header_lines]
                col_anchor_x = min((l["x0"] for l in cax_lines), default=col_x0)
            for ln in col_lines:
                if id(ln) in header_lines:
                    continue
                t = ln["text"].strip()
                em = EXPECTED_COUNT.search(t)
                if em:
                    res.expected_counts[cur_sid or cur_name] = int(em.group(1))
                first = ln["words"][0]
                if QNUM.match(first[4]) and first[0] < col_anchor_x + 30:
                    rest = " ".join(w[4] for w in ln["words"][1:])
                    if BOILERPLATE.match(rest) or FALSE_ANCHOR.match(rest):
                        continue
                    no = int(first[4][:-1])
                    exp = expected_next.get(cur_sid, 1)
                    if no < exp:
                        # geriye ginen çapa: soru metni içi referans
                        # ("1. işlem:", "2. satır..." vb.)
                        continue
                    if no == exp + 1:
                        res.warnings.append(
                            f"soru atlandı: {cur_sid} no={exp} (s.{pi + 1})")
                    elif no > exp + 1:
                        res.warnings.append(
                            f"sıra dışı çapa: {cur_sid} no={no} "
                            f"beklenen={exp} (s.{pi + 1})")
                    expected_next[cur_sid] = no + 1
                    anchors.append((no, ln["y0"], ln))

            for i, (no, y0, ln) in enumerate(anchors):
                y1 = cut_y if i == len(anchors) - 1 else anchors[i + 1][1] - 3
                # bölüm geçiş noktasına kadar kes
                for sy in switch_ys:
                    if y0 < sy - 2:
                        y1 = min(y1, sy - 2)
                y1 = min(y1, cut_y)
                if y1 - y0 < 18:
                    res.warnings.append(
                        f"şüpheli çapa: s.{pi + 1} no={no} yükseklik={y1 - y0:.0f}")
                    continue
                if cur_sid is None:
                    cur_sid, cur_name = "belirsiz", "BELİRSİZ"
                    if ("belirsiz", "BELİRSİZ") not in res.sections:
                        res.sections.append((cur_sid, cur_name))
                    res.warnings.append(f"başlıksız bölüm s.{pi + 1} no={no}")
                res.questions.append(Question(
                    section=cur_sid, section_name=cur_name, no=no, page=pi,
                    bbox=(max(col_x0 - 6, 0), max(y0 - 5, 0),
                          min(col_x1 + 6, page.rect.x1), min(y1, page.rect.y1)),
                ))

    res.warnings.append(f"cevap anahtarı sayfaları: {sorted(p + 1 for p in answer_pages)}")
    for pi in sorted(answer_pages):
        res.answer_key.update(_parse_answer_page(doc[pi]))
    # ayrı cevap anahtarı PDF'i (2010-2011 YGS, 2010 LYS-5)
    if key_pdf is not None and Path(key_pdf).exists():
        kdoc = pymupdf.open(str(key_pdf))
        ext = {}
        for pi in range(len(kdoc)):
            ext.update(_parse_answer_page(kdoc[pi]))
        for sid, entries in ext.items():
            tgt = res.answer_key.setdefault(sid, {})
            for no, letter in entries.items():
                tgt[no] = letter  # ayrı dosya önceliklidir
        res.warnings.append(f"ayrı cevap anahtarı: {key_pdf}")
    _attach_answers(res)
    return res


def _key_segments(words, split=10.0):
    """Anahtar sayfası için satır-segmentleri üretir.

    Kelimeler y-bant ile satırlara birleşir (bazı eski PDF'lerde her kelime
    ayrı bloktur). Satır içi bölünme boşluk eşiğiyle değil içerik kuralıyla
    yapılır: harf (A-E/İPTAL) sonrası 'N.' sayısı yeni girdi, TESTİ sonrası
    büyük harf kelime yeni başlıktır (tablo hücre dolguları değişkendir)."""
    segs = []
    for row in _visual_rows(words):
        ws = sorted(row, key=lambda w: w[0])
        cur: list = []
        for w in ws:
            brk = False
            if cur:
                lw = cur[-1][4]
                gap = w[0] - cur[-1][2]
                if gap > 25:
                    brk = True
                elif re.fullmatch(r"\d{1,3}\.", w[4]) and (
                        re.fullmatch(r"[A-E]", lw) or lw.upper() == "İPTAL"):
                    brk = True  # önceki girdi bitti, yeni 'N.' başlıyor
                elif w[4][:1].isupper() and lw.upper() in ("TESTİ", "TESTI"):
                    brk = True  # önceki başlık bitti
            if brk:
                segs.append(cur)
                cur = [w]
            else:
                cur.append(w)
        if cur:
            segs.append(cur)
    out = []
    for ws in segs:
        ws.sort(key=lambda w: w[0])
        out.append({"text": " ".join(w[4] for w in ws),
                    "x0": ws[0][0], "y0": min(w[1] for w in ws),
                    "x1": ws[-1][2], "y1": max(w[3] for w in ws),
                    "block": -1, "line": -1, "words": ws})
    out.sort(key=lambda l: (l["y0"], l["x0"]))
    return out


def _visual_rows(words):
    """Kelimeleri y-bant ile satırlara gruplar (kelime listeleri döner).

    Bant satırın İLK kelimesine sabitlenir (kayan ortalama kullanılmaz):
    kayan ortalama, şekil etiketleri gibi araya giren kelimelerle zincirleme
    büyüyüp komşu satırları yutabiliyordu.
    """
    rows = []
    for w in sorted(words, key=lambda w: (w[1], w[0])):
        mid = (w[1] + w[3]) / 2
        placed = False
        for row in rows:
            if abs(mid - row["_anchor"]) < 4:
                row["words"].append(w)
                placed = True
                break
        if not placed:
            rows.append({"words": [w], "_anchor": mid})
    rows.sort(key=lambda r: r["words"][0][1])
    return [r["words"] for r in rows]


def _repair_headers(lines):
    """Bölünmüş başlıkları onarır.

    İki biçim: dikey kaydırma ('SOSYAL BİLİMLER' üstte + 'TESTİ' altta) ve
    aynı satırda yatay bölünme ('TEMEL MATEMATİK' | 'TESTİ' hücre dolgusu
    nedeniyle ayrı segmentte).
    """
    known_ids = set(SECTION_ID_MAP.values())
    fixed, consumed = [], set()
    for ln in lines:
        if id(ln) in consumed:
            continue
        t = ln["text"].strip()
        if t.endswith(("TESTİ", "TESTI")) and len(t) < 55 and section_id_from_name(t) not in known_ids:
            for p in lines:
                pt = p["text"].strip()
                if p is ln or id(p) in consumed:
                    continue
                if pt.endswith(("TESTİ", "TESTI")) or ANSWER_LINE.match(pt) or len(pt) > 60:
                    continue
                vertical = (abs(p["x0"] - ln["x0"]) < 60
                            and -4 < ln["y0"] - p["y1"] < 26)
                horizontal = (abs(p["y0"] - ln["y0"]) < 5
                              and 0 < ln["x0"] - p["x1"] < 40)
                if vertical or horizontal:
                    nl = dict(ln)
                    nl["text"] = pt + " " + t
                    nl["y0"] = min(nl["y0"], p["y0"])
                    nl["x0"] = min(nl["x0"], p["x0"])
                    nl["x1"] = max(nl["x1"], p["x1"])
                    ln = nl
                    consumed.add(id(p))
                    break
        fixed.append(ln)
    return fixed


def _parse_answer_page(page) -> dict:
    """Cevap anahtarı sayfasını {section_id: {no: harf}} olarak ayrıştırır.

    Yöntem:
      1. Satırlar y-bantla kurulur; satır içi birimler içerik kuralıyla
         bölünür (harf sonrası 'N.' yeni girdi, TESTİ sonrası yeni başlık).
      2. Başlık birimleri iç boşluklarla (~15pt) test adlarına ayrılır,
         dikey kaymış TESTİ parçaları onarılır.
      3. Her cevap girişi, konum olarak en yakın başlığa atanır (üstünde
         başlık varsa onların arasından; kolon boşlukları belgeden belgeye
         değiştiğinden sabit bant kullanılmaz).
    """
    key = {}
    words = page_words(page, y_top=15)
    units = _key_segments(words)

    answers = []
    header_units = []
    for ln in units:
        t = ln["text"].strip()
        if _is_end_line(t):
            continue
        if ANSWER_LINE.match(t) or ANSWER_IPTAL.match(t):
            answers.append(ln)
            continue
        if "CEVAP ANAHTARI" in _norm_upper(t) or "KİTAPÇIĞI" in _norm_upper(t):
            continue  # sayfa başlığı/başlık kalabalığı, test adı değil
        if (len(t) < 60 and sum(1 for c in t if c.isupper()) >= 4):
            header_units.append(ln)
        elif t in ("TESTİ", "TESTI"):
            header_units.append(ln)

    # başlık birimlerini iç boşluklarla parçala (başlık içi ~3pt,
    # testler arası ≥20pt), TESTİ kaymalarını onar
    pieces = []
    for ln in header_units:
        ws = sorted(ln["words"], key=lambda w: w[0])
        part = [ws[0]]
        for w in ws[1:]:
            if w[0] - part[-1][2] > 15:
                pieces.append(part)
                part = [w]
            else:
                part.append(w)
        pieces.append(part)
    pieces = [{"text": " ".join(w[4] for w in ws),
               "x0": ws[0][0], "y0": min(w[1] for w in ws),
               "x1": ws[-1][2], "y1": max(w[3] for w in ws),
               "words": ws} for ws in pieces]
    pieces = _repair_headers(pieces)

    header_pts = []  # (y, x0, sid)
    for ln in pieces:
        t = ln["text"].strip()
        name = extract_section_name(t) if len(t) < 55 else None
        if name:
            header_pts.append((ln["y0"], ln["x0"], section_id_from_name(name)))
    header_pts.sort()

    for u in answers:
        t = u["text"].strip()
        am = ANSWER_LINE.match(t)
        if am:
            no, letter = int(am.group(1)), am.group(2)
        else:
            im = ANSWER_IPTAL.match(t)
            if not im:
                continue
            no, letter = int(im.group(1)), ""
        cands = [h for h in header_pts if h[0] <= u["y0"] + 1] or header_pts
        if not cands:
            continue
        best = min(cands, key=lambda h: (abs(h[1] - u["x0"]), -h[0]))
        key.setdefault(best[2], {})[no] = letter
    return key


def _attach_answers(res: BookletResult):
    for q in res.questions:
        q.answer = res.answer_key.get(q.section, {}).get(q.no, "")


# ---------------------------------------------------------------- render

# Boş kırpım eşiği: içerik alanında (sol numara şeridi hariç) bu orandan
# az koyu piksel varsa kırpım boş kabul edilir (%10 örneklerde '1.' gibi
# yalnız numara blokları soru metni olmadan gelebilir).
BLANK_RATIO = 0.002


def _is_blank_crop(img: Image.Image) -> bool:
    g = img.convert("L").resize((80, 80))
    px = g.load()
    # sol şerit (ilk 10 sütun) numara bölgesi: hesaba katılmaz
    ink = sum(1 for x in range(10, 80) for y in range(80) if px[x, y] < 245)
    return ink < BLANK_RATIO * (70 * 80)


def render_questions(pdf_path: str | Path, result: BookletResult,
                     out_dir: str | Path, fmt: str = "webp", quality: int = 82,
                     drop_blank: bool = True):
    """Her sorunun bbox alanını yüksek çözünürlükte kırpıp kaydeder.

    drop_blank=True ise boş/neredeyse boş kırpımlar soru listesinden de
    düşürülür (%10 örnek kitapçıklardaki soru aralarındaki boşluk blokları).
    """
    doc = pymupdf.open(str(pdf_path))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # eski koşuldan kalan kırpımları temizle (bırakılan soruların dosyaları
    # aksi halde diskte boş kırpım olarak kalır)
    for old in out_dir.glob("q_*." + fmt):
        old.unlink()
    mat = pymupdf.Matrix(ZOOM, ZOOM)
    kept = []
    dropped = []
    for q in result.questions:
        pix = doc[q.page].get_pixmap(matrix=mat, clip=pymupdf.Rect(*q.bbox))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        if drop_blank and _is_blank_crop(img):
            dropped.append(q)
            continue
        fname = f"q_{q.section}_{q.no:03d}.{fmt}"
        img.save(out_dir / fname, fmt.upper(), quality=quality, method=4)
        q.img = fname
        kept.append(q)
    if dropped:
        result.warnings.append(
            f"boş kırpım atıldı: {len(dropped)} soru "
            f"({', '.join(f'{q.section}#{q.no}' for q in dropped[:6])}"
            f"{'…' if len(dropped) > 6 else ''})")
        result.questions = kept


def save_json(result: BookletResult, out_dir: str | Path, meta: dict | None = None):
    out = {
        "meta": meta or {},
        "sections": [{"id": sid, "name": name} for sid, name in result.sections],
        "qa": result.qa_report(),
        "warnings": result.warnings,
        "questions": [asdict(q) for q in result.questions],
    }
    (Path(out_dir) / "questions.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
