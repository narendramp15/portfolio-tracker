import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { LogOut, Moon, Search, Sun } from 'lucide-react'

import { api } from '../../lib/api'
import { useAuth } from '../../providers/auth/AuthProvider'
import { useTheme } from '../../providers/theme/ThemeProvider'
import { useAppStore } from '../../store/appStore'
import { type Portfolio } from '../../types/domain'

export function TopBar() {
  const { user, logout } = useAuth()
  const { mode, toggle } = useTheme()
  const navigate = useNavigate()
  const { selectedPortfolioId, setSelectedPortfolioId } = useAppStore()

  const portfoliosQuery = useQuery({
    queryKey: ['portfolios'],
    queryFn: async () => {
      const { data } = await api.get<Portfolio[]>('/portfolio/')
      return data
    },
  })

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface/80 backdrop-blur-xl shadow-lg">
      <div className="flex items-center justify-between gap-4 px-6 py-4">
        <div className="relative hidden w-full max-w-md sm:block">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            className="w-full rounded-xl border border-border bg-bg px-10 py-2.5 text-sm text-text placeholder-muted outline-none transition-all focus:border-indigo-500/50 focus:bg-surface focus:ring-2 focus:ring-indigo-500/20"
            placeholder="Search symbols, portfolios..."
            type="search"
          />
        </div>

        <div className="flex items-center gap-3">
          <select
            className="hidden rounded-xl border border-border bg-bg px-4 py-2.5 text-sm font-medium text-text transition-all hover:border-indigo-500/50 focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/20 sm:block"
            value={selectedPortfolioId ?? ''}
            onChange={(e) => setSelectedPortfolioId(e.target.value ? Number(e.target.value) : null)}
            title="Selected portfolio (used for broker sync)"
            disabled={portfoliosQuery.isLoading || portfoliosQuery.isError}
          >
            <option value="">All portfolios</option>
            {(portfoliosQuery.data ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={toggle}
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-bg px-3 py-2 text-sm font-medium hover:bg-surface"
            aria-label="Toggle theme"
          >
            {mode === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            <span className="hidden sm:inline">{mode === 'dark' ? 'Light' : 'Dark'}</span>
          </button>

          <div className="hidden items-center gap-2 rounded-xl border border-border bg-bg px-3 py-2 sm:flex">
            <div className="min-w-0">
              <div className="max-w-[180px] truncate text-sm font-semibold">{user?.username ?? 'User'}</div>
              <div className="max-w-[180px] truncate text-xs text-muted">{user?.email ?? ''}</div>
            </div>
          </div>

          <button
            type="button"
            onClick={() => {
              logout()
              navigate('/login', { replace: true })
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-bg px-3 py-2 text-sm font-medium text-danger hover:bg-surface"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  )
}
