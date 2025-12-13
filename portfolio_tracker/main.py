"""FastAPI application entry point."""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from portfolio_tracker.database import create_tables
from portfolio_tracker.routers import (auth, broker, dashboard, portfolio,
                                       transactions)

# Create tables on startup
create_tables()

# Initialize FastAPI app
app = FastAPI(
    title="Portfolio Tracker",
    description="A modern Python portfolio tracking application",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Setup Jinja2 templates
templates_path = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_path)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(portfolio.router, prefix="/api/portfolios", tags=["portfolios"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(broker.router, prefix="/api/broker", tags=["broker"])


# Public pages (no authentication required)
@app.get("/login")
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register")
async def register_page(request: Request):
    """Register page."""
    return templates.TemplateResponse("register.html", {"request": request})


# Protected pages (authentication required via client-side check)
@app.get("/")
async def root(request: Request):
    """Root endpoint - serves homepage."""
    return templates.TemplateResponse("base.html", {"request": request})


@app.get("/portfolios")
async def portfolios_page(request: Request):
    """Portfolios page."""
    return templates.TemplateResponse("portfolio.html", {"request": request})


@app.get("/dashboard")
async def dashboard_page(request: Request):
    """Dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/transactions")
async def transactions_page(request: Request):
    """Transactions page."""
    return templates.TemplateResponse("transactions.html", {"request": request})


@app.get("/broker-settings")
async def broker_settings_page(request: Request):
    """Broker settings page."""
    return templates.TemplateResponse("broker-settings.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
