import { useState, useEffect } from 'react'
import { api } from '../../lib/api'

const ACCENT = '#00ff9d'
const BG = '#040c15'
const CARD = '#080f1a'
const BORDER = '#112030'
const RED = '#ff4d6d'
const GREEN = '#00ff9d'
const YELLOW = '#ffd166'
const PURPLE = '#a78bfa'
const BLUE = '#38bdf8'

// ── Types ────────────────────────────────────────────────────────────────────
interface TokenUsage {
    inputTokens: number
    outputTokens: number
    cacheReadTokens: number
    cacheWriteTokens: number
    costInr: number
    cached: boolean
}

interface UsageData {
    tier: string
    tier_label: string
    credits: number
    analyses_today: number
    daily_limit: number
    circuit_breaker_hit: boolean
    allowed_types: string[]
    credits_per_analysis: Record<string, number>
    cooldown_seconds: number
}

// ────────────────────────────────────────────────────────────────────────────

// Inline style helpers (shared atoms)
const S = {
    card: { background: CARD, border: `1px solid ${BORDER}`, borderRadius: '14px', padding: '22px', position: 'relative', overflow: 'hidden' } as React.CSSProperties,
    label: { fontSize: '10px', color: '#475569', letterSpacing: '0.15em', marginBottom: '5px', display: 'block', textTransform: 'uppercase' } as React.CSSProperties,
    input: { width: '100%', background: '#060e18', border: `1px solid ${BORDER}`, borderRadius: '7px', padding: '9px 12px', color: '#e2e8f0', fontSize: '12px', fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box', transition: 'border-color 0.2s, box-shadow 0.2s' } as React.CSSProperties,
    select: { width: '100%', background: '#060e18', border: `1px solid ${BORDER}`, borderRadius: '7px', padding: '9px 12px', color: '#e2e8f0', fontSize: '12px', fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' } as React.CSSProperties,
    dataRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 0', borderBottom: `1px solid ${BORDER}` } as React.CSSProperties,
    tag: { display: 'inline-flex', padding: '3px 10px', borderRadius: '4px', fontSize: '10px', fontWeight: '700', letterSpacing: '0.08em' } as React.CSSProperties,
}

const marketDefaults = {
    niftyClose: '24765.90',
    bankniftyClose: '59055.85',
    giftNifty: '24820',
    vix: '13.45',
    fiiActivity: '-4630',
    diiActivity: '+24312',
    usMarket: '+0.5',
    crude: '72.40',
    dollarIndex: '104.20',
    majorEvents: 'No major events',
    capitalRisk: '2',
    traderExperience: 'Intermediate',
    sessionType: 'Intraday',
}

type MarketData = typeof marketDefaults

// ── Markdown renderer ────────────────────────────────────────────────────
function renderInline(text: string): React.ReactNode {
    const parts = text.split(/(\*\*[^*]+\*\*)/g)
    return parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={i} style={{ color: '#f1f5f9', fontWeight: '700' }}>{part.slice(2, -2)}</strong>
        }
        return <span key={i}>{part}</span>
    })
}

function renderMarkdown(text: string): React.ReactNode {
    const lines = text.split('\n')
    const elements: React.ReactNode[] = []
    let i = 0
    while (i < lines.length) {
        const line = lines[i]
        if (line.startsWith('# ')) {
            elements.push(
                <h1 key={i} style={{ color: ACCENT, fontSize: '15px', fontWeight: '700', margin: '16px 0 8px', letterSpacing: '0.1em', borderBottom: `1px solid ${ACCENT}30`, paddingBottom: '8px' }}>
                    {renderInline(line.slice(2))}
                </h1>
            )
            i++
        } else if (line.startsWith('## ')) {
            elements.push(
                <h2 key={i} style={{ color: ACCENT, fontSize: '12px', fontWeight: '700', margin: '14px 0 6px', letterSpacing: '0.12em', textTransform: 'uppercase', opacity: 0.85 }}>
                    {renderInline(line.slice(3))}
                </h2>
            )
            i++
        } else if (line.startsWith('### ')) {
            elements.push(
                <h3 key={i} style={{ color: YELLOW, fontSize: '12px', fontWeight: '700', margin: '10px 0 4px', letterSpacing: '0.08em' }}>
                    {renderInline(line.slice(4))}
                </h3>
            )
            i++
        } else if (/^-{3,}$/.test(line.trim())) {
            elements.push(<hr key={i} style={{ border: 'none', borderTop: `1px solid ${BORDER}`, margin: '10px 0' }} />)
            i++
        } else if (/^[-*] /.test(line)) {
            const items: React.ReactNode[] = []
            while (i < lines.length && /^[-*] /.test(lines[i])) {
                items.push(
                    <li key={i} style={{ marginBottom: '3px', paddingLeft: '2px' }}>
                        {renderInline(lines[i].slice(2))}
                    </li>
                )
                i++
            }
            elements.push(
                <ul key={`ul-${i}`} style={{ margin: '4px 0 6px', paddingLeft: '18px', listStyleType: 'disc', color: '#cbd5e1' }}>
                    {items}
                </ul>
            )
        } else if (line.trim() === '') {
            elements.push(<div key={i} style={{ height: '6px' }} />)
            i++
        } else {
            elements.push(
                <p key={i} style={{ margin: '3px 0', color: '#cbd5e1' }}>
                    {renderInline(line)}
                </p>
            )
            i++
        }
    }
    return elements
}
// ─────────────────────────────────────────────────────────────────────────────

function formatNum(n: string): string {
    return parseFloat(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })
}

function getVixColor(vix: string): string {
    const v = parseFloat(vix)
    if (v < 12) return GREEN
    if (v < 16) return YELLOW
    return RED
}

export default function NiftyOptionsAnalyzerPage() {
    const [data, setData] = useState<MarketData>(marketDefaults)
    const [aiResponse, setAiResponse] = useState('')
    const [loading, setLoading] = useState(false)
    const [fetching, setFetching] = useState(false)
    const [error, setError] = useState('')
    const [currentTime, setCurrentTime] = useState(new Date())
    const [analysisType, setAnalysisType] = useState<'quick' | 'full' | 'advanced'>('quick')
    const [tokensUsed, setTokensUsed] = useState<TokenUsage | null>(null)
    const [usage, setUsage] = useState<UsageData | null>(null)
    const [cooldownUntil, setCooldownUntil] = useState<number | null>(null)
    const [cooldownSecsLeft, setCooldownSecsLeft] = useState(0)

    useEffect(() => {
        const t = setInterval(() => setCurrentTime(new Date()), 1000)
        return () => clearInterval(t)
    }, [])

    // Countdown ticker for free-tier cooldown
    useEffect(() => {
        if (!cooldownUntil) return
        const tick = setInterval(() => {
            const left = Math.ceil((cooldownUntil - Date.now()) / 1000)
            if (left <= 0) {
                setCooldownSecsLeft(0)
                setCooldownUntil(null)
            } else {
                setCooldownSecsLeft(left)
            }
        }, 250)
        return () => clearInterval(tick)
    }, [cooldownUntil])

    useEffect(() => {
        api.get<UsageData>('/ai/usage').then(r => setUsage(r.data)).catch(() => { })
        // Auto-fetch live market data on first load
        setFetching(true)
        api.get<Partial<MarketData>>('/ai/market-snapshot')
            .then(r => setData(d => ({ ...d, ...r.data })))
            .catch(() => { })
            .finally(() => setFetching(false))
    }, [])

    const IST = currentTime.toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
    })

    const today = currentTime.toLocaleDateString('en-IN', {
        timeZone: 'Asia/Kolkata',
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    })

    const handleChange = (key: keyof MarketData, val: string) => {
        setData((d) => ({ ...d, [key]: val }))
    }

    const fetchLiveData = async () => {
        setFetching(true)
        try {
            const res = await api.get<Partial<MarketData>>('/ai/market-snapshot')
            setData(d => ({ ...d, ...res.data }))
        } catch {
            // If live fetch fails, silently keep existing values
        } finally {
            setFetching(false)
        }
    }

    // Calls the backend proxy — API key never leaves the server; tier enforced server-side
    const analyzeWithAI = async () => {
        setLoading(true)
        setError('')
        setAiResponse('')
        setTokensUsed(null)

        try {
            const res = await api.post('/ai/nifty-analyze', {
                analysis_type: analysisType,
                market_data: { ...data, today, ist: IST },
            })
            const d2 = res.data
            setAiResponse(d2.text || 'No response.')

            const u = d2.usage || {}
            setTokensUsed({
                inputTokens: u.input_tokens || 0,
                outputTokens: u.output_tokens || 0,
                cacheReadTokens: u.cache_read_input_tokens || 0,
                cacheWriteTokens: u.cache_creation_input_tokens || 0,
                costInr: u.cost_inr || 0,
                cached: u.cached || false,
            })
            // Update usage counter without page reload
            if (d2.analyses_today !== undefined) {
                setUsage(prev => prev ? {
                    ...prev,
                    analyses_today: d2.analyses_today,
                    daily_limit: d2.daily_limit,
                    credits: d2.credits,
                } : prev)
            }
            // Activate cooldown timer (free/starter tier)
            if (d2.cooldown_seconds > 0) {
                setCooldownUntil(Date.now() + d2.cooldown_seconds * 1000)
            }
        } catch (e: any) {
            const detail = e?.response?.data?.detail || (e instanceof Error ? e.message : String(e))
            if (e?.response?.status === 402) {
                setError('⚡ ' + detail + ' Visit Billing to upgrade your plan.')
            } else if (e?.response?.status === 403) {
                setError('🔒 ' + detail)
            } else if (e?.response?.status === 429) {
                setError('⏳ ' + detail)
            } else {
                setError('Error: ' + detail)
            }
        } finally {
            setLoading(false)
        }
    }

    const fiiNum = parseFloat(data.fiiActivity)
    const vixNum = parseFloat(data.vix)
    const giftDiff = parseFloat(data.giftNifty) - parseFloat(data.niftyClose)
    const giftPct = ((giftDiff / parseFloat(data.niftyClose)) * 100).toFixed(2)
    const tierColor = usage?.tier === 'elite' ? YELLOW : usage?.tier === 'pro' ? PURPLE : usage?.tier === 'starter' ? BLUE : ACCENT
    const diiNum = parseFloat(data.diiActivity)

    return (
        <div style={{ minHeight: '100vh', background: BG, fontFamily: "'JetBrains Mono','Fira Code',monospace", color: '#e2e8f0' }}>
            <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');
        @keyframes spin  { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
        @keyframes glow  { 0%,100%{box-shadow:0 0 18px ${ACCENT}30} 50%{box-shadow:0 0 32px ${ACCENT}60,0 0 60px ${ACCENT}20} }
        @keyframes shimmer { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
        .ai-out { animation: fadeUp .45s ease; }
        .noa-spin { animation: spin .75s linear infinite; }
        .noa-input:focus { border-color: ${ACCENT}60 !important; box-shadow: 0 0 0 3px ${ACCENT}12 !important; }
        .noa-card-g  { background: linear-gradient(#080f1a,#080f1a) padding-box, linear-gradient(135deg,${ACCENT}35 0%,${BORDER} 50%,${ACCENT}10 100%) border-box; border:1px solid transparent; border-radius:14px; }
        .noa-card-p  { background: linear-gradient(#080f1a,#080f1a) padding-box, linear-gradient(135deg,${PURPLE}35 0%,${BORDER} 50%,${PURPLE}10 100%) border-box; border:1px solid transparent; border-radius:14px; }
        .noa-card-n  { background: linear-gradient(#080f1a,#080f1a) padding-box, linear-gradient(135deg,#1a2c3d50 0%,${BORDER} 100%) border-box; border:1px solid transparent; border-radius:14px; }
        .noa-btn-primary { background:linear-gradient(135deg,${ACCENT},#00c97a); color:#030810; border:none; border-radius:10px; font-family:inherit; font-weight:800; letter-spacing:.1em; cursor:pointer; text-transform:uppercase; transition:all .2s; display:flex; align-items:center; gap:8px; }
        .noa-btn-primary:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 8px 24px ${ACCENT}40; }
        .noa-btn-primary:disabled { opacity:.5; cursor:not-allowed; }
        .noa-btn-outline { background:transparent; border:1px solid ${ACCENT}40; color:${ACCENT}; border-radius:8px; font-family:inherit; font-weight:600; letter-spacing:.08em; cursor:pointer; text-transform:uppercase; transition:all .2s; }
        .noa-btn-outline:hover:not(:disabled) { background:${ACCENT}10; border-color:${ACCENT}80; }
        .noa-btn-outline:disabled { opacity:.4; cursor:not-allowed; }
        .noa-row:last-child { border-bottom:none !important; }
        .noa-pill { display:inline-flex; align-items:center; padding:3px 10px; border-radius:4px; font-size:10px; font-weight:700; letter-spacing:.08em; }
        .pulse-dot { width:7px; height:7px; border-radius:50%; background:${GREEN}; box-shadow:0 0 8px ${GREEN}; animation:pulse 1.8s infinite; }
        ::-webkit-scrollbar { width:5px; height:5px; }
        ::-webkit-scrollbar-track { background:${BG}; }
        ::-webkit-scrollbar-thumb { background:#1a2c3d; border-radius:3px; }
        .noa-type-btn { background:transparent; border:1px solid #1a2c3d; border-radius:8px; padding:10px 16px; font-family:inherit; font-size:11px; font-weight:600; letter-spacing:.08em; cursor:pointer; transition:all .2s; text-transform:uppercase; display:flex; flex-direction:column; align-items:center; gap:3px; }
        .noa-type-btn:disabled { opacity:.35; cursor:not-allowed; }
        .noa-data-row { display:flex; justify-content:space-between; align-items:center; padding:9px 0; border-bottom:1px solid ${BORDER}; }
        .noa-data-row:last-child { border-bottom:none; }
        .dot-grid { background-image: radial-gradient(rgba(0,255,157,.04) 1px,transparent 1px); background-size:22px 22px; }
      `}</style>

            {/* ── TOP STATUS BAR ─────────────────────────────────────────── */}
            <div style={{ background: '#020810', borderBottom: '1px solid #0a1624', padding: '5px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10px', letterSpacing: '0.08em' }}>
                <span style={{ color: '#233040' }}>QUANTLEAP FINANCIAL  ·  OPTIONS ANALYZER v2.0</span>
                <div style={{ display: 'flex', gap: '18px', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <div className="pulse-dot" />
                        <span style={{ color: '#475569' }}>IST {IST}</span>
                    </div>
                    <span style={{ color: '#233040' }}>{today}</span>
                    {usage && (
                        <>
                            <span style={{ color: tierColor, background: `${tierColor}15`, border: `1px solid ${tierColor}35`, padding: '1px 9px', borderRadius: '3px', fontWeight: '700' }}>
                                {usage.tier_label}
                            </span>
                            <span style={{ color: usage.analyses_today >= usage.daily_limit ? RED : '#475569' }}>
                                {usage.analyses_today}<span style={{ color: '#233040' }}>/{usage.daily_limit}</span>
                                <span style={{ color: '#233040' }}> analyses</span>
                            </span>
                            <span style={{ color: (usage.credits || 0) < 3 ? RED : '#475569' }}>
                                ⚡ <span style={{ color: (usage.credits || 0) < 3 ? RED : '#64748b', fontWeight: '700' }}>{usage.credits}</span> credits
                            </span>
                        </>
                    )}
                    <span style={{ color: GREEN, display: 'flex', gap: '4px', alignItems: 'center' }}>🔒 Secured</span>
                </div>
            </div>

            {/* ── MAIN HEADER ───────────────────────────────────────────── */}
            <div style={{ background: 'linear-gradient(180deg,#0a1625 0%,#060d14 100%)', borderBottom: `1px solid ${BORDER}`, padding: '20px 28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 50, backdropFilter: 'blur(16px)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    {/* Logo icon */}
                    <div style={{ width: '46px', height: '46px', background: `linear-gradient(135deg,${ACCENT},#00c47a)`, borderRadius: '11px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px', boxShadow: `0 0 28px ${ACCENT}45, 0 4px 12px #00000060`, flexShrink: 0 }}>⚡</div>
                    <div>
                        <div style={{ fontSize: '18px', fontWeight: '800', letterSpacing: '0.06em', color: '#f1f5f9', lineHeight: 1.1 }}>NIFTY OPTIONS ANALYZER</div>
                        <div style={{ fontSize: '10px', color: '#334155', letterSpacing: '0.2em', marginTop: '3px' }}>AI-POWERED INTRADAY ANALYSIS  ·  INDIAN DERIVATIVES</div>
                    </div>
                    <span style={{ background: `${ACCENT}15`, border: `1px solid ${ACCENT}40`, color: ACCENT, fontSize: '9px', padding: '4px 10px', borderRadius: '4px', letterSpacing: '0.2em', fontWeight: '700', alignSelf: 'center' }}>AI POWERED</span>
                </div>
                <button className="noa-btn-outline" style={{ padding: '8px 18px', fontSize: '11px' }} onClick={fetchLiveData} disabled={fetching}>
                    {fetching ? '⟳ Fetching...' : '⟳ Live Data'}
                </button>
            </div>

            {/* ── MARKET PULSE STRIP ────────────────────────────────────── */}
            <div style={{ background: '#040c14', borderBottom: '1px solid #0a1624', overflowX: 'auto' }}>
                <div style={{ display: 'flex', minWidth: 'max-content' }}>
                    {([
                        { label: 'NIFTY 50', val: formatNum(data.niftyClose), color: GREEN, sub: '' },
                        { label: 'BANK NIFTY', val: formatNum(data.bankniftyClose), color: PURPLE, sub: '' },
                        { label: 'GIFT NIFTY', val: formatNum(data.giftNifty), color: giftDiff >= 0 ? GREEN : RED, sub: `${giftDiff >= 0 ? '+' : ''}${giftPct}%` },
                        { label: 'INDIA VIX', val: data.vix, color: getVixColor(data.vix), sub: vixNum < 12 ? 'SELL OPT' : vixNum < 16 ? 'BALANCED' : 'BUY OPT' },
                        { label: 'FII NET', val: `₹${fiiNum >= 0 ? '+' : ''}${formatNum(data.fiiActivity)}Cr`, color: fiiNum >= 0 ? GREEN : RED, sub: fiiNum >= 0 ? '▲ BUYING' : '▼ SELLING' },
                        { label: 'DII NET', val: `₹${diiNum >= 0 ? '+' : ''}${formatNum(data.diiActivity)}Cr`, color: diiNum >= 0 ? GREEN : RED, sub: '' },
                        { label: 'WTI CRUDE', val: `$${data.crude}`, color: '#e2e8f0', sub: '/bbl' },
                        { label: 'DXY', val: data.dollarIndex, color: parseFloat(data.dollarIndex) > 104 ? RED : GREEN, sub: 'DOLLAR IDX' },
                        { label: 'S&P 500', val: `${parseFloat(data.usMarket) >= 0 ? '' : ''}${data.usMarket}%`, color: parseFloat(data.usMarket) >= 0 ? GREEN : RED, sub: 'OVERNIGHT' },
                    ] as Array<{ label: string; val: string; color: string; sub: string }>).map((item, i) => (
                        <div key={i} style={{ padding: '9px 22px', borderRight: '1px solid #0a1624', flexShrink: 0 }}>
                            <div style={{ fontSize: '8px', color: '#2d4258', letterSpacing: '0.2em', marginBottom: '3px' }}>{item.label}</div>
                            <div style={{ fontSize: '13px', fontWeight: '700', color: item.color, letterSpacing: '-0.01em' }}>{item.val}</div>
                            {item.sub && <div style={{ fontSize: '8px', color: item.color, opacity: 0.65, marginTop: '1px' }}>{item.sub}</div>}
                        </div>
                    ))}
                </div>
            </div>

            {/* ── PAGE BODY ─────────────────────────────────────────────── */}
            <div className="dot-grid" style={{ maxWidth: '1320px', margin: '0 auto', padding: '28px 24px' }}>

                {/* HOW-TO-USE banner */}
                <div style={{ background: `${ACCENT}07`, border: `1px solid ${ACCENT}20`, borderRadius: '10px', padding: '12px 18px', marginBottom: '22px', fontSize: '11px', color: '#64748b', lineHeight: '1.9', display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
                    <span style={{ color: ACCENT, fontSize: '16px', flexShrink: 0 }}>💡</span>
                    <div>
                        <span style={{ color: ACCENT, fontWeight: '700', letterSpacing: '.08em' }}>HOW TO USE —</span>{'  '}
                        Before 9:15 AM: verify <strong style={{ color: '#94a3b8' }}>Nifty / BankNifty prev close</strong>, <strong style={{ color: '#94a3b8' }}>Gift Nifty</strong>, <strong style={{ color: '#94a3b8' }}>India VIX</strong>, <strong style={{ color: '#94a3b8' }}>FII/DII</strong>, <strong style={{ color: '#94a3b8' }}>Crude</strong>, <strong style={{ color: '#94a3b8' }}>DXY</strong> from{' '}
                        <a href="https://www.nseindia.com" target="_blank" rel="noopener noreferrer" style={{ color: ACCENT }}>NSE</a> /{' '}
                        <a href="https://kite.zerodha.com" target="_blank" rel="noopener noreferrer" style={{ color: ACCENT }}>Zerodha</a> /{' '}
                        <a href="https://sensibull.com" target="_blank" rel="noopener noreferrer" style={{ color: ACCENT }}>Sensibull</a>.
                        {' '}Edit the fields below, choose <strong style={{ color: ACCENT }}>⚡ Quick</strong> or <strong style={{ color: ACCENT }}>📊 Full Report</strong>, then hit <strong style={{ color: GREEN }}>Analyze with AI</strong>.
                    </div>
                </div>

                {/* ── MARKET SNAPSHOT CARDS ─────────────────────────────── */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>

                    {/* Nifty 50 */}
                    <div className="noa-card-g" style={{ padding: '22px' }}>
                        <div style={{ fontSize: '9px', letterSpacing: '.22em', color: '#334155', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '7px' }}>
                            <span style={{ display: 'inline-block', width: '3px', height: '14px', background: `linear-gradient(${GREEN},#00c47a)`, borderRadius: '2px' }} />
                            NIFTY 50
                        </div>
                        <div style={{ fontSize: '34px', fontWeight: '800', color: GREEN, letterSpacing: '-0.02em', lineHeight: 1, textShadow: `0 0 24px ${GREEN}50` }}>{formatNum(data.niftyClose)}</div>
                        <div style={{ marginTop: '8px', marginBottom: '14px' }}>
                            <span className="noa-pill" style={{ background: `${GREEN}15`, color: GREEN }}>PREV CLOSE</span>
                        </div>
                        <div className="noa-data-row">
                            <span style={{ fontSize: '11px', color: '#475569' }}>Gift Nifty</span>
                            <span style={{ fontSize: '13px', fontWeight: '600', color: giftDiff >= 0 ? GREEN : RED }}>
                                {formatNum(data.giftNifty)} <span style={{ fontSize: '11px' }}>({giftDiff >= 0 ? '+' : ''}{giftPct}%)</span>
                            </span>
                        </div>
                        <div className="noa-data-row">
                            <span style={{ fontSize: '11px', color: '#475569' }}>Gap Open Signal</span>
                            <span className="noa-pill" style={{ background: giftDiff >= 0 ? `${GREEN}15` : `${RED}15`, color: giftDiff >= 0 ? GREEN : RED }}>
                                {giftDiff >= 0 ? '▲ GAP UP' : '▼ GAP DOWN'} ~{Math.abs(giftDiff).toFixed(0)} pts
                            </span>
                        </div>
                    </div>

                    {/* Bank Nifty */}
                    <div className="noa-card-p" style={{ padding: '22px' }}>
                        <div style={{ fontSize: '9px', letterSpacing: '.22em', color: '#334155', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '7px' }}>
                            <span style={{ display: 'inline-block', width: '3px', height: '14px', background: `linear-gradient(${PURPLE},#8b5cf6)`, borderRadius: '2px' }} />
                            BANK NIFTY
                        </div>
                        <div style={{ fontSize: '34px', fontWeight: '800', color: PURPLE, letterSpacing: '-0.02em', lineHeight: 1, textShadow: `0 0 24px ${PURPLE}40` }}>{formatNum(data.bankniftyClose)}</div>
                        <div style={{ marginTop: '8px', marginBottom: '14px' }}>
                            <span className="noa-pill" style={{ background: `${PURPLE}15`, color: PURPLE }}>PREV CLOSE</span>
                        </div>
                        <div className="noa-data-row">
                            <span style={{ fontSize: '11px', color: '#475569' }}>India VIX</span>
                            <span style={{ fontSize: '13px', fontWeight: '700', color: getVixColor(data.vix) }}>{data.vix}</span>
                        </div>
                        <div className="noa-data-row">
                            <span style={{ fontSize: '11px', color: '#475569' }}>VIX Signal</span>
                            <span className="noa-pill" style={{
                                background: vixNum < 12 ? `${GREEN}15` : vixNum < 16 ? `${YELLOW}15` : `${RED}15`,
                                color: getVixColor(data.vix),
                            }}>
                                {vixNum < 12 ? '✓ SELL OPTIONS' : vixNum < 16 ? '↔ BALANCED' : '⚡ BUY OPTIONS'}
                            </span>
                        </div>
                    </div>

                    {/* FII / DII */}
                    <div className="noa-card-n" style={{ padding: '22px' }}>
                        <div style={{ fontSize: '9px', letterSpacing: '.22em', color: '#334155', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '7px' }}>
                            <span style={{ display: 'inline-block', width: '3px', height: '14px', background: `linear-gradient(${YELLOW},#f59e0b)`, borderRadius: '2px' }} />
                            FII / DII ACTIVITY
                        </div>
                        <div className="noa-data-row" style={{ borderBottom: `1px solid ${BORDER}` }}>
                            <span style={{ fontSize: '11px', color: '#475569' }}>FII Net</span>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                <span style={{ fontSize: '13px', fontWeight: '700', color: fiiNum >= 0 ? GREEN : RED }}>₹{fiiNum >= 0 ? '+' : ''}{formatNum(data.fiiActivity)} Cr</span>
                                <span className="noa-pill" style={{ background: fiiNum >= 0 ? `${GREEN}12` : `${RED}12`, color: fiiNum >= 0 ? GREEN : RED }}>{fiiNum >= 0 ? 'BUYING' : 'SELLING'}</span>
                            </div>
                        </div>
                        <div className="noa-data-row">
                            <span style={{ fontSize: '11px', color: '#475569' }}>DII Net</span>
                            <span style={{ fontSize: '13px', fontWeight: '700', color: diiNum >= 0 ? GREEN : RED }}>₹{diiNum >= 0 ? '+' : ''}{formatNum(data.diiActivity)} Cr</span>
                        </div>
                        <div style={{ marginTop: '14px' }}>
                            <div style={{ fontSize: '9px', color: '#2d4258', letterSpacing: '.15em', marginBottom: '6px' }}>NET INSTITUTIONAL SENTIMENT</div>
                            <div style={{ height: '6px', borderRadius: '3px', background: '#0a1624', overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: fiiNum >= 0 ? '65%' : '35%', background: fiiNum >= 0 ? `linear-gradient(90deg,${GREEN},#00c47a)` : `linear-gradient(90deg,${RED},#ff6b6b)`, borderRadius: '3px', transition: 'width 1s ease' }} />
                            </div>
                        </div>
                    </div>

                    {/* Global Cues */}
                    <div className="noa-card-n" style={{ padding: '22px' }}>
                        <div style={{ fontSize: '9px', letterSpacing: '.22em', color: '#334155', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '7px' }}>
                            <span style={{ display: 'inline-block', width: '3px', height: '14px', background: `linear-gradient(${BLUE},#0ea5e9)`, borderRadius: '2px' }} />
                            GLOBAL CUES
                        </div>
                        <div className="noa-data-row" style={{ borderBottom: `1px solid ${BORDER}` }}>
                            <span style={{ fontSize: '11px', color: '#475569' }}>US Markets (O/N)</span>
                            <span style={{ fontSize: '13px', fontWeight: '700', color: parseFloat(data.usMarket) >= 0 ? GREEN : RED }}>{parseFloat(data.usMarket) >= 0 ? '+' : ''}{data.usMarket}%</span>
                        </div>
                        <div className="noa-data-row" style={{ borderBottom: `1px solid ${BORDER}` }}>
                            <span style={{ fontSize: '11px', color: '#475569' }}>Crude Oil (WTI)</span>
                            <span style={{ fontSize: '13px', fontWeight: '600', color: '#e2e8f0' }}>${data.crude}<span style={{ color: '#475569', fontSize: '10px' }}>/bbl</span></span>
                        </div>
                        <div className="noa-data-row" style={{ borderBottom: `1px solid ${BORDER}` }}>
                            <span style={{ fontSize: '11px', color: '#475569' }}>Dollar Index (DXY)</span>
                            <span style={{ fontSize: '13px', fontWeight: '700', color: parseFloat(data.dollarIndex) > 104 ? RED : GREEN }}>{data.dollarIndex}</span>
                        </div>
                        <div className="noa-data-row">
                            <span style={{ fontSize: '11px', color: '#475569' }}>Events Today</span>
                            <span style={{ fontSize: '11px', fontWeight: '600', color: YELLOW, maxWidth: '180px', textAlign: 'right' }}>{data.majorEvents}</span>
                        </div>
                    </div>
                </div>

                {/* ── EDIT MARKET DATA ──────────────────────────────────── */}
                <div className="noa-card-n" style={{ padding: '24px', marginBottom: '16px' }}>
                    {/* Section header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', paddingBottom: '14px', borderBottom: `1px solid ${BORDER}` }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{ fontSize: '14px' }}>⚙️</span>
                            <span style={{ fontSize: '11px', fontWeight: '700', color: '#94a3b8', letterSpacing: '.18em', textTransform: 'uppercase' }}>Edit Market Data</span>
                        </div>
                        <div style={{ fontSize: '10px', color: '#ffd16680', background: `${YELLOW}10`, border: `1px solid ${YELLOW}25`, borderRadius: '6px', padding: '5px 12px', lineHeight: 1.6 }}>
                            ⚠️ Verify with{' '}
                            <a href="https://www.nseindia.com" target="_blank" rel="noopener noreferrer" style={{ color: YELLOW }}>NSE</a> /{' '}
                            <a href="https://kite.zerodha.com" target="_blank" rel="noopener noreferrer" style={{ color: YELLOW }}>Zerodha</a> before trading
                        </div>
                    </div>

                    {/* Numeric inputs */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '14px', marginBottom: '14px' }}>
                        {([
                            { key: 'niftyClose', label: 'Nifty Prev Close', hint: 'From NSE / Zerodha' },
                            { key: 'bankniftyClose', label: 'Bank Nifty Prev Close', hint: 'From NSE / Zerodha' },
                            { key: 'giftNifty', label: 'Gift Nifty', hint: 'Pre-market from NSE Indices' },
                            { key: 'vix', label: 'India VIX', hint: 'From NSE VIX page' },
                            { key: 'fiiActivity', label: 'FII Activity (₹ Cr)', hint: 'Negative = selling' },
                            { key: 'diiActivity', label: 'DII Activity (₹ Cr)', hint: 'Positive = buying' },
                            { key: 'crude', label: 'Crude Oil ($)', hint: 'WTI from investing.com' },
                            { key: 'dollarIndex', label: 'Dollar Index (DXY)', hint: 'From investing.com' },
                        ] as Array<{ key: keyof MarketData; label: string; hint: string }>).map(({ key, label, hint }) => (
                            <div key={key}>
                                <label style={S.label} title={hint}>{label}</label>
                                <input className="noa-input" style={S.input} value={data[key]} onChange={e => handleChange(key, e.target.value)} placeholder={hint} />
                            </div>
                        ))}
                    </div>

                    {/* Text / select row */}
                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: '14px' }}>
                        <div>
                            <label style={S.label}>Major Events / News Today</label>
                            <input className="noa-input" style={S.input} value={data.majorEvents} onChange={e => handleChange('majorEvents', e.target.value)} placeholder="e.g., RBI Policy, Weekly Expiry, Q3 Results..." />
                        </div>
                        <div>
                            <label style={S.label}>US Markets % Change</label>
                            <input className="noa-input" style={S.input} value={data.usMarket} onChange={e => handleChange('usMarket', e.target.value)} placeholder="+0.5 or -1.2" />
                        </div>
                        <div>
                            <label style={S.label}>Max Risk % / Trade</label>
                            <input className="noa-input" style={S.input} value={data.capitalRisk} onChange={e => handleChange('capitalRisk', e.target.value)} placeholder="2" />
                        </div>
                        <div>
                            <label style={S.label}>Trader Level</label>
                            <select className="noa-input" style={S.select} value={data.traderExperience} onChange={e => handleChange('traderExperience', e.target.value)}>
                                <option>Beginner</option>
                                <option>Intermediate</option>
                                <option>Advanced</option>
                                <option>Expert</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* ── ANALYSIS CONTROLS ─────────────────────────────────── */}
                <div className="noa-card-n" style={{ padding: '24px', marginBottom: '16px' }}>
                    <div style={{ fontSize: '9px', letterSpacing: '.22em', color: '#334155', marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '7px' }}>
                        <span style={{ display: 'inline-block', width: '3px', height: '14px', background: `linear-gradient(${ACCENT},#00c47a)`, borderRadius: '2px' }} />
                        ANALYSIS TYPE
                    </div>

                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                        {/* Quick */}
                        <button
                            className="noa-type-btn"
                            onClick={() => setAnalysisType('quick')}
                            style={{
                                color: analysisType === 'quick' ? ACCENT : '#475569',
                                borderColor: analysisType === 'quick' ? `${ACCENT}60` : BORDER,
                                background: analysisType === 'quick' ? `${ACCENT}10` : 'transparent',
                                minWidth: '120px',
                            }}
                            title="Fast 150-word market summary"
                        >
                            <span style={{ fontSize: '18px' }}>⚡</span>
                            <span>Quick</span>
                            <span style={{ fontSize: '9px', color: analysisType === 'quick' ? `${ACCENT}80` : '#2d4258' }}>150-word summary</span>
                        </button>

                        {/* Full Report */}
                        {(() => {
                            const locked = usage !== null && !usage?.allowed_types?.includes('full')
                            return (
                                <button
                                    className="noa-type-btn"
                                    onClick={() => !locked && setAnalysisType('full')}
                                    disabled={locked}
                                    style={{
                                        color: locked ? '#2d4258' : analysisType === 'full' ? ACCENT : '#475569',
                                        borderColor: locked ? BORDER : analysisType === 'full' ? `${ACCENT}60` : BORDER,
                                        background: analysisType === 'full' ? `${ACCENT}10` : 'transparent',
                                        minWidth: '120px',
                                    }}
                                    title={locked ? '🔒 Pro plan required' : 'Full 7-section trade plan'}
                                >
                                    <span style={{ fontSize: '18px' }}>{locked ? '🔒' : '📊'}</span>
                                    <span>Full Report</span>
                                    <span style={{ fontSize: '9px', color: locked ? '#1e2c3a' : analysisType === 'full' ? `${ACCENT}80` : '#2d4258' }}>{locked ? 'Pro plan' : '7-section plan'}</span>
                                </button>
                            )
                        })()}

                        {/* Advanced — elite only */}
                        {usage?.allowed_types?.includes('advanced') && (
                            <button
                                className="noa-type-btn"
                                onClick={() => setAnalysisType('advanced')}
                                style={{
                                    color: analysisType === 'advanced' ? YELLOW : '#475569',
                                    borderColor: analysisType === 'advanced' ? `${YELLOW}60` : BORDER,
                                    background: analysisType === 'advanced' ? `${YELLOW}10` : 'transparent',
                                    minWidth: '120px',
                                }}
                                title="Advanced deep-dive analysis (Elite)"
                            >
                                <span style={{ fontSize: '18px' }}>🔬</span>
                                <span>Advanced</span>
                                <span style={{ fontSize: '9px', color: analysisType === 'advanced' ? `${YELLOW}80` : '#2d4258' }}>Elite only</span>
                            </button>
                        )}

                        {/* Divider + session selector */}
                        <div style={{ marginLeft: '8px', paddingLeft: '18px', borderLeft: `1px solid ${BORDER}`, alignSelf: 'stretch', display: 'flex', alignItems: 'center' }}>
                            <div>
                                <label style={S.label}>Session</label>
                                <select className="noa-input" style={{ ...S.select, width: '130px' }} value={data.sessionType} onChange={e => handleChange('sessionType', e.target.value)}>
                                    <option>Intraday</option>
                                    <option>Positional</option>
                                    <option>Expiry Day</option>
                                </select>
                            </div>
                        </div>

                        {/* Analyze button */}
                        <div style={{ marginLeft: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                            {cooldownSecsLeft > 0 && (
                                <div style={{ fontSize: '10px', color: YELLOW, display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <span style={{ animation: 'pulse 1s infinite' }}>⏳</span>
                                    Next analysis in <strong>{cooldownSecsLeft}s</strong>
                                    {usage && <span style={{ color: '#334155' }}> · Free tier cooldown</span>}
                                </div>
                            )}
                            <button
                                className="noa-btn-primary"
                                style={{ padding: '14px 36px', fontSize: '13px', letterSpacing: '0.12em', boxShadow: loading || cooldownSecsLeft > 0 ? 'none' : `0 0 28px ${ACCENT}30, 0 4px 16px #00000050` }}
                                onClick={analyzeWithAI}
                                disabled={loading || cooldownSecsLeft > 0}
                            >
                                {loading ? (
                                    <>
                                        <span className="noa-spin" style={{ display: 'inline-block', width: '15px', height: '15px', border: `2px solid #03100a50`, borderTop: `2px solid #030810`, borderRadius: '50%' }} />
                                        Analyzing Market...
                                    </>
                                ) : cooldownSecsLeft > 0 ? (
                                    <>⏳ Wait {cooldownSecsLeft}s</>
                                ) : (
                                    <><span>🤖</span> Analyze with AI</>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* ── AI RESPONSE ───────────────────────────────────────── */}
                {(aiResponse || loading || error) && (
                    <div className="noa-card-g" style={{ padding: '0', marginBottom: '16px', overflow: 'hidden' }}>
                        {/* Response header bar */}
                        <div style={{ padding: '14px 22px', borderBottom: `1px solid ${BORDER}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#060e17' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <span style={{ fontSize: '15px' }}>🤖</span>
                                <span style={{ fontSize: '11px', fontWeight: '700', color: '#94a3b8', letterSpacing: '.15em' }}>AI INTRADAY ANALYSIS</span>
                                {analysisType && (
                                    <span className="noa-pill" style={{ background: `${ACCENT}15`, color: ACCENT }}>
                                        {analysisType === 'quick' ? '⚡ QUICK' : analysisType === 'full' ? '📊 FULL REPORT' : '🔬 ADVANCED'}
                                    </span>
                                )}
                            </div>
                            {aiResponse && (
                                <div style={{ display: 'flex', gap: '8px' }}>
                                    <button className="noa-btn-outline" style={{ padding: '5px 14px', fontSize: '10px' }} onClick={() => navigator.clipboard.writeText(aiResponse)}>
                                        📋 Copy
                                    </button>
                                    <button className="noa-btn-outline" style={{ padding: '5px 14px', fontSize: '10px', borderColor: `${RED}40`, color: RED }} onClick={() => { setAiResponse(''); setTokensUsed(null) }}>
                                        ✕ Clear
                                    </button>
                                </div>
                            )}
                        </div>

                        <div style={{ padding: '22px' }}>
                            {loading && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: ACCENT, fontSize: '13px' }}>
                                    <span className="noa-spin" style={{ display: 'inline-block', width: '18px', height: '18px', border: `2px solid ${ACCENT}25`, borderTop: `2px solid ${ACCENT}`, borderRadius: '50%' }} />
                                    <span>Analyzing market conditions with AI</span>
                                    <span style={{ color: '#2d4258', animation: 'pulse 1.5s infinite' }}>●●●</span>
                                </div>
                            )}
                            {error && (
                                <div style={{ color: RED, fontSize: '13px', padding: '12px 16px', background: `${RED}08`, borderRadius: '8px', border: `1px solid ${RED}25`, lineHeight: 1.7 }}>
                                    ⚠️ {error}
                                </div>
                            )}
                            {aiResponse && (
                                <div className="ai-out" style={{ background: '#040c14', border: `1px solid ${BORDER}`, borderRadius: '10px', padding: '22px', fontSize: '13px', lineHeight: '1.85', color: '#cbd5e1' }}>
                                    {renderMarkdown(aiResponse)}
                                </div>
                            )}

                            {/* Token usage chip */}
                            {aiResponse && tokensUsed && (
                                <div style={{ marginTop: '14px', padding: '10px 16px', background: '#020810', border: `1px solid ${BORDER}`, borderRadius: '8px', display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '10px', color: '#334155', alignItems: 'center', letterSpacing: '.04em' }}>
                                    <span style={{ color: ACCENT, fontWeight: '700' }}>📊 USAGE</span>
                                    <span>In <strong style={{ color: '#64748b' }}>{tokensUsed.inputTokens.toLocaleString()}</strong></span>
                                    <span>Out <strong style={{ color: '#64748b' }}>{tokensUsed.outputTokens.toLocaleString()}</strong></span>
                                    {tokensUsed.cacheReadTokens > 0 && (
                                        <span style={{ color: GREEN }}>⚡ Cache hit <strong>{tokensUsed.cacheReadTokens.toLocaleString()}</strong> tokens</span>
                                    )}
                                    {tokensUsed.cacheWriteTokens > 0 && (
                                        <span style={{ color: YELLOW }}>💾 Wrote <strong>{tokensUsed.cacheWriteTokens.toLocaleString()}</strong></span>
                                    )}
                                    <span style={{ marginLeft: 'auto', color: GREEN, fontWeight: '700' }}>~₹{tokensUsed.costInr.toFixed(3)}</span>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* ── DISCLAIMER ────────────────────────────────────────── */}
                <div style={{ textAlign: 'center', padding: '18px', fontSize: '10px', color: '#c05a4580', letterSpacing: '.05em', lineHeight: '1.9' }}>
                    ⚠️ DISCLAIMER: This tool is for EDUCATIONAL purposes only. Not SEBI registered financial advice.
                    <br />
                    Options trading involves significant risk of loss. Always verify data and use proper risk management before trading.
                </div>
            </div>
        </div>
    )
}
