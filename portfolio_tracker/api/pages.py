"""Non-API page routes: SPA entry points, legacy redirects, static assets.

The React SPA is optional at runtime (its ``dist`` folder may not be built);
every route degrades to a redirect to ``/docs`` when it is absent.
"""

import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

router = APIRouter()

# SPA (React) build output (optional)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SPA_DIST_DIR = BASE_DIR / "frontend" / "dist"
SPA_INDEX = SPA_DIST_DIR / "index.html"
SPA_ASSETS_DIR = SPA_DIST_DIR / "assets"
ACME_CHALLENGE_DIR = BASE_DIR / ".well-known" / "acme-challenge"


@router.get("/.well-known/acme-challenge/{token}")
async def acme_challenge(token: str):
    """Serve Let's Encrypt HTTP-01 challenge files directly from disk.

    On this deployment every request is proxied through Passenger to this
    app (no .htaccess static-file fallback — see deploye_to_milesweb.md), so
    without this route domain validation for api.quantleap.in silently fails
    and the CA issues a cert missing that name while other, pre-validated
    names on the account still succeed.
    """
    if "/" in token or ".." in token:
        raise HTTPException(status_code=404)
    path = ACME_CHALLENGE_DIR / token
    if not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="text/plain")


def spa_available() -> bool:
    return SPA_INDEX.exists()


def serve_spa_index() -> FileResponse:
    return FileResponse(SPA_INDEX)


def mount_static(app: FastAPI) -> None:
    """Mount legacy static files and SPA asset bundles when they exist."""
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")

    if spa_available() and SPA_ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(SPA_ASSETS_DIR)), name="spa-assets")


# Public pages (no authentication required)
@router.get("/login")
async def login_page(request: Request):
    """Login page."""
    if spa_available():
        return serve_spa_index()
    return RedirectResponse(url="/docs")


@router.get("/register")
async def register_page(request: Request):
    """Register page."""
    if spa_available():
        return serve_spa_index()
    return RedirectResponse(url="/docs")


# Protected pages (authentication required via client-side check)
@router.get("/")
async def root(request: Request):
    """Root endpoint - serves homepage."""
    if spa_available():
        return RedirectResponse(url="/app/dashboard")
    # If SPA not available, redirect to API docs instead of trying to serve non-existent template
    return RedirectResponse(url="/docs")


@router.get("/portfolios")
async def portfolios_page(request: Request):
    """Portfolios page."""
    if spa_available():
        return RedirectResponse(url="/app/holdings")
    return RedirectResponse(url="/docs")


@router.get("/dashboard")
async def dashboard_page(request: Request):
    """Dashboard page."""
    if spa_available():
        return RedirectResponse(url="/app/dashboard")
    return RedirectResponse(url="/docs")


@router.get("/transactions")
async def transactions_page(request: Request):
    """Transactions page."""
    if spa_available():
        return RedirectResponse(url="/app/transactions")
    return RedirectResponse(url="/docs")


@router.get("/broker-settings")
async def broker_settings_page(request: Request):
    """Broker settings page."""
    if spa_available():
        return RedirectResponse(url="/app/brokers")
    return RedirectResponse(url="/docs")


@router.get("/app")
@router.get("/app/{path:path}")
async def spa_app(path: str = ""):
    """Single-page app entry for the modern UI."""
    if spa_available():
        return serve_spa_index()
    return RedirectResponse(url="/dashboard")


@router.get("/favicon.svg")
async def favicon_svg():
    """Serve SPA favicon when available."""
    path = SPA_DIST_DIR / "favicon.svg"
    if path.exists():
        return FileResponse(path)
    return RedirectResponse(url="/static/favicon.ico")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
