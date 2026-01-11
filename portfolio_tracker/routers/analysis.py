"""Technical analysis and AI recommendation API endpoints."""

import random
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from portfolio_tracker import crud, schemas
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import UserModel

router = APIRouter()


def calculate_technical_indicators(symbol: str, current_price: float) -> dict:
    """
    Calculate technical indicators for a given asset.
    In production, integrate with actual market data APIs (e.g., Alpha Vantage, Yahoo Finance).
    """
    # Simulated technical indicators (replace with real API calls)
    # These would come from historical price data analysis
    
    # RSI (Relative Strength Index) - 0-100 scale
    rsi = random.uniform(30, 70)
    
    # MACD (Moving Average Convergence Divergence)
    macd_value = random.uniform(-5, 5)
    macd_signal = random.uniform(-5, 5)
    macd_histogram = macd_value - macd_signal
    
    # Moving Averages
    sma_20 = current_price * random.uniform(0.95, 1.05)
    sma_50 = current_price * random.uniform(0.92, 1.08)
    sma_200 = current_price * random.uniform(0.85, 1.15)
    
    # Bollinger Bands
    bb_upper = current_price * 1.05
    bb_middle = current_price
    bb_lower = current_price * 0.95
    
    # Volume analysis (simulated)
    volume_trend = random.choice(['increasing', 'decreasing', 'stable'])
    avg_volume = random.randint(100000, 10000000)
    
    return {
        'rsi': round(rsi, 2),
        'macd': {
            'value': round(macd_value, 2),
            'signal': round(macd_signal, 2),
            'histogram': round(macd_histogram, 2)
        },
        'moving_averages': {
            'sma_20': round(sma_20, 2),
            'sma_50': round(sma_50, 2),
            'sma_200': round(sma_200, 2)
        },
        'bollinger_bands': {
            'upper': round(bb_upper, 2),
            'middle': round(bb_middle, 2),
            'lower': round(bb_lower, 2)
        },
        'volume': {
            'trend': volume_trend,
            'average': avg_volume
        }
    }


def generate_ai_recommendation(symbol: str, name: str, indicators: dict, current_price: float, purchase_price: float) -> dict:
    """
    Generate AI-powered buy/sell recommendation based on technical indicators.
    In production, integrate with OpenAI, Anthropic, or custom ML models.
    """
    signals = []
    bullish_score = 0
    bearish_score = 0
    
    # RSI Analysis
    rsi = indicators['rsi']
    if rsi < 30:
        signals.append("RSI indicates oversold conditions - potential buying opportunity")
        bullish_score += 2
    elif rsi > 70:
        signals.append("RSI indicates overbought conditions - consider taking profits")
        bearish_score += 2
    elif 40 <= rsi <= 60:
        signals.append("RSI in neutral zone - no strong directional signal")
    
    # MACD Analysis
    macd_hist = indicators['macd']['histogram']
    if macd_hist > 0:
        signals.append("MACD histogram positive - bullish momentum")
        bullish_score += 1
    else:
        signals.append("MACD histogram negative - bearish momentum")
        bearish_score += 1
    
    # Moving Average Analysis
    ma = indicators['moving_averages']
    if current_price > ma['sma_20'] > ma['sma_50']:
        signals.append("Price above key moving averages - uptrend confirmed")
        bullish_score += 2
    elif current_price < ma['sma_20'] < ma['sma_50']:
        signals.append("Price below key moving averages - downtrend confirmed")
        bearish_score += 2
    
    # Bollinger Bands Analysis
    bb = indicators['bollinger_bands']
    if current_price <= bb['lower']:
        signals.append("Price at lower Bollinger Band - potential reversal zone")
        bullish_score += 1
    elif current_price >= bb['upper']:
        signals.append("Price at upper Bollinger Band - resistance area")
        bearish_score += 1
    
    # Volume Analysis
    if indicators['volume']['trend'] == 'increasing':
        signals.append(f"Volume trend: {indicators['volume']['trend']} - strong participation")
        bullish_score += 1
    
    # Current Position Analysis
    return_pct = ((current_price - purchase_price) / purchase_price) * 100
    if return_pct > 20:
        signals.append(f"Current position up {return_pct:.1f}% - consider partial profit booking")
        bearish_score += 1
    elif return_pct < -10:
        signals.append(f"Current position down {return_pct:.1f}% - evaluate stop-loss levels")
    
    # Determine recommendation
    total_score = bullish_score - bearish_score
    if total_score >= 3:
        recommendation = "strong_buy"
        action_text = "Strong Buy"
        confidence = min(90, 70 + (total_score * 5))
    elif total_score >= 1:
        recommendation = "buy"
        action_text = "Buy"
        confidence = min(80, 65 + (total_score * 5))
    elif total_score <= -3:
        recommendation = "strong_sell"
        action_text = "Strong Sell"
        confidence = min(90, 70 + (abs(total_score) * 5))
    elif total_score <= -1:
        recommendation = "sell"
        action_text = "Sell"
        confidence = min(80, 65 + (abs(total_score) * 5))
    else:
        recommendation = "hold"
        action_text = "Hold"
        confidence = 60
    
    return {
        'recommendation': recommendation,
        'action_text': action_text,
        'confidence': confidence,
        'signals': signals,
        'bullish_factors': bullish_score,
        'bearish_factors': bearish_score
    }


@router.get("/analysis", response_model=List[schemas.TechnicalAnalysis])
async def get_technical_analysis(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get technical analysis and AI recommendations for all user holdings.
    """
    portfolios = crud.get_portfolios(db, user_id=user.id)
    analysis_results = []
    
    for portfolio in portfolios:
        for asset in portfolio.assets:
            current_price = float(asset.current_price)
            purchase_price = float(asset.purchase_price)
            quantity = float(asset.quantity)
            
            # Calculate technical indicators
            indicators = calculate_technical_indicators(asset.symbol, current_price)
            
            # Generate AI recommendation
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
async def get_asset_analysis(
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
