import { useEffect, useState } from 'react'
import type { CatalogEntry, TestData } from './types'
import { loadTheme } from './lib/storage'
import Landing from './components/Landing'
import Home from './components/Home'
import Runner from './components/Runner'
import Results from './components/Results'

export type View =
  | { name: 'home' }
  | { name: 'run'; entry: CatalogEntry; test: TestData; sectionFilter: string }
  | { name: 'result'; entry: CatalogEntry; test: TestData; sectionFilter: string }

const SEEN_KEY = 'arsov:visited'

export default function App() {
  const [catalog, setCatalog] = useState<CatalogEntry[] | null>(null)
  const [error, setError] = useState('')
  const [view, setView] = useState<View>({ name: 'home' })
  const [landing, setLanding] = useState(() => !localStorage.getItem(SEEN_KEY))
  // tema artık tek (aydınlık); bayrak geriye dönük uyumluluk için okunur
  useEffect(() => { loadTheme() }, [])

  useEffect(() => {
    fetch('/data/index.json')
      .then((r) => {
        if (!r.ok) throw new Error(`katalog yüklenemedi (${r.status})`)
        return r.json() as Promise<CatalogEntry[]>
      })
      .then(setCatalog)
      .catch((e) => setError(String(e.message ?? e)))
  }, [])

  const openTest = async (entry: CatalogEntry, sectionFilter: string, fresh: boolean) => {
    const test: TestData = await fetch(`${entry.path}/questions.json`).then((r) => r.json())
    if (fresh && sectionFilter) {
      test.questions = test.questions.filter((q) => q.section === sectionFilter)
    }
    setView({ name: 'run', entry, test, sectionFilter })
  }

  const enterApp = () => {
    localStorage.setItem(SEEN_KEY, '1')
    setLanding(false)
  }

  if (landing) return <Landing onEnter={enterApp} ready={catalog !== null} />

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
          <button onClick={() => setView({ name: 'home' })} className="flex items-center gap-2.5 text-left">
            <span className="grid size-9 place-items-center rounded-xl bg-accent text-base font-bold text-white">ÖA</span>
            <span>
              <span className="block text-[15px] font-bold leading-tight tracking-tight">Soru Arşivim</span>
              <span className="block text-[11px] text-ink-faint">ÖSYM & MEB Çıkmış Sorular</span>
            </span>
          </button>
          <nav className="text-sm text-ink-soft">
            <button onClick={() => setView({ name: 'home' })} className="rounded-lg px-3 py-1.5 hover:bg-accent-soft hover:text-accent">
              Arşiv
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">
        {error && (
          <div className="card border-red-200 bg-red-50 p-5 text-sm text-red-700">
            {error}
            <div className="mt-1 text-xs opacity-70">
              Kataloğu üretmek için <code>python pipeline/build_catalog.py</code> çalıştırın.
            </div>
          </div>
        )}
        {view.name === 'home' && catalog && <Home catalog={catalog} onOpen={openTest} />}
        {view.name === 'run' && (
          <Runner
            entry={view.entry}
            test={view.test}
            sectionFilter={view.sectionFilter}
            onExit={() => setView({ name: 'home' })}
            onFinish={() => setView({ ...view, name: 'result' })}
          />
        )}
        {view.name === 'result' && (
          <Results
            entry={view.entry}
            test={view.test}
            sectionFilter={view.sectionFilter}
            onHome={() => setView({ name: 'home' })}
            onRetry={(section) => openTest(view.entry, section, true)}
          />
        )}
      </main>

      <footer className="mx-auto max-w-6xl px-5 pb-10 pt-2 text-center text-[11px] text-ink-faint">
        Sorular ÖSYM / MEB telifidir — bu arşiv yalnızca kişisel çalışma amaçlıdır.
      </footer>
    </div>
  )
}
