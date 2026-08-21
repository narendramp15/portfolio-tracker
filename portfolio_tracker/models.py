"""Data models for portfolio tracking."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Index, Integer,
                        Numeric, String, Text, UniqueConstraint)
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

    # Subscription fields
    subscription_tier = Column(String(20), default="free", nullable=False, server_default="free")
    subscription_status = Column(String(20), default="active", nullable=False, server_default="active")
    subscription_expires_at = Column(DateTime, nullable=True)
    razorpay_subscription_id = Column(String(255), nullable=True)
    razorpay_customer_id = Column(String(255), nullable=True)

    # Options Analyzer fields
    options_tier = Column(String(20), default="free", nullable=False, server_default="free")
    options_starter_payment_id = Column(String(100), nullable=True, unique=True)  # Razorpay pay_ID used for Starter activation — prevents reuse
    options_credits = Column(Integer, default=5, nullable=False, server_default="5")
    options_analyses_today = Column(Integer, default=0, nullable=False, server_default="0")
    options_analyses_date = Column(String(10), nullable=True)   # YYYY-MM-DD
    options_ai_cost_month = Column(Numeric(10, 4), default=Decimal("0"), nullable=False, server_default="0")
    options_ai_cost_month_key = Column(String(7), nullable=True)  # YYYY-MM

    # Relationships
    portfolios = relationship("PortfolioModel", back_populates="owner", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetTokenModel", back_populates="user", cascade="all, delete-orphan")
    export_logs = relationship("ExportLogModel", back_populates="user", cascade="all, delete-orphan")
    options_analysis_logs = relationship("OptionsAnalysisLogModel", back_populates="user", cascade="all, delete-orphan")
    mf_holdings = relationship("MutualFundHoldingModel", back_populates="owner", cascade="all, delete-orphan")


class PasswordResetTokenModel(Base):
    """SQLAlchemy model for Password Reset Tokens."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("UserModel", back_populates="password_reset_tokens")


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
    symbol = Column(String(20), nullable=False, index=True)  # Increased to 20 to support .NS/.BO suffixes
    # Real instrument identity. Symbols are a display and market-data concern:
    # they get renamed and differ per exchange and per broker, which is why the
    # same security can currently exist as two asset rows.
    isin = Column(String(12), nullable=True, index=True)
    # Which demat holds this. Needed for account-wise FIFO.
    demat_account = Column(String(60), nullable=True)
    name = Column(String(100), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    current_price = Column(Numeric(20, 8), nullable=False)
    previous_close = Column(Numeric(20, 8), nullable=True)  # Previous day's closing price for today's change
    purchase_price = Column(Numeric(20, 8), nullable=False)
    purchase_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_price_update = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)
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

    # Transaction charges, kept separate because they are treated differently
    # under Indian capital gains rules: brokerage and other transfer expenses
    # are deductible against the gain, STT explicitly is not (Sec 48).
    brokerage = Column(Numeric(20, 4), nullable=True, default=Decimal("0"), server_default="0")
    stt = Column(Numeric(20, 4), nullable=True, default=Decimal("0"), server_default="0")
    other_charges = Column(  # stamp duty, exchange turnover, SEBI fee, GST
        Numeric(20, 4), nullable=True, default=Decimal("0"), server_default="0"
    )
    transaction_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    portfolio = relationship("PortfolioModel", back_populates="transactions")
    asset = relationship("AssetModel", back_populates="transactions")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_transactions_portfolio_asset', 'portfolio_id', 'asset_id'),
        Index('ix_transactions_portfolio_type', 'portfolio_id', 'type'),
        Index('ix_transactions_asset_type', 'asset_id', 'type'),
        Index('ix_transactions_date', 'transaction_date'),
    )


class PortfolioEventModel(Base):
    """Append-only ledger of everything that happened to an instrument.

    Positions, capital gains, XIRR and dividend attribution are all folded from
    this table rather than stored, so they cannot drift apart. Rows are never
    updated or deleted: a correction is a new, compensating event, which is
    what keeps a tax figure that has already been filed reproducible.

    Identity is the ISIN, not the symbol - tickers get renamed, differ by
    exchange and differ again by broker.
    """

    __tablename__ = "portfolio_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True, index=True)

    # Instrument key: a validated ISIN where known, otherwise a marked
    # placeholder ("SYM:RELIANCE"). Wider than an ISIN's 12 characters because
    # of those placeholders - at 12 the database silently truncated them.
    isin = Column(String(24), nullable=False, index=True)
    symbol = Column(String(30), nullable=True)  # display only, never identity

    # Which demat account. Load-bearing: FIFO is applied account-wise for
    # dematerialised securities (CBDT Circular 768), so lots must not pool.
    account = Column(String(60), nullable=False, server_default="")

    event_type = Column(String(20), nullable=False, index=True)
    trade_date = Column(DateTime, nullable=False, index=True)

    quantity = Column(Numeric(20, 8), nullable=False, server_default="0")
    price = Column(Numeric(20, 8), nullable=False, server_default="0")

    brokerage = Column(Numeric(20, 4), nullable=True, server_default="0")
    stt = Column(Numeric(20, 4), nullable=True, server_default="0")  # not deductible
    other_charges = Column(Numeric(20, 4), nullable=True, server_default="0")

    ratio = Column(Numeric(20, 8), nullable=True)   # corporate action ratio
    amount = Column(Numeric(20, 4), nullable=True)  # dividend cash

    # Provenance. The same trade legitimately arrives from more than one place
    # (a depository statement knows the movement, a tradebook knows the price),
    # so ingestion is idempotent on (source, source_ref).
    source = Column(String(60), nullable=False, server_default="")
    source_ref = Column(String(64), nullable=False, server_default="")

    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        # Re-importing the same statement must be a no-op.
        UniqueConstraint("user_id", "source", "source_ref", name="uix_event_source_ref"),
        # The fold's access pattern: one user's events for one instrument,
        # in one account, in date order.
        Index("ix_events_user_isin_account_date", "user_id", "isin", "account", "trade_date"),
    )


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
    extra_config = Column(Text, nullable=True)  # JSON string for broker-specific config (encrypted)
    is_active = Column(Boolean, default=True, nullable=False)
    last_synced = Column(DateTime, nullable=True)  # Last time holdings were synced
    consent_given = Column(Boolean, default=False, nullable=False)  # Whether user consented to data processing
    consent_timestamp = Column(DateTime, nullable=True)  # When consent was given
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owner = relationship("UserModel")

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('ix_broker_configs_user_broker', 'user_id', 'broker_name'),
        Index('ix_broker_configs_active', 'user_id', 'is_active'),
    )


class PriceHistoryModel(Base):
    """
    Lean price history table - stores only recent daily closes.
    
    Storage strategy for free tier:
    - Only stores last 90 days of data per symbol
    - Only tracks symbols that users actually hold
    - Older data fetched on-demand from yfinance (free API)
    - ~40 bytes per row = 72KB per user with 20 stocks over 90 days
    """

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # e.g., RELIANCE.NS
    date = Column(DateTime, nullable=False)  # Trading date (DATE precision)
    close = Column(Numeric(12, 2), nullable=False)  # Closing price (2 decimal places enough for INR)
    
    # Composite unique constraint and index for efficient queries
    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uix_symbol_date'),
        Index('ix_price_history_symbol_date', 'symbol', 'date'),
    )


class ExportLogModel(Base):
    """Tracks CSV export usage per user for free-tier rate limiting."""

    __tablename__ = "export_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    export_type = Column(String(50), nullable=False)  # 'transactions' | 'tax_report' | 'holdings'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("UserModel", back_populates="export_logs")

    __table_args__ = (
        Index('ix_export_logs_user_month', 'user_id', 'created_at'),
    )


class OptionsAnalysisLogModel(Base):
    """Audit log for every Options Analyzer AI call. Never stores prompt content."""

    __tablename__ = "options_analysis_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tier = Column(String(20), nullable=False)
    analysis_type = Column(String(20), nullable=False)  # quick | full | advanced
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    cache_read_tokens = Column(Integer, default=0, nullable=False)
    ai_cost_inr = Column(Numeric(10, 4), default=Decimal("0"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("UserModel", back_populates="options_analysis_logs")

    __table_args__ = (
        Index('ix_options_logs_user_id', 'user_id'),
    )


class ProcessedPaymentModel(Base):
    """Records every Razorpay payment already credited, to block replay/reuse.

    The UNIQUE constraint on ``payment_id`` is the backstop that makes credit
    fulfilment idempotent: a repeated verify call for the same payment fails the
    insert instead of granting credits again.
    """

    __tablename__ = "processed_payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_id = Column(String(100), nullable=False, unique=True)  # Razorpay pay_ID
    order_id = Column(String(100), nullable=True)
    purpose = Column(String(40), nullable=False)  # e.g. "options_credits"
    pack_id = Column(String(40), nullable=True)
    amount_paise = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class MutualFundHoldingModel(Base):
    """Mutual fund folios imported from CAMS/KFintech CAS statements."""

    __tablename__ = "mf_holdings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    folio_number = Column(String(50), nullable=False)
    scheme_name = Column(String(300), nullable=False)
    amc = Column(String(150), nullable=True)           # Fund house / AMC name
    isin = Column(String(20), nullable=True, index=True)
    units = Column(Numeric(20, 4), nullable=False, default=Decimal("0"))
    nav = Column(Numeric(20, 4), nullable=True)        # Latest NAV (from CAS or refreshed)
    cost_value = Column(Numeric(20, 4), nullable=True) # Total invested (cost)
    current_value = Column(Numeric(20, 4), nullable=True)
    category = Column(String(100), nullable=True)      # Equity, Debt, Hybrid, …
    registrar = Column(String(20), nullable=True)      # CAMS / KFintech
    cas_import_date = Column(DateTime, nullable=True)   # When this CAS was generated
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owner = relationship("UserModel", back_populates="mf_holdings")
    mf_transactions = relationship("MutualFundTransactionModel", back_populates="holding", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_mf_holdings_user_folio', 'user_id', 'folio_number'),
        UniqueConstraint('user_id', 'folio_number', 'scheme_name', name='uix_user_folio_scheme'),
    )


class MutualFundTransactionModel(Base):
    """Individual MF transactions (SIP / purchase / redemption) from CAS."""

    __tablename__ = "mf_transactions"

    id = Column(Integer, primary_key=True, index=True)
    holding_id = Column(Integer, ForeignKey("mf_holdings.id"), nullable=False, index=True)
    type = Column(String(30), nullable=False)          # purchase / redemption / switch_in / switch_out / dividend
    amount = Column(Numeric(20, 4), nullable=True)     # ₹ value of the transaction
    units = Column(Numeric(20, 4), nullable=True)
    nav = Column(Numeric(20, 4), nullable=True)
    transaction_date = Column(DateTime, nullable=False)
    description = Column(String(300), nullable=True)    # Original CAS description line
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    holding = relationship("MutualFundHoldingModel", back_populates="mf_transactions")

    __table_args__ = (
        Index('ix_mf_tx_holding_date', 'holding_id', 'transaction_date'),
    )


class StockThesisCacheModel(Base):
    """Server-side cache for AI-generated per-stock investment theses (Pro feature)."""

    __tablename__ = "stock_thesis_cache"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)  # e.g. RELIANCE.NS
    thesis = Column(Text, nullable=False)
    generated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('ix_stock_thesis_symbol', 'symbol'),
    )


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
