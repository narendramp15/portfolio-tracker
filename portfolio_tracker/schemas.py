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


# Asset Schemas
class AssetBase(BaseModel):
    """Base asset schema."""

    symbol: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=100)
    quantity: Decimal = Field(..., gt=0)
    current_price: Decimal = Field(..., gt=0)
    purchase_price: Decimal = Field(..., gt=0)


class AssetCreate(AssetBase):
    """Schema for creating an asset."""

    pass


class AssetUpdate(BaseModel):
    """Schema for updating an asset."""

    quantity: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    purchase_price: Optional[Decimal] = None


class Asset(AssetBase):
    """Asset schema with database fields."""

    id: int
    portfolio_id: int
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


class BrokerConfigResponse(BrokerConfigBase):
    """Schema for broker configuration response."""

    id: int
    user_id: int
    is_active: bool
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


class BrokerTransactionsSyncResponse(BaseModel):
    """Schema for broker transactions sync response."""

    success: bool
    message: str
    transactions_count: int = 0
    transactions_imported: int = 0
