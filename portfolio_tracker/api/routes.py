"""Single registry of every API router and its mount point.

Keeping the full route map in one table makes URL surface changes reviewable
in a single diff and keeps ``main.py`` free of router imports.
"""

from fastapi import FastAPI

from portfolio_tracker.routers import (
    ai_proxy,
    analysis,
    auth,
    billing,
    broker,
    broker_token_refresh,
    dashboard,
    market,
    mutual_funds,
    portfolio,
    stock_screener,
    tax_reports,
    transactions,
)

# (router, prefix, tag) — order preserved from the original main.py
API_ROUTERS = [
    (auth.router, "/api/auth", "auth"),
    (portfolio.router, "/api/portfolios", "portfolios"),
    (transactions.router, "/api/transactions", "transactions"),
    (dashboard.router, "/api/dashboard", "dashboard"),
    (market.router, "/api/market", "market"),
    # Legacy singular alias kept for old frontend builds; do not remove
    # without confirming no clients still call /api/portfolio/*.
    (portfolio.router, "/api/portfolio", "portfolio"),
    (broker.router, "/api/broker", "broker"),
    (analysis.router, "/api/analysis", "analysis"),
    (tax_reports.router, "/api", "tax-reports"),
    (broker_token_refresh.router, "/api/broker", "broker-token"),
    (ai_proxy.router, "/api/ai", "ai"),
    (billing.router, "/api/billing", "billing"),
    (mutual_funds.router, "/api", "mutual-funds"),
    (stock_screener.router, "/api/screener", "stock-screener"),
]


def register_routes(app: FastAPI) -> None:
    """Mount every API router on the given application."""
    for router, prefix, tag in API_ROUTERS:
        app.include_router(router, prefix=prefix, tags=[tag])
