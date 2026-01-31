"""Market data service using Yahoo Finance."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import yfinance as yf

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching live market data from Yahoo Finance."""
    
    @staticmethod
    def get_stock_info(symbol: str) -> Optional[Dict]:
        """
        Get comprehensive stock information including current price and company name.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'RELIANCE.NS', 'AAPL', 'TCS.BO')
            
        Returns:
            Dictionary with stock info or None if not found
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if valid data returned
            if not info or 'regularMarketPrice' not in info:
                logger.warning(f"No market data found for symbol: {symbol}")
                return None
            
            return {
                'symbol': symbol,
                'name': info.get('longName') or info.get('shortName', symbol),
                'current_price': info.get('regularMarketPrice') or info.get('currentPrice', 0),
                'currency': info.get('currency', 'INR'),
                'exchange': info.get('exchange', ''),
                'market_cap': info.get('marketCap', 0),
                'previous_close': info.get('previousClose', 0),
                'day_high': info.get('dayHigh', 0),
                'day_low': info.get('dayLow', 0),
                'volume': info.get('volume', 0),
                'updated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    @staticmethod
    def get_current_price(symbol: str) -> Optional[float]:
        """
        Get just the current price for a symbol (faster than full info).
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Current price as float or None if not found
        """
        try:
            ticker = yf.Ticker(symbol)
            # Use fast_info for quicker price lookup
            try:
                return float(ticker.fast_info['lastPrice'])
            except:
                # Fallback to regular info
                info = ticker.info
                return info.get('regularMarketPrice') or info.get('currentPrice')
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None
    
    @staticmethod
    def search_stocks(query: str, market: str = 'IN') -> List[Dict]:
        """
        Search for stocks by name or symbol with live Yahoo Finance validation.
        
        Args:
            query: Search term (company name or symbol)
            market: Market to search ('IN' for India, 'US' for USA)
            
        Returns:
            List of matching stocks with symbol, name, and current price
        """
        results = []
        query_upper = query.upper().strip()
        
        if not query_upper or len(query_upper) < 2:
            return []
        
        # Common Indian stocks (NSE) - expanded list
        if market == 'IN':
            indian_stocks = [
                # Top 50 NSE stocks
                ('RELIANCE.NS', 'Reliance Industries Limited'),
                ('TCS.NS', 'Tata Consultancy Services Limited'),
                ('HDFCBANK.NS', 'HDFC Bank Limited'),
                ('INFY.NS', 'Infosys Limited'),
                ('ICICIBANK.NS', 'ICICI Bank Limited'),
                ('HINDUNILVR.NS', 'Hindustan Unilever Limited'),
                ('SBIN.NS', 'State Bank of India'),
                ('BHARTIARTL.NS', 'Bharti Airtel Limited'),
                ('ITC.NS', 'ITC Limited'),
                ('KOTAKBANK.NS', 'Kotak Mahindra Bank Limited'),
                ('LT.NS', 'Larsen & Toubro Limited'),
                ('AXISBANK.NS', 'Axis Bank Limited'),
                ('ASIANPAINT.NS', 'Asian Paints Limited'),
                ('MARUTI.NS', 'Maruti Suzuki India Limited'),
                ('TITAN.NS', 'Titan Company Limited'),
                ('SUNPHARMA.NS', 'Sun Pharmaceutical Industries Limited'),
                ('WIPRO.NS', 'Wipro Limited'),
                ('ULTRACEMCO.NS', 'UltraTech Cement Limited'),
                ('NESTLEIND.NS', 'Nestle India Limited'),
                ('BAJFINANCE.NS', 'Bajaj Finance Limited'),
                ('HCLTECH.NS', 'HCL Technologies Limited'),
                ('TATAMOTORS.NS', 'Tata Motors Limited'),
                ('BAJAJFINSV.NS', 'Bajaj Finserv Limited'),
                ('TECHM.NS', 'Tech Mahindra Limited'),
                ('ADANIPORTS.NS', 'Adani Ports and Special Economic Zone Limited'),
                ('POWERGRID.NS', 'Power Grid Corporation of India Limited'),
                ('NTPC.NS', 'NTPC Limited'),
                ('ONGC.NS', 'Oil and Natural Gas Corporation Limited'),
                ('COALINDIA.NS', 'Coal India Limited'),
                ('TATASTEEL.NS', 'Tata Steel Limited'),
                ('HINDALCO.NS', 'Hindalco Industries Limited'),
                ('JSWSTEEL.NS', 'JSW Steel Limited'),
                ('VEDL.NS', 'Vedanta Limited'),
                ('GRASIM.NS', 'Grasim Industries Limited'),
                ('CIPLA.NS', 'Cipla Limited'),
                ('DRREDDY.NS', 'Dr. Reddy\'s Laboratories Limited'),
                ('DIVISLAB.NS', 'Divi\'s Laboratories Limited'),
                ('EICHERMOT.NS', 'Eicher Motors Limited'),
                ('HEROMOTOCO.NS', 'Hero MotoCorp Limited'),
                ('M&M.NS', 'Mahindra & Mahindra Limited'),
                ('SHREECEM.NS', 'Shree Cement Limited'),
                ('BRITANNIA.NS', 'Britannia Industries Limited'),
                ('INDUSINDBK.NS', 'IndusInd Bank Limited'),
                ('BAJAJ-AUTO.NS', 'Bajaj Auto Limited'),
                ('ADANIENT.NS', 'Adani Enterprises Limited'),
            ]
            
            # Filter matches from database
            for symbol, name in indian_stocks:
                if query_upper in symbol.upper() or query_upper in name.upper():
                    # Try to fetch live price for matched stocks
                    stock_info = MarketDataService.get_stock_info(symbol)
                    if stock_info:
                        results.append({
                            'symbol': symbol,
                            'name': name,
                            'exchange': 'NSE',
                            'current_price': stock_info.get('current_price', 0),
                            'currency': stock_info.get('currency', 'INR')
                        })
                    else:
                        # If live fetch fails, still show the stock
                        results.append({
                            'symbol': symbol, 
                            'name': name, 
                            'exchange': 'NSE',
                            'current_price': None,
                            'currency': 'INR'
                        })
            
            # If no matches, try direct symbol lookup (user typed exact symbol)
            if not results:
                test_symbol = f"{query_upper}.NS"
                stock_info = MarketDataService.get_stock_info(test_symbol)
                if stock_info:
                    results.append({
                        'symbol': test_symbol,
                        'name': stock_info.get('name', query_upper),
                        'exchange': 'NSE',
                        'current_price': stock_info.get('current_price', 0),
                        'currency': stock_info.get('currency', 'INR')
                    })
        
        # Common US stocks
        elif market == 'US':
            us_stocks = [
                ('AAPL', 'Apple Inc.'),
                ('MSFT', 'Microsoft Corporation'),
                ('GOOGL', 'Alphabet Inc.'),
                ('AMZN', 'Amazon.com Inc.'),
                ('TSLA', 'Tesla Inc.'),
                ('META', 'Meta Platforms Inc.'),
                ('NVDA', 'NVIDIA Corporation'),
                ('BRK-B', 'Berkshire Hathaway Inc.'),
                ('V', 'Visa Inc.'),
                ('JPM', 'JPMorgan Chase & Co.'),
                ('WMT', 'Walmart Inc.'),
                ('MA', 'Mastercard Incorporated'),
                ('PG', 'Procter & Gamble Company'),
                ('HD', 'The Home Depot Inc.'),
                ('DIS', 'The Walt Disney Company'),
                ('NFLX', 'Netflix Inc.'),
                ('PYPL', 'PayPal Holdings Inc.'),
                ('INTC', 'Intel Corporation'),
                ('CSCO', 'Cisco Systems Inc.'),
                ('ADBE', 'Adobe Inc.'),
            ]
            
            for symbol, name in us_stocks:
                if query_upper in symbol.upper() or query_upper in name.upper():
                    stock_info = MarketDataService.get_stock_info(symbol)
                    if stock_info:
                        results.append({
                            'symbol': symbol,
                            'name': name,
                            'exchange': 'NASDAQ/NYSE',
                            'current_price': stock_info.get('current_price', 0),
                            'currency': stock_info.get('currency', 'USD')
                        })
                    else:
                        results.append({
                            'symbol': symbol, 
                            'name': name, 
                            'exchange': 'NASDAQ/NYSE',
                            'current_price': None,
                            'currency': 'USD'
                        })
            
            # Direct symbol lookup for US stocks
            if not results:
                stock_info = MarketDataService.get_stock_info(query_upper)
                if stock_info:
                    results.append({
                        'symbol': query_upper,
                        'name': stock_info.get('name', query_upper),
                        'exchange': 'NASDAQ/NYSE',
                        'current_price': stock_info.get('current_price', 0),
                        'currency': stock_info.get('currency', 'USD')
                    })
        
        return results[:15]  # Return top 15 matches
    
    @staticmethod
    def format_symbol(symbol: str, exchange: str = 'NSE') -> str:
        """
        Format symbol with proper suffix for Yahoo Finance.
        
        Args:
            symbol: Base stock symbol (e.g., 'RELIANCE')
            exchange: Exchange name ('NSE', 'BSE', or leave empty for US)
            
        Returns:
            Formatted symbol (e.g., 'RELIANCE.NS', 'RELIANCE.BO', or 'AAPL')
        """
        symbol = symbol.upper().strip()
        
        # Already has suffix
        if '.' in symbol:
            return symbol
        
        # Add appropriate suffix
        if exchange == 'NSE':
            return f"{symbol}.NS"
        elif exchange == 'BSE':
            return f"{symbol}.BO"
        else:
            return symbol  # US stocks don't need suffix
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """
        Check if a symbol is valid and tradeable.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            True if symbol is valid, False otherwise
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return 'regularMarketPrice' in info or 'currentPrice' in info
        except:
            return False


# Singleton instance
market_data_service = MarketDataService()
