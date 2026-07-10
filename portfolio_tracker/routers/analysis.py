"""Technical analysis and AI recommendation API endpoints.

This module provides real technical analysis using historical price data from Yahoo Finance.
Indicators calculated:
- RSI (Relative Strength Index) - Momentum oscillator (0-100)
- MACD (Moving Average Convergence Divergence) - Trend following
- Bollinger Bands - Volatility indicator
- Moving Averages (SMA 20, 50, 200) - Trend identification
- Volume Analysis - Participation strength
"""

import logging
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from portfolio_tracker import crud, schemas
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import UserModel
from portfolio_tracker.services.technical_indicators import \
    technical_indicators_service

logger = logging.getLogger(__name__)
router = APIRouter()


def calculate_technical_indicators(symbol: str, current_price: float) -> dict:
    """
    Calculate real technical indicators for a given asset using historical price data.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'RELIANCE.NS', 'AAPL')
        current_price: Current market price of the asset
        
    Returns:
        Dictionary containing RSI, MACD, Bollinger Bands, Moving Averages, and Volume analysis
    """
    logger.info(f"Calculating technical indicators for {symbol}")
    
    # Use the real technical indicators service
    indicators = technical_indicators_service.get_all_indicators(symbol, current_price)
    
    return indicators


def generate_ai_recommendation(symbol: str, name: str, indicators: dict, current_price: float, purchase_price: float) -> dict:
    """
    Generate AI-powered buy/sell recommendation based on real technical indicators.
    
    Analysis includes:
    - RSI (overbought/oversold conditions)
    - MACD (momentum and trend direction)
    - Moving Average alignment (trend confirmation)
    - Bollinger Band position (volatility and mean reversion)
    - Volume patterns (participation strength)
    - Position P&L (risk management)
    """
    signals = []
    bullish_score = 0
    bearish_score = 0
    
    # RSI Analysis (Real data)
    rsi = indicators['rsi']
    if rsi < 30:
        signals.append(f"RSI at {rsi:.1f} - in oversold zone (below 30), historically associated with potential reversals")
        bullish_score += 2
    elif rsi < 40:
        signals.append(f"RSI at {rsi:.1f} - approaching oversold levels")
        bullish_score += 1
    elif rsi > 70:
        signals.append(f"RSI at {rsi:.1f} - in overbought zone (above 70), historically associated with potential pullbacks")
        bearish_score += 2
    elif rsi > 60:
        signals.append(f"RSI at {rsi:.1f} - approaching overbought levels")
        bullish_score += 1
    else:
        signals.append(f"RSI at {rsi:.1f} - in neutral zone (30-70)")
    
    # MACD Analysis (Real data)
    macd = indicators['macd']
    macd_hist = macd['histogram']
    macd_value = macd['value']
    macd_signal = macd['signal']
    
    if macd_hist > 0 and macd_value > macd_signal:
        signals.append(f"MACD bullish crossover (histogram: {macd_hist:.2f})")
        bullish_score += 2
    elif macd_hist > 0:
        signals.append(f"MACD histogram positive ({macd_hist:.2f}) - bullish momentum")
        bullish_score += 1
    elif macd_hist < 0 and macd_value < macd_signal:
        signals.append(f"MACD bearish crossover (histogram: {macd_hist:.2f})")
        bearish_score += 2
    else:
        signals.append(f"MACD histogram negative ({macd_hist:.2f}) - bearish momentum")
        bearish_score += 1
    
    # Moving Average Analysis (Real data)
    ma = indicators['moving_averages']
    sma_20 = ma.get('sma_20')
    sma_50 = ma.get('sma_50')
    sma_200 = ma.get('sma_200')
    
    if sma_20 and sma_50 and sma_200:
        if current_price > sma_20 > sma_50 > sma_200:
            signals.append("Perfect bullish alignment: Price > SMA20 > SMA50 > SMA200")
            bullish_score += 3
        elif current_price > sma_20 and current_price > sma_50:
            signals.append("Price above short and medium-term averages - uptrend")
            bullish_score += 2
        elif current_price < sma_20 < sma_50 < sma_200:
            signals.append("Perfect bearish alignment: Price < SMA20 < SMA50 < SMA200")
            bearish_score += 3
        elif current_price < sma_20 and current_price < sma_50:
            signals.append("Price below short and medium-term averages - downtrend")
            bearish_score += 2
        elif sma_50 and current_price > sma_50:
            signals.append("Price above 50-day SMA - medium-term bullish")
            bullish_score += 1
        elif sma_50 and current_price < sma_50:
            signals.append("Price below 50-day SMA - medium-term bearish")
            bearish_score += 1
    elif sma_20:
        if current_price > sma_20:
            signals.append(f"Price above 20-day SMA (₹{sma_20:.2f})")
            bullish_score += 1
        else:
            signals.append(f"Price below 20-day SMA (₹{sma_20:.2f})")
            bearish_score += 1
    
    # Bollinger Bands Analysis (Real data)
    bb = indicators['bollinger_bands']
    bb_width = bb.get('width', 0)
    price_position = indicators.get('price_position', 'unknown')
    
    if price_position == 'below_lower_band':
        signals.append(f"Price at lower Bollinger Band - potential bounce zone")
        bullish_score += 2
    elif price_position == 'above_upper_band':
        signals.append(f"Price at upper Bollinger Band - extended, may pull back")
        bearish_score += 1
    elif price_position == 'lower_half':
        signals.append("Price in lower half of Bollinger Bands")
        bullish_score += 1
    
    if bb_width > 15:
        signals.append(f"High volatility (Band width: {bb_width:.1f}%)")
    elif bb_width < 5:
        signals.append(f"Low volatility squeeze (Band width: {bb_width:.1f}%) - breakout potential")
    
    # Volume Analysis (Real data)
    volume = indicators['volume']
    volume_trend = volume.get('trend', 'unknown')
    volume_ratio = volume.get('ratio', 1.0)
    
    if volume_trend == 'increasing' and volume_ratio > 1.5:
        signals.append(f"Volume surge ({volume_ratio:.1f}x average) - strong participation")
        bullish_score += 1
    elif volume_trend == 'increasing':
        signals.append(f"Volume increasing - building momentum")
    elif volume_trend == 'decreasing' and volume_ratio < 0.5:
        signals.append(f"Volume drying up ({volume_ratio:.1f}x average) - weak conviction")
        bearish_score += 1
    
    # Current Position Analysis (educational only)
    return_pct = ((current_price - purchase_price) / purchase_price) * 100
    if return_pct > 30:
        signals.append(f"Position shows {return_pct:.1f}% unrealized gain")
    elif return_pct > 15:
        signals.append(f"Position shows {return_pct:.1f}% unrealized gain")
    elif return_pct < -15:
        signals.append(f"Position shows {return_pct:.1f}% unrealized loss")
    elif return_pct < -5:
        signals.append(f"Position shows {return_pct:.1f}% unrealized loss")
    
    # Calculate final recommendation - now as educational signals only
    total_score = bullish_score - bearish_score
    
    if total_score >= 5:
        recommendation = "strong_bullish"
        action_text = "Strong Bullish Signal"
        confidence = 0  # Remove confidence to avoid performance claims
    elif total_score >= 2:
        recommendation = "bullish"
        action_text = "Bullish Signal"
        confidence = 0
    elif total_score <= -5:
        recommendation = "strong_bearish"
        action_text = "Strong Bearish Signal"
        confidence = 0
    elif total_score <= -2:
        recommendation = "bearish"
        action_text = "Bearish Signal"
        confidence = 0
    else:
        recommendation = "neutral"
        action_text = "Neutral Signal"
        confidence = 0
    
    return {
        'recommendation': recommendation,
        'action_text': action_text,
        'confidence': confidence,
        'signals': signals,
        'bullish_factors': bullish_score,
        'bearish_factors': bearish_score
    }


@router.get("/analysis", response_model=List[schemas.TechnicalAnalysis])
# Sync `def` so FastAPI runs this in its threadpool: the yfinance fetches below
# are blocking, and an `async def` would stall the whole event loop per call.
def get_technical_analysis(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get real technical analysis and AI recommendations for all user holdings.
    
    Returns comprehensive technical indicators calculated from historical price data:
    - RSI (14-period)
    - MACD (12, 26, 9)
    - Bollinger Bands (20-period, 2 std dev)
    - Moving Averages (SMA 20, 50, 200)
    - Volume analysis
    """
    logger.info(f"Fetching technical analysis for user {user.id}")
    portfolios = crud.get_portfolios(db, user_id=user.id)
    analysis_results = []
    
    for portfolio in portfolios:
        for asset in portfolio.assets:
            current_price = float(asset.current_price)
            purchase_price = float(asset.purchase_price)
            quantity = float(asset.quantity)
            
            # Calculate REAL technical indicators from historical data
            indicators = calculate_technical_indicators(asset.symbol, current_price)
            
            # Generate AI recommendation based on real indicators
            ai_recommendation = generate_ai_recommendation(
                asset.symbol,
                asset.name,
                indicators,
                current_price,
                purchase_price
            )
            
            # Calculate position metrics
            invested_value = purchase_price * quantity
            current_value = current_price * quantity
            gain_loss = current_value - invested_value
            gain_loss_pct = (gain_loss / invested_value) * 100 if invested_value > 0 else 0
            
            analysis_results.append({
                'asset_id': asset.id,
                'symbol': asset.symbol,
                'name': asset.name,
                'portfolio_name': portfolio.name,
                'current_price': current_price,
                'purchase_price': purchase_price,
                'quantity': quantity,
                'invested_value': invested_value,
                'current_value': current_value,
                'gain_loss': gain_loss,
                'gain_loss_percentage': gain_loss_pct,
                'indicators': indicators,
                'recommendation': ai_recommendation['recommendation'],
                'action_text': ai_recommendation['action_text'],
                'confidence': ai_recommendation['confidence'],
                'signals': ai_recommendation['signals'],
                'bullish_factors': ai_recommendation['bullish_factors'],
                'bearish_factors': ai_recommendation['bearish_factors']
            })
    
    return analysis_results


@router.get("/analysis/{asset_id}", response_model=schemas.TechnicalAnalysis)
# Sync `def` (threadpool) — the yfinance history fetch below is blocking.
def get_asset_analysis(
    asset_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed technical analysis for a specific asset.
    """
    # Get asset and verify ownership
    portfolios = crud.get_portfolios(db, user_id=user.id)
    asset = None
    portfolio_name = ""
    
    for portfolio in portfolios:
        for a in portfolio.assets:
            if a.id == asset_id:
                asset = a
                portfolio_name = portfolio.name
                break
        if asset:
            break
    
    if not asset:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Asset not found")
    
    current_price = float(asset.current_price)
    purchase_price = float(asset.purchase_price)
    quantity = float(asset.quantity)
    
    indicators = calculate_technical_indicators(asset.symbol, current_price)
    ai_recommendation = generate_ai_recommendation(
        asset.symbol,
        asset.name,
        indicators,
        current_price,
        purchase_price
    )
    
    invested_value = purchase_price * quantity
    current_value = current_price * quantity
    gain_loss = current_value - invested_value
    gain_loss_pct = (gain_loss / invested_value) * 100 if invested_value > 0 else 0
    
    return {
        'asset_id': asset.id,
        'symbol': asset.symbol,
        'name': asset.name,
        'portfolio_name': portfolio_name,
        'current_price': current_price,
        'purchase_price': purchase_price,
        'quantity': quantity,
        'invested_value': invested_value,
        'current_value': current_value,
        'gain_loss': gain_loss,
        'gain_loss_percentage': gain_loss_pct,
        'indicators': indicators,
        'recommendation': ai_recommendation['recommendation'],
        'action_text': ai_recommendation['action_text'],
        'confidence': ai_recommendation['confidence'],
        'signals': ai_recommendation['signals'],
        'bullish_factors': ai_recommendation['bullish_factors'],
        'bearish_factors': ai_recommendation['bearish_factors']
    }
