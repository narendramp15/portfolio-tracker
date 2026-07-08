"""Portfolio synchronization from broker feeds.

The holdings-upsert loop here replaces five near-identical copies that
previously lived inline in the broker router (Zerodha, Angel, 5Paisa, Dhan,
Groww). All brokers return ``schemas.BrokerHolding``; the persistence logic
is broker-agnostic.

Raises ``ValueError`` for domain errors; routers translate to HTTP statuses.
"""

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.orm import Session

from portfolio_tracker.models import AssetModel, TransactionModel
from portfolio_tracker.repositories import assets as assets_repo
from portfolio_tracker.repositories import portfolios as portfolios_repo
from portfolio_tracker.repositories import transactions as transactions_repo
from portfolio_tracker.schemas import BrokerHolding
from portfolio_tracker.services.symbol_mapper import symbol_mapper

logger = logging.getLogger(__name__)


def require_portfolio(db: Session, user_id: int, portfolio_id: int):
    """Return the portfolio if it exists and belongs to the user, else raise."""
    portfolio = portfolios_repo.get_portfolio_by_id(db, portfolio_id)
    if not portfolio or portfolio.user_id != user_id:
        raise ValueError("Portfolio not found")
    return portfolio


def upsert_holdings(
    db: Session,
    portfolio_id: int,
    holdings: Sequence[BrokerHolding],
    exchange: str = "NSE",
) -> int:
    """Create or update portfolio assets from broker holdings.

    Symbols are normalized to Yahoo Finance format so positions from
    different brokers merge into one asset row. Returns the number of
    newly created assets.
    """
    assets_imported = 0
    for holding in holdings:
        normalized_symbol = symbol_mapper.normalize_broker_symbol(
            symbol=holding.symbol,
            exchange=exchange,
            isin=holding.isin,
        )
        company_name = symbol_mapper.get_company_name(normalized_symbol) or holding.symbol

        asset = assets_repo.get_asset_by_symbol(db, portfolio_id, normalized_symbol)
        if not asset:
            asset = AssetModel(
                portfolio_id=portfolio_id,
                symbol=normalized_symbol,
                name=company_name,
                quantity=holding.quantity,
                current_price=holding.current_price,
                purchase_price=holding.average_price,
            )
            db.add(asset)
            assets_imported += 1
        else:
            asset.name = company_name  # update name in case it changed
            asset.quantity = holding.quantity
            asset.current_price = holding.current_price
            asset.purchase_price = holding.average_price

        db.commit()

    return assets_imported


def _parse_trade_timestamp(trade: dict) -> datetime:
    """Best-effort timestamp from a broker trade record, defaulting to now (UTC)."""
    ts = trade.get("exchange_timestamp") or trade.get("order_timestamp") or trade.get("trade_timestamp")
    tx_dt = None
    if isinstance(ts, datetime):
        tx_dt = ts
    elif isinstance(ts, str) and ts:
        try:
            tx_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            tx_dt = None
    if tx_dt is None:
        tx_dt = datetime.now(timezone.utc)
    if tx_dt.tzinfo is None:
        tx_dt = tx_dt.replace(tzinfo=timezone.utc)
    return tx_dt


def _normalize_trade_type(trade: dict) -> str | None:
    """Map a broker trade record to 'buy'/'sell', or None when unrecognized."""
    tx_type_raw = trade.get("transaction_type") or trade.get("trade_type") or ""
    tx_type = str(tx_type_raw).strip().lower()
    if tx_type in {"buy", "b"}:
        return "buy"
    if tx_type in {"sell", "s"}:
        return "sell"
    if str(tx_type_raw).upper() in {"BUY", "SELL"}:
        return str(tx_type_raw).lower()
    return None


def import_trades(
    db: Session,
    portfolio_id: int,
    trades: Sequence[dict],
    source_label: str = "Zerodha",
) -> int:
    """Import broker trade records as portfolio transactions, skipping duplicates.

    Returns the number of newly created transactions.
    """
    imported = 0
    for idx, trade in enumerate(trades):
        symbol = trade.get("tradingsymbol") or trade.get("symbol") or ""
        if not symbol:
            logger.debug(f"Trade {idx}: Skipping - no symbol found")
            continue

        tx_type = _normalize_trade_type(trade)
        if tx_type is None:
            logger.debug(f"Trade {idx} ({symbol}): Skipping - invalid transaction type")
            continue

        quantity = trade.get("quantity") or 0
        price = trade.get("average_price") or trade.get("price") or 0
        tx_dt = _parse_trade_timestamp(trade)

        # Ensure asset exists in the portfolio.
        asset = assets_repo.get_asset_by_symbol(db, portfolio_id, symbol)
        if not asset:
            asset = AssetModel(
                portfolio_id=portfolio_id,
                symbol=symbol,
                name=symbol,
                quantity=0,
                current_price=price or 0,
                purchase_price=price or 0,
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)

        # Avoid duplicates by matching key fields.
        existing = transactions_repo.find_duplicate_transaction(
            db, portfolio_id, asset.id, tx_type, quantity, price, tx_dt
        )
        if existing:
            logger.debug(f"Trade {idx}: {symbol} - duplicate, skipping")
            continue

        note = trade.get("trade_id")
        notes = f"Imported from {source_label} trade {note}" if note else f"Imported from {source_label}"

        tx = TransactionModel(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            type=tx_type,
            quantity=quantity,
            price=price,
            notes=notes,
            transaction_date=tx_dt,
        )
        db.add(tx)
        imported += 1

    if imported:
        db.commit()
        logger.info(f"Imported {imported}/{len(trades)} trades")

    return imported
