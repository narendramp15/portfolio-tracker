"""Transactions API endpoints."""

import csv
from decimal import Decimal
from io import StringIO
from typing import Optional

from fastapi import (APIRouter, Depends, File, HTTPException, Query,
                     UploadFile, status)
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from portfolio_tracker import models, schemas
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import (check_export_limit, get_current_user,
                                    log_export)
from portfolio_tracker.models import UserModel
from portfolio_tracker.services.csv_import import parse_csv

router = APIRouter()


def get_available_quantity(db: Session, portfolio_id: int, asset_id: int) -> Decimal:
    """
    Calculate available quantity for an asset based on transactions.
    This is the source of truth, not the assets table.
    """
    buy_sum = (
        db.query(func.sum(models.TransactionModel.quantity))
        .filter(
            models.TransactionModel.portfolio_id == portfolio_id,
            models.TransactionModel.asset_id == asset_id,
            models.TransactionModel.type == 'buy'
        )
        .scalar() or Decimal('0')
    )
    
    sell_sum = (
        db.query(func.sum(models.TransactionModel.quantity))
        .filter(
            models.TransactionModel.portfolio_id == portfolio_id,
            models.TransactionModel.asset_id == asset_id,
            models.TransactionModel.type == 'sell'
        )
        .scalar() or Decimal('0')
    )
    
    return buy_sum - sell_sum


@router.get("/available/{portfolio_id}/{asset_id}")
async def get_asset_available_quantity(
    portfolio_id: int,
    asset_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get available quantity for an asset (for sell validation)."""
    # Verify portfolio ownership
    portfolio = db.query(models.PortfolioModel).filter(
        models.PortfolioModel.id == portfolio_id,
        models.PortfolioModel.user_id == user.id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Verify asset exists
    asset = db.query(models.AssetModel).filter(
        models.AssetModel.id == asset_id,
        models.AssetModel.portfolio_id == portfolio_id
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    available_qty = get_available_quantity(db, portfolio_id, asset_id)
    
    return {
        "asset_id": asset_id,
        "symbol": asset.symbol,
        "available_quantity": float(available_qty),
        "display_quantity": float(asset.quantity)  # From assets table for display
    }


@router.get("/export")
async def export_all_transactions_csv(
    user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Export all transactions across all portfolios to CSV."""
    # Enforce monthly export quota for free-tier users
    check_export_limit(user, db)

    transactions = (
        db.query(models.TransactionModel)
        .join(models.PortfolioModel, models.TransactionModel.portfolio_id == models.PortfolioModel.id)
        .filter(models.PortfolioModel.user_id == user.id)
        .order_by(models.TransactionModel.transaction_date.desc())
        .all()
    )
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Date',
        'Portfolio',
        'Symbol',
        'Asset Name',
        'Type',
        'Quantity',
        'Price per Unit (₹)',
        'Total Value (₹)',
        'Notes'
    ])
    
    # Write data rows
    for t in transactions:
        quantity = float(t.quantity)
        price = float(t.price)
        total_value = quantity * price
        
        writer.writerow([
            t.transaction_date.strftime('%Y-%m-%d'),
            t.portfolio.name if t.portfolio else 'Unknown',
            t.asset.symbol if t.asset else 'N/A',
            t.asset.name if t.asset else 'Unknown',
            t.type.upper(),
            quantity,
            price,
            round(total_value, 2),
            t.notes or ''
        ])
    
    output.seek(0)

    # Record export for rate-limiting
    log_export(user, "transactions", db)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=all_transactions.csv"
        }
    )


@router.get("/")
async def list_all_transactions(
    user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List all transactions across all portfolios."""
    try:
        transactions = (
            db.query(models.TransactionModel)
            .join(models.PortfolioModel, models.TransactionModel.portfolio_id == models.PortfolioModel.id)
            .filter(models.PortfolioModel.user_id == user.id)
            .all()
        )
        result = []
        for t in transactions:
            result.append({
                "id": t.id,
                "portfolio_id": t.portfolio_id,
                "portfolio_name": t.portfolio.name if t.portfolio else "Unknown",
                "asset_id": t.asset_id,
                "asset_name": t.asset.name if t.asset else "Unknown",
                "asset_symbol": t.asset.symbol if t.asset else "N/A",
                "transaction_type": t.type,
                "quantity": float(t.quantity),
                "price_per_unit": float(t.price),
                "notes": t.notes,
                "transaction_date": t.transaction_date.isoformat(),
                "created_at": t.created_at
            })
        return result
    except Exception as e:
        print(f"Error loading transactions: {e}")
        return []


# ---------------------------------------------------------------------------
# CSV Import  (must be declared BEFORE /{portfolio_id} routes so the literal
# path segments are matched first — Starlette routes in definition order)
# ---------------------------------------------------------------------------

_MAX_CSV_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/import-csv")
async def import_transactions_csv(
    file: UploadFile = File(...),
    portfolio_id: int = Query(..., description="Target portfolio"),
    broker: Optional[str] = Query(
        default=None,
        description="Broker hint: zerodha, groww, fivepaisa, generic. Auto-detected if omitted.",
    ),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import transactions from a CSV file.

    Supported formats:
    - **Zerodha** tradebook (Console → Trade book → Download)
    - **Groww** trade report
    - **5Paisa** trade report
    - **Generic / manual** CSV with columns: symbol, type, quantity, price, date, notes

    The format is auto-detected from headers unless `broker` is specified.
    """
    # Validate portfolio ownership
    portfolio = (
        db.query(models.PortfolioModel)
        .filter(
            models.PortfolioModel.id == portfolio_id,
            models.PortfolioModel.user_id == user.id,
        )
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Validate file type
    if file.content_type and file.content_type not in (
        "text/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
        "text/plain",
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a CSV file.",
        )

    raw = await file.read()
    if len(raw) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB).")

    result = parse_csv(raw, broker_hint=broker)

    if result.errors and not result.rows:
        raise HTTPException(
            status_code=400,
            detail=f"CSV parsing failed: {'; '.join(result.errors[:5])}",
        )

    imported = 0
    skipped_dupes = 0
    from datetime import datetime as _dt
    from datetime import timezone as _tz

    for row in result.rows:
        symbol = row["symbol"]
        tx_type = row["type"]
        quantity = row["quantity"]
        price = row["price"]
        tx_date = row["date"] or _dt.now(_tz.utc)
        notes = row.get("notes", "")

        # Find or create asset in this portfolio
        asset = (
            db.query(models.AssetModel)
            .filter(
                models.AssetModel.portfolio_id == portfolio_id,
                models.AssetModel.symbol == symbol,
            )
            .first()
        )
        if not asset:
            asset = models.AssetModel(
                portfolio_id=portfolio_id,
                symbol=symbol,
                name=symbol,
                quantity=Decimal("0"),
                current_price=price,
                purchase_price=price,
            )
            db.add(asset)
            db.flush()  # get asset.id without committing

        # Duplicate check: same portfolio, asset, type, qty, price, date
        existing = (
            db.query(models.TransactionModel)
            .filter(
                models.TransactionModel.portfolio_id == portfolio_id,
                models.TransactionModel.asset_id == asset.id,
                models.TransactionModel.type == tx_type,
                models.TransactionModel.quantity == quantity,
                models.TransactionModel.price == price,
                models.TransactionModel.transaction_date == tx_date,
            )
            .first()
        )
        if existing:
            skipped_dupes += 1
            continue

        tx = models.TransactionModel(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            type=tx_type,
            quantity=quantity,
            price=price,
            notes=notes,
            transaction_date=tx_date,
        )
        db.add(tx)
        imported += 1

    if imported:
        db.commit()

    return {
        "success": True,
        "detected_format": result.detected_format,
        "total_rows": len(result.rows),
        "imported": imported,
        "skipped_duplicates": skipped_dupes,
        "skipped_invalid": result.skipped,
        "errors": result.errors[:10],
    }


@router.get("/import-csv/sample")
async def get_sample_csv():
    """Download a sample CSV template for manual transaction import."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["symbol", "type", "quantity", "price", "date", "notes"])
    writer.writerow(["RELIANCE", "buy", "10", "2450.50", "2025-01-15", "Initial purchase"])
    writer.writerow(["TCS", "buy", "5", "3800.00", "2025-02-10", "Added on dip"])
    writer.writerow(["INFY", "sell", "8", "1520.75", "2025-03-01", "Partial exit"])
    writer.writerow(["HDFCBANK", "buy", "15", "1650.00", "2025-03-15", ""])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=quantleap_import_template.csv"},
    )


@router.get("/{portfolio_id}")
async def list_transactions(
    portfolio_id: int, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List all transactions for a portfolio."""
    portfolio = db.query(models.PortfolioModel).filter(models.PortfolioModel.id == portfolio_id).first()
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    txs = (
        db.query(models.TransactionModel)
        .filter(models.TransactionModel.portfolio_id == portfolio_id)
        .order_by(models.TransactionModel.transaction_date.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "portfolio_id": t.portfolio_id,
            "portfolio_name": t.portfolio.name if t.portfolio else "Unknown",
            "asset_id": t.asset_id,
            "asset_name": t.asset.name if t.asset else "Unknown",
            "asset_symbol": t.asset.symbol if t.asset else "N/A",
            "transaction_type": t.type,
            "quantity": float(t.quantity),
            "price_per_unit": float(t.price),
            "notes": t.notes,
            "transaction_date": t.transaction_date.isoformat(),
            "created_at": t.created_at,
        }
        for t in txs
    ]


@router.post("/{portfolio_id}")
async def create_transaction(
    portfolio_id: int,
    transaction: schemas.TransactionCreate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new transaction."""
    portfolio = db.query(models.PortfolioModel).filter(models.PortfolioModel.id == portfolio_id).first()
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    asset = (
        db.query(models.AssetModel)
        .filter(models.AssetModel.id == transaction.asset_id, models.AssetModel.portfolio_id == portfolio_id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Validate sell transaction - compute available from transactions
    if transaction.type.lower() == 'sell':
        available_qty = get_available_quantity(db, portfolio_id, transaction.asset_id)
        if available_qty < transaction.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient quantity to sell. Available: {available_qty}, Requested: {transaction.quantity}"
            )

    # Create the transaction
    tx = models.TransactionModel(
        portfolio_id=portfolio_id,
        asset_id=transaction.asset_id,
        type=transaction.type.lower(),
        quantity=transaction.quantity,
        price=transaction.price,
        notes=transaction.notes,
    )
    db.add(tx)

    # Update asset quantities and average price
    if transaction.type.lower() == 'buy':
        # For buy: increase quantity, recalculate average price
        total_value = (asset.quantity * asset.purchase_price) + (transaction.quantity * transaction.price)
        total_quantity = asset.quantity + transaction.quantity
        new_avg_price = total_value / total_quantity if total_quantity > 0 else transaction.price
        
        asset.quantity = total_quantity
        asset.purchase_price = new_avg_price
    elif transaction.type.lower() == 'sell':
        # For sell: decrease quantity
        asset.quantity = asset.quantity - transaction.quantity
        
        # If quantity becomes 0, we could delete the asset or keep it
        # For now, keep it but maybe set quantity to 0

    db.commit()
    db.refresh(tx)

    return {
        "id": tx.id,
        "portfolio_id": tx.portfolio_id,
        "portfolio_name": portfolio.name,
        "asset_id": tx.asset_id,
        "asset_name": asset.name,
        "asset_symbol": asset.symbol,
        "transaction_type": tx.type,
        "quantity": float(tx.quantity),
        "price_per_unit": float(tx.price),
        "notes": tx.notes,
        "transaction_date": tx.transaction_date.isoformat(),
        "created_at": tx.created_at,
    }


@router.get("/{portfolio_id}/{transaction_id}")
async def get_transaction(
    portfolio_id: int,
    transaction_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific transaction."""
    portfolio = db.query(models.PortfolioModel).filter(models.PortfolioModel.id == portfolio_id).first()
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    tx = (
        db.query(models.TransactionModel)
        .filter(models.TransactionModel.id == transaction_id, models.TransactionModel.portfolio_id == portfolio_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "id": tx.id,
        "portfolio_id": tx.portfolio_id,
        "portfolio_name": portfolio.name,
        "asset_id": tx.asset_id,
        "asset_name": tx.asset.name if tx.asset else "Unknown",
        "asset_symbol": tx.asset.symbol if tx.asset else "N/A",
        "transaction_type": tx.type,
        "quantity": float(tx.quantity),
        "price_per_unit": float(tx.price),
        "notes": tx.notes,
        "transaction_date": tx.transaction_date.isoformat(),
        "created_at": tx.created_at,
    }


@router.delete("/{portfolio_id}/{transaction_id}")
async def delete_transaction(
    portfolio_id: int,
    transaction_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a transaction."""
    portfolio = db.query(models.PortfolioModel).filter(models.PortfolioModel.id == portfolio_id).first()
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    tx = (
        db.query(models.TransactionModel)
        .filter(models.TransactionModel.id == transaction_id, models.TransactionModel.portfolio_id == portfolio_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Reverse the asset changes
    asset = tx.asset
    if tx.type == 'buy':
        # Reverse buy: decrease quantity
        if asset.quantity < tx.quantity:
            raise HTTPException(status_code=400, detail="Cannot delete transaction: insufficient quantity")
        asset.quantity = asset.quantity - tx.quantity
    elif tx.type == 'sell':
        # Reverse sell: increase quantity
        asset.quantity = asset.quantity + tx.quantity

    # Note: Reversing average price calculation is complex and not implemented
    # In a production system, you'd need to recalculate from all transactions

    db.delete(tx)
    db.commit()

    return {"message": "Transaction deleted successfully"}


# (CSV import routes moved above /{portfolio_id} — see top of file)
