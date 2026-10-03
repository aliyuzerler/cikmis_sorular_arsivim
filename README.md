# Soru Arşivim — ÖSYM & MEB Çıkmış Sorular Arşivi

Geçmiş yılların resmî sınav sorularını **çözülebilir test formatına** getiren
kişisel arşiv uygulaması. Sorular kitapçık PDF'lerinden yüksek çözünürlükte
kesilir (formüller/şekiller bozulmaz), cevap anahtarlarıyla eşleşir ve
tarayıcıda test olarak çözülür.

## Kapsam

| Kaynak | Sınav | Yıllar | Kitapçık |
|---|---|---|---|
| ÖSYM | YKS — TYT / AYT / YDT (5 dil) | 2018-2026 | 63 |
| ÖSYM | YGS / LYS | 2010-2013, 2017 | 68 |
| ÖSYM | KPSS %10 örnekleri (Lisans GY-GK+Eğitim B., A Grubu Alan Bilgisi oturumları, ÖABT branşları, Ortaöğretim, Ön Lisans, DHBT) | 2016-2026 | 211 |
| ÖSYM | ALES /2 %10 örnekleri | 2018-2026 | 9 (cevap anahtarı ÖSYM yayımlamıyor) |
| ÖSYM | DGS %10 örneği | 2026 | 1 |
| MEB | LGS (Sözel + Sayısal) | 2018-2025 | 16 |
| MEB | Açık Öğretim (Lise + Ortaokul, dönem sınavları) | 2014-2026 | 44 |
| MEB | Adalet Bakanlığı Görevde Yükselme (10 kademe × A/B) | 2025 | 20 |

Toplam: **432 kitapçık, ~22.000 soru.** Her kitapçığın soru sayısı ve cevap
anahtarı otomatik QA'dan geçirilir; eksik olanlar arayüzde "⚠ kontrol öner"
rozetiyle işaretlenir.

> **Yayımlanmayan sınavlar:** Ehliyet (MTSK) e-sınava geçtiği için, özel
> güvenlik görevlisi kitaplıkları EGM'de bulunduğu için, YDS/YÖKDİL/ALES /1-/3
> duyurularında PDF bağlantısı bulunmadığı için, DGS/MSÜ eski yılları yalnız
> AİS (aday girişi) üzerinden erişildiği için ve TUS/DUS/EUS/TR-YÖS aynı AİS
> modelini kullandığı için bu sınavlar arşivde yer almamaktadır.
> YGS/LYS 2014-2016 için ÖSYM yalnızca %20'lik bölümü yayımlamıştır.

## Çalıştırma

```bash
cd app
npm install
npm run dev        # http://localhost:5173 (veya 5200)
```

Uygulama, kök dizindeki `data/` klasörünü `/data` yolu üzerinden servis eder
(Vite middleware). İnternet gerekmez; ilerleme localStorage'da tutulur.

Telefonda kullanım: aynı ağ üzerinden `npm run dev -- --host` ile açın ve
telefondan "Ana ekrana ekle" deyin (PWA paketi planlı).

## Veri hattı (yeni sınav/ yıl eklemek)

```
data/raw/<sinav>/<yil>_<oturum>/kitapcik.pdf     # ham PDF
        │  python -m pipeline.process_all [sinav]
        ▼
data/processed/<sinav>/<yil>/<oturum>/           # q_<bolum>_<no>.webp + questions.json
        │  python pipeline/build_catalog.py
        ▼
data/index.json                                  # uygulama kataloğu
```

1. **İndirme** — her kaynak için `pipeline/downloaders/` altında bir modül:
   - `yks.py` — ÖSYM duyuru sayfalarından YKS 2018-2026
   - `osym_general.py` — YGS/LYS duyuruları (eski `eskidosyalar` + yeni bağlantı biçimleri)
   - `meb.py` — MEB/ODSGM LGS kitapçıkları
2. **İşleme** — `pipeline/osym_parser.py`:
   - sütun tespiti (belge geneli medyan gutter),
   - soru numarası çapaları + sıra sürekliliği denetimi,
   - bölüm başlığı tespiti (TESTİ'li, TESTİ'siz/MEB, birleşik adlar),
   - cevap anahtarı sayfası ayrıştırıcı (yatay/dikey/kolon düzenleri, İPTAL desteği),
   - parçalanmış blok yapısına sahip eski PDF'ler için görsel y-bant satırları.
3. **Yamalar** — ayrıştırıcının çözemediği kenar durumlar için
   `pipeline/fixes/<sinav>_<yil>_<oturum>.json`:
   `expected_counts`, `key_overrides`, `drop_questions`, `section_map`.
   Örn. LGS anahtarları `pipeline/fix_lgs.py` ile otomatik üretilir.
4. **İçerik doğrulama** — `python -m pipeline.verify_sessions` klasör adı ile
   PDF içeriği uyuşmayan kitaplıkları (ÖSYM bağlantı kaymaları) bulur ve
   döngüsel zincirleri güvenli biçimde yeniden adlandırır.

## Katalog yapısı

`data/index.json` her test için: `id, exam, examName, source (osym|meb),
sourceName, year, session, sessionName, path, total, withAnswers, sections[],
qaOk`. Arayüz kaynak sekmesi (ÖSYM/MEB) → sınav kategorisi → yıl → oturum
akışıyla filtreler.

## Sorun giderme

- Katalog boş görünüyorsa: `python pipeline/build_catalog.py`
- Bir kitapçığın soruları eksikse: `data/qa/report.json`'da o kitapçığın
  `questions_found / expected` değerlerine bakın; gerekirse `pipeline/fixes/`
  yaması ekleyip `python -m pipeline.process_all <sinav>` çalıştırın.
- Ayrıştırıcıyı tek kitapçıkta denemek: `python -c "import sys; sys.path.insert(0,'pipeline'); from osym_parser import parse_booklet; print(parse_booklet('<pdf>').qa_report())"`

## Telif

Sorular ÖSYM'ye / MEB'e aittir. Bu arşiv **yalnızca kişisel çalışma amaçlıdır**;
ticari kullanım veya yeniden yayım uygun değildir.
