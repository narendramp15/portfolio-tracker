import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, ChevronDown, ChevronRight, RefreshCw, Sparkles } from 'lucide-react'

import { api } from '../../lib/api'

// ── Helpers ────────────────────────────────────────────────────────────────

const fmtDuration = (sec: number): string => {
    if (sec <= 0) return 'now'
    const h = Math.floor(sec / 3600)
    const m = Math.floor((sec % 3600) / 60)
    if (h >= 23) return 'tomorrow'
    if (h > 0) return `${h}h ${m}m`
    return `${m}m`
}

// ── Types ──────────────────────────────────────────────────────────────────

interface Signal {
    label: string
    ok: boolean
    detail: string
}

interface BeginnerStock {
    symbol: string
    name: string
    sector: string
    current_price: number
    overall: string
    overall_emoji: string
    safety_score: number
    signals: Signal[]
    one_liner: string
    pe: number | null
    roe: number | null
    debt_to_equity: number | null
}

interface BeginnerScreenerResponse {
    stocks: BeginnerStock[]
    scanned_count: number
    successful_count: number
    scan_timestamp: string
    cached: boolean
    cache_age_seconds: number
    next_refresh_seconds: number
}

// ── Helpers ────────────────────────────────────────────────────────────────

function overallStyle(overall: string) {
    if (overall === 'Safe Pick') return { pill: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40', bar: '#10b981', ring: 'border-emerald-500/30' }
    if (overall === 'Watchlist') return { pill: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40', bar: '#f59e0b', ring: 'border-yellow-500/30' }
    return { pill: 'bg-red-500/15 text-red-300 border-red-500/40', bar: '#ef4444', ring: 'border-red-500/20' }
}

// ── Single stock card ──────────────────────────────────────────────────────

function StockCard({ stock }: { stock: BeginnerStock }) {
    const [open, setOpen] = useState(false)
    const style = overallStyle(stock.overall)

    return (
        <div className={`rounded-2xl border bg-surface shadow-sm transition-all duration-200 hover:shadow-md ${style.ring}`}>
            {/* Header */}
            <div className="p-4">
                <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-2xl leading-none">{stock.overall_emoji}</span>
                            <span className="font-bold text-text truncate">{stock.name}</span>
                            <span className="font-mono text-[10px] text-muted bg-border/30 rounded px-1.5 py-0.5 flex-shrink-0">
                                {stock.symbol.replace('.NS', '')}
                            </span>
                        </div>
                        <p className="mt-1.5 text-xs text-muted leading-relaxed">{stock.one_liner}</p>
                    </div>
                    <div className="text-right flex-shrink-0">
                        <div className="text-lg font-extrabold text-text">
                            ₹{stock.current_price.toLocaleString('en-IN')}
                        </div>
                        <div className="text-[10px] text-muted">{stock.sector}</div>
                    </div>
                </div>

                {/* Overall pill + safety bar */}
                <div className="mt-3 flex items-center gap-3">
                    <span className={`inline-block rounded-full border px-3 py-0.5 text-xs font-bold ${style.pill}`}>
                        {stock.overall}
                    </span>
                    <div className="flex-1 h-1.5 rounded-full bg-border/50 overflow-hidden">
                        <div
                            className="h-1.5 rounded-full transition-all duration-700"
                            style={{ width: `${stock.safety_score}%`, background: style.bar }}
                        />
                    </div>
                    <span className="text-xs font-bold text-muted w-8 text-right">{stock.safety_score}</span>
                </div>
            </div>

            {/* Signals strip */}
            <div className="border-t border-border/30 px-4 py-2 flex flex-wrap gap-1.5">
                {stock.signals.map(s => (
                    <span
                        key={s.label}
                        title={s.detail}
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold border cursor-default ${s.ok
                            ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                            : 'bg-red-500/10 text-red-300 border-red-500/30'
                            }`}
                    >
                        {s.ok ? '✓' : '✗'} {s.label}
                    </span>
                ))}
            </div>

            {/* Expand for details */}
            <button
                onClick={() => setOpen(v => !v)}
                className="flex w-full items-center justify-between border-t border-border/30 px-4 py-2 text-xs font-semibold text-muted hover:text-text hover:bg-border/10 transition-colors rounded-b-2xl"
            >
                <span>What do these signals mean?</span>
                {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            </button>

            {open && (
                <div className="border-t border-border/20 px-4 py-3 space-y-2 bg-border/5 rounded-b-2xl">
                    {stock.signals.map(s => (
                        <div key={s.label} className="flex items-start gap-2.5">
                            <span className={`mt-0.5 flex-shrink-0 text-sm ${s.ok ? 'text-emerald-400' : 'text-red-400'}`}>
                                {s.ok ? '✓' : '✗'}
                            </span>
                            <div>
                                <span className="text-xs font-bold text-text">{s.label}: </span>
                                <span className="text-xs text-muted">{s.detail}</span>
                            </div>
                        </div>
                    ))}
                    {/* Quick numbers */}
                    <div className="mt-2 flex gap-4 pt-2 border-t border-border/20">
                        {stock.pe != null && (
                            <div className="text-center">
                                <div className="text-xs font-bold text-text">{stock.pe.toFixed(1)}×</div>
                                <div className="text-[10px] text-muted">P/E Ratio</div>
                            </div>
                        )}
                        {stock.roe != null && (
                            <div className="text-center">
                                <div className="text-xs font-bold text-text">{(stock.roe * 100).toFixed(1)}%</div>
                                <div className="text-[10px] text-muted">Return on Equity</div>
                            </div>
                        )}
                        {stock.debt_to_equity != null && (
                            <div className="text-center">
                                <div className="text-xs font-bold text-text">{stock.debt_to_equity.toFixed(2)}</div>
                                <div className="text-[10px] text-muted">Debt / Equity</div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

// ── Section header ─────────────────────────────────────────────────────────

function SectionHeader({ emoji, label, count, color }: { emoji: string; label: string; count: number; color: string }) {
    return (
        <div className="flex items-center gap-3 mt-6 mb-3">
            <span className="text-xl">{emoji}</span>
            <h2 className={`text-sm font-extrabold uppercase tracking-widest ${color}`}>{label}</h2>
            <span className="rounded-full bg-border/30 px-2 py-0.5 text-[11px] font-bold text-muted">{count}</span>
            <div className="flex-1 h-px bg-border/40" />
        </div>
    )
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function BeginnerScreenerPage() {
    const [forceRefresh, setForceRefresh] = useState(false)

    const { data, isLoading, isFetching, error, refetch } = useQuery<BeginnerScreenerResponse>({
        queryKey: ['beginner-screener'],
        queryFn: () =>
            api
                .get<BeginnerScreenerResponse>(
                    `/screener/beginner${forceRefresh ? '?force_refresh=true' : ''}`
                )
                .then(r => r.data)
                .finally(() => setForceRefresh(false)),
        staleTime: 25 * 60 * 1000,
    })

    const busy = isLoading || isFetching

    const safePicks = data?.stocks.filter(s => s.overall === 'Safe Pick') ?? []
    const watchlist = data?.stocks.filter(s => s.overall === 'Watchlist') ?? []
    const tooRisky = data?.stocks.filter(s => s.overall === 'Too Risky') ?? []

    return (
        <div className="mx-auto max-w-5xl space-y-4 p-6">

            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 shadow-lg shadow-emerald-500/25">
                            <BookOpen className="h-5 w-5 text-white" />
                        </div>
                        <h1 className="text-2xl font-extrabold tracking-tight text-text">Beginner Picks</h1>
                    </div>
                    <p className="mt-1 text-sm text-muted max-w-xl">
                        Plain-English signals on {data?.scanned_count ?? 30} blue-chip Nifty 50 stocks.
                        No jargon — just <span className="text-emerald-400 font-semibold">Safe Pick</span>,{' '}
                        <span className="text-yellow-400 font-semibold">Watchlist</span>, or{' '}
                        <span className="text-red-400 font-semibold">Too Risky</span>.
                        {data?.cached && (
                            <span className="ml-1 text-indigo-400">· cached, refreshes in {fmtDuration(data.next_refresh_seconds)}</span>
                        )}
                    </p>
                </div>

                <button
                    onClick={() => { setForceRefresh(true); refetch() }}
                    disabled={busy}
                    className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-md hover:bg-emerald-500 disabled:opacity-60 transition-colors"
                >
                    <RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />
                    {busy ? 'Scanning…' : data?.cached ? 'Force Refresh' : 'Scan Now'}
                </button>
            </div>

            {/* How it works banner */}
            <div className="rounded-xl border border-teal-500/20 bg-teal-500/5 px-4 py-3 text-xs text-muted flex items-start gap-2.5">
                <Sparkles className="h-3.5 w-3.5 text-teal-400 mt-0.5 flex-shrink-0" />
                <span>
                    Each stock is checked for <strong className="text-text">3 things</strong> a beginner should care about:{' '}
                    <strong className="text-text">Debt level</strong> (is the company overleveraged?),{' '}
                    <strong className="text-text">Valuation</strong> (is it expensive?), and{' '}
                    <strong className="text-text">Profitability</strong> (is it making money?).
                    Hover any signal tag for a plain-English explanation, or click "What do these signals mean?"
                </span>
            </div>

            {/* Error */}
            {error && !busy && (
                <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
                    Failed to fetch market data. Please try again.
                </div>
            )}

            {/* Loading skeleton */}
            {busy && !data && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {Array.from({ length: 9 }).map((_, i) => (
                        <div key={i} className="h-44 animate-pulse rounded-2xl border border-border bg-surface" />
                    ))}
                    <p className="col-span-full text-center text-sm text-muted animate-pulse pt-2">
                        Fetching live data for 30 blue-chip stocks…
                    </p>
                </div>
            )}

            {/* Results */}
            {data && (
                <>
                    {/* Meta bar */}
                    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-xs text-muted">
                        <span>
                            <strong className="text-emerald-400">{safePicks.length} Safe Picks</strong>
                            {' · '}
                            <strong className="text-yellow-400">{watchlist.length} Watchlist</strong>
                            {' · '}
                            <strong className="text-red-400">{tooRisky.length} Too Risky</strong>
                            {' '}out of {data.successful_count} scanned
                        </span>
                        <div className="flex items-center gap-3">
                            {data.cached ? (
                                <span className="rounded-full bg-indigo-500/10 border border-indigo-500/30 px-2.5 py-1 text-indigo-400 font-semibold">
                                    ⚡ Cached · {fmtDuration(data.cache_age_seconds)} ago
                                </span>
                            ) : (
                                <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 text-emerald-400 font-semibold">
                                    ✓ Live data
                                </span>
                            )}
                            <span>Last scan: <strong className="text-text">{new Date(data.scan_timestamp + 'Z').toLocaleTimeString()}</strong></span>
                        </div>
                    </div>

                    {/* Safe Picks */}
                    {safePicks.length > 0 && (
                        <>
                            <SectionHeader emoji="✅" label="Safe Picks" count={safePicks.length} color="text-emerald-400" />
                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                                {safePicks.map(s => <StockCard key={s.symbol} stock={s} />)}
                            </div>
                        </>
                    )}

                    {/* Watchlist */}
                    {watchlist.length > 0 && (
                        <>
                            <SectionHeader emoji="⚠️" label="Watchlist" count={watchlist.length} color="text-yellow-400" />
                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                                {watchlist.map(s => <StockCard key={s.symbol} stock={s} />)}
                            </div>
                        </>
                    )}

                    {/* Too Risky */}
                    {tooRisky.length > 0 && (
                        <>
                            <SectionHeader emoji="🚫" label="Too Risky for Beginners" count={tooRisky.length} color="text-red-400" />
                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                                {tooRisky.map(s => <StockCard key={s.symbol} stock={s} />)}
                            </div>
                        </>
                    )}

                    <p className="text-center text-xs text-muted/50 pt-2">
                        Not financial advice. Data via Yahoo Finance. Always do your own research before investing.
                    </p>
                </>
            )}
        </div>
    )
}
