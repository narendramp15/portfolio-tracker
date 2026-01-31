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

        Credentials are stored per-user in the database (broker_config table).
        All 6 credentials are required for full API access:
        - USER_KEY (VendorKey) - stored as api_key
        - ENCRYPTION_KEY - stored as api_secret
        - APP_NAME, APP_SOURCE, USER_ID, PASSWORD - stored in extra_config JSON

        Args:
            api_key: 5Paisa User Key (also called VendorKey)
            api_secret: 5Paisa Encryption Key
            user_key: Same as api_key (alias)
            encryption_key: Same as api_secret (alias)
            app_name: 5Paisa App Name
            app_source: 5Paisa App Source
            user_id: 5Paisa User ID
            password: 5Paisa Password
        """
        # Support both naming conventions
        self.user_key = api_key or user_key or ""
        self.encryption_key = api_secret or encryption_key or ""
        self.app_name = app_name or ""
        self.app_source = app_source or ""
        self.user_id = user_id or ""
        self.password = password or ""
        
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

                # All 6 credentials for full API access
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

        The request_token from 5Paisa is actually a JWT that contains:
        - unique_name: the client code
        - role: the API key

        Args:
            request_token: Authorization request token (JWT) from callback

        Returns:
            Access token for subsequent API calls
        """
        import base64
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # The request_token is a JWT - extract client code from it
            # JWT format: header.payload.signature
            parts = request_token.split('.')
            if len(parts) >= 2:
                # Decode the payload (add padding if needed)
                payload = parts[1]
                padding = 4 - len(payload) % 4
                if padding != 4:
                    payload += '=' * padding
                decoded = base64.urlsafe_b64decode(payload)
                claims = json.loads(decoded)
                self.client_code = claims.get('unique_name', '')
                logger.info(f"5Paisa: Extracted client_code={self.client_code} from JWT")
            
            # Try to get OAuth session from 5Paisa SDK
            client = self._get_client()
            try:
                client.get_oauth_session(request_token)
                sdk_token = client.get_access_token()
                if sdk_token:
                    self.access_token = sdk_token
                    logger.info(f"5Paisa: Got access token from SDK")
                else:
                    # SDK returned empty - use JWT token directly
                    self.access_token = request_token
                    logger.info(f"5Paisa: SDK returned empty, using JWT as access token")
            except Exception as e:
                # If SDK fails, use the JWT token directly as access token
                logger.warning(f"5Paisa SDK error: {e}, using JWT as access token")
                self.access_token = request_token
            
            return self.access_token
        except Exception as e:
            raise ValueError(f"Failed to generate session: {str(e)}")

    def set_token(self, access_token: str, client_code: Optional[str] = None) -> None:
        """
        Set access token for subsequent API calls.

        Args:
            access_token: 5Paisa access token
            client_code: 5Paisa client code (optional)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        self.access_token = access_token
        self.client_code = client_code
        
        # If client_code not provided, try to extract from JWT
        if not client_code and access_token:
            try:
                import base64
                import json
                parts = access_token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    padding = 4 - len(payload) % 4
                    if padding != 4:
                        payload += '=' * padding
                    decoded = base64.urlsafe_b64decode(payload)
                    claims = json.loads(decoded)
                    self.client_code = claims.get('unique_name', '')
                    logger.info(f"5Paisa: Extracted client_code={self.client_code} from stored token")
            except Exception as e:
                logger.warning(f"5Paisa: Failed to extract client_code from token: {e}")
        
        client = self._get_client()
        if self.client_code:
            logger.info(f"5Paisa: Setting access token with client_code={self.client_code}")
            client.set_access_token(access_token, self.client_code)
        else:
            logger.warning("5Paisa: No client_code available, set_access_token may fail")
            client.set_access_token(access_token, "")

    def get_holdings(self) -> List[BrokerHolding]:
        """
        Fetch holdings from 5Paisa account.

        Returns:
            List of BrokerHolding objects
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.access_token:
            raise ValueError("Access token not set. Please complete OAuth flow first.")
        
        try:
            client = self._get_client()
            logger.info(f"5Paisa: Fetching holdings with client_code={self.client_code}, token_len={len(self.access_token)}")
            holdings_data = client.holdings()
            logger.info(f"5Paisa: Holdings response: {holdings_data}")
            
            # SDK returns None on auth errors (401) - need to re-login
            if holdings_data is None:
                raise ValueError("5Paisa session expired. Please click 'Login' to re-authorize.")
            
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
            error_msg = str(e).lower()
            if "401" in error_msg or "unauthorized" in error_msg:
                raise ValueError("5Paisa session expired. Please re-authorize by clicking 'Login' again.")
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
            
            # 5Paisa doesn't have a direct profile endpoint in the SDK
            # Return basic info based on credentials (masked user key)
            return {
                "user_id": self.user_key[:8] + "..." if self.user_key else "unknown",
                "name": "5Paisa User"
            }
        except Exception as e:
            raise ValueError(f"Failed to fetch profile: {str(e)}")


# Keep the old class name for backwards compatibility
FivepaIsaBroker = FivePaisaBroker
