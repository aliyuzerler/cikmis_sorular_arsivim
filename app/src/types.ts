export interface Question {
  section: string
  section_name: string
  no: number
  img: string
  answer: string
}

export interface TestData {
  meta: Record<string, unknown>
  sections: { id: string; name: string }[]
  qa: Record<string, { name: string; questions_found: number; expected: number | null; ok: boolean }>
  questions: Question[]
}

export interface CatalogEntry {
  id: string
  exam: string
  examName: string
  source: 'osym' | 'meb'
  sourceName: string
  year: number
  session: string
  sessionName: string
  path: string
  total: number
  withAnswers: number
  sections: { id: string; name: string; count: number }[]
  qaOk: boolean
}

export interface Progress {
  answers: Record<string, string>   // qid -> harf
  flags: string[]
  elapsed: number                   // saniye
  finished: boolean
  questionIds: string[]             // bu koşuya dahil sorular
  updatedAt: number
}
