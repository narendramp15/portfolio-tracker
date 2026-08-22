"""Pydantic schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# Authentication Schemas
class UserRegister(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: Optional[str] = Field(None, max_length=100, description="User full name")


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    """Schema for JWT token data."""

    email: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr = Field(..., description="User email address")


class PasswordReset(BaseModel):
    """Schema for password reset."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class GrowthDataPoint(BaseModel):
    """Schema for growth chart data point."""

    year: int
    month: int
    value: float
    # Null when no index close is available for that date - the chart draws a
    # gap rather than interpolating a benchmark that was never observed.
    nifty_value: Optional[float] = None
    label: str
    # Fraction of portfolio value that could be priced from real history.
    # Below 1.0 the line understates the portfolio and the UI says so.
    coverage: float = 1.0


# Asset Schemas
class AssetBase(BaseModel):
    """Base asset schema."""

    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol (e.g., RELIANCE.NS)")
    name: Optional[str] = Field(None, max_length=100, description="Company name (auto-filled if not provided)")
    quantity: Decimal = Field(..., gt=0, description="Number of shares")
    current_price: Optional[Decimal] = Field(None, gt=0, description="Current market price (auto-fetched if not provided)")
    purchase_price: Decimal = Field(..., gt=0, description="Average purchase price per share")


class AssetCreate(AssetBase):
    """Schema for creating an asset with symbol validation."""

    pass


class AssetUpdate(BaseModel):
    """Schema for updating an asset."""

    quantity: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    purchase_price: Optional[Decimal] = None


class Asset(AssetBase):
    """Asset schema with database fields.

    Note: numeric constraints (gt=0) are intentionally removed here relative to
    AssetBase so that response serialisation never fails for historical rows that
    may have a stored price/quantity of 0 (e.g. created before a price refresh).
    Input validation still enforces gt=0 via AssetCreate -> AssetBase.
    """

    id: int
    portfolio_id: int
    # Override parent gt=0 constraints — responses must not reject stored zeros
    quantity: Decimal
    current_price: Optional[Decimal] = None
    purchase_price: Decimal
    previous_close: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class PortfolioBase(BaseModel):
    """Base portfolio schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class PortfolioCreate(PortfolioBase):
    """Schema for creating a portfolio."""

    pass


class PortfolioUpdate(BaseModel):
    """Schema for updating a portfolio."""

    name: Optional[str] = None
    description: Optional[str] = None


class Portfolio(PortfolioBase):
    """Portfolio schema with database fields and assets."""

    id: int
    created_at: datetime
    updated_at: datetime
    assets: list[Asset] = []

    class Config:
        """Pydantic config."""

        from_attributes = True


class TransactionBase(BaseModel):
    """Base transaction schema."""

    type: str = Field(..., pattern="^(buy|sell)$")
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    notes: Optional[str] = None

    # Charges are optional: a user who does not enter them gets the same
    # numbers as before, but one who does gets gains net of trading costs.
    brokerage: Optional[Decimal] = Field(default=None, ge=0)
    stt: Optional[Decimal] = Field(default=None, ge=0)
    other_charges: Optional[Decimal] = Field(default=None, ge=0)


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction."""

    asset_id: int


class Transaction(TransactionBase):
    """Transaction schema with database fields."""

    id: int
    asset_id: int
    portfolio_id: int
    transaction_date: datetime
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class DashboardStats(BaseModel):
    """Dashboard statistics schema."""

    total_portfolio_value: Decimal
    total_invested: Decimal
    total_gain_loss: Decimal
    gain_loss_percentage: Decimal
    number_of_portfolios: int
    number_of_assets: int
    
    # Professional KPIs
    today_change: Optional[Decimal] = None
    today_change_percentage: Optional[Decimal] = None
    best_performer: Optional[dict] = None  # {symbol, name, return_pct}
    worst_performer: Optional[dict] = None  # {symbol, name, return_pct}
    average_return: Optional[Decimal] = None
    total_return_percentage: Optional[Decimal] = None
    diversification_score: Optional[int] = None  # Number of unique assets
    winning_assets: Optional[int] = None  # Assets with positive returns
    losing_assets: Optional[int] = None  # Assets with negative returns

# Broker Configuration Schemas
class BrokerConfigBase(BaseModel):
    """Base broker configuration schema."""

    broker_name: str = Field(..., description="Broker name (zerodha, angel, 5paisa, etc.)")
    broker_user_id: str = Field(..., description="Broker user ID")


class BrokerConfigCreate(BrokerConfigBase):
    """Schema for creating broker configuration."""

    access_token: Optional[str] = Field(None, description="Broker access token")
    refresh_token: Optional[str] = Field(None, description="Broker refresh token")
    api_key: Optional[str] = Field(None, description="Broker API key")


# ---------------------------------------------------------------------------
# Broker credential submission
#
# These MUST be request bodies, never query parameters. Query strings are
# written verbatim to web-server access logs, reverse-proxy logs, browser
# history and Referer headers — none of which are under our control, and all of
# which would then hold live broker API secrets and account passwords.
# ---------------------------------------------------------------------------


class BrokerSetupRequest(BaseModel):
    """API key/secret pair used by Zerodha, Upstox and Groww setup."""

    api_key: str = Field(..., min_length=1, max_length=200, description="Broker API key")
    api_secret: str = Field(..., min_length=1, max_length=500, description="Broker API secret")
    consent_given: bool = Field(default=False, description="User consented to credential storage")


class DhanSetupRequest(BaseModel):
    """Dhan issues a long-lived access token directly, with no OAuth exchange."""

    client_id: str = Field(..., min_length=1, max_length=200, description="Dhan Client ID")
    access_token: str = Field(..., min_length=1, max_length=2000, description="Dhan Access Token")
    consent_given: bool = Field(default=False)


class FivePaisaSetupRequest(BaseModel):
    """5Paisa needs app-level credentials plus the user's own login password."""

    user_key: Optional[str] = Field(None, max_length=200, description="5Paisa User Key (VendorKey)")
    encryption_key: Optional[str] = Field(None, max_length=500, description="5Paisa Encryption Key")
    api_key: Optional[str] = Field(None, max_length=200, description="Legacy alias for user_key")
    api_secret: Optional[str] = Field(None, max_length=500, description="Legacy alias for encryption_key")
    app_name: Optional[str] = Field(None, max_length=200)
    app_source: Optional[str] = Field(None, max_length=200)
    user_id_5p: Optional[str] = Field(None, max_length=200, description="5Paisa User ID")
    password: Optional[str] = Field(None, max_length=200, description="5Paisa Password")
    consent_given: bool = Field(default=False)


class BrokerCallbackRequest(BaseModel):
    """OAuth request token returned by a broker redirect.

    Short-lived, but still single-use proof of authorisation — it is exchanged
    for an access token, so it does not belong in a URL either.
    """

    request_token: str = Field(..., min_length=1, max_length=2000)
    config_id: Optional[int] = Field(default=None)


class BrokerConfigResponse(BrokerConfigBase):
    """Schema for broker configuration response."""

    id: int
    user_id: int
    is_active: bool
    is_authorized: bool = Field(default=False, description="Whether the broker has a valid access token")
    last_synced: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BrokerHolding(BaseModel):
    """Schema for broker holding data."""

    symbol: str = Field(..., description="Stock symbol")
    isin: Optional[str] = Field(None, description="ISIN code")
    quantity: Decimal = Field(..., gt=0, description="Quantity held")
    average_price: Decimal = Field(..., gt=0, description="Average buy price")
    current_price: Decimal = Field(..., gt=0, description="Current market price")
    last_price: Decimal = Field(..., gt=0, description="Last traded price")


class BrokerSyncResponse(BaseModel):
    """Schema for broker sync response."""

    success: bool
    message: str
    holdings_count: int = 0
    assets_imported: int = 0


# Technical Analysis Schemas
class TechnicalIndicators(BaseModel):
    """Schema for technical indicators calculated from real historical data."""

    rsi: float  # 0-100, Relative Strength Index
    macd: dict  # value, signal, histogram
    moving_averages: dict  # sma_20, sma_50, sma_200
    bollinger_bands: dict  # upper, middle, lower, width
    volume: dict  # trend, average, current, ratio
    price_position: Optional[str] = None  # Position relative to Bollinger Bands
    data_points: Optional[int] = None  # Number of historical data points used
    last_updated: Optional[str] = None  # ISO timestamp of calculation


class TechnicalAnalysis(BaseModel):
    """Schema for technical analysis with AI recommendation."""

    asset_id: int
    symbol: str
    name: str
    portfolio_name: str
    current_price: float
    purchase_price: float
    quantity: float
    invested_value: float
    current_value: float
    gain_loss: float
    gain_loss_percentage: float
    indicators: dict
    recommendation: str
    action_text: str
    signals: list[str]
    bullish_factors: int
    bearish_factors: int


class BrokerTransactionsSyncResponse(BaseModel):
    """Schema for broker transactions sync response."""

    success: bool
    message: str
    transactions_count: int = 0
    transactions_imported: int = 0
