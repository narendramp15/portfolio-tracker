# Portfolio Tracker AI Coding Instructions

## Project Overview

**Portfolio Tracker** is a full-stack investment portfolio management application with:
- **Backend**: FastAPI + SQLAlchemy (Python 3.13+) with multi-broker integration (Zerodha, Angel, 5Paisa)
- **Frontend**: Modern React SPA with TypeScript, React Router v7, Zustand, TanStack Query, Tailwind CSS
- **Database**: SQLite with SQLAlchemy ORM + Pydantic validation (no Alembic - auto-creates tables)
- **Development Tool**: `uv` for Python package management (cross-platform, replaces pip/venv)
- **Security**: Argon2 password hashing, JWT tokens, Fernet encryption for broker credentials

## Architecture Patterns

### Backend Architecture
1. **Routers Pattern**: API endpoints organized in `portfolio_tracker/routers/` (auth, broker, portfolio, transactions, dashboard)
   - Routers registered at **dual prefixes** for backward compatibility (`/api/portfolio` and `/api/portfolios` - see `main.py` lines 63-74)
   - **Important**: When adding routes, include both prefix patterns if maintaining compatibility
2. **Models → Schemas Pipeline**: SQLAlchemy ORM models in `models.py` → Pydantic schemas in `schemas.py` for validation
   - Example flow: `AssetModel` (ORM) → `AssetBase` (Pydantic) → `AssetResponse` (API response)
3. **Dependency Injection**: FastAPI's `Depends()` for:
   - Auth: `get_current_user` (from `deps.py`) - extracts JWT from header OR query param `?token=...`
   - Database: `get_db` (from `database.py`) - yields SQLAlchemy session
   - CRUD: Helper functions in `crud.py` for database operations
4. **Encryption for Secrets**: `EncryptionManager` encrypts broker credentials using Fernet (symmetric key from env var `ENCRYPTION_KEY`)
   - Encrypt before DB insert: `EncryptionManager.encrypt(api_key)`
   - Decrypt on retrieval: `EncryptionManager.decrypt(config.api_key)`
5. **CORS**: Wildcard `allow_origins=["*"]` in dev - **must restrict for production**

### Frontend Architecture
1. **React Router v7**: Declarative routing in `src/router/router.tsx`
   - Protected routes wrapped in `<RequireAuth>` which checks localStorage for `access_token`
   - Nested layout with `<AppShell>` component containing sidebar navigation
2. **Zustand State**: Minimal global state in `src/store/appStore.ts`
   - Only stores `selectedPortfolioId` with localStorage persistence
   - **Do not** expand Zustand - prefer TanStack Query for server state
3. **TanStack Query**: Primary data fetching pattern
   - All API calls via `api` axios instance from `src/lib/api.ts`
   - Automatic caching, refetching, and error handling
4. **Axios Interceptor**: Request interceptor auto-adds `Authorization: Bearer <token>` header
   - Token sourced from `localStorage.getItem('access_token')`
   - No need to manually add auth headers in components
5. **Tailwind + Lucide Icons**: Utility-first CSS with lucide-react for icons
   - Custom CSS variables in `index.css` for theme colors (e.g., `--background`, `--surface`)

### Broker Integration Pattern
- **Pluggable Brokers**: `portfolio_tracker/brokers/` contains broker classes (ZerodhaBroker, AngelBroker, FivepaisaBroker)
  - Each implements: `__init__()`, `get_login_url()`, `set_access_token(request_token)`, `set_token(token)`, `get_holdings()`
  - Example: `ZerodhaBroker` wraps KiteConnect API, handles OAuth2 flow
- **OAuth2 Flow**: 
  1. User provides credentials → broker setup endpoint creates `broker_config` record with encrypted credentials
  2. Backend generates login URL (e.g., Zerodha OAuth page)
  3. User authorizes → broker redirects to `ZERODHA_REDIRECT_URL` with `request_token` query param
  4. Callback endpoint exchanges `request_token` for `access_token`, saves encrypted token to DB
- **Credential Storage**: Per-user in `broker_config` table, all secrets encrypted via `EncryptionManager.encrypt()`
- **Query Params Pattern**: Broker setup endpoints use `Query(...)` params, **not request body**
  - Example: `POST /api/broker/zerodha/setup?api_key=xxx&api_secret=yyy`
  - Reason: OAuth callbacks must use query params, so setup endpoints follow same pattern for consistency

## Development Workflows

### Setup & Running
```bash
# Backend (Python 3.13+ required)
uv sync --all-extras           # Install all dependencies including dev tools
uv run uvicorn portfolio_tracker.main:app --reload  # Start backend at :8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev  # Vite dev server at :5173, proxies /api to :8000
```

### Testing & Quality
```bash
uv run pytest --cov=portfolio_tracker  # Run tests with coverage report
uv run black .                         # Format code (auto-formats on save)
uv run ruff check .                    # Linting
uv run mypy portfolio_tracker          # Type checking (strict mode enabled)
```

### Production Build
```bash
cd frontend && npm run build  # Creates dist/; FastAPI serves static from here
# Backend serves SPA from /frontend/dist if spa_available() returns True
```

## Key Code Patterns

### Database & CRUD
- **Session Management**: `db: Session = Depends(get_db)` in router functions - yields session, auto-closes
- **Relationships**: SQLAlchemy `back_populates` for bidirectional refs; `cascade="all, delete-orphan"` for cleanup
  - Example: `PortfolioModel.assets` deletes all assets when portfolio deleted
- **Decimal Precision**: Use `Numeric(20,8)` column type for financial values (never float)
  - Helper: `_to_decimal()` in `models.py` converts str/float/int to Decimal safely
- **Timestamps**: All models have `created_at` (immutable), `updated_at` (auto-updates via `onupdate=`) with timezone-aware datetime
- **CRUD Helpers**: `crud.py` provides reusable functions like `get_portfolio_by_id()`, `create_asset()`, `update_broker_config()`

### Authentication  
- **JWT Tokens**: Generated by `create_access_token()` in `auth.py` (default 30-day expiry); decoded by `get_current_user` in `deps.py`
- **Token Extraction**: `get_access_token()` checks both query param `?token=...` AND `Authorization: Bearer` header
  - Dual extraction supports both browser redirects (query) and API clients (header)
- **Protected Routes**: Depend on `get_current_user` which:
  1. Extracts token → 2. Decodes JWT → 3. Fetches user from DB by email
- **Password Hashing**: Argon2 via passlib (`pwd_context.hash/verify`) - no 72-byte limit, more secure than bcrypt
- **Storage**: JWT in `localStorage.access_token`, auto-injected by axios interceptor

### API Design
- **Base URL**: All routes under `/api/{resource}` (mounted in `main.py`)
- **Query Parameters**: Broker setup prefers Query params - e.g., `POST /api/broker/zerodha/setup?api_key=...&api_secret=...`
- **Validation**: Pydantic schemas; use `response_model` in route decorators
- **Errors**: Raise `HTTPException` with status codes; details shown to frontend
- **Backward Compat**: Routers registered at multiple prefixes for old API consumers

### Frontend Components
- **Card Component**: Base wrapper in `src/ui/components/Card.tsx` - template for other cards
- **BrokerSetupForm**: Modal form pattern accepting `brokerType` (union: 'zerodha'|'angel'|'fivepaisa'), `brokerName`, `onSuccess` callback
  - Uses `api.post()` with query params (not request body): `params: { api_key, api_secret }`
  - For Zerodha, redirects to `login_url` from response after successful setup
- **API Calls**: Always use `api` axios instance from `src/lib/api.ts` (auto-adds Bearer header)
  - Example: `api.get('/portfolios')`, `api.post('/broker/zerodha/setup', undefined, { params })`
- **Broker-Specific Styling**: Tailwind gradient classes in `brokerColors` record
  - zerodha: `from-purple-600 to-purple-700`, angel: `from-pink-600 to-pink-700`, fivepaisa: `from-cyan-600 to-cyan-700`

## Critical Files & Concepts

| File | Purpose |
|------|---------|
| `main.py` | FastAPI init, CORS, router mounting, SPA static serving |
| `models.py` | SQLAlchemy ORM: User, Portfolio, Asset, Transaction, BrokerTemplate, BrokerConfig |
| `schemas.py` | Pydantic: UserRegister, AssetBase, BrokerHolding, BrokerConfig schemas |
| `routers/*.py` | Domain-specific endpoints (auth, broker, portfolio, transactions, dashboard) |
| `brokers/*.py` | Broker integrations (Zerodha KiteConnect, Angel, 5Paisa) |
| `encryption.py` | EncryptionManager for credential encryption/decryption |
| `database.py` | SQLAlchemy Base, connection, `create_tables()` on startup |
| `crud.py` | Helper functions for CRUD operations |
| `deps.py` | FastAPI dependencies: `get_current_user`, `get_db` |
| `frontend/src/App.tsx` | React Router + AppProviders |
| `frontend/src/lib/api.ts` | Axios instance + JWT interceptor |
| `frontend/src/store/appStore.ts` | Zustand store for portfolio selection |

## Common Tasks

### Adding a New Broker
1. Create `portfolio_tracker/brokers/new_broker.py` implementing interface methods
2. Add `@router.post("/new_broker/setup")` endpoint in `broker.py` using Query params
3. Handle OAuth callback: decrypt creds, exchange token, store encrypted access token via `crud.update_broker_config()`
4. Update `BrokerSetupForm.tsx`: add to `BrokerType` union, `brokerColors`, `brokerIcons` records
5. Test: creds → login URL → callback → holdings

### Adding an API Endpoint
1. Define Pydantic schemas in `schemas.py`
2. Add route in `routers/{domain}.py` with `Depends(get_current_user)`, `Depends(get_db)`
3. Use CRUD helpers from `crud.py` for database operations
4. Return validated Pydantic response

### Modifying Frontend State
1. **Global state**: Update Zustand store in `appStore.ts`, use `useAppStore()` hook
2. **API data**: Use TanStack Query with `api` client
3. **Sensitive data**: Store only in localStorage (via interceptor), never in Zustand

## Database & Environment

- **SQLite**: Default database (configured in `database.py`), stores at `./portfolio.db`
- **Table Creation**: No Alembic migrations; models auto-create tables on app startup via `create_tables()` in `main.py`
- **Environment Variables**: Required for brokers:
  - `ZERODHA_API_KEY`, `ZERODHA_API_SECRET`, `ZERODHA_REDIRECT_URL` (same pattern for Angel/5Paisa)
  - `ENCRYPTION_KEY` (Fernet key for credential encryption - generates default if missing with WARNING)
  - `SECRET_KEY` (JWT signing key - defaults to insecure value, must set in production)
  - `DATABASE_URL` (optional, defaults to SQLite)
- **Transaction Model**: Links to Assets with `price`, `quantity`, `type` (buy/sell), stores full trade history

## Important Conventions

- **Type Hints**: Full annotations required (mypy strict mode enabled in `pyproject.toml`)
- **Naming**: snake_case (Python), camelCase (TypeScript/React)
- **Components**: One per file in `frontend/src/ui/components/`, pages in `frontend/src/ui/pages/`
- **Error Handling**: User-facing messages in `HTTPException.detail`; avoid exposing internal errors
- **Financial Values**: Always use `Decimal` type (never float) - use `_to_decimal()` helper from `models.py`
- **Token Storage**: localStorage key is `access_token`, automatically injected by axios interceptor
- **CORS**: Dev allows all origins (`allow_origins=["*"]`); must restrict to specific domains in production
- **Unused Files**: `schema.py` (singular) exists but unused - always import from `schemas.py` (plural)
- **Vite Proxy**: Frontend dev server (`localhost:5173`) proxies `/api/*` to backend (`localhost:8000`) per `vite.config.ts`

## Debugging Tips

- **Backend logs**: `uv run uvicorn portfolio_tracker.main:app --reload --log-level debug`
- **Network requests**: Browser DevTools → Network tab to inspect `/api/*` + JWT headers
- **Database**: SQLite browser to view `portfolio.db`
- **Encryption**: Verify `EncryptionManager.encrypt/decrypt` symmetry in broker callbacks
- **CORS errors**: Check `CORSMiddleware` in `main.py`
