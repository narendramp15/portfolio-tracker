# QuantLeap Portfolio Tracker - Product Roadmap

## 🚀 Strategic Vision
Transform from a basic portfolio tracker into a comprehensive financial intelligence platform for Indian investors.

---

## ✅ Codebase-Informed Roadmap (Engineering Priorities)

These items are derived from reviewing the current FastAPI + React implementation. They focus on correctness, consistency, and production-readiness (the things that make users trust a financial product).

### A. Data correctness (highest priority)
- [ ] **Holdings computed from transactions (source of truth)**
  - Model FIFO lots so average cost, realized P&L, and remaining quantity are correct
  - Prevent invalid sells (sell quantity > available)
  - Treat the `assets` table as a cached snapshot (optional) vs primary truth

### B. API consistency & typing
- [ ] **Standardize API response models**
  - Add Pydantic response models for transactions list/detail (no ad-hoc dicts)
  - Avoid returning `[]` on server errors; return proper `HTTPException` and log
- [ ] **Unify auth dependency usage**
  - Ensure authenticated endpoints use the same token extraction logic (header + `?token=`)
  - Make `/api/auth/me` use the shared dependency approach

### C. Production security & reliability
- [ ] **Lock down CORS for production**
  - Never use `ALLOWED_ORIGINS="*"` with `allow_credentials=True` in production
- [ ] **Replace password reset token logging**
  - Send email via provider (Postmark/SendGrid) instead of printing tokens
- [ ] **Add rate limiting to auth endpoints**
  - Protect `/api/auth/login`, `/api/auth/register`, `/api/auth/forgot-password`

### D. Broker sync “productization”
- [ ] **Scheduled background sync**
  - Daily sync jobs with retries (Celery/Redis or APScheduler)
  - Persist sync runs (start/end, status, error, imported counts)
- [ ] **Reconciliation checks**
  - Detect mismatch between broker holdings and computed holdings; surface warnings

### E. Market data & performance history
- [ ] **Market price service**
  - Store daily price history (EOD) per symbol for charts and performance
- [ ] **Returns that match cashflows**
  - Implement TWR and XIRR correctly from transactions and portfolio value history

### F. Reporting & tax readiness
- [ ] **Capital gains reporting**
  - STCG/LTCG using transaction lots + holding period
  - Export CSV first, then PDF

---

## Phase 1: Core Enhancement (Weeks 1-4)

### 0. Trading Journal Feature ✅ NEW
- [x] **Trading Journal Database Table**
  - Columns: portfolio_id, trade_id, symbol, entry_price, exit_price, quantity, entry_date, exit_date, profit_loss, notes, created_at, updated_at
  - Migration: migrations/006_create_trading_journal_table.sql
- [x] **Trading Journal API Endpoints**
  - POST /api/journal/{portfolio_id} - Create trade entry
  - GET /api/journal/{portfolio_id} - List all entries
  - GET /api/journal/{portfolio_id}/stats - Get statistics
  - GET /api/journal/{portfolio_id}/{journal_id} - Get specific entry
  - PATCH /api/journal/{portfolio_id}/{journal_id} - Update entry
  - DELETE /api/journal/{portfolio_id}/{journal_id} - Delete entry
- [x] **Trading Journal Frontend**
  - TradingJournalPage - Main journal view with stats
  - TradingJournalForm - Create/edit trade form
  - Sidebar navigation to journal
- [x] **Comprehensive Testing**
  - Backend unit tests (test_trading_journal.py)
  - Integration tests (test_trading_journal_integration.py)
  - E2E tests (test_trading_journal_e2e.py)
- [x] **Documentation**
  - API documentation (docs/TRADING_JOURNAL_API.md)
  - Performance tests (docs/TRADING_JOURNAL_PERFORMANCE.md)
  - Security tests (docs/TRADING_JOURNAL_SECURITY.md)

### 1. Enhanced Portfolio Analytics
- [ ] **Asset Allocation Visualizations**
  - Sector-wise breakdown (IT, Pharma, Banking, FMCG, Auto, etc.)
  - Market cap distribution (Large/Mid/Small cap pie chart)
  - Geographic exposure (Indian/US/International stocks)
  - Industry diversification heat map

- [ ] **Performance Benchmarking**
  - Compare portfolio vs. Nifty50, Sensex, custom benchmarks
  - Alpha/Beta calculations with explanations
  - Sharpe ratio (risk-adjusted returns)
  - Sortino ratio (downside risk focus)
  - Maximum drawdown analysis

- [ ] **Historical Performance Charts**
  - Time-weighted returns (TWR)
  - Money-weighted returns (XIRR calculation)
  - Cumulative returns line chart
  - Year-over-year comparison
  - Monthly returns heat map

### 2. Advanced Broker Features
- [ ] **Auto-sync Holdings** (daily/hourly refresh)
  - Scheduled background jobs (Celery)
  - Manual refresh button
  - Last sync timestamp display

- [ ] **Order Execution Integration**
  - Place buy/sell orders from QuantLeap
  - Real-time order status tracking
  - Order history with fill prices

- [ ] **Dividend Tracking**
  - Auto-capture dividend payments
  - Dividend calendar (upcoming dates)
  - Dividend yield calculations
  - Total dividends earned dashboard

- [ ] **Corporate Actions Support**
  - Stock splits (auto-adjust quantities)
  - Bonus issues
  - Rights issues
  - Merger/demerger handling

### 3. Tax & Reporting
- [ ] **Capital Gains Calculator**
  - STCG (Short-term) calculation with 15% tax
  - LTCG (Long-term) calculation with 10% tax above ₹1L
  - FIFO/LIFO lot selection methods
  - Year-wise gains breakdown

- [ ] **Tax Loss Harvesting**
  - Identify losing positions for tax optimization
  - Suggest trades to minimize tax liability
  - Wash sale warnings

- [ ] **Downloadable Reports**
  - Annual P&L statement (PDF/Excel)
  - Transaction ledger with all trades
  - ITR-ready format for tax filing
  - Broker-wise holding summary

---

## Phase 2: Intelligence Layer (Weeks 5-8)

### 4. AI-Powered Insights
- [ ] **Portfolio Health Score** (0-100 rating)
  - Diversification score
  - Risk exposure score
  - Performance consistency score
  - Overall health with explanations

- [ ] **Risk Assessment Dashboard**
  - Concentration risk alerts (single stock > 20%)
  - Volatility analysis (standard deviation)
  - Beta-weighted portfolio risk
  - Value at Risk (VaR) - 1%, 5%, 10% scenarios
  - Correlation matrix between holdings

- [ ] **Smart Rebalancing Engine**
  - Define target allocation (% per sector/asset)
  - Current vs. target drift calculation
  - Recommended buy/sell to rebalance
  - Tax-efficient rebalancing (sell losses first)

- [ ] **Intelligent Alerts System**
  - Price target hit notifications
  - Unusual volume alerts (>3x average)
  - 52-week high/low breaches
  - Earnings date reminders
  - Dividend announcement alerts
  - Support/resistance level breaks

### 5. Research & Discovery Tools
- [ ] **Advanced Stock Screener**
  - Fundamental filters: P/E, P/B, ROE, debt/equity, market cap
  - Technical filters: RSI, MACD, moving average crossovers
  - Momentum screens: 52-week highs, breakouts
  - Value screens: Low P/E + high dividend yield
  - Growth screens: Revenue/profit growth > 20%
  - Save custom screens

- [ ] **Watchlists with Smart Alerts**
  - Multiple watchlists (e.g., "Potential Buys", "Watch for Dip")
  - Price alerts, volume alerts, news alerts
  - Technical indicator alerts (RSI < 30)

- [ ] **News Feed Integration**
  - Stock-specific news aggregation
  - Sentiment analysis (positive/negative/neutral)
  - Breaking news push notifications
  - Filter by relevance/source

- [ ] **Earnings Calendar & Analysis**
  - Upcoming earnings dates calendar view
  - Earnings call transcripts
  - EPS beat/miss tracking
  - Historical earnings trends

---

## Phase 3: Community & Learning (Weeks 9-12)

### 6. Social Features
- [ ] **Public Portfolio Sharing**
  - Optional: Share portfolio with unique link
  - Anonymous or named portfolios
  - View others' holdings & returns
  - Follow top-performing portfolios

- [ ] **Community Leaderboards**
  - Top performers (anonymized or opt-in)
  - Monthly/yearly/all-time rankings
  - Category leaderboards (small cap kings, dividend hunters)

- [ ] **Investment Ideas Forum**
  - Reddit/Twitter-style discussion threads
  - Post bullish/bearish stock ideas
  - Upvote/downvote system
  - Comment threads with threading
  - Tag stocks (e.g., $RELIANCE)

- [ ] **Portfolio Templates Library**
  - Pre-built portfolios: "Buffett Value", "FIRE Portfolio", "Aggressive Growth"
  - One-click copy to your account
  - Community-submitted templates
  - Performance tracking of templates

### 7. Educational Content Hub
- [ ] **Tutorials & Guides**
  - "Understanding XIRR vs CAGR"
  - "How to read technical indicators"
  - "Tax-efficient investing strategies"
  - Video walkthroughs embedded
  - Step-by-step onboarding

- [ ] **Financial Glossary**
  - Searchable definitions (Alpha, Beta, XIRR, etc.)
  - Examples with portfolio context
  - Related terms linking

- [ ] **Investment Calculators**
  - SIP calculator (monthly investment → future value)
  - Lumpsum calculator
  - Retirement planning calculator
  - Compound interest calculator
  - Goal-based investment calculator

---

## Phase 4: Advanced Tools (Weeks 13-16)

### 8. Goal-Based Investing
- [ ] **Financial Goals Module**
  - Create goals: Retirement, house, education, car, vacation
  - Set target amount & timeline
  - Link specific portfolios to goals
  - Track progress with visual indicators

- [ ] **Goal Progress Dashboard**
  - "On Track" / "Behind" / "Ahead" status
  - Monthly SIP recommendation to hit goal
  - Scenario analysis (what if returns are 8% vs 12%?)

- [ ] **Retirement Planner**
  - Current age, retirement age input
  - Expected monthly expenses in retirement
  - Calculate corpus needed (25x annual expenses)
  - Track progress toward retirement goal

### 9. Multi-Asset Class Support
- [ ] **Mutual Funds Integration**
  - BSE/NSE mutual fund APIs
  - Import MF holdings from broker
  - SIP tracking & returns calculation
  - Fund comparison tool

- [ ] **Fixed Income Assets**
  - Fixed deposits (manual entry)
  - Bonds (corporate, government)
  - PPF, EPF tracking
  - Interest earned calculations

- [ ] **Real Estate Module**
  - Property value tracking (manual updates)
  - Rental income tracking
  - Appreciation/depreciation over time

- [ ] **Cryptocurrency Integration**
  - WazirX, CoinDCX API integration
  - Bitcoin, Ethereum, altcoin holdings
  - Crypto P&L in INR
  - Portfolio allocation including crypto

- [ ] **Gold & Commodities**
  - Physical gold tracking (grams)
  - Gold ETFs, Sovereign Gold Bonds
  - Silver, other commodities

### 10. Advanced Charting
- [ ] **TradingView Integration**
  - Embed TradingView charts for each stock
  - Full technical analysis suite
  - Drawing tools, trend lines

- [ ] **Custom Indicators**
  - Build custom technical indicators
  - Combine multiple indicators (e.g., RSI + MACD strategy)
  - Backtest indicator performance

- [ ] **Pattern Recognition**
  - Auto-detect: Head & Shoulders, Double Top, Flags, Triangles
  - Alert when patterns form
  - Success rate statistics

---

## Phase 5: Monetization & Growth (Weeks 17-20)

### 11. Freemium Pricing Model

**Free Tier (Basic Investor)**
- 2 portfolios maximum
- 1 broker connection
- Basic analytics (P&L, holdings)
- Manual data entry
- 7-day data retention for charts

**Pro Tier ($10/month or ₹799/year)**
- Unlimited portfolios
- Unlimited broker connections
- Advanced analytics (benchmarking, risk metrics, XIRR)
- Tax reports & capital gains calculator
- Auto-sync holdings (daily)
- Email alerts & notifications
- Export to PDF/Excel
- Priority email support
- 5-year historical data

**Enterprise Tier ($50/month or ₹3,999/year)**
- Everything in Pro +
- Family/team accounts (up to 5 members)
- Custom reports & branding
- API access for developers
- White-label options
- Dedicated account manager
- Advanced integrations (QuickBooks, Tally)

### 12. Referral Program
- [ ] **Invite & Earn System**
  - Unique referral link per user
  - Referrer gets 1 month Pro free per signup
  - Referee gets 10% discount on first payment
  - Track referrals in dashboard

- [ ] **Affiliate Partnerships**
  - Partner with finance bloggers/YouTubers
  - 20% recurring commission on subscriptions
  - Dedicated affiliate dashboard

### 13. Revenue Streams
- [ ] **Display Advertising**
  - Google AdSense integration (free tier only)
  - Native ads blended with content
  - Non-intrusive placement

- [ ] **Sponsored Content**
  - Featured mutual funds / stocks
  - Educational content sponsored by financial institutions
  - Clearly marked as "Sponsored"

- [ ] **Broker Affiliate Commissions**
  - Earn commission when users open accounts via QuantLeap
  - Zerodha, Angel, 5Paisa affiliate programs
  - Transparent disclosure

---

## Phase 6: Scale & Trust (Ongoing)

### 14. Performance Optimization
- [ ] **Redis Caching Layer**
  - Cache holdings data (5-min TTL)
  - Cache market data (1-min TTL)
  - Session storage in Redis

- [ ] **Database Optimization**
  - PostgreSQL read replicas for queries
  - Connection pooling (PgBouncer)
  - Indexes on frequently queried columns
  - Partitioning for transactions table

- [ ] **CDN for Static Assets**
  - Cloudflare/CloudFront for React build
  - Compress images (WebP format)
  - Lazy loading for charts

- [ ] **Background Job Queue**
  - Celery + Redis for async tasks
  - Daily holdings sync jobs
  - Email sending queue
  - Report generation jobs

### 15. Security & Compliance
- [ ] **Two-Factor Authentication (2FA)**
  - TOTP-based (Google Authenticator, Authy)
  - SMS-based backup
  - Enforce 2FA for high-value accounts

- [ ] **Audit Logging**
  - Track all data access (who, when, what)
  - IP address logging
  - Failed login attempt tracking
  - Export audit logs for compliance

- [ ] **Privacy & Compliance**
  - GDPR-compliant data handling
  - Privacy policy & terms of service
  - Cookie consent banner
  - Right to data deletion

- [ ] **Bug Bounty Program**
  - Invite ethical hackers
  - Rewards for security vulnerabilities
  - Hall of fame for reporters

### 16. Data Management
- [ ] **Automated Backups**
  - Daily database backups (retain 30 days)
  - Weekly full backups (retain 1 year)
  - S3/Wasabi storage

- [ ] **Data Portability**
  - One-click export all data (CSV/JSON)
  - Move to competitor platforms
  - Delete account & data permanently

- [ ] **Version History**
  - Track changes to portfolio (undo/redo)
  - Restore previous state
  - Audit trail of edits

### 17. Mobile App
- [ ] **React Native Cross-Platform App**
  - iOS + Android with single codebase
  - Push notifications for alerts
  - Biometric login (fingerprint/Face ID)
  - Offline mode for viewing holdings
  - App Store & Play Store submission

---

## 🎯 Priority Implementation Timeline

### **Month 1 (Immediate Impact)**
1. ✅ Auto-sync holdings daily
2. ✅ Tax calculator (STCG/LTCG)
3. ✅ Portfolio benchmarking vs Nifty/Sensex
4. ✅ Dividend tracking
5. ✅ Export to Excel/PDF

**Expected User Value:** Save 2 hours/week on manual updates + tax calculations

### **Month 2 (User Engagement)**
6. ✅ Stock screener with filters
7. ✅ Watchlist with price alerts
8. ✅ Goal-based investing module
9. ✅ AI portfolio health score
10. ✅ Dark mode toggle

**Expected User Value:** Discovery tools + personalized insights drive daily engagement

### **Month 3 (Growth Features)**
11. ✅ Public portfolio sharing
12. ✅ Investment ideas forum
13. ✅ Freemium pricing launch
14. ✅ Referral program
15. ✅ Email alert system

**Expected User Value:** Viral growth + monetization starts

### **Months 4-6 (Platform Expansion)**
16. ✅ Mutual funds integration
17. ✅ Advanced charting (TradingView)
18. ✅ Mobile app (React Native)
19. ✅ 2FA security
20. ✅ Crypto holdings support

**Expected User Value:** Comprehensive financial dashboard

### **Months 7-12 (Maturity)**
21. ✅ Options/F&O tracking
22. ✅ White-label for advisors
23. ✅ International stocks (US markets)
24. ✅ Advanced risk analytics (VaR, stress testing)
25. ✅ Portfolio optimization algorithms

**Expected User Value:** Professional-grade tools competing with Bloomberg Terminal

---

## 💡 Quick Wins (This Week)

1. **Dark Mode Toggle** - 2 hours
   - Add theme context provider
   - Toggle button in settings
   - Store preference in localStorage

2. **Export to Excel** - 3 hours
   - Use SheetJS library
   - Export holdings, transactions, P&L

3. **Email Alerts Setup** - 4 hours
   - SendGrid/Postmark integration
   - Daily portfolio summary email
   - Price alert emails

4. **Portfolio Comparison View** - 4 hours
   - Side-by-side portfolio stats
   - Visual comparison charts

5. **Keyboard Shortcuts** - 2 hours
   - Ctrl+K: Command palette
   - / : Search focus
   - G + D: Go to dashboard

**Total: ~15 hours → Ship by weekend**

---

## 🔥 Unique Differentiators (vs Competitors)

### vs. Groww / Zerodha Coin / INDmoney

1. **AI Portfolio Doctor**
   - Weekly health checkup with actionable advice
   - "Your portfolio is overweight in banking sector by 15%"
   - Personalized recommendations, not generic

2. **Tax Optimization Engine**
   - Real-time tax implications before selling
   - Suggest trades to minimize tax (loss harvesting)
   - Year-end tax planning dashboard

3. **Family Wealth Dashboard**
   - Manage entire family's portfolios in one view
   - Parent/child account linking
   - Consolidated family net worth tracking

4. **Investment Journal**
   - Document why you bought each stock
   - Track investment thesis over time
   - Reflect on decisions (right/wrong analysis)

5. **Peer Comparison Intelligence**
   - "You're in top 15% of investors in your age group"
   - Benchmark against similar portfolios
   - Learn from better-performing peers

6. **Multi-Broker Unified View**
   - Unlike Groww (only Groww holdings), we show ALL brokers
   - True portfolio aggregation
   - Cross-broker analytics

---

## 📊 Success Metrics (KPIs)

### User Growth
- Monthly Active Users (MAU)
- Daily Active Users (DAU)
- User retention (Day 1, Day 7, Day 30)
- Referral conversion rate

### Engagement
- Average session duration
- Holdings sync frequency
- Portfolios created per user
- Transactions added per week

### Monetization
- Free → Pro conversion rate (target: 5%)
- Monthly Recurring Revenue (MRR)
- Customer Lifetime Value (LTV)
- Churn rate (target: < 3%/month)

### Product
- Feature adoption rates
- Bug reports / Critical issues
- Page load time (target: < 2s)
- API uptime (target: 99.9%)

---

## 🛠️ Technical Debt to Address

1. **Migration to Alembic** (database migrations)
2. **API Rate Limiting** (prevent abuse)
3. **Comprehensive Test Coverage** (>80%)
4. **CI/CD Pipeline** (GitHub Actions)
5. **Monitoring & Alerts** (Sentry, DataDog)
6. **API Documentation** (OpenAPI/Swagger enhancements)
7. **Code Quality** (SonarQube integration)

---

## 📝 Notes

- Focus on Indian market first (INR, NSE/BSE stocks)
- Prioritize mobile experience (60% users on mobile)
- Keep UI simple - financial data is complex enough
- Build trust through transparency & security
- Community features drive retention & viral growth
- Freemium model: Free tier good enough, Pro irresistible

---

**Last Updated:** January 27, 2026  
**Maintained By:** QuantLeap Team  
**Next Review:** End of Month 1

If you want to make it even better:

Database of all NSE/BSE stocks (use CSV import from NSE website)
BSE stock support (.BO suffix)
Crypto support (Bitcoin, Ethereum via Yahoo Finance)
Real-time WebSocket prices (live updates without refresh)
Historical price charts in search results
Fuzzy search (misspelling tolerance)
Your holdings system is now professional-grade with symbol validation and live pricing! 🎉


You have solid foundations—auth, portfolio CRUD, Zerodha integration, and a polished React UI. However, critical gaps prevent monetization.

🔴 IMMEDIATE NEEDS (Why Would Anyone Use This?)
The Hard Truth
Competitors like INDmoney, Kuvera, Groww, Smallcase already offer:

✅ Free portfolio tracking
✅ Multiple broker syncs
✅ Tax reports
✅ Mutual fund support
Your Unique Selling Points (USPs) to Emphasize:
USP	Why It Matters
Technical Analysis Dashboard	INDmoney/Kuvera don't have RSI/MACD charts—but yours is simulated, not real
AI Buy/Sell Recommendations	Unique! But currently returns random data
Self-Hostable/Privacy-First	Appeal to developers who don't trust 3rd parties with portfolio data
Real Zerodha OAuth	Automatic sync (not CSV import)—this is legitimately valuable
Bottom Line: Your differentiator is technical analysis + AI recommendations, but they're fake. Fix this first.

📋 Prioritized Roadmap
🔴 HIGH PRIORITY (Do First—Before Any Launch)
#	Task	Why It's Critical
1	Real Technical Indicators	Your USP is fake. Use yfinance historical data to calculate actual RSI/MACD/Bollinger Bands
2	Historical Price Storage	Without price_history table, charts are meaningless. Store daily closes.
3	Fix "Today's Change"	Dashboard shows ₹0 for today's change—embarrassing for a finance app
4	Remove or Complete Angel/5Paisa	They show in UI but return empty data—looks broken
5	Price Alerts	Every competitor has this. Add email/push notifications when stock hits target
🟡 MEDIUM PRIORITY (Before Monetization)
#	Task	Why It Matters
6	Tax Reports (STCG/LTCG)	India-specific pain point. Calculate based on holding period (< 1yr = STCG). Major selling point.
7	FIFO Cost Basis	Current P&L assumes LIFO—inaccurate for tax purposes
8	Billing System (Razorpay)	Can't monetize without payments
9	Feature Gating	Free tier vs Pro tier (e.g., alerts and tax reports = paid)
10	Dividend Tracking	Sync dividends from Zerodha trades
🟢 LOW PRIORITY (Growth Features)
#	Task	Impact
11	Mutual Fund Support	Expand addressable market
12	Stock Screener	P/E, ROE filters
13	Goal-Based Investing	"Retire at 50" calculators
14	Portfolio Sharing	Social proof, virality
15	Mobile App	React Native wrapper
💡 Monetization Models
Recommended: Freemium
Tier	Features	Price
Free	Portfolio tracking, manual entry, basic charts	₹0
Pro	Broker sync, price alerts, technical analysis, tax reports	₹199/mo or ₹1,499/yr
Pro+	AI recommendations, API access, priority support	₹499/mo
Alternative: One-Time Tax Report
Charge ₹299-499 for annual capital gains statement (high demand during tax season).

🏁 Suggested 4-Week Sprint
Week	Focus	Deliverables
1	Fix Core Data	Real technical indicators, price history table, today's change
2	Alerts + Tax	Price alerts with email, basic STCG/LTCG calculation
3	Broker Polish	Complete Angel integration OR remove it, improve Zerodha error handling
4	Monetization	Razorpay integration, subscription tiers, feature gating
🎯 Your Positioning Statement
"The only portfolio tracker for Indian investors with built-in technical analysis and AI-powered buy/sell signals—sync your Zerodha in one click."

This differentiates you from:

INDmoney (no technical analysis)
Kuvera (MF-focused, no broker sync)
Smallcase (curated portfolios, not tracking)
Would you like me to start implementing any of these priorities? I'd recommend beginning with real technical indicators since that's your main differentiator.