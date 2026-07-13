# Software Design Document — Portfolio Tracker

**Author**: Generated with Claude Code, reviewed by project owner
**Date**: 2026-07-13
**Status**: Living document — reflects the codebase as of the July 2026 clean-architecture refactor (phase 1)

> **Primary goal (inferred, not stated by the requester)**: this document was requested without a stated
> migration target. Given the actual state of the repo — an in-progress layered-architecture refactor
> (see §5) and a production deployment that was unstable enough to require a full debugging session this
> week (see §5) — this SDD treats the primary goal as **stabilizing production deployment and paying down
> the documented migration debt**, not a rewrite or a framework change. If the real goal is different
> (e.g., a TypeScript rewrite, a microservices split), section 6 should be revisited with that constraint
> stated explicitly.

---

## 1. Project Overview & Context

### What it does

Portfolio Tracker is a web application for Indian retail investors to track equity and mutual fund
portfolios in one place. Its core value proposition, distinct from a generic portfolio spreadsheet:

- **Multi-broker aggregation** — connects to five Indian brokers (Zerodha, Angel One, 5Paisa, Dhan,
  Groww) via their APIs and syncs holdings/trades automatically, so a user with accounts across
  multiple brokers sees one consolidated view.
- **Manual + CAS-import mutual fund tracking** — mutual fund folios can be added manually or imported
  in bulk from CAMS/KFintech Consolidated Account Statement (CAS) PDFs.
- **Indian tax compliance** — computes short-term/long-term capital gains (STCG/LTCG) using FIFO/LIFO
  matching against India's April–March financial year, with CSV/PDF export.
- **AI-assisted analysis** — technical indicators (RSI, MACD, Bollinger Bands, moving averages) plus an
  LLM-generated (Anthropic) investment thesis per stock, and a separate "Nifty Options Analyzer" AI
  feature, both server-proxied so API keys never reach the browser.
- **Subscription billing** — tiered plans (Free / Pro / Teams) enforced server-side via quota checks,
  billed through Razorpay (India-focused payment gateway).

### High-level architecture

```
┌─────────────────────┐        HTTPS/JSON, JWT bearer         ┌──────────────────────────────┐
│  React SPA           │ ─────────────────────────────────────▶│  FastAPI monolith             │
│  (Vercel)             │                                       │  (Milesweb shared cPanel,     │
│  quantleap.in          │◀──────────────────────────────────── │   Passenger WSGI)              │
└─────────────────────┘                                        │  api.quantleap.in              │
                                                                 └───────────┬───────────────────┘
                                                                             │
                       ┌─────────────────────────────────────────────────────────────────────────┐
                       │                                                                           │
              ┌────────▼────────┐   ┌────────────────┐   ┌───────────────┐   ┌───────────────────┐
              │ PostgreSQL        │   │ Broker APIs      │   │ Yahoo Finance   │   │ Anthropic API,      │
              │ (Neon/Supabase)   │   │ (5 adapters)     │   │ (yfinance)      │   │ Razorpay, Google    │
              │                   │   │                  │   │                 │   │ OAuth, SMTP          │
              └───────────────────┘   └──────────────────┘   └─────────────────┘   └─────────────────────┘
```

Both frontend and backend are single deployable units (no separate microservices). The system is a
classic **modular monolith**: one FastAPI process serves the entire API surface; the frontend is a
static SPA build.

---

## 2. System Architecture & Components

### Frontend

- **Stack**: React 19 + TypeScript, Vite 7, Tailwind CSS, Zustand (client state), TanStack Query (server
  state/caching), react-hook-form + zod (forms/validation), axios (HTTP), Recharts (charts), react-router-dom 7.
- **Structure** (`frontend/src/`): `ui/pages/` (route-level screens — dashboard, holdings, transactions,
  brokers, mutual funds, tax reports, billing, stock screener, technical analysis, options analyzer),
  `ui/components/` (reusable widgets), `ui/layout/` (shell/sidebar/topbar), `providers/auth/` (JWT session
  state), `providers/theme/`, `store/` (Zustand), `lib/api.ts` (single axios instance — see below), `router/`.
- **Hosting**: Vercel, static build output. DNS for `quantleap.in` is managed via Vercel's nameservers
  (domain registered at GoDaddy, but GoDaddy is not the DNS authority).
- **API base URL**: `frontend/src/lib/api.ts` — `baseURL: import.meta.env.VITE_API_URL || '/api'`. In
  local dev this falls back to `/api`, proxied by Vite (`vite.config.ts`) to `localhost:8000`. In
  production it's pinned to `https://api.quantleap.in/api` via Vercel env vars, baked in at build time
  (changing it requires a redeploy, not just an env var update).

### Backend

- **Stack**: Python 3.13, FastAPI, SQLAlchemy 2.0 (ORM), Pydantic v2, `python-jose` (JWT), `passlib[argon2]`
  (password hashing), `cryptography` (Fernet, for broker credential encryption).
- **Layered architecture** (`portfolio_tracker/`, enforced top-down, documented in `docs/ARCHITECTURE.md`):

  | Layer | Location | Responsibility |
  |---|---|---|
  | Delivery (HTTP) | `api/`, `routers/` | Request parsing, domain-error → HTTP-status mapping, response shaping. No business rules, no SQL. |
  | Services (domain) | `services/` | Business logic: broker credential vault, portfolio sync, plan entitlements, tax calc, market data, CSV import. Raises `ValueError`/domain exceptions. |
  | Adapters (integrations) | `brokers/` | One class per broker (Zerodha, 5Paisa, Angel, Dhan, Groww). Vendor payload → neutral `BrokerHolding` schema. No DB access. |
  | Persistence | `repositories/` | One module per aggregate (users, portfolios, assets, transactions, broker_configs). Pure queries/writes; caller owns the `Session`. |
  | Infrastructure | `config.py`, `database.py`, `auth.py`, `encryption.py`, `rate_limit.py`, `models.py`, `schemas.py` | Settings, engine/session, JWT + hashing, Fernet encryption, ORM models, Pydantic schemas. |

  A rule worth calling out because it's a real invariant, not aspirational: **the encryption boundary is
  `services/broker_accounts.py`** — code above it sees plaintext broker credentials, the repository and DB
  only ever see ciphertext, and `EncryptionManager` must never be called directly from a router.

- **URL map**: every route is registered in one table, `api/routes.py` (`API_ROUTERS`), rather than
  scattered `app.include_router()` calls — 14 routers covering auth, portfolios (mounted at both
  `/api/portfolios` and the legacy `/api/portfolio` alias), transactions, dashboard, market data, broker
  integration, technical analysis, tax reports, broker token refresh, AI proxy, billing, mutual funds,
  and stock screener.
- **Deployment mechanics** (the hard-won part): the backend runs as a WSGI app under Phusion Passenger on
  shared cPanel hosting (Milesweb). Since FastAPI is ASGI-only, `passenger_wsgi.py` is a hand-written
  synchronous ASGI↔WSGI bridge (`asyncio.run()` per request) — there is no uvicorn/gunicorn process
  manager in production; Passenger itself manages the worker process.
  - The backend is served at a **dedicated subdomain, `api.quantleap.in`**, not cPanel's
    auto-provisioned `*.cpanel.site` hostname. That auto-hostname is flagged internally by cPanel as a
    "technical domain" and silently blocks cross-site browser requests (`Sec-Fetch-Site: cross-site`)
    with a 428 interstitial page — while direct navigation and tools like `curl` pass through fine. This
    presented as an unsolvable CORS error for days until the actual response body was inspected. See
    `deploye_to_milesweb.md` for the incident writeup.
  - `.htaccess` is **deliberately absent** from the app directory: cPanel's Python Selector (Setup Python
    App) configures Passenger routing at the vhost level for this domain, and any `.htaccess` that
    re-declares `PassengerEnabled`/rewrite rules conflicts with that and 500s every request, regardless
    of the file's content.
  - CORS is enforced entirely inside the FastAPI app (`api/middleware.py`'s `CORSPreflightMiddleware`,
    layered outermost so it answers `OPTIONS` before `SessionMiddleware` can reject the request, plus
    `CORSMiddleware` for normal responses) — not at any reverse-proxy layer, since that layer has proven
    unreliable on this host (`AllowOverride` restrictions silently drop `Header` directives).

### Database

- SQLAlchemy ORM. **PostgreSQL in production** (Neon or Supabase — README documents both as free-tier
  options; `config.py` also supports MySQL via `pymysql`/individual `PG*` env vars). **SQLite for local
  dev and the test suite** (file-based, one per test session, to avoid shared-cache issues).
- `create_tables()` runs unconditionally at **import time** in `main.py` — not a lifespan hook, not a
  migration tool. This means a transient DB outage at process start crashes the entire app before any
  request-level error handling exists (flagged in §5).

### Third-party integrations

| Integration | Purpose | Notes |
|---|---|---|
| Zerodha, Angel One, 5Paisa, Dhan, Groww | Broker holdings/trade sync | Per-vendor adapter classes in `brokers/`; credentials encrypted at rest |
| Yahoo Finance (`yfinance`) | Live/historical market data, symbol search | `services/market_data.py`; price history cached in a lean `price_history` table (recent closes only) |
| Anthropic API | AI stock thesis (Pro feature) + Nifty Options Analyzer | Server-side only (`ANTHROPIC_API_KEY` never sent to browser); responses cached in `StockThesisCacheModel` to bound cost; every call audit-logged (`OptionsAnalysisLogModel`, without storing prompt content) |
| Razorpay | Subscription billing (India) | Idempotency via `ProcessedPaymentModel`; webhook secret verification |
| Google OAuth | One-click sign-in | `authlib` |
| SMTP | Password-reset emails | Falls back to console log if unset (dev convenience) |

### Communication patterns

- Frontend ↔ Backend: REST over HTTPS, JSON bodies, JWT bearer token in `Authorization` header (30-day
  expiry), CORS-gated by an explicit origin allowlist (`CORS_ORIGINS`, auto-expanded to include both
  `www.` and bare variants).
- Backend ↔ Brokers/Yahoo Finance/Anthropic/Razorpay: outbound HTTPS via `requests`/`httpx`/vendor SDKs
  (`kiteconnect`, `py5paisa`), synchronous.

---

## 3. Data Model & Storage

Core tables (SQLAlchemy models in `models.py`; `UserModel` is the graph's single highest-connectivity
node — 217 edges in the dependency graph — touched by nearly every feature):

| Model | Table | Purpose |
|---|---|---|
| `UserModel` | `users` | Account, subscription tier, auth |
| `PasswordResetTokenModel` | `password_reset_tokens` | Password-reset flow |
| `PortfolioModel` | `portfolios` | User's named portfolios (1 user : N portfolios) |
| `AssetModel` | `assets` | Holdings within a portfolio |
| `TransactionModel` | `transactions` | Buy/sell trade history |
| `BrokerTemplateModel` | `broker_templates` | Static per-broker config metadata |
| `BrokerConfigModel` | `broker_configs` | Per-user encrypted broker credentials + sync state |
| `PriceHistoryModel` | `price_history` | Lean cache: recent daily closes only, not a full time series store |
| `ExportLogModel` | `export_logs` | CSV export events, used for free-tier quota enforcement |
| `OptionsAnalysisLogModel` | `options_analysis_logs` | Audit log for AI calls (no prompt content stored) |
| `ProcessedPaymentModel` | `processed_payments` | Razorpay payment idempotency ledger |
| `MutualFundHoldingModel` | `mf_holdings` | MF folios (manual entry or CAS import) |
| `MutualFundTransactionModel` | `mf_transactions` | Individual SIP/purchase/redemption records |
| `StockThesisCacheModel` | `stock_thesis_cache` | Server-side cache of AI-generated per-stock theses (Pro feature) |

Relationships are conventional one-to-many hanging off `UserModel` and `PortfolioModel`; there is no
graph/document data, no denormalized read models, and no event sourcing — a straightforward relational
schema.

**Encryption boundary**: `BrokerConfigModel` credential fields are Fernet-encrypted
(`encryption.py::EncryptionManager`) before they ever reach the repository layer; the encryption key
(`ENCRYPTION_KEY`) must be persistent across deploys or existing stored credentials become unreadable.

**Frontend state**: server data lives in TanStack Query's cache (fetched via `lib/api.ts`); local/UI
state (theme, sidebar, etc.) in Zustand (`store/appStore.ts`); the JWT and a denormalized user object are
persisted to `localStorage` directly by `AuthProvider` (not through Zustand), validated against
`/api/auth/me` on mount.

---

## 4. Non-Functional Requirements

### Security

- Passwords hashed with argon2 (`passlib`); JWTs signed with `SECRET_KEY`, HS256, 30-day expiry.
- Broker credentials encrypted at rest (Fernet); the encryption boundary is enforced by code convention
  (documented in `docs/ARCHITECTURE.md`), not by a runtime check — a router *could* call
  `EncryptionManager` directly and nothing stops it today.
- CORS: explicit origin allowlist, wildcard-with-credentials blocked in code
  (`config.py::CORS_ORIGINS` raises/falls back rather than allowing `*` + credentials).
- Rate limiting on auth endpoints (`rate_limit.py`, in-memory sliding window — see scalability note below).
- A prior incident (fixed in the July 2026 refactor) had auth-failure logging dump full request headers,
  leaking `Authorization` tokens into logs — now removed.
- `SECRET_KEY` has a hardcoded development fallback (`"dev-secret-key-change-in-production"`) in
  `config.py`. If unset in any deployment environment, the app runs with a **publicly known** JWT signing
  key rather than failing to start. This is a real risk, not just a lint nag.
- `.env` files (containing `ANTHROPIC_API_KEY`, DB credentials, etc.) are loaded via `python-dotenv` both
  in `config.py` and independently in `passenger_wsgi.py` — two load points for the same file, worth
  consolidating (minor, not a security issue per se).

### Scalability

- The production backend is a **single Passenger worker process on shared cPanel hosting**. There is no
  load balancer, no horizontal scaling path, and no separate worker/queue tier — CPU-bound work (PDF
  parsing for CAS import, AI proxy calls, technical-indicator calculation) runs inline in the request
  path.
- Rate limiting is in-memory (`rate_limit.py`) — correct for a single process, but would silently stop
  working correctly (each process gets its own independent counter) the moment the deployment gains a
  second worker.
- The managed Postgres tier (Neon/Supabase free tier, per README) has its own connection limits and, on
  some providers, auto-suspend-on-idle behavior — worth confirming which provider and tier is actually in
  use in production, since that directly affects the `create_tables()`-at-import-time risk below.

### Performance

- Market data: `price_history` is intentionally a lean table (recent closes only, not full history) —
  a deliberate cache-not-store design to bound Yahoo Finance calls and DB size.
- AI cost control: `StockThesisCacheModel` caches generated theses server-side rather than re-calling
  Anthropic per request; `OptionsAnalysisLogModel` implies cost/usage is tracked per call.
- No CDN/edge-caching layer evident for the API (expected, given it's a small user base on shared
  hosting); the frontend gets Vercel's edge network for free.

### Accessibility

- No accessibility tooling detected (`eslint-plugin-jsx-a11y`, `axe-core`, etc. are absent from
  `frontend/package.json`). This is a genuine gap rather than a deliberate choice as far as the repo
  shows — worth an explicit decision (adopt tooling, or accept the gap) rather than leaving it implicit.

### Reliability / Observability

- `RequestLoggingMiddleware` logs every request/response pair with origin and status to Python's
  standard `logging` module — sufficient for the debugging done this session, but there is no
  structured logging, tracing, or metrics/APM system. Diagnosing the production outage this week required
  live `curl` probing against production because the deployed log stream alone couldn't distinguish
  "app crashed at import" from "Apache/cPanel rejected the request before reaching the app."
- Health check exists (`GET /health`) but nothing appears to poll it automatically (no uptime monitor
  configured in the repo).

---

## 5. Current Pain Points & Technical Debt

### From the codebase itself (documented in `docs/ARCHITECTURE.md`, in the maintainers' own priority order)

1. **ORM queries still leak into routers** for `dashboard.py`, `transactions.py`, `tax_reports.py`,
   `billing.py`, `stock_screener.py`, `mutual_funds.py` — the service/repository extraction done for the
   broker vertical slice hasn't been applied everywhere yet.
2. **`routers/broker.py` setup/callback flows still construct adapter clients inline**, per broker — a
   `BrokerClient` protocol + factory would collapse five near-identical code paths into one.
3. **`crud.py` is a deprecated compatibility facade** over `repositories/`, still imported from ~15 call
   sites (routers, tests, migration scripts) that haven't been updated.
4. **`models.py` / `schemas.py` are monolithic** — flagged for splitting once either passes ~600 lines.
5. **`services/broker_sync` commits once per holding**, not once per sync — inherited behavior, not a new
   bug, but a known transaction-batching gap with no failure-path test yet.
6. **`create_tables()` runs at import time** rather than in a FastAPI lifespan handler, and the project has
   no real migration tool (no Alembic) — schema changes are ad-hoc `run_*_migration.py` scripts committed
   to the repo root rather than versioned migrations.
7. **Root-directory hygiene**: triplicated `requirements*.txt` files, a committed `portfolio.db`,
   ad-hoc migration scripts, and `htmlcov/` coverage output are all committed to git. `pyproject.toml` +
   `uv.lock` is the actual source of truth for dependencies; the loose `requirements.txt` variants should
   be generated artifacts, not hand-maintained.
8. **`core.py` (`PortfolioTracker` class) is dead legacy code** — in-memory, unrelated to the real API,
   only exercised by `tests/test_core.py`. Both should be deleted together.

### From this week's production incident (not previously documented until now)

9. **The production deployment is fragile in ways that are invisible until they break.** Two separate
   root causes produced the *same symptom* (a browser-only CORS/network failure that looked identical to
   a misconfigured `Access-Control-Allow-Origin`):
   - An `.htaccess` file re-declaring Passenger directives conflicted with cPanel's own vhost-level
     config and 500'd every single request, with no trace in the application's own log (the crash
     happened before the app was ever invoked).
   - cPanel's auto-generated `*.cpanel.site` hostname blocks cross-site browser requests by design (a
     428 "Technical Domain" interstitial), which is indistinguishable from a CORS failure in Chrome's
     DevTools unless you inspect the actual response body.

   Both are now fixed and documented (`deploye_to_milesweb.md`, `docs/ARCHITECTURE.md` commit history),
   but the underlying risk — a shared-hosting + Passenger + manual-FTP-deploy pipeline with no staging
   environment and no deploy-time smoke test — remains. Nothing currently prevents this class of outage
   from recurring on the next manual file upload.
10. **No CI/CD gate before production.** `.github/workflows/tests.yml` runs the pytest suite on GitHub,
    but deployment to Milesweb is a manual FTP/File Manager upload with no automated step in between —
    a green test suite on `main` says nothing about whether the next manual upload will actually boot.
11. **`SECRET_KEY` silently defaults** to a known dev value instead of refusing to start in production if
    unset (see §4, Security).

### From the dependency graph (`graphify-out/GRAPH_REPORT.md`)

- `UserModel` (217 edges), `BrokerHolding`, and the five broker adapter classes (`ZerodhaBroker`,
  `AngelBroker`, `FivePaisaBroker`, `GrowwBroker`, `DhanBroker` — 52–78 edges each) are the dominant
  "god nodes." This is consistent with, not independent of, pain point #2 above: the five broker classes
  are structurally near-duplicates of each other, which is exactly why they show up as separately
  high-connectivity nodes instead of converging on a shared abstraction.

---

## 6. Future Proposed Architecture (RFC)

Given the actual scale of this project (single-team, shared-hosting deployment, a few hundred KLOC-scale
codebase, no evidence of a scaling bottleneck that a monolith can't handle), **the recommendation is
explicitly against a microservices split at this stage.** The pain points in §5 are consequences of an
unfinished refactor and a fragile deploy target, not of the monolith's architecture itself — splitting
services now would add operational surface area (more deploy targets, more network calls, more places
for the CORS-class of incident to recur) without solving any problem currently observed.

Proposed roadmap, in priority order, each step independently shippable:

### Phase A — Finish the in-progress refactor (low risk, already the documented plan)
Execute `docs/ARCHITECTURE.md`'s existing migration-debt list (§5, items 1–8) in the order already
specified there. This is the highest-leverage work available: it's already scoped, already has a
precedent (the broker vertical slice was done this way and verified behavior-preserving), and directly
reduces the "god node" coupling the graph analysis surfaced.

### Phase B — De-risk the deployment target
This week's incident cost real debugging time for something that should be structurally impossible:
1. Introduce a **staging subdomain** (e.g. `staging-api.quantleap.in`) on the same Milesweb account,
   pointed at a separate app directory, so `.htaccess`/Passenger config changes can be verified before
   touching production.
2. Add a **post-deploy smoke test** — even a five-line script that curls `/health` and one authenticated
   endpoint immediately after a manual upload — to catch the "every request 500s" class of failure before
   a user does.
3. Evaluate moving off shared cPanel hosting to a platform with real process management and zero-downtime
   deploys (Render is already partially set up per `render.yaml` and the README; Railway/Fly are
   alternatives). This removes the entire category of Passenger/`.htaccess`/vhost-conflict risk rather
   than continuing to route around it.
4. Replace `create_tables()`-at-import with a lifespan handler plus a real migration tool (Alembic),
   closing debt item #6 and removing the "DB hiccup at boot crashes the whole app with no log trace"
   failure mode observed this week.

### Phase C — Harden security posture
1. Make `SECRET_KEY` (and `ENCRYPTION_KEY`) **fail-fast** if unset outside test mode, instead of falling
   back to a known dev value.
2. Add a lint/CI check (or a runtime assertion) enforcing the encryption-boundary rule in
   `docs/ARCHITECTURE.md` §"Key rules" #2, so it can't silently regress as new routers are added.

### Phase D — Only if/when a real scaling signal appears
If broker-sync volume, AI-proxy call volume, or concurrent users grow to the point the single Passenger
process is measurably the bottleneck (not before), the first extraction candidate is **broker sync as a
queue-backed background worker** (separate from the request/response path) — not a broader microservices
split. This directly targets the one component (`services/broker_sync`) that already does slow,
per-holding, external-API-bound work inline in a request handler.

---

## Appendix: Reference facts for future sessions

- Frontend: Vercel, DNS on Vercel nameservers, domain registered at GoDaddy.
- Backend: Milesweb shared cPanel, Passenger WSGI, app directory `/home/tyerhinx/quantleap`, served at
  `api.quantleap.in` (own Let's Encrypt cert — reissue via cPanel **Let's Encrypt™ SSL**, not the generic
  "SSL/TLS Certificates" tool, and remember issued certs sit in "Not installed" status until explicitly
  installed).
- Deploys to Milesweb are manual (FTP/File Manager) — no git checkout on that server.
- Never upload `.htaccess` to the Milesweb app directory (see §2, §5).
- Full incident history for the production outage fixed this week: `deploye_to_milesweb.md` and git log
  on the `something-new` branch (commits `5478e88`, `5db0c87`).
