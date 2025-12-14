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

export type DashboardStats = {
  total_portfolio_value: number
  total_invested: number
  total_gain_loss: number
  gain_loss_percentage: number
  number_of_portfolios: number
  number_of_assets: number
}

export type Asset = {
  id: number
  portfolio_id: number
  symbol: string
  name: string
  quantity: number | string
  current_price: number | string
  purchase_price: number | string
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
