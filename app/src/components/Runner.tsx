import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { CatalogEntry, Progress, Question, TestData } from '../types'
import { loadProgress, saveProgress } from '../lib/storage'

const LETTERS = ['A', 'B', 'C', 'D', 'E']

interface Props {
  entry: CatalogEntry
  test: TestData
  sectionFilter: string
  onExit: () => void
  onFinish: () => void
}

/**
 * Çözme ekranı — üst-alt düzen:
 *   üst sabit şerit  : test bilgisi + sayaç + ilerleme
 *   orta (esnek)     : soru görseli, ekrana sığacak şekilde ölçeklenir
 *   alt sabit şerit  : A–E şıkları + gezinme (her ekranda görünür)
 */
export default function Runner({ entry, test, sectionFilter, onExit, onFinish }: Props) {
  const questions: Question[] = useMemo(() => {
    if (sectionFilter) return test.questions.filter((q) => q.section === sectionFilter)
    const saved = loadProgress(entry.id)
    if (saved && !saved.finished && saved.questionIds.length > 0) {
      const set = new Set(saved.questionIds)
      const filtered = test.questions.filter((q) => set.has(`${q.section}_${q.no}`))
      if (filtered.length) return filtered
    }
    return test.questions
  }, [entry.id, sectionFilter, test.questions])

  const saved = useRef(loadProgress(entry.id))
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>(() => saved.current?.answers ?? {})
  const [flags, setFlags] = useState<Set<string>>(() => new Set(saved.current?.flags ?? []))
  const [elapsed, setElapsed] = useState(saved.current?.elapsed ?? 0)
  const [confirming, setConfirming] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [showKey, setShowKey] = useState(false)
  const q = questions[idx]
  const qid = q ? `${q.section}_${q.no}` : ''

  const persist = useCallback(
    (a: Record<string, string>, f: Set<string>, e: number, finished = false) => {
      const p: Progress = {
        answers: a,
        flags: [...f],
        elapsed: e,
        finished,
        questionIds: questions.map((x) => `${x.section}_${x.no}`),
        updatedAt: Date.now(),
      }
      saveProgress(entry.id, p)
    },
    [entry.id, questions],
  )

  useEffect(() => {
    const t = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    persist(answers, flags, elapsed)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answers, flags])

  const answer = useCallback(
    (letter: string) => {
      setAnswers((prev) => {
        const next = { ...prev }
        if (next[qid] === letter) delete next[qid]
        else next[qid] = letter
        return next
      })
    },
    [qid],
  )

  const move = useCallback(
    (d: number) => setIdx((i) => Math.min(questions.length - 1, Math.max(0, i + d))),
    [questions.length],
  )

  const toggleFlag = useCallback(() => {
    setFlags((prev) => {
      const next = new Set(prev)
      if (next.has(qid)) next.delete(qid)
      else next.add(qid)
      return next
    })
  }, [qid])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return
      const k = e.key.toUpperCase()
      if (LETTERS.includes(k)) answer(k)
      else if (k >= '1' && k <= '5') answer(LETTERS[Number(k) - 1])
      else if (e.key === 'ArrowRight') move(1)
      else if (e.key === 'ArrowLeft') move(-1)
      else if (k === 'F') toggleFlag()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [answer, move, toggleFlag])

  if (!q) {
    return (
      <div className="card p-8 text-center text-sm text-ink-soft">
        Bu bölümde soru bulunamadı.
        <button onClick={onExit} className="ml-2 font-semibold text-accent underline">Ana sayfa</button>
      </div>
    )
  }

  const answeredCount = Object.keys(answers).length
  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0')
  const ss = String(elapsed % 60).padStart(2, '0')

  const finish = () => {
    persist(answers, flags, elapsed, true)
    onFinish()
  }

  return (
    <div className="flex h-[calc(100vh-65px)] flex-col -my-8">
      {/* üst sabit şerit */}
      <div className="border-b border-line bg-white px-5 py-2.5">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-1 text-[13px]">
          <button
            onClick={onExit}
            className="rounded-lg border border-line px-2.5 py-1 text-xs font-semibold text-ink-soft hover:border-accent hover:text-accent"
          >
            ← Çık
          </button>
          <span className="font-bold">
            {entry.examName} {entry.year}
            <span className="ml-1.5 font-medium text-ink-soft">· {entry.sessionName}</span>
          </span>
          <span className="rounded-lg bg-canvas px-2.5 py-0.5 font-mono text-xs font-bold tabular-nums text-ink">
            ⏱ {mm}:{ss}
          </span>
          <span className="text-xs text-ink-faint">
            {answeredCount}/{questions.length} işaretli
          </span>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setPaletteOpen((v) => !v)}
              className="rounded-lg border border-line px-2.5 py-1 text-xs font-semibold text-ink-soft hover:border-accent hover:text-accent"
            >
              ▦ Sorular
            </button>
            <button
              onClick={() => setConfirming(true)}
              className="rounded-lg bg-good px-3 py-1 text-xs font-bold text-white hover:bg-emerald-700"
            >
              Testi Bitir
            </button>
          </div>
        </div>
        {/* ilerleme çizgisi */}
        <div className="mx-auto mt-2 h-1 max-w-5xl overflow-hidden rounded-full bg-line">
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${questions.length ? (answeredCount / questions.length) * 100 : 0}%` }}
          />
        </div>
        {paletteOpen && (
          <div className="mx-auto mt-2 flex max-w-5xl flex-wrap gap-1.5 pb-1">
            {questions.map((x, i) => {
              const xid = `${x.section}_${x.no}`
              const isCur = i === idx
              const ans = answers[xid]
              return (
                <button
                  key={xid}
                  onClick={() => { setIdx(i); setPaletteOpen(false) }}
                  className={`grid size-8 place-items-center rounded-lg text-xs font-bold tabular-nums ${
                    isCur
                      ? 'bg-accent text-white'
                      : ans
                        ? 'bg-emerald-50 text-good ring-1 ring-emerald-200'
                        : 'bg-canvas text-ink-soft ring-1 ring-line'
                  } ${flags.has(xid) ? 'ring-2 !ring-amber-400' : ''}`}
                >
                  {x.no}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* orta: soru alanı — görsel ekrana sığar, gerekirse panelde kaydırılır */}
      <div className="relative min-h-0 flex-1 overflow-hidden bg-canvas">
        <div className="mx-auto h-full max-w-4xl px-5 pt-3">
          <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold text-ink-faint">
            <span>{q.section_name}</span>
            <span>·</span>
            <span>Soru {q.no} / {questions.length}</span>
            {flags.has(qid) && <span className="text-amber-600">⚑ işaretli</span>}
            <div className="ml-auto flex gap-1.5">
              <button
                onClick={() => setShowKey((v) => !v)}
                className="rounded-md border border-line bg-white px-2 py-0.5 text-[11px] font-semibold text-ink-soft hover:border-accent hover:text-accent"
                title="Cevabı göster/gizle"
              >
                {showKey ? 'Cevabı gizle' : 'Cevabı göster'}
              </button>
            </div>
          </div>
          <div className="h-[calc(100%-2rem)] w-full overflow-hidden rounded-xl border border-line bg-white shadow-sm">
            <img
              src={`${entry.path}/${q.img}`}
              alt={`${q.section_name} ${q.no}. soru`}
              className="q-fit"
              loading="eager"
            />
          </div>
          {showKey && q.answer && (
            <div className="absolute right-6 top-10 rounded-xl bg-ink/90 px-4 py-2 text-sm font-bold text-white shadow-lg">
              Cevap: {q.answer}
            </div>
          )}
        </div>
      </div>

      {/* alt sabit şerit: şıklar + gezinme */}
      <div className="border-t border-line bg-white px-5 py-3 shadow-[0_-4px_16px_rgb(0_0_0/0.04)]">
        <div className="mx-auto max-w-4xl">
          <div className="grid grid-cols-5 gap-2">
            {LETTERS.map((L) => (
              <button
                key={L}
                onClick={() => answer(L)}
                className={`rounded-xl py-2.5 text-base font-bold transition ${
                  answers[qid] === L
                    ? 'bg-accent text-white shadow-md shadow-indigo-100'
                    : 'border border-line bg-white text-ink-soft hover:border-accent hover:text-accent'
                }`}
              >
                {L}
              </button>
            ))}
          </div>
          <div className="mt-2.5 flex items-center justify-between">
            <button
              onClick={() => move(-1)}
              disabled={idx === 0}
              className="rounded-lg border border-line px-4 py-1.5 text-[13px] font-semibold text-ink-soft disabled:opacity-40 hover:border-accent hover:text-accent"
            >
              ← Önceki
            </button>
            <button
              onClick={toggleFlag}
              className={`rounded-lg border px-3 py-1.5 text-[13px] font-semibold ${
                flags.has(qid)
                  ? 'border-amber-300 bg-amber-50 text-amber-700'
                  : 'border-line text-ink-soft hover:border-amber-400 hover:text-amber-600'
              }`}
            >
              ⚑ İşaretle
            </button>
            {idx === questions.length - 1 ? (
              <button
                onClick={() => setConfirming(true)}
                className="rounded-lg bg-good px-4 py-1.5 text-[13px] font-bold text-white hover:bg-emerald-700"
              >
                ✓ Bitir
              </button>
            ) : (
              <button
                onClick={() => move(1)}
                className="rounded-lg bg-accent px-4 py-1.5 text-[13px] font-bold text-white hover:bg-indigo-700"
              >
                Sonraki →
              </button>
            )}
          </div>
        </div>
      </div>

      {/* bitirme onayı */}
      {confirming && (
        <div className="fixed inset-0 z-30 grid place-items-center bg-ink/40 p-4 backdrop-blur-sm">
          <div className="card w-full max-w-sm p-6">
            <h3 className="text-base font-bold">Testi bitiriyor musun?</h3>
            <p className="mt-2 text-[13px] text-ink-soft">
              {answeredCount} soru işaretli, {questions.length - answeredCount} boş.
              Sonuç ekranına geçeceksin.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setConfirming(false)}
                className="rounded-lg border border-line px-4 py-2 text-[13px] font-semibold text-ink-soft"
              >
                Vazgeç
              </button>
              <button onClick={finish} className="rounded-lg bg-good px-4 py-2 text-[13px] font-bold text-white">
                Bitir ve Sonucu Gör
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
