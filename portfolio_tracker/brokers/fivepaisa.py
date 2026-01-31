"""5Paisa broker integration."""

import os
from decimal import Decimal
from typing import List, Optional

from portfolio_tracker.schemas import BrokerHolding


class FivePaisaBroker:
    """5Paisa broker integration using py5paisa SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        user_key: Optional[str] = None,
        encryption_key: Optional[str] = None,
        app_name: Optional[str] = None,
        app_source: Optional[str] = None,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize 5Paisa broker.

        The 5Paisa API requires either:
        1. Full credentials (app_name, app_source, user_id, password, user_key, encryption_key)
        2. OAuth flow with request token

        For simplicity, we store api_key/api_secret and use OAuth flow.

        Args:
            api_key: 5Paisa User Key (also called VendorKey)
            api_secret: 5Paisa Encryption Key
            user_key: Same as api_key (alias for compatibility)
            encryption_key: Same as api_secret (alias for compatibility)
            app_name: 5Paisa App Name (optional, for credential-based auth)
            app_source: 5Paisa App Source (optional, for credential-based auth)
            user_id: 5Paisa User ID (optional, for credential-based auth)
            password: 5Paisa Password (optional, for credential-based auth)
        """
        # Support both naming conventions
        self.user_key = api_key or user_key or os.getenv("5PAISA_API_KEY", "")
        self.encryption_key = api_secret or encryption_key or os.getenv("5PAISA_API_SECRET", "")
        
        # Optional full credential fields
        self.app_name = app_name or os.getenv("5PAISA_APP_NAME", "")
        self.app_source = app_source or os.getenv("5PAISA_APP_SOURCE", "")
        self.user_id = user_id or os.getenv("5PAISA_USER_ID", "")
        self.password = password or os.getenv("5PAISA_PASSWORD", "")
        
        if not self.user_key:
            raise ValueError("5Paisa User Key (api_key) not configured")
        
        self.access_token: Optional[str] = None
        self.client_code: Optional[str] = None
        self._client = None

    def _get_client(self):
        """Get or create the 5Paisa client."""
        if self._client is None:
            try:
                from py5paisa import FivePaisaClient
                
                cred = {
                    "APP_NAME": self.app_name,
                    "APP_SOURCE": self.app_source,
                    "USER_ID": self.user_id,
                    "PASSWORD": self.password,
                    "USER_KEY": self.user_key,
                    "ENCRYPTION_KEY": self.encryption_key,
                }
                self._client = FivePaisaClient(cred=cred)
            except ImportError:
                raise ValueError("py5paisa package not installed. Run: pip install py5paisa")
        return self._client

    def get_login_url(self, redirect_url: Optional[str] = None) -> str:
        """
        Get the login URL for 5Paisa OAuth authorization.

        Args:
            redirect_url: URL to redirect after login

        Returns:
            Login URL for user to authorize the app
        """
        if not redirect_url:
            redirect_url = os.getenv("FIVEPAISA_REDIRECT_URL", "")
            if not redirect_url:
                frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
                redirect_url = f"{frontend_url}/app/brokers"
        
        # 5Paisa OAuth login URL format
        login_url = f"https://dev-openapi.5paisa.com/WebVendorLogin/VLogin/Index?VendorKey={self.user_key}&ResponseURL={redirect_url}"
        return login_url

    def set_access_token(self, request_token: str) -> str:
        """
        Exchange request token for access token using OAuth.

        Args:
            request_token: Authorization request token from callback

        Returns:
            Access token for subsequent API calls
        """
        try:
            client = self._get_client()
            client.get_oauth_session(request_token)
            self.access_token = client.get_access_token()
            return self.access_token or ""
        except Exception as e:
            raise ValueError(f"Failed to generate session: {str(e)}")

    def set_token(self, access_token: str, client_code: Optional[str] = None) -> None:
        """
        Set access token for subsequent API calls.

        Args:
            access_token: 5Paisa access token
            client_code: 5Paisa client code (optional)
        """
        self.access_token = access_token
        self.client_code = client_code
        client = self._get_client()
        if client_code:
            client.set_access_token(access_token, client_code)
        else:
            # Try to set without client code
            client.set_access_token(access_token, "")

    def get_holdings(self) -> List[BrokerHolding]:
        """
        Fetch holdings from 5Paisa account.

        Returns:
            List of BrokerHolding objects
        """
        if not self.access_token:
            raise ValueError("Access token not set. Please complete OAuth flow first.")
        
        try:
            client = self._get_client()
            holdings_data = client.holdings()
            
            if not holdings_data:
                return []
            
            holdings = []
            # Handle different response formats
            if isinstance(holdings_data, dict):
                # Response might be wrapped in a data key
                holdings_list = holdings_data.get("Data", holdings_data.get("data", []))
                if isinstance(holdings_list, dict):
                    holdings_list = holdings_list.get("Data", [])
            else:
                holdings_list = holdings_data if isinstance(holdings_data, list) else []
            
            for holding in holdings_list:
                if not isinstance(holding, dict):
                    continue
                    
                # Map 5Paisa fields to our schema
                # 5Paisa uses different field names
                symbol = holding.get("ScripName", holding.get("Symbol", holding.get("TradingSymbol", "")))
                quantity = holding.get("Quantity", holding.get("Qty", holding.get("BuyQty", 0)))
                avg_price = holding.get("BuyAvgRate", holding.get("AvgRate", holding.get("BuyValue", 0)))
                current_price = holding.get("LTP", holding.get("CurrentPrice", holding.get("LastTradedPrice", 0)))
                isin = holding.get("ISIN", holding.get("Isin", None))
                
                if not symbol or quantity == 0:
                    continue
                
                broker_holding = BrokerHolding(
                    symbol=str(symbol),
                    isin=isin,
                    quantity=Decimal(str(quantity)),
                    average_price=Decimal(str(avg_price)) if avg_price else Decimal("0"),
                    current_price=Decimal(str(current_price)) if current_price else Decimal("0"),
                    last_price=Decimal(str(current_price)) if current_price else Decimal("0"),
                )
                holdings.append(broker_holding)
            
            return holdings
        except Exception as e:
            raise ValueError(f"Failed to fetch holdings: {str(e)}")

    def get_profile(self) -> dict:
        """
        Fetch user profile from 5Paisa.

        Returns:
            User profile information
        """
        try:
            # If we have a client code from set_token, return it
            if self.client_code:
                return {"user_id": self.client_code, "name": f"5Paisa User ({self.client_code})"}
            
            # Try to get profile from client
            client = self._get_client()
            
            # 5Paisa doesn't have a direct profile endpoint in the SDK
            # Return basic info based on credentials
            return {
                "user_id": self.user_id or self.user_key[:8] + "...",
                "name": "5Paisa User"
            }
        except Exception as e:
            raise ValueError(f"Failed to fetch profile: {str(e)}")


# Keep the old class name for backwards compatibility
FivepaIsaBroker = FivePaisaBroker
