"""
AI Proxy Router — securely forwards requests to Anthropic on behalf of the frontend.

Security guarantees:
- Anthropic API key read from server env — NEVER sent to browser.
- Model names NEVER appear in any API response or log message to the client.
- Tier enforced server-side from DB on every request — cannot be spoofed.
- Daily limits + burst rate + monthly circuit breaker all checked BEFORE any API call.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from portfolio_tracker.config import settings
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import OptionsAnalysisLogModel, UserModel

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Server-side model vars — NEVER sent to client ─────────────────────────────
_MODEL_STARTER = os.getenv("MODEL_STARTER", "claude-haiku-4-5-20251001")
_MODEL_PRO      = os.getenv("MODEL_PRO",     "claude-sonnet-4-6")
_MODEL_ELITE    = os.getenv("MODEL_ELITE",   "claude-sonnet-4-6")  # swap to opus when available

# Cost per 1M tokens in USD — server-side only, never returned to client
_MODEL_COST_USD: dict[str, dict[str, float]] = {
    _MODEL_STARTER: {"input": 1.0,  "output": 5.0,  "cache_read": 0.10},
    _MODEL_PRO:     {"input": 3.0,  "output": 15.0, "cache_read": 0.30},
    _MODEL_ELITE:   {"input": 15.0, "output": 75.0, "cache_read": 1.50},
}
_USD_TO_INR = 84

# ── Analysis type → model + token budget ─────────────────────────────────────
_ANALYSIS_MODEL: dict[str, str] = {
    "quick":    _MODEL_STARTER,
    "full":     _MODEL_PRO,
    "advanced": _MODEL_ELITE,
}
_MAX_OUTPUT_TOKENS: dict[str, int] = {
    "quick":    500,
    "full":     1600,
    "advanced": 1400,
}

# ── Tier configuration ────────────────────────────────────────────────────────
_per_user_cooldown: dict[int, float] = {}  # user_id → last call epoch (in-memory)

_TIER_CONFIG: dict[str, dict] = {
    "free": {
        "total_limit":           5,       # lifetime cap (no daily reset), enforced via credits
        "circuit_breaker_inr":   10.0,
        "allowed_types":         {"quick"},
        "credits_per":           {"quick": 1},
        "label":                 "FREE 🆓",
        "cooldown_seconds":      120,     # 2-minute cooldown between calls
    },
    "starter": {
        "daily_limit":           10,
        "circuit_breaker_inr":   80.0,
        "allowed_types":         {"quick"},
        "credits_per":           {"quick": 1},
        "label":                 "STARTER 🥉",
        "cooldown_seconds":      60,      # 1-minute cooldown between calls
    },
    "pro": {
        "daily_limit":           30,
        "circuit_breaker_inr":   240.0,
        "allowed_types":         {"quick", "full"},
        "credits_per":           {"quick": 1, "full": 3},
        "label":                 "PRO ⚡",
        "cooldown_seconds":      0,
    },
    "elite": {
        "daily_limit":           50,
        "circuit_breaker_inr":   650.0,
        "allowed_types":         {"quick", "full", "advanced"},
        "credits_per":           {"quick": 1, "full": 3, "advanced": 5},
        "label":                 "ELITE 🏆",
        "cooldown_seconds":      0,
    },
}

# ── Burst rate limiter (in-memory) — 5 req / 60 s per user ────────────────────
_burst_tracker: dict[int, list[float]] = defaultdict(list)
_BURST_WINDOW = 60
_BURST_MAX    = 5

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

_YF_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
_YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Static prompts (cached server-side by Anthropic) ─────────────────────────
SYSTEM_QUICK = (
    "You are an expert intraday trading analyst for Indian markets.\n"
    "When given today's market data, respond with a concise analysis of exactly 4 points:\n"
    "1. Market Bias — Bullish / Bearish / Sideways with 2-line reasoning\n"
    "2. Key Levels — Nifty & Bank Nifty: top 2 Support and 2 Resistance levels\n"
    "3. Best Trade Setup — ONE setup: Entry zone, Stop Loss, Target 1, Target 2, "
    "preferred CE or PE strike + expiry\n"
    "4. Options Verdict — BUY or SELL options today and why (base it on India VIX)\n"
    "Be concise. 150 words max. No filler text."
)

SYSTEM_FULL = (
    "You are an expert SEBI-registered intraday trading analyst specialising in Indian equity "
    "derivatives — Nifty 50 and Bank Nifty.\n"
    "When given today's market data, produce a complete intraday analysis with the following "
    "7 sections — use emojis, clear section headers, and specific price levels (no vague advice):\n\n"
    "1. 🎯 MARKET BIAS\n"
    "   - Overall direction: Bullish / Bearish / Sideways with 3-line reasoning\n"
    "   - Sentiment score: X/10\n\n"
    "2. 📊 KEY LEVELS\n"
    "   Nifty 50: Strong Support 1 & 2, Strong Resistance 1 & 2, Day's Pivot Point\n"
    "   Bank Nifty: Strong Support 1 & 2, Strong Resistance 1 & 2, Day's Pivot Point\n\n"
    "3. 📈 INTRADAY TRADE SETUPS (2–3 setups)\n"
    "   For EACH: Index, Direction (Long/Short), Entry Zone, Stop Loss (hard SL), "
    "Target 1 & 2, Risk:Reward, Instrument (Futures or CE/PE with strike & expiry), "
    "Best Time Window, Confidence Level\n\n"
    "4. 🧠 OPTIONS STRATEGY\n"
    "   - BUY or SELL options today? Justify with VIX level.\n"
    "   - If BUYING: Best CE or PE strike + expiry\n"
    "   - If SELLING: Best strategy (Iron Condor / Strangle / Credit Spread)\n"
    "   - Respect the capital-risk % supplied by the user. Include expected premium range.\n\n"
    "5. ⚠️ RISK FACTORS\n"
    "   - What invalidates these setups | Sectors / stocks to avoid | "
    "Global risk events during market hours\n\n"
    "6. 🕐 TIMING GUIDE\n"
    "   - Best entry windows (IST) | Chop zones to avoid | Hard exit time rule\n\n"
    "7. 📌 DISCIPLINE REMINDER\n"
    "   - One key mindset tip for today's market condition"
)

SYSTEM_ADVANCED = (
    SYSTEM_FULL + "\n\n"
    "ADDITIONALLY — Advanced Options Section (Elite only):\n\n"
    "8. 🎯 ADVANCED STRATEGIES\n"
    "   - Evaluate and recommend ONE of: Iron Condor / Bull Call Spread / Bear Put Spread / "
    "Synthetic Long/Short — whichever fits today's VIX and trend best.\n"
    "   - Provide: strikes, expiry, max profit, max loss, breakeven points\n"
    "   - Net premium: credit or debit estimate in ₹\n"
    "   - Greeks snapshot: approximate Delta, Theta, Vega impact\n\n"
    "9. 📅 POSITIONAL IDEA (only if strong setup exists)\n"
    "   - If a 3–5 day positional setup is visible: Index, direction, entry, SL, target, instrument\n\n"
    "Keep entire response under 1,400 output tokens."
)

_SYSTEM_MAP: dict[str, str] = {
    "quick":    SYSTEM_QUICK,
    "full":     SYSTEM_FULL,
    "advanced": SYSTEM_ADVANCED,
}


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class MarketData(BaseModel):
    niftyClose: str
    bankniftyClose: str
    giftNifty: str
    vix: str
    fiiActivity: str
    diiActivity: str
    usMarket: str
    crude: str
    dollarIndex: str
    majorEvents: str
    capitalRisk: str
    traderExperience: str
    sessionType: str
    today: str
    ist: str


class AnalyzeRequest(BaseModel):
    market_data: MarketData
    analysis_type: Literal["quick", "full", "advanced"] = "quick"


class TokenUsageResponse(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cost_inr: float = 0.0
    cached: bool = False


class AnalyzeResponse(BaseModel):
    text: str
    usage: TokenUsageResponse
    analyses_today: int
    daily_limit: int
    credits: int
    cooldown_seconds: int = 0   # per-tier cooldown; >0 means wait this many seconds
    # NOTE: model name is intentionally excluded from this response


class UsageResponse(BaseModel):
    tier: str
    tier_label: str
    credits: int
    analyses_today: int
    daily_limit: int
    circuit_breaker_hit: bool
    allowed_types: list[str]
    credits_per_analysis: dict[str, int]
    cooldown_seconds: int = 0   # inter-call cooldown for this tier


# ── Helpers ───────────────────────────────────────────────────────────────────
def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _calc_cost_inr(model: str, input_tok: int, output_tok: int, cache_read_tok: int) -> float:
    prices = _MODEL_COST_USD.get(model, _MODEL_COST_USD[_MODEL_PRO])
    billable_input = max(0, input_tok - cache_read_tok)
    cost_usd = (
        (billable_input   / 1_000_000) * prices["input"]
        + (cache_read_tok / 1_000_000) * prices["cache_read"]
        + (output_tok     / 1_000_000) * prices["output"]
    )
    return round(cost_usd * _USD_TO_INR, 4)


def _reset_daily_if_needed(user: UserModel, today: str, tier: str) -> None:
    # Free tier uses a lifetime total_limit enforced by credits — never reset the counter
    if tier == "free":
        return
    if user.options_analyses_date != today:
        user.options_analyses_today = 0
        user.options_analyses_date = today


def _reset_monthly_if_needed(user: UserModel, month: str) -> None:
    if user.options_ai_cost_month_key != month:
        user.options_ai_cost_month = Decimal("0")
        user.options_ai_cost_month_key = month


def _check_burst(user_id: int) -> None:
    now = time.time()
    window_start = now - _BURST_WINDOW
    calls = _burst_tracker[user_id]
    calls[:] = [t for t in calls if t > window_start]
    if len(calls) >= _BURST_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Max {_BURST_MAX} analyses per {_BURST_WINDOW} seconds.",
        )
    calls.append(now)


def _check_cooldown(user_id: int, tier: str) -> None:
    """Enforce per-tier inter-call cooldown. API-level guard — cannot be bypassed."""
    cooldown_secs: int = _TIER_CONFIG.get(tier, {}).get("cooldown_seconds", 0)
    if cooldown_secs <= 0:
        return
    last = _per_user_cooldown.get(user_id, 0.0)
    wait = cooldown_secs - (time.time() - last)
    if wait > 0:
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {int(wait) + 1}s before your next analysis. Upgrade for no cooldown.",
        )


def _build_user_message(d: MarketData) -> str:
    try:
        fii_val = float(d.fiiActivity)
        dii_val = float(d.diiActivity)
        vix_val = float(d.vix)
    except ValueError:
        fii_val = dii_val = vix_val = 0.0

    fii_sign = "+" if fii_val >= 0 else ""
    dii_sign = "+" if dii_val >= 0 else ""
    vix_label = (
        "(LOW — options selling favoured)" if vix_val < 12
        else "(MODERATE — balanced)" if vix_val < 16
        else "(HIGH — options buying favoured)"
    )
    return (
        f"Today's Date: {d.today}\n"
        f"Current IST Time: {d.ist}\n"
        f"Trader Profile: {d.traderExperience} | Max Risk/Trade: {d.capitalRisk}% of capital "
        f"| Session: {d.sessionType}\n\n"
        f"═══ TODAY'S MARKET DATA ═══\n"
        f"Nifty 50 Prev Close  : {d.niftyClose}\n"
        f"Bank Nifty Prev Close: {d.bankniftyClose}\n"
        f"Gift Nifty (pre-mkt) : {d.giftNifty}\n"
        f"India VIX            : {d.vix} {vix_label}\n"
        f"FII Net Activity     : ₹{fii_sign}{d.fiiActivity} crore "
        f"({'Net BUYERS' if fii_val >= 0 else 'Net SELLERS'})\n"
        f"DII Net Activity     : ₹{dii_sign}{d.diiActivity} crore "
        f"({'Net BUYERS' if dii_val >= 0 else 'Net SELLERS'})\n"
        f"US Markets (O/N)     : {d.usMarket}%\n"
        f"Crude Oil (WTI)      : ${d.crude}/bbl\n"
        f"Dollar Index (DXY)   : {d.dollarIndex}\n"
        f"Major Events Today   : {d.majorEvents}"
    )


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _yf_fetch(client: httpx.AsyncClient, symbol: str) -> dict[str, Any]:
    """Fetch meta block for one Yahoo Finance symbol. Returns {} on any error."""
    try:
        r = await client.get(
            f"{_YF_BASE}/{symbol}",
            params={"range": "1d", "interval": "1d"},
            headers=_YF_HEADERS,
            timeout=8.0,
        )
        if r.status_code != 200:
            return {}
        meta: dict = r.json()["chart"]["result"][0]["meta"]
        return meta
    except Exception:  # noqa: BLE001
        return {}


async def _nse_fii_dii(client: httpx.AsyncClient) -> dict[str, str]:
    """Try to fetch FII/DII data from NSE India. Returns {} on failure."""
    try:
        # Step 1: get a session cookie from the NSE homepage
        await client.get(
            "https://www.nseindia.com",
            headers={**_YF_HEADERS, "Referer": "https://www.google.com/"},
            timeout=8.0,
        )
        # Step 2: fetch FII/DII trade data using that cookie
        r = await client.get(
            "https://www.nseindia.com/api/fiidiiTradeReact",
            headers={**_YF_HEADERS, "Referer": "https://www.nseindia.com/"},
            timeout=8.0,
        )
        if r.status_code != 200:
            return {}
        rows: list[dict] = r.json()
        fii_net = dii_net = None
        for row in rows:
            cat = row.get("category", "").upper()
            # The API returns nested buy/sell values; net = buyValue - sellValue
            if "FII" in cat or "FPI" in cat:
                fii_net = float(row.get("netValue", 0) or 0)
            elif "DII" in cat:
                dii_net = float(row.get("netValue", 0) or 0)
        result: dict[str, str] = {}
        if fii_net is not None:
            result["fiiActivity"] = f"{fii_net:+.0f}"
        if dii_net is not None:
            result["diiActivity"] = f"{dii_net:+.0f}"
        return result
    except Exception:  # noqa: BLE001
        return {}


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/market-snapshot")
async def market_snapshot(
    user: UserModel = Depends(get_current_user),
) -> dict[str, str]:
    """
    Returns live market data fetched from free public sources (Yahoo Finance + NSE India).
    - Nifty 50: live price then previous close fallback (^NSEI)
    - BankNifty: live price then previous close fallback (^NSEBANK)
    - India VIX: current reading (^INDIAVIX)
    - Crude WTI: current price (CL=F)
    - Dollar Index: current price (DX-Y.NYB)
    - US Market: S&P 500 overnight % change (^GSPC)
    - Gift Nifty: tried via GIFT_NIFTY.NS; falls back to ^NSEI live price
      (Gift Nifty trades at near-parity with Nifty spot)
    - FII/DII: NSE India API (best-effort, skipped if unavailable)
    Only fields that successfully resolved are returned; frontend keeps its current value for misses.
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        nifty_m, bnk_m, vix_m, crude_m, dxy_m, sp_m, gift_m, fii_dii = await asyncio.gather(
            _yf_fetch(client, "^NSEI"),
            _yf_fetch(client, "^NSEBANK"),
            _yf_fetch(client, "^INDIAVIX"),
            _yf_fetch(client, "CL=F"),
            _yf_fetch(client, "DX-Y.NYB"),
            _yf_fetch(client, "^GSPC"),
            _yf_fetch(client, "NIFTY25MARFUT.NS"),  # near-month futures; falls back below
            _nse_fii_dii(client),
        )

    result: dict[str, str] = {}

    # Nifty 50 — prefer live price, fall back to previous close
    nifty_price = (
        nifty_m.get("regularMarketPrice")
        or nifty_m.get("regularMarketPreviousClose")
    )
    if nifty_price:
        result["niftyClose"] = f"{nifty_price:.2f}"

    # BankNifty — same logic
    bnk_price = (
        bnk_m.get("regularMarketPrice")
        or bnk_m.get("regularMarketPreviousClose")
    )
    if bnk_price:
        result["bankniftyClose"] = f"{bnk_price:.2f}"

    if vix_m.get("regularMarketPrice"):
        result["vix"] = f"{vix_m['regularMarketPrice']:.2f}"
    if crude_m.get("regularMarketPrice"):
        result["crude"] = f"{crude_m['regularMarketPrice']:.2f}"
    if dxy_m.get("regularMarketPrice"):
        result["dollarIndex"] = f"{dxy_m['regularMarketPrice']:.2f}"
    if sp_m.get("regularMarketChangePercent") is not None:
        pct: float = sp_m["regularMarketChangePercent"]
        result["usMarket"] = f"{pct:+.2f}"

    # Gift Nifty — try near-month futures ticker; if 404/unavailable fall back to Nifty live
    gift_price = gift_m.get("regularMarketPrice")
    if not gift_price:
        gift_price = nifty_price  # near-parity proxy
    if gift_price:
        result["giftNifty"] = f"{gift_price:.0f}"

    result.update(fii_dii)  # FII/DII if available
    return result


@router.get("/usage", response_model=UsageResponse)
def get_usage(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageResponse:
    today = _today_key()
    month = _month_key()
    tier = user.options_tier or "free"
    _reset_daily_if_needed(user, today, tier)
    _reset_monthly_if_needed(user, month)
    db.commit()
    cfg = _TIER_CONFIG.get(tier, _TIER_CONFIG["free"])
    circuit_hit = float(user.options_ai_cost_month or 0) >= cfg["circuit_breaker_inr"]
    daily_limit = cfg.get("daily_limit", cfg.get("total_limit", 5))

    return UsageResponse(
        tier=tier,
        tier_label=cfg["label"],
        credits=user.options_credits or 0,
        analyses_today=user.options_analyses_today or 0,
        daily_limit=daily_limit,
        circuit_breaker_hit=circuit_hit,
        allowed_types=sorted(cfg["allowed_types"]),
        credits_per_analysis=cfg["credits_per"],
        cooldown_seconds=cfg.get("cooldown_seconds", 0),
    )


@router.post("/nifty-analyze", response_model=AnalyzeResponse)
async def nifty_analyze(
    body: AnalyzeRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service is not configured on this server.")

    tier = user.options_tier or "free"
    cfg  = _TIER_CONFIG.get(tier, _TIER_CONFIG["free"])
    analysis_type = body.analysis_type

    # 1. Analysis type allowed for this tier?
    if analysis_type not in cfg["allowed_types"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Your {cfg['label']} plan does not include {analysis_type} analysis. "
                "Upgrade your plan to unlock this feature."
            ),
        )

    # 2. Burst rate check
    _check_burst(user.id)

    # 2b. Per-call cooldown (free/starter tier: 60s between calls — API-level, un-bypassable)
    _check_cooldown(user.id, tier)

    # 3. Reset daily / monthly counters if period has rolled over
    today = _today_key()
    month = _month_key()
    _reset_daily_if_needed(user, today, tier)
    _reset_monthly_if_needed(user, month)

    # 4. Daily/total limit check
    limit = cfg.get("daily_limit") or cfg.get("total_limit", 5)
    if (user.options_analyses_today or 0) >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"{'Lifetime' if tier == 'free' else 'Daily'} limit of {limit} analyses reached. "
                   f"{'Purchase a credit pack or upgrade' if tier == 'free' else 'Resets at midnight UTC'}.",
        )

    # 5. Monthly circuit breaker
    if float(user.options_ai_cost_month or 0) >= cfg["circuit_breaker_inr"]:
        raise HTTPException(
            status_code=402,
            detail="Monthly analysis quota reached. Upgrade your plan or purchase credits to continue.",
        )

    # 6. Credits check
    credits_needed = cfg["credits_per"].get(analysis_type, 1)
    if (user.options_credits or 0) < credits_needed:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Insufficient credits. {analysis_type.title()} analysis costs "
                f"{credits_needed} credit(s). Purchase a credit pack to continue."
            ),
        )

    # 7. Select model server-side — NEVER from request body
    model      = _ANALYSIS_MODEL[analysis_type]
    system_txt = _SYSTEM_MAP[analysis_type]
    user_msg   = _build_user_message(body.market_data)
    max_tokens = _MAX_OUTPUT_TOKENS[analysis_type]

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": system_txt, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user_msg}],
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
        "anthropic-beta": "prompt-caching-2024-07-31",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)

        data = response.json()
        if response.status_code != 200:
            error_msg = data.get("error", {}).get("message", "Unknown error")
            logger.error("AI API error %s: %s", response.status_code, error_msg)
            raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Analysis timed out. Please try again.")
    except httpx.RequestError as exc:
        logger.exception("Network error calling AI service: %s", exc)
        raise HTTPException(status_code=502, detail="Network error. Please try again.")

    text = "".join(
        block.get("text", "") for block in data.get("content", [])
        if isinstance(block, dict)
    ) or "No response."

    usage_raw  = data.get("usage", {})
    inp        = usage_raw.get("input_tokens", 0)
    out        = usage_raw.get("output_tokens", 0)
    cache_read = usage_raw.get("cache_read_input_tokens", 0)
    cache_write = usage_raw.get("cache_creation_input_tokens", 0)
    cost_inr   = _calc_cost_inr(model, inp, out, cache_read)

    # 8. Update user record atomically
    user.options_credits          = max(0, (user.options_credits or 0) - credits_needed)
    user.options_analyses_today   = (user.options_analyses_today or 0) + 1
    user.options_analyses_date    = today
    user.options_ai_cost_month    = Decimal(str(float(user.options_ai_cost_month or 0) + cost_inr))
    user.options_ai_cost_month_key = month

    # 9. Audit log — metadata only, no prompt content
    db.add(OptionsAnalysisLogModel(
        user_id=user.id,
        tier=tier,
        analysis_type=analysis_type,
        input_tokens=inp,
        output_tokens=out,
        cache_read_tokens=cache_read,
        ai_cost_inr=Decimal(str(cost_inr)),
    ))
    db.commit()

    # Record cooldown timestamp AFTER successful commit
    cooldown_secs: int = cfg.get("cooldown_seconds", 0)
    if cooldown_secs > 0:
        _per_user_cooldown[user.id] = time.time()

    logger.info(
        "Options AI [user=%d tier=%s type=%s] in=%d out=%d cache=%d cost=₹%.4f",
        user.id, tier, analysis_type, inp, out, cache_read, cost_inr,
    )

    return AnalyzeResponse(
        text=text,
        usage=TokenUsageResponse(
            input_tokens=inp,
            output_tokens=out,
            cache_read_input_tokens=cache_read,
            cache_creation_input_tokens=cache_write,
            cost_inr=cost_inr,
            cached=cache_read > 0,
        ),
        analyses_today=user.options_analyses_today,
        daily_limit=cfg.get("daily_limit") or cfg.get("total_limit", 5),
        credits=user.options_credits,
        cooldown_seconds=cooldown_secs,
    )
