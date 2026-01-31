"""
Technical Indicators Service - Real calculations using historical price data.

Calculates:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Moving Averages (SMA 20, 50, 200)
- Volume Analysis
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class TechnicalIndicatorsService:
    """Service for calculating real technical indicators from historical price data."""

    # Cache for historical data (symbol -> (data, timestamp))
    _cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}
    CACHE_DURATION = timedelta(minutes=15)  # Cache data for 15 minutes

    @classmethod
    def _get_historical_data(
        cls, symbol: str, period: str = "1y", interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data from Yahoo Finance with caching.

        Args:
            symbol: Stock ticker symbol (e.g., 'RELIANCE.NS', 'AAPL')
            period: Time period ('1mo', '3mo', '6mo', '1y', '2y')
            interval: Data interval ('1d', '1wk', '1mo')

        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        cache_key = f"{symbol}_{period}_{interval}"

        # Check cache
        if cache_key in cls._cache:
            data, timestamp = cls._cache[cache_key]
            if datetime.now() - timestamp < cls.CACHE_DURATION:
                logger.debug(f"Using cached data for {symbol}")
                return data

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                logger.warning(f"No historical data found for {symbol}")
                return None

            # Cache the data
            cls._cache[cache_key] = (df, datetime.now())
            logger.info(f"Fetched {len(df)} days of data for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """
        Calculate Relative Strength Index (RSI).

        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss over period

        Args:
            prices: Series of closing prices
            period: RSI period (default 14)

        Returns:
            RSI value (0-100)
        """
        if len(prices) < period + 1:
            return 50.0  # Neutral if insufficient data

        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = (-delta).where(delta < 0, 0.0)

        # Calculate average gains and losses using EMA (Wilder's smoothing)
        avg_gain = gains.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = losses.ewm(alpha=1 / period, min_periods=period).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Return the latest RSI value
        latest_rsi = rsi.iloc[-1]
        return round(float(latest_rsi), 2) if not np.isnan(latest_rsi) else 50.0

    @staticmethod
    def calculate_macd(
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Dict[str, float]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        MACD Line = 12-day EMA - 26-day EMA
        Signal Line = 9-day EMA of MACD Line
        Histogram = MACD Line - Signal Line

        Args:
            prices: Series of closing prices
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)

        Returns:
            Dictionary with 'value', 'signal', and 'histogram'
        """
        if len(prices) < slow_period + signal_period:
            return {"value": 0.0, "signal": 0.0, "histogram": 0.0}

        # Calculate EMAs
        ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=slow_period, adjust=False).mean()

        # MACD Line
        macd_line = ema_fast - ema_slow

        # Signal Line
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

        # Histogram
        histogram = macd_line - signal_line

        return {
            "value": round(float(macd_line.iloc[-1]), 2),
            "signal": round(float(signal_line.iloc[-1]), 2),
            "histogram": round(float(histogram.iloc[-1]), 2),
        }

    @staticmethod
    def calculate_bollinger_bands(
        prices: pd.Series, period: int = 20, std_dev: float = 2.0
    ) -> Dict[str, float]:
        """
        Calculate Bollinger Bands.

        Middle Band = 20-day SMA
        Upper Band = Middle Band + (2 * 20-day Standard Deviation)
        Lower Band = Middle Band - (2 * 20-day Standard Deviation)

        Args:
            prices: Series of closing prices
            period: Moving average period (default 20)
            std_dev: Number of standard deviations (default 2)

        Returns:
            Dictionary with 'upper', 'middle', 'lower', and 'width'
        """
        if len(prices) < period:
            current_price = float(prices.iloc[-1])
            return {
                "upper": round(current_price * 1.05, 2),
                "middle": round(current_price, 2),
                "lower": round(current_price * 0.95, 2),
                "width": 10.0,
            }

        # Calculate middle band (SMA)
        middle = prices.rolling(window=period).mean()

        # Calculate standard deviation
        std = prices.rolling(window=period).std()

        # Calculate upper and lower bands
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        # Band width as percentage
        width = ((upper.iloc[-1] - lower.iloc[-1]) / middle.iloc[-1]) * 100

        return {
            "upper": round(float(upper.iloc[-1]), 2),
            "middle": round(float(middle.iloc[-1]), 2),
            "lower": round(float(lower.iloc[-1]), 2),
            "width": round(float(width), 2),
        }

    @staticmethod
    def calculate_moving_averages(prices: pd.Series) -> Dict[str, Optional[float]]:
        """
        Calculate Simple Moving Averages (SMA).

        Args:
            prices: Series of closing prices

        Returns:
            Dictionary with 'sma_20', 'sma_50', 'sma_200'
        """
        result = {"sma_20": None, "sma_50": None, "sma_200": None}

        if len(prices) >= 20:
            result["sma_20"] = round(float(prices.rolling(window=20).mean().iloc[-1]), 2)

        if len(prices) >= 50:
            result["sma_50"] = round(float(prices.rolling(window=50).mean().iloc[-1]), 2)

        if len(prices) >= 200:
            result["sma_200"] = round(
                float(prices.rolling(window=200).mean().iloc[-1]), 2
            )

        return result

    @staticmethod
    def analyze_volume(volumes: pd.Series, prices: pd.Series) -> Dict[str, any]:
        """
        Analyze volume patterns.

        Args:
            volumes: Series of volume data
            prices: Series of closing prices

        Returns:
            Dictionary with volume analysis
        """
        if len(volumes) < 20:
            return {
                "trend": "unknown",
                "average": 0,
                "current": 0,
                "ratio": 1.0,
            }

        avg_volume = volumes.rolling(window=20).mean().iloc[-1]
        current_volume = volumes.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Determine trend based on recent vs average volume
        recent_avg = volumes.tail(5).mean()
        older_avg = volumes.tail(20).head(15).mean()

        if recent_avg > older_avg * 1.2:
            trend = "increasing"
        elif recent_avg < older_avg * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "average": int(avg_volume),
            "current": int(current_volume),
            "ratio": round(float(volume_ratio), 2),
        }

    @classmethod
    def get_all_indicators(cls, symbol: str, current_price: float = None) -> Dict:
        """
        Calculate all technical indicators for a symbol.

        Args:
            symbol: Stock ticker symbol
            current_price: Current price (optional, will be fetched if not provided)

        Returns:
            Dictionary with all technical indicators
        """
        # Fetch historical data
        df = cls._get_historical_data(symbol, period="1y", interval="1d")

        if df is None or df.empty:
            logger.warning(f"No data available for {symbol}, using fallback values")
            price = current_price or 100.0
            return cls._get_fallback_indicators(price)

        close_prices = df["Close"]
        volumes = df["Volume"]

        # Use actual current price if not provided
        if current_price is None:
            current_price = float(close_prices.iloc[-1])

        # Calculate all indicators
        rsi = cls.calculate_rsi(close_prices)
        macd = cls.calculate_macd(close_prices)
        bollinger = cls.calculate_bollinger_bands(close_prices)
        moving_avgs = cls.calculate_moving_averages(close_prices)
        volume_analysis = cls.analyze_volume(volumes, close_prices)

        # Add price position relative to bands
        price_position = cls._calculate_price_position(current_price, bollinger)

        return {
            "rsi": rsi,
            "macd": macd,
            "moving_averages": moving_avgs,
            "bollinger_bands": bollinger,
            "volume": volume_analysis,
            "price_position": price_position,
            "data_points": len(df),
            "last_updated": datetime.now().isoformat(),
        }

    @staticmethod
    def _calculate_price_position(price: float, bollinger: Dict) -> str:
        """Determine price position relative to Bollinger Bands."""
        if price >= bollinger["upper"]:
            return "above_upper_band"
        elif price <= bollinger["lower"]:
            return "below_lower_band"
        elif price > bollinger["middle"]:
            return "upper_half"
        else:
            return "lower_half"

    @staticmethod
    def _get_fallback_indicators(price: float) -> Dict:
        """Return neutral indicators when data is unavailable."""
        return {
            "rsi": 50.0,
            "macd": {"value": 0.0, "signal": 0.0, "histogram": 0.0},
            "moving_averages": {
                "sma_20": round(price, 2),
                "sma_50": round(price, 2),
                "sma_200": round(price, 2),
            },
            "bollinger_bands": {
                "upper": round(price * 1.05, 2),
                "middle": round(price, 2),
                "lower": round(price * 0.95, 2),
                "width": 10.0,
            },
            "volume": {
                "trend": "unknown",
                "average": 0,
                "current": 0,
                "ratio": 1.0,
            },
            "price_position": "unknown",
            "data_points": 0,
            "last_updated": datetime.now().isoformat(),
        }


# Singleton instance
technical_indicators_service = TechnicalIndicatorsService()
