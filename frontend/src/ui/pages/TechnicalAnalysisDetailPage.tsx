import { useQuery } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, Activity, Target, Zap, AlertCircle, CheckCircle, ArrowUpRight, ArrowDownRight, ArrowLeft } from 'lucide-react'

import { api } from '../../lib/api'
import { formatCurrencyINR } from '../../lib/format'
import { Card } from '../components/Card'

type TechnicalAnalysis = {
    asset_id: number
    symbol: string
    name: string
    portfolio_name: string
    current_price: number
    purchase_price: number
    quantity: number
    invested_value: number
    current_value: number
    gain_loss: number
    gain_loss_percentage: number
    indicators: {
        rsi: number
        macd: {
            value: number
            signal: number
            histogram: number
        }
        moving_averages: {
            sma_20: number
            sma_50: number
            sma_200: number
        }
        bollinger_bands: {
            upper: number
            middle: number
            lower: number
        }
        volume: {
            trend: string
            average: number
        }
    }
    recommendation: string
    action_text: string
    confidence: number
    signals: string[]
    bullish_factors: number
    bearish_factors: number
}

async function fetchAssetAnalysis(assetId: string) {
    const { data } = await api.get<TechnicalAnalysis>(`/analysis/analysis/${assetId}`)
    return data
}

function getRecommendationColor(recommendation: string) {
    switch (recommendation) {
        case 'strong_buy':
            return 'from-emerald-600/50 to-green-600/50 dark:from-emerald-600/50 dark:to-green-600/50'
        case 'buy':
            return 'from-emerald-600/30 to-green-600/30 dark:from-emerald-600/30 dark:to-green-600/30'
        case 'hold':
            return 'from-border/30 to-border/30 dark:from-zinc-600/30 dark:to-zinc-700/30'
        case 'sell':
            return 'from-rose-600/30 to-red-600/30 dark:from-rose-600/30 dark:to-red-600/30'
        case 'strong_sell':
            return 'from-rose-600/50 to-red-600/50 dark:from-rose-600/50 dark:to-red-600/50'
        default:
            return 'from-border/30 to-border/30 dark:from-zinc-600/30 dark:to-zinc-700/30'
    }
}

function getRecommendationIcon(recommendation: string) {
    switch (recommendation) {
        case 'strong_buy':
        case 'buy':
            return <TrendingUp className="h-5 w-5 text-emerald-400" />
        case 'strong_sell':
        case 'sell':
            return <TrendingDown className="h-5 w-5 text-rose-400" />
        default:
            return <Activity className="h-5 w-5 text-muted" />
    }
}

function RSIIndicator({ value }: { value: number }) {
    const isOversold = value < 30
    const isOverbought = value > 70
    const color = isOversold ? 'text-emerald-400' : isOverbought ? 'text-rose-400' : 'text-muted'

    return (
        <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
                <span className="text-muted">RSI</span>
                <span className={`font-bold ${color}`}>{value.toFixed(1)}</span>
            </div>
            <div className="h-2 bg-border rounded-full overflow-hidden">
                <div
                    className={`h-full transition-all ${isOversold ? 'bg-emerald-500' : isOverbought ? 'bg-rose-500' : 'bg-indigo-500'}`}
                    style={{ width: `${value}%` }}
                />
            </div>
            <div className="flex justify-between text-[10px] text-muted">
                <span>Oversold</span>
                <span>Neutral</span>
                <span>Overbought</span>
            </div>
        </div>
    )
}

export function TechnicalAnalysisDetailPage() {
    const { assetId } = useParams<{ assetId: string }>()
    const navigate = useNavigate()
    const query = useQuery({
        queryKey: ['analysis', assetId],
        queryFn: () => fetchAssetAnalysis(assetId!),
        enabled: !!assetId
    })

    if (query.isLoading) {
        return (
            <div className="space-y-4">
                <div className="h-[200px] animate-pulse rounded-xl border border-border bg-surface" />
                <div className="h-[200px] animate-pulse rounded-xl border border-border bg-surface" />
            </div>
        )
    }

    if (query.isError || !query.data) {
        return (
            <Card>
                <div className="text-sm text-danger">Failed to load technical analysis.</div>
            </Card>
        )
    }

    const item = query.data
    const isPositive = item.gain_loss >= 0

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate('/app/analysis')}
                        className="flex h-10 w-10 items-center justify-center rounded-xl bg-border/50 text-muted hover:bg-border hover:text-text transition-all border border-border"
                    >
                        <ArrowLeft className="h-5 w-5" />
                    </button>
                    <div>
                        <div className="text-xs font-bold uppercase tracking-widest text-indigo-400/70 flex items-center gap-2">
                            <span className="inline-block w-8 h-0.5 bg-gradient-to-r from-indigo-500 to-transparent rounded-full"></span>
                            Detailed Analysis
                        </div>
                        <h1 className="mt-2 text-4xl font-black tracking-tight bg-gradient-to-r from-indigo-400 via-purple-300 to-indigo-500 bg-clip-text text-transparent">
                            {item.symbol} - {item.name}
                        </h1>
                    </div>
                </div>
            </div>

            <Card variant="gradient" className="overflow-hidden">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Left Column - Asset Info & Recommendation */}
                    <div className="space-y-4">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <h3 className="text-2xl font-black text-white">{item.symbol}</h3>
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${isPositive ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                                    {isPositive ? '+' : ''}{item.gain_loss_percentage.toFixed(2)}%
                                </span>
                            </div>
                            <p className="text-sm text-muted truncate">{item.name}</p>
                            <p className="text-xs text-muted mt-1">{item.portfolio_name}</p>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <div className="text-xs text-muted">Current Price</div>
                                <div className="text-base font-black text-white">{formatCurrencyINR(item.current_price)}</div>
                            </div>
                            <div>
                                <div className="text-xs text-muted">Quantity</div>
                                <div className="text-base font-black text-white">{item.quantity}</div>
                            </div>
                            <div>
                                <div className="text-xs text-muted">Invested</div>
                                <div className="text-sm font-bold text-white">{formatCurrencyINR(item.invested_value)}</div>
                            </div>
                            <div>
                                <div className="text-xs text-muted">Current Value</div>
                                <div className="text-sm font-bold text-white">{formatCurrencyINR(item.current_value)}</div>
                            </div>
                        </div>

                        {/* AI Recommendation */}
                        <Card className={`bg-gradient-to-br ${getRecommendationColor(item.recommendation)} border-none`}>
                            <div className="flex items-center gap-3">
                                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-black/30 flex-shrink-0">
                                    {getRecommendationIcon(item.recommendation)}
                                </div>
                                <div className="flex-1">
                                    <div className="text-xs font-bold uppercase tracking-wider text-white/70">AI Recommendation</div>
                                    <div className="text-lg font-black text-white">{item.action_text}</div>
                                    <div className="text-xs text-white/60 mt-1">Confidence: {item.confidence}%</div>
                                </div>
                            </div>
                        </Card>

                        {/* Bullish vs Bearish */}
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                                <ArrowUpRight className="h-4 w-4 text-emerald-400" />
                                <span className="text-xs text-muted">Bullish: <span className="font-bold text-emerald-400">{item.bullish_factors}</span></span>
                            </div>
                            <div className="flex items-center gap-2">
                                <ArrowDownRight className="h-4 w-4 text-rose-400" />
                                <span className="text-xs text-muted">Bearish: <span className="font-bold text-rose-400">{item.bearish_factors}</span></span>
                            </div>
                        </div>
                    </div>

                    {/* Middle Column - Technical Indicators */}
                    <div className="space-y-4">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-muted flex items-center gap-2">
                            <Target className="h-3 w-3" />
                            Technical Indicators
                        </h4>

                        <RSIIndicator value={item.indicators.rsi} />

                        <div className="space-y-2">
                            <div className="text-xs font-semibold text-muted">MACD</div>
                            <div className="grid grid-cols-3 gap-2 text-xs">
                                <div>
                                    <div className="text-muted">Value</div>
                                    <div className="font-bold text-text">{item.indicators.macd.value.toFixed(2)}</div>
                                </div>
                                <div>
                                    <div className="text-muted">Signal</div>
                                    <div className="font-bold text-text">{item.indicators.macd.signal.toFixed(2)}</div>
                                </div>
                                <div>
                                    <div className="text-muted">Histogram</div>
                                    <div className={`font-bold ${item.indicators.macd.histogram > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                        {item.indicators.macd.histogram.toFixed(2)}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="text-xs font-semibold text-muted">Moving Averages</div>
                            <div className="space-y-1.5">
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-muted">SMA 20</span>
                                    <span className="font-bold text-text">{formatCurrencyINR(item.indicators.moving_averages.sma_20)}</span>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-muted">SMA 50</span>
                                    <span className="font-bold text-text">{formatCurrencyINR(item.indicators.moving_averages.sma_50)}</span>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-muted">SMA 200</span>
                                    <span className="font-bold text-text">{formatCurrencyINR(item.indicators.moving_averages.sma_200)}</span>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="text-xs font-semibold text-muted">Bollinger Bands</div>
                            <div className="space-y-1.5">
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-muted">Upper</span>
                                    <span className="font-bold text-text">{formatCurrencyINR(item.indicators.bollinger_bands.upper)}</span>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-muted">Middle</span>
                                    <span className="font-bold text-indigo-400">{formatCurrencyINR(item.indicators.bollinger_bands.middle)}</span>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-muted">Lower</span>
                                    <span className="font-bold text-text">{formatCurrencyINR(item.indicators.bollinger_bands.lower)}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right Column - AI Signals */}
                    <div className="space-y-4">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-muted flex items-center gap-2">
                            <Zap className="h-3 w-3" />
                            AI Analysis Signals
                        </h4>

                        <div className="space-y-2">
                            {item.signals.map((signal, idx) => (
                                <div key={idx} className="flex items-start gap-2 p-3 rounded-lg bg-indigo-50 dark:bg-surface border border-border">
                                    <CheckCircle className="h-4 w-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                                    <p className="text-xs text-indigo-900 dark:text-text leading-relaxed">{signal}</p>
                                </div>
                            ))}
                        </div>

                        <div className="p-4 rounded-lg bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-500/30">
                            <div className="flex items-start gap-2">
                                <AlertCircle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
                                <div className="text-xs text-amber-200/80 leading-relaxed">
                                    <strong className="text-amber-300">Disclaimer:</strong> This analysis is AI-generated based on technical indicators.
                                    Always do your own research and consult financial advisors before making investment decisions.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </Card>
        </div>
    )
}
