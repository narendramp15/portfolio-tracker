"""Groww broker integration (OAuth2 / Partner API)."""

import os
from decimal import Decimal
from typing import List, Optional

from portfolio_tracker.schemas import BrokerHolding


class GrowwBroker:
    """Groww Partner API broker integration (OAuth2 flow).

    Setup flow:
        1. POST /broker/groww/setup?api_key=CLIENT_ID&api_secret=CLIENT_SECRET
           → returns login_url for user to authorize
        2. User authorizes → Groww redirects to GROWW_REDIRECT_URL with ?code=...
        3. POST /broker/groww/callback?request_token=<code>
           → stores access_token; is_authorized becomes True
        4. POST /broker/groww/sync-holdings?portfolio_id=N syncs holdings

    Holdings are currently a stub pending Groww Partner API registration.
    The OAuth flow scaffolding is fully wired so holdings will work once
    a registered client_id / client_secret is provided.
    """

    AUTH_URL = "https://groww.in/trade/api/oauth/authorize"
    TOKEN_URL = "https://groww.in/trade/api/oauth/token"
    BASE_URL = "https://groww.in/trade/api/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GROWW_API_KEY", "")
        self.api_secret = api_secret or os.getenv("GROWW_API_SECRET", "")

        if not self.api_key:
            raise ValueError("GROWW_API_KEY not configured")

        self._access_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def get_login_url(self) -> str:
        """Build Groww OAuth authorization URL."""
        redirect_url = os.getenv("GROWW_REDIRECT_URL", "")
        if not redirect_url:
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
            redirect_url = f"{frontend_url}/app/brokers"
        return (
            f"{self.AUTH_URL}"
            f"?client_id={self.api_key}"
            f"&redirect_uri={redirect_url}"
            f"&response_type=code"
            f"&scope=portfolio"
        )

    def set_access_token(self, code_or_token: str) -> str:
        """Accept the authorization code (or direct token) returned by Groww OAuth."""
        # In production, exchange `code` for a real access_token via TOKEN_URL.
        # For now, store the code directly as the token — the holdings stub
        # will be replaced once a registered Groww Partner account is available.
        self._access_token = code_or_token
        return code_or_token

    def set_token(self, access_token: str) -> None:
        self._access_token = access_token

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_profile(self) -> dict:
        prefix = self.api_key[:8] if len(self.api_key) >= 8 else self.api_key
        return {"user_id": f"GROWW_{prefix}"}

    def get_holdings(self) -> List[BrokerHolding]:
        """Fetch holdings from Groww account.

        Full implementation example (uncomment once Partner API access is available):

            import requests
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            }
            resp = requests.get(f"{self.BASE_URL}/portfolio/holdings", headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            # parse data into List[BrokerHolding] ...
        """
        # TODO: Implement once Groww Partner API credentials are available
        return []
