export type User = {
  id: number
  email: string
  username: string
  full_name?: string | null
  is_active: boolean
  created_at: string
}

export type TokenResponse = {
  access_token: string
  token_type: string
  user: User
}

// ---------------------------------------------------------------------------
// Subscription / billing types
// ---------------------------------------------------------------------------

export type SubscriptionTier = 'free' | 'pro' | 'teams'

export type PlanLimits = {
  max_brokers: number | null        // null = unlimited
  exports_per_month: number | null  // null = unlimited
  auto_sync: string                 // 'daily' | 'hourly'
}

export type SubscriptionStatus = {
  tier: SubscriptionTier
  status: 'active' | 'cancelled' | 'expired'
  expires_at: string | null
  limits: PlanLimits
  usage: {
    exports_this_month: number
  }
  razorpay_key_id: string | null
}

export type DashboardStats = {
  total_portfolio_value: number
  total_invested: number
  total_gain_loss: number
  gain_loss_percentage: number
  number_of_portfolios: number
  number_of_assets: number
  today_change?: number | null
  today_change_percentage?: number | null
  best_performer?: {
    symbol: string
    name: string
    return_pct: number
  } | null
  worst_performer?: {
    symbol: string
    name: string
    return_pct: number
  } | null
  average_return?: number | null
  total_return_percentage?: number | null
  diversification_score?: number | null
  winning_assets?: number | null
  losing_assets?: number | null
}

export type Asset = {
  id: number
  portfolio_id: number
  symbol: string
  name: string
  quantity: number | string
  current_price: number | string
  purchase_price: number | string
  previous_close?: number | string | null
}

export type Portfolio = {
  id: number
  name: string
  description?: string | null
  created_at: string
  updated_at: string
  assets: Asset[]
}

export type TransactionRow = {
  id: number
  portfolio_id: number
  portfolio_name: string
  asset_id: number | null
  asset_name: string
  asset_symbol: string
  transaction_type: string
  quantity: number
  price_per_unit: number
  notes?: string | null
  transaction_date: string
}
