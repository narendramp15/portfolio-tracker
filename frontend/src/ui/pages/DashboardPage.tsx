import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { Award, BarChart3, ArrowDownRight, ArrowUpRight, Briefcase, Coins, TrendingUp, TrendingDown, Wallet, Target, Activity, PieChart, Palette } from 'lucide-react'

import { api } from '../../lib/api'
import { formatCurrencyINR, formatPercent } from '../../lib/format'
import { type DashboardStats } from '../../types/domain'
import { Card } from '../components/Card'
import { KpiCard } from '../components/KpiCard'
import { PortfolioGrowthChart } from '../components/PortfolioGrowthChart'

type DashboardTheme = 'indigo-purple' | 'blue-gray' | 'cyan-emerald' | 'orange-amber' | 'deep-blue'

const themeConfig = {
  'indigo-purple': {
    name: 'Indigo Purple',
    welcomeText: 'text-indigo-400/70 dark:text-indigo-400/70',
    welcomeBar: 'from-indigo-500 dark:from-indigo-500',
    headerGradient: 'from-indigo-400 via-purple-300 to-indigo-500 dark:from-indigo-400 dark:via-purple-300 dark:to-indigo-500',
    accentIcon: 'bg-indigo-500/20 text-indigo-400 dark:bg-indigo-500/20 dark:text-indigo-400',
    accentIcon2: 'bg-purple-500/20 text-purple-400 dark:bg-purple-500/20 dark:text-purple-400',
    nextStepsGradient: 'from-indigo-500/30 to-purple-500/30 dark:from-indigo-500/30 dark:to-purple-500/30',
    nextStepsIcon: 'text-indigo-300 dark:text-indigo-300',
    nextStepsBlur: 'bg-indigo-500/10 dark:bg-indigo-500/10',
  },
  'blue-gray': {
    name: 'Professional Blue-Gray',
    welcomeText: 'text-slate-600/70 dark:text-slate-400/70',
    welcomeBar: 'from-slate-500 dark:from-slate-500',
    headerGradient: 'from-slate-700 via-slate-600 to-blue-600 dark:from-slate-400 dark:via-slate-300 dark:to-blue-400',
    accentIcon: 'bg-slate-500/20 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400',
    accentIcon2: 'bg-blue-500/20 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400',
    nextStepsGradient: 'from-slate-500/30 to-blue-500/30 dark:from-slate-500/30 dark:to-blue-500/30',
    nextStepsIcon: 'text-slate-600 dark:text-slate-300',
    nextStepsBlur: 'bg-slate-500/10 dark:bg-slate-500/10',
  },
  'cyan-emerald': {
    name: 'Fresh Cyan-Emerald',
    welcomeText: 'text-cyan-600/70 dark:text-cyan-400/70',
    welcomeBar: 'from-cyan-500 dark:from-cyan-500',
    headerGradient: 'from-cyan-600 via-teal-500 to-emerald-600 dark:from-cyan-400 dark:via-teal-300 dark:to-emerald-400',
    accentIcon: 'bg-cyan-500/20 text-cyan-600 dark:bg-cyan-500/20 dark:text-cyan-400',
    accentIcon2: 'bg-teal-500/20 text-teal-600 dark:bg-teal-500/20 dark:text-teal-400',
    nextStepsGradient: 'from-cyan-500/30 to-emerald-500/30 dark:from-cyan-500/30 dark:to-emerald-500/30',
    nextStepsIcon: 'text-cyan-600 dark:text-cyan-300',
    nextStepsBlur: 'bg-cyan-500/10 dark:bg-cyan-500/10',
  },
  'orange-amber': {
    name: 'Warm Orange-Amber',
    welcomeText: 'text-orange-600/70 dark:text-orange-400/70',
    welcomeBar: 'from-orange-500 dark:from-orange-500',
    headerGradient: 'from-orange-600 via-amber-500 to-yellow-600 dark:from-orange-400 dark:via-amber-300 dark:to-yellow-400',
    accentIcon: 'bg-orange-500/20 text-orange-600 dark:bg-orange-500/20 dark:text-orange-400',
    accentIcon2: 'bg-amber-500/20 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400',
    nextStepsGradient: 'from-orange-500/30 to-amber-500/30 dark:from-orange-500/30 dark:to-amber-500/30',
    nextStepsIcon: 'text-orange-600 dark:text-orange-300',
    nextStepsBlur: 'bg-orange-500/10 dark:bg-orange-500/10',
  },
  'deep-blue': {
    name: 'Deep Blue',
    welcomeText: 'text-blue-600/70 dark:text-blue-400/70',
    welcomeBar: 'from-blue-600 dark:from-blue-500',
    headerGradient: 'from-blue-700 via-blue-600 to-sky-600 dark:from-blue-400 dark:via-blue-300 dark:to-sky-400',
    accentIcon: 'bg-blue-500/20 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400',
    accentIcon2: 'bg-sky-500/20 text-sky-600 dark:bg-sky-500/20 dark:text-sky-400',
    nextStepsGradient: 'from-blue-500/30 to-sky-500/30 dark:from-blue-500/30 dark:to-sky-500/30',
    nextStepsIcon: 'text-blue-600 dark:text-blue-300',
    nextStepsBlur: 'bg-blue-500/10 dark:bg-blue-500/10',
  },
}

type GrowthDataPoint = {
  year: number
  month: number
  value: number
  nifty_value: number
  label: string
}

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
    average_return: data.average_return != null ? Number(data.average_return) : null,
    diversification_score: Number(data.diversification_score) || 0,
    winning_assets: Number(data.winning_assets) || 0,
    losing_assets: Number(data.losing_assets) || 0,
    best_performer: data.best_performer,
    worst_performer: data.worst_performer,
  }
}

async function fetchGrowthData() {
  const { data } = await api.get<GrowthDataPoint[]>('/dashboard/growth')
  return data
}

export function DashboardPage() {
  const [theme, setTheme] = useState<DashboardTheme>(() => {
    const saved = localStorage.getItem('dashboardTheme')
    return (saved as DashboardTheme) || 'indigo-purple'
  })

  useEffect(() => {
    localStorage.setItem('dashboardTheme', theme)
  }, [theme])

  const colors = themeConfig[theme]

  const query = useQuery({ queryKey: ['dashboard', 'stats'], queryFn: fetchStats })
  const growthQuery = useQuery({ queryKey: ['dashboard', 'growth'], queryFn: fetchGrowthData })

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
  const winRate = stats.number_of_assets > 0 ? (stats.winning_assets / stats.number_of_assets) * 100 : 0

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className={`text-xs font-bold uppercase tracking-widest ${colors.welcomeText} flex items-center gap-2`}>
            <span className={`inline-block w-8 h-0.5 bg-gradient-to-r ${colors.welcomeBar} to-transparent rounded-full`}></span>
            Welcome back
          </div>
          <h1 className={`mt-3 text-5xl font-black tracking-tight bg-gradient-to-r ${colors.headerGradient} bg-clip-text text-transparent`}>Portfolio Overview</h1>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Palette className="h-4 w-4 text-muted" />
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value as DashboardTheme)}
            className="px-3 py-2 text-xs font-semibold rounded-lg border border-border bg-surface text-text hover:bg-border/30 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          >
            {Object.entries(themeConfig).map(([key, config]) => (
              <option key={key} value={key}>
                {config.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Primary KPIs */}
      <div>
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted mb-4 flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Portfolio Performance
        </h2>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Total Value" value={formatCurrencyINR(stats.total_portfolio_value)} icon={<Wallet className="h-5 w-5" />} />
          <KpiCard label="Total Invested" value={formatCurrencyINR(stats.total_invested)} icon={<Coins className="h-5 w-5" />} />
          <KpiCard
            label="Total Return"
            value={formatCurrencyINR(stats.total_gain_loss)}
            helper={formatPercent(stats.gain_loss_percentage)}
            tone={isUp ? 'success' : 'danger'}
            icon={
              isUp ? (
                <ArrowUpRight className="h-5 w-5 text-success" />
              ) : (
                <ArrowDownRight className="h-5 w-5 text-danger" />
              )
            }
          />
          {stats.average_return != null && (
            <KpiCard
              label="Avg. Return"
              value={formatPercent(stats.average_return)}
              tone={stats.average_return >= 0 ? 'success' : 'danger'}
              icon={<Target className="h-5 w-5" />}
            />
          )}
        </div>
      </div>

      {/* Performance Insights */}
      <div>
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4" />
          Performance Insights
        </h2>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {stats.best_performer && (
            <Card variant="gradient" className="border-emerald-500/30">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400 flex-shrink-0">
                  <Award className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-bold uppercase tracking-widest text-muted">Best Performer</div>
                  <div className="mt-1 text-lg font-black text-text truncate">{stats.best_performer.symbol}</div>
                  <div className="text-sm font-bold text-emerald-400">{formatPercent(stats.best_performer.return_pct)}</div>
                </div>
              </div>
            </Card>
          )}

          {stats.worst_performer && (
            <Card variant="gradient" className="border-rose-500/30">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-rose-500/20 text-rose-400 flex-shrink-0">
                  <TrendingDown className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-bold uppercase tracking-widest text-muted">Worst Performer</div>
                  <div className="mt-1 text-lg font-black text-text truncate">{stats.worst_performer.symbol}</div>
                  <div className="text-sm font-bold text-rose-400">{formatPercent(stats.worst_performer.return_pct)}</div>
                </div>
              </div>
            </Card>
          )}

          <Card>
            <div className="flex items-start gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${colors.accentIcon} flex-shrink-0`}>
                <PieChart className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <div className="text-xs font-bold uppercase tracking-widest text-muted">Win Rate</div>
                <div className="mt-1 text-2xl font-black text-text">{winRate.toFixed(1)}%</div>
                <div className="text-xs text-muted mt-1">
                  {stats.winning_assets} wins / {stats.losing_assets} losses
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-start gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${colors.accentIcon2} flex-shrink-0`}>
                <Briefcase className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <div className="text-xs font-bold uppercase tracking-widest text-muted">Diversification</div>
                <div className="mt-1 text-2xl font-black text-text">{stats.diversification_score}</div>
                <div className="text-xs text-muted mt-1">
                  Unique assets across {stats.number_of_portfolios} portfolio{stats.number_of_portfolios !== 1 ? 's' : ''}
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Growth Chart */}
      <PortfolioGrowthChart data={growthQuery.data || []} isLoading={growthQuery.isLoading} />

      <Card variant="gradient" className="relative overflow-hidden">
        <div className={`absolute top-0 right-0 w-64 h-64 ${colors.nextStepsBlur} rounded-full blur-3xl -z-10`} />
        <div className="flex items-start gap-5">
          <div className={`flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br ${colors.nextStepsGradient} ${colors.nextStepsIcon} flex-shrink-0 shadow-lg`}>
            <TrendingUp className="h-7 w-7" />
          </div>
          <div className="flex-1">
            <div className="text-lg font-black text-text mb-1">Next Steps</div>
            <div className="text-sm text-muted leading-relaxed">
              Connect your broker accounts to start syncing holdings and tracking performance across multiple exchanges.
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}
