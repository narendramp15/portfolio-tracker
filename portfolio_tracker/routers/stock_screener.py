"""Stock Screener — value scoring engine.

Scans a universe of NSE-listed stocks, scores each across five pillars
(Financial Strength, Earnings Quality, Valuation, Business Quality,
Future Outlook) and returns the top-10 value picks.
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import StockThesisCacheModel, UserModel
from portfolio_tracker.services.anthropic_client import call_anthropic

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Anthropic config for AI thesis generation
# ---------------------------------------------------------------------------
_THESIS_MODEL = os.getenv("MODEL_PRO", "claude-sonnet-4-6")
_THESIS_CACHE_HOURS = 24  # re-generate thesis after 24 hours

_THESIS_SYSTEM = (
    "You are a concise value-investing analyst covering Indian equities. "
    "Given a stock's quantitative scores across 5 pillars (Financial Strength, Earnings Quality, "
    "Valuation, Business Quality, Future Outlook) and its key fundamental metrics, "
    "write a crisp 3-paragraph investment thesis in plain English. "
    "Paragraph 1: what makes this a value opportunity (or not). "
    "Paragraph 2: the biggest risk or red flag in the numbers. "
    "Paragraph 3: one-line verdict. "
    "Keep total length under 180 words. No bullet points. No markdown headings."
)

# ---------------------------------------------------------------------------
# Server-side daily cache  (shared across all users; auto-refreshes each new IST day)
# ---------------------------------------------------------------------------
_cache: ScreenerResponse | None = None  # forward-declared; set after class definition
_cache_ts: float = 0.0                  # monotonic time of last scan (for "X ago" display)
_CACHE_DATE: str = ""                   # IST date of last scan ("YYYY-MM-DD")
_WORKERS = 12                           # concurrent yfinance threads


def _today_ist() -> str:
    """Return today's date string in IST (UTC+5:30)."""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%Y-%m-%d")


def _seconds_until_midnight_ist() -> int:
    """Seconds from now until next IST midnight."""
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(0, int((midnight - now).total_seconds()))

# ---------------------------------------------------------------------------
# Stock universe – Nifty-50 + popular liquid mid-caps (NSE tickers)
# ---------------------------------------------------------------------------
STOCK_UNIVERSE: list[str] = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "WIPRO.NS", "AXISBANK.NS", "SBIN.NS",
    "KOTAKBANK.NS", "BAJFINANCE.NS", "LT.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "NESTLEIND.NS", "ULTRACEMCO.NS", "POWERGRID.NS",
    "NTPC.NS", "TECHM.NS", "HCLTECH.NS", "BAJAJFINSV.NS", "TATASTEEL.NS",
    "JSWSTEEL.NS", "TATAMOTORS.NS", "M&M.NS", "ONGC.NS", "COALINDIA.NS",
    "GRASIM.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "EICHERMOT.NS",
    "BRITANNIA.NS", "HEROMOTOCO.NS", "BPCL.NS", "ADANIENT.NS", "ADANIPORTS.NS",
]

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class PillarScores(BaseModel):
    financial_strength: float
    earnings_quality: float
    valuation: float
    business_quality: float
    future_outlook: float


class KeyMetrics(BaseModel):
    pe: float | None = None
    peg: float | None = None
    pb: float | None = None
    ev_ebitda: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    roe: float | None = None
    profit_margin: float | None = None
    revenue_growth: float | None = None
    earnings_growth: float | None = None


class StockResult(BaseModel):
    rank: int
    symbol: str
    name: str
    sector: str
    current_price: float
    value_score: float
    pillar_scores: PillarScores
    key_metrics: KeyMetrics
    recommendation: str
    error: str | None = None


class ScreenerResponse(BaseModel):
    top_stocks: list[StockResult]
    scanned_count: int
    successful_count: int
    scan_timestamp: str
    cached: bool = False          # True when result came from cache
    cache_age_seconds: int = 0    # seconds since last live fetch
    next_refresh_seconds: int = 0 # seconds until cache expires


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _safe(val: Any, default: float | None = None) -> float | None:
    """Return a numeric value or default; treats NaN/None as missing."""
    if val is None:
        return default
    try:
        f = float(val)
        return default if (f != f) else f  # NaN check via self-inequality
    except (TypeError, ValueError):
        return default


def _score_financial_strength(info: dict) -> tuple[float, dict]:
    """Score 0-10.  Weights: D/E 40 %, current ratio 30 %, int coverage 30 %."""
    score = 0.0
    details: dict[str, float | None] = {}

    de = _safe(info.get("debtToEquity"))
    details["debt_to_equity"] = de
    if de is not None:
        if de < 20:      score += 4.0   # yfinance returns % (e.g. 50 = 0.5)
        elif de < 50:    score += 3.0
        elif de < 100:   score += 2.0
        elif de < 200:   score += 1.0

    cr = _safe(info.get("currentRatio"))
    details["current_ratio"] = cr
    if cr is not None:
        if cr > 2.5:     score += 3.0
        elif cr > 1.5:   score += 2.0
        elif cr > 1.0:   score += 1.0

    # Interest coverage proxy: EBIT / interest expense
    ebit = _safe(info.get("ebit"))
    interest = _safe(info.get("interestExpense"))
    if ebit is not None and interest is not None and interest != 0:
        cov = abs(ebit / interest)
        details["interest_coverage"] = round(cov, 2)
        if cov > 10:     score += 3.0
        elif cov > 5:    score += 2.0
        elif cov > 3:    score += 1.0
    else:
        details["interest_coverage"] = None

    return min(score, 10.0), details


def _score_earnings_quality(info: dict) -> tuple[float, dict]:
    """Score 0-10.  Revenue growth, profit margin, EPS growth, op margin."""
    score = 0.0
    details: dict[str, float | None] = {}

    rev_growth = _safe(info.get("revenueGrowth"))
    details["revenue_growth"] = rev_growth
    if rev_growth is not None:
        if rev_growth > 0.20:   score += 3.0
        elif rev_growth > 0.10: score += 2.0
        elif rev_growth > 0.0:  score += 1.0

    pm = _safe(info.get("profitMargins"))
    details["profit_margin"] = pm
    if pm is not None:
        if pm > 0.20:    score += 2.5
        elif pm > 0.10:  score += 1.5
        elif pm > 0.0:   score += 0.5

    eg = _safe(info.get("earningsGrowth"))
    details["earnings_growth"] = eg
    if eg is not None:
        if eg > 0.20:    score += 2.5
        elif eg > 0.10:  score += 1.5
        elif eg > 0.0:   score += 0.5

    op_margin = _safe(info.get("operatingMargins"))
    details["operating_margin"] = op_margin
    if op_margin is not None:
        if op_margin > 0.25:  score += 2.0
        elif op_margin > 0.15: score += 1.0
        elif op_margin > 0.0:  score += 0.5

    return min(score, 10.0), details


def _score_valuation(info: dict) -> tuple[float, dict]:
    """Score 0-10.  P/E, PEG, P/B, EV/EBITDA."""
    score = 0.0
    details: dict[str, float | None] = {}

    pe = _safe(info.get("trailingPE"))
    details["pe"] = pe
    if pe is not None and pe > 0:
        if pe < 10:      score += 3.0
        elif pe < 15:    score += 2.5
        elif pe < 20:    score += 2.0
        elif pe < 25:    score += 1.5
        elif pe < 35:    score += 1.0
        else:            score += 0.0

    peg = _safe(info.get("pegRatio"))
    details["peg"] = peg
    if peg is not None and peg > 0:
        if peg < 0.5:    score += 3.0
        elif peg < 1.0:  score += 2.5
        elif peg < 1.5:  score += 1.5
        elif peg < 2.0:  score += 0.5

    pb = _safe(info.get("priceToBook"))
    details["pb"] = pb
    if pb is not None and pb > 0:
        if pb < 1.0:     score += 2.0
        elif pb < 2.0:   score += 1.5
        elif pb < 3.0:   score += 1.0
        elif pb < 5.0:   score += 0.5

    ev_ebitda = _safe(info.get("enterpriseToEbitda"))
    details["ev_ebitda"] = ev_ebitda
    if ev_ebitda is not None and ev_ebitda > 0:
        if ev_ebitda < 8:    score += 2.0
        elif ev_ebitda < 12: score += 1.5
        elif ev_ebitda < 18: score += 1.0
        elif ev_ebitda < 25: score += 0.5

    return min(score, 10.0), details


def _score_business_quality(info: dict) -> tuple[float, dict]:
    """Score 0-10.  ROE, gross margin, return on assets."""
    score = 0.0
    details: dict[str, float | None] = {}

    roe = _safe(info.get("returnOnEquity"))
    details["roe"] = roe
    if roe is not None:
        if roe > 0.25:   score += 4.0
        elif roe > 0.15: score += 3.0
        elif roe > 0.10: score += 2.0
        elif roe > 0.0:  score += 1.0

    gm = _safe(info.get("grossMargins"))
    details["gross_margin"] = gm
    if gm is not None:
        if gm > 0.50:    score += 3.0
        elif gm > 0.35:  score += 2.0
        elif gm > 0.20:  score += 1.5
        elif gm > 0.0:   score += 0.5

    roa = _safe(info.get("returnOnAssets"))
    details["roa"] = roa
    if roa is not None:
        if roa > 0.15:   score += 3.0
        elif roa > 0.10: score += 2.0
        elif roa > 0.05: score += 1.0
        elif roa > 0.0:  score += 0.5

    return min(score, 10.0), details


def _score_future_outlook(info: dict) -> tuple[float, dict]:
    """Score 0-10.  Forward P/E vs trailing, analyst target upside, recommendation."""
    score = 0.0
    details: dict[str, float | None] = {}

    fwd_pe = _safe(info.get("forwardPE"))
    trail_pe = _safe(info.get("trailingPE"))
    details["forward_pe"] = fwd_pe
    if fwd_pe is not None and trail_pe is not None and trail_pe > 0 and fwd_pe > 0:
        # Falling forward P/E means earnings expected to grow
        ratio = trail_pe / fwd_pe
        if ratio > 1.3:    score += 4.0
        elif ratio > 1.15: score += 3.0
        elif ratio > 1.0:  score += 2.0
        elif ratio > 0.9:  score += 1.0

    target = _safe(info.get("targetMeanPrice"))
    price = _safe(info.get("currentPrice")) or _safe(info.get("regularMarketPrice"))
    details["target_price"] = target
    if target is not None and price is not None and price > 0:
        upside = (target - price) / price
        details["analyst_upside"] = round(upside, 4)
        if upside > 0.30:    score += 4.0
        elif upside > 0.15:  score += 3.0
        elif upside > 0.05:  score += 2.0
        elif upside > -0.05: score += 1.0
    else:
        details["analyst_upside"] = None

    # Analyst recommendation mean: 1 = strong buy, 5 = strong sell
    rec_mean = _safe(info.get("recommendationMean"))
    details["analyst_rec_mean"] = rec_mean
    if rec_mean is not None:
        if rec_mean <= 1.5:   score += 2.0
        elif rec_mean <= 2.5: score += 1.5
        elif rec_mean <= 3.0: score += 1.0

    return min(score, 10.0), details


def _compute_value_score(
    fs: float, eq: float, val: float, bq: float, fo: float
) -> float:
    """Weighted composite score (0-100)."""
    return round(
        fs * 0.20 * 10 +
        eq * 0.25 * 10 +
        val * 0.25 * 10 +
        bq * 0.15 * 10 +
        fo * 0.15 * 10,
        2,
    )


def _recommendation(score: float) -> str:
    if score >= 75:  return "Strong Value Buy"
    if score >= 60:  return "Value Buy"
    if score >= 45:  return "Moderate Value"
    if score >= 30:  return "Fairly Valued"
    return "Avoid / Overvalued"


# ---------------------------------------------------------------------------
# Core analysis for a single ticker
# ---------------------------------------------------------------------------

def _analyse_stock(symbol: str) -> StockResult | None:
    """Fetch yfinance data and compute value score.  Returns None on hard error."""
    try:
        import yfinance as yf  # lazy import – already in deps

        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        # Require at minimum a price to be useful
        price = _safe(info.get("currentPrice")) or _safe(info.get("regularMarketPrice"))
        if not price:
            logger.debug("No price for %s – skipping", symbol)
            return None

        name = info.get("longName") or info.get("shortName") or symbol
        sector = info.get("sector") or "Unknown"

        fs_score, _fs = _score_financial_strength(info)
        eq_score, _eq = _score_earnings_quality(info)
        val_score, _val = _score_valuation(info)
        bq_score, _bq = _score_business_quality(info)
        fo_score, _fo = _score_future_outlook(info)

        value_score = _compute_value_score(fs_score, eq_score, val_score, bq_score, fo_score)

        # Normalise D/E – yfinance sometimes returns it as percentage (e.g. 50 for 0.50)
        de_raw = _safe(info.get("debtToEquity"))
        de_display = round(de_raw / 100, 4) if de_raw is not None else None

        return StockResult(
            rank=0,  # filled later
            symbol=symbol,
            name=name,
            sector=sector,
            current_price=round(price, 2),
            value_score=value_score,
            pillar_scores=PillarScores(
                financial_strength=round(fs_score, 2),
                earnings_quality=round(eq_score, 2),
                valuation=round(val_score, 2),
                business_quality=round(bq_score, 2),
                future_outlook=round(fo_score, 2),
            ),
            key_metrics=KeyMetrics(
                pe=_safe(_val.get("pe")),
                peg=_safe(_val.get("peg")),
                pb=_safe(_val.get("pb")),
                ev_ebitda=_safe(_val.get("ev_ebitda")),
                debt_to_equity=de_display,
                current_ratio=_safe(_fs.get("current_ratio")),
                roe=_safe(_bq.get("roe")),
                profit_margin=_safe(_eq.get("profit_margin")),
                revenue_growth=_safe(_eq.get("revenue_growth")),
                earnings_growth=_safe(_eq.get("earnings_growth")),
            ),
            recommendation=_recommendation(value_score),
        )
    except Exception as exc:
        logger.warning("Error analysing %s: %s", symbol, exc)
        return None


# ---------------------------------------------------------------------------
# Parallel scan – fetches all tickers concurrently
# ---------------------------------------------------------------------------

def _run_parallel_scan() -> ScreenerResponse:
    """Fetch all tickers in parallel and build a ranked ScreenerResponse."""
    results: list[StockResult] = []

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        futures = {pool.submit(_analyse_stock, sym): sym for sym in STOCK_UNIVERSE}
        for future in as_completed(futures):
            try:
                result = future.result(timeout=15)
                if result is not None:
                    results.append(result)
            except Exception as exc:
                logger.warning("Parallel fetch error for %s: %s", futures[future], exc)

    if not results:
        raise HTTPException(
            status_code=503,
            detail="Could not fetch market data. Please try again later.",
        )

    results.sort(key=lambda r: r.value_score, reverse=True)
    # Assign ranks for the full sorted list
    for i, stock in enumerate(results, start=1):
        stock.rank = i

    return ScreenerResponse(
        top_stocks=results,
        scanned_count=len(STOCK_UNIVERSE),
        successful_count=len(results),
        scan_timestamp=datetime.utcnow().isoformat(),
        cached=False,
        cache_age_seconds=0,
        next_refresh_seconds=_seconds_until_midnight_ist(),
    )


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

@router.get("/top-value", response_model=ScreenerResponse)
def get_top_value_stocks(
    top_n: int = 10,
    force_refresh: bool = False,
    _user: UserModel = Depends(get_current_user),
) -> ScreenerResponse:
    """Return the top-N value stocks from the screener.

    - Results are cached server-side for the full trading day (shared across all users).
    - Cache auto-invalidates at midnight IST; set `force_refresh=true` to bypass early.
    - Parallel fetching (12 threads) keeps live scans to ~4-5 seconds.
    - `top_n` is capped at 20.
    """
    global _cache, _cache_ts, _CACHE_DATE

    top_n = min(max(top_n, 1), 20)
    today = _today_ist()
    age = int(time.monotonic() - _cache_ts)
    cache_valid = _cache is not None and _CACHE_DATE == today and not force_refresh

    if cache_valid and _cache is not None:
        # Serve from cache – slice to requested top_n
        sliced = _cache.model_copy(update={
            "top_stocks": _cache.top_stocks[:top_n],
            "cached": True,
            "cache_age_seconds": age,
            "next_refresh_seconds": _seconds_until_midnight_ist(),
        })
        return sliced

    # Live scan
    logger.info("Stock screener: starting parallel scan (%d tickers, %d workers)",
                len(STOCK_UNIVERSE), _WORKERS)
    t0 = time.monotonic()
    fresh = _run_parallel_scan()
    elapsed = time.monotonic() - t0
    logger.info("Stock screener: scan complete in %.1fs (%d/%d tickers OK)",
                elapsed, fresh.successful_count, fresh.scanned_count)

    # Update cache
    _cache = fresh
    _cache_ts = time.monotonic()
    _CACHE_DATE = today

    return ScreenerResponse(
        top_stocks=fresh.top_stocks[:top_n],
        scanned_count=fresh.scanned_count,
        successful_count=fresh.successful_count,
        scan_timestamp=fresh.scan_timestamp,
        cached=False,
        cache_age_seconds=0,
        next_refresh_seconds=_seconds_until_midnight_ist(),
    )


# ---------------------------------------------------------------------------
# AI Thesis endpoint  (Pro-gated, 24-hour DB cache)
# ---------------------------------------------------------------------------

class ThesisResponse(BaseModel):
    symbol: str
    thesis: str
    from_cache: bool
    generated_at: str


def _build_thesis_prompt(result: StockResult) -> str:
    ps = result.pillar_scores
    km = result.key_metrics
    return (
        f"Stock: {result.name} ({result.symbol})\n"
        f"Sector: {result.sector}\n"
        f"Current Price: ₹{result.current_price:,.2f}\n"
        f"Overall Value Score: {result.value_score}/100\n\n"
        f"Pillar Scores (0-10):\n"
        f"  Financial Strength: {ps.financial_strength:.1f}\n"
        f"  Earnings Quality:   {ps.earnings_quality:.1f}\n"
        f"  Valuation:          {ps.valuation:.1f}\n"
        f"  Business Quality:   {ps.business_quality:.1f}\n"
        f"  Future Outlook:     {ps.future_outlook:.1f}\n\n"
        f"Key Metrics:\n"
        f"  P/E: {km.pe or 'N/A'}  |  PEG: {km.peg or 'N/A'}  |  P/B: {km.pb or 'N/A'}\n"
        f"  Debt/Equity: {km.debt_to_equity or 'N/A'}  |  Current Ratio: {km.current_ratio or 'N/A'}\n"
        f"  ROE: {f'{km.roe*100:.1f}%' if km.roe else 'N/A'}  |  "
        f"Profit Margin: {f'{km.profit_margin*100:.1f}%' if km.profit_margin else 'N/A'}\n"
        f"  Revenue Growth: {f'{km.revenue_growth*100:.1f}%' if km.revenue_growth else 'N/A'}  |  "
        f"EPS Growth: {f'{km.earnings_growth*100:.1f}%' if km.earnings_growth else 'N/A'}\n"
    )


@router.get("/thesis/{symbol}", response_model=ThesisResponse)
async def get_stock_thesis(
    symbol: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ThesisResponse:
    """Generate an AI investment thesis for a screened stock.

    - **Pro/Teams plan only** — Free users receive HTTP 403.
    - Results are cached in DB for 24 hours; the same thesis is served to all users.
    - Requires ANTHROPIC_API_KEY to be set on the server.
    """
    # 1. Pro gate
    tier = (user.subscription_tier or "free").lower()
    if tier not in ("pro", "teams", "elite"):
        raise HTTPException(
            status_code=403,
            detail="AI Stock Thesis is a Pro plan feature. Upgrade to unlock.",
        )

    # 2. Normalise symbol (accept with or without .NS)
    sym = symbol.upper()
    if not sym.endswith(".NS"):
        sym = sym + ".NS"

    # 3. Check DB cache
    from portfolio_tracker.config import \
        settings  # local import to avoid circular

    cached_row: StockThesisCacheModel | None = (
        db.query(StockThesisCacheModel).filter(StockThesisCacheModel.symbol == sym).first()
    )
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_THESIS_CACHE_HOURS)
    if cached_row and cached_row.generated_at.replace(tzinfo=timezone.utc) > cutoff:
        return ThesisResponse(
            symbol=sym,
            thesis=cached_row.thesis,
            from_cache=True,
            generated_at=cached_row.generated_at.isoformat(),
        )

    # 4. Find the stock in the screener cache → build prompt
    if _cache is None:
        raise HTTPException(
            status_code=404,
            detail="Screener data not yet loaded. Run a scan first.",
        )
    stock_result: StockResult | None = next(
        (s for s in _cache.top_stocks if s.symbol == sym), None
    )
    if stock_result is None:
        raise HTTPException(
            status_code=404,
            detail=f"{sym} was not found in the latest screener results.",
        )

    # 5. Call Anthropic
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service is not configured on this server.")

    user_msg = _build_thesis_prompt(stock_result)
    thesis_text, _usage = await call_anthropic(
        api_key=api_key,
        model=_THESIS_MODEL,
        system_text=_THESIS_SYSTEM,
        user_msg=user_msg,
        max_tokens=400,
        timeout=30.0,
    )
    thesis_text = thesis_text or "No thesis generated."

    # 6. Upsert into DB cache
    now_utc = datetime.now(timezone.utc)
    if cached_row:
        cached_row.thesis = thesis_text
        cached_row.generated_at = now_utc
    else:
        db.add(StockThesisCacheModel(symbol=sym, thesis=thesis_text, generated_at=now_utc))
    db.commit()

    return ThesisResponse(
        symbol=sym,
        thesis=thesis_text,
        from_cache=False,
        generated_at=now_utc.isoformat(),
    )


# ---------------------------------------------------------------------------
# Beginner Screener  — plain-English signals, Nifty 50 large-caps only
# ---------------------------------------------------------------------------

# Only Nifty 50 blue-chips — safe for beginners
BEGINNER_UNIVERSE: list[str] = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "WIPRO.NS", "AXISBANK.NS", "SBIN.NS",
    "KOTAKBANK.NS", "BAJFINANCE.NS", "LT.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "NESTLEIND.NS", "ULTRACEMCO.NS", "POWERGRID.NS",
    "NTPC.NS", "TECHM.NS", "HCLTECH.NS", "TATAMOTORS.NS", "M&M.NS",
    "ONGC.NS", "COALINDIA.NS", "CIPLA.NS", "DRREDDY.NS", "BRITANNIA.NS",
]

_beginner_cache: "BeginnerScreenerResponse | None" = None
_beginner_cache_ts: float = 0.0
_BEGINNER_CACHE_DATE: str = ""


class BeginnerSignal(BaseModel):
    label: str          # e.g. "Low Debt", "Overvalued"
    ok: bool            # True = green, False = amber/red
    detail: str         # one plain-English sentence


class BeginnerStock(BaseModel):
    symbol: str
    name: str
    sector: str
    current_price: float
    overall: str        # "Safe Pick" | "Watchlist" | "Too Risky"
    overall_emoji: str  # ✅ ⚠️ 🚫
    safety_score: int   # 0-100
    signals: list[BeginnerSignal]
    one_liner: str      # what the company does, plain English
    pe: float | None = None
    roe: float | None = None
    debt_to_equity: float | None = None


class BeginnerScreenerResponse(BaseModel):
    stocks: list[BeginnerStock]
    scanned_count: int
    successful_count: int
    scan_timestamp: str
    cached: bool = False
    cache_age_seconds: int = 0
    next_refresh_seconds: int = 0


# plain-English one-liners for well-known companies
_ONE_LINERS: dict[str, str] = {
    "RELIANCE.NS":    "India's largest conglomerate — oil refining, telecom (Jio) & retail.",
    "TCS.NS":         "India's biggest IT services company, works with Fortune 500 clients worldwide.",
    "HDFCBANK.NS":    "India's largest private bank — savings accounts, loans & credit cards.",
    "INFY.NS":        "Global IT & consulting firm, India's second-largest software exporter.",
    "ICICIBANK.NS":   "Major private bank offering retail & corporate banking across India.",
    "HINDUNILVR.NS":  "Makes everyday products — Surf, Dove, Lipton — sold in millions of homes.",
    "ITC.NS":         "Diversified giant — cigarettes, FMCG foods (Sunfeast, Bingo), hotels & paper.",
    "WIPRO.NS":       "IT services & consulting company helping global businesses with technology.",
    "AXISBANK.NS":    "India's third-largest private bank — retail banking & financial services.",
    "SBIN.NS":        "State Bank of India — the country's largest public-sector bank.",
    "KOTAKBANK.NS":   "Premium private bank known for strong asset quality and retail focus.",
    "BAJFINANCE.NS":  "India's leading NBFC — consumer loans, EMI finance & fixed deposits.",
    "LT.NS":          "Engineering & construction giant — builds infrastructure, power & defence projects.",
    "ASIANPAINT.NS":  "Market leader in decorative paints with a dominant distribution network.",
    "MARUTI.NS":      "India's #1 car maker — sells every other passenger vehicle in the country.",
    "SUNPHARMA.NS":   "India's largest pharmaceutical company — prescription & specialty drugs.",
    "TITAN.NS":       "Makes Tanishq jewellery, Titan watches & Fastrack accessories.",
    "NESTLEIND.NS":   "FMCG giant behind Maggi, KitKat, and Nescafé in India.",
    "ULTRACEMCO.NS":  "India's largest cement producer — supplies infrastructure & housing sectors.",
    "POWERGRID.NS":   "Government-owned power transmission company — stable, dividend-paying utility.",
    "NTPC.NS":        "India's largest power generation company — coal & expanding into renewables.",
    "TECHM.NS":       "IT & telecom services firm — strong in 5G and enterprise tech solutions.",
    "HCLTECH.NS":     "Major IT services company with a large global enterprise customer base.",
    "TATAMOTORS.NS":  "Makes Tata cars, trucks & owns Jaguar Land Rover globally.",
    "M&M.NS":         "Makes SUVs (Scorpio, Thar), tractors & farm equipment across India.",
    "ONGC.NS":        "State-owned oil & gas explorer — India's largest energy company.",
    "COALINDIA.NS":   "World's largest coal producer — government-owned, consistent dividends.",
    "CIPLA.NS":       "Generic pharma company — affordable medicines sold in 100+ countries.",
    "DRREDDY.NS":     "Pharma company making generics for the US, Europe & Indian markets.",
    "BRITANNIA.NS":   "Biscuits, bread & dairy — a household FMCG brand in every Indian home.",
}


def _analyse_beginner_stock(symbol: str) -> BeginnerStock | None:
    try:
        import yfinance as yf  # type: ignore[import]
        ticker = yf.Ticker(symbol)
        info: dict = ticker.info or {}

        name = info.get("longName") or info.get("shortName") or symbol
        sector = info.get("sector") or "—"
        price = _safe(info.get("currentPrice") or info.get("regularMarketPrice")) or 0.0

        if price <= 0:
            return None

        # ── Raw metrics ──────────────────────────────────────────────────────
        de_raw = _safe(info.get("debtToEquity"))
        de = round(de_raw / 100, 3) if de_raw else None
        cr = _safe(info.get("currentRatio"))
        pe = _safe(info.get("trailingPE"))
        roe = _safe(info.get("returnOnEquity"))
        pm = _safe(info.get("profitMargins"))
        rev_growth = _safe(info.get("revenueGrowth"))

        # ── Signals ──────────────────────────────────────────────────────────
        signals: list[BeginnerSignal] = []
        safety = 0  # accumulates 0-100

        # 1. Debt level
        if de is not None:
            if de < 0.5:
                signals.append(BeginnerSignal(label="Low Debt", ok=True,
                    detail=f"Debt-to-equity is {de:.2f} — company is not heavily borrowed."))
                safety += 30
            elif de < 1.5:
                signals.append(BeginnerSignal(label="Moderate Debt", ok=True,
                    detail=f"Debt-to-equity is {de:.2f} — manageable but watch for increases."))
                safety += 15
            else:
                signals.append(BeginnerSignal(label="High Debt", ok=False,
                    detail=f"Debt-to-equity is {de:.2f} — company carries significant debt."))
        else:
            safety += 10  # no debt data, neutral

        # 2. Liquidity
        if cr is not None:
            if cr >= 1.5:
                signals.append(BeginnerSignal(label="Good Liquidity", ok=True,
                    detail=f"Current ratio is {cr:.1f} — company can easily pay short-term bills."))
                safety += 20
            elif cr >= 1.0:
                signals.append(BeginnerSignal(label="Adequate Liquidity", ok=True,
                    detail=f"Current ratio is {cr:.1f} — just enough to cover short-term obligations."))
                safety += 10
            else:
                signals.append(BeginnerSignal(label="Liquidity Concern", ok=False,
                    detail=f"Current ratio is {cr:.1f} — may struggle to cover short-term bills."))
        else:
            safety += 10

        # 3. Profitability
        if pe is not None:
            if pe <= 0:
                signals.append(BeginnerSignal(label="Not Profitable", ok=False,
                    detail="Company is currently making a loss — riskier for beginners."))
            elif pe < 20:
                signals.append(BeginnerSignal(label="Reasonably Priced", ok=True,
                    detail=f"P/E ratio is {pe:.1f} — stock looks reasonably valued vs earnings."))
                safety += 25
            elif pe < 35:
                signals.append(BeginnerSignal(label="Fairly Priced", ok=True,
                    detail=f"P/E ratio is {pe:.1f} — priced in line with growth expectations."))
                safety += 15
            else:
                signals.append(BeginnerSignal(label="Expensive Valuation", ok=False,
                    detail=f"P/E ratio is {pe:.1f} — stock is priced for perfection, limited margin of safety."))
        else:
            safety += 10

        # 4. Profitability / ROE
        if roe is not None:
            if roe >= 0.15:
                signals.append(BeginnerSignal(label="Strong Returns", ok=True,
                    detail=f"ROE is {roe*100:.1f}% — management generates good returns on your money."))
                safety += 15
            elif roe >= 0.08:
                signals.append(BeginnerSignal(label="Decent Returns", ok=True,
                    detail=f"ROE is {roe*100:.1f}% — acceptable but room for improvement."))
                safety += 8
            else:
                signals.append(BeginnerSignal(label="Weak Returns", ok=False,
                    detail=f"ROE is {roe*100:.1f}% — management is not using capital efficiently."))

        # 5. Revenue growth
        if rev_growth is not None:
            if rev_growth >= 0.10:
                signals.append(BeginnerSignal(label="Growing Revenue", ok=True,
                    detail=f"Revenue grew {rev_growth*100:.1f}% — business is expanding."))
                safety += 10
            elif rev_growth >= 0:
                signals.append(BeginnerSignal(label="Stable Revenue", ok=True,
                    detail=f"Revenue grew {rev_growth*100:.1f}% — steady but not accelerating."))
                safety += 5
            else:
                signals.append(BeginnerSignal(label="Shrinking Revenue", ok=False,
                    detail=f"Revenue fell {abs(rev_growth)*100:.1f}% — business may be under pressure."))

        # ── Overall verdict ───────────────────────────────────────────────────
        safety = min(safety, 100)
        if safety >= 65:
            overall, emoji = "Safe Pick", "✅"
        elif safety >= 40:
            overall, emoji = "Watchlist", "⚠️"
        else:
            overall, emoji = "Too Risky", "🚫"

        one_liner = _ONE_LINERS.get(symbol, f"A listed company in the {sector} sector.")

        return BeginnerStock(
            symbol=symbol,
            name=name,
            sector=sector,
            current_price=round(price, 2),
            overall=overall,
            overall_emoji=emoji,
            safety_score=safety,
            signals=signals,
            one_liner=one_liner,
            pe=pe,
            roe=roe,
            debt_to_equity=de,
        )
    except Exception as exc:
        logger.warning("Beginner analyse error %s: %s", symbol, exc)
        return None


def _run_beginner_scan() -> BeginnerScreenerResponse:
    results: list[BeginnerStock] = []
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        futures = {pool.submit(_analyse_beginner_stock, sym): sym for sym in BEGINNER_UNIVERSE}
        for future in as_completed(futures):
            try:
                r = future.result(timeout=15)
                if r is not None:
                    results.append(r)
            except Exception as exc:
                logger.warning("Beginner parallel error: %s", exc)

    if not results:
        raise HTTPException(status_code=503, detail="Could not fetch market data. Please try again.")

    # Sort: Safe Picks first, then Watchlist, then Too Risky; within group by safety_score desc
    order = {"Safe Pick": 0, "Watchlist": 1, "Too Risky": 2}
    results.sort(key=lambda r: (order.get(r.overall, 9), -r.safety_score))

    return BeginnerScreenerResponse(
        stocks=results,
        scanned_count=len(BEGINNER_UNIVERSE),
        successful_count=len(results),
        scan_timestamp=datetime.utcnow().isoformat(),
        cached=False,
        cache_age_seconds=0,
        next_refresh_seconds=_seconds_until_midnight_ist(),
    )


@router.get("/beginner", response_model=BeginnerScreenerResponse)
def get_beginner_picks(
    force_refresh: bool = False,
    _user: UserModel = Depends(get_current_user),
) -> BeginnerScreenerResponse:
    """Beginner-friendly screener — Nifty 50 stocks with plain-English signals.

    Returns all 30 stocks sorted as: Safe Picks → Watchlist → Too Risky.
    Cached for the full trading day (shared across all users), resets at midnight IST.
    """
    global _beginner_cache, _beginner_cache_ts, _BEGINNER_CACHE_DATE

    today = _today_ist()
    age = int(time.monotonic() - _beginner_cache_ts)
    if _beginner_cache is not None and _BEGINNER_CACHE_DATE == today and not force_refresh:
        return _beginner_cache.model_copy(update={
            "cached": True,
            "cache_age_seconds": age,
            "next_refresh_seconds": _seconds_until_midnight_ist(),
        })

    fresh = _run_beginner_scan()
    _beginner_cache = fresh
    _beginner_cache_ts = time.monotonic()
    _BEGINNER_CACHE_DATE = today
    return fresh
