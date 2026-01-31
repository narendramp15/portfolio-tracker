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
from portfolio_tracker.routers import (analysis, auth, broker, dashboard,
                                       market, portfolio, transactions)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create tables on startup
create_tables()

# Log CORS configuration on startup (helps debug production issues)
logger.info(f"✓ CORS Origins configured: {settings.CORS_ORIGINS}")
logger.info(f"✓ Frontend URL: {settings.FRONTEND_URL}")
logger.info(f"✓ Google OAuth: {'Configured' if settings.GOOGLE_CLIENT_ID else 'Not configured'}")


# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Incoming: {request.method} {request.url.path} - Origin: {request.headers.get('origin', 'None')}")
        
        # Log CORS preflight specifically
        if request.method == "OPTIONS":
            logger.info(f"CORS Preflight: {request.url.path} from {request.headers.get('origin', 'Unknown')}")
        
        response = await call_next(request)
        
        logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code}")
        return response


# Initialize FastAPI app
app = FastAPI(
    title="Portfolio Tracker",
    description="A modern Python portfolio tracking application",
    version="1.0.0",
)

# Add request logging middleware (runs first)
app.add_middleware(RequestLoggingMiddleware)

# Add Session middleware for OAuth (must be added first, runs last in chain)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Add CORS middleware using centralized config
# This runs before SessionMiddleware in the request chain
# Must handle preflight OPTIONS requests properly
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

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
    app.mount("/assets", StaticFiles(directory=str(SPA_ASSETS_DIR)), name="spa-assets")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(portfolio.router, prefix="/api/portfolios", tags=["portfolios"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(market.router, prefix="/api/market", tags=["market"])


# Include routers (backwards-compatible duplicate prefixes)
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(broker.router, prefix="/api/broker", tags=["broker"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


# Public pages (no authentication required)
@app.get("/login")
async def login_page(request: Request):
    """Login page."""
    if spa_available():
        return serve_spa_index()
    return RedirectResponse(url="/docs")


@app.get("/register")
async def register_page(request: Request):
    """Register page."""
    if spa_available():
        return serve_spa_index()
    return RedirectResponse(url="/docs")


# Protected pages (authentication required via client-side check)
@app.get("/")
async def root(request: Request):
    """Root endpoint - serves homepage."""
    if spa_available():
        return RedirectResponse(url="/app/dashboard")
    # If SPA not available, redirect to API docs instead of trying to serve non-existent template
    return RedirectResponse(url="/docs")


@app.get("/portfolios")
async def portfolios_page(request: Request):
    """Portfolios page."""
    if spa_available():
        return RedirectResponse(url="/app/holdings")
    return RedirectResponse(url="/docs")


@app.get("/dashboard")
async def dashboard_page(request: Request):
    """Dashboard page."""
    if spa_available():
        return RedirectResponse(url="/app/dashboard")
    return RedirectResponse(url="/docs")


@app.get("/transactions")
async def transactions_page(request: Request):
    """Transactions page."""
    if spa_available():
        return RedirectResponse(url="/app/transactions")
    return RedirectResponse(url="/docs")


@app.get("/broker-settings")
async def broker_settings_page(request: Request):
    """Broker settings page."""
    if spa_available():
        return RedirectResponse(url="/app/brokers")
    return RedirectResponse(url="/docs")


@app.get("/app")
@app.get("/app/{path:path}")
async def spa_app(path: str = ""):
    """Single-page app entry for the modern UI."""
    if spa_available():
        return serve_spa_index()
    return RedirectResponse(url="/dashboard")


@app.get("/favicon.svg")
async def favicon_svg():
    """Serve SPA favicon when available."""
    path = SPA_DIST_DIR / "favicon.svg"
    if path.exists():
        return FileResponse(path)
    return RedirectResponse(url="/static/favicon.ico")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/debug/config")
async def debug_config():
    """Debug endpoint to check configuration (remove in production if needed)."""
    return {
        "cors_origins": settings.CORS_ORIGINS,
        "frontend_url": settings.FRONTEND_URL,
        "google_oauth_configured": bool(settings.GOOGLE_CLIENT_ID),
        "google_redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
