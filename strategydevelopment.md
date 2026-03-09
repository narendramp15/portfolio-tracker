# QuantLeap.in — Options Analyzer Production Upgrade Spec

> **Version:** 1.0 | **Status:** Ready for Dev | **Audience:** Coding Agent | **Classification:** CONFIDENTIAL

---

## 1. Project Overview

QuantLeap.in currently has a login system and a basic `/app/option-analyzer` route. This document specifies ALL changes required to upgrade it into a production-grade, monetised SaaS with route protection, tier-based AI model selection, and per-usage billing.

> 🚨 **CRITICAL RULE:** The words `Haiku`, `Sonnet`, `Opus`, `Claude`, or any Anthropic model identifiers must **NEVER** appear anywhere in the user-facing UI, emails, or billing pages.

---

## 2. Route Protection

### 2.1 Guard: /app/option-analyzer

Every request to `/app/option-analyzer` (and all sub-routes) must be intercepted before rendering:

1. Read session/JWT token from memory (never `localStorage`).
2. If token is absent or expired → redirect immediately to `/login?next=/app/option-analyzer`.
3. After successful login → redirect back to the original `?next=` destination URL.
4. If token is valid → verify tier from server-side session, then render the page.
5. On every Claude API call (server-side) → re-verify tier before selecting model. **Never trust client-side tier claims.**

### 2.2 Session Rules

- JWT expiry: **8 hours** for active sessions, **24 hours** if "Remember Me" is checked.
- Auto-refresh token silently 30 minutes before expiry if user is active.
- Force logout and redirect to `/login` on `401` from any protected API endpoint.
- Session timeout warning modal at T-5 minutes with option to extend.

---

## 3. Tier System

### 3.1 Tier Definitions

Map user-friendly tier names to internal models. This mapping lives **ONLY on the server** — never sent to the client.

| User Tier Name | Display Badge | Internal Model        | Daily Limit | Monthly Sub | Per Credit |
| -------------- | ------------- | --------------------- | ----------- | ----------- | ---------- |
| Starter 🥉      | `STARTER`     | [REDACTED — see §3.2] | 10 / day    | ₹99/mo      | ₹12/credit |
| Pro ⚡          | `PRO`         | [REDACTED — see §3.2] | 30 / day    | ₹299/mo     | ₹9/credit  |
| Elite 🏆        | `ELITE`       | [REDACTED — see §3.2] | Unlimited   | ₹799/mo     | ₹6/credit  |

### 3.2 Server-Side Model Mapping (Backend Only)

Store this mapping **ONLY** in backend environment variables or a secrets manager. Never in frontend code.

```js
// .env (server only — never commit actual values)
MODEL_STARTER=<haiku_model_string>
MODEL_PRO=<sonnet_model_string>
MODEL_ELITE=<opus_model_string>

// server/config.js
const TIER_MODEL_MAP = {
  starter: process.env.MODEL_STARTER,
  pro:     process.env.MODEL_PRO,
  elite:   process.env.MODEL_ELITE,
};
```

> ⚠️ Never hardcode model strings in source code. Use environment variables only. Rotate them without redeployment when new model versions release.

### 3.3 Tier Feature Matrix

| Feature                                  | Starter   | Pro       | Elite     |
| ---------------------------------------- | --------- | --------- | --------- |
| Quick Analysis (150-word)                | ✅         | ✅         | ✅         |
| Full Report (detailed trade plan)        | 🔒 Upgrade | ✅         | ✅         |
| Options Strategy (CE/PE suggestion)      | 🔒 Upgrade | ✅         | ✅         |
| Advanced Strategies (Iron Condor etc.)   | 🔒 Upgrade | 🔒 Upgrade | ✅         |
| Multi-index analysis (Nifty + BankNifty) | 🔒 Upgrade | ✅         | ✅         |
| Analysis History                         | Last 3    | Last 10   | Unlimited |
| Export Analysis as PDF                   | ❌         | ✅         | ✅         |
| Response Priority                        | Standard  | Standard  | Priority  |

---

## 4. Per-Usage Billing System

### 4.1 Credit System

Every analysis consumes credits. Users can subscribe monthly **OR** buy credit packs (credits never expire).

| Action                    | Credits Used | Starter              | Pro / Elite          |
| ------------------------- | ------------ | -------------------- | -------------------- |
| Quick Analysis            | 1 credit     | From daily allowance | From daily allowance |
| Full Analysis             | 3 credits    | ❌ Not available      | From daily allowance |
| Advanced Options Strategy | 5 credits    | ❌ Not available      | Elite only           |

### 4.2 Credit Packs (Pay-as-you-go)

| Pack Name    | Credits     | Price | Per Credit |
| ------------ | ----------- | ----- | ---------- |
| Starter Pack | 10 credits  | ₹99   | ₹9.90      |
| Growth Pack  | 40 credits  | ₹299  | ₹7.48      |
| Power Pack   | 120 credits | ₹749  | ₹6.24      |

### 4.3 Usage Tracking Requirements

- Track per user: `analyses_used_today`, `analyses_this_month`, `credits_balance`, `credits_used_this_month`.
- Reset daily counter at **midnight IST** using a cron job.
- Show live usage in header: `"12 / 30 analyses used today"` with progress bar.
- Warning toast at 80% daily usage: *"Only 6 analyses remaining today"*.
- Soft block at limit: disable Analyze button, show upgrade modal — do **NOT** hard 404.
- Billing page shows: current plan, credits left, monthly spend in ₹INR, full usage history.

---

## 5. UI Component Requirements

### 5.1 Login / Signup Page (`/login`)

- Two tabs: **Login** | **Sign Up**. No separate pages.
- Fields: Email, Password. Sign Up adds: Full Name, Confirm Password.
- "Remember Me" checkbox — sets 24h JWT expiry vs default 8h.
- After login → redirect to `?next=` param or `/app/option-analyzer`.
- Error states: wrong password (red inline), unverified email (yellow inline).
- Dark trading terminal aesthetic — consistent with main app.

### 5.2 Header (Authenticated)

The authenticated header must show, left to right:

- **QuantLeap logo** (links to `/dashboard`)
- **Live index ticker:** `Nifty ₹24,765 ▲ +1.2%` — refreshed every 60s
- **Tier badge pill:** `STARTER` / `PRO` / `ELITE` with colour coding
- **Usage counter:** `12 / 30 today` with mini progress bar
- **Credits badge:** `⚡ 28 credits` — click opens `/billing`
- **Avatar dropdown:** Profile | Billing | Logout

### 5.3 Analyzer Page — Feature Gating

- Locked features show a 🔒 icon instead of being hidden.
- Hovering a locked feature shows tooltip: *"Available on Pro plan — Upgrade ₹299/mo"*.
- Upgrade CTA button appears inline — non-intrusive but visible.
- When daily limit reached: Analyze button shows *"Limit Reached — Upgrade or Buy Credits"*.

### 5.4 Billing Page (`/billing`)

- Current plan card with renewal date and cancel option.
- Three plan cards (Starter / Pro / Elite) — current plan highlighted.
- Credit pack purchase section with three pack options.
- Usage breakdown: daily chart of analyses used this month.
- Invoice history table (mock for prototype).

---

## 6. Backend API Architecture

### 6.1 Endpoints Required

| Endpoint               | Method | Purpose                                                                    |
| ---------------------- | ------ | -------------------------------------------------------------------------- |
| `/api/auth/login`      | POST   | Validate credentials, return JWT                                           |
| `/api/auth/signup`     | POST   | Create user, return JWT                                                    |
| `/api/auth/refresh`    | POST   | Refresh expiring JWT                                                       |
| `/api/user/me`         | GET    | Return user profile + tier + usage                                         |
| `/api/analyze`         | POST   | Verify tier → select model → call AI API → deduct credit → return response |
| `/api/usage/today`     | GET    | Return daily usage stats for header                                        |
| `/api/billing/plans`   | GET    | Return plan definitions                                                    |
| `/api/billing/upgrade` | POST   | Upgrade tier (mock for prototype)                                          |
| `/api/billing/credits` | POST   | Purchase credit pack (mock)                                                |

### 6.2 POST /api/analyze — Critical Logic

This is the most important endpoint. Implement in this **exact order**:

1. **Authenticate:** Verify JWT. Return `401` if invalid.
2. **Load user tier** from DB — never from request body.
3. **Check daily limit:** If exceeded, return `429` with upgrade prompt.
4. **Check credit balance:** If insufficient, return `402` with credit pack CTA.
5. **Validate analysisType** against tier permissions. Return `403` if not allowed.
6. **Select model** from server-side `TIER_MODEL_MAP[user.tier]`.
7. **Build prompt** based on tier (see §9.2).
8. **Call AI API** with selected model. Never expose API key to client.
9. **On success:** Deduct credits, increment usage counters, save to history.
10. **Return** analysis text + updated usage stats to client.

> 🚨 The client should **NEVER** send model name, prompt type, or tier in the API request body. Tier is always derived server-side from the authenticated JWT.

---

## 7. Mock Users for Prototype / Demo

| Email                       | Password  | Tier    | Daily Left | Credits    |
| --------------------------- | --------- | ------- | ---------- | ---------- |
| `starter@demo.quantleap.in` | `demo123` | Starter | 3 / 10     | 5 credits  |
| `pro@demo.quantleap.in`     | `demo123` | Pro     | 22 / 30    | 40 credits |
| `elite@demo.quantleap.in`   | `demo123` | Elite   | Unlimited  | ∞ credits  |

---

## 8. Security Requirements

> 🚨 All items below are **REQUIRED** for production. Do not skip any.

- Anthropic API key stored in **server environment variable only** — never in client bundle.
- All `/api/*` routes require valid JWT except `/api/auth/login` and `/api/auth/signup`.
- Rate limit `/api/analyze` to **60 requests/hour** per IP regardless of tier.
- Rate limit `/api/auth/login` to **10 attempts/15min** per IP. Lock account for 30 min after 10 failures.
- Sanitize all market data inputs (`niftyClose`, `vix`, etc.) — accept numbers only.
- `TIER_MODEL_MAP` stored in environment variables. Rotate without code change.
- Log all `/api/analyze` calls: `user_id`, `tier`, `credits_used`, `timestamp` — no prompt content logged.
- HTTPS enforced. HSTS header set. No HTTP fallback.
- CORS: allow only `quantleap.in` and `app.quantleap.in` origins.

---

## 9. Implementation Notes for Coding Agent

### 9.1 Tech Stack Assumptions

- **Frontend:** React (existing) + Tailwind CSS
- **Backend:** Node.js / Express OR Next.js API routes — agent's choice based on existing stack
- **Auth:** JWT (`jsonwebtoken` library) — tokens in memory on client, HttpOnly cookie optional
- **DB:** For prototype use in-memory or JSON file. For production use PostgreSQL or Supabase.
- **Payments:** Razorpay (India) — mock for prototype, real integration in v2.

### 9.2 Prompt Construction by Tier

| Tier    | Prompt Type           | Extra Instructions                                                                                                                                                                                          |
| ------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Starter | Quick only (150-word) | No options strategy section                                                                                                                                                                                 |
| Pro     | Full (all 7 sections) | Standard full prompt                                                                                                                                                                                        |
| Elite   | Full + Advanced       | Append: *"Additionally provide: advanced options strategies including Iron Condor, Bull/Bear Spreads, and positional ideas with risk-defined entry. Include Greek analysis (Delta, Theta) where relevant."* |

> Never tell the user which prompt version they are receiving.

### 9.3 Frontend State Checklist

```js
authState:  { userId, email, name, tier, token, isAuthenticated }
usageState: { dailyUsed, dailyLimit, creditsBalance, monthlyUsed }
analysisHistory: [] // last N results by tier — React state only, never localStorage
```

### 9.4 Deliverables Expected from Coding Agent

1. `ProtectedRoute` wrapper component
2. Login / Signup page component
3. Updated header with tier badge + usage counter
4. Updated analyzer page with tier-gated feature locking
5. Billing / upgrade page
6. Backend API endpoints (§6.1) with mock data for prototype
7. `TIER_MODEL_MAP` in environment config (values redacted in committed code)
8. All existing analyzer functionality preserved and working

---

## 10. Acceptance Criteria

The upgrade is complete when **ALL** of the following pass:

- [ ] Visiting `/app/option-analyzer` without login redirects to `/login` immediately.
- [ ] After login with `starter@demo` user, Full Analysis button is locked with upgrade tooltip.
- [ ] After login with `pro@demo` user, Full Analysis runs and returns a response.
- [ ] No mention of `Haiku`, `Sonnet`, `Opus`, `Claude`, or model strings anywhere in the UI.
- [ ] Daily limit enforcement: starter user blocked after 10 analyses with upgrade modal shown.
- [ ] Credit deduction works: Quick = 1 credit deducted, Full = 3 credits deducted.
- [ ] Header shows correct tier badge and live usage counter after each analysis.
- [ ] Logout clears all state and redirects to `/login`.
- [ ] Direct URL access to `/billing` without login redirects to `/login`.
- [ ] Anthropic API key never appears in browser network tab or client-side bundle.

---

*QuantLeap.in — Internal Engineering Document — Do not distribute*