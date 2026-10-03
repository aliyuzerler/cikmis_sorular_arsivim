import { useMemo, useState } from 'react'
import type { CatalogEntry } from '../types'
import { loadProgress } from '../lib/storage'

interface Props {
  catalog: CatalogEntry[]
  onOpen: (entry: CatalogEntry, sectionFilter: string, fresh: boolean) => void
}

type Source = 'all' | 'osym' | 'meb'

export default function Home({ catalog, onOpen }: Props) {
  const [source, setSource] = useState<Source>('all')
  const [examFilter, setExamFilter] = useState<string>('all')

  const sources = useMemo(() => {
    const set = new Map<string, string>()
    for (const e of catalog) set.set(e.source, e.sourceName ?? e.source)
    return [...set.entries()].map(([id, name]) => ({ id: id as Source, name }))
  }, [catalog])

  const bySource = useMemo(
    () => catalog.filter((e) => source === 'all' || e.source === source),
    [catalog, source],
  )

  const categories = useMemo(() => {
    const map = new Map<string, { name: string; count: number; questions: number }>()
    for (const e of bySource) {
      const c = map.get(e.exam) ?? { name: e.examName, count: 0, questions: 0 }
      c.count++
      c.questions += e.total
      map.set(e.exam, c)
    }
    return [...map.entries()]
      .map(([id, v]) => ({ id, ...v }))
      .sort((a, b) => b.questions - a.questions)
  }, [bySource])

  const visible = useMemo(
    () => (examFilter === 'all' ? bySource : bySource.filter((e) => e.exam === examFilter)),
    [bySource, examFilter],
  )

  const exams = useMemo(() => {
    const map = new Map<string, CatalogEntry[]>()
    for (const e of visible) {
      if (!map.has(e.exam)) map.set(e.exam, [])
      map.get(e.exam)!.push(e)
    }
    return [...map.values()].map((entries) => ({
      entries: entries.sort((a, b) => b.year - a.year),
    }))
  }, [visible])

  const totalQ = visible.reduce((s, e) => s + e.total, 0)

  return (
    <div className="space-y-7">
      {/* başlık şeridi */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Sınav arşivi</h1>
          <p className="mt-1 text-sm text-ink-soft">
            {visible.length} kitapçık · {totalQ.toLocaleString('tr-TR')} soru
            {source !== 'all' && ` · ${sources.find((s) => s.id === source)?.name}`}
          </p>
        </div>
      </div>

      {/* kaynak sekmeleri */}
      <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Kaynak">
        <SourceTab active={source === 'all'} label="Tümü" onClick={() => { setSource('all'); setExamFilter('all') }} />
        {sources.map((s) => (
          <SourceTab
            key={s.id}
            active={source === s.id}
            label={s.name}
            onClick={() => { setSource(s.id); setExamFilter('all') }}
          />
        ))}
      </div>

      {/* sınav kategorileri */}
      {categories.length > 1 && (
        <div className="flex flex-wrap gap-1.5" aria-label="Sınav kategorileri">
          <Chip active={examFilter === 'all'} label={`Tüm sınavlar (${bySource.length})`} onClick={() => setExamFilter('all')} />
          {categories.map((c) => (
            <Chip
              key={c.id}
              active={examFilter === c.id}
              label={`${c.name} (${c.count})`}
              onClick={() => setExamFilter(c.id)}
            />
          ))}
        </div>
      )}

      {/* sınav kartları */}
      <div className="space-y-6">
        {exams.map(({ entries }) => (
          <ExamCard key={entries[0].exam} entries={entries} onOpen={onOpen} />
        ))}
      </div>
    </div>
  )
}

function SourceTab({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`rounded-xl px-4 py-2 text-sm font-bold transition ${
        active
          ? 'bg-accent text-white shadow-md shadow-indigo-100'
          : 'border border-line bg-white text-ink-soft hover:border-accent hover:text-accent'
      }`}
    >
      {label}
    </button>
  )
}

function Chip({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
        active
          ? 'bg-ink text-white'
          : 'border border-line bg-white text-ink-soft hover:border-ink-soft'
      }`}
    >
      {label}
    </button>
  )
}

function ExamCard({
  entries,
  onOpen,
}: {
  exam?: string
  entries: CatalogEntry[]
  onOpen: Props['onOpen']
}) {
  const name = entries[0].examName
  const total = entries.reduce((s, e) => s + e.total, 0)
  const years = useMemo(() => {
    const map = new Map<number, CatalogEntry[]>()
    for (const e of entries) {
      if (!map.has(e.year)) map.set(e.year, [])
      map.get(e.year)!.push(e)
    }
    return [...map.entries()].sort((a, b) => b[0] - a[0])
  }, [entries])

  return (
    <section className="card overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <h2 className="text-[15px] font-bold">{name}</h2>
        <span className="text-[11px] font-medium text-ink-faint">
          {entries.length} oturum · {total.toLocaleString('tr-TR')} soru
        </span>
      </div>
      <div className="divide-y divide-line">
        {years.map(([year, sessions]) => (
          <YearRow key={year} year={year} sessions={sessions} onOpen={onOpen} />
        ))}
      </div>
    </section>
  )
}

function YearRow({
  year,
  sessions,
  onOpen,
}: {
  year: number
  sessions: CatalogEntry[]
  onOpen: Props['onOpen']
}) {
  const [open, setOpen] = useState(false)

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-5 py-3 text-left transition hover:bg-accent-soft/60"
      >
        <span className="w-14 text-xl font-extrabold tabular-nums text-accent">{year}</span>
        <span className="flex flex-wrap gap-1.5">
          {sessions.map((s) => (
            <span key={s.id} className="rounded-full bg-canvas px-2.5 py-0.5 text-[11px] font-semibold text-ink-soft">
              {s.session.toUpperCase()}
            </span>
          ))}
        </span>
        <span className="ml-auto text-ink-faint">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="space-y-2.5 bg-canvas px-5 py-4">
          {sessions.map((s) => (
            <SessionPanel key={s.id} entry={s} onOpen={onOpen} />
          ))}
        </div>
      )}
    </div>
  )
}

function SessionPanel({ entry, onOpen }: { entry: CatalogEntry; onOpen: Props['onOpen'] }) {
  const progress = loadProgress(entry.id)

  let status: { label: string; cls: string } | null = null
  if (progress?.finished) {
    status = {
      label: '✓ Tamamlandı',
      cls: 'bg-emerald-50 text-good',
    }
  } else if (progress) {
    const pct = Math.round(
      (Object.keys(progress.answers).length / progress.questionIds.length) * 100,
    )
    status = { label: `⏸ %${pct} — devam ediyor`, cls: 'bg-amber-50 text-amber-700' }
  }

  return (
    <div className="rounded-xl border border-line bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-bold">{entry.sessionName}</span>
        <span className="text-[11px] text-ink-faint">{entry.total} soru</span>
        {!entry.qaOk && (
          <span
            title="Bazı bölümlerde soru sayısı/cevap anahtarı uyuşmuyor"
            className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700"
          >
            ⚠ kontrol öner
          </span>
        )}
        {status && (
          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${status.cls}`}>
            {status.label}
          </span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          onClick={() => onOpen(entry, '', true)}
          className="rounded-lg bg-accent px-3.5 py-1.5 text-[13px] font-bold text-white hover:bg-indigo-700"
        >
          ▶ Tümü ({entry.total})
        </button>
        {progress && !progress.finished && (
          <button
            onClick={() => onOpen(entry, '', false)}
            className="rounded-lg border border-amber-300 bg-amber-50 px-3.5 py-1.5 text-[13px] font-bold text-amber-700 hover:bg-amber-100"
          >
            ⏸ Kaldığım yerden
          </button>
        )}
        {entry.sections.map((s) => (
          <button
            key={s.id}
            onClick={() => onOpen(entry, s.id, true)}
            className="rounded-lg border border-line px-3.5 py-1.5 text-[13px] font-medium text-ink-soft hover:border-accent hover:text-accent"
          >
            {s.name} ({s.count})
          </button>
        ))}
      </div>
    </div>
  )
}
