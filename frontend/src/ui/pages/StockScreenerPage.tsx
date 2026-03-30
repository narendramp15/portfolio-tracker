import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
    ChevronDown,
    ChevronRight,
    Lock,
    RefreshCw,
    Search,
    Sparkles,
    Star,
} from 'lucide-react'

import { api } from '../../lib/api'
import { useSubscription } from '../../hooks/useSubscription'

// ── Types ──────────────────────────────────────────────────────────────────

interface PillarScores {
    financial_strength: number
    earnings_quality: number
    valuation: number
    business_quality: number
    future_outlook: number
}

interface KeyMetrics {
    pe: number | null
    peg: number | null
    pb: number | null
    ev_ebitda: number | null
    debt_to_equity: number | null
    current_ratio: number | null
    roe: number | null
    profit_margin: number | null
    revenue_growth: number | null
    earnings_growth: number | null
}

interface StockResult {
    rank: number
    symbol: string
    name: string
    sector: string
    current_price: number
    value_score: number
    pillar_scores: PillarScores
    key_metrics: KeyMetrics
    recommendation: string
}

interface ScreenerResponse {
    top_stocks: StockResult[]
    scanned_count: number
    successful_count: number
    scan_timestamp: string
    cached: boolean
    cache_age_seconds: number
    next_refresh_seconds: number
}

// ── Helpers ────────────────────────────────────────────────────────────────

const fmtNum = (n: number | null | undefined, decimals = 2): string =>
    n == null ? '—' : n.toFixed(decimals)

const fmtPct = (n: number | null | undefined): string =>
    n == null ? '—' : `${(n * 100).toFixed(1)}%`

const fmtDuration = (sec: number): string => {
    if (sec <= 0) return 'now'
    const h = Math.floor(sec / 3600)
    const m = Math.floor((sec % 3600) / 60)
    if (h >= 23) return 'tomorrow'
    if (h > 0) return `${h}h ${m}m`
    return `${m}m`
}

function recStyle(rec: string) {
    if (rec.includes('Strong Value Buy')) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/40'
    if (rec.includes('Value Buy')) return 'text-green-400 bg-green-500/10 border-green-500/40'
    if (rec.includes('Moderate')) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/40'
    if (rec.includes('Fairly')) return 'text-blue-400 bg-blue-500/10 border-blue-500/40'
    return 'text-red-400 bg-red-500/10 border-red-500/40'
}

function pillarColor(s: number) {
    if (s >= 7.5) return '#10b981' // emerald
    if (s >= 5.0) return '#6366f1' // indigo
    if (s >= 2.5) return '#f59e0b' // amber
    return '#ef4444'               // red
}

function scoreTextColor(s: number) {
    if (s >= 75) return 'text-emerald-400'
    if (s >= 60) return 'text-green-400'
    if (s >= 45) return 'text-yellow-400'
    if (s >= 30) return 'text-blue-400'
    return 'text-red-400'
}

function rankCls(r: number) {
    if (r === 1) return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40'
    if (r === 2) return 'bg-zinc-400/20  text-zinc-300  border-zinc-400/40'
    if (r === 3) return 'bg-amber-700/20 text-amber-400 border-amber-600/40'
    return 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20'
}

// ── Tiny pillar cell: numeric score + mini bar ─────────────────────────────

function PillarCell({ score }: { score: number }) {
    const color = pillarColor(score)
    return (
        <div className="flex flex-col items-center gap-0.5 min-w-[44px]">
            <span className="text-xs font-bold text-text">{score.toFixed(1)}</span>
            <div className="h-1 w-full rounded-full bg-border/50">
                <div
                    className="h-1 rounded-full"
                    style={{ width: `${(score / 10) * 100}%`, background: color }}
                />
            </div>
        </div>
    )
}

// ── Expandable metrics row ─────────────────────────────────────────────────

// ── AI Thesis panel (lazy — fetched on demand) ────────────────────────────

interface ThesisResponse {
    symbol: string
    thesis: string
    from_cache: boolean
    generated_at: string
}

function AIThesisPanel({ symbol, isPro }: { symbol: string; isPro: boolean }) {
    const [requested, setRequested] = useState(false)

    const { data, isFetching, error } = useQuery<ThesisResponse>({
        queryKey: ['stock-thesis', symbol],
        queryFn: () =>
            api.get<ThesisResponse>(`/screener/thesis/${encodeURIComponent(symbol)}`).then(r => r.data),
        enabled: requested && isPro,
        staleTime: 23 * 60 * 60 * 1000, // 23 h — matches server 24-h cache
        retry: 1,
    })

    if (!isPro) {
        return (
            <div className="relative mt-5 overflow-hidden rounded-xl border border-indigo-500/30 bg-indigo-500/5">
                {/* Blurred sample text */}
                <div className="select-none blur-sm px-4 py-3 text-xs text-muted leading-relaxed pointer-events-none">
                    This stock presents a compelling value opportunity driven by strong earnings
                    growth and an undemanding valuation relative to peers. The balance sheet
                    remains robust with manageable leverage and healthy cash conversion. The
                    primary risk is margin compression from input cost inflation. Verdict: a
                    patient accumulation candidate for value-oriented portfolios.
                </div>
                {/* Overlay */}
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-surface/80 backdrop-blur-[1px]">
                    <Lock className="h-5 w-5 text-indigo-400" />
                    <p className="text-xs font-semibold text-text">AI Insight — Pro only</p>
                    <a
                        href="/app/billing"
                        className="mt-1 rounded-full bg-indigo-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-indigo-500 transition-colors"
                    >
                        Upgrade to Pro
                    </a>
                </div>
            </div>
        )
    }

    if (!requested) {
        return (
            <div className="mt-5">
                <button
                    onClick={() => setRequested(true)}
                    className="flex items-center gap-2 rounded-xl border border-indigo-500/40 bg-indigo-500/10 px-4 py-2 text-xs font-semibold text-indigo-300 hover:bg-indigo-500/20 transition-colors"
                >
                    <Sparkles className="h-3.5 w-3.5" />
                    Get AI Insight
                </button>
            </div>
        )
    }

    if (isFetching) {
        return (
            <div className="mt-5 flex items-center gap-2 text-xs text-muted animate-pulse">
                <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
                Generating thesis…
            </div>
        )
    }

    if (error || !data) {
        return (
            <div className="mt-5 text-xs text-red-400">
                Could not generate thesis. Please try again.
            </div>
        )
    }

    return (
        <div className="mt-5 rounded-xl border border-indigo-500/30 bg-indigo-500/5 px-4 py-3">
            <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
                    <span className="text-[11px] font-bold uppercase tracking-widest text-indigo-400">AI Insight</span>
                </div>
                <span className="text-[10px] text-muted/60">
                    {data.from_cache ? '⚡ cached' : '✓ freshly generated'}
                </span>
            </div>
            <p className="text-xs text-text leading-relaxed whitespace-pre-wrap">{data.thesis}</p>
        </div>
    )
}

// ── Expandable metrics row ─────────────────────────────────────────────────

function MetricsRow({ m, ps, symbol, isPro }: { m: KeyMetrics; ps: PillarScores; symbol: string; isPro: boolean }) {
    const metrics = [
        { label: 'P/E', val: fmtNum(m.pe), note: 'Lower = cheaper on earnings' },
        { label: 'PEG', val: fmtNum(m.peg), note: '< 1 = growth underpriced' },
        { label: 'P/B', val: fmtNum(m.pb), note: '< 3 = asset-backed value' },
        { label: 'EV/EBITDA', val: fmtNum(m.ev_ebitda), note: '< 12 = operationally cheap' },
        { label: 'Debt/Equity', val: fmtNum(m.debt_to_equity), note: '< 0.5 = low leverage' },
        { label: 'Current Ratio', val: fmtNum(m.current_ratio), note: '> 1.5 = liquid' },
        { label: 'ROE', val: fmtPct(m.roe), note: '> 15% = efficient capital use' },
        { label: 'Profit Margin', val: fmtPct(m.profit_margin), note: '> 10% = quality earnings' },
        { label: 'Rev. Growth', val: fmtPct(m.revenue_growth), note: '> 10% CAGR is healthy' },
        { label: 'EPS Growth', val: fmtPct(m.earnings_growth), note: 'Consistent = quality' },
    ]
    const pillars = [
        {
            label: 'Financial Strength', score: ps.financial_strength, weight: 20, color: '#3b82f6',
            note: 'D/E ratio, Current Ratio, Interest Coverage'
        },
        {
            label: 'Earnings Quality', score: ps.earnings_quality, weight: 25, color: '#6366f1',
            note: 'Revenue growth, Profit margin, EPS growth, Op margin'
        },
        {
            label: 'Valuation', score: ps.valuation, weight: 25, color: '#a855f7',
            note: 'P/E, PEG, P/B, EV/EBITDA vs benchmarks'
        },
        {
            label: 'Business Quality', score: ps.business_quality, weight: 15, color: '#8b5cf6',
            note: 'ROE, Gross margin, Return on Assets'
        },
        {
            label: 'Future Outlook', score: ps.future_outlook, weight: 15, color: '#d946ef',
            note: 'Forward P/E trend, Analyst target upside, Rec mean'
        },
    ]
    const total = pillars.reduce((acc, p) => acc + p.score * (p.weight / 10), 0)

    return (
        <td colSpan={8} className="p-0">
            <div className="border-t border-border/40 bg-gradient-to-b from-indigo-950/10 to-transparent px-6 py-5">
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

                    {/* Score breakdown */}
                    <div>
                        <p className="mb-3 text-xs font-bold uppercase tracking-widest text-muted">Score Breakdown</p>
                        <div className="space-y-2">
                            {pillars.map(p => (
                                <div key={p.label} className="flex items-center gap-3">
                                    <div className="w-36 flex-shrink-0">
                                        <div className="flex items-center justify-between mb-0.5">
                                            <span className="text-xs text-muted">{p.label}</span>
                                            <span className="text-xs font-bold text-text">{p.score.toFixed(1)}</span>
                                        </div>
                                        <div className="h-1.5 rounded-full bg-border/50">
                                            <div className="h-1.5 rounded-full" style={{ width: `${(p.score / 10) * 100}%`, background: p.color }} />
                                        </div>
                                    </div>
                                    <span className="text-[11px] text-muted/70 flex-1">{p.note}</span>
                                    <span className="text-xs font-semibold text-text w-16 text-right">
                                        ×{p.weight}% = <span style={{ color: p.color }}>{(p.score * p.weight / 10).toFixed(1)}</span>
                                    </span>
                                </div>
                            ))}
                        </div>
                        <div className="mt-3 flex items-center justify-end gap-2 border-t border-border/40 pt-2">
                            <span className="text-xs text-muted">Total Value Score</span>
                            <span className={`text-lg font-extrabold ${scoreTextColor(total)}`}>{total.toFixed(1)} / 100</span>
                        </div>
                    </div>

                    {/* Key metrics grid */}
                    <div>
                        <p className="mb-3 text-xs font-bold uppercase tracking-widest text-muted">Key Metrics</p>
                        <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
                            {metrics.map(({ label, val, note }) => (
                                <div key={label} className="group flex items-center justify-between border-b border-border/20 pb-1">
                                    <span className="text-xs text-muted group-hover:text-text transition-colors" title={note}>{label}</span>
                                    <span className="text-xs font-semibold text-text">{val}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* AI Thesis */}
                <AIThesisPanel symbol={symbol} isPro={isPro} />
            </div>
        </td>
    )
}

// ── Table row ──────────────────────────────────────────────────────────────

function StockRow({ stock, isPro }: { stock: StockResult; isPro: boolean }) {
    const [open, setOpen] = useState(false)
    const ps = stock.pillar_scores

    return (
        <>
            <tr
                onClick={() => setOpen(v => !v)}
                className="cursor-pointer border-b border-border/30 hover:bg-indigo-500/5 transition-colors"
            >
                {/* Rank */}
                <td className="py-3 pl-4 pr-2 w-10">
                    <span className={`inline-flex h-7 w-7 items-center justify-center rounded-lg border text-[11px] font-bold ${rankCls(stock.rank)}`}>
                        {stock.rank}
                    </span>
                </td>

                {/* Name */}
                <td className="py-3 px-3 min-w-[160px]">
                    <div className="font-semibold text-text text-sm leading-tight">{stock.name}</div>
                    <div className="flex gap-1.5 mt-0.5">
                        <span className="font-mono text-[10px] text-muted bg-border/30 rounded px-1.5 py-0.5">{stock.symbol.replace('.NS', '')}</span>
                        <span className="text-[10px] text-muted/70 truncate max-w-[100px]">{stock.sector}</span>
                    </div>
                </td>

                {/* Price */}
                <td className="py-3 px-3 text-right whitespace-nowrap">
                    <span className="text-sm font-semibold text-text">₹{stock.current_price.toLocaleString('en-IN')}</span>
                </td>

                {/* Value Score */}
                <td className="py-3 px-3 text-center w-20">
                    <span className={`text-xl font-extrabold ${scoreTextColor(stock.value_score)}`}>{stock.value_score}</span>
                    <div className="text-[9px] text-muted/60">/ 100</div>
                </td>

                {/* 5 pillar scores */}
                <td className="py-3 px-2 w-12"><PillarCell score={ps.financial_strength} /></td>
                <td className="py-3 px-2 w-12"><PillarCell score={ps.earnings_quality} /></td>
                <td className="py-3 px-2 w-12"><PillarCell score={ps.valuation} /></td>
                <td className="py-3 px-2 w-12"><PillarCell score={ps.business_quality} /></td>
                <td className="py-3 px-2 w-12"><PillarCell score={ps.future_outlook} /></td>

                {/* Recommendation */}
                <td className="py-3 px-3 hidden sm:table-cell">
                    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-[10px] font-semibold whitespace-nowrap ${recStyle(stock.recommendation)}`}>
                        {stock.recommendation}
                    </span>
                </td>

                {/* Expand toggle */}
                <td className="py-3 pr-4 text-right w-8">
                    {open
                        ? <ChevronDown className="h-4 w-4 text-muted inline" />
                        : <ChevronRight className="h-4 w-4 text-muted inline" />}
                </td>
            </tr>

            {open && (
                <tr className="border-b border-border/20">
                    <MetricsRow m={stock.key_metrics} ps={ps} symbol={stock.symbol} isPro={isPro} />
                </tr>
            )}
        </>
    )
}

// ── How-score-works footer panel ───────────────────────────────────────────

function ScoreFormulaPanel() {
    const pillars = [
        {
            label: 'Financial Strength', abbr: 'FS', weight: 20, color: '#3b82f6',
            metrics: 'Debt/Equity < 0.2 · Current Ratio > 1.5 · Interest Coverage > 3'
        },
        {
            label: 'Earnings Quality', abbr: 'EQ', weight: 25, color: '#6366f1',
            metrics: 'Revenue Growth > 10% · Profit Margin > 10% · EPS Growth · Op Margin'
        },
        {
            label: 'Valuation', abbr: 'Val', weight: 25, color: '#a855f7',
            metrics: 'P/E < 20 · PEG < 1 · P/B < 3 · EV/EBITDA < 12'
        },
        {
            label: 'Business Quality', abbr: 'BQ', weight: 15, color: '#8b5cf6',
            metrics: 'ROE > 15% · Gross Margin > 35% · Return on Assets > 10%'
        },
        {
            label: 'Future Outlook', abbr: 'FO', weight: 15, color: '#d946ef',
            metrics: 'Forward P/E falling · Analyst upside > 15% · Strong buy consensus'
        },
    ]

    return (
        <div className="rounded-2xl border border-border bg-surface p-6">
            <div className="flex items-center gap-2 mb-5">
                <Star className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-text">How the Value Score is Calculated</h3>
            </div>

            {/* Formula bar */}
            <div className="mb-5 flex flex-wrap items-center gap-2 text-sm font-mono">
                <span className="text-muted">Score =</span>
                {pillars.map((p, i) => (
                    <span key={p.abbr} className="flex items-center gap-1">
                        <span className="font-bold" style={{ color: p.color }}>{p.abbr}</span>
                        <span className="text-muted text-xs">×{p.weight}%</span>
                        {i < pillars.length - 1 && <span className="text-muted mx-0.5">+</span>}
                    </span>
                ))}
                <span className="text-muted ml-1">→ 0–100</span>
            </div>

            {/* Pillar cards */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
                {pillars.map(p => (
                    <div key={p.abbr} className="rounded-xl border border-border/60 bg-border/10 p-3">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-bold text-text">{p.label}</span>
                            <span className="rounded-full px-2 py-0.5 text-[10px] font-bold bg-border/30 text-muted">{p.weight}%</span>
                        </div>
                        <div className="h-0.5 rounded-full mb-2" style={{ background: p.color, opacity: 0.7 }} />
                        <p className="text-[10px] text-muted leading-relaxed">{p.metrics}</p>
                    </div>
                ))}
            </div>

            {/* Each pillar scored 0-10 note */}
            <p className="mt-4 text-[11px] text-muted/60 text-center">
                Each pillar is scored <strong className="text-muted">0–10</strong> from rule-based thresholds on live Yahoo Finance data.
                The weighted sum produces the final <strong className="text-muted">0–100 Value Score</strong>.
                Scores ≥ 75 = Strong Value Buy · ≥ 60 = Value Buy · ≥ 45 = Moderate · ≥ 30 = Fairly Valued · &lt; 30 = Avoid.
            </p>
        </div>
    )
}

// ── Main page ──────────────────────────────────────────────────────────────

const PILLAR_HEADERS = [
    { label: 'FS', title: 'Financial Strength (20%)', color: '#3b82f6' },
    { label: 'EQ', title: 'Earnings Quality (25%)', color: '#6366f1' },
    { label: 'Val', title: 'Valuation (25%)', color: '#a855f7' },
    { label: 'BQ', title: 'Business Quality (15%)', color: '#8b5cf6' },
    { label: 'FO', title: 'Future Outlook (15%)', color: '#d946ef' },
]

export default function StockScreenerPage() {
    const [topN, setTopN] = useState(10)
    const [forceRefresh, setForceRefresh] = useState(false)
    const { isPro } = useSubscription()

    const { data, isLoading, isFetching, error, refetch } = useQuery<ScreenerResponse>({
        queryKey: ['stock-screener', topN],
        queryFn: () =>
            api
                .get<ScreenerResponse>(
                    `/screener/top-value?top_n=${topN}${forceRefresh ? '&force_refresh=true' : ''}`
                )
                .then((r) => r.data)
                .finally(() => setForceRefresh(false)),
        staleTime: 25 * 60 * 1000,
    })

    const busy = isLoading || isFetching

    function handleForceRefresh() {
        setForceRefresh(true)
        refetch()
    }

    return (
        <div className="mx-auto max-w-7xl space-y-6 p-6">

            {/* ── Header ── */}
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 shadow-lg shadow-indigo-500/25">
                            <Search className="h-5 w-5 text-white" />
                        </div>
                        <h1 className="text-2xl font-extrabold tracking-tight text-text">Value Stock Screener</h1>
                    </div>
                    <p className="mt-1 text-sm text-muted">
                        Scans {data?.scanned_count ?? '40+'} NSE stocks · ranks by 5-pillar value score · click any row to expand
                        {data?.cached && (
                            <span className="ml-2 text-indigo-400">
                                · cached, refreshes in {fmtDuration(data.next_refresh_seconds)}
                            </span>
                        )}
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <select
                        value={topN}
                        onChange={(e) => setTopN(Number(e.target.value))}
                        disabled={busy}
                        className="rounded-xl border border-border bg-surface px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                        {[5, 10, 15, 20].map((n) => (
                            <option key={n} value={n}>Top {n}</option>
                        ))}
                    </select>

                    <button
                        onClick={handleForceRefresh}
                        disabled={busy}
                        title={data?.cached ? `Data from ${fmtDuration(data.cache_age_seconds)} ago — force a fresh scan` : 'Scan all stocks now'}
                        className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-md hover:bg-indigo-500 disabled:opacity-60 transition-colors"
                    >
                        <RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />
                        {busy ? 'Scanning…' : data?.cached ? 'Force Refresh' : 'Scan Now'}
                    </button>
                </div>
            </div>

            {/* ── Error ── */}
            {error && !busy && (
                <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
                    Failed to fetch market data. Please try again.
                </div>
            )}

            {/* ── Loading skeleton ── */}
            {busy && !data && (
                <div className="space-y-2">
                    {Array.from({ length: 8 }).map((_, i) => (
                        <div key={i} className="h-12 animate-pulse rounded-xl border border-border bg-surface" />
                    ))}
                    <p className="text-center text-sm text-muted animate-pulse pt-2">
                        Scanning 40 stocks in parallel — usually done in ~5 seconds…
                    </p>
                </div>
            )}

            {/* ── Results table ── */}
            {data && (
                <>
                    {/* Meta bar */}
                    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-xs text-muted">
                        <span>
                            Showing top <strong className="text-text">{data.top_stocks.length}</strong> of{' '}
                            <strong className="text-text">{data.successful_count}</strong> scanned stocks
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

                    {/* Table */}
                    <div className="overflow-x-auto rounded-2xl border border-border bg-surface shadow-sm">
                        <table className="w-full border-collapse text-sm">
                            <thead>
                                <tr className="border-b border-border/60 bg-border/10 text-xs text-muted">
                                    <th className="py-3 pl-4 pr-2 text-left font-semibold w-10">#</th>
                                    <th className="py-3 px-3 text-left font-semibold">Stock</th>
                                    <th className="py-3 px-3 text-right font-semibold">Price</th>
                                    <th className="py-3 px-3 text-center font-semibold w-20">Score</th>
                                    {PILLAR_HEADERS.map(h => (
                                        <th key={h.label} className="py-3 px-2 text-center w-12 font-semibold" title={h.title}>
                                            <span style={{ color: h.color }}>{h.label}</span>
                                        </th>
                                    ))}
                                    <th className="py-3 px-3 text-left font-semibold hidden sm:table-cell">Signal</th>
                                    <th className="py-3 pr-4 w-8" />
                                </tr>
                            </thead>
                            <tbody>
                                {data.top_stocks.map((stock) => (
                                    <StockRow key={stock.symbol} stock={stock} isPro={isPro} />
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Score formula panel */}
                    <ScoreFormulaPanel />

                    <p className="text-center text-xs text-muted/50">
                        Not financial advice. Data via Yahoo Finance. Always do your own due diligence.
                    </p>
                </>
            )}
        </div>
    )
}
