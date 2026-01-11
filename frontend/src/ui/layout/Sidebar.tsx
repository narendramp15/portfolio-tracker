import { NavLink } from 'react-router-dom'
import { BarChart3, Briefcase, CreditCard, LayoutDashboard, Link2, Settings, TrendingUp } from 'lucide-react'

import { cn } from '../../lib/cn'

const nav = [
  { to: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/app/holdings', label: 'Holdings', icon: Briefcase },
  { to: '/app/transactions', label: 'Transactions', icon: CreditCard },
  { to: '/app/analysis', label: 'Analysis', icon: TrendingUp },
  { to: '/app/brokers', label: 'Brokers', icon: Link2 },
  { to: '/app/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="border-zinc-800/50 bg-gradient-to-b from-zinc-900/95 via-slate-900/90 to-zinc-900/95 md:sticky md:top-0 md:h-screen md:border-r backdrop-blur-xl">
      <div className="flex items-center gap-3 border-b border-zinc-800/50 px-6 py-7 bg-gradient-to-r from-indigo-950/30 via-purple-950/20 to-zinc-900/30">
        <div className="relative flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 via-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/25 hover:shadow-xl hover:shadow-indigo-500/30 transition-all duration-300 hover:scale-110 group">
          <BarChart3 className="h-6 w-6 transition-transform group-hover:scale-110" />
          <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-lg font-extrabold tracking-tight bg-gradient-to-r from-indigo-200 via-purple-200 to-indigo-300 bg-clip-text text-transparent">Quatleap</div>
          <div className="truncate text-xs text-zinc-400 font-medium">Portfolio Tracker</div>
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
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50 border border-transparent hover:border-zinc-700/50',
              )
            }
            end
          >
            <Icon className="h-4 w-4 flex-shrink-0 transition-transform group-hover:scale-110" />
            <span className="flex-1">{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
