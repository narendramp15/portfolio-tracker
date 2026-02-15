"""FastAPI application entry point."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from portfolio_tracker.config import settings
from portfolio_tracker.database import create_tables
from portfolio_tracker.routers import (analysis, auth, broker,
                                       broker_token_refresh, dashboard, market,
                                       portfolio, tax_reports, trading_journal,
                                       transactions)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create tables on startup
create_tables()

# Log CORS configuration on startup (helps debug production issues)
logger.info(f"âœ“ CORS Origins configured: {settings.CORS_ORIGINS}")
logger.info(f"âœ“ Frontend URL: {settings.FRONTEND_URL}")
logger.info(f"âœ“ Google OAuth: {'Configured' if settings.GOOGLE_CLIENT_ID else 'Not configured'}")


# Raw ASGI middleware to handle OPTIONS BEFORE anything else
# This runs at the lowest level, before SessionMiddleware can reject the request
class CORSPreflightMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "OPTIONS":
            # Get origin from headers
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode("utf-8")
            
            logger.debug(f"[ASGI] OPTIONS preflight: {scope['path']} - Origin: {origin}")
            
            # Check if origin is allowed (use same logic as config)
            allowed_origin = ""
            if origin in settings.CORS_ORIGINS:
                allowed_origin = origin
            elif "*" in settings.CORS_ORIGINS and settings.CORS_ORIGINS == ["*"]:
                # Only allow "*" if it's the ONLY origin (already validated in config)
                allowed_origin = "*"
            
            # Send CORS preflight response directly
            response_headers = [
                (b"access-control-allow-origin", allowed_origin.encode() if allowed_origin else b""),
                (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS, PATCH"),
                (b"access-control-allow-headers", b"authorization, content-type, accept, origin, x-requested-with"),
                (b"access-control-allow-credentials", b"true"),
                (b"access-control-max-age", b"3600"),
                (b"content-length", b"0"),
            ]
            
            await send({
                "type": "http.response.start",
                "status": 200 if allowed_origin else 403,
                "headers": response_headers,
            })
            await send({
                "type": "http.response.body",
                "body": b"",
            })
            return
        
        await self.app(scope, receive, send)


# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get('origin', 'None')
        logger.info(f"Incoming: {request.method} {request.url.path} - Origin: {origin}")
        
        response = await call_next(request)
        
        logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code}")
        return response


# Initialize FastAPI app
_app = FastAPI(
    title="Portfolio Tracker",
    description="A modern Python portfolio tracking application",
    version="1.0.0",
)

# MIDDLEWARE ORDER MATTERS!
# Middleware added first runs LAST in the request chain

# Add Session middleware for OAuth (added first, runs last)
_app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Add request logging middleware (added second, runs middle)
_app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware (runs before logging and session)
_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Wrap with raw ASGI CORS preflight handler (runs FIRST, before any Starlette middleware)
# This is the outermost layer that will catch OPTIONS before anything else can reject it
app = CORSPreflightMiddleware(_app)

# Expose the FastAPI app for testing (tests need dependency_overrides)
fastapi_app = _app

# Mount static files on the inner app
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    _app.mount("/static", StaticFiles(directory=static_path), name="static")

# Setup Jinja2 templates
templates_path = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_path)

# SPA (React) build output (optional)
BASE_DIR = Path(__file__).resolve().parent.parent
SPA_DIST_DIR = BASE_DIR / "frontend" / "dist"
SPA_INDEX = SPA_DIST_DIR / "index.html"
SPA_ASSETS_DIR = SPA_DIST_DIR / "assets"


def spa_available() -> bool:
    return SPA_INDEX.exists()


def serve_spa_index() -> FileResponse:
    return FileResponse(SPA_INDEX)


if spa_available() and SPA_ASSETS_DIR.exists():
    _app.mount("/assets", StaticFiles(directory=str(SPA_ASSETS_DIR)), name="spa-assets")


# Include routers on the inner FastAPI app
_app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
_app.include_router(portfolio.router, prefix="/api/portfolios", tags=["portfolios"])
_app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
_app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
_app.include_router(market.router, prefix="/api/market", tags=["market"])
_app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
_app.include_router(broker.router, prefix="/api/broker", tags=["broker"])
_app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
_app.include_router(tax_reports.router, prefix="/api", tags=["tax-reports"])
_app.include_router(broker_token_refresh.router, prefix="/api/broker", tags=["broker-token"])


# Public pages (no authentication required)
@_app.get("/login")
async def login_page(request: Request):
    """Login page."""
    if spa_available():
        return serve_spa_index()
    return RedirectResponse(url="/docs")


@_app.get("/register")
async def register_page(request: Request):
    """Register page."""
    if spa_available():
        return serve_spa_index()
    return RedirectResponse(url="/docs")


# Protected pages (authentication required via client-side check)
@_app.get("/")
async def root(request: Request):
    """Root endpoint - serves homepage."""
    if spa_available():
        return RedirectResponse(url="/app/dashboard")
    # If SPA not available, redirect to API docs instead of trying to serve non-existent template
    return RedirectResponse(url="/docs")


@_app.get("/portfolios")
async def portfolios_page(request: Request):
    """Portfolios page."""
    if spa_available():
        return RedirectResponse(url="/app/holdings")
    return RedirectResponse(url="/docs")


@_app.get("/dashboard")
async def dashboard_page(request: Request):
    """Dashboard page."""
    if spa_available():
        return RedirectResponse(url="/app/dashboard")
    return RedirectResponse(url="/docs")


@_app.get("/transactions")
async def transactions_page(request: Request):
    """Transactions page."""
    if spa_available():
        return RedirectResponse(url="/app/transactions")
    return RedirectResponse(url="/docs")


@_app.get("/broker-settings")
async def broker_settings_page(request: Request):
    """Broker settings page."""
    if spa_available():
        return RedirectResponse(url="/app/brokers")
    return RedirectResponse(url="/docs")


@_app.get("/app")
@_app.get("/app/{path:path}")
async def spa_app(path: str = ""):
    """Single-page app entry for the modern UI."""
    if spa_available():
        return serve_spa_index()
    return RedirectResponse(url="/dashboard")


@_app.get("/favicon.svg")
async def favicon_svg():
    """Serve SPA favicon when available."""
    path = SPA_DIST_DIR / "favicon.svg"
    if path.exists():
        return FileResponse(path)
    return RedirectResponse(url="/static/favicon.ico")


@_app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@_app.get("/debug/config")
async def debug_config():
    """Debug endpoint to check configuration (remove in production if needed)."""
    return {
        "cors_origins": settings.CORS_ORIGINS,
        "frontend_url": settings.FRONTEND_URL,
        "google_oauth_configured": bool(settings.GOOGLE_CLIENT_ID),
        "google_redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }


_app.include_router(trading_journal.router, prefix="/api/journal", tags=["journal"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
