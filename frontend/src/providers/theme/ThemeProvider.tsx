import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { type PropsWithChildren } from 'react'

export type ThemeMode = 'light' | 'dark'

type ThemeContextValue = {
  mode: ThemeMode
  setMode: (mode: ThemeMode) => void
  toggle: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function applyThemeToDocument(mode: ThemeMode) {
  document.body.dataset.theme = mode
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const [mode, setModeState] = useState<ThemeMode>('light')

  useEffect(() => {
    const saved = localStorage.getItem('theme_mode')
    if (saved === 'dark' || saved === 'light') {
      setModeState(saved)
      applyThemeToDocument(saved)
      return
    }
    const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)')?.matches ?? false
    const initial: ThemeMode = prefersDark ? 'dark' : 'light'
    setModeState(initial)
    applyThemeToDocument(initial)
  }, [])

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next)
    localStorage.setItem('theme_mode', next)
    applyThemeToDocument(next)
  }, [])

  const toggle = useCallback(() => {
    setMode(mode === 'dark' ? 'light' : 'dark')
  }, [mode, setMode])

  const value = useMemo(() => ({ mode, setMode, toggle }), [mode, setMode, toggle])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

