# QuantLeap Monetization - 8-Week Action Plan
**Start Date:** February 16, 2026  
**Launch Target:** April 13, 2026 (Week 8)  
**Goal:** Generate ₹10,000+ MRR from 50+ paid users

---

## Quick Summary

**Strategy:** Freemium subscription model  
**Pricing:** Free (current features) → Pro (₹199/mo) → Teams (₹999/mo)  
**Timeline:** 8 weeks to revenue  
**Year 1 Target:** ₹32L-60L ARR

---

## Week-by-Week Breakdown

### Week 1: Foundation & Planning (Feb 16-23)
**Owner:** Founder + Tech Lead

#### Tasks
- [x] Read monetization strategy report
- [ ] **Decision:** Choose Razorpay (recommended) vs. Stripe
  - **Razorpay Pros:** Indian company, better INR support, UPI payments, 2% fee
  - **Stripe Pros:** Better API docs, international expansion ready
- [ ] **Finalize Free vs. Pro split** (see table below)
- [ ] Legal review: Update Terms of Service and Privacy Policy
  - Hire contract lawyer (₹10-20K budget)
  - Add subscription terms, refund policy, DPDP compliance
- [ ] Setup project board (GitHub Projects or Notion)
- [ ] Kickoff meeting with full team

#### Deliverables
- ✅ Signed-off feature matrix
- ✅ Legal docs updated
- ✅ Payment gateway selected
- ✅ Project plan in GitHub/Notion

---

### Week 2-3: Backend Infrastructure (Feb 24 - Mar 9)
**Owner:** Backend Developer

#### Tasks
- [ ] **Integrate payment gateway**
  - Install Razorpay/Stripe SDK
  - Create subscription products in dashboard
  - Test payment flow end-to-end
  - `portfolio_tracker/routers/billing.py` (new file)

- [ ] **Database schema updates**
  ```python
  # Add to portfolio_tracker/models.py
  class SubscriptionModel(Base):
      __tablename__ = "subscriptions"
      id = Column(Integer, primary_key=True)
      user_id = Column(Integer, ForeignKey("users.id"))
      plan_type = Column(String(20))  # 'free', 'pro', 'teams'
      status = Column(String(20))  # 'active', 'cancelled', 'past_due'
      razorpay_subscription_id = Column(String(100))
      current_period_start = Column(DateTime)
      current_period_end = Column(DateTime)
      cancel_at_period_end = Column(Boolean, default=False)
  
  class PaymentModel(Base):
      __tablename__ = "payments"
      id = Column(Integer, primary_key=True)
      user_id = Column(Integer, ForeignKey("users.id"))
      subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
      amount = Column(Numeric(10, 2))
      currency = Column(String(3), default='INR')
      status = Column(String(20))
      razorpay_payment_id = Column(String(100))
      created_at = Column(DateTime)
  ```

- [ ] **Feature gating middleware**
  ```python
  # Add to portfolio_tracker/deps.py
  def require_subscription(plan: str = "pro"):
      async def dependency(user: UserModel = Depends(get_current_user)):
          if user.subscription.plan_type not in [plan, "teams"]:
              raise HTTPException(403, "Upgrade to Pro to access this feature")
          return user
      return dependency
  
  # Usage in routers:
  @router.post("/broker/{broker}/sync-holdings")
  async def sync_holdings(
      user: UserModel = Depends(require_subscription("pro"))
  ):
      ...
  ```

- [ ] **Webhook handler**
  ```python
  @router.post("/billing/webhook")
  async def handle_webhook(request: Request):
      # Verify Razorpay signature
      # Handle: subscription.charged, subscription.cancelled
      # Update database
  ```

- [ ] **Migration script**
  - Set all existing users to "free" tier
  - No downtime migration

- [ ] **Tests**
  - `tests/test_billing.py` (create subscription, payment, webhook)
  - Edge cases: failed payments, cancellations

#### Deliverables
- ✅ Payment flow works on staging
- ✅ Database migrated successfully
- ✅ Feature gating tested
- ✅ 90%+ test coverage on billing code

---

### Week 3-4: Frontend Pricing & Checkout (Feb 24 - Mar 9)
**Owner:** Frontend Developer

#### Tasks
- [ ] **Standalone Pricing page**
  - Extract from `LandingPage.tsx` (lines 532-622)
  - Create `frontend/src/ui/pages/PricingPage.tsx`
  - Add route `/pricing` in `router.tsx`
  - Make comparison table responsive

- [ ] **Upgrade flow in Settings**
  ```tsx
  // frontend/src/ui/pages/SettingsPage.tsx
  import { useAuth } from '@/providers/auth/AuthProvider'
  
  function SubscriptionSection() {
    const { user } = useAuth()
    const isProUser = user?.subscription?.plan === 'pro'
    
    if (isProUser) return <div>✅ Pro</div>
    
    return (
      <div>
        <h3>Upgrade to Pro</h3>
        <button onClick={handleUpgrade}>Upgrade Now</button>
      </div>
    )
  }
  ```

- [ ] **Razorpay checkout integration**
  ```tsx
  // Install: npm install razorpay
  const handleUpgrade = async () => {
    const { data } = await api.post('/billing/create-checkout')
    
    const options = {
      key: import.meta.env.VITE_RAZORPAY_KEY,
      subscription_id: data.subscription_id,
      name: 'QuantLeap Pro',
      description: 'Monthly Pro Plan',
      handler: function (response) {
        // Verify and activate subscription
        api.post('/billing/verify-payment', response)
      }
    }
    
    const rzp = new Razorpay(options)
    rzp.open()
  }
  ```

- [ ] **Upgrade CTAs ("paywalls")**
  - Dashboard: "Want hourly auto-sync?" → modal
  - Brokers page: "Connect more than 2 brokers" → banner
  - Analytics: "Advanced indicators" → blur preview + CTA
  - Holdings CSV export: "Unlock unlimited exports" → modal

- [ ] **Success/failure pages**
  - `/app/upgrade/success` → redirect to dashboard with toast
  - `/app/upgrade/failed` → show error, offer retry

#### Deliverables
- ✅ `/pricing` page live
- ✅ Upgrade flow end-to-end working
- ✅ At least 3 upgrade CTAs placed
- ✅ Mobile-responsive design

---

### Week 4-5: Feature Gating Implementation (Mar 10-23)
**Owner:** Full-Stack Developer

#### Priority Paywalls

1. **Broker connection limit (Free: 2, Pro: unlimited)**
   ```tsx
   // frontend/src/ui/pages/BrokersPage.tsx
   const connectedBrokers = brokerConfigs.length
   const canConnect = user.subscription.plan === 'pro' || connectedBrokers < 2
   
   if (!canConnect) {
     return <UpgradeModal feature="Connect 5+ brokers" />
   }
   ```

2. **CSV export limit (Free: 3/month, Pro: unlimited)**
   ```python
   # backend: track exports per user per month
   if user.subscription.plan == 'free':
       exports_this_month = count_exports(user.id, current_month)
       if exports_this_month >= 3:
           raise HTTPException(403, "Upgrade to Pro for unlimited exports")
   ```

3. **Sync frequency (Free: manual, Pro: hourly auto-sync)**
   ```python
   # backend cron job (runs hourly)
   pro_users = db.query(UserModel).join(SubscriptionModel).filter(
       SubscriptionModel.plan_type.in_(['pro', 'teams'])
   ).all()
   
   for user in pro_users:
       sync_all_brokers(user)
   ```

4. **Advanced analytics (Pro only)**
   - Gate `/api/analysis/advanced` endpoint
   - Show blurred preview on frontend for free users

#### UX Guidelines
- **Don't hard-block:** Show value first, then paywall
- **Clear messaging:** "Upgrade to Pro to unlock this feature" (not generic "Access Denied")
- **One-click upgrade:** Directly open Razorpay modal, don't redirect

#### Deliverables
- ✅ All 4 paywalls implemented
- ✅ Free tier degradation tested (no broken features)
- ✅ Upgrade conversion funnel tracked

---

### Week 5-6: Analytics & Admin Dashboard (Mar 24 - Apr 6)
**Owner:** Backend Developer

#### Tasks
- [ ] **Integrate analytics (Mixpanel or PostHog)**
  ```typescript
  // frontend/src/lib/analytics.ts
  import mixpanel from 'mixpanel-browser'
  
  mixpanel.init(import.meta.env.VITE_MIXPANEL_TOKEN)
  
  export const track = (event: string, props?: object) => {
    mixpanel.track(event, props)
  }
  
  // Track key events:
  track('user_signed_up')
  track('broker_connected', { broker: 'zerodha' })
  track('upgrade_clicked', { source: 'dashboard' })
  track('payment_success', { plan: 'pro', amount: 199 })
  ```

- [ ] **Conversion funnels**
  - Landing → Sign Up → Broker Connect → Upgrade
  - Track dropoff at each step

- [ ] **Internal admin dashboard**
  - Route: `/admin` (protect with admin role check)
  - Metrics:
    - Total users, paid users, MRR
    - Today's signups, upgrade, churn
    - Top referral sources
  - Actions:
    - Grant free Pro trial (for support/influencers)
    - Manually refund payment
    - View user subscription details

- [ ] **Monitoring & alerts**
  - Slack webhook: New payment received
  - Email alert: Payment failure
  - Daily summary: MRR, new users, churn

#### Deliverables
- ✅ Mixpanel tracking live
- ✅ Admin dashboard accessible
- ✅ Alerts configured

---

### Week 6-7: QA & Security Audit (Apr 7-20)
**Owner:** QA Lead (or Founder)

#### Test Cases
- [ ] **Happy path:** Sign up → connect broker → upgrade → payment succeeds
- [ ] **Failed payment:** Card declined → retry → update card
- [ ] **Cancellation:** Cancel Pro → downgrade to Free tier → data preserved
- [ ] **Refund:** Request refund → manually process in Razorpay → mark cancelled
- [ ] **Webhook reliability:** Simulate webhook failure → retry mechanism
- [ ] **Feature gating:** Try to access Pro feature as free user → 403 error

#### Security Checks
- [ ] **SQL injection:** Test all payment-related endpoints
- [ ] **XSS:** Ensure no user input rendered unescaped
- [ ] **CSRF:** Verify CSRF tokens on state-changing requests
- [ ] **Rate limiting:** Auth endpoints limited to 5 req/min
- [ ] **HTTPS:** Entire site on HTTPS (Let's Encrypt)

#### Performance Testing
- [ ] Load test: 1000 concurrent users on dashboard
- [ ] Payment processing: <3 second Razorpay redirect
- [ ] Database queries: All billing queries <100ms

#### Deliverables
- ✅ All test cases pass
- ✅ No critical security issues
- ✅ Performance benchmarks met
- ✅ Production deployment checklist ready

---

### Week 8: Launch Week 🚀 (Apr 21-27)
**Owner:** Founder

#### Pre-Launch (Monday-Wednesday)
- [ ] **Deploy to production**
  - Merge all feature branches
  - Run database migrations
  - Deploy backend to Render
  - Deploy frontend to Vercel
  - Verify payment flow on production

- [ ] **Final checks**
  - Test payment with real card (₹199)
  - Verify webhook receives events
  - Check admin dashboard
  - Review Terms of Service one last time

- [ ] **Prepare launch assets**
  - Blog post: "Introducing QuantLeap Pro"
  - Email to existing users (announce Pro tier)
  - Social media posts (Twitter, LinkedIn, Reddit)
  - Demo video (30 sec Loom)

#### Launch Day (Thursday)
- [ ] **Update landing page**
  - Change "Coming Q2 2026" to "Available Now"
  - Add "Upgrade to Pro" button in navbar

- [ ] **Announce**
  - Email existing users (subject: "QuantLeap Pro is now live!")
  - Post on Reddit: r/IndiaInvestments, r/IndianStockMarket
  - Tweet with demo video
  - LinkedIn post (founder's network)
  - Product Hunt launch (optional)

- [ ] **Monitor**
  - Watch Slack for payment notifications
  - Check admin dashboard every hour
  - Respond to support emails within 2 hours

#### Post-Launch (Friday-Sunday)
- [ ] **Collect feedback**
  - Email first 10 paying users: "Thank you! Any feedback?"
  - Post in Discord/community: "We launched Pro!"
  - Monitor social media mentions

- [ ] **Fix urgent bugs**
  - Triage critical issues (payment failures)
  - Deploy hotfixes within 24 hours

- [ ] **Celebrate!** 🎉
  - Team dinner/video call
  - Share first MRR milestone on Twitter

#### Deliverables
- ✅ Pro tier live on production
- ✅ 10+ paying users in first 7 days
- ✅ ₹1,990+ MRR (minimum 10 users)
- ✅ Zero critical bugs
- ✅ <5% payment failure rate

---

## Free vs. Pro Feature Split (Final)

| Feature                     | Free                      | Pro (₹199/mo)                      |
| --------------------------- | ------------------------- | ---------------------------------- |
| **Portfolios**              | Unlimited                 | Unlimited                          |
| **Broker connections**      | 2 (Zerodha + 5Paisa)      | 5+ (add Angel, Upstox)             |
| **Sync frequency**          | Manual only               | Hourly auto-sync                   |
| **Real-time prices**        | ✅                         | ✅                                  |
| **Holdings & transactions** | ✅                         | ✅                                  |
| **Basic analytics**         | ✅ (P&L, sector breakdown) | ✅                                  |
| **Technical indicators**    | Basic (RSI, MACD)         | Advanced (Bollinger, VWAP, custom) |
| **Tax reports**             | 1 FY export/month         | Unlimited FY exports               |
| **CSV exports**             | 3/month                   | Unlimited                          |
| **Price alerts**            | ❌                         | ✅ Email + SMS                      |
| **Portfolio rebalancing**   | ❌                         | ✅ AI-powered                       |
| **Mutual funds**            | ❌                         | ✅ MF tracking                      |
| **Historical data**         | 90 days                   | 3 years                            |
| **Support**                 | Community forum           | Email (24h response)               |

---

## Success Metrics (Week 8)

### Primary KPIs
- [x] Pro tier launched
- [ ] **10+ paid users** in first 7 days
- [ ] **₹1,990+ MRR** (10 × ₹199)
- [ ] **<5% payment failure rate**
- [ ] **<10% churn** in first month

### Secondary KPIs
- [ ] 2% freemium conversion rate
- [ ] Average time to upgrade: <7 days
- [ ] NPS score: >40
- [ ] Zero legal compliance issues
- [ ] <3 critical bugs reported

---

## Team Roles & Responsibilities

| Role              | Owner               | Weekly Hours | Deliverables                              |
| ----------------- | ------------------- | ------------ | ----------------------------------------- |
| **Product Owner** | Founder             | 20h          | Feature decisions, launch plan, marketing |
| **Backend Dev**   | (Name)              | 40h          | Billing API, webhooks, feature gating     |
| **Frontend Dev**  | (Name)              | 40h          | Pricing page, checkout, upgrade CTAs      |
| **QA/Security**   | Founder or Contract | 20h          | Test cases, security audit                |
| **Legal**         | Contract Lawyer     | 8h           | Terms update, DPDP compliance             |

---

## Budget (8-Week Sprint)

| Item              | Cost      | Notes                                 |
| ----------------- | --------- | ------------------------------------- |
| **Team Salaries** | ₹2-3L     | 2 developers × 8 weeks                |
| **Legal Review**  | ₹10-20K   | Contract lawyer, Terms/Privacy update |
| **Tools**         | ₹5-10K    | Mixpanel, hosting, domains            |
| **Marketing**     | ₹10-20K   | Demo video, ads (optional)            |
| **Contingency**   | ₹20K      | Unexpected costs                      |
| **Total**         | ₹2.5-3.7L | One-time investment                   |

**Break-even:** 12-18 months at ₹10K MRR growth rate

---

## Risk Register

| Risk                                   | Probability | Impact   | Mitigation                            |
| -------------------------------------- | ----------- | -------- | ------------------------------------- |
| **Payment gateway integration issues** | Medium      | High     | Budget 1 extra week, test early       |
| **Low conversion rate (<1%)**          | Medium      | High     | Offer 14-day free trial               |
| **Legal compliance issues**            | Low         | Critical | Hire lawyer, follow checklist         |
| **Competitive pricing pressure**       | High        | Medium   | Differentiate on privacy, not price   |
| **Technical bugs on launch day**       | Medium      | High     | Comprehensive QA, staging environment |

---

## Post-Launch Roadmap (Weeks 9-16)

### Phase 2: Growth (Months 3-6)
- [ ] **Affiliate partnerships**
  - Sign Angel One, Upstox, Cleartax
  - Add affiliate tracking
  - Place CTAs strategically

- [ ] **Pro feature development**
  - Price alerts (email + SMS)
  - Advanced technical indicators
  - Mutual fund tracking

- [ ] **Marketing & community**
  - 2 blog posts/week
  - r/IndiaInvestments engagement
  - Referral program: "Invite a friend, both get Pro free for 1 month"

### Phase 3: Scale (Months 7-12)
- [ ] **Teams/Family plan** (₹999/mo)
- [ ] **API launch** (₹499-₹2,999/mo)
- [ ] **Enterprise partnerships**

---

## Quick Links

- 📊 [Full Monetization Report](./MONETIZATION_STRATEGY_2026.md)
- 📋 [Feature Checklist](./FEATURES_CHECKLIST.md)
- 🗺️ [Product Roadmap](./ROADMAP.md)
- 📝 [Terms of Service](./docs/TERMS_AND_CONDITIONS.md)

---

## Contact & Support

**Questions?** File an issue or reach out to the founder.

**Launch Date Target:** April 13, 2026 (8 weeks from today)

Let's build a profitable, privacy-first portfolio tracker! 🚀
