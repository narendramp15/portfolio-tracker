# Portfolio Tracker AI Coding Instructions

## Project Overview

**Portfolio Tracker** is a full-stack investment portfolio management application with:
- **Backend**: FastAPI + SQLAlchemy (Python 3.13+) with multi-broker integration (Zerodha, Angel, 5Paisa)
- **Frontend**: Modern React SPA with TypeScript, React Router, Zustand, TanStack Query, Tailwind CSS
- **Database**: SQLAlchemy ORM with Pydantic validation
- **Development Tool**: `uv` for Python package management (cross-platform, faster than pip)

## Architecture Patterns

### Backend Architecture
1. **Routers Pattern**: API endpoints organized in `portfolio_tracker/routers/` (auth, broker, portfolio, transactions, dashboard)
2. **Models → Schemas Pipeline**: SQLAlchemy ORM models in `models.py` are validated against Pydantic schemas in `schemas.py` for request/response consistency
3. **Dependency Injection**: FastAPI's `Depends()` for auth (`get_current_user`), database sessions (`get_db`), and CRUD operations
4. **Encryption for Secrets**: `EncryptionManager` encrypts broker API keys/secrets before DB storage (see `portfolio_tracker/encryption.py`)
5. **CORS**: Wildcard allow-origins for dev; restrict in production

### Frontend Architecture
1. **React Router v7**: App-based routing in `src/router/router.tsx` with `RequireAuth` wrapper for protected routes
2. **Zustand State**: Minimal global state (`selectedPortfolioId`) in `src/store/appStore.ts` with localStorage persistence
3. **TanStack Query (React Query)**: Primary data fetching (not visible in provided files but inferred from package.json)
4. **Axios Interceptor**: Bearer token auto-injection from `localStorage.access_token` in `src/lib/api.ts`
5. **Tailwind + Lucide Icons**: CSS utility-first with lucide-react for consistent iconography

### Broker Integration Pattern
- **Pluggable Brokers**: `portfolio_tracker/brokers/` contains broker-specific classes (ZerodhaBroker, AngelBroker, FivepaisaBroker)
- **OAuth2 Flow**: Zerodha uses KiteConnect OAuth → broker redirects to `ZERODHA_REDIRECT_URL` after user authorization
- **Unified Interface**: All brokers inherit interface with methods: `get_holdings()`, `get_login_url()`, `set_access_token()`
- **Credential Storage**: API keys encrypted and stored in `broker_config` table per user

## Development Workflows

### Setup & Running
```bash
# Backend setup (Python 3.13+ required)
uv sync --all-extras          # Install deps with dev tools
uv run uvicorn portfolio_tracker.main:app --reload

# Frontend setup
cd frontend
npm install
npm run dev                   # Vite dev server (proxies /api to localhost:8000)
```

### Testing
```bash
uv run pytest --cov=portfolio_tracker  # Runs tests, generates htmlcov/
```

### Code Quality
```bash
uv run black .                # Format Python files
uv run ruff check .           # Lint
uv run mypy portfolio_tracker # Type checking
```

### Building for Production
```bash
cd frontend && npm run build  # Creates frontend/dist/
# FastAPI serves SPA from frontend/dist/index.html
```

## Key Code Patterns

### Database & CRUD
- **Session Management**: Use `db: Session = Depends(get_db)` in router functions
- **Relationships**: SQLAlchemy back_populates for bidirectional relationships (e.g., User ↔ Portfolios)
- **Decimal Precision**: Financial values use `Decimal` type, not float (see `_to_decimal()` in models.py)
- **Timestamp Defaults**: All models have `created_at`, `updated_at` with timezone-aware datetime

### Authentication
- **JWT Tokens**: `create_access_token()` generates bearer tokens (see `portfolio_tracker/auth.py`)
- **Protected Routes**: Depend on `get_current_user` which decodes JWT and fetches user from DB
- **Hash Storage**: Passwords hashed with argon2 (passlib), never stored plaintext

### API Design
- **Base URL**: `/api/{resource}` prefix for all REST endpoints
- **Request/Response**: Pydantic schemas ensure validation; use `response_model` in route decorator
- **Error Handling**: Raise `HTTPException` with appropriate status codes (400, 401, 404, etc.)
- **Duplicate Routes**: Note auth/broker routers registered twice (backward compatibility) at `/api/auth` and legacy prefix

### Frontend Components
- **Card Component**: Base UI wrapper in `src/ui/components/Card.tsx` (used by BrokerSetupForm)
- **Form Pattern**: React Hook Form + Zod validation (inferred from dependencies)
- **API Calls**: Use `api` axios client from `src/lib/api.ts` (auto-injects Bearer token)
- **Gradient Colors**: Broker cards use Tailwind gradient classes by type (`from-purple-600 to-purple-700`)

## Critical Files & Concepts

| File | Purpose |
|------|---------|
| `portfolio_tracker/main.py` | FastAPI app init, router mounting, SPA serving |
| `portfolio_tracker/models.py` | SQLAlchemy ORM definitions (User, Portfolio, Asset, etc.) |
| `portfolio_tracker/schemas.py` | Pydantic validation schemas (UserRegister, AssetBase, etc.) |
| `portfolio_tracker/routers/*.py` | API endpoint implementations by domain |
| `portfolio_tracker/brokers/*.py` | Broker-specific API integrations |
| `portfolio_tracker/encryption.py` | EncryptionManager for secure credential storage |
| `frontend/src/App.tsx` | React router setup + provider wrappers |
| `frontend/src/lib/api.ts` | Axios instance with JWT interceptor |
| `frontend/src/store/appStore.ts` | Zustand store for portfolio selection state |

## Common Tasks

### Adding a New Broker
1. Create `portfolio_tracker/brokers/{broker_name}.py` with class inheriting broker interface
2. Implement: `__init__()`, `get_login_url()`, `get_holdings()`, `set_token()`
3. Add router endpoint in `portfolio_tracker/routers/broker.py` (mirror Zerodha pattern)
4. Update frontend `BrokerSetupForm.tsx` to include new broker type and colors
5. Store encrypted credentials using `EncryptionManager.encrypt()`

### Adding an API Endpoint
1. Define request/response Pydantic schema in `portfolio_tracker/schemas.py`
2. Add route in appropriate `portfolio_tracker/routers/{domain}.py`
3. Use `Depends(get_current_user)` and `Depends(get_db)` for auth/DB access
4. Call CRUD functions from `portfolio_tracker/crud.py` for DB operations
5. Return Pydantic-validated response

### Modifying Frontend State
1. Update Zustand store in `frontend/src/store/appStore.ts` if cross-component state needed
2. Use `useAppStore()` hook in components to read/write state
3. For API-driven data: use TanStack Query (inferred from dependencies)
4. Store sensitive data (JWT) in localStorage via interceptor

## Database & Environment

- **SQLite by default** (check `portfolio_tracker/database.py` for connection string)
- **Environment Variables**: Uses python-dotenv; common vars: `ZERODHA_API_KEY`, `ZERODHA_API_SECRET`, `ZERODHA_REDIRECT_URL`
- **Migrations**: Not using Alembic (models.py auto-creates tables on startup via `create_tables()`)
- **Transaction Model**: Financial transactions linked to Assets with price, quantity, type (buy/sell)

## Important Conventions

- **Type Hints**: Use full type annotations in Python (mypy enabled)
- **Naming**: Snake_case for Python, camelCase for TypeScript/React
- **Component Structure**: Each UI component in `frontend/src/ui/components/` as separate file
- **Error Messages**: User-facing errors in HTTPException detail; logged server-side
- **Decimal Math**: Always use Decimal for financial calculations, never float
- **Token Storage**: JWT stored in localStorage under key `access_token`
- **CORS**: Dev mode allows all origins; update in `main.py` for production

## Performance Notes

- Frontend dev server proxies `/api/*` requests to `localhost:8000` (see vite.config.ts)
- Production: Static SPA assets served by FastAPI from `frontend/dist/`
- TanStack Query handles caching and request deduplication
- SQLAlchemy relationships use lazy-loading; add `.options()` for N+1 prevention if needed
