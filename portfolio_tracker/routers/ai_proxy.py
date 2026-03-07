"""
AI Proxy Router — securely forwards requests to Anthropic on behalf of the frontend.

The Anthropic API key is read from server-side env (ANTHROPIC_API_KEY) and is
NEVER exposed to the browser. The frontend only sends plain market data.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from portfolio_tracker.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Anthropic constants ────────────────────────────────────────────────────────
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL_QUICK = "claude-haiku-4-5-20251001"   # cheap / fast
MODEL_FULL  = "claude-sonnet-4-6"           # full depth

# ── Static (cached) system prompts ────────────────────────────────────────────
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


# ── Request / Response schemas ─────────────────────────────────────────────────
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
    today: str        # formatted date string, sent by client
    ist: str          # current IST time string, sent by client


class AnalyzeRequest(BaseModel):
    market_data: MarketData
    analysis_type: Literal["quick", "full"] = "full"


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


class AnalyzeResponse(BaseModel):
    text: str
    model: str
    usage: TokenUsage


# ── Helper: build the user message from market data ───────────────────────────
def _build_user_message(d: MarketData) -> str:
    try:
        fii_val  = float(d.fiiActivity)
        dii_val  = float(d.diiActivity)
        vix_val  = float(d.vix)
    except ValueError:
        fii_val = dii_val = vix_val = 0.0

    fii_sign = "+" if fii_val >= 0 else ""
    dii_sign = "+" if dii_val >= 0 else ""
    vix_label = (
        "(LOW — options selling favoured)" if vix_val < 12
        else "(MODERATE — balanced)" if vix_val < 16
        else "(HIGH — options buying favoured)"
    )
    fii_dir = "(Net BUYERS)" if fii_val >= 0 else "(Net SELLERS)"
    dii_dir = "(Net BUYERS)" if dii_val >= 0 else "(Net SELLERS)"

    return (
        f"Today's Date: {d.today}\n"
        f"Current IST Time: {d.ist}\n"
        f"Trader Profile: {d.traderExperience} | Max Risk/Trade: {d.capitalRisk}% of capital "
        f"| Session: {d.sessionType}\n\n"
        f"═══ TODAY'S MARKET DATA ═══\n"
        f"Nifty 50 Prev Close : {d.niftyClose}\n"
        f"Bank Nifty Prev Close: {d.bankniftyClose}\n"
        f"Gift Nifty (pre-mkt) : {d.giftNifty}\n"
        f"India VIX            : {d.vix} {vix_label}\n"
        f"FII Net Activity     : ₹{fii_sign}{d.fiiActivity} crore {fii_dir}\n"
        f"DII Net Activity     : ₹{dii_sign}{d.diiActivity} crore {dii_dir}\n"
        f"US Markets (O/N)     : {d.usMarket}%\n"
        f"Crude Oil (WTI)      : ${d.crude}/bbl\n"
        f"Dollar Index (DXY)   : {d.dollarIndex}\n"
        f"Major Events Today   : {d.majorEvents}"
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────
@router.post("/nifty-analyze", response_model=AnalyzeResponse)
async def nifty_analyze(body: AnalyzeRequest) -> AnalyzeResponse:
    """
    Proxies a market analysis request to Anthropic.
    The API key is read from the server environment — never sent to the browser.
    """
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY is not configured on the server. "
                   "Add it to your .env file and restart.",
        )

    model       = MODEL_QUICK if body.analysis_type == "quick" else MODEL_FULL
    system_txt  = SYSTEM_QUICK if body.analysis_type == "quick" else SYSTEM_FULL
    user_msg    = _build_user_message(body.market_data)
    max_tokens  = 500 if body.analysis_type == "quick" else 1600

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        # System prompt is static every day → eligible for prompt caching
        "system": [{"type": "text", "text": system_txt, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user_msg}],
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
        # Enable prompt caching beta
        "anthropic-beta": "prompt-caching-2024-07-31",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)

        data = response.json()

        if response.status_code != 200:
            error_msg = data.get("error", {}).get("message", response.text)
            logger.error("Anthropic API error %s: %s", response.status_code, error_msg)
            raise HTTPException(status_code=502, detail=f"Anthropic error: {error_msg}")

        text = "".join(
            block.get("text", "") for block in data.get("content", [])
            if isinstance(block, dict)
        ) or "No response."

        usage_raw = data.get("usage", {})
        usage = TokenUsage(
            input_tokens=usage_raw.get("input_tokens", 0),
            output_tokens=usage_raw.get("output_tokens", 0),
            cache_read_input_tokens=usage_raw.get("cache_read_input_tokens", 0),
            cache_creation_input_tokens=usage_raw.get("cache_creation_input_tokens", 0),
        )

        logger.info(
            "Nifty AI [%s] in=%d out=%d cache_read=%d",
            model, usage.input_tokens, usage.output_tokens, usage.cache_read_input_tokens,
        )
        return AnalyzeResponse(text=text, model=model, usage=usage)

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Anthropic request timed out (>60s). Try again.")
    except httpx.RequestError as exc:
        logger.exception("Network error calling Anthropic: %s", exc)
        raise HTTPException(status_code=502, detail=f"Network error: {exc}")
