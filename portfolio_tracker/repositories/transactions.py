"""Transaction persistence."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from portfolio_tracker.models import TransactionModel


def get_transaction_by_id(db: Session, transaction_id: int):
    """Get a transaction by ID."""
    return db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()


def get_portfolio_transactions(db: Session, portfolio_id: int, skip: int = 0, limit: int = 100):
    """Get all transactions for a portfolio."""
    return db.query(TransactionModel).filter(
        TransactionModel.portfolio_id == portfolio_id
    ).order_by(TransactionModel.transaction_date.desc()).offset(skip).limit(limit).all()


def create_transaction(
    db: Session,
    portfolio_id: int,
    asset_id: int,
    type: Optional[str] = None,
    quantity: Decimal = Decimal("0"),
    price: Decimal = Decimal("0"),
    transaction_date: Optional[datetime] = None,
    notes: Optional[str] = None,
    # Legacy parameter alias
    transaction_type: Optional[str] = None,
):
    """
    Create a new transaction.

    Supports both 'type' and 'transaction_type' parameters for backwards compatibility.
    """
    # Handle legacy parameter
    if transaction_type and not type:
        type = transaction_type

    transaction = TransactionModel(
        portfolio_id=portfolio_id,
        asset_id=asset_id,
        type=type,
        quantity=quantity,
        price=price,
        transaction_date=transaction_date or datetime.now(timezone.utc),
        notes=notes,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def find_duplicate_transaction(
    db: Session,
    portfolio_id: int,
    asset_id: int,
    tx_type: str,
    quantity,
    price,
    transaction_date: datetime,
):
    """Find an existing transaction matching all key fields (broker-sync dedupe)."""
    return (
        db.query(TransactionModel)
        .filter(
            TransactionModel.portfolio_id == portfolio_id,
            TransactionModel.asset_id == asset_id,
            TransactionModel.type == tx_type,
            TransactionModel.quantity == quantity,
            TransactionModel.price == price,
            TransactionModel.transaction_date == transaction_date,
        )
        .first()
    )


def delete_transaction(db: Session, transaction_id: int):
    """Delete a transaction."""
    transaction = get_transaction_by_id(db, transaction_id)
    if not transaction:
        return False
    db.delete(transaction)
    db.commit()
    return True
