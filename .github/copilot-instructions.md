# Copilot instructions (Portfolio Tracker)

## Quick start
- Backend: `uv sync --all-extras` then `uv run uvicorn portfolio_tracker.main:app --reload` (serves API + optionally the SPA).
- Frontend dev: `cd frontend && npm install && npm run dev` (Vite on `:5173`, proxies `/api` to `:8000`).
- Tests/quality: `uv run pytest`, `uv run black .`, `uv run ruff check .`, `uv run mypy portfolio_tracker`.

## Backend architecture & conventions
- Entry point is `portfolio_tracker/main.py`; it calls `create_tables()` on import (no Alembic; schema is defined by ORM models).
- Routers live in `portfolio_tracker/routers/`. `main.py` mounts some routers twice for compatibility (e.g. `/api/portfolios` and legacy `/api/portfolio`). Prefer updating the router once rather than duplicating endpoints.
- Auth is dependency-based: use `user: UserModel = Depends(get_current_user)` and `db: Session = Depends(get_db)`.
- Token extraction supports both `Authorization: Bearer ...` and `?token=...` query param (`portfolio_tracker/deps.py`). For OAuth-style callback endpoints, accept `token: Optional[str] = Query(default=None)` so redirects can authenticate via query string.

## Data & storage
- DB config is in `portfolio_tracker/database.py`: prefers `PGUSER/PGPASSWORD/PGHOST/PGDATABASE` (Neon/Supabase style), else `DATABASE_URL`, else SQLite `sqlite:///./portfolio.db`.
- Money/quantities use `Decimal` + `Numeric(20, 8)` columns; convert via `_to_decimal()` in `portfolio_tracker/models.py` (avoid floats).

## Broker integrations
- Broker endpoints are in `portfolio_tracker/routers/broker.py`; setup endpoints take credentials as query params (e.g. `/zerodha/setup?api_key=...&api_secret=...`) to match OAuth callback mechanics.
- Secrets/tokens are encrypted at rest via `EncryptionManager` (`portfolio_tracker/encryption.py`). Set `ENCRYPTION_KEY` in `.env` for persistence; otherwise a new key is generated at runtime.

## Required environment variables
See `.env.example` for the full template. The critical ones for production:
- `SECRET_KEY` – JWT signing key (`openssl rand -hex 32`).
- `ENCRYPTION_KEY` – Fernet key for broker credential encryption. Must persist across deploys.
- `CORS_ORIGINS` – Explicit comma-separated origins; wildcard `*` is blocked with credentials.
- `FRONTEND_URL` – Used for OAuth redirects and password-reset email links.
- Database: either `DATABASE_URL` or individual `PGUSER`/`PGPASSWORD`/`PGHOST`/`PGDATABASE` vars.
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` – For password-reset emails (falls back to console log).
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` – When billing is enabled.
- `ANTHROPIC_API_KEY` – When AI proxy is enabled.

## Rate limiting & email
- Auth endpoints (login, register, forgot-password) are rate-limited via `portfolio_tracker/rate_limit.py` (in-memory sliding window).
- Password-reset emails are sent via `portfolio_tracker/services/email_service.py` (SMTP with console fallback).

## Tax reports
- Tax endpoints in `portfolio_tracker/routers/tax_reports.py` include CSV export, PDF export (via `reportlab`), FY auto-detection, and share-with-CA.

## Frontend conventions
- API calls go through `frontend/src/lib/api.ts` (Axios instance). It sets `baseURL` to `VITE_API_URL` or `/api` and injects `Authorization: Bearer ${localStorage.access_token}` automatically.
- Routing/auth: protected routes are gated by `frontend/src/router/RequireAuth.tsx` using the AuthProvider.
- Keep global state minimal: `frontend/src/store/appStore.ts` only persists `selectedPortfolioId`; prefer server state via React Query patterns over adding more Zustand state.

## SPA serving
- If `frontend/dist/index.html` exists, FastAPI serves the SPA for `/app/*` and mounts built assets under `/assets` (see `portfolio_tracker/main.py`).
