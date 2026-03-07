import { useState, useEffect } from 'react'

const ACCENT = '#00ff9d'
const BG = '#0a0e1a'
const CARD = '#111827'
const BORDER = '#1e2d40'
const RED = '#ff4d6d'
const GREEN = '#00ff9d'
const YELLOW = '#ffd166'

// ── Model & pricing constants ──────────────────────────────────────────────
const MODEL_QUICK = 'claude-haiku-4-5-20251001'   // $1 / $5 per MTok
const MODEL_FULL = 'claude-sonnet-4-6'           // $3 / $15 per MTok
// Cache reads: $0.30/MTok — 90% saving on the repeated system prompt
const PRICE: Record<string, { input: number; output: number; cacheRead: number }> = {
    [MODEL_QUICK]: { input: 1.0, output: 5.0, cacheRead: 0.10 },
    [MODEL_FULL]: { input: 3.0, output: 15.0, cacheRead: 0.30 },
}
const USD_TO_INR = 84

interface TokenUsage {
    inputTokens: number
    outputTokens: number
    cacheReadTokens: number
    cacheWriteTokens: number
    estimatedCostUSD: number
    model: string
}

// ────────────────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
    app: {
        minHeight: '100vh',
        background: BG,
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        color: '#e2e8f0',
        padding: '0',
    },
    header: {
        background: 'linear-gradient(135deg, #0d1b2a 0%, #0a0e1a 100%)',
        borderBottom: `1px solid ${BORDER}`,
        padding: '18px 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        backdropFilter: 'blur(12px)',
    },
    logo: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        fontSize: '18px',
        fontWeight: '700',
        letterSpacing: '0.05em',
        color: ACCENT,
    },
    badge: {
        background: `${ACCENT}20`,
        border: `1px solid ${ACCENT}60`,
        color: ACCENT,
        fontSize: '10px',
        padding: '2px 8px',
        borderRadius: '4px',
        letterSpacing: '0.15em',
    },
    liveIndicator: {
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        fontSize: '11px',
        color: '#64748b',
    },
    liveDot: {
        width: '7px',
        height: '7px',
        borderRadius: '50%',
        background: GREEN,
        boxShadow: `0 0 8px ${GREEN}`,
    },
    main: {
        maxWidth: '1280px',
        margin: '0 auto',
        padding: '28px 24px',
    },
    grid: {
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '16px',
        marginBottom: '20px',
    },
    card: {
        background: CARD,
        border: `1px solid ${BORDER}`,
        borderRadius: '12px',
        padding: '20px',
        position: 'relative',
        overflow: 'hidden',
    },
    cardTitle: {
        fontSize: '10px',
        letterSpacing: '0.2em',
        color: '#475569',
        marginBottom: '14px',
        textTransform: 'uppercase',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
    },
    dataRow: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 0',
        borderBottom: `1px solid ${BORDER}`,
    },
    label: {
        fontSize: '11px',
        color: '#64748b',
    },
    value: {
        fontSize: '13px',
        fontWeight: '600',
        color: '#e2e8f0',
    },
    valueGreen: { color: GREEN, fontWeight: '700' },
    valueRed: { color: RED, fontWeight: '700' },
    valueYellow: { color: YELLOW, fontWeight: '700' },
    bigNumber: {
        fontSize: '28px',
        fontWeight: '800',
        letterSpacing: '-0.02em',
        lineHeight: 1,
        marginBottom: '4px',
    },
    changeTag: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        fontSize: '12px',
        padding: '2px 8px',
        borderRadius: '4px',
        fontWeight: '600',
    },
    inputGroup: {
        marginBottom: '12px',
    },
    inputLabel: {
        fontSize: '10px',
        color: '#475569',
        letterSpacing: '0.12em',
        marginBottom: '5px',
        display: 'block',
        textTransform: 'uppercase',
    } as React.CSSProperties,
    input: {
        width: '100%',
        background: '#0d1b2a',
        border: `1px solid ${BORDER}`,
        borderRadius: '6px',
        padding: '8px 12px',
        color: '#e2e8f0',
        fontSize: '12px',
        fontFamily: 'inherit',
        outline: 'none',
        boxSizing: 'border-box',
        transition: 'border-color 0.2s',
    } as React.CSSProperties,
    select: {
        width: '100%',
        background: '#0d1b2a',
        border: `1px solid ${BORDER}`,
        borderRadius: '6px',
        padding: '8px 12px',
        color: '#e2e8f0',
        fontSize: '12px',
        fontFamily: 'inherit',
        outline: 'none',
        boxSizing: 'border-box',
    } as React.CSSProperties,
    btn: {
        background: `linear-gradient(135deg, ${ACCENT}, #00c97a)`,
        color: '#0a0e1a',
        border: 'none',
        borderRadius: '8px',
        padding: '12px 28px',
        fontSize: '12px',
        fontWeight: '800',
        fontFamily: 'inherit',
        letterSpacing: '0.1em',
        cursor: 'pointer',
        textTransform: 'uppercase',
        transition: 'all 0.2s',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
    } as React.CSSProperties,
    btnSecondary: {
        background: 'transparent',
        color: ACCENT,
        border: `1px solid ${ACCENT}50`,
        borderRadius: '8px',
        padding: '10px 20px',
        fontSize: '11px',
        fontWeight: '600',
        fontFamily: 'inherit',
        letterSpacing: '0.08em',
        cursor: 'pointer',
        textTransform: 'uppercase',
        transition: 'all 0.2s',
    } as React.CSSProperties,
    aiResponse: {
        background: '#0d1b2a',
        border: `1px solid ${ACCENT}30`,
        borderRadius: '10px',
        padding: '20px',
        fontSize: '13px',
        lineHeight: '1.8',
        color: '#cbd5e1',
        minHeight: '100px',
        position: 'relative',
    },
    loading: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        color: ACCENT,
        fontSize: '13px',
    },
    spinner: {
        width: '16px',
        height: '16px',
        border: `2px solid ${ACCENT}30`,
        borderTop: `2px solid ${ACCENT}`,
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
    },
    sentimentBar: {
        height: '6px',
        borderRadius: '3px',
        background: '#1e2d40',
        marginTop: '10px',
        overflow: 'hidden',
    },
    sectionTitle: {
        fontSize: '12px',
        letterSpacing: '0.15em',
        color: ACCENT,
        textTransform: 'uppercase',
        marginBottom: '16px',
        paddingBottom: '8px',
        borderBottom: `1px solid ${BORDER}`,
        fontWeight: '700',
    } as React.CSSProperties,
    tag: {
        display: 'inline-flex',
        padding: '3px 10px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: '700',
        letterSpacing: '0.08em',
    },
    alertBox: {
        background: `${YELLOW}10`,
        border: `1px solid ${YELLOW}40`,
        borderRadius: '8px',
        padding: '10px 14px',
        fontSize: '11px',
        color: YELLOW,
        marginBottom: '14px',
        lineHeight: '1.6',
    },
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
    const [analysisType, setAnalysisType] = useState<'quick' | 'full'>('full')
    const [tokensUsed, setTokensUsed] = useState<TokenUsage | null>(null)

    useEffect(() => {
        const t = setInterval(() => setCurrentTime(new Date()), 1000)
        return () => clearInterval(t)
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
        await new Promise((r) => setTimeout(r, 1800))
        setData((d) => ({
            ...d,
            niftyClose: '24765.90',
            bankniftyClose: '59055.85',
            giftNifty: (24765 + Math.floor(Math.random() * 120 - 60)).toString(),
            vix: (13 + Math.random() * 2).toFixed(2),
        }))
        setFetching(false)
    }

    // Calls the backend proxy — the API key never leaves the server
    const analyzeWithAI = async () => {
        setLoading(true)
        setError('')
        setAiResponse('')
        setTokensUsed(null)

        try {
            const response = await fetch('/api/ai/nifty-analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    analysis_type: analysisType,
                    market_data: {
                        ...data,
                        today,
                        ist: IST,
                    },
                }),
            })

            const res = await response.json()
            if (!response.ok) {
                throw new Error(res.detail || `Server error ${response.status}`)
            }

            setAiResponse(res.text || 'No response.')

            // ── Token & cost tracking ────────────────────────────
            const model = res.model as string
            const u = res.usage || {}
            const inp = u.input_tokens || 0
            const out = u.output_tokens || 0
            const cRead = u.cache_read_input_tokens || 0
            const cWrite = u.cache_creation_input_tokens || 0
            const p = PRICE[model] ?? PRICE['claude-sonnet-4-6']
            const costUSD =
                ((inp - cRead) / 1_000_000) * p.input +
                (cRead / 1_000_000) * p.cacheRead +
                (out / 1_000_000) * p.output
            setTokensUsed({
                inputTokens: inp, outputTokens: out,
                cacheReadTokens: cRead, cacheWriteTokens: cWrite,
                estimatedCostUSD: costUSD, model
            })
        } catch (e: unknown) {
            setError('Error: ' + (e instanceof Error ? e.message : String(e)))
        } finally {
            setLoading(false)
        }
    }

    const fiiNum = parseFloat(data.fiiActivity)
    const vixNum = parseFloat(data.vix)
    const giftDiff = parseFloat(data.giftNifty) - parseFloat(data.niftyClose)
    const giftPct = ((giftDiff / parseFloat(data.niftyClose)) * 100).toFixed(2)

    return (
        <div style={styles.app}>
            <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes spin { to{transform:rotate(360deg)} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        .noa-pulse { animation: pulse 1.5s infinite; }
        .noa-spin { animation: spin 0.8s linear infinite; }
        .ai-out { animation: fadeIn 0.5s ease; }
        .noa-input:focus { border-color: #00ff9d60 !important; box-shadow: 0 0 0 2px #00ff9d15; }
        .noa-btn:hover { opacity: 0.88; transform: translateY(-1px); }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0a0e1a; }
        ::-webkit-scrollbar-thumb { background: #1e2d40; border-radius: 3px; }
      `}</style>

            {/* HEADER */}
            <div style={styles.header}>
                <div style={styles.logo}>
                    <span>⚡</span>
                    <span>NIFTY OPTIONS ANALYZER</span>
                    <span style={styles.badge}>AI POWERED</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <div style={styles.liveIndicator}>
                        <div style={{ ...styles.liveDot, animation: 'pulse 1.5s infinite' }} />
                        <span>IST {IST}</span>
                    </div>
                    <div style={{ fontSize: '10px', color: '#334155', letterSpacing: '0.05em' }}>
                        {today}
                    </div>
                    {/* API Secured indicator */}
                    <div style={{ fontSize: '10px', color: '#00ff9d', display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <span>🔒</span><span>API Secured</span>
                    </div>
                </div>
            </div>



            <div style={styles.main}>

                {/* HOW TO USE — daily guide */}
                <div style={{
                    ...styles.alertBox,
                    background: `${ACCENT}08`,
                    border: `1px solid ${ACCENT}30`,
                    color: '#94a3b8',
                    marginBottom: '20px',
                    fontSize: '12px',
                    lineHeight: '1.8',
                }}>
                    <strong style={{ color: ACCENT }}>HOW TO USE EACH MORNING (before 9:15 AM):</strong>
                    <br />
                    1. Update the fields below with live data from NSE / Zerodha / Sensibull
                    <br />
                    2. Fill: Nifty &amp; Bank Nifty prev close, Gift Nifty, India VIX, FII/DII activity, Crude, Dollar Index
                    <br />
                    3. Add any major events (expiry, RBI meeting, key results) in the Events field
                    <br />
                    4. Choose <strong style={{ color: ACCENT }}>⚡ Quick</strong> (fast 150-word idea) or <strong style={{ color: ACCENT }}>📊 Full Report</strong> (complete strategy)
                    <br />
                    5. Hit <strong style={{ color: GREEN }}>Analyze with AI</strong> → get your trade plan instantly
                </div>

                {/* MARKET SNAPSHOT */}
                <div style={styles.grid}>
                    {/* Nifty Card */}
                    <div style={{ ...styles.card, borderColor: `${GREEN}30` }}>
                        <div style={styles.cardTitle}>
                            <span style={{ color: GREEN }}>▲</span> NIFTY 50
                        </div>
                        <div style={{ ...styles.bigNumber, color: GREEN }}>{formatNum(data.niftyClose)}</div>
                        <div style={{ display: 'flex', gap: '8px', marginTop: '8px', marginBottom: '12px' }}>
                            <span style={{ ...styles.changeTag, background: `${GREEN}15`, color: GREEN }}>▲ PREV CLOSE</span>
                        </div>
                        <div style={styles.dataRow}>
                            <span style={styles.label}>Gift Nifty</span>
                            <span style={{ ...styles.value, color: giftDiff >= 0 ? GREEN : RED }}>
                                {formatNum(data.giftNifty)} ({giftDiff >= 0 ? '+' : ''}{giftPct}%)
                            </span>
                        </div>
                        <div style={styles.dataRow}>
                            <span style={styles.label}>Gap Open Expected</span>
                            <span style={{ ...styles.value, color: giftDiff >= 0 ? GREEN : RED }}>
                                {giftDiff >= 0 ? '▲ GAP UP' : '▼ GAP DOWN'} ~{Math.abs(giftDiff).toFixed(0)} pts
                            </span>
                        </div>
                    </div>

                    {/* BankNifty Card */}
                    <div style={{ ...styles.card, borderColor: '#a78bfa30' }}>
                        <div style={styles.cardTitle}>
                            <span style={{ color: '#a78bfa' }}>▲</span> BANK NIFTY
                        </div>
                        <div style={{ ...styles.bigNumber, color: '#a78bfa' }}>{formatNum(data.bankniftyClose)}</div>
                        <div style={{ display: 'flex', gap: '8px', marginTop: '8px', marginBottom: '12px' }}>
                            <span style={{ ...styles.changeTag, background: '#a78bfa15', color: '#a78bfa' }}>▲ PREV CLOSE</span>
                        </div>
                        <div style={styles.dataRow}>
                            <span style={styles.label}>India VIX</span>
                            <span style={{ ...styles.value, color: getVixColor(data.vix) }}>{data.vix}</span>
                        </div>
                        <div style={styles.dataRow}>
                            <span style={styles.label}>VIX Signal</span>
                            <span style={{
                                ...styles.tag,
                                background: vixNum < 12 ? `${GREEN}15` : vixNum < 16 ? `${YELLOW}15` : `${RED}15`,
                                color: getVixColor(data.vix),
                                fontSize: '10px',
                            }}>
                                {vixNum < 12 ? '✓ SELL OPTIONS' : vixNum < 16 ? '↔ BALANCED' : '⚡ BUY OPTIONS'}
                            </span>
                        </div>
                    </div>

                    {/* FII/DII Card */}
                    <div style={styles.card}>
                        <div style={styles.cardTitle}>🏦 FII / DII ACTIVITY</div>
                        <div style={styles.dataRow}>
                            <span style={styles.label}>FII Net</span>
                            <div>
                                <span style={{ ...styles.value, color: fiiNum >= 0 ? GREEN : RED }}>
                                    ₹{fiiNum >= 0 ? '+' : ''}{formatNum(data.fiiActivity)} Cr
                                </span>
                                <span style={{
                                    ...styles.tag, marginLeft: '8px', fontSize: '9px',
                                    background: fiiNum >= 0 ? `${GREEN}15` : `${RED}15`,
                                    color: fiiNum >= 0 ? GREEN : RED,
                                }}>
                                    {fiiNum >= 0 ? 'BUYING' : 'SELLING'}
                                </span>
                            </div>
                        </div>
                        <div style={styles.dataRow}>
                            <span style={styles.label}>DII Net</span>
                            <span style={{ ...styles.value, color: parseFloat(data.diiActivity) >= 0 ? GREEN : RED }}>
                                ₹{parseFloat(data.diiActivity) >= 0 ? '+' : ''}{formatNum(data.diiActivity)} Cr
                            </span>
                        </div>
                        <div style={{ marginTop: '10px' }}>
                            <div style={{ fontSize: '10px', color: '#475569', marginBottom: '5px' }}>NET SENTIMENT</div>
                            <div style={styles.sentimentBar}>
                                <div style={{
                                    height: '100%',
                                    width: fiiNum >= 0 ? '65%' : '35%',
                                    background: fiiNum >= 0
                                        ? `linear-gradient(90deg, ${GREEN}, #00c97a)`
                                        : `linear-gradient(90deg, ${RED}, #ff6b6b)`,
                                    borderRadius: '3px',
                                    transition: 'width 0.8s ease',
                                }} />
                            </div>
                        </div>
                    </div>

                    {/* Global Cues */}
                    <div style={styles.card}>
                        <div style={styles.cardTitle}>🌍 GLOBAL CUES</div>
                        <div style={styles.dataRow}>
                            <span style={styles.label}>US Markets</span>
                            <span style={{ ...styles.value, color: parseFloat(data.usMarket) >= 0 ? GREEN : RED }}>
                                {parseFloat(data.usMarket) >= 0 ? '+' : ''}{data.usMarket}%
                            </span>
                        </div>
                        <div style={styles.dataRow}>
                            <span style={styles.label}>Crude Oil (WTI)</span>
                            <span style={styles.value}>${data.crude}/bbl</span>
                        </div>
                        <div style={styles.dataRow}>
                            <span style={styles.label}>Dollar Index (DXY)</span>
                            <span style={{ ...styles.value, color: parseFloat(data.dollarIndex) > 104 ? RED : GREEN }}>
                                {data.dollarIndex}
                            </span>
                        </div>
                        <div style={styles.dataRow}>
                            <span style={styles.label}>Events Today</span>
                            <span style={{ ...styles.value, fontSize: '11px', color: YELLOW }}>{data.majorEvents}</span>
                        </div>
                    </div>
                </div>

                {/* MANUAL INPUT SECTION */}
                <div style={styles.card}>
                    <div style={styles.sectionTitle}>⚙️ EDIT MARKET DATA</div>
                    <div style={styles.alertBox}>
                        ⚠️ Auto-fetch shows estimated/placeholder data. Please verify with{' '}
                        <a href="https://www.nseindia.com" target="_blank" rel="noopener noreferrer"
                            style={{ color: YELLOW, textDecoration: 'underline' }}>NSE</a>{' '}
                        /{' '}
                        <a href="https://kite.zerodha.com" target="_blank" rel="noopener noreferrer"
                            style={{ color: YELLOW, textDecoration: 'underline' }}>Zerodha</a>{' '}
                        /{' '}
                        <a href="https://sensibull.com" target="_blank" rel="noopener noreferrer"
                            style={{ color: YELLOW, textDecoration: 'underline' }}>Sensibull</a>{' '}
                        before trading. Edit fields below to match live market.
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                        {([
                            { key: 'niftyClose', label: 'Nifty Prev Close', hint: 'From NSE or Zerodha' },
                            { key: 'bankniftyClose', label: 'Bank Nifty Prev Close', hint: 'From NSE or Zerodha' },
                            { key: 'giftNifty', label: 'Gift Nifty', hint: 'Pre-market from NSE Indices' },
                            { key: 'vix', label: 'India VIX', hint: 'From NSE VIX page' },
                            { key: 'fiiActivity', label: 'FII Activity (₹ Cr)', hint: 'Negative = selling, from NSE FII/DII page' },
                            { key: 'diiActivity', label: 'DII Activity (₹ Cr)', hint: 'Positive = buying' },
                            { key: 'crude', label: 'Crude Oil ($)', hint: 'WTI from investing.com' },
                            { key: 'dollarIndex', label: 'Dollar Index (DXY)', hint: 'From investing.com' },
                        ] as Array<{ key: keyof MarketData; label: string; hint: string }>).map(({ key, label, hint }) => (
                            <div key={key} style={styles.inputGroup}>
                                <label style={styles.inputLabel} title={hint}>{label}</label>
                                <input
                                    className="noa-input"
                                    style={styles.input}
                                    value={data[key]}
                                    onChange={(e) => handleChange(key, e.target.value)}
                                    placeholder={hint}
                                />
                            </div>
                        ))}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: '12px' }}>
                        <div style={styles.inputGroup}>
                            <label style={styles.inputLabel}>Major Events / News Today</label>
                            <input
                                className="noa-input"
                                style={styles.input}
                                value={data.majorEvents}
                                onChange={(e) => handleChange('majorEvents', e.target.value)}
                                placeholder="e.g., RBI Policy, Q3 Results, Weekly Expiry..."
                            />
                        </div>
                        <div style={styles.inputGroup}>
                            <label style={styles.inputLabel}>US Markets % Change</label>
                            <input
                                className="noa-input"
                                style={styles.input}
                                value={data.usMarket}
                                onChange={(e) => handleChange('usMarket', e.target.value)}
                                placeholder="+0.5 or -1.2"
                            />
                        </div>
                        <div style={styles.inputGroup}>
                            <label style={styles.inputLabel}>Max Risk % / Trade</label>
                            <input
                                className="noa-input"
                                style={styles.input}
                                value={data.capitalRisk}
                                onChange={(e) => handleChange('capitalRisk', e.target.value)}
                                placeholder="2"
                            />
                        </div>
                        <div style={styles.inputGroup}>
                            <label style={styles.inputLabel}>Trader Level</label>
                            <select
                                className="noa-input"
                                style={styles.select}
                                value={data.traderExperience}
                                onChange={(e) => handleChange('traderExperience', e.target.value)}
                            >
                                <option>Beginner</option>
                                <option>Intermediate</option>
                                <option>Advanced</option>
                                <option>Expert</option>
                            </select>
                        </div>
                    </div>

                    {/* Analysis Type & Buttons */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '8px', flexWrap: 'wrap' }}>
                        <div style={styles.inputGroup}>
                            <label style={styles.inputLabel}>Analysis Type</label>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                <button
                                    className="noa-btn"
                                    onClick={() => setAnalysisType('quick')}
                                    style={{
                                        ...styles.btnSecondary,
                                        background: analysisType === 'quick' ? `${ACCENT}20` : 'transparent',
                                        borderColor: analysisType === 'quick' ? ACCENT : `${ACCENT}30`,
                                        color: analysisType === 'quick' ? ACCENT : '#64748b',
                                    }}
                                    title="Uses claude-haiku — 3× cheaper, 150-word fast result"
                                >
                                    ⚡ Quick
                                    <span style={{ fontSize: '9px', marginLeft: '4px', opacity: 0.7 }}>Haiku·~₹0.01</span>
                                </button>
                                <button
                                    className="noa-btn"
                                    onClick={() => setAnalysisType('full')}
                                    style={{
                                        ...styles.btnSecondary,
                                        background: analysisType === 'full' ? `${ACCENT}20` : 'transparent',
                                        borderColor: analysisType === 'full' ? ACCENT : `${ACCENT}30`,
                                        color: analysisType === 'full' ? ACCENT : '#64748b',
                                    }}
                                    title="Uses claude-sonnet — full 7-section trade plan with prompt caching"
                                >
                                    📊 Full Report
                                    <span style={{ fontSize: '9px', marginLeft: '4px', opacity: 0.7 }}>Sonnet·~₹0.10</span>
                                </button>
                            </div>
                        </div>

                        <div style={{ display: 'flex', gap: '10px', marginLeft: 'auto' }}>
                            <button className="noa-btn" style={styles.btnSecondary} onClick={fetchLiveData} disabled={fetching}>
                                {fetching ? '⟳ Refreshing...' : '⟳ Refresh Data'}
                            </button>
                            <button
                                className="noa-btn"
                                style={{
                                    ...styles.btn,
                                    opacity: loading ? 0.7 : 1,
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                }}
                                onClick={analyzeWithAI}
                                disabled={loading}
                            >
                                {loading ? (
                                    <>
                                        <div style={{ ...styles.spinner, animation: 'spin 0.8s linear infinite' }} />
                                        Analyzing...
                                    </>
                                ) : (
                                    <><span>🤖</span> Analyze with AI</>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* AI RESPONSE */}
                {(aiResponse || loading || error) && (
                    <div style={{ ...styles.card, marginTop: '16px' }}>
                        <div style={styles.sectionTitle}>🤖 AI INTRADAY ANALYSIS</div>
                        {loading && (
                            <div style={styles.loading}>
                                <div style={{ ...styles.spinner, animation: 'spin 0.8s linear infinite' }} />
                                <span>Claude is analyzing market data...</span>
                            </div>
                        )}
                        {error && (
                            <div style={{
                                color: RED, fontSize: '13px', padding: '10px',
                                background: `${RED}10`, borderRadius: '6px', border: `1px solid ${RED}30`,
                            }}>
                                ⚠️ {error}
                            </div>
                        )}
                        {aiResponse && (
                            <div style={styles.aiResponse} className="ai-out">
                                {renderMarkdown(aiResponse)}
                            </div>
                        )}
                        {aiResponse && (
                            <>
                                {/* Token & cost summary */}
                                {tokensUsed && (
                                    <div style={{
                                        display: 'flex', gap: '10px', flexWrap: 'wrap',
                                        marginTop: '12px', padding: '10px 14px',
                                        background: '#0a1525', border: `1px solid ${BORDER}`,
                                        borderRadius: '8px', fontSize: '10px', color: '#475569',
                                        letterSpacing: '0.05em',
                                    }}>
                                        <span style={{ color: ACCENT }}>📊 USAGE</span>
                                        <span>Model: <strong style={{ color: '#94a3b8' }}>{tokensUsed.model}</strong></span>
                                        <span>In: <strong style={{ color: '#94a3b8' }}>{tokensUsed.inputTokens.toLocaleString()}</strong></span>
                                        <span>Out: <strong style={{ color: '#94a3b8' }}>{tokensUsed.outputTokens.toLocaleString()}</strong></span>
                                        {tokensUsed.cacheReadTokens > 0 && (
                                            <span style={{ color: GREEN }}>⚡ Cache hit: <strong>{tokensUsed.cacheReadTokens.toLocaleString()}</strong> tokens (90% saved)</span>
                                        )}
                                        {tokensUsed.cacheWriteTokens > 0 && (
                                            <span style={{ color: YELLOW }}>💾 Cache write: <strong>{tokensUsed.cacheWriteTokens.toLocaleString()}</strong></span>
                                        )}
                                        <span style={{ marginLeft: 'auto', color: GREEN }}>Cost: <strong>~₹{(tokensUsed.estimatedCostUSD * USD_TO_INR).toFixed(3)}</strong> (${tokensUsed.estimatedCostUSD.toFixed(5)})</span>
                                    </div>
                                )}
                                <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
                                    <button
                                        className="noa-btn"
                                        style={styles.btnSecondary}
                                        onClick={() => navigator.clipboard.writeText(aiResponse)}
                                    >
                                        📋 Copy Analysis
                                    </button>
                                    <button className="noa-btn" style={styles.btnSecondary} onClick={() => { setAiResponse(''); setTokensUsed(null) }}>
                                        🗑️ Clear
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                )}

                {/* DISCLAIMER */}
                <div style={{
                    textAlign: 'center', padding: '20px', fontSize: '10px',
                    color: '#f4937a', letterSpacing: '0.05em', lineHeight: '1.8',
                }}>
                    ⚠️ DISCLAIMER: This tool is for EDUCATIONAL purposes only. Not SEBI registered advice.
                    <br />
                    Options trading involves significant risk. Always use proper risk management. Verify all data before trading.
                </div>
            </div>
        </div>
    )
}
