# Portfolio Tracker

An Indian-market investment portfolio tracker: FastAPI backend, React SPA, broker sync, and a capital-gains engine that follows CBDT rules rather than approximating them.

Built around an **append-only event ledger**. Every buy, sell, transfer, split and bonus is recorded as an immutable event keyed on ISIN, and holdings, cost basis and tax lots are derived by folding those events. That is what makes per-account FIFO, basis-preserving inter-broker transfers and correct grandfathering possible — see [The ledger](#the-ledger).

- **Live:** [quantleap.in](https://quantleap.in)
- **API docs:** `/docs` (Swagger) and `/redoc` on any running instance
- **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · **Design:** [docs/SOFTWARE_DESIGN_DOCUMENT.md](docs/SOFTWARE_DESIGN_DOCUMENT.md)

---

## Contents

- [Status](#status)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [The ledger](#the-ledger)
- [Capital gains](#capital-gains)
- [Broker integrations](#broker-integrations)
- [API surface](#api-surface)
- [Database and migrations](#database-and-migrations)
- [Testing](#testing)
- [Code quality](#code-quality)
- [Deployment](#deployment)
- [Security notes](#security-notes)
- [Documentation index](#documentation-index)

---

## Status

Honest assessment, so you know what you are looking at:

| Area | State |
| --- | --- |
| Ledger, FIFO lot engine, tax calculator, return analytics | Solid. Heavily unit-tested (~160 tests). |
| Backend structure | Layered and mostly consistent; a few god-object routers remain. |
| Broker sync (Zerodha, Angel, 5Paisa, Dhan, Groww) | Works; error handling is uneven across adapters. |
| React SPA | Functional, 24 routes, no design system yet, no component tests. |
| Data model | No cash ledger, no multi-currency, no first-class account entity. |
| Operations | No automated backups, error tracking or worker/scheduler yet. |

The screens still read cost basis from a mutable running average rather than from the ledger. **Wiring the UI to the ledger is the highest-value remaining change** — the engine is already correct, the presentation layer just doesn't use it yet.

---

## Quick start

**Requirements:** Python 3.13+, Node 20+, [uv](https://docs.astral.sh/uv/).

```bash
# 1. Install uv (once)
curl -LsSf https://astral.sh/uv/install.sh | sh          # macOS/Linux
powershell -c "irm https://astral.sh/uv/install.ps1|iex" # Windows

# 2. Backend
git clone https://github.com/narendramp15/portfolio-tracker.git
cd portfolio-tracker
uv sync --all-extras
cp .env.example .env        # then edit — see Configuration
uv run uvicorn portfolio_tracker.main:app --reload

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to `http://localhost:8000`.

<details>
<summary><b>Running the SPA from FastAPI instead (single port)</b></summary>

```bash
cd frontend && npm run build && cd ..
uv run uvicorn portfolio_tracker.main:app --reload
```

When `frontend/dist/index.html` exists, FastAPI serves the SPA at `/login`, `/register` and `/app/*`. Without it, those routes redirect to `/docs`, so the backend is usable on its own.

</details>

---

## Configuration

All settings come from environment variables, read via `portfolio_tracker/config.py`. Precedence: **process env → `.env` → default.**

`validate_or_die()` runs at startup and **refuses to boot** when `ENVIRONMENT` is anything other than `development` and `SECRET_KEY` or `ENCRYPTION_KEY` is missing or still a placeholder. That is deliberate: both have fallbacks that fail silently and unsafely.

### Required

| Variable | Notes |
| --- | --- |
| `ENVIRONMENT` | `development` (default), `staging` or `production`. Anything but `development` enables strict startup validation and HSTS. |
| `SECRET_KEY` | JWT signing key, 32+ chars. `openssl rand -hex 32`. Rotating it logs everyone out — nothing worse. |
| `ENCRYPTION_KEY` | Fernet key for broker credentials at rest. See the warning below. |
| `DATABASE_URL` | Full connection string. Takes precedence over the `PG*` variables. |
| `CORS_ORIGINS` | Comma-separated origins. `*` is rejected when credentials are allowed. |
| `FRONTEND_URL` | Used for OAuth redirects and password-reset links. |

> [!WARNING]
> **`ENCRYPTION_KEY` must outlive the process and must never be auto-generated.** It decrypts stored broker credentials; a new key makes every one of them permanently unreadable. Generate it once and store it out of band:
> ```bash
> python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```
> Do not use a platform's "generate value" feature for this variable. Rotating it requires a re-encryption migration, which does not exist yet.

`DATABASE_URL` can be replaced by `PGUSER` + `PGPASSWORD` + `PGHOST` + `PGDATABASE` (+ optional `PGPORT`, `PGSSLMODE`), which are assembled into a connection string. An explicit `DATABASE_URL` always wins — hosting panels can leave stale `PG*` values in the process environment after you delete them from the UI.

### Optional

| Variable | Enables |
| --- | --- |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | "Sign in with Google" — see [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Password-reset emails. Falls back to a console log. |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `RAZORPAY_PLAN_ID_PRO` | Billing. The webhook **fails closed** without its secret. |
| `ANTHROPIC_API_KEY`, `MODEL_STARTER`, `MODEL_PRO`, `MODEL_ELITE` | Nifty Options Analyzer. Never exposed to the browser. |
| `ZERODHA_REDIRECT_URL` | Zerodha OAuth callback. Per-user API keys live encrypted in the DB, not here. |
| `DEBUG`, `DB_ECHO`, `LOG_LEVEL` | Diagnostics. |

Templates: [`.env.example`](.env.example) for general use, [`.env.cpanel.example`](.env.cpanel.example) for the cPanel/Passenger host.

---

## Architecture

Layered, with dependencies pointing one way only:

```
routers/      HTTP only — parse, authorise, map errors to status codes
   ↓
services/     business logic — no FastAPI imports, no raw SQL
   ↓
repositories/ persistence — SQLAlchemy queries, one module per aggregate
   ↓
models.py     ORM tables
```

`ledger/` sits beside `services/` as the domain core and depends on nothing above it. `api/` holds HTTP plumbing (middleware, page routes, the router registry) so `main.py` stays a composition root.

```
portfolio_tracker/
├── main.py                  # composition root: logging, middleware, routers
├── config.py                # settings + validate_or_die()
├── deps.py                  # auth dependencies (Authorization header only)
├── auth.py, encryption.py   # JWT/argon2, Fernet at rest
├── rate_limit.py            # in-process sliding window (Redis-ready)
├── models.py, schemas.py    # ORM tables, Pydantic contracts
│
├── api/
│   ├── routes.py            # single table of every router + prefix
│   ├── middleware.py        # CORS preflight, security headers, logging
│   └── pages.py             # SPA entry points, .well-known, /health
│
├── ledger/                  # ── domain core ──
│   ├── events.py            # immutable event records
│   ├── lots.py              # FIFO lot book: fold(), _consume_fifo, transfers
│   ├── instruments.py       # ISIN-keyed instrument identity
│   ├── repository.py        # event persistence
│   ├── sources.py           # projections from transactions/broker imports
│   └── backfill.py          # rebuild the ledger from existing tables
│
├── services/
│   ├── portfolio_analytics.py  # XIRR, TWR, drawdown, volatility
│   ├── tax_calculator.py       # capital gains per CBDT rules
│   ├── grandfathering.py       # 31 Jan 2018 FMV
│   ├── broker_sync.py, broker_accounts.py
│   ├── market_data.py, price_history.py, symbol_mapper.py
│   ├── cas_parser.py           # CAMS/KFintech CAS statements
│   ├── csv_import.py, entitlements.py, email_service.py
│   └── technical_indicators.py, anthropic_client.py
│
├── repositories/            # assets, portfolios, transactions, users, broker_configs
├── brokers/                 # zerodha, angel, fivepaisa, dhan, groww adapters
└── routers/                 # one module per API area

frontend/src/
├── lib/          # axios instance with request + response interceptors
├── providers/    # auth and theme context
├── router/       # route table, all routes code-split via React.lazy
├── hooks/ store/ types/
└── ui/           # pages/, components/, layout/
```

**Stack:** FastAPI · SQLAlchemy 2.0 · Pydantic v2 · React 19 · TanStack Query · Zustand · Tailwind · **recharts** · Vite · pytest · uv.

---

## The ledger

`AssetModel.quantity` and `purchase_price` are mutable running values. They cannot answer "what did I actually pay for the shares I sold in March?" — averaging destroys the information, and reversing an average on delete is not well-defined.

So the ledger keeps every event instead:

```python
from portfolio_tracker.ledger.lots import fold

book = fold(events)          # events → LotBook
book.lots                    # open lots, each with its own cost and acquisition date
book.disposals               # matched sells, each pointing at the lots it consumed
```

Design decisions worth knowing:

- **Keyed on ISIN, not ticker.** Tickers are reused and renamed; `RELIANCE` and `RELIANCE.NS` are the same security. `ledger/instruments.py` resolves identity, with a 24-char key ceiling because MariaDB silently truncates longer values.
- **Append-only, with idempotency.** `UniqueConstraint(user_id, source, source_ref)` means re-importing the same broker statement cannot double-count.
- **Per-account lots.** FIFO is scoped to the demat account, per CBDT Circular 768 — not pooled across brokers.
- **Transfers preserve basis.** An off-market transfer between your own accounts is paired within a 7-day window and carries cost and acquisition date across, instead of registering as a sale plus a purchase.
- **Corporate actions adjust lots.** Splits and bonuses rewrite quantity and per-unit cost without inventing a disposal.

Rebuild from existing tables:

```bash
uv run python backfill_ledger.py --dry-run       # report, write nothing
uv run python backfill_ledger.py --verify        # check an existing ledger agrees
uv run python backfill_ledger.py --user 42       # one user only
uv run python backfill_ledger.py
```

---

## Capital gains

`services/tax_calculator.py` implements Indian equity capital-gains rules rather than a generic FIFO:

- **Per-account FIFO** (Circular 768), not portfolio-pooled.
- **Grandfathering:** for pre-1 Feb 2018 acquisitions, cost is the higher of actual cost and 31 Jan 2018 FMV, capped at the sale price.
- **Section 48 charges:** brokerage and transaction charges are deductible; **STT is not**.
- **LTCG exemption:** the ₹1.25 lakh annual threshold is applied per financial year.
- **Indian financial years** (1 Apr – 31 Mar) throughout, not calendar years.

Reports are available as JSON, CSV and PDF under `/api/tax-reports/*`.

> [!NOTE]
> This is a reporting tool, not tax advice. Reconcile against your broker's own statement before filing.

---

## Broker integrations

| Broker | Auth flow | Holdings | Transactions |
| --- | --- | --- | --- |
| Zerodha (Kite) | OAuth request token | ✅ | ✅ |
| Angel One | API key/secret | ✅ | — |
| 5Paisa | OAuth + app credentials | ✅ | — |
| Dhan | Long-lived access token | ✅ | — |
| Groww | OAuth authorization code | ✅ | — |

Credentials are encrypted with Fernet before storage and **must be sent in the request body** — never as query parameters, which end up in access logs. Mutual funds are imported separately by uploading a CAMS or KFintech CAS PDF to `/api/mutual-funds/import-cas` (password as a form field, since it is usually PAN + date of birth).

Setup guides: [ZERODHA_SETUP.md](ZERODHA_SETUP.md) · [ZERODHA_AUTH_DEBUGGING.md](ZERODHA_AUTH_DEBUGGING.md) · [docs/CONSENT_REQUIREMENTS.md](docs/CONSENT_REQUIREMENTS.md)

---

## API surface

Every route is registered in one table: [`portfolio_tracker/api/routes.py`](portfolio_tracker/api/routes.py). Browse the live spec at `/docs`.

| Prefix | Purpose |
| --- | --- |
| `/api/auth` | register, login, `me`, password reset, Google OAuth |
| `/api/portfolios` | portfolio and asset CRUD, CSV export (`/api/portfolio` is a legacy alias) |
| `/api/transactions` | transaction CRUD, CSV import/export, available quantity |
| `/api/dashboard` | `stats`, `growth`, `returns`, per-portfolio dashboard |
| `/api/market` | quotes, search, price history, backfill |
| `/api/broker` | per-broker setup, OAuth callback, sync, token status |
| `/api/tax-reports` | capital gains, tax summary, CSV/PDF export |
| `/api/mutual-funds` | CAS import, folio CRUD |
| `/api/analysis`, `/api/screener` | technical indicators, stock screeners |
| `/api/billing` | Razorpay orders, verification, webhook, credits |
| `/api/ai` | Nifty Options Analyzer proxy |

Authentication is a **bearer token in the `Authorization` header**. There is no query-parameter token.

```python
import requests

BASE = "http://localhost:8000/api"

token = requests.post(f"{BASE}/auth/login",
                      json={"email": "you@example.com", "password": "..."}
                      ).json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

portfolio = requests.post(f"{BASE}/portfolios/",
                          json={"name": "Long term", "description": "Core equity"},
                          headers=headers).json()

requests.post(f"{BASE}/portfolios/{portfolio['id']}/assets",
              json={"symbol": "RELIANCE", "name": "Reliance Industries",
                    "quantity": 10, "purchase_price": 2500.00,
                    "current_price": 2700.00},
              headers=headers)

stats = requests.get(f"{BASE}/dashboard/stats", headers=headers).json()
print(f"Total value: ₹{stats['total_portfolio_value']}")
```

---

## Database and migrations

SQLite by default for local work; PostgreSQL or MariaDB in production. Tables are created from the ORM metadata on startup.

Schema changes are numbered SQL files under `migrations/`, applied through the app's own connection so the same command works on either backend:

```bash
uv run python run_sql_migration.py 011_add_transaction_charges.sql --dry-run
uv run python run_sql_migration.py 011_add_transaction_charges.sql
```

Migrations are written to be safe to re-run, because MySQL/MariaDB commit DDL implicitly and cannot roll a failed migration back.

Hosted Postgres options: [SUPABASE_SETUP.md](SUPABASE_SETUP.md), Neon, or Render's managed instance ([RENDER_DEPLOY.md](RENDER_DEPLOY.md)). Moving between engines: `migrate_pg_to_mariadb.py`.

> Alembic is not wired up yet. Adding it is a known gap.

---

## Testing

```bash
uv run pytest                                   # full suite (~12 min)
uv run pytest tests/test_ledger.py -v           # one file
uv run pytest --cov=portfolio_tracker           # with coverage
uv run pytest -q --no-cov -k "tax or ledger"    # fast subset
```

269 tests. The domain core carries most of them:

| File | Covers |
| --- | --- |
| `test_ledger.py`, `test_ledger_persistence.py` | fold, FIFO consumption, transfer pairing, corporate actions |
| `test_tax_calculator.py` | grandfathering, Section 48, LTCG exemption, FY boundaries |
| `test_portfolio_analytics.py` | XIRR, TWR, flow adjustment, drawdown |
| `test_security_regressions.py` | credentials never in query params, payment binding, webhook fails closed, startup validation |
| `test_broker_*.py`, `test_csv_*.py`, `test_dashboard_endpoints.py` | integration paths |

The suite recreates the schema per test function, which is why it is slow. Speeding it up with transactional rollback is a known gap.

```bash
cd frontend && npm test    # Vitest — no component tests exist yet
```

---

## Code quality

```bash
uv run ruff check portfolio_tracker tests
uv run black portfolio_tracker tests
uv run mypy portfolio_tracker
cd frontend && npx tsc --noEmit && npm run lint
```

Install the hooks once — they run ruff, gitleaks, and two repo-specific guards that block credentials reappearing as query parameters:

```bash
uv run pre-commit install
```

CI ([`.github/workflows/tests.yml`](.github/workflows/tests.yml)) runs pytest on every branch plus a frontend typecheck and build. Lint and type checks are **advisory** for now — there is a backlog of pre-existing findings, mostly whitespace and pre-PEP604 annotations — with a hard gate on undefined and redefined names. Pre-commit retires that backlog on changed files instead of blocking the whole pipeline.

---

## Deployment

The repo carries configuration for three targets. **Pick one**; keeping all three live is a known source of confusion.

| Target | Entry point | Notes |
| --- | --- | --- |
| **cPanel / Passenger** (currently live) | `passenger_wsgi.py` | Every request is proxied to the app — no static-file fallback, which is why `.well-known` is served in Python. See [deploye_to_milesweb.md](deploye_to_milesweb.md). |
| **Render** | `render.yaml` + `build.sh` | Blueprint deploy with managed Postgres. See [RENDER_DEPLOY.md](RENDER_DEPLOY.md). |
| **Vercel** (frontend) | `frontend/` | SPA only; needs `VITE_API_URL` pointing at the backend. |

General notes: [DEPLOYMENT.md](DEPLOYMENT.md).

Before any production deploy:

- [ ] `ENVIRONMENT=production` and real `SECRET_KEY` / `ENCRYPTION_KEY` set — the app will refuse to start otherwise
- [ ] `ENCRYPTION_KEY` is the *same* value as the previous deploy
- [ ] `CORS_ORIGINS` and `FRONTEND_URL` match the real domains
- [ ] `RAZORPAY_WEBHOOK_SECRET` set if billing is enabled — the webhook returns 503 without it
- [ ] pending migrations applied
- [ ] `frontend/dist` built, if FastAPI is serving the SPA

---

## Security notes

Applied and enforced by tests in `tests/test_security_regressions.py`:

- **No credentials in URLs.** Broker keys and secrets, OAuth request tokens, Razorpay identifiers, CAS passwords and the JWT all travel in request bodies or headers. Query strings reach access logs, proxy logs, browser history and `Referer` headers.
- **Payments are bound.** A valid Razorpay signature is necessary but not sufficient: the order is fetched server-side and checked against the caller, the price and its paid status, then recorded under a unique constraint before anything is granted.
- **Failures are loud.** A missing `ENCRYPTION_KEY`, an undecryptable credential, a missing webhook secret and a placeholder `SECRET_KEY` all raise. None of them degrade quietly.
- **Security headers** on every response: CSP, `Referrer-Policy: no-referrer`, `X-Content-Type-Options`, `X-Frame-Options`, HSTS in production.
- **Credentials encrypted at rest** with Fernet; passwords hashed with argon2.
- **Rate limiting** on login, registration and both password-reset endpoints.

Known gaps, in priority order: access tokens last 30 days and are not revocable (logout is client-side only); rate limiting is per-process, so it weakens behind multiple workers; the Google OAuth callback still hands the JWT to the frontend as a query parameter (scrubbed from history on arrival, but a one-time exchange code is the real fix).

Found something? Open a private security advisory rather than a public issue.

---

## Documentation index

**Start here**
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — layering and module responsibilities
- [docs/SOFTWARE_DESIGN_DOCUMENT.md](docs/SOFTWARE_DESIGN_DOCUMENT.md) — full design
- [ROADMAP.md](ROADMAP.md) · [docs/FEATURE_GAPS.md](docs/FEATURE_GAPS.md) · [FEATURES_CHECKLIST.md](FEATURES_CHECKLIST.md)

**Setup and operations**
- [DEPLOYMENT.md](DEPLOYMENT.md) · [RENDER_DEPLOY.md](RENDER_DEPLOY.md) · [deploye_to_milesweb.md](deploye_to_milesweb.md)
- [SUPABASE_SETUP.md](SUPABASE_SETUP.md) · [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md)
- [ZERODHA_SETUP.md](ZERODHA_SETUP.md) · [ZERODHA_AUTH_DEBUGGING.md](ZERODHA_AUTH_DEBUGGING.md)

**Compliance**
- [docs/TERMS_AND_CONDITIONS.md](docs/TERMS_AND_CONDITIONS.md) · [docs/CONSENT_REQUIREMENTS.md](docs/CONSENT_REQUIREMENTS.md)

**Product and strategy**
- [MONETIZATION_STRATEGY_2026.md](MONETIZATION_STRATEGY_2026.md) · [MONETIZATION_ACTION_PLAN.md](MONETIZATION_ACTION_PLAN.md) · [docs/START_EARNING.md](docs/START_EARNING.md)

Scratch notes and working files also live at the repo root (`*todolist.md`, `strategy*.md`, `stocksanalyzer.md`, `prompt.txt`). They are working material, not documentation — worth moving under `docs/notes/` or deleting.

---

## Contributing

1. Branch from `main`.
2. `uv run pre-commit install` before your first commit.
3. Keep the layering: routers do HTTP, services do logic, repositories do SQL. A service importing `fastapi` is a smell.
4. Domain changes need tests — `ledger/`, `tax_calculator.py` and `portfolio_analytics.py` especially.
5. Never put a credential in a query parameter. A pre-commit hook will stop you.

## License

MIT — see [LICENSE](LICENSE).
