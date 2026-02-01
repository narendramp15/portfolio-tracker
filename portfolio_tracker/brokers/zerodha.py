"""Zerodha KiteConnect broker integration."""

import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from kiteconnect import KiteConnect

from portfolio_tracker.schemas import BrokerHolding


class ZerodhaBroker:
    """Zerodha broker integration using KiteConnect API."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Zerodha broker.

        Args:
            api_key: Zerodha KiteConnect API key
            api_secret: Zerodha KiteConnect API secret
        """
        self.api_key = api_key or os.getenv("ZERODHA_API_KEY", "")
        self.api_secret = api_secret or os.getenv("ZERODHA_API_SECRET", "")
        
        if not self.api_key:
            raise ValueError("ZERODHA_API_KEY not configured")
        
        self.kite = KiteConnect(api_key=self.api_key)

    def get_login_url(self) -> str:
        """
        Get the login URL for Zerodha authorization.

        Returns:
            Login URL for user to authorize the app
        """
        redirect_url = os.getenv("ZERODHA_REDIRECT_URL", "http://localhost:8000/app/brokers")
        # Use FRONTEND_URL if ZERODHA_REDIRECT_URL is not explicitly set
        frontend_url = os.getenv("FRONTEND_URL")
        if not os.getenv("ZERODHA_REDIRECT_URL") and frontend_url:
            redirect_url = f"{frontend_url}/app/brokers"
        if redirect_url:
            self.kite.redirect_url = redirect_url
        return self.kite.login_url()

    def set_access_token(self, request_token: str, api_secret: str) -> str:
        """
        Exchange request token for access token.

        Args:
            request_token: Authorization request token from callback
            api_secret: Zerodha API secret

        Returns:
            Access token for subsequent API calls
        """
        try:
            response = self.kite.generate_session(request_token, api_secret=api_secret)
            access_token = response.get("access_token")
            self.kite.set_access_token(access_token)
            return access_token
        except Exception as e:
            raise ValueError(f"Failed to generate session: {str(e)}")

    def set_token(self, access_token: str) -> None:
        """
        Set access token for subsequent API calls.

        Args:
            access_token: Zerodha access token
        """
        self.kite.set_access_token(access_token)

    def get_holdings(self) -> List[BrokerHolding]:
        """
        Fetch holdings from Zerodha account.

        Returns:
            List of BrokerHolding objects
        """
        try:
            holdings_data = self.kite.holdings()
            holdings = []

            for holding in holdings_data:
                broker_holding = BrokerHolding(
                    symbol=holding.get("tradingsymbol", ""),
                    isin=holding.get("isin"),
                    quantity=Decimal(str(holding.get("quantity", 0))),
                    average_price=Decimal(str(holding.get("average_price", 0))),
                    current_price=Decimal(str(holding.get("last_price", 0))),
                    last_price=Decimal(str(holding.get("last_price", 0))),
                )
                holdings.append(broker_holding)

            return holdings
        except Exception as e:
            # Add more detailed error information
            error_msg = f"Failed to fetch holdings: {str(e)}"
            if hasattr(e, 'code'):
                error_msg += f" (Error code: {e.code})"
            if hasattr(e, 'message'):
                error_msg += f" (Message: {e.message})"
            raise ValueError(error_msg)

    def get_profile(self) -> dict:
        """
        Fetch user profile from Zerodha.

        Returns:
            User profile information
        """
        try:
            profile = self.kite.profile()
            return profile
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to fetch profile: {str(e)}")
            if hasattr(e, 'code'):
                logger.error(f"  Error code: {e.code}")
            if hasattr(e, 'message'):
                logger.error(f"  Error message: {e.message}")
            raise ValueError(f"Failed to fetch profile: {str(e)}")

    def get_trades(self) -> list[dict[str, Any]]:
        """
        Fetch recent trades from Zerodha account.

        Returns:
            List of trade dicts from KiteConnect.
        """
        try:
            trades = self.kite.trades()
            if not isinstance(trades, list):
                return []
            return trades
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            error_details = f"{str(e)}"
            if hasattr(e, 'code'):
                error_details += f" (code: {e.code})"
            if hasattr(e, 'message'):
                error_details += f" (message: {e.message})"
            logger.error(f"Failed to fetch trades: {error_details}")
            raise ValueError(f"Failed to fetch trades: {error_details}")

    def get_historical_trades(self, days_back: int = 90) -> list[dict[str, Any]]:
        """
        Fetch historical trades using the orders API.
        
        KiteConnect.trades() only returns recent trades (last ~2 weeks).
        This method uses orders() to fetch historical orders and extracts filled trades.

        Args:
            days_back: Number of days to look back (default 90 days)

        Returns:
            List of trade dicts from KiteConnect orders.
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Fetch all orders (this includes cancelled/pending orders too)
            orders = self.kite.orders()
            if not isinstance(orders, list):
                logger.warning("Orders API returned non-list response")
                return []
            
            logger.info(f"📊 Retrieved {len(orders)} total orders from Zerodha")
            
            # Filter to only COMPLETE orders that represent executed trades
            # These are the orders that actually went through
            trades = []
            for order in orders:
                # Only include completed orders
                if order.get("status") == "COMPLETE":
                    trades.append(order)
            
            logger.info(f"📊 Filtered to {len(trades)} completed orders (executed trades)")
            return trades
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            error_details = f"{str(e)}"
            if hasattr(e, 'code'):
                error_details += f" (code: {e.code})"
            if hasattr(e, 'message'):
                error_details += f" (message: {e.message})"
            logger.error(f"Failed to fetch historical trades: {error_details}")
            raise ValueError(f"Failed to fetch historical trades: {error_details}")
