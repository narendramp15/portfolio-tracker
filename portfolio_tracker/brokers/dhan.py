"""Dhan broker integration using Dhan REST API."""

import os
from decimal import Decimal
from typing import List, Optional

import requests

from portfolio_tracker.schemas import BrokerHolding


class DhanBroker:
    """Dhan broker integration.

    Dhan uses a simple token-based auth model — no OAuth redirect needed.
    Users generate a Client ID + Access Token directly from the Dhan developer
    portal (https://dhanhq.co/developer) and paste them here.
    """

    BASE_URL = "https://api.dhan.co"

    def __init__(
        self,
        client_id: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("DHAN_CLIENT_ID", "")
        self._access_token = access_token or os.getenv("DHAN_ACCESS_TOKEN", "")

        if not self.client_id:
            raise ValueError("DHAN_CLIENT_ID not configured")

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def set_token(self, access_token: str) -> None:
        self._access_token = access_token

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {
            "access-token": self._access_token or "",
            "client-id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_profile(self) -> dict:
        """Return minimal profile dict — Dhan client_id is the user identifier."""
        return {"user_id": self.client_id, "client_id": self.client_id}

    def get_holdings(self) -> List[BrokerHolding]:
        """Fetch holdings from Dhan account via GET /v2/holdings.

        Dhan holdings response is a JSON array where each item contains:
            tradingSymbol, exchange, isin, totalQty, avgCostPrice,
            lastTradedPrice, ...
        """
        try:
            resp = requests.get(
                f"{self.BASE_URL}/v2/holdings",
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            holdings: List[BrokerHolding] = []
            for item in data:
                try:
                    qty = Decimal(str(item.get("totalQty") or 0))
                    avg_price = Decimal(str(item.get("avgCostPrice") or 0))
                    ltp = Decimal(
                        str(item.get("lastTradedPrice") or item.get("ltp") or 0)
                    )
                    if ltp == 0:
                        ltp = avg_price
                    if qty <= 0:
                        continue
                    holdings.append(
                        BrokerHolding(
                            symbol=item.get("tradingSymbol", ""),
                            isin=item.get("isin"),
                            quantity=qty,
                            average_price=avg_price,
                            current_price=ltp,
                            last_price=ltp,
                        )
                    )
                except Exception:
                    continue

            return holdings
        except requests.HTTPError as e:
            raise ValueError(f"Dhan API error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise ValueError(f"Failed to fetch Dhan holdings: {str(e)}")
