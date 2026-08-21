import { Activity } from 'lucide-react'
import { Card } from './Card'

export type PortfolioReturns = {
    /** Money-weighted annualised return. Null when the cash flows cannot yield one. */
    xirr: number | null
    /** Time-weighted return over the window, contribution-timing neutral. */
    twr: number | null
    twr_annualised: number | null
    /** Nifty 50 return over the same window. */
    benchmark_return: number | null
    /** TWR less the benchmark. */
    alpha: number | null
    max_drawdown: number | null
    volatility: number | null
    current_value: number
    data_points: number
}

type ReturnsPanelProps = {
    data?: PortfolioReturns
    isLoading?: boolean
}

function formatPercent(value: number | null): string {
    if (value == null || !Number.isFinite(value)) return '—'
    const pct = value * 100
    return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`
}

function toneFor(value: number | null): string {
    if (value == null || !Number.isFinite(value)) return 'text-muted'
    if (value > 0) return 'text-emerald-600 dark:text-emerald-400'
    if (value < 0) return 'text-rose-600 dark:text-rose-400'
    return 'text-text'
}

type MetricProps = {
    label: string
    value: string
    tone?: string
    hint: string
}

function Metric({ label, value, tone = 'text-text', hint }: MetricProps) {
    return (
        <div className="flex flex-col gap-1">
            <div className="text-xs font-bold uppercase tracking-widest text-muted">{label}</div>
            <div className={`text-2xl font-black tabular-nums ${tone}`}>{value}</div>
            <div className="text-xs text-muted leading-snug">{hint}</div>
        </div>
    )
}

export function ReturnsPanel({ data, isLoading }: ReturnsPanelProps) {
    if (isLoading) {
        return (
            <Card>
                <div className="h-[180px] animate-pulse rounded-lg bg-surface-light" />
            </Card>
        )
    }

    // Nothing computable yet - say why rather than showing a row of dashes.
    if (!data || (data.xirr == null && data.twr == null)) {
        return (
            <Card>
                <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/15 text-indigo-500 flex-shrink-0">
                        <Activity className="h-5 w-5" />
                    </div>
                    <div>
                        <div className="text-sm font-black text-text">Returns</div>
                        <p className="mt-1 text-xs text-muted max-w-md leading-relaxed">
                            XIRR and time-weighted return need at least a month of
                            recorded transactions. Add or sync your trade history and
                            these will fill in.
                        </p>
                    </div>
                </div>
            </Card>
        )
    }

    return (
        <Card>
            <div className="flex items-center gap-3 mb-5">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/15 text-indigo-500">
                    <Activity className="h-5 w-5" />
                </div>
                <div>
                    <h3 className="text-sm font-black text-text">Returns</h3>
                    <p className="text-xs text-muted">Computed from your transaction history</p>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-x-6 gap-y-5 lg:grid-cols-4">
                <Metric
                    label="XIRR"
                    value={formatPercent(data.xirr)}
                    tone={toneFor(data.xirr)}
                    hint="Annualised, weighted by when you invested"
                />
                <Metric
                    label="Time-weighted"
                    value={formatPercent(data.twr)}
                    tone={toneFor(data.twr)}
                    hint="Ignores contribution timing — comparable to an index"
                />
                <Metric
                    label="Nifty 50"
                    value={formatPercent(data.benchmark_return)}
                    tone={toneFor(data.benchmark_return)}
                    hint="Same period, for comparison"
                />
                <Metric
                    label="Alpha"
                    value={formatPercent(data.alpha)}
                    tone={toneFor(data.alpha)}
                    hint="Time-weighted return less the index"
                />
                <Metric
                    label="Max drawdown"
                    value={formatPercent(data.max_drawdown)}
                    tone={data.max_drawdown ? 'text-rose-600 dark:text-rose-400' : 'text-muted'}
                    hint="Largest fall from a peak in this window"
                />
                <Metric
                    label="Volatility"
                    value={formatPercent(data.volatility)}
                    hint="Annualised standard deviation of monthly returns"
                />
            </div>

            <p className="mt-5 border-t border-border pt-3 text-xs text-muted">
                XIRR answers how your money did; time-weighted return answers how the
                holdings did. Only the latter is a fair comparison against Nifty 50.
            </p>
        </Card>
    )
}
