import { useMemo } from 'react'
import type { CatalogEntry, Question, TestData } from '../types'
import { loadProgress } from '../lib/storage'

interface Props {
  entry: CatalogEntry
  test: TestData
  sectionFilter: string
  onHome: () => void
  onRetry: (sectionFilter: string) => void
}

export default function Results({ entry, test, sectionFilter, onHome, onRetry }: Props) {
  const questions = useMemo(() => {
    const saved = loadProgress(entry.id)
    if (saved?.questionIds.length) {
      const set = new Set(saved.questionIds)
      const filtered = test.questions.filter((q) => set.has(`${q.section}_${q.no}`))
      if (filtered.length) return filtered
    }
    return sectionFilter
      ? test.questions.filter((q) => q.section === sectionFilter)
      : test.questions
  }, [entry.id, sectionFilter, test.questions])

  const progress = loadProgress(entry.id)
  const answers = progress?.answers ?? {}

  const rows = useMemo(() => {
    const bySection = new Map<
      string,
      { name: string; qs: Question[]; correct: number; wrong: number; blank: number }
    >()
    for (const q of questions) {
      const s = bySection.get(q.section) ?? {
        name: q.section_name,
        qs: [],
        correct: 0,
        wrong: 0,
        blank: 0,
      }
      const a = answers[`${q.section}_${q.no}`]
      if (!a) s.blank++
      else if (a === q.answer) s.correct++
      else s.wrong++
      s.qs.push(q)
      bySection.set(q.section, s)
    }
    return [...bySection.values()]
  }, [questions, answers])

  const total = rows.reduce(
    (acc, r) => ({
      correct: acc.correct + r.correct,
      wrong: acc.wrong + r.wrong,
      blank: acc.blank + r.blank,
    }),
    { correct: 0, wrong: 0, blank: 0 },
  )
  const net = total.correct - total.wrong / 4
  const pct = questions.length ? Math.round((total.correct / questions.length) * 100) : 0
  const elapsed = progress?.elapsed ?? 0
  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0')
  const ss = String(elapsed % 60).padStart(2, '0')

  const wrongList = questions.filter((q) => {
    const a = answers[`${q.section}_${q.no}`]
    return a && a !== q.answer
  })

  return (
    <div className="space-y-6 pb-10">
      {/* özet */}
      <section className="card p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-accent">Sonuç</div>
            <h1 className="mt-0.5 text-xl font-extrabold tracking-tight">
              {entry.examName} {entry.year} · {entry.sessionName}
            </h1>
          </div>
          <div className="text-right text-[13px] text-ink-soft">
            <div className="font-mono font-bold">⏱ {mm}:{ss}</div>
            <div>{questions.length} soru</div>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Doğru" value={total.correct} tone="good" />
          <Stat label="Yanlış" value={total.wrong} tone="bad" />
          <Stat label="Boş" value={total.blank} tone="soft" />
          <Stat label="Net (÷4)" value={net.toFixed(2)} tone="accent" />
        </div>

        <div className="mt-5">
          <div className="h-2 overflow-hidden rounded-full bg-line">
            <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${pct}%` }} />
          </div>
          <div className="mt-1.5 text-right text-[11px] font-semibold text-ink-faint">Başarı %{pct}</div>
        </div>
      </section>

      {/* bölüm dökümü */}
      <section className="card overflow-hidden">
        <h2 className="border-b border-line px-5 py-3.5 text-sm font-bold">Bölüm bazında</h2>
        <table className="w-full text-[13px]">
          <thead className="bg-canvas text-[11px] uppercase tracking-wide text-ink-faint">
            <tr>
              <th className="px-5 py-2 text-left font-bold">Bölüm</th>
              <th className="px-2 py-2 font-bold">D</th>
              <th className="px-2 py-2 font-bold">Y</th>
              <th className="px-2 py-2 font-bold">B</th>
              <th className="px-5 py-2 font-bold">Net</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((r) => (
              <tr key={r.name}>
                <td className="px-5 py-2.5 font-semibold">{r.name}</td>
                <td className="px-2 py-2.5 text-center font-bold text-good">{r.correct}</td>
                <td className="px-2 py-2.5 text-center font-bold text-bad">{r.wrong}</td>
                <td className="px-2 py-2.5 text-center text-ink-faint">{r.blank}</td>
                <td className="px-5 py-2.5 text-center font-bold tabular-nums">
                  {(r.correct - r.wrong / 4).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* yanlışlar */}
      {wrongList.length > 0 && (
        <section className="card overflow-hidden">
          <h2 className="border-b border-line px-5 py-3.5 text-sm font-bold">
            Yanlış yapılan sorular <span className="text-ink-faint">({wrongList.length})</span>
          </h2>
          <div className="divide-y divide-line">
            {wrongList.map((q) => {
              const a = answers[`${q.section}_${q.no}`]
              return (
                <div key={`${q.section}_${q.no}`} className="flex items-center gap-3 px-5 py-2.5 text-[13px]">
                  <span className="text-xs text-ink-faint">
                    {q.section_name} · {q.no}
                  </span>
                  <span className="rounded-md bg-red-50 px-2 py-0.5 text-xs font-bold text-bad">Senin: {a}</span>
                  <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-bold text-good">
                    Doğru: {q.answer || '—'}
                  </span>
                  <a
                    href={`${entry.path}/${q.img}`}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-auto text-xs font-semibold text-accent hover:underline"
                  >
                    soruyu gör →
                  </a>
                </div>
              )
            })}
          </div>
        </section>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onRetry(sectionFilter)}
          className="rounded-xl bg-accent px-5 py-2.5 text-sm font-bold text-white hover:bg-indigo-700"
        >
          ↻ Yeniden çöz
        </button>
        <button
          onClick={onHome}
          className="rounded-xl border border-line bg-white px-5 py-2.5 text-sm font-semibold text-ink-soft hover:border-accent hover:text-accent"
        >
          Ana sayfa
        </button>
      </div>
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: string | number; tone: string }) {
  const tones: Record<string, string> = {
    good: 'bg-emerald-50 text-good',
    bad: 'bg-red-50 text-bad',
    soft: 'bg-canvas text-ink-soft',
    accent: 'bg-accent-soft text-accent',
  }
  return (
    <div className={`rounded-xl px-4 py-3 ${tones[tone] ?? ''}`}>
      <div className="text-[10px] font-bold uppercase tracking-wider opacity-70">{label}</div>
      <div className="text-2xl font-extrabold tabular-nums">{value}</div>
    </div>
  )
}
