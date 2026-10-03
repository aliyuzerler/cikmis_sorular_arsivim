import type { Progress } from '../types'

const PREFIX = 'arsov:'

export function loadProgress(testId: string): Progress | null {
  try {
    const raw = localStorage.getItem(PREFIX + testId)
    return raw ? (JSON.parse(raw) as Progress) : null
  } catch {
    return null
  }
}

export function saveProgress(testId: string, p: Progress) {
  localStorage.setItem(PREFIX + testId, JSON.stringify({ ...p, updatedAt: Date.now() }))
}

export function clearProgress(testId: string) {
  localStorage.removeItem(PREFIX + testId)
}

export function loadTheme(): 'light' | 'dark' {
  const saved = localStorage.getItem(PREFIX + 'theme')
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function saveTheme(t: 'light' | 'dark') {
  localStorage.setItem(PREFIX + 'theme', t)
}
