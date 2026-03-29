import { NavLink } from 'react-router-dom'
import { BarChart3, Briefcase, CreditCard, Crown, FileText, LayoutDashboard, Link2, PieChart, Settings, TrendingUp, Zap } from 'lucide-react'

import { cn } from '../../lib/cn'
import { useSubscription } from '../../hooks/useSubscription'

const baseNav = [
  { to: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/app/holdings', label: 'Holdings', icon: Briefcase },
  { to: '/app/mutual-funds', label: 'Mutual Funds', icon: PieChart },
  { to: '/app/transactions', label: 'Transactions', icon: CreditCard },
  { to: '/app/analysis', label: 'Analysis', icon: TrendingUp },
  { to: '/app/tax-reports', label: 'Tax Reports', icon: FileText },
  { to: '/app/brokers', label: 'Brokers', icon: Link2 },
  { to: '/app/settings', label: 'Settings', icon: Settings },
  { to: '/app/options-analyzer', label: 'Options Analyzer', icon: Zap },
  { to: '/app/options-billing', label: 'Options Plans', icon: Crown },
]

export function Sidebar() {
  const { isPro } = useSubscription()
  const nav = [...baseNav]

  return (
    <aside className="border-border bg-surface md:sticky md:top-0 md:h-screen md:border-r">
      <div className="flex items-center gap-3 border-b border-border px-6 py-7 bg-gradient-to-r from-indigo-950/10 via-purple-950/5 to-transparent dark:from-indigo-950/30 dark:via-purple-950/20 dark:to-zinc-900/30">
        <div className="relative flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 via-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/25 hover:shadow-xl hover:shadow-indigo-500/30 transition-all duration-300 hover:scale-110 group">
          <BarChart3 className="h-6 w-6 transition-transform group-hover:scale-110" />
          <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-lg font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-purple-300 to-indigo-500 bg-clip-text text-transparent">Quantleap</div>
          <div className="truncate text-xs text-muted font-medium">Portfolio Tracker</div>
        </div>
      </div>

      <nav className="space-y-2 px-4 py-6">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-all duration-200 group',
                isActive
                  ? 'bg-gradient-to-r from-indigo-600/50 via-purple-600/40 to-indigo-600/50 text-white shadow-lg shadow-indigo-500/20 border border-indigo-500/50'
                  : 'text-muted hover:text-text hover:bg-border/30 border border-transparent hover:border-border',
              )
            }
            end
          >
            <Icon className="h-4 w-4 flex-shrink-0 transition-transform group-hover:scale-110" />
            <span className="flex-1">{label}</span>
          </NavLink>
        ))}

        {/* Billing / Upgrade link */}
        <NavLink
          to="/app/billing"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-all duration-200 group',
              isActive
                ? 'bg-gradient-to-r from-indigo-600/50 via-purple-600/40 to-indigo-600/50 text-white shadow-lg shadow-indigo-500/20 border border-indigo-500/50'
                : isPro
                  ? 'text-muted hover:text-text hover:bg-border/30 border border-transparent hover:border-border'
                  : 'text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 border border-transparent hover:border-indigo-500/30',
            )
          }
          end
        >
          <Crown className="h-4 w-4 flex-shrink-0 transition-transform group-hover:scale-110" />
          <span className="flex-1">Billing</span>
          {!isPro && (
            <span className="rounded-full bg-indigo-500/20 px-2 py-0.5 text-[10px] font-bold text-indigo-300 border border-indigo-500/30">
              Upgrade
            </span>
          )}
          {isPro && (
            <span className="rounded-full bg-green-500/20 px-2 py-0.5 text-[10px] font-bold text-green-300 border border-green-500/30">
              Pro
            </span>
          )}
        </NavLink>
      </nav>
    </aside>
  )
}
