# QuantLeap — Strategic Validation & Execution Report

**Prepared:** July 8, 2026 · **Stage:** Live, zero paying users · **Founder:** Solo, ~20 hrs/week · **Decision sought:** Continue or pivot

---

## Inputs & Assumptions

Derived from the codebase (README, FEATURES_CHECKLIST.md, MONETIZATION_STRATEGY_2026.md, ROADMAP.md) and your answers:

- **Product:** QuantLeap (quantleap.in) — FastAPI + React portfolio tracker for Indian retail investors. Live features: multi-portfolio tracking, Zerodha + 5Paisa OAuth sync, real-time P&L, RSI/MACD signals, STCG/LTCG tax reports (FIFO/LIFO, FY filtering, ₹1.25L exemption logic), CSV exports, Google OAuth, Razorpay billing plumbing.
- **Adjacent asset:** Nifty Options Analyzer (spec + JSX prototype, Anthropic AI proxy wired) and a separate algotrader project.
- **Traction:** Deployed (Render/Vercel/cPanel), free signups only, ₹0 revenue as of July 2026.
- **Direction requested:** Both products under one QuantLeap brand.

**Assumptions (labeled):**
- A1: Budget ≈ ₹10–25k/month; no plans to raise institutional funding in the next 6 months.
- A2: You keep your full-time job; 20 hrs/week is sustained, not aspirational.
- A3: Current free user count is small (< 200 registered, < 30 weekly active). If materially higher, the verdict improves one notch.
- A4: You have no existing audience (newsletter, YouTube, Twitter following) to launch into.

---

## 1. Executive Summary

**What it is:** A privacy-first, multi-broker portfolio tracker with India-specific capital gains tax reporting, plus an in-development options analytics product, aimed at Indian retail investors and active traders.

**Verdict: Partially aligned but needs refinement.**

The market is real and large — [13.1 crore unique NSE investors as of May 2026](https://acumengroup.in/how-many-people-invest-in-the-stock-market-in-india/) — but the product as positioned ("portfolio tracker") is a commodity that INDmoney, ET Money, and Zerodha Console give away free, with VC money and distribution you cannot match. Nobody in India pays for *tracking*.

However, buried inside QuantLeap is a feature Indians demonstrably **do** pay for: **capital gains tax computation**. Quicko, Cleartax, and CA services charge ₹1,000–5,000/year for exactly what your tax_reports engine does — and the multi-broker, FIFO-lot, ITR-ready version of it is genuinely underserved for DIY filers with 2+ brokers.

- **Biggest opportunity:** Reposition from "portfolio tracker" (commodity) to "multi-broker capital gains & ITR-ready tax engine" (paid utility) — and it is July, peak ITR season, the single best validation window of the year.
- **Biggest risk:** Distribution, not product. A solo founder with 20 hrs/week and no audience loses a features war; the only winnable game is a sharp wedge + content/SEO in a niche the big free apps treat as an afterthought.
- **Recommended next step:** Run a 90-day tax-wedge validation with explicit kill criteria (Section 8 & 21) before writing any more product code. Do **not** split effort across the options analyzer now — SEBI's F&O crackdown ([₹1.05 lakh crore retail losses in FY25, contract sizes tripled, weekly expiries cut](https://www.moneylife.in/article/106-lakh-crore-lost-by-individual-traders-in-fo-in-fy2425-govt-confirms-sebi-action-on-4-entities-for-market-abuse/79124.html)) is shrinking that market's top of funnel while Sensibull owns what remains.

**Reasoning:** Strong technical execution + real market + wrong positioning + zero distribution = refine, don't abandon. The pivot required is a *positioning and focus* pivot, not a rebuild.

---

## 2. Problem Analysis

**The problem as currently framed** ("I can't see all my investments in one place") is real but weak: it's solved free by INDmoney/ET Money via MF Central + broker APIs, and single-broker users get it from their broker's own app. Frequency is high, pain is low, willingness to pay is near zero.

**The problem worth attacking** ("Every July I have to compute STCG/LTCG across Zerodha + 5Paisa + old holdings, reconcile FIFO lots across splits/bonuses, apply the ₹1.25L exemption and post-Budget-2024 rates, and produce something my ITR or my CA accepts — and broker P&L statements disagree with each other") is:

- **Real:** every filer with equity sales faces it annually; multi-broker users face it acutely.
- **Frequent:** annually intense (Apr–Sep), quarterly for advance-tax payers — low frequency but calendar-guaranteed.
- **Paid today:** Quicko (₹1,000–2,000/yr plans), Cleartax (₹1,500–6,000), CAs (₹2,000–10,000). Proven WTP.
- **Most intense for:** DIY filers with 2+ brokers, ESOP/US-stock holders, and anyone who switched brokers mid-year (broker statements lose cost-basis history).
- **Trigger:** ITR deadline (usually July 31 / mid-Sep with extensions), advance tax dates, capital-gains statement requests from CAs.
- **If they do nothing:** wrong tax paid, notices, or ₹2–10k to a CA. This is a must-have with a deadline — the best kind.

| Criteria | Score / 10 | Reason |
|---|---:|---|
| Pain intensity | 7 | Deadline-driven, money + compliance fear; but only seasonal peak |
| Frequency | 4 | Annual spike, quarterly for advance-tax users; tracking keeps them the rest of the year |
| Willingness to pay | 7 | Quicko/Cleartax/CA fees prove ₹1–5k/yr; near-zero for pure tracking |
| Market size | 7 | ~13 crore investors; realistically lakhs of multi-broker DIY filers |
| Competitive gap | 5 | Quicko is strong but broker-import-centric and filing-focused; multi-broker lot-level reconciliation is weak everywhere |
| Urgency | 8 | It is literally ITR season right now |

Pure tracking scores ~3 on WTP; the tax wedge is where the numbers work.

---

## 3. Target Customer Analysis

**Ideal customer profile:** Salaried Indian professional, 28–45, ₹15L+ income, 2+ demat accounts (typically Zerodha + one legacy/bank broker), files ITR-2 themselves or wants to stop paying a CA, active enough to have 20+ sell transactions a year.

**Do NOT target initially:** pure buy-and-hold single-broker investors (broker app suffices), F&O day traders (different product, shrinking segment), NRIs (non-resident tax you don't compute), HNIs with family offices (need audit-grade tooling).

### Persona 1 — "Two-Broker Tech Professional" (primary)
- **Rahul, 33, senior software engineer, Bengaluru.** Zerodha for trading, ICICI Direct from his first job, some US RSUs.
- **Pain:** Every July he exports three CSVs, fights Excel FIFO formulas, and still isn't sure his LTCG exemption math is right post-Budget-2024.
- **Current workaround:** Excel + Quicko's Zerodha import (which misses ICICI) or ₹3,000 to a CA.
- **Why QuantLeap:** one sync, one ITR-ready capital gains report across both brokers, FIFO/LIFO toggle.
- **What stops him:** trust (will you leak my holdings?), accuracy doubts, "is this maintained?"
- **Channel:** Reddit r/IndiaInvestments, Google search ("capital gains report multiple brokers"), Twitter finance circles.

### Persona 2 — "DIY Filer Upgrading from Excel" (secondary)
- **Priya, 41, doctor, Pune.** MFs + stocks via 5Paisa and Groww, files ITR-2 with her husband's help.
- **Pain:** doesn't trust herself on STCG vs LTCG classification; CA charges ₹4k and asks her for the same spreadsheets anyway.
- **Workaround:** CA + shoebox of contract notes.
- **Why QuantLeap:** a report she can hand to the CA (or file from) that's already classified and exemption-applied.
- **What stops her:** OAuth broker linking feels scary; needs CSV-upload path and plain-language explanations.
- **Channel:** YouTube ("how to file ITR-2 capital gains 2026"), WhatsApp forwards, Google.

### Persona 3 — "The CA with 40 retail clients" (buyer ≠ user; expansion persona)
- **Mehta & Associates, 2-partner firm.** Each July they manually consolidate clients' broker statements.
- **Why QuantLeap Teams:** client-portfolio workspace + white-label capital gains reports = hours saved per client at ₹999/mo.
- **What stops them:** needs audit trail, bulk import, and reliability guarantees a solo project struggles to signal.
- **Channel:** CA communities, LinkedIn, Taxguru/CAclubindia forums. **Park until product is validated with retail.**

**Early adopter segment:** Persona 1 — technical, multi-broker, deadline-pressured *right now*, reachable on Reddit/Twitter, tolerant of rough edges if the math is right.

---

## 4. Market Research

- **Market size:** [~13.1 crore unique NSE investors (May 2026)](https://acumengroup.in/how-many-people-invest-in-the-stock-market-in-india/); [~22.9 crore demat accounts](https://www.nseindia.com/registered-client-accounts). *Estimate:* if even 3–5% are multi-broker DIY filers with taxable equity sales, the serviceable segment is 40–65 lakh people; capturing 0.05% at ₹999/yr ≈ ₹20–32L ARR — a good solo business, not a VC story.
- **Growth:** cooling — [demat additions fell ~22% in FY26](https://www.angelone.in/news/market-updates/demat-account-openings-drop-22-in-fy26-as-market-volatility-rises) amid volatility. Tax complexity, however, grew (Budget 2024 rate changes, exemption changes) — good for the wedge.
- **Trends & tailwinds:** DIY ITR filing rising; account aggregator / MF Central rails normalizing data-linking; post-Budget-2024 rules confuse even CAs; brokers' own tax P&L statements are notoriously inconsistent → reconciliation demand.
- **Headwinds/risks:** [SEBI's F&O clampdown](https://www.nism.ac.in/blog/equity-linked-exchange-traded-derivative-contracts-the-retail-rush-and-regulatory-measures/) shrinks the active-trader segment (bad for options analyzer); a market downturn reduces both trading and capital gains to report; big free apps could bundle better tax reports anytime.
- **Regulatory:** storing broker credentials/tokens → you already encrypt (good); if you ever *file* returns you enter ERI-registration territory — stay "report generator," let users file via the IT portal or partner with an ERI. SEBI's [algo-trading framework (fully mandatory April 2026)](https://www.sahi.com/blogs/sebi-algo-trading-rules-2026-what-every-retail-trader-must-know-before-april) makes the algotrader product legally heavier — another reason to defer it.
- **Funding activity:** INDmoney, Dezerv, Jar etc. raised large rounds for wealth super-apps; tax-tech (Quicko, Cleartax) is established — validation that both adjacent spaces monetize.
- **Market type:** **Fragmented niche with expansion potential.** Tracking is winner-takes-most (free, distribution game — avoid); tax tooling is fragmented with room for a sharp specialist.

**Manual research still needed (search queries to run):** "capital gains statement multiple brokers site:reddit.com", "Quicko vs Cleartax capital gains 2026", Google Keyword Planner volumes for "capital gains calculator India", "ITR-2 capital gains", App Store reviews of INDmoney mentioning "tax".

---

## 5. Competitive Analysis

| Competitor | What they do | Target users | Pricing | Strengths | Weaknesses | Opportunity for us |
|---|---|---|---|---|---|---|
| INDmoney | Net-worth super-app (stocks, MF, US, EPF) | Mass retail | Free + premium | Design, funding, US stocks | Tax reports shallow; pushes cross-sell; privacy skepticism | Depth on tax, no cross-sell agenda |
| Zerodha Console | Broker's own reports & tax P&L | Zerodha users | Free | Authoritative for Zerodha data | Single-broker only; FIFO quirks; no consolidation | Multi-broker consolidation |
| Quicko | Tax filing + broker imports | DIY filers, traders | Free tier; ~₹1–2k/yr paid | ERI filing, broker tie-ins, trusted | Filing-centric; year-round portfolio view weak; multi-broker lot reconciliation patchy | Live year-round tracker that *becomes* the tax report |
| Cleartax | Tax filing suite | Mass filers | ₹1.5–6k/yr | Brand, SEO monster | Generic; capital-gains UX clunky; expensive assisted plans | Cheaper, investor-native, reconciled data |
| ET Money / Kuvera | MF-first tracking & investing | MF investors | Free | MF depth, brand | Equity + multi-broker tax weak | Equity capital-gains depth |
| Sensibull | [Options analytics](https://sensibull.com/) | Active F&O traders | [₹800–1,600/mo](https://www.strike.money/reviews/sensibull) | Market leader, Zerodha distribution | Expensive; F&O market shrinking | Only if you later enter options — don't now |
| Excel + CA | Manual consolidation | Everyone | ₹0–10k | Trusted, flexible | Hours of work, error-prone | The real competitor; beat it on time-to-report |

- **What users complain about (observed in forums):** broker tax P&Ls disagreeing with each other, Quicko imports missing/duplicating trades, Console FIFO confusion after splits/bonuses, CAs re-asking for data.
- **Room for another player?** In free tracking, no. In multi-broker tax reconciliation, yes — it's an annoying, India-specific, correctness-critical niche the funded players under-serve because it doesn't cross-sell products.
- **Possible unfair advantages:** correctness obsession (lot-level FIFO from transactions — already on your roadmap as item A), privacy-first stance (no product cross-sell, tokens encrypted), and founder-as-user authenticity. None are moats yet; a corpus of verified corporate-action-adjusted lot histories could become one.

---

## 6. Differentiation Strategy

**UVP:** "Your capital gains, correct across every broker — ITR-ready in 5 minutes, not a weekend of Excel."

**Positioning statement:** For Indian DIY investors with multiple brokers, QuantLeap is the tax-first portfolio tracker that computes lot-accurate STCG/LTCG across all accounts and produces ITR-ready reports — unlike super-apps that track everything shallowly and filing sites that see your portfolio one day a year.

**Wedge:** multi-broker capital gains reconciliation. **Compete on:** accuracy + niche specialization + privacy. **Not on:** price (race to free), breadth (INDmoney wins), or design alone.

- **Avoid (generic, no defensibility):** generic RSI/MACD signals, watchlists, news feeds, "AI insights" without a specific job, leaderboards/community.
- **Defensibility candidates:** corporate-action-adjusted lot engine, broker-statement reconciliation test corpus, published accuracy guarantees ("we match or explain every ₹ of difference vs your broker statement"), CA-workflow features later.

**Three positioning options:**
1. **Conservative — "Portfolio tracker with great tax reports."** Pros: no rework, keeps current site. Cons: commodity framing, converts like a commodity (i.e., doesn't). *Reject.*
2. **Aggressive — "Fire your CA: file capital gains yourself."** Pros: sharp, emotional, high CPC keywords. Cons: overpromise (you don't file), invites accuracy liability, antagonizes the CA channel you may want later. *Reject.*
3. **Niche — "The capital gains engine for multi-broker investors."** Pros: exactly matches the underserved pain, searchable, credible for a solo product, expands naturally to full tracker usage year-round. Cons: seasonal demand curve, smaller top-of-funnel. **← Recommended.**

---

## 7. Product Strategy

**Core concept:** connect brokers (or upload CSVs) → transactions become the source of truth → lot engine computes holdings, P&L, and capital gains → one dashboard year-round, one ITR-ready report at tax time.

**Main user flow:** Sign in with Google → connect Zerodha (or upload tradebook CSV) → see reconciled holdings → open Tax Report FY2025-26 → verify against broker statement → pay → download ITR-ready CSV/PDF.

**Aha moment:** the first time a user sees *both* brokers' trades merged into one correct capital-gains statement that matches (or explains deltas vs) their broker P&L — within 5 minutes of signup.

| Priority | Feature | Why it matters | Build now or later |
|---|---|---|---|
| P0 | Transaction-sourced FIFO lot engine (your roadmap item A) | Wrong numbers kill a tax product permanently | Now |
| P0 | Corporate actions (splits/bonus) auto-adjust | #1 source of wrong cost basis | Now |
| P0 | Tradebook CSV upload (Zerodha/Groww/ICICI/HDFC formats) | Covers brokers without OAuth; removes trust barrier | Now |
| P0 | ITR-ready export (Schedule 112A-compatible CSV + PDF) | The thing people pay for | Now |
| P0 | Razorpay one-time "Tax Report ₹499/FY" purchase flow | Fastest WTP validation | Now |
| P1 | Reconciliation view ("we differ from Console by ₹X because…") | Trust builder, unique | Next |
| P1 | Advance-tax quarterly gains estimate | Extends value beyond July | Next |
| P1 | Dividend capture + Schedule OS summary | Adjacent, same buyer | Next |
| P2 | MF capital gains (CAMS/KFintech CAS upload) | Doubles TAM, heavy parsing work | Later |
| P2 | Scheduled auto-sync, price history, TWR/XIRR | Year-round retention | Later |
| P3 | Teams/CA workspace, white-label reports | Expansion revenue | Much later |
| P3 | Options analyzer under same login | Only after tax wedge validates | Parked |

- **Integrations:** Zerodha (have), 5Paisa (have), CSV importers (build), CAMS CAS (later). **Admin:** user list, sync-run logs, payment reconciliation, feature flags. **Analytics:** PostHog or Plausible + backend events (Section 18). **Security:** you have Fernet-encrypted tokens; add rate limiting on auth (your roadmap item C) and an explicit data-deletion endpoint — privacy is part of the pitch.
- **Onboarding:** demo portfolio pre-loaded so the dashboard is never empty; "upload CSV" offered as prominently as OAuth. **Retention mechanics:** quarterly advance-tax emails, FY-end "your estimated tax so far" digest, price alerts later.

---

## 8. MVP Recommendation

You've already built past MVP on breadth; the gap is depth + monetization. This is a **re-scoped MVP**, mostly repackaging.

- **Goal:** ≥ 25 strangers pay for a tax report by Sep 30, 2026 (extended ITR deadline window).
- **Audience:** Persona 1 (multi-broker tech professionals), India, English.
- **MVP features:** the six P0 items above + repositioned landing page. Nothing else.
- **Exclusions:** options analyzer, mutual funds, mobile app, Teams, alerts, community, order execution (delete from roadmap — regulatory weight, zero wedge value).
- **Success criteria (kill/continue gates):** 25+ paid reports **or** 500+ tax-page signups with >5% purchase intent → continue. < 10 paid despite 2,000+ landing visitors → the wedge failed; see Section 20 pivot plan.
- **Timeline:** 8 weeks build+launch inside ITR season (Sprint plan, Section 15). **Budget:** ₹15–40k total (domain/hosting you have; ₹10–25k ads; ₹5k tools).
- **Manual-first (concierge):** before automating every broker format, offer "email us your tradebook CSVs, get your report in 24h, ₹499" — you personally run them through the engine. Validates WTP with zero new parsing code and surfaces real-world data edge cases.
- **Demand test before more code:** the landing page + concierge offer can start **this week**.

---

## 9. Validation Plan

| Test | Goal | How to run it | Success metric | Timeline |
|---|---|---|---|---|
| Landing page repositioning | Does "multi-broker capital gains" convert? | New hero + ₹499 CTA on quantleap.in, Plausible funnel | >3% visitor→signup | Week 1 |
| Concierge tax report | WTP + data edge cases | Manual offer on Reddit/Twitter/IndiaInvestments, cap 20 users | 10 paid @ ₹499 | Weeks 1–3 |
| User interviews | Understand workflow & trust barriers | 8–10 calls with multi-broker filers (recruit from signups + LinkedIn) | 6+ confirm >2h/season pain & name a price | Weeks 1–4 |
| Google Ads probe | Search demand & CPC | ₹8–10k on "capital gains report/calculator" keywords → landing | CPA < ₹300/signup | Weeks 2–4 |
| Reddit/community test | Organic resonance | Genuine "I built this, roast it" posts in r/IndiaInvestments, r/personalfinanceindia | 50+ upvotes / 20+ signups per post | Weeks 2–6 |
| Cold outreach | Persona-1 direct validation | 50 DMs to people complaining about broker tax statements on Twitter/Reddit | 20% reply, 5 users | Weeks 2–5 |
| Pricing test | ₹499 one-time vs ₹999/yr sub | A/B on checkout page | Revenue/visitor winner | Weeks 4–8 |
| Prototype usability | Can Priya (Persona 2) finish alone? | 5 moderated sessions, CSV-upload path | 4/5 complete without help | Weeks 5–6 |

**10 interview questions:** 1) Walk me through last year's ITR capital gains — every step. 2) How many brokers/demats? Why multiple? 3) How long did it take? What broke? 4) What did you pay (CA/tool)? 5) Did your broker statements agree with each other? 6) What would you *not* trust software to do here? 7) Would you link broker login or prefer CSV upload — why? 8) What did you do about splits/bonuses? 9) If this existed, what's a fair price? At ₹499? At ₹1,999? 10) Who else do you know with this problem? (referral seed)

**10 landing headlines:** 1) Capital gains across all your brokers. Correct. In 5 minutes. 2) Stop reconciling tradebooks in Excel every July. 3) Zerodha + anything else? Your tax report just got easy. 4) The ITR-ready capital gains report your brokers can't give you. 5) Your CA charges ₹3,000 for this. 6) FIFO lots, splits, bonuses, ₹1.25L exemption — handled. 7) One tax report for every demat you own. 8) Multi-broker investors: tax season, minus the weekend. 9) We match your broker's P&L — or explain every rupee of difference. 10) Track all year. File in minutes.

**5 value-prop variants:** accuracy-first ("lot-level correct, reconciled vs broker"); time-first ("weekend of Excel → 5 minutes"); money-first ("₹499 vs ₹3,000 CA"); trust-first ("read-only, encrypted, no product cross-sell ever"); completeness-first ("every broker, every split, every FY in one place").

**5 pricing tests:** ₹499 one-time/FY · ₹999/yr sub incl. year-round tracking · ₹299 early-bird season pass · ₹1,499/yr incl. advance-tax quarterly reports · Free report for 1 broker, ₹499 to unlock multi-broker (recommended first test: the last one — it monetizes exactly the differentiator).

---

## 10. Business Model

**Recommended:** seasonal one-time purchase (₹499/FY tax report) to validate → convert to **freemium annual subscription** once retention features exist. Annual (not monthly) matches the seasonal usage; monthly ₹199 (your Feb plan) will churn 10 months a year.

| Plan | Target user | Price | Features | Limitations |
|---|---|---:|---|---|
| Free | New/single-broker users | ₹0 | Tracking, 1 broker sync, dashboard, 1-broker tax preview | No multi-broker tax report, no exports |
| Tax Report | Seasonal filers | ₹499/FY | Full multi-broker ITR-ready report, one FY | No year-round features |
| Pro | Multi-broker DIY investors | ₹999/yr | Everything + all FYs, advance-tax estimates, dividends, alerts | Single user |
| Teams (later) | CAs/advisors | ₹999/mo | Client workspaces, white-label reports | Post-validation only |

- **Alternatives considered:** affiliate broker referrals (conflicts with privacy positioning — only accept transparent ones like Angel One "open account" links, clearly labeled); ads (kills trust, wrong scale); marketplace (no); API licensing to CAs/fintechs (real long-term option).
- **Unit economics (estimates):** CAC ₹150–400 via search/content; LTV ₹999–2,500 (1–2.5 renewal years); gross margin > 85% (hosting is trivial; watch market-data API costs). **Break-even on cash costs (~₹20k/mo):** ~250 Pro subscribers — plausible within 12 months if validation passes.

---

## 11. Go-To-Market Strategy

**Channels that fit a solo, 20 hr/wk founder:** SEO/content (compounding, deadline keywords), Reddit/community (Persona 1 lives there), Google Search ads in season (high intent), Twitter/X finance niche. **Avoid initially:** Instagram/YouTube production (time sink), paid social (low intent), influencer deals (expensive, unmeasurable at your scale), PR.

1. **Pre-launch (now–Week 2):** reposition landing page; set up analytics funnel; start concierge offers in communities; write 2 cornerstone SEO articles ("Capital gains tax on shares FY2025-26 explained", "How to consolidate Zerodha + ICICI tradebooks").
2. **Launch (Weeks 3–6, peak ITR):** ship ₹499 report flow; Reddit launch posts; Google Ads on filing keywords; daily Twitter build-in-public thread; Product Hunt is *optional* (audience is US-heavy — an IndieHackers/India-specific launch matters more).
3. **Post-launch (Weeks 7–12):** interviews → iterate; publish "we reconciled 1,000 tradebooks: the 7 ways broker statements lie to you" (data-driven link magnet); referral: give a free FY report for each referred payer.
4. **Scale (Month 4+ if validated):** SEO to 20+ articles targeting every "capital gains + <broker/situation>" query; CA partnerships; CAMS/MF support to widen TAM; consider Sensibull-style broker marketplace listings.

**Product-led growth:** the exported PDF report footer ("Generated by QuantLeap") lands on CAs' desks — make it beautiful; that's your viral surface.

---

## 12. Promotion Plan

**Platforms:** Reddit (r/IndiaInvestments, r/personalfinanceindia, r/IndiaTax), Twitter/X fintwit, LinkedIn (Persona 2 + CAs), Google Search, one long-form blog on quantleap.in. **Frequency:** 3 tweets/wk, 1 blog post/wk in season, 1 Reddit value-post/2wks (never spam — answer tax questions genuinely, mention tool when relevant).

**20 content ideas:** STCG/LTCG rates FY25-26 cheat sheet · ₹1.25L exemption explained with examples · FIFO vs LIFO impact calculator post · Why Console and Quicko show different P&L · Splits/bonuses and your cost basis · ITR-2 Schedule 112A walkthrough · Multi-broker consolidation guide · Advance tax on capital gains dates · Tax-loss harvesting before Mar 31 · Switched brokers? Here's what happens to cost basis · Groww tradebook export guide · ICICI Direct export guide · "I analyzed 100 tradebooks" data post · Dividend taxation (Schedule OS) · US RSU + Indian broker combined guide · Common ITR capital-gains mistakes → notices · CA vs DIY cost comparison · Build-in-public: how our lot engine works · Why we'll never sell you insurance · FY26 tax calendar for investors.

**10 social post examples (compressed):** 1) "Your broker's tax P&L is wrong more often than you think. Thread on the 5 ways 🧵" 2) Poll: "How many demat accounts do you have?" 3) Before/after screenshot: Excel hell → one report. 4) "Budget 2024 changed LTCG. Half the spreadsheets on Reddit still use old rates." 5) Build-in-public: "Day 12: our FIFO engine now survives a 1:5 split + bonus in the same month." 6) "Paid your CA ₹3k to copy-paste your tradebook? Same." 7) Quarterly advance-tax reminder with calculator link. 8) "We reconciled Zerodha vs our engine on 50 accounts: ₹0.00 unexplained. Receipts:" 9) User quote screenshot + "this is why we build." 10) "July 31 is X days away. Your multi-broker capital gains report takes 5 minutes."

**5 cold outreach templates (one-liners; personalize the first line from their post):** 1) To a Redditor complaining about Console: "Saw your post on Console's FIFO — I built a tool that reconciles it lot-by-lot; want a free report in exchange for feedback?" 2) To a tweeter with 2+ brokers: same, Twitter-length. 3) To a CA: "I generate ITR-ready consolidated capital-gains reports your clients can hand you — want 3 free client credits?" 4) To a finance blogger: "Data post offer: anonymized stats from 500 tradebooks — exclusive if you want it." 5) To Quicko-frustrated user: "What broke in your import? Ours handles X — free run to compare."

**5 landing copy examples:** hero variants from the 10 headlines above, each paired with a subhead naming brokers ("Zerodha, 5Paisa, ICICI, Groww — one report") and a single CTA ("Get my FY25-26 report — ₹499").

**5 launch announcements:** Reddit long-form origin story ("I had 3 demats and a lost weekend…") · Twitter thread with demo GIF · LinkedIn post targeting salaried filers · IndieHackers post with revenue-transparency promise · Email to existing free signups ("the feature you actually wanted is here — founding-user price ₹299").

---

## 13. Technical Architecture

Your stack is already right for this stage. Recommendation: **change almost nothing; harden what exists.**

| Stack | Best for | Pros | Cons | Recommended? |
|---|---|---|---|---|
| Current: FastAPI + React/Vite + Postgres (Supabase) + Razorpay + Render/Vercel | You, now | Built, typed, tested, deployed; zero migration cost | Render cold starts; background jobs missing | ✅ Yes |
| Next.js full-stack + Vercel + Neon | JS-first teams | One deploy, edge | Full rewrite for zero user value | ❌ |
| Django + HTMX monolith | Solo simplicity | Admin for free | Rewrite; you lose the SPA already built | ❌ |

**Keep:** FastAPI, SQLAlchemy, Postgres, React+TS+Tailwind, Razorpay, Google OAuth, Fernet token encryption.
**Add (only these):** APScheduler for daily sync + sync-run persistence (your roadmap D — skip Celery/Redis until >1k users); rate limiting (slowapi) on auth; Sentry free tier; Plausible/PostHog; transactional email via your SMTP → move password-reset tokens out of logs (roadmap C); pick **one** production DB — the repo shows Postgres, MariaDB migration, SQLite artifacts; consolidate on Postgres and delete the rest.

- **Core entities:** users, broker_configs (encrypted), portfolios, transactions (source of truth), **lots** (new: buy-lot decomposition), corporate_actions, tax_reports (persisted, versioned), payments, sync_runs.
- **API structure:** existing routers + `/api/lots`, `/api/tax-reports/{fy}/purchase`, `/api/imports/csv`. Webhook: `/api/billing/razorpay-webhook` (verify signature — you have the secret env var).
- **Security/privacy:** data-deletion endpoint + privacy page (it's a selling point); never store broker passwords (you don't); annual key-rotation runbook for `ENCRYPTION_KEY`.
- **Scalability:** a few thousand users on one Render instance + Supabase is fine; the only hot path is tax computation — precompute lots on sync, not on report view.

---

## 14. Build vs Buy vs No-Code Analysis

| Approach | Cost | Speed | Flexibility | Scalability | Best use case |
|---|---:|---|---|---|---|
| Custom code (current) | Sunk + time | Slow to add | Total | High | The lot/tax engine — your differentiator |
| Existing APIs | Low–mid | Fast | Medium | High | Prices (yfinance/NSE), email, payments — already doing this |
| No-code | Low | Fastest | Low | Low | Landing page A/Bs only (Framer/Carrd probe pages) |
| White-label | Mid | Fast | Low | Med | None — tax engine IS the product |
| Manual ops first | ~₹0 | Immediate | Total | None | **Concierge tax reports — do this first** |

**Recommendation:** manual-first for validation (concierge), custom code only for the lot engine and importers, APIs for everything commodity. You are past the no-code decision point; don't rebuild anything.

---

## 15. Sprint-Based Execution Plan

2-week sprints, sized for ~40 hrs/sprint (20 hrs/wk solo). Sprints 1–4 land inside ITR season — sequencing is deliberate: validation before deep engineering.

### Sprint 0 (this week, compressed): Reposition & instrument
**Goal:** tax-wedge landing live + concierge offer out. **Product specs:** new hero/CTA, ₹499 concierge checkout (Razorpay payment link is fine). **Technical:** Plausible + funnel events; Sentry. **Marketing:** 2 Reddit value-posts; interview recruiting. **Validation:** first 5 concierge orders attempted. **Acceptance:** landing live, funnel measurable, ≥1 paid concierge. **Risks:** communities reject promotion → lead with free tax answers. 

### Sprint 1: Lot engine foundation
**Goal:** transactions → FIFO lots, correct through splits/bonuses. **Specs:** lots table, corporate-action ingestion (manual admin entry acceptable), invalid-sell prevention. **Technical:** lot decomposition module + pytest suite seeded with real concierge tradebooks; property-based tests (hypothesis) on lot math. **Marketing:** build-in-public thread; cornerstone article #1. **Validation:** 4 user interviews. **Acceptance:** engine matches hand-computed gains on 10 real tradebooks to the rupee. **Risks:** corporate-action data messiness → start with manual entry, automate later. **Dependencies:** concierge data from Sprint 0.

### Sprint 2: CSV importers + report generation
**Goal:** self-serve path without OAuth. **Specs:** Zerodha/Groww/ICICI tradebook parsers with format detection; ITR-ready CSV (112A columns) + branded PDF. **Technical:** parser framework + golden-file tests; report persistence. **Marketing:** broker-specific export guides (SEO). **Validation:** 5 usability sessions on upload flow. **Acceptance:** stranger uploads CSV → correct report, unaided, <10 min. **Risks:** format drift → version parsers, log unknown headers.

### Sprint 3: Paid flow + reconciliation view
**Goal:** money self-serve. **Specs:** free 1-broker preview → ₹499 unlock multi-broker (pricing test A); reconciliation panel vs broker-reported P&L. **Technical:** Razorpay order flow + webhook verification + entitlements; feature flags. **Marketing:** Google Ads on (₹8–10k); Reddit launch post. **Validation:** pricing A/B live. **Acceptance:** end-to-end stranger payment with zero founder touch. **Risks:** checkout drop-off → keep guest-friendly, minimal fields.

### Sprint 4: Season push + hardening
**Goal:** maximize paid reports before deadline. **Specs:** advance-tax estimate teaser; email digest to free users. **Technical:** rate limiting, sync-run logging, data-deletion endpoint. **Marketing:** deadline-countdown content daily; referral credit. **Validation:** interview payers ("what almost stopped you?"). **Acceptance:** ≥25 cumulative paid OR clear kill signal documented. **Risks:** deadline extension shifts urgency → advance-tax angle keeps relevance.

### Sprint 5: Decision gate + retention seed
**Goal:** continue/pivot decision per Section 21 criteria; if continue: annual Pro plan, auto-sync scheduling. 

### Sprint 6: Public "v1" launch
**Goal:** Pro ₹999/yr live; IndieHackers/Twitter launch; 10 SEO articles cumulative.

### Sprint 7+: Growth
**Goal:** MF capital gains (CAS upload), CA outreach pilot, dividend tracking — sequence by what payers ask for.

---

## 16. Product Requirements Document (MVP)

- **Overview:** QuantLeap Tax — multi-broker capital gains computation and ITR-ready reporting for Indian resident individual investors, layered on the existing tracker.
- **Goals:** correct lot-level STCG/LTCG across ≥2 data sources; report in <10 min from first visit; ≥25 paid reports by Sep 30.
- **Non-goals:** tax *filing* (no ERI), F&O/intraday business-income computation, NRI taxation, MFs (v1), mobile app, advisory of any kind (display disclaimers).
- **Personas:** Rahul (primary), Priya (secondary) — Section 3.
- **Key user stories:** As a multi-broker investor I can upload tradebook CSVs from different brokers so all trades merge into one timeline · I can see holdings computed from transactions with FIFO lots so my average cost is right after splits · I can generate an FY capital-gains report with STCG/LTCG classification and the ₹1.25L exemption applied · I can compare QuantLeap's numbers against my broker statement and see explained differences · I can pay ₹499 to unlock the full multi-broker report and download CSV+PDF · I can delete my account and all data.
- **Functional requirements:** parser per supported broker with row-level error reporting; dedupe on (broker, trade_id) and fuzzy match on (symbol, date, qty, price); lot engine (FIFO default, LIFO toggle); FY boundary Apr 1–Mar 31; post-23-Jul-2024 rate logic (STCG 20%, LTCG 12.5%, ₹1.25L exemption); grandfathering for pre-2018 buys (31-Jan-2018 FMV) — flag if FMV data unavailable rather than silently computing.
- **Non-functional:** report generation < 5s for 5,000 transactions; all money as Decimal (never float); audit log of report versions; 99% uptime in July–Sep; WCAG-AA on report pages.
- **Edge cases:** sell qty > holdings (block + explain); same-day buy/sell ordering; symbol changes (e.g., mergers); missing buy history ("orphan sells" → prompt user for acquisition cost/date); duplicate uploads; zero-price corporate-action entries; multiple demats at the *same* broker.
- **Admin:** user/payment/sync dashboards; parser-failure queue; manual corporate-action entry.
- **Analytics events:** signup, broker_connected, csv_uploaded, csv_parse_failed, report_previewed, paywall_viewed, payment_started/completed, report_downloaded, delta_explained_viewed.
- **Security:** existing JWT + OAuth; rate limits on auth and upload; encrypted tokens; deletion endpoint; no PII in logs.
- **Launch requirements:** pricing page, privacy policy + data-handling page, tax-disclaimer page ("not tax advice"), refund policy (7-day, no-questions — cheap trust).

---

## 17. Technical Specs (MVP delta)

**Architecture:** existing FastAPI monolith + React SPA; add `tax/` domain module (lot engine), `importers/` (parser framework), APScheduler in-process for nightly sync.

**Schema (new/changed):**
```sql
lots(id, user_id, portfolio_id, symbol, buy_txn_id, buy_date, qty, qty_remaining,
     cost_per_unit NUMERIC(18,4), adjusted_for_actions BOOL, created_at)
corporate_actions(id, symbol, type ENUM(split,bonus,merger,symbol_change),
     ratio_num, ratio_den, ex_date, source, verified BOOL)
tax_reports(id, user_id, fy, method ENUM(fifo,lifo), status, totals JSONB,
     version, paid BOOL, generated_at)
payments(id, user_id, razorpay_order_id, amount, currency, status, entitlement, created_at)
import_batches(id, user_id, broker, filename, rows_ok, rows_failed, errors JSONB, created_at)
```

**Endpoints (delta):** `POST /api/imports/csv` (multipart, returns batch summary) · `GET /api/tax-reports/{fy}?method=fifo` (preview: free = 1 broker, paid = all) · `POST /api/tax-reports/{fy}/purchase` → Razorpay order · `POST /api/billing/webhook` (signature-verified) · `GET /api/tax-reports/{fy}/export?format=csv|pdf` · `DELETE /api/account`.

**Flows:** Payment — create order server-side → Razorpay Checkout JS → webhook marks entitlement → client polls entitlement (never trust client success callback). Email — SMTP for receipts + report-ready; log-and-continue on failure. Auth — unchanged.

**Frontend pages:** repositioned landing, `/app/import`, `/app/tax-reports/{fy}` (preview + paywall + reconciliation panel), checkout modal, settings→delete account.

**Error states:** parse failures shown per-row with downloadable error CSV; orphan-sell wizard; payment-pending state with retry; report "stale — re-generate" flag when new transactions arrive.

**Testing:** pytest golden files per broker format; hypothesis property tests on lot math (sum of lots == holdings; gains invariant under transaction re-ordering within same timestamp rules); Vitest on paywall/preview logic; one Playwright happy-path (upload→pay→download) in CI. **Deployment:** existing Render/Vercel; add migration step (alembic via `uv run`); Sentry release tagging. **Monitoring:** Sentry + UptimeRobot on `/health` + daily job summary email to you.

---

## 18. Metrics and KPIs

**North Star:** paid tax reports generated (cleanly ties value + revenue).

| Metric | Target (by Sep 30) | Why it matters | Tool |
|---|---:|---|---|
| Landing → signup | > 3% | Positioning resonance | Plausible |
| Signup → report preview | > 50% | Onboarding/import works | PostHog |
| Preview → paid | > 8% | WTP proof (core gate) | PostHog + Razorpay |
| Paid reports | ≥ 25 | The continue/pivot gate | Razorpay |
| CSV parse success rate | > 90% | Product quality | Backend events |
| Reconciliation delta explained | 100% of paid reports | Trust promise kept | Manual QA sample |
| Refund rate | < 8% | Accuracy/expectation match | Razorpay |
| CAC (paid channel) | < ₹400 | Channel viability | Ads + Plausible |
| Support tickets/paid user | < 0.5 | Solo-founder sustainability | Email |

**Checkpoints:** Week 1 — repositioned page live, ≥1 concierge sale. Month 1 — 10 paid (concierge + self-serve), 6 interviews done, parse success >80%. Month 3 — 25+ paid, one channel with CAC <₹400, decision made. Month 6 (if continue) — 100 Pro/annual payers, 5k monthly organic visits, MF support shipped.

---

## 19. Risk Analysis

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Nobody pays even for tax wedge | Medium | Fatal | Concierge-first validation before more code; kill criteria pre-committed |
| Wrong tax numbers → trust collapse / user harm | Medium | Severe | Golden-file + property tests on real tradebooks; reconciliation transparency; disclaimers; refunds |
| Seasonality: revenue 3 months/yr | High | Medium | Advance-tax quarterly features; annual pricing; MF gains extend season |
| INDmoney/Quicko ship better multi-broker reports | Medium | High | Speed + niche depth; corpus of edge cases; year-round tracker lock-in |
| Solo-founder burnout / life events | Medium | High | Ruthless scope (P0 only); automation of support; kill criteria prevent zombie mode |
| Broker API/ToS changes (Zerodha Kite fees, OAuth churn) | Medium | Medium | CSV upload as first-class fallback — never OAuth-only |
| Regulatory: advice/filing boundary | Low | Medium | Stay a computation tool; disclaimers; no ERI filing v1 |
| Market downturn → fewer gains to report | Medium | Medium | Losses need reporting too (carry-forward!) — market that angle |
| Options-analyzer distraction | High | Medium | Explicit parking decision (Section 20); revisit only post-gate |

**Signals the idea is not working:** 2,000+ targeted visitors with <1% purchase; interviewees consistently say "I'll just use Quicko/my CA"; parse-support burden > 1 hr/user; paid users don't return next quarter for advance tax; refunds > 15%.

---

## 20. Feedback and Recommendations

**Direct assessment:** you have built a good product in a bad position. The engineering (typed FastAPI, encrypted tokens, real tax logic, honest roadmap self-critique in ROADMAP.md) is well above typical solo-founder quality. But eight months of building produced zero revenue because "portfolio tracker" is a free commodity in India, and building continued instead of selling. The Feb monetization doc diagnosed this ("80% ready, revenue in 8–12 weeks") — it's July and the gap was product breadth, not billing: nothing users *must* pay for was gated behind something they *can't get free elsewhere*.

**Build first:** lot engine correctness + CSV import + paid multi-broker report (Sprints 0–3). **Improve:** landing positioning; onboarding to first-report time. **Remove/park:** options analyzer (SEBI headwinds + Sensibull + focus), order execution (regulatory weight, zero wedge value), community/leaderboard roadmap items, the second `requirements*.txt` files and dual-DB paths (operational drag).

**On "both under one brand":** keep the brand umbrella, but *sequence* the products. QuantLeap-the-brand can house the options analyzer in 2027; QuantLeap-the-company gets one wedge at a time. A solo founder running two unvalidated products at 20 hrs/wk validates neither. The algotrader work additionally lands under [SEBI's algo framework, fully mandatory since April 2026](https://www.sahi.com/blogs/sebi-algo-trading-rules-2026-what-every-retail-trader-must-know-before-april) — the compliance cost alone disqualifies it as a side-project wedge.

**If the tax wedge fails the gate**, the recovery path in order of preference: 1) same engine, CA/advisor buyer (Teams — they have budgets and 40 clients each); 2) white-label capital-gains API to fintechs; 3) sunset gracefully, keep it as the best free multi-broker tracker + your strongest portfolio piece, and take the lot-engine expertise to the options analyzer only if you can commit full-time-level hours. Do not slow-drip nights-and-weekends on a product no one pays for — that is the actual failure mode to fear, not shutting down.

---

## 21. Final Recommendation

**Should you build this?** Mostly built. **Validate first?** Yes — that is the entire next 90 days. **Pivot?** Positioning pivot now (tracker → tax engine); product pivot only if the gate fails. **Niche down?** Yes: multi-broker DIY filers. **Change business model?** Yes: seasonal one-time → annual sub; drop monthly. **Change target customer?** Narrow to Persona 1; CAs later.

- **Next 7 days:** reposition landing page; launch ₹499 concierge offer on Reddit/Twitter; instrument funnel; book 4 interviews. Zero new product code except the payment link.
- **Next 30 days:** Sprints 0–1 (lot engine on real concierge tradebooks); 10 interviews; first Google Ads probe; 10 paid reports.
- **Next 90 days:** Sprints 2–4; hit the gate (≥25 paid) inside ITR season; make the continue/pivot call in writing against the pre-committed criteria — then either double down (Pro annual, MF gains, SEO engine) or execute the Section 20 recovery path.

| Category | Score / 10 |
|---|---:|
| Problem strength (tax wedge) | 7 |
| Market opportunity | 6 |
| Differentiation (current → potential) | 4 → 7 |
| Monetization potential | 6 |
| Technical feasibility | 9 |
| Go-to-market feasibility | 4 |
| Founder-market fit | 7 |
| **Overall** | **6.0** |

**Final word:** Your constraint was never engineering — it's that you've been competing in the free aisle of the store. Move to the paid aisle where Quicko and every CA in India already proved customers queue up each July, carrying the one asset the funded super-apps can't fake: lot-level correctness across brokers. You are sitting inside the best three-month demand window this product will see all year. Spend it selling ₹499 reports, not writing features — and let 25 strangers' payments, or their absence, make the continue-or-pivot decision for you with data instead of hope.

---

*Sources: [NSE registered client accounts](https://www.nseindia.com/registered-client-accounts) · [13.1 crore unique investors](https://acumengroup.in/how-many-people-invest-in-the-stock-market-in-india/) · [FY26 demat slowdown](https://www.angelone.in/news/market-updates/demat-account-openings-drop-22-in-fy26-as-market-volatility-rises) · [SEBI F&O measures & retail losses](https://www.nism.ac.in/blog/equity-linked-exchange-traded-derivative-contracts-the-retail-rush-and-regulatory-measures/) · [₹1.05L crore FY25 F&O losses](https://www.moneylife.in/article/106-lakh-crore-lost-by-individual-traders-in-fo-in-fy2425-govt-confirms-sebi-action-on-4-entities-for-market-abuse/79124.html) · [SEBI algo rules 2026](https://www.sahi.com/blogs/sebi-algo-trading-rules-2026-what-every-retail-trader-must-know-before-april) · [Sensibull pricing](https://www.strike.money/reviews/sensibull) · [India investment app comparison 2026](https://fundgenie.online/blog/best-investment-app-in-india-2026)*
