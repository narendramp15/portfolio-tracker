# QuantLeap.in — Profitability-First Development Prompt
### Options Analyzer SaaS — Billing, Tier & Cost Protection System

> **Hand this entire document to your coding agent.**
> Every decision below is made with margin protection as the primary constraint.

---

## 🎯 North Star Principle

> **Every line of code must protect the business margin.**
> The AI API cost is variable and can exceed revenue if unchecked.
> The system must make it structurally impossible to lose money on any user.

---

## 1. Pricing & Tier Architecture

### 1.1 User-Facing Tiers (Never expose internal model names)

| User Tier | Badge     | Daily Limit                  | Monthly Price | Per-Credit Price |
| --------- | --------- | ---------------------------- | ------------- | ---------------- |
| Starter 🥉 | `STARTER` | 10 analyses / day            | ₹99 / mo      | ₹12 / credit     |
| Pro ⚡     | `PRO`     | 30 analyses / day            | ₹299 / mo     | ₹9 / credit      |
| Elite 🏆   | `ELITE`   | 50 analyses / day (fair use) | ₹799 / mo     | ₹6 / credit      |

### 1.2 Server-Side Model Map (Backend `.env` Only)

```env
# NEVER commit actual model strings. Rotate without redeployment.
MODEL_STARTER=<haiku_model_string>
MODEL_PRO=<sonnet_model_string>
MODEL_ELITE=<opus_model_string>
```

```js
// server/config.js — never imported by frontend
const TIER_MODEL_MAP = {
  starter: process.env.MODEL_STARTER,
  pro:     process.env.MODEL_PRO,
  elite:   process.env.MODEL_ELITE,
};
```

> 🚨 The words `Haiku`, `Sonnet`, `Opus`, `Claude`, or any Anthropic model string
> must **never** appear in UI, emails, error messages, or API responses to the client.

### 1.3 Credit Cost Per Analysis (What User Spends)

| Analysis Type                                    | Credits Consumed | Available To     |
| ------------------------------------------------ | ---------------- | ---------------- |
| Quick Analysis                                   | 1 credit         | All tiers        |
| Full Report                                      | 3 credits        | Pro + Elite only |
| Advanced Strategy (Greeks, Iron Condor, Spreads) | 5 credits        | Elite only       |

### 1.4 Credit Packs (Pay-as-you-go — Best Margin Product)

| Pack Name    | Credits     | Price | Effective Per Credit |
| ------------ | ----------- | ----- | -------------------- |
| Starter Pack | 10 credits  | ₹99   | ₹9.90                |
| Growth Pack  | 40 credits  | ₹299  | ₹7.48                |
| Power Pack   | 120 credits | ₹749  | ₹6.24                |

> Credits never expire. Push credit packs aggressively — they are 96–99% margin.

---

## 2. Cost Protection Rules (Critical — Implement All)

### 2.1 Hard Limits Per Tier Per Day

These are **non-negotiable server-side limits**. Enforce on every `/api/analyze` call
before any model selection or API call is made.

```
Starter → MAX 10 analyses / day  (Quick only)
Pro     → MAX 30 analyses / day  (Quick + Full)
Elite   → MAX 50 analyses / day  (Quick + Full + Advanced)
```

> Elite is marketed as "priority access" not "unlimited."
> Fair use cap of 50/day must appear in Terms of Service.
> Never use the word "unlimited" in Elite marketing copy.

### 2.2 Token Budget Caps Per Call (Server-Side — Hard Enforce)

Set `max_tokens` on every Anthropic API call. Never let the model run open-ended.

```js
const TOKEN_BUDGETS = {
  starter_quick:    { max_input: 600,   max_output: 400  },  // ~₹0.04 / call
  pro_full:         { max_input: 2000,  max_output: 1000 },  // ~₹0.83 / call
  elite_advanced:   { max_input: 2500,  max_output: 1400 },  // ~₹1.74 / call
};
```

If a prompt exceeds max input tokens → truncate market data fields in priority order:
1. Keep: system instructions, tier prompt, key levels
2. Truncate first: majorEvents field (cap at 100 chars)
3. Truncate last: historical context

### 2.3 Prompt Caching (Non-Negotiable — Cuts Cost 60–70%)

The system prompt and tier instructions are identical on every call.
Cache them using Anthropic's prompt caching API.

```js
// Mark static parts as cacheable
messages: [
  {
    role: "user",
    content: [
      {
        type: "text",
        text: STATIC_SYSTEM_PROMPT,        // same every call
        cache_control: { type: "ephemeral" }  // cache this block
      },
      {
        type: "text",
        text: buildDynamicMarketData(userData)  // changes every call
      }
    ]
  }
]
```

> Cache read cost drops to $0.30/MTok vs $3.00/MTok for Sonnet.
> On 30 analyses/day per Pro user, this saves ~₹180/user/month.
> Implement prompt caching on Day 1 — not as an optimisation later.

### 2.4 Monthly Cost Circuit Breaker Per User

Track `ai_cost_inr` for every user in real time.
If a user's AI cost this month exceeds their revenue contribution → throttle to 5 analyses/day
and show a banner: *"You've reached your monthly analysis quota. Upgrade or purchase credits."*

```
Starter  → circuit breaker at ₹80  (revenue = ₹99, leaves ₹19 margin minimum)
Pro      → circuit breaker at ₹240 (revenue = ₹299, leaves ₹59 margin minimum)
Elite    → circuit breaker at ₹650 (revenue = ₹799, leaves ₹149 margin minimum)
```

### 2.5 Rate Limiting (Infrastructure Layer)

```
/api/analyze         → 60 requests / hour / IP  (all tiers)
/api/analyze         → burst cap: max 5 requests / 60 seconds / user
/api/auth/login      → 10 attempts / 15 min / IP
```

> Burst cap prevents scripts or bots from draining credits in seconds.

---

## 3. Margin-Aware Prompt Construction

### 3.1 Starter Prompt (Quick — uses MODEL_STARTER)

**Target:** ~400 input tokens, ~300 output tokens → ~₹0.04/call at Haiku pricing.

```
You are an expert intraday trading analyst for Indian markets.
Today: {DATE} | IST: {TIME}

Market Snapshot:
- Nifty Close: {niftyClose}
- Bank Nifty Close: {bankniftyClose}
- Gift Nifty: {giftNifty}
- India VIX: {vix}
- FII Activity: ₹{fiiActivity} Cr
- US Markets: {usMarket}%
- Events: {majorEvents}

Provide in under 150 words:
1. Market Bias (Bullish/Bearish/Sideways) — 1 line reason
2. Nifty key Support and Resistance (2 levels each)
3. Bank Nifty key Support and Resistance (2 levels each)
4. One trade setup: Index, Direction, Entry, SL, Target
Be direct. Numbers only. No fluff.
```

### 3.2 Pro Prompt (Full — uses MODEL_PRO)

**Target:** ~1,800 input tokens, ~900 output tokens → ~₹0.83/call at Sonnet pricing.

```
You are an expert SEBI-registered intraday trading analyst.
Today: {DATE} | IST: {TIME} | Trader Level: {traderLevel}

Market Data:
- Nifty Close: {niftyClose}        - Bank Nifty Close: {bankniftyClose}
- Gift Nifty: {giftNifty}          - India VIX: {vix}
- FII: ₹{fiiActivity} Cr           - DII: ₹{diiActivity} Cr
- US Markets: {usMarket}%          - Crude: ${crude}
- Dollar Index: {dollarIndex}      - Events: {majorEvents}

Provide all 7 sections:
1. MARKET BIAS — direction + sentiment score /10
2. KEY LEVELS — Nifty & BankNifty: S1, S2, R1, R2, Pivot
3. TRADE SETUPS (2-3) — each with: Index, Direction, Entry Zone,
   Stop Loss, Target 1, Target 2, R:R, CE/PE strike, time window
4. OPTIONS STRATEGY — Buy or Sell options today with VIX justification,
   strike + expiry recommendation
5. RISK FACTORS — what invalidates setups, sectors to avoid
6. TIMING GUIDE — best entry windows IST, chop zones, hard exit time
7. DISCIPLINE NOTE — one mindset tip for today's condition

Be specific with price levels. No vague advice.
```

### 3.3 Elite Prompt (Advanced — uses MODEL_ELITE)

**Target:** ~2,400 input tokens, ~1,300 output tokens → ~₹1.74/call at Opus pricing.

Use the full Pro prompt above and **append this block**:

```
ADDITIONALLY — Advanced Options Section (Elite only):

8. ADVANCED STRATEGIES
   - Evaluate and recommend ONE of: Iron Condor / Bull Call Spread /
     Bear Put Spread / Synthetic Long/Short — whichever fits today's
     VIX and trend best.
   - Provide: strikes, expiry, max profit, max loss, breakeven points
   - Net premium: credit or debit estimate in ₹
   - Greeks snapshot: approximate Delta, Theta, Vega impact

9. POSITIONAL IDEA (optional — only if strong setup exists)
   - If a 3–5 day positional setup is visible, describe it briefly:
     Index, direction, entry, SL, target, preferred instrument

Keep entire response under 1,400 output tokens.
```

> The output token cap instruction is literal — include it in the prompt text.
> This prevents Opus from writing essays and controls your API cost directly.

---

## 4. Revenue & Margin Projections

### 4.1 AI Cost Per User Per Month (Worst Case — Full Daily Usage)

| Tier             | Daily Analyses | Monthly Analyses | AI Cost / Month | Revenue | **Floor Margin**  |
| ---------------- | -------------- | ---------------- | --------------- | ------- | ----------------- |
| Starter (10/day) | 10 Quick       | 220              | ₹8.80           | ₹99     | **₹90.20 (91%)**  |
| Pro (30/day)     | 30 Full        | 660              | ₹547.80         | ₹299    | **⚠️ -₹248**       |
| Pro + caching    | 30 Full        | 660              | ₹164.34         | ₹299    | **₹134.66 (45%)** |
| Elite (50/day)   | 50 Advanced    | 1,100            | ₹1,914          | ₹799    | **⚠️ -₹1,115**     |
| Elite + caching  | 50 Advanced    | 1,100            | ₹574.20         | ₹799    | **₹224.80 (28%)** |

> Without prompt caching, Pro and Elite lose money for heavy users.
> **Prompt caching is not optional — it is the margin protection mechanism.**

### 4.2 Credit Pack Margins (Always Profitable)

| Pack            | Price | Max AI Cost (all credits used) | **Minimum Profit** | **Margin** |
| --------------- | ----- | ------------------------------ | ------------------ | ---------- |
| Starter (10 cr) | ₹99   | ₹0.44                          | **₹98.56**         | **99.6%**  |
| Growth (40 cr)  | ₹299  | ₹10.79                         | **₹288.21**        | **96.4%**  |
| Power (120 cr)  | ₹749  | ₹32.37                         | **₹716.63**        | **95.7%**  |

### 4.3 Target P&L at 100 Users

| Tier              | Users   | Monthly Revenue | Est. AI Cost | **Net Profit** | **Margin** |
| ----------------- | ------- | --------------- | ------------ | -------------- | ---------- |
| 50 Starter users  | 50      | ₹4,950          | ₹352         | **₹4,598**     | 93%        |
| 35 Pro users      | 35      | ₹10,465         | ₹3,920       | **₹6,545**     | 63%        |
| 15 Elite users    | 15      | ₹11,985         | ₹5,400       | **₹6,585**     | 55%        |
| Credit pack sales | —       | ₹4,500          | ₹135         | **₹4,365**     | 97%        |
| **TOTAL**         | **100** | **₹31,900**     | **₹9,807**   | **🟢 ₹22,093**  | **69%**    |

---

## 5. Implementation Checklist for Coding Agent

### Phase 1 — Cost Protection (Build First, Before Any Feature)
- [ ] `TIER_MODEL_MAP` in `.env` only — confirmed never in client bundle
- [ ] Hard daily limit check at top of `/api/analyze` before any API call
- [ ] `max_tokens` enforced on every Anthropic API call (values from §2.2)
- [ ] Prompt caching implemented for static system prompt blocks
- [ ] Per-user monthly cost tracker (`ai_cost_inr`) writing to DB on every call
- [ ] Monthly circuit breaker logic (values from §2.4)
- [ ] Burst rate limiter: max 5 requests / 60 seconds / user

### Phase 2 — Auth & Route Protection
- [ ] All `/app/*` routes redirect to `/login` if JWT absent or expired
- [ ] JWT stored in memory only — no `localStorage`, no `sessionStorage`
- [ ] Tier loaded from DB on every `/api/analyze` call — never from request body
- [ ] Session timeout warning at T-5 min with extend option

### Phase 3 — Tier-Gated UI
- [ ] Locked features show 🔒 with upgrade tooltip — never hidden entirely
- [ ] Header: tier badge + `X / Y analyses today` with progress bar
- [ ] Header: `⚡ N credits` badge linking to `/billing`
- [ ] Soft block at daily limit: button disabled + upgrade modal shown
- [ ] Circuit breaker banner when monthly cost cap hit

### Phase 4 — Billing Page
- [ ] Three plan cards with current plan highlighted
- [ ] Credit pack purchase section (Razorpay mock for prototype)
- [ ] Usage chart: daily analyses this month
- [ ] Show `credits_balance`, `analyses_today`, `analyses_this_month`

### Phase 5 — Observability
- [ ] Log every `/api/analyze` call: `user_id`, `tier`, `analysis_type`,
  `input_tokens`, `output_tokens`, `ai_cost_inr`, `cached`, `timestamp`
- [ ] Never log prompt content or market data in production logs
- [ ] Daily cost report: total AI spend vs total revenue (cron, midnight IST)
- [ ] Alert if any single user's monthly AI cost exceeds 90% of their revenue tier

---

## 6. Security Rules

- Anthropic API key in server `.env` only — confirmed absent from client bundle
- All `/api/*` require valid JWT except `/api/auth/login` and `/api/auth/signup`
- Sanitize all numeric inputs (`niftyClose`, `vix`, etc.) — reject non-numeric values
- HTTPS enforced, HSTS header set, no HTTP fallback
- CORS: allow `quantleap.in` and `app.quantleap.in` only
- Rate limit `/api/auth/login`: 10 attempts / 15 min / IP, 30 min lockout after breach

---

## 7. Mock Demo Users (Prototype)

| Email                       | Password  | Tier    | Daily Used | Credits |
| --------------------------- | --------- | ------- | ---------- | ------- |
| `starter@demo.quantleap.in` | `demo123` | Starter | 3 / 10     | 5       |
| `pro@demo.quantleap.in`     | `demo123` | Pro     | 22 / 30    | 40      |
| `elite@demo.quantleap.in`   | `demo123` | Elite   | 41 / 50    | 120     |

> Set elite demo user to 41/50 so the agent can test the near-limit warning state.

---

## 8. Acceptance Criteria

The build is production-ready when **every item below passes**:

**Cost Protection**
- [ ] Starter user blocked after 10 analyses — upgrade modal shown, no 500 error
- [ ] Pro user at 30/day cap blocked — circuit breaker activates gracefully
- [ ] Elite user at 50/day cap blocked — fair use banner shown
- [ ] `max_tokens` verified in Anthropic API call logs — no open-ended calls
- [ ] Prompt caching confirmed active — cache hit rate visible in server logs
- [ ] Monthly cost circuit breaker tested — throttle activates at correct ₹ threshold

**Security & Auth**
- [ ] `/app/option-analyzer` without token → immediate redirect to `/login`
- [ ] Tier cannot be spoofed via request body — server always reads from DB
- [ ] Anthropic API key absent from browser network tab and client JS bundle
- [ ] `Haiku`, `Sonnet`, `Opus`, `Claude` absent from all UI text and API responses

**Revenue**
- [ ] Credit deduction: Quick=1cr, Full=3cr, Advanced=5cr — verified in DB
- [ ] Credit pack purchase flow works end-to-end (mock Razorpay)
- [ ] Usage counter in header updates after each analysis without page reload
- [ ] Billing page shows accurate `credits_balance` and `analyses_today`

---

## 9. Recommended Pricing Adjustment (Before Launch)

Based on the margin analysis, consider these price changes before going live:

| Tier        | Current Price | Recommended | Reason                                                  |
| ----------- | ------------- | ----------- | ------------------------------------------------------- |
| Starter     | ₹99/mo        | ₹99/mo ✅    | Margin is safe at 91% even worst case                   |
| Pro         | ₹299/mo       | **₹399/mo** | At 30/day heavy use even with caching, ₹299 is thin     |
| Elite       | ₹799/mo       | **₹999/mo** | Opus is 5x more expensive than Haiku — buffer needed    |
| Growth Pack | ₹299 (40cr)   | ₹349 (40cr) | Small increase, still competitive, adds ₹50 pure margin |

> These are suggestions — implement current prices first, adjust after first 30 days of real usage data.

---

*QuantLeap.in — Profitability-First Engineering Spec — Confidential*
*Do not share outside the development team*