import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { TrendingUp } from 'lucide-react'
import { formatCurrencyINR } from '../../lib/format'
import { Card } from './Card'

type GrowthDataPoint = {
    year: number
    month: number
    value: number
    nifty_value: number
    label: string
}

type PortfolioGrowthChartProps = {
    data: GrowthDataPoint[]
    isLoading?: boolean
}

export function PortfolioGrowthChart({ data, isLoading }: PortfolioGrowthChartProps) {
    if (isLoading) {
        return (
            <Card>
                <div className="h-[400px] animate-pulse rounded-lg bg-surface-light" />
            </Card>
        )
    }

    if (!data || data.length === 0) {
        return (
            <Card>
                <div className="flex items-center justify-center h-[400px] text-sm text-muted">
                    No growth data available
                </div>
            </Card>
        )
    }

    const formatValue = (value: number) => {
        if (value >= 100000) {
            return `₹${(value / 100000).toFixed(1)}L`
        } else if (value >= 1000) {
            return `₹${(value / 1000).toFixed(1)}K`
        }
        return `₹${value.toFixed(0)}`
    }

    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-surface/95 backdrop-blur-xl border border-border rounded-lg p-3 shadow-2xl">
                    <p className="text-xs font-semibold text-muted mb-2">{payload[0].payload.label}</p>
                    <div className="space-y-1">
                        <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
                                <span className="text-xs text-muted">Portfolio</span>
                            </div>
                            <span className="text-sm font-black text-text">
                                {formatCurrencyINR(payload[0].value)}
                            </span>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                                <span className="text-xs text-muted">Nifty 50</span>
                            </div>
                            <span className="text-sm font-black text-amber-600 dark:text-amber-400">
                                {formatCurrencyINR(payload[1]?.value || 0)}
                            </span>
                        </div>
                    </div>
                </div>
            )
        }
        return null
    }

    return (
        <Card variant="gradient" className="relative overflow-hidden">
            <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl -z-10" />

            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/30 to-purple-500/30 text-indigo-300 shadow-lg">
                        <TrendingUp className="h-6 w-6" />
                    </div>
                    <div>
                        <h3 className="text-lg font-black text-white">Portfolio Growth</h3>
                        <p className="text-xs text-muted">12-month value trend vs Nifty 50</p>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-indigo-500"></div>
                        <span className="text-xs font-semibold text-text">Portfolio</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                        <span className="text-xs font-semibold text-text">Nifty 50</span>
                    </div>
                </div>
            </div>

            <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                        data={data}
                        margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                    >
                        <defs>
                            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorNifty" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid
                            strokeDasharray="3 3"
                            className="stroke-border"
                            vertical={false}
                        />
                        <XAxis
                            dataKey="label"
                            className="stroke-muted"
                            tick={{ fill: 'currentColor', fontSize: 11, className: 'fill-muted' }}
                            tickLine={{ className: 'stroke-border' }}
                        />
                        <YAxis
                            className="stroke-muted"
                            tick={{ fill: 'currentColor', fontSize: 11, className: 'fill-muted' }}
                            tickLine={{ className: 'stroke-border' }}
                            tickFormatter={formatValue}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Area
                            type="monotone"
                            dataKey="value"
                            stroke="#6366f1"
                            strokeWidth={3}
                            fill="url(#colorValue)"
                            dot={{
                                fill: '#6366f1',
                                strokeWidth: 2,
                                r: 4,
                                stroke: '#18181b'
                            }}
                            activeDot={{
                                r: 6,
                                fill: '#6366f1',
                                stroke: '#18181b',
                                strokeWidth: 2
                            }}
                        />
                        <Area
                            type="monotone"
                            dataKey="nifty_value"
                            stroke="#f59e0b"
                            strokeWidth={2}
                            strokeDasharray="5 5"
                            fill="url(#colorNifty)"
                            dot={{
                                fill: '#f59e0b',
                                strokeWidth: 2,
                                r: 3,
                                stroke: '#18181b'
                            }}
                            activeDot={{
                                r: 5,
                                fill: '#f59e0b',
                                stroke: '#18181b',
                                strokeWidth: 2
                            }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </Card>
    )
}
