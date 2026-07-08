# Architecture

Last updated: July 2026 (clean-architecture refactor, phase 1).

## Layers

Request flow is strictly top-down; a layer may only import from layers below it.

```
┌────────────────────────────────────────────────────────────┐
│  Delivery (HTTP)         portfolio_tracker/api/            │
│                          portfolio_tracker/routers/        │
│  Parses requests, maps domain errors → HTTP statuses,      │
│  shapes responses. No business rules, no SQL.              │
├────────────────────────────────────────────────────────────┤
│  Services (domain)       portfolio_tracker/services/       │
│  Business logic: broker credential vault, portfolio sync,  │
│  plan entitlements, tax calculation, market data, CSV      │
│  import. Raises ValueError (or domain exceptions) — never  │
│  crafts HTTP responses (known exception: entitlements).    │
├────────────────────────────────────────────────────────────┤
│  Adapters (integrations) portfolio_tracker/brokers/        │
│  One class per external broker API (Zerodha, 5Paisa,       │
│  Angel, Dhan, Groww). Translate vendor payloads into       │
│  neutral schemas (BrokerHolding). No DB access.            │
├────────────────────────────────────────────────────────────┤
│  Persistence             portfolio_tracker/repositories/   │
│  One module per aggregate (users, portfolios, assets,      │
│  transactions, broker_configs). Only queries and writes;   │
│  callers own the Session.                                  │
├────────────────────────────────────────────────────────────┤
│  Infrastructure          config.py · database.py ·         │
│                          auth.py · encryption.py ·         │
│                          rate_limit.py · models.py ·       │
│                          schemas.py                        │
│  Settings, engine/session, JWT + password hashing, Fernet  │
│  encryption, ORM models, Pydantic schemas.                 │
└────────────────────────────────────────────────────────────┘
```

## Folder structure

```
portfolio_tracker/
├── main.py                    # Composition root ONLY: create_app(), middleware
│                              #   order, exports `app` (passenger/render) and
│                              #   `fastapi_app` (tests). ~90 lines.
├── api/
│   ├── middleware.py          # CORSPreflightMiddleware, RequestLoggingMiddleware
│   ├── pages.py               # SPA serving, legacy redirects, /health, static mounts
│   └── routes.py              # API_ROUTERS table — the entire URL map in one diff
├── routers/                   # Thin HTTP handlers (one file per feature area)
├── services/
│   ├── broker_accounts.py     # Credential vault: owns the encrypt/decrypt boundary
│   ├── broker_sync.py         # Holdings upsert + trade import (broker-agnostic)
│   ├── entitlements.py        # PLAN_LIMITS + quota enforcement per tier
│   ├── tax_calculator.py      # FIFO/LIFO capital gains (pre-existing)
│   ├── market_data.py …       # (pre-existing services unchanged)
├── repositories/
│   ├── users.py               # get/create user
│   ├── portfolios.py          # CRUD + portfolio stats
│   ├── assets.py              # CRUD + get_asset_by_symbol
│   ├── transactions.py        # CRUD + find_duplicate_transaction (sync dedupe)
│   └── broker_configs.py      # Encrypted-credential rows, sync timestamps
├── brokers/                   # Vendor API adapters (zerodha, fivepaisa, …)
├── models.py                  # SQLAlchemy ORM models
├── schemas.py                 # Pydantic request/response + BrokerHolding DTO
├── config.py                  # Pydantic settings (env-driven)
├── database.py                # Engine, SessionLocal, get_db
├── auth.py                    # JWT encode/decode, password hashing
├── encryption.py              # Fernet EncryptionManager
├── deps.py                    # FastAPI auth dependencies (get_current_user)
└── crud.py                    # ⚠ Compatibility facade → repositories/ (deprecated)
```

## Key rules

1. **Routers never touch the ORM.** They call repositories (simple reads) or
   services (anything with logic). The `db.query(...)` calls that remain in
   older routers are migration debt — see below.
2. **The encryption boundary is `services/broker_accounts.py`.** Code above it
   sees plaintext credentials; the repository and DB only ever see ciphertext.
   Never call `EncryptionManager` from a router.
3. **Services raise `ValueError` for domain failures.** Routers translate to
   HTTP statuses. `services/entitlements.py` currently raises `HTTPException(402)`
   directly (documented exception; lift the mapping if a non-HTTP caller appears).
4. **Every URL lives in `api/routes.py`.** Adding/removing an endpoint prefix is
   a one-table diff. The duplicate mount of `portfolio.router` at both
   `/api/portfolios` and `/api/portfolio` is intentional legacy compatibility.
5. **`main.py` exports are a public contract.** `app` is imported by
   `passenger_wsgi.py` and `render.yaml`; `fastapi_app` by `tests/conftest.py`.
   Do not rename.
6. **Callers own the unit of work.** Repository functions take an explicit
   `Session`; they commit per call today (pre-existing behavior). Batching
   commits (e.g., one commit per sync instead of one per holding) is a known
   optimization — do it deliberately, with tests, not as a drive-by.

## What changed in the phase-1 refactor (July 2026)

Behavior-preserving — verified by an identical 121-route table before/after and
the full pytest suite.

| Before | After |
|---|---|
| `main.py` (270 lines): middleware classes, SPA serving, router mounts, page routes | `main.py` (~90 lines) composition root + `api/middleware.py`, `api/pages.py`, `api/routes.py` |
| `crud.py`: flat 383-line module, function-level imports to dodge a circular dependency that didn't exist | `repositories/` — five aggregate modules with module-level imports; `crud.py` kept as a deprecated re-export facade |
| `deps.py`: auth dependencies + plan limits + export quotas + DB queries | `deps.py` auth-only; business policy in `services/entitlements.py` (names re-exported for compatibility) |
| `routers/broker.py`: 1,336 lines; the holdings-upsert loop copy-pasted 5× (Zerodha/Angel/5Paisa/Dhan/Groww); encryption calls inline in every endpoint | `routers/broker.py` ~660 lines of thin handlers; one `broker_sync.upsert_holdings()`, one `broker_sync.import_trades()`, credentials via `broker_accounts` |
| Dead `templates = Jinja2Templates(...)` in main; full request headers logged on auth failure | Removed (headers logging leaked Authorization tokens into logs) |

## Migration debt (next phases, in priority order)

1. **Move remaining ORM queries out of routers** — `dashboard.py`,
   `transactions.py`, `tax_reports.py`, `billing.py`, `stock_screener.py`,
   `mutual_funds.py` still query models directly. Same recipe as the broker
   slice: extract a service + repository per feature, keep error strings.
2. **`routers/broker.py` per-broker service modules** — setup/callback flows
   still construct adapter clients in the router. A `BrokerClient` protocol +
   factory would let one generic endpoint set replace the per-broker copies.
   Do this when adding the next broker, not before.
3. **Retire `crud.py`** — update the ~15 import sites (routers, tests,
   migration scripts) to `repositories.*`, then delete the facade.
4. **Split `models.py` / `schemas.py` by aggregate** once either passes ~600
   lines.
5. **Batch commits in `broker_sync`** — currently one commit per holding
   (inherited). Wrap each sync in a single transaction and add a failure test.
6. **`create_tables()` at import time** — move to a FastAPI lifespan handler
   and rely on Alembic-style migrations instead of `create_all`.
7. **Root-directory hygiene** — `requirements*.txt` triplicates, `portfolio.db`,
   ad-hoc `run_*_migration.py`, `htmlcov/` are committed; consolidate on
   `pyproject.toml`/`uv.lock` and gitignore artifacts.
8. **`core.py` (`PortfolioTracker` class)** — in-memory legacy unrelated to the
   API; only `tests/test_core.py` uses it. Delete both together.
