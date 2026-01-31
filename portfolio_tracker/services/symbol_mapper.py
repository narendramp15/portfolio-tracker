"""Symbol mapping service for broker-to-Yahoo Finance compatibility."""

import logging
from typing import Optional

from portfolio_tracker.services.market_data import market_data_service

logger = logging.getLogger(__name__)


class SymbolMapper:
    """Maps broker symbols to Yahoo Finance compatible symbols."""
    
    # Common exchange mappings for Indian brokers
    EXCHANGE_SUFFIX_MAP = {
        'NSE': '.NS',
        'BSE': '.BO',
        'NFO': '.NS',  # NSE Futures & Options
        'BFO': '.BO',  # BSE Futures & Options
        'MCX': '',     # MCX commodities (not supported by Yahoo)
        'CDS': '',     # Currency derivatives (not supported by Yahoo)
    }
    
    @staticmethod
    def normalize_broker_symbol(symbol: str, exchange: Optional[str] = None, isin: Optional[str] = None) -> str:
        """
        Convert broker symbol to Yahoo Finance compatible format.
        
        Strategy:
        1. If symbol already has .NS or .BO suffix, return as-is
        2. Try with .NS suffix (most common for Indian stocks)
        3. Try with .BO suffix
        4. If neither works and ISIN provided, try ISIN lookup
        5. Return original symbol as fallback
        
        Args:
            symbol: Trading symbol from broker (e.g., 'RELIANCE', 'TCS')
            exchange: Exchange name if available (e.g., 'NSE', 'BSE')
            isin: ISIN code if available (e.g., 'INE002A01018')
            
        Returns:
            Yahoo Finance compatible symbol (e.g., 'RELIANCE.NS')
        """
        if not symbol:
            return symbol
        
        symbol = symbol.strip().upper()
        
        # Already has exchange suffix
        if '.' in symbol and any(suffix in symbol for suffix in ['.NS', '.BO', '.N', '.O']):
            logger.debug(f"Symbol {symbol} already has exchange suffix")
            return symbol
        
        # Use exchange info if provided
        if exchange:
            exchange = exchange.upper()
            suffix = SymbolMapper.EXCHANGE_SUFFIX_MAP.get(exchange)
            if suffix:
                test_symbol = f"{symbol}{suffix}"
                if SymbolMapper._validate_yahoo_symbol(test_symbol):
                    logger.info(f"Mapped {symbol} -> {test_symbol} using exchange {exchange}")
                    return test_symbol
        
        # Try NSE first (most common)
        test_symbol_ns = f"{symbol}.NS"
        if SymbolMapper._validate_yahoo_symbol(test_symbol_ns):
            logger.info(f"Mapped {symbol} -> {test_symbol_ns}")
            return test_symbol_ns
        
        # Try BSE
        test_symbol_bo = f"{symbol}.BO"
        if SymbolMapper._validate_yahoo_symbol(test_symbol_bo):
            logger.info(f"Mapped {symbol} -> {test_symbol_bo}")
            return test_symbol_bo
        
        # If ISIN provided, could implement ISIN lookup here
        # This would require a database of ISIN -> Symbol mappings
        
        # Fallback: return original symbol (might work for US stocks)
        logger.warning(f"Could not map symbol {symbol} to Yahoo Finance format, using as-is")
        return symbol
    
    @staticmethod
    def _validate_yahoo_symbol(symbol: str) -> bool:
        """
        Check if symbol is valid on Yahoo Finance.
        
        Args:
            symbol: Symbol to validate
            
        Returns:
            True if symbol exists on Yahoo Finance
        """
        try:
            # Quick validation using market data service
            return market_data_service.validate_symbol(symbol)
        except Exception as e:
            logger.debug(f"Symbol validation failed for {symbol}: {e}")
            return False
    
    @staticmethod
    def get_company_name(symbol: str) -> Optional[str]:
        """
        Fetch company name for a symbol from Yahoo Finance.
        
        Args:
            symbol: Yahoo Finance compatible symbol
            
        Returns:
            Company name or None if not found
        """
        try:
            stock_info = market_data_service.get_stock_info(symbol)
            if stock_info:
                return stock_info.get('name')
        except Exception as e:
            logger.error(f"Error fetching name for {symbol}: {e}")
        
        return None


# Singleton instance
symbol_mapper = SymbolMapper()
