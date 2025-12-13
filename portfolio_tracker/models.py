"""Data models for portfolio tracking."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        Numeric, String)
from sqlalchemy.orm import relationship

from portfolio_tracker.database import Base


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    """Convert incoming numeric-like values to Decimal for precise arithmetic."""
    return value if isinstance(value, Decimal) else Decimal(str(value))


# SQLAlchemy ORM Models
class UserModel(Base):
    """SQLAlchemy model for User."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    portfolios = relationship("PortfolioModel", back_populates="owner", cascade="all, delete-orphan")


class PortfolioModel(Base):
    """SQLAlchemy model for Portfolio."""

    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), index=True, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owner = relationship("UserModel", back_populates="portfolios")
    assets = relationship("AssetModel", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("TransactionModel", back_populates="portfolio", cascade="all, delete-orphan")


class AssetModel(Base):
    """SQLAlchemy model for Asset."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    current_price = Column(Numeric(20, 8), nullable=False)
    purchase_price = Column(Numeric(20, 8), nullable=False)
    purchase_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    portfolio = relationship("PortfolioModel", back_populates="assets")
    transactions = relationship("TransactionModel", back_populates="asset", cascade="all, delete-orphan")


class TransactionModel(Base):
    """SQLAlchemy model for Transaction."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    type = Column(String(10), nullable=False)  # 'buy' or 'sell'
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    notes = Column(String(500), nullable=True)
    transaction_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    portfolio = relationship("PortfolioModel", back_populates="transactions")
    asset = relationship("AssetModel", back_populates="transactions")


class BrokerTemplateModel(Base):
    """SQLAlchemy model for Broker API Configuration Template."""

    __tablename__ = "broker_templates"

    id = Column(Integer, primary_key=True, index=True)
    broker_name = Column(String(50), unique=True, index=True, nullable=False)  # 'zerodha', 'angel', '5paisa'
    display_name = Column(String(100), nullable=False)  # Display name for UI
    api_key_required = Column(Boolean, default=False, nullable=False)  # Whether API key is required
    api_secret_required = Column(Boolean, default=False, nullable=False)  # Whether API secret is required
    oauth_enabled = Column(Boolean, default=False, nullable=False)  # Whether OAuth is used
    config_fields = Column(String(500), nullable=True)  # JSON of required config fields
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class BrokerConfigModel(Base):
    """SQLAlchemy model for Broker Configuration."""

    __tablename__ = "broker_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    broker_name = Column(String(50), nullable=False)  # 'zerodha', 'angel', '5paisa', etc.
    broker_user_id = Column(String(100), nullable=False)  # Broker's user identifier
    api_key = Column(String(500), nullable=True)  # Encrypted API key
    api_secret = Column(String(500), nullable=True)  # Encrypted API secret
    access_token = Column(String(500), nullable=True)  # Encrypted access token
    refresh_token = Column(String(500), nullable=True)  # Encrypted refresh token
    is_active = Column(Boolean, default=True, nullable=False)
    last_synced = Column(DateTime, nullable=True)  # Last time holdings were synced
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owner = relationship("UserModel")


# Dataclass Models (for core business logic)
@dataclass
class Asset:
    """Represents a single asset in a portfolio."""

    symbol: str
    name: str
    quantity: Decimal = Decimal("0")
    current_price: Decimal = Decimal("0")
    purchase_price: Decimal = Decimal("0")
    purchase_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get_current_value(self) -> Decimal:
        """Get the current total value of the asset."""
        return self.quantity * self.current_price

    def get_cost_basis(self) -> Decimal:
        """Get the total cost basis of the asset."""
        return self.quantity * self.purchase_price

    def get_gain_loss(self) -> Decimal:
        """Get the unrealized gain or loss."""
        return self.get_current_value() - self.get_cost_basis()

    def get_gain_loss_percent(self) -> Decimal:
        """Get the unrealized gain or loss as a percentage."""
        cost_basis = self.get_cost_basis()
        if cost_basis == 0:
            return Decimal("0")
        return (self.get_gain_loss() / cost_basis) * Decimal("100")


@dataclass
class Portfolio:
    """Represents an investment portfolio containing multiple assets."""

    name: str
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    assets: dict[str, Asset] = field(default_factory=dict)

    def add_asset(
        self,
        symbol: str,
        name: str,
        quantity: Decimal | float | int,
        current_price: Decimal | float | int = Decimal("0"),
        purchase_price: Decimal | float | int = Decimal("0"),
    ) -> Asset:
        """
        Add or update an asset in the portfolio.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            name: Asset name
            quantity: Number of shares
            current_price: Current price per share
            purchase_price: Purchase price per share

        Returns:
            The Asset object
        """
        new_quantity = _to_decimal(quantity)
        new_current_price = _to_decimal(current_price)
        new_purchase_price = _to_decimal(purchase_price)

        if symbol in self.assets:
            # Merge with existing position to preserve running totals.
            existing = self.assets[symbol]
            combined_quantity = existing.quantity + new_quantity
            if combined_quantity == 0:
                # Avoid division by zero; treat as reset position.
                combined_purchase_price = new_purchase_price
            else:
                total_cost = existing.get_cost_basis() + (new_quantity * new_purchase_price)
                combined_purchase_price = total_cost / combined_quantity

            asset = Asset(
                symbol=symbol,
                name=name,
                quantity=combined_quantity,
                current_price=new_current_price,
                purchase_price=combined_purchase_price,
                purchase_date=datetime.now(timezone.utc),
            )
        else:
            asset = Asset(
                symbol=symbol,
                name=name,
                quantity=new_quantity,
                current_price=new_current_price,
                purchase_price=new_purchase_price,
            )

        self.assets[symbol] = asset
        return asset

    def remove_asset(self, symbol: str) -> bool:
        """
        Remove an asset from the portfolio.

        Args:
            symbol: Stock symbol to remove

        Returns:
            True if removed, False if not found
        """
        if symbol in self.assets:
            del self.assets[symbol]
            return True
        return False

    def get_asset(self, symbol: str) -> Asset | None:
        """
        Get an asset by symbol.

        Args:
            symbol: Stock symbol

        Returns:
            The Asset object or None if not found
        """
        return self.assets.get(symbol)

    def get_all_assets(self) -> list[Asset]:
        """
        Get all assets in the portfolio.

        Returns:
            List of all assets
        """
        return list(self.assets.values())

    def get_total_value(self) -> Decimal:
        """Get the total current value of the portfolio."""
        return sum((asset.get_current_value() for asset in self.assets.values()), Decimal("0"))

    def get_total_cost_basis(self) -> Decimal:
        """Get the total cost basis of the portfolio."""
        return sum((asset.get_cost_basis() for asset in self.assets.values()), Decimal("0"))

    def get_total_gain_loss(self) -> Decimal:
        """Get the total unrealized gain or loss."""
        return self.get_total_value() - self.get_total_cost_basis()

    def get_total_gain_loss_percent(self) -> Decimal:
        """Get the total unrealized gain or loss as a percentage."""
        cost_basis = self.get_total_cost_basis()
        if cost_basis == 0:
            return Decimal("0")
        return (self.get_total_gain_loss() / cost_basis) * Decimal("100")
