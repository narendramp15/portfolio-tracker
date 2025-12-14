import { NavLink } from 'react-router-dom'
import { BarChart3, Briefcase, CreditCard, LayoutDashboard, Link2, Settings } from 'lucide-react'

import { cn } from '../../lib/cn'

const nav = [
  { to: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/app/holdings', label: 'Holdings', icon: Briefcase },
  { to: '/app/transactions', label: 'Transactions', icon: CreditCard },
  { to: '/app/brokers', label: 'Brokers', icon: Link2 },
  { to: '/app/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="border-border bg-surface md:sticky md:top-0 md:h-screen md:border-r">
      <div className="flex items-center gap-3 px-4 py-4 sm:px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-fg shadow-soft">
          <BarChart3 className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold tracking-tight">Portfolio Tracker</div>
          <div className="truncate text-xs text-muted">Investments at a glance</div>
        </div>
      </div>

      <nav className="px-2 pb-4 sm:px-4">
        <div className="space-y-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-muted transition hover:bg-bg hover:text-text',
                  isActive && 'bg-bg text-text shadow-soft',
                )
              }
              end
            >
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </NavLink>
          ))}

        </div>
      </nav>
    </aside>
  )
}
