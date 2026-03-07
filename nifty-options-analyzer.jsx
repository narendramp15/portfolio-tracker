import { useState, useEffect } from "react";

const ACCENT = "#00ff9d";
const BG = "#0a0e1a";
const CARD = "#111827";
const BORDER = "#1e2d40";
const RED = "#ff4d6d";
const GREEN = "#00ff9d";
const YELLOW = "#ffd166";

const styles = {
  app: {
    minHeight: "100vh",
    background: BG,
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    color: "#e2e8f0",
    padding: "0",
  },
  header: {
    background: `linear-gradient(135deg, #0d1b2a 0%, #0a0e1a 100%)`,
    borderBottom: `1px solid ${BORDER}`,
    padding: "18px 32px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    position: "sticky",
    top: 0,
    zIndex: 100,
    backdropFilter: "blur(12px)",
  },
  logo: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    fontSize: "18px",
    fontWeight: "700",
    letterSpacing: "0.05em",
    color: ACCENT,
  },
  badge: {
    background: `${ACCENT}20`,
    border: `1px solid ${ACCENT}60`,
    color: ACCENT,
    fontSize: "10px",
    padding: "2px 8px",
    borderRadius: "4px",
    letterSpacing: "0.15em",
  },
  liveIndicator: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    fontSize: "11px",
    color: "#64748b",
  },
  liveDot: {
    width: "7px",
    height: "7px",
    borderRadius: "50%",
    background: GREEN,
    boxShadow: `0 0 8px ${GREEN}`,
    animation: "pulse 1.5s infinite",
  },
  main: {
    maxWidth: "1280px",
    margin: "0 auto",
    padding: "28px 24px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "16px",
    marginBottom: "20px",
  },
  fullRow: {
    gridColumn: "1 / -1",
  },
  card: {
    background: CARD,
    border: `1px solid ${BORDER}`,
    borderRadius: "12px",
    padding: "20px",
    position: "relative",
    overflow: "hidden",
  },
  cardTitle: {
    fontSize: "10px",
    letterSpacing: "0.2em",
    color: "#475569",
    marginBottom: "14px",
    textTransform: "uppercase",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  dataRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 0",
    borderBottom: `1px solid ${BORDER}`,
  },
  label: {
    fontSize: "11px",
    color: "#64748b",
  },
  value: {
    fontSize: "13px",
    fontWeight: "600",
    color: "#e2e8f0",
  },
  valueGreen: { color: GREEN, fontWeight: "700" },
  valueRed: { color: RED, fontWeight: "700" },
  valueYellow: { color: YELLOW, fontWeight: "700" },
  bigNumber: {
    fontSize: "28px",
    fontWeight: "800",
    letterSpacing: "-0.02em",
    lineHeight: 1,
    marginBottom: "4px",
  },
  changeTag: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    fontSize: "12px",
    padding: "2px 8px",
    borderRadius: "4px",
    fontWeight: "600",
  },
  inputGroup: {
    marginBottom: "12px",
  },
  inputLabel: {
    fontSize: "10px",
    color: "#475569",
    letterSpacing: "0.12em",
    marginBottom: "5px",
    display: "block",
    textTransform: "uppercase",
  },
  input: {
    width: "100%",
    background: "#0d1b2a",
    border: `1px solid ${BORDER}`,
    borderRadius: "6px",
    padding: "8px 12px",
    color: "#e2e8f0",
    fontSize: "12px",
    fontFamily: "inherit",
    outline: "none",
    boxSizing: "border-box",
    transition: "border-color 0.2s",
  },
  select: {
    width: "100%",
    background: "#0d1b2a",
    border: `1px solid ${BORDER}`,
    borderRadius: "6px",
    padding: "8px 12px",
    color: "#e2e8f0",
    fontSize: "12px",
    fontFamily: "inherit",
    outline: "none",
    boxSizing: "border-box",
  },
  textarea: {
    width: "100%",
    background: "#0d1b2a",
    border: `1px solid ${BORDER}`,
    borderRadius: "6px",
    padding: "10px 12px",
    color: "#e2e8f0",
    fontSize: "12px",
    fontFamily: "inherit",
    outline: "none",
    boxSizing: "border-box",
    resize: "vertical",
    minHeight: "80px",
  },
  btn: {
    background: `linear-gradient(135deg, ${ACCENT}, #00c97a)`,
    color: "#0a0e1a",
    border: "none",
    borderRadius: "8px",
    padding: "12px 28px",
    fontSize: "12px",
    fontWeight: "800",
    fontFamily: "inherit",
    letterSpacing: "0.1em",
    cursor: "pointer",
    textTransform: "uppercase",
    transition: "all 0.2s",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  btnSecondary: {
    background: "transparent",
    color: ACCENT,
    border: `1px solid ${ACCENT}50`,
    borderRadius: "8px",
    padding: "10px 20px",
    fontSize: "11px",
    fontWeight: "600",
    fontFamily: "inherit",
    letterSpacing: "0.08em",
    cursor: "pointer",
    textTransform: "uppercase",
    transition: "all 0.2s",
  },
  btnRow: {
    display: "flex",
    gap: "12px",
    alignItems: "center",
    marginTop: "16px",
    flexWrap: "wrap",
  },
  aiResponse: {
    background: "#0d1b2a",
    border: `1px solid ${ACCENT}30`,
    borderRadius: "10px",
    padding: "20px",
    fontSize: "13px",
    lineHeight: "1.8",
    whiteSpace: "pre-wrap",
    color: "#cbd5e1",
    minHeight: "100px",
    position: "relative",
  },
  loading: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    color: ACCENT,
    fontSize: "13px",
  },
  spinner: {
    width: "16px",
    height: "16px",
    border: `2px solid ${ACCENT}30`,
    borderTop: `2px solid ${ACCENT}`,
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  sentimentBar: {
    height: "6px",
    borderRadius: "3px",
    background: "#1e2d40",
    marginTop: "10px",
    overflow: "hidden",
  },
  sectionTitle: {
    fontSize: "12px",
    letterSpacing: "0.15em",
    color: ACCENT,
    textTransform: "uppercase",
    marginBottom: "16px",
    paddingBottom: "8px",
    borderBottom: `1px solid ${BORDER}`,
    fontWeight: "700",
  },
  tag: {
    display: "inline-flex",
    padding: "3px 10px",
    borderRadius: "4px",
    fontSize: "11px",
    fontWeight: "700",
    letterSpacing: "0.08em",
  },
  alertBox: {
    background: `${YELLOW}10`,
    border: `1px solid ${YELLOW}40`,
    borderRadius: "8px",
    padding: "10px 14px",
    fontSize: "11px",
    color: YELLOW,
    marginBottom: "14px",
    lineHeight: "1.6",
  },
  vixMeter: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    marginTop: "6px",
  },
};

const marketDefaults = {
  niftyClose: "24765.90",
  bankniftyClose: "59055.85",
  giftNifty: "24820",
  vix: "13.45",
  fiiActivity: "-4630",
  diiActivity: "+24312",
  usMarket: "+0.5",
  crude: "72.40",
  dollarIndex: "104.20",
  majorEvents: "No major events",
  capitalRisk: "2",
  traderExperience: "Intermediate",
  sessionType: "Intraday",
};

function formatNum(n) {
  return parseFloat(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function getVixColor(vix) {
  const v = parseFloat(vix);
  if (v < 12) return GREEN;
  if (v < 16) return YELLOW;
  return RED;
}

function getSentimentColor(fii) {
  return parseFloat(fii) >= 0 ? GREEN : RED;
}

export default function NiftyAnalyzer() {
  const [data, setData] = useState(marketDefaults);
  const [aiResponse, setAiResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState("");
  const [currentTime, setCurrentTime] = useState(new Date());
  const [analysisType, setAnalysisType] = useState("full");

  useEffect(() => {
    const t = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const IST = currentTime.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  const today = currentTime.toLocaleDateString("en-IN", {
    timeZone: "Asia/Kolkata",
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const handleChange = (key, val) => {
    setData((d) => ({ ...d, [key]: val }));
  };

  const fetchLiveData = async () => {
    setFetching(true);
    // Simulate fetching — in production wire to NSE API / Yahoo Finance
    await new Promise((r) => setTimeout(r, 1800));
    setData((d) => ({
      ...d,
      niftyClose: "24765.90",
      bankniftyClose: "59055.85",
      giftNifty: (24765 + Math.floor(Math.random() * 120 - 60)).toString(),
      vix: (13 + Math.random() * 2).toFixed(2),
    }));
    setFetching(false);
  };

  const buildPrompt = () => {
    const fiiSign = parseFloat(data.fiiActivity) >= 0 ? "+" : "";
    const diiSign = parseFloat(data.diiActivity) >= 0 ? "+" : "";
    const usSign = parseFloat(data.usMarket) >= 0 ? "Positive" : "Negative";

    if (analysisType === "quick") {
      return `Act as an expert intraday trading analyst for Indian markets.
Today is ${today} | IST: ${IST}

Market Data:
- Nifty Previous Close: ${data.niftyClose}
- Bank Nifty Previous Close: ${data.bankniftyClose}
- Gift Nifty: ${data.giftNifty}
- India VIX: ${data.vix}
- FII Activity: ₹${fiiSign}${data.fiiActivity} crore
- DII Activity: ₹${diiSign}${data.diiActivity} crore
- US Markets: ${usSign} (${data.usMarket}%)
- Crude Oil: $${data.crude}
- Dollar Index: ${data.dollarIndex}
- Major Events: ${data.majorEvents}

Give me:
1. Market Bias (Bullish/Bearish/Sideways) in 2 lines
2. Nifty & Bank Nifty: Key Support and Resistance levels
3. ONE best trade setup with Entry, SL, Target, and preferred CE/PE strike
4. Whether to BUY or SELL options today and why (based on VIX)

Be concise. 150 words max.`;
    }

    return `You are an expert SEBI-registered intraday trading analyst specializing in Indian equity derivatives — Nifty 50 and Bank Nifty.

Today's Date: ${today}
Current IST Time: ${IST}
Trader Profile: ${data.traderExperience} trader | Max Risk per trade: ${data.capitalRisk}% of capital | Session: ${data.sessionType}

═══ LIVE MARKET DATA ═══
📊 Nifty 50 Previous Close: ${formatNum(data.niftyClose)}
📊 Bank Nifty Previous Close: ${formatNum(data.bankniftyClose)}
🌏 Gift Nifty (Pre-market): ${formatNum(data.giftNifty)}
⚡ India VIX: ${data.vix} ${parseFloat(data.vix) < 12 ? "(LOW - Options selling favored)" : parseFloat(data.vix) < 16 ? "(MODERATE - Balanced)" : "(HIGH - Options buying favored)"}
🏦 FII Net Activity: ₹${fiiSign}${formatNum(data.fiiActivity)} crore ${parseFloat(data.fiiActivity) >= 0 ? "(Net BUYERS)" : "(Net SELLERS)"}
🏦 DII Net Activity: ₹${diiSign}${formatNum(data.diiActivity)} crore ${parseFloat(data.diiActivity) >= 0 ? "(Net BUYERS)" : "(Net SELLERS)"}
🌍 US Markets (Overnight): ${data.usMarket}%
🛢️ Crude Oil: $${data.crude}/barrel
💵 Dollar Index (DXY): ${data.dollarIndex}
📅 Major Events Today: ${data.majorEvents}

═══ ANALYSIS REQUIRED ═══

1. 🎯 MARKET BIAS
   - Overall direction: Bullish / Bearish / Sideways with 3-line reasoning
   - Sentiment score: X/10

2. 📊 KEY LEVELS
   Nifty 50:
   - Strong Support 1 & Support 2
   - Strong Resistance 1 & Resistance 2
   - Day's Pivot Point
   
   Bank Nifty:
   - Strong Support 1 & Support 2
   - Strong Resistance 1 & Resistance 2
   - Day's Pivot Point

3. 📈 INTRADAY TRADE SETUPS (2-3 setups)
   For EACH setup:
   - Index: Nifty / Bank Nifty
   - Direction: Long / Short
   - Entry Zone: [price range]
   - Stop Loss: [price] (hard SL)
   - Target 1 & Target 2
   - Risk:Reward Ratio
   - Instrument: Futures OR Options (CE/PE with specific strike & expiry)
   - Best Time Window to execute
   - Confidence: High / Medium / Low

4. 🧠 OPTIONS STRATEGY
   - BUY or SELL options today? (justify with VIX level)
   - If BUYING: Best CE or PE strike with expiry
   - If SELLING: Best strategy (Iron Condor / Strangle / Credit Spread)
   - Max risk per trade in % of capital (respect the ${data.capitalRisk}% rule)
   - Expected premium range

5. ⚠️ RISK FACTORS
   - What invalidates these setups
   - Sectors / stocks to avoid
   - Global risk events during market hours

6. 🕐 TIMING GUIDE
   - Best entry windows (IST)
   - Chop zones to avoid
   - Hard exit time rule today

7. 📌 DISCIPLINE REMINDER
   - One key mindset tip for today's market condition

Format clearly with emojis and section headers. Be specific with price levels. No vague advice.`;
  };

  const analyzeWithAI = async () => {
    setLoading(true);
    setError("");
    setAiResponse("");

    const prompt = buildPrompt();

    try {
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          messages: [{ role: "user", content: prompt }],
        }),
      });

      const res = await response.json();
      if (res.error) throw new Error(res.error.message);
      const text = res.content?.map((c) => c.text || "").join("\n") || "No response.";
      setAiResponse(text);
    } catch (e) {
      setError("API error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const fiiNum = parseFloat(data.fiiActivity);
  const vixNum = parseFloat(data.vix);
  const giftDiff = parseFloat(data.giftNifty) - parseFloat(data.niftyClose);
  const giftPct = ((giftDiff / parseFloat(data.niftyClose)) * 100).toFixed(2);

  return (
    <div style={styles.app}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes spin { to{transform:rotate(360deg)} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        input:focus, select:focus, textarea:focus { border-color: #00ff9d60 !important; box-shadow: 0 0 0 2px #00ff9d15; }
        button:hover { opacity: 0.88; transform: translateY(-1px); }
        ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: #0a0e1a; } ::-webkit-scrollbar-thumb { background: #1e2d40; border-radius: 3px; }
        .ai-out { animation: fadeIn 0.5s ease; }
      `}</style>

      {/* HEADER */}
      <div style={styles.header}>
        <div style={styles.logo}>
          <span>⚡</span>
          <span>NIFTY OPTIONS ANALYZER</span>
          <span style={styles.badge}>AI POWERED</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <div style={styles.liveIndicator}>
            <div style={styles.liveDot} />
            <span>IST {IST}</span>
          </div>
          <div style={{ fontSize: "10px", color: "#334155", letterSpacing: "0.05em" }}>
            {today}
          </div>
        </div>
      </div>

      <div style={styles.main}>

        {/* MARKET SNAPSHOT */}
        <div style={styles.grid}>
          {/* Nifty Card */}
          <div style={{ ...styles.card, borderColor: `${GREEN}30` }}>
            <div style={styles.cardTitle}>
              <span style={{ color: GREEN }}>▲</span> NIFTY 50
            </div>
            <div style={{ ...styles.bigNumber, color: GREEN }}>{formatNum(data.niftyClose)}</div>
            <div style={{ display: "flex", gap: "8px", marginTop: "8px", marginBottom: "12px" }}>
              <span style={{ ...styles.changeTag, background: `${GREEN}15`, color: GREEN }}>
                ▲ +1.17%
              </span>
              <span style={{ ...styles.tag, background: "#1e2d40", color: "#64748b", fontSize: "11px" }}>
                PREV CLOSE
              </span>
            </div>
            <div style={styles.dataRow}>
              <span style={styles.label}>Gift Nifty</span>
              <span style={{ ...styles.value, color: giftDiff >= 0 ? GREEN : RED }}>
                {formatNum(data.giftNifty)} ({giftDiff >= 0 ? "+" : ""}{giftPct}%)
              </span>
            </div>
            <div style={styles.dataRow}>
              <span style={styles.label}>Gap Open Expected</span>
              <span style={{ ...styles.value, color: giftDiff >= 0 ? GREEN : RED }}>
                {giftDiff >= 0 ? "GAP UP" : "GAP DOWN"} ~{Math.abs(giftDiff).toFixed(0)} pts
              </span>
            </div>
          </div>

          {/* BankNifty Card */}
          <div style={{ ...styles.card, borderColor: `#a78bfa30` }}>
            <div style={{ ...styles.cardTitle }}>
              <span style={{ color: "#a78bfa" }}>▲</span> BANK NIFTY
            </div>
            <div style={{ ...styles.bigNumber, color: "#a78bfa" }}>{formatNum(data.bankniftyClose)}</div>
            <div style={{ display: "flex", gap: "8px", marginTop: "8px", marginBottom: "12px" }}>
              <span style={{ ...styles.changeTag, background: "#a78bfa15", color: "#a78bfa" }}>
                ▲ +0.51%
              </span>
              <span style={{ ...styles.tag, background: "#1e2d40", color: "#64748b", fontSize: "11px" }}>
                PREV CLOSE
              </span>
            </div>
            <div style={styles.dataRow}>
              <span style={styles.label}>India VIX</span>
              <span style={{ ...styles.value, color: getVixColor(data.vix) }}>{data.vix}</span>
            </div>
            <div style={styles.dataRow}>
              <span style={styles.label}>VIX Signal</span>
              <span style={{ ...styles.tag, 
                background: vixNum < 12 ? `${GREEN}15` : vixNum < 16 ? `${YELLOW}15` : `${RED}15`, 
                color: getVixColor(data.vix), fontSize: "10px" }}>
                {vixNum < 12 ? "SELL OPTIONS" : vixNum < 16 ? "BALANCED" : "BUY OPTIONS"}
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
                  ₹{fiiNum >= 0 ? "+" : ""}{formatNum(data.fiiActivity)} Cr
                </span>
                <span style={{ ...styles.tag, marginLeft: "8px", fontSize: "9px",
                  background: fiiNum >= 0 ? `${GREEN}15` : `${RED}15`,
                  color: fiiNum >= 0 ? GREEN : RED }}>
                  {fiiNum >= 0 ? "BUYING" : "SELLING"}
                </span>
              </div>
            </div>
            <div style={styles.dataRow}>
              <span style={styles.label}>DII Net</span>
              <div>
                <span style={{ ...styles.value, color: parseFloat(data.diiActivity) >= 0 ? GREEN : RED }}>
                  ₹{parseFloat(data.diiActivity) >= 0 ? "+" : ""}{formatNum(data.diiActivity)} Cr
                </span>
              </div>
            </div>
            <div style={{ marginTop: "10px" }}>
              <div style={{ fontSize: "10px", color: "#475569", marginBottom: "5px" }}>
                NET SENTIMENT
              </div>
              <div style={styles.sentimentBar}>
                <div style={{
                  height: "100%",
                  width: fiiNum >= 0 ? "65%" : "35%",
                  background: fiiNum >= 0 ? `linear-gradient(90deg, ${GREEN}, #00c97a)` : `linear-gradient(90deg, ${RED}, #ff6b6b)`,
                  borderRadius: "3px",
                  transition: "width 0.8s ease"
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
                {parseFloat(data.usMarket) >= 0 ? "+" : ""}{data.usMarket}%
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
              <span style={{ ...styles.value, fontSize: "11px", color: YELLOW }}>{data.majorEvents}</span>
            </div>
          </div>
        </div>

        {/* MANUAL INPUT SECTION */}
        <div style={styles.card}>
          <div style={styles.sectionTitle}>⚙️ EDIT MARKET DATA</div>

          <div style={{ ...styles.alertBox }}>
            ⚠️ Auto-fetch shows estimated data. Please verify with NSE/Zerodha before trading. Edit fields below to match live market.
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "12px" }}>
            {[
              { key: "niftyClose", label: "Nifty Close" },
              { key: "bankniftyClose", label: "Bank Nifty Close" },
              { key: "giftNifty", label: "Gift Nifty" },
              { key: "vix", label: "India VIX" },
              { key: "fiiActivity", label: "FII Activity (₹ Cr)" },
              { key: "diiActivity", label: "DII Activity (₹ Cr)" },
              { key: "crude", label: "Crude Oil ($)" },
              { key: "dollarIndex", label: "Dollar Index" },
            ].map(({ key, label }) => (
              <div key={key} style={styles.inputGroup}>
                <label style={styles.inputLabel}>{label}</label>
                <input
                  style={styles.input}
                  value={data[key]}
                  onChange={(e) => handleChange(key, e.target.value)}
                />
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: "12px" }}>
            <div style={styles.inputGroup}>
              <label style={styles.inputLabel}>Major Events / News Today</label>
              <input
                style={styles.input}
                value={data.majorEvents}
                onChange={(e) => handleChange("majorEvents", e.target.value)}
                placeholder="e.g., RBI Policy, Q3 Results, Expiry..."
              />
            </div>
            <div style={styles.inputGroup}>
              <label style={styles.inputLabel}>Max Risk % / Trade</label>
              <input
                style={styles.input}
                value={data.capitalRisk}
                onChange={(e) => handleChange("capitalRisk", e.target.value)}
              />
            </div>
            <div style={styles.inputGroup}>
              <label style={styles.inputLabel}>Trader Level</label>
              <select style={styles.select} value={data.traderExperience}
                onChange={(e) => handleChange("traderExperience", e.target.value)}>
                <option>Beginner</option>
                <option>Intermediate</option>
                <option>Advanced</option>
                <option>Expert</option>
              </select>
            </div>
          </div>

          {/* Analysis Type & Buttons */}
          <div style={{ display: "flex", alignItems: "center", gap: "16px", marginTop: "8px", flexWrap: "wrap" }}>
            <div style={styles.inputGroup}>
              <label style={styles.inputLabel}>Analysis Type</label>
              <div style={{ display: "flex", gap: "8px" }}>
                {["quick", "full"].map((t) => (
                  <button key={t}
                    onClick={() => setAnalysisType(t)}
                    style={{
                      ...styles.btnSecondary,
                      background: analysisType === t ? `${ACCENT}20` : "transparent",
                      borderColor: analysisType === t ? ACCENT : `${ACCENT}30`,
                      color: analysisType === t ? ACCENT : "#64748b",
                    }}>
                    {t === "quick" ? "⚡ Quick" : "📊 Full Report"}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", marginLeft: "auto" }}>
              <button style={styles.btnSecondary} onClick={fetchLiveData} disabled={fetching}>
                {fetching ? "⟳ Fetching..." : "⟳ Refresh Data"}
              </button>
              <button style={styles.btn} onClick={analyzeWithAI} disabled={loading}>
                {loading ? (
                  <><div style={styles.spinner} /> Analyzing...</>
                ) : (
                  <><span>🤖</span> Analyze with AI</>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* AI RESPONSE */}
        {(aiResponse || loading || error) && (
          <div style={{ ...styles.card, marginTop: "16px" }}>
            <div style={styles.sectionTitle}>🤖 AI INTRADAY ANALYSIS</div>
            {loading && (
              <div style={styles.loading}>
                <div style={styles.spinner} />
                <span>Claude is analyzing market data...</span>
              </div>
            )}
            {error && (
              <div style={{ color: RED, fontSize: "13px", padding: "10px", 
                background: `${RED}10`, borderRadius: "6px", border: `1px solid ${RED}30` }}>
                ⚠️ {error}
              </div>
            )}
            {aiResponse && (
              <div style={styles.aiResponse} className="ai-out">
                {aiResponse}
              </div>
            )}
            {aiResponse && (
              <div style={{ marginTop: "12px", display: "flex", gap: "10px" }}>
                <button style={styles.btnSecondary}
                  onClick={() => navigator.clipboard.writeText(aiResponse)}>
                  📋 Copy Analysis
                </button>
                <button style={styles.btnSecondary} onClick={() => setAiResponse("")}>
                  🗑️ Clear
                </button>
              </div>
            )}
          </div>
        )}

        {/* DISCLAIMER */}
        <div style={{ textAlign: "center", padding: "20px", fontSize: "10px", 
          color: "#334155", letterSpacing: "0.05em", lineHeight: "1.8" }}>
          ⚠️ DISCLAIMER: This tool is for EDUCATIONAL purposes only. Not SEBI registered advice.<br />
          Options trading involves significant risk. Always use proper risk management. Verify all data before trading.
        </div>
      </div>
    </div>
  );
}
