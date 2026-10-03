import { useEffect, useState } from 'react'

interface Props {
  onEnter: () => void
  ready: boolean
}

const FEATURES = [
  {
    icon: '📚',
    title: 'Karışık yok — hepsi tek yerde',
    body: 'YKS, KPSS, LGS, ALES, YGS/LYS, Açık Öğretim ve daha fazlası; kaynak ve sınav kategorilerine ayrılmış temiz bir arşiv.',
  },
  {
    icon: '✍️',
    title: 'Gerçek sınav deneyimi',
    body: 'Sorular orijinal kitapçıktan kesilir; formüller ve şekiller bozulmaz. Süre tutarız, işaretlersin, netini anında görürsün.',
  },
  {
    icon: '📈',
    title: 'İlerlemen saklı kalır',
    body: 'Yarım bıraktığın test kaldığın yerden devam eder; sonuçların tarayıcında güvende.',
  },
]

export default function Landing({ onEnter, ready }: Props) {
  const [stats, setStats] = useState<{ tests: number; questions: number } | null>(null)

  useEffect(() => {
    fetch('/data/index.json')
      .then((r) => r.json())
      .then((d) => setStats({ tests: d.length, questions: d.reduce((s: number, e: any) => s + e.total, 0) }))
      .catch(() => setStats(null))
  }, [])

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      {/* arka plan dokusu: yumuşak gradyan halkalar */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -top-40 right-[-10%] size-[34rem] rounded-full bg-accent-soft blur-3xl" />
        <div className="absolute bottom-[-30%] left-[-10%] size-[30rem] rounded-full bg-indigo-100 blur-3xl" />
      </div>

      <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-xl bg-accent text-base font-bold text-white">ÖA</span>
          <span className="text-[15px] font-bold tracking-tight">Soru Arşivim</span>
        </div>
        <button
          onClick={onEnter}
          className="rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink-soft hover:border-accent hover:text-accent"
        >
          Arşive git
        </button>
      </header>

      <main className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col justify-center px-6 pb-16">
        <div className="max-w-2xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1 text-[11px] font-semibold text-ink-soft">
            <span className="size-1.5 rounded-full bg-good" />
            {stats ? `${stats.tests} kitapçık · ${stats.questions.toLocaleString('tr-TR')} soru hazır` : 'arşiv yükleniyor…'}
          </span>
          <h1 className="mt-5 text-[2.6rem] font-extrabold leading-[1.1] tracking-tight text-ink sm:text-6xl">
            Çıkmış sorular,
            <br />
            <span className="text-accent">gerçekten çözebileceğin</span> bir arşivde.
          </h1>
          <p className="mt-5 max-w-xl text-[17px] leading-relaxed text-ink-soft">
            ÖSYM ve MEB'in yayımladığı geçmiş yılların sınav soruları; orijinal hâliyle
            kesildi, cevap anahtarlarıyla eşleşti ve test olarak çözülmeyi bekliyor.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <button
              onClick={onEnter}
              disabled={!ready}
              className="rounded-xl bg-accent px-6 py-3 text-[15px] font-bold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700 disabled:opacity-50"
            >
              {ready ? 'Çözmeye başla →' : 'Katalog hazırlanıyor…'}
            </button>
            <span className="text-xs text-ink-faint">kurulum yok · internet gerekmez · ilerlemen tarayıcıda</span>
          </div>
        </div>

        <div className="mt-14 grid gap-4 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="card p-5">
              <div className="text-2xl">{f.icon}</div>
              <h3 className="mt-3 text-sm font-bold">{f.title}</h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-ink-soft">{f.body}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="relative z-10 mx-auto w-full max-w-6xl px-6 pb-6 text-[11px] text-ink-faint">
        Sorular ÖSYM / MEB telifidir — bu arşiv yalnızca kişisel çalışma amaçlıdır.
      </footer>
    </div>
  )
}
