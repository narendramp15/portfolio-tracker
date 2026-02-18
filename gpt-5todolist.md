# GPT-5 Todo List

Date: 2026-02-15

This file contains the consolidated TODOs discovered while scanning the repository (backend + frontend).

## Summary

- Explored backend request flow and main entrypoints.
- Explored frontend API client and auth interceptor.
- Identified potential bugs and improvement areas; listed below as actionable tasks.

## Todo

- [x] Explore backend request flow
- [x] Explore frontend request flow
- [x] Summarize and identify potential bugs
- [ ] Fix CORS preflight response headers (`portfolio_tracker/main.py`)
  - Raw ASGI `CORSPreflightMiddleware` sends empty header values when origin not allowed and may return 403 with empty origin header; ensure headers are not empty and logic matches `CORSMiddleware` behavior.
- [ ] Avoid committing inside loop in Zerodha holdings sync (`portfolio_tracker/routers/broker.py`)
  - Currently commits inside the holdings loop; move commit outside loop and batch operations to reduce DB overhead and avoid partial commits on failure.
- [ ] Improve `EncryptionManager` key handling and logging (`portfolio_tracker/encryption.py`)
  - Avoid printing/generating keys at runtime in production; log warnings via logger and surface config guidance.
- [ ] Remove plaintext token prints in forgot-password flow (`portfolio_tracker/routers/auth.py`)
  - Development-only prints leak tokens to stdout; replace with secure email sending or remove logs.
- [ ] Add unit tests for token extraction (`portfolio_tracker/deps.py`)
  - Test extraction via `?token=` query and `Authorization: Bearer ...` header, and expected 401 path when missing.
- [ ] Improve frontend auth interceptor robustness (`frontend/src/lib/api.ts`)
  - Ensure interceptor handles missing `localStorage` gracefully and does not overwrite existing headers object unexpectedly.
- [ ] Consider moving `create_tables()` to startup event to avoid import side-effects (`portfolio_tracker/main.py`)
  - Calling `create_tables()` at import time can cause DB activity during tests or imports; prefer `@app.on_event("startup")`.

## Notes / Next steps

- I can start implementing any of the unchecked items; tell me which to do first or I can proceed with priority (security fixes first).
