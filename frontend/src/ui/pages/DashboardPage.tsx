import { useQuery } from '@tanstack/react-query'
import { ArrowDownRight, ArrowUpRight, Briefcase, Coins, TrendingUp, Wallet } from 'lucide-react'

import { api } from '../../lib/api'
import { formatCurrencyINR, formatPercent } from '../../lib/format'
import { type DashboardStats } from '../../types/domain'
import { Card } from '../components/Card'
import { KpiCard } from '../components/KpiCard'

async function fetchStats() {
  const { data } = await api.get<DashboardStats>('/dashboard/stats')
  return {
    ...data,
    total_portfolio_value: Number(data.total_portfolio_value) || 0,
    total_invested: Number(data.total_invested) || 0,
    total_gain_loss: Number(data.total_gain_loss) || 0,
    gain_loss_percentage: Number(data.gain_loss_percentage) || 0,
    number_of_portfolios: Number(data.number_of_portfolios) || 0,
    number_of_assets: Number(data.number_of_assets) || 0,
  }
}

export function DashboardPage() {
  const query = useQuery({ queryKey: ['dashboard', 'stats'], queryFn: fetchStats })

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, idx) => (
            <div key={idx} className="h-[110px] animate-pulse rounded-xl border border-border bg-surface" />
          ))}
        </div>
        <div className="h-[220px] animate-pulse rounded-xl border border-border bg-surface" />
      </div>
    )
  }

  if (query.isError || !query.data) {
    return (
      <Card>
        <div className="text-sm text-danger">Failed to load dashboard.</div>
      </Card>
    )
  }

  const stats = query.data
  const isUp = stats.total_gain_loss >= 0

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-sm text-muted">Overview</div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        </div>
        <div className="text-xs text-muted">MVP UI</div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <KpiCard label="Total Value" value={formatCurrencyINR(stats.total_portfolio_value)} icon={<Wallet className="h-4 w-4" />} />
        <KpiCard label="Invested" value={formatCurrencyINR(stats.total_invested)} icon={<Coins className="h-4 w-4" />} />
        <KpiCard
          label="Total P&L"
          value={formatCurrencyINR(stats.total_gain_loss)}
          helper={formatPercent(stats.gain_loss_percentage)}
          tone={isUp ? 'success' : 'danger'}
          icon={
            isUp ? (
              <ArrowUpRight className="h-4 w-4 text-success" />
            ) : (
              <ArrowDownRight className="h-4 w-4 text-danger" />
            )
          }
        />
        <KpiCard label="Portfolios" value={String(stats.number_of_portfolios)} icon={<Briefcase className="h-4 w-4" />} />
        <KpiCard label="Assets" value={String(stats.number_of_assets)} icon={<TrendingUp className="h-4 w-4" />} />
      </div>

      <Card>
        <div className="text-sm font-semibold">Next steps</div>
        <div className="mt-1 text-sm text-muted">
          Implement time-series charts, allocation breakdowns, and broker syncing inside the SPA.
        </div>
      </Card>
    </div>
  )
}
