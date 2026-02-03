# Features Checklist - Portfolio Tracker

## Free Tier Features

### ✅ IMPLEMENTED & AVAILABLE

#### 1. **Unlimited Portfolios**
- ✅ Users can create multiple portfolios
- ✅ Manage and switch between portfolios
- ✅ Each portfolio has independent holdings and transactions
- **Location**: `HoldingsPage.tsx`, `portfolio.py` router

#### 2. **Connect 2 Brokers (Zerodha, 5Paisa)**
- ✅ **Zerodha**: Full OAuth2 integration
  - Login/authorize via Kite web
  - Sync holdings automatically
  - Sync recent trades (last ~2 weeks)
  - Sync all historical trades
  - **Location**: `BrokersPage.tsx`, `broker.py` router, `brokers/zerodha.py`

- ✅ **5Paisa**: Full OAuth2 integration
  - Login/authorize via 5Paisa web
  - Sync holdings automatically
  - **Location**: `BrokersPage.tsx`, `broker.py` router, `brokers/fivepaisa.py`

- ❌ **Angel**: Marked as "Coming Soon" (not implemented)

#### 3. **Real-time P&L Tracking**
- ✅ Dashboard shows live portfolio value
- ✅ Total gain/loss calculation with percentage
- ✅ Holdings page shows current prices and P&L per asset
- ✅ Today's change calculated from previous close
- **Location**: `DashboardPage.tsx`, `HoldingsPage.tsx`, `dashboard.py` router

#### 4. **Technical Indicators (RSI, MACD)**
- ✅ **RSI Indicator**: Displayed with color coding
  - Green zone: Oversold (< 30)
  - Red zone: Overbought (> 70)
  - **Location**: `TechnicalAnalysisPage.tsx`, `analysis.py` router

- ✅ **MACD Indicator**: Displayed with signal lines
  - Positive/negative divergence highlighted
  - **Location**: `TechnicalAnalysisPage.tsx`, `analysis.py` router

- ✅ Technical signals page shows all holdings with indicators
- **Location**: `/app/analysis` route

#### 5. **Tax Reports (STCG/LTCG)** ⭐ NEW
- ✅ Capital gains calculation using FIFO/LIFO method
- ✅ STCG vs LTCG breakdown by symbol
- ✅ Tax liability calculation with current rates:
  - STCG: 20% (no exemption)
  - LTCG: 12.5% (with ₹1.25L annual exemption)
- ✅ Filter by financial year (FY 2024-25, etc.)
- ✅ Transaction-level details with holding periods
- ✅ Unrealized gains calculation
- ✅ CSV export for ITR filing
- **Location**: `/app/tax-reports` route, `TaxReportsPage.tsx`, `tax_reports.py` router, `tax_calculator.py`

#### 6. **Export to CSV/Excel**
- ✅ Portfolio holdings export (CSV)
  - Includes: Symbol, Quantity, Buy Price, Current Price, Gain/Loss
  - **Location**: `HoldingsPage.tsx`, `portfolio.py` router

- ✅ All transactions export (CSV)
  - Includes: Date, Symbol, Type (Buy/Sell), Quantity, Price, Total Value
  - **Location**: `TransactionsPage.tsx`, `transactions.py` router

- ✅ Tax report export (CSV)
  - Includes: Buy/Sell dates, quantities, gains, holding periods, type (STCG/LTCG)
  - **Location**: `TaxReportsPage.tsx`

#### 7. **Email Support**
- ❌ Not yet implemented
- Planned for Pro tier or separate support channel
- **Status**: Roadmap item

---

## Premium Tier Features (Coming Q2 2026)

### 🚧 IN PROGRESS / PLANNED

- [ ] **Price Alerts** (email + push notifications)
- [ ] **Advanced AI Technical Signals**
- [ ] **Mutual Fund Support**
- [ ] **Portfolio Sharing** (family/friends)
- [ ] **Goal-Based Investing**
- [ ] **Dividend Tracking**
- [ ] **Stock Screener** (P/E, ROE filters)
- [ ] **Mobile App** (React Native)

---

## Implementation Status by Page

| Page | Route | Status | Features |
|------|-------|--------|----------|
| Dashboard | `/app/dashboard` | ✅ Live | Real-time P&L, portfolio summary |
| Holdings | `/app/holdings` | ✅ Live | Portfolio management, CSV export |
| Transactions | `/app/transactions` | ✅ Live | Transaction history, CSV export |
| Technical Analysis | `/app/analysis` | ✅ Live | RSI, MACD, AI signals |
| **Tax Reports** | `/app/tax-reports` | ✅ **LIVE** | STCG/LTCG, FY filtering, CSV export |
| Brokers | `/app/brokers` | ✅ Live | Zerodha, 5Paisa sync, Angel coming soon |
| Settings | `/app/settings` | ✅ Live | Profile, password reset |

---

## API Endpoints Summary

### Portfolio Management
- `GET /api/portfolios/` - List user's portfolios
- `POST /api/portfolios/` - Create new portfolio
- `GET /api/portfolio/{id}` - Get portfolio details
- `GET /api/portfolio/{id}/export` - Export holdings to CSV

### Transactions
- `GET /api/transactions/` - List all transactions
- `GET /api/transactions/export` - Export all transactions to CSV
- `POST /api/transactions/` - Add transaction

### Broker Integration
- `POST /api/broker/zerodha/setup` - Setup Zerodha
- `POST /api/broker/zerodha/callback` - Zerodha OAuth callback
- `POST /api/broker/zerodha/sync-holdings` - Sync Zerodha holdings
- `POST /api/broker/zerodha/sync-transactions` - Sync Zerodha trades
- `GET /api/broker/zerodha/login-url` - Get Zerodha login URL
- `POST /api/broker/fivepaisa/setup` - Setup 5Paisa
- `POST /api/broker/fivepaisa/callback` - 5Paisa OAuth callback
- `POST /api/broker/fivepaisa/sync-holdings` - Sync 5Paisa holdings
- `GET /api/broker/fivepaisa/login-url` - Get 5Paisa login URL
- `GET /api/broker/configs` - List connected brokers
- `DELETE /api/broker/configs/{id}` - Disconnect broker

### Technical Analysis
- `GET /api/analysis/technical` - Get technical indicators for all holdings

### Tax Reports ⭐ NEW
- `GET /api/tax-reports/portfolios/{id}/capital-gains` - Calculate tax report
- `GET /api/tax-reports/portfolios/{id}/available-years` - Get available FYs
- `GET /api/tax-reports/portfolios/{id}/tax-summary` - Multi-year summary

### Dashboard
- `GET /api/dashboard/summary` - Portfolio summary

---

## Free Tier - Feature List

✅ Unlimited portfolios  
✅ Connect 2 brokers (Zerodha, 5Paisa)  
✅ Real-time P&L tracking  
✅ Technical indicators (RSI, MACD)  
✅ **Tax reports (STCG/LTCG)** ← NEW!  
✅ Export to CSV/Excel  
⏳ Email support (planned)  

---

## Known Limitations

1. **Angel Broking**: Not yet implemented (UI shows "Coming Soon")
2. **Email Notifications**: Not yet implemented
3. **Historical Price Data**: Limited to broker sync data, not daily EOD history
4. **Indexation Benefit**: Not calculated (12.5% LTCG rate applies without indexation)
5. **STT**: Not calculated (informational note only)
6. **Non-Resident Tax**: Not calculated (assumed resident)

---

## Notes

- All tax calculations follow **Post-July 23, 2024 Budget 2024** rates
- FIFO/LIFO method can be toggled to see impact on tax liability
- ₹1.25L LTCG exemption per financial year (April 1 - March 31)
- Holding period threshold: 365 days for LTCG classification
- All CSV exports are sortable and can be opened in Excel
