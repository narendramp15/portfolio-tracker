"""Zerodha KiteConnect broker integration."""

import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from kiteconnect import KiteConnect

from portfolio_tracker.schemas import BrokerHolding

logger = logging.getLogger(__name__)


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
                quantity = Decimal(str(holding.get("quantity", 0) or 0))
                # Kite returns fully-sold / T1 rows with quantity 0; BrokerHolding
                # enforces quantity > 0, so skip them instead of aborting the sync.
                if quantity <= 0:
                    continue

                avg_price = Decimal(str(holding.get("average_price", 0) or 0))
                last_price = Decimal(str(holding.get("last_price", 0) or 0))
                # BrokerHolding requires prices > 0; fall back to the other price
                # field when one is missing rather than raising on the whole batch.
                avg_price = avg_price if avg_price > 0 else last_price
                last_price = last_price if last_price > 0 else avg_price
                if avg_price <= 0 or last_price <= 0:
                    logger.warning("Skipping Zerodha holding %s: no usable price", holding.get("tradingsymbol"))
                    continue

                broker_holding = BrokerHolding(
                    symbol=holding.get("tradingsymbol", ""),
                    isin=holding.get("isin"),
                    quantity=quantity,
                    average_price=avg_price,
                    current_price=last_price,
                    last_price=last_price,
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

    def refresh_access_token(self, api_secret: str) -> tuple[str, str]:
        """
        Refresh the access token using the existing access token.
        
        Note: Zerodha doesn't have a traditional refresh token flow.
        Access tokens remain valid until explicitly revoked by the user.
        This method attempts to validate the current token and returns new token if valid.
        
        Args:
            api_secret: The API secret used to generate the original token
            
        Returns:
            Tuple of (access_token, None) - Zerodha doesn't return refresh tokens
            
        Raises:
            ValueError: If token cannot be refreshed (user needs to re-authenticate)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Try to validate the current token by making a profile call
            profile = self.kite.profile()
            logger.info(f"Zerodha token validated successfully for user: {profile.get('user_name', 'Unknown')}")
            
            # Token is valid, return current access token
            current_token = self.kite.access_token
            return current_token, None
            
        except Exception as e:
            error_msg = str(e).lower()
            if '401' in error_msg or 'unauthorized' in error_msg or 'token' in error_msg:
                logger.warning("Zerodha access token expired or invalid. User needs to re-authenticate.")
                raise ValueError(
                    "Zerodha access token has expired. Please reconnect your Zerodha account "
                    "from the Brokers page to continue syncing."
                )
            else:
                logger.error(f"Failed to validate Zerodha token: {e}")
                raise ValueError(f"Failed to refresh Zerodha token: {e}")

    def is_token_valid(self) -> bool:
        """
        Check if the current access token is still valid.
        
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Try to make a simple API call to validate the token
            self.kite.profile()
            return True
        except Exception:
            return False
