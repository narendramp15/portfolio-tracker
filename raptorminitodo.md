# Raptor Mini TODO

## Summary ✅
- Fixed: `POST /api/broker/fivepaisa/setup` now accepts legacy `api_key`/`api_secret` and is backwards-compatible. (Edited: `portfolio_tracker/routers/broker.py`) — tests now pass.

---

## High priority 🔥
1. Add unit tests for 5Paisa setup edge-cases
   - Files: `tests/test_broker_setup.py`
   - Acceptance: cover legacy `api_key`/`api_secret`, full-params path, and missing/partial extra_config.

2. Frontend: validate token on load (prevent stale-token UI) — DONE
   - Files updated: `frontend/src/providers/auth/AuthProvider.tsx`, `frontend/src/router/RequireAuth.tsx`
   - Behaviour: `GET /api/auth/me` validation at app init; on 401 performs logout + redirect to `/login`.
   - Tests added: `frontend/src/providers/auth/__tests__/AuthProvider.test.tsx`

3. Replace `print()` with structured logging in backend
   - Targets: `portfolio_tracker/encryption.py`, `portfolio_tracker/services/price_history.py`, other modules that use `print()` for runtime messages.

---

## Medium priority ⚙️
4. Tighten CORS preflight response
   - File: `portfolio_tracker/main.py`
   - Fix: avoid sending empty `Access-Control-Allow-Origin` header when origin not allowed; return 403/clear message.

5. Migrate Pydantic `Config` classes to `ConfigDict`
   - File: `portfolio_tracker/schemas.py`
   - Reason: remove deprecation warnings and future-proof the codebase.

6. Raise automated test coverage for untested modules
   - Targets: `brokers/*`, `routers/*` (broker/token-refresh), `services/*` (price_history, market_data, technical_indicators).

---

## Low priority / improvements 🛠️
7. Add integration / e2e smoke test
   - Verify SPA serves, login flow, basic API endpoints.

8. CI: enforce pytest + coverage thresholds
   - Add CI job to fail on regressions.

9. Documentation: update `ZERODHA_AUTH_DEBUGGING.md` and `README.md` with the 5Paisa legacy-params note.

---

## Completed / Notes ✅
- Fixed failing test: `tests/test_broker_setup.py::TestBrokerSetup::test_fivepaisa_setup_success` by making the 5Paisa setup endpoint accept legacy param names.
- All tests pass locally after the fix.

---

---

## Monetization Features (Q2 2026) 💰

### Phase 1: Billing Infrastructure (Weeks 1-8)
10. **Payment Gateway Integration**
    - [ ] Choose payment gateway (Razorpay vs. Stripe)
    - [ ] Create subscription products (Free, Pro ₹199/mo, Teams ₹999/mo)
    - [ ] Add `SubscriptionModel` and `PaymentModel` to database
    - [ ] Implement webhook handlers for subscription events
    - [ ] Create `/billing` router in backend
    - Files: `portfolio_tracker/models.py`, `portfolio_tracker/routers/billing.py`

11. **Feature Gating Middleware**
    - [ ] Create `@require_subscription(plan="pro")` decorator
    - [ ] Gate broker connections (Free: 2, Pro: 5+)
    - [ ] Gate CSV exports (Free: 3/month, Pro: unlimited)
    - [ ] Add subscription tier to JWT claims
    - Files: `portfolio_tracker/deps.py`, `portfolio_tracker/routers/broker.py`

12. **Frontend Pricing & Upgrade Flow**
    - [x] Create standalone `/pricing` page — DONE
    - [x] Add `/pricing` route to router — DONE
    - [ ] Build upgrade modal in Settings page
    - [ ] Integrate Razorpay/Stripe checkout UI
    - [ ] Add upgrade CTAs to dashboard, analytics, brokers pages
    - Files: `frontend/src/ui/pages/SettingsPage.tsx`, `frontend/src/components/UpgradeModal.tsx`

13. **Analytics & Monitoring**
    - [ ] Integrate Mixpanel or PostHog
    - [ ] Track conversion events (signup, upgrade_clicked, payment_success)
    - [ ] Build internal admin dashboard (`/admin` route)
    - [ ] Setup Slack/email alerts for new subscriptions
    - Files: `frontend/src/lib/analytics.ts`, `frontend/src/ui/pages/AdminDashboard.tsx`

14. **Legal & Compliance**
    - [ ] Update Terms of Service (subscription terms, refund policy)
    - [ ] Update Privacy Policy (payment processor data sharing)
    - [ ] Add consent checkbox for data processing
    - Files: `docs/TERMS_AND_CONDITIONS.md`, consent UI in broker connection flow

### Phase 2: Pro Features (Weeks 9-16)
15. **Price Alerts**
    - [ ] User-defined price targets (email + SMS via Twilio)
    - [ ] Backend cron job (check prices every 5 min)
    - [ ] Alert history and management UI
    - Files: `portfolio_tracker/routers/alerts.py`, `frontend/src/ui/pages/AlertsPage.tsx`

16. **Advanced Technical Indicators**
    - [ ] Bollinger Bands, VWAP, Fibonacci retracements
    - [ ] Custom indicator builder for power users
    - Files: `portfolio_tracker/services/technical_indicators.py`

17. **Mutual Fund Tracking**
    - [ ] Integrate with MFCentral API or CAMS
    - [ ] Display MF holdings alongside stocks
    - [ ] NAV tracking and returns calculation
    - Files: `portfolio_tracker/brokers/mutual_funds.py`

18. **Hourly Auto-Sync (Pro only)**
    - [ ] Background cron job for Pro users
    - [ ] Sync all connected brokers hourly
    - [ ] Last sync timestamp display
    - Files: `portfolio_tracker/services/auto_sync.py`

### Phase 3: Affiliate & Growth (Weeks 9-12)
19. **Affiliate Partnerships**
    - [ ] Sign affiliate agreements (Angel One, Upstox, Cleartax, Groww)
    - [ ] Add affiliate tracking (UTM parameters, clicks, conversions)
    - [ ] Strategic placement (Settings → Brokers, Tax Reports page)
    - Files: `portfolio_tracker/routers/affiliates.py`, database tracking

20. **Referral Program**
    - [ ] "Invite a friend, both get 1 month Pro free"
    - [ ] Unique referral links per user
    - [ ] Referral dashboard
    - Files: `portfolio_tracker/routers/referrals.py`, `frontend/src/ui/pages/ReferralsPage.tsx`

---

## Next steps (pick one)
- [ ] I can add the 5Paisa unit tests now
- [ ] I can implement frontend token validation  
- [ ] I can clean up `print()` → `logger` in specified files
- [ ] I can update the CORS preflight behavior
- [ ] I can start implementing billing infrastructure (payment gateway integration)

Reply with which task you want me to do next and I will implement it.
