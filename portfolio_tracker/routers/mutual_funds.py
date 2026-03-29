"""Mutual fund endpoints — holdings, CAS import, manual CRUD."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from portfolio_tracker.deps import get_current_user, get_db
from portfolio_tracker.models import (MutualFundHoldingModel,
                                      MutualFundTransactionModel, UserModel)
from portfolio_tracker.services.cas_parser import parse_cas_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mutual-funds", tags=["mutual-funds"])


# ---------------------------------------------------------------------------
# List holdings
# ---------------------------------------------------------------------------


@router.get("/")
def list_mf_holdings(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all mutual fund holdings for the authenticated user."""
    holdings = (
        db.query(MutualFundHoldingModel)
        .filter(MutualFundHoldingModel.user_id == user.id)
        .order_by(MutualFundHoldingModel.amc, MutualFundHoldingModel.scheme_name)
        .all()
    )

    total_invested = Decimal("0")
    total_current = Decimal("0")

    items = []
    for h in holdings:
        cost = h.cost_value or Decimal("0")
        current = h.current_value or (h.units * (h.nav or Decimal("0")))
        total_invested += cost
        total_current += current

        items.append({
            "id": h.id,
            "folio_number": h.folio_number,
            "scheme_name": h.scheme_name,
            "amc": h.amc,
            "isin": h.isin,
            "units": float(h.units),
            "nav": float(h.nav) if h.nav else None,
            "cost_value": float(cost),
            "current_value": float(current),
            "gain_loss": float(current - cost),
            "gain_loss_pct": float(
                ((current - cost) / cost * 100) if cost > 0 else Decimal("0")
            ),
            "category": h.category,
            "registrar": h.registrar,
            "updated_at": h.updated_at.isoformat() if h.updated_at else None,
        })

    return {
        "holdings": items,
        "summary": {
            "total_invested": float(total_invested),
            "total_current": float(total_current),
            "total_gain_loss": float(total_current - total_invested),
            "total_gain_loss_pct": float(
                ((total_current - total_invested) / total_invested * 100)
                if total_invested > 0
                else Decimal("0")
            ),
            "fund_count": len(items),
        },
    }


# ---------------------------------------------------------------------------
# Holding detail + transactions
# ---------------------------------------------------------------------------


@router.get("/{holding_id}")
def get_mf_holding(
    holding_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a single MF holding with its transaction history."""
    holding = (
        db.query(MutualFundHoldingModel)
        .filter(MutualFundHoldingModel.id == holding_id, MutualFundHoldingModel.user_id == user.id)
        .first()
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Mutual fund holding not found")

    transactions = (
        db.query(MutualFundTransactionModel)
        .filter(MutualFundTransactionModel.holding_id == holding.id)
        .order_by(MutualFundTransactionModel.transaction_date.desc())
        .all()
    )

    cost = holding.cost_value or Decimal("0")
    current = holding.current_value or (holding.units * (holding.nav or Decimal("0")))

    return {
        "id": holding.id,
        "folio_number": holding.folio_number,
        "scheme_name": holding.scheme_name,
        "amc": holding.amc,
        "isin": holding.isin,
        "units": float(holding.units),
        "nav": float(holding.nav) if holding.nav else None,
        "cost_value": float(cost),
        "current_value": float(current),
        "gain_loss": float(current - cost),
        "category": holding.category,
        "registrar": holding.registrar,
        "transactions": [
            {
                "id": t.id,
                "type": t.type,
                "amount": float(t.amount) if t.amount else None,
                "units": float(t.units) if t.units else None,
                "nav": float(t.nav) if t.nav else None,
                "transaction_date": t.transaction_date.isoformat(),
                "description": t.description,
            }
            for t in transactions
        ],
    }


# ---------------------------------------------------------------------------
# CAS PDF import
# ---------------------------------------------------------------------------

_MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/import-cas")
async def import_cas_pdf(
    file: UploadFile = File(...),
    password: Optional[str] = Query(
        default=None,
        description="PDF password (usually PAN+DOB e.g. ABCDE1234F01011990)",
    ),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a CAMS or KFintech CAS PDF to import mutual fund holdings.

    - Auto-detects CAMS vs KFintech format.
    - Existing folios are **updated** (units, NAV, values); new folios are created.
    - Duplicate transactions (same date + description + amount) are skipped.
    - If the PDF is password-protected, pass the password as a query parameter.
    """
    if file.content_type and file.content_type not in (
        "application/pdf",
        "application/octet-stream",
    ):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    raw = await file.read()
    if len(raw) > _MAX_PDF_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB).")

    result = parse_cas_pdf(raw, password=password)

    if result.errors and not result.folios:
        raise HTTPException(
            status_code=400,
            detail="; ".join(result.errors[:5]),
        )

    folios_created = 0
    folios_updated = 0
    txns_imported = 0
    txns_skipped = 0

    for folio_data in result.folios:
        # Upsert holding
        existing = (
            db.query(MutualFundHoldingModel)
            .filter(
                MutualFundHoldingModel.user_id == user.id,
                MutualFundHoldingModel.folio_number == folio_data.folio_number,
                MutualFundHoldingModel.scheme_name == folio_data.scheme_name,
            )
            .first()
        )

        if existing:
            # Update with latest CAS data
            existing.units = folio_data.closing_units
            if folio_data.closing_nav is not None:
                existing.nav = folio_data.closing_nav
            if folio_data.cost_value is not None:
                existing.cost_value = folio_data.cost_value
            if folio_data.current_value is not None:
                existing.current_value = folio_data.current_value
            if folio_data.isin:
                existing.isin = folio_data.isin
            if folio_data.amc:
                existing.amc = folio_data.amc
            existing.registrar = folio_data.registrar or existing.registrar
            existing.cas_import_date = result.statement_to or datetime.now(timezone.utc)
            holding = existing
            folios_updated += 1
        else:
            holding = MutualFundHoldingModel(
                user_id=user.id,
                folio_number=folio_data.folio_number,
                scheme_name=folio_data.scheme_name,
                amc=folio_data.amc,
                isin=folio_data.isin,
                units=folio_data.closing_units,
                nav=folio_data.closing_nav,
                cost_value=folio_data.cost_value,
                current_value=folio_data.current_value,
                registrar=folio_data.registrar,
                cas_import_date=result.statement_to or datetime.now(timezone.utc),
            )
            db.add(holding)
            db.flush()
            folios_created += 1

        # Import transactions
        for tx in folio_data.transactions:
            # Duplicate check
            dup = (
                db.query(MutualFundTransactionModel)
                .filter(
                    MutualFundTransactionModel.holding_id == holding.id,
                    MutualFundTransactionModel.transaction_date == tx.date,
                    MutualFundTransactionModel.description == tx.description,
                    MutualFundTransactionModel.amount == tx.amount,
                )
                .first()
            )
            if dup:
                txns_skipped += 1
                continue

            db.add(MutualFundTransactionModel(
                holding_id=holding.id,
                type=tx.tx_type,
                amount=tx.amount,
                units=tx.units,
                nav=tx.nav,
                transaction_date=tx.date,
                description=tx.description,
            ))
            txns_imported += 1

    db.commit()

    return {
        "success": True,
        "registrar_detected": result.registrar or "Unknown",
        "statement_period": {
            "from": result.statement_from.isoformat() if result.statement_from else None,
            "to": result.statement_to.isoformat() if result.statement_to else None,
        },
        "folios_created": folios_created,
        "folios_updated": folios_updated,
        "transactions_imported": txns_imported,
        "transactions_skipped": txns_skipped,
        "total_folios_in_cas": len(result.folios),
        "warnings": result.errors[:10],
    }


# ---------------------------------------------------------------------------
# Delete a holding
# ---------------------------------------------------------------------------


@router.delete("/{holding_id}")
def delete_mf_holding(
    holding_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a mutual fund holding and all its transactions."""
    holding = (
        db.query(MutualFundHoldingModel)
        .filter(MutualFundHoldingModel.id == holding_id, MutualFundHoldingModel.user_id == user.id)
        .first()
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    db.delete(holding)
    db.commit()
    return {"message": "Holding deleted"}


# ---------------------------------------------------------------------------
# Manual add (for users without CAS)
# ---------------------------------------------------------------------------


@router.post("/manual")
def add_mf_holding_manual(
    scheme_name: str = Query(..., min_length=1, max_length=300),
    folio_number: str = Query(..., min_length=1, max_length=50),
    units: float = Query(..., gt=0),
    nav: Optional[float] = Query(default=None),
    cost_value: Optional[float] = Query(default=None),
    amc: Optional[str] = Query(default=None, max_length=150),
    isin: Optional[str] = Query(default=None, max_length=20),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually add a mutual fund holding (for users who don't have a CAS PDF)."""
    existing = (
        db.query(MutualFundHoldingModel)
        .filter(
            MutualFundHoldingModel.user_id == user.id,
            MutualFundHoldingModel.folio_number == folio_number,
            MutualFundHoldingModel.scheme_name == scheme_name,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="This folio + scheme already exists. Use CAS import to update, or delete and re-add.",
        )

    holding = MutualFundHoldingModel(
        user_id=user.id,
        folio_number=folio_number,
        scheme_name=scheme_name,
        amc=amc or "",
        isin=isin or "",
        units=Decimal(str(units)),
        nav=Decimal(str(nav)) if nav else None,
        cost_value=Decimal(str(cost_value)) if cost_value else None,
        current_value=Decimal(str(units * nav)) if nav else None,
        registrar="manual",
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)

    return {
        "id": holding.id,
        "scheme_name": holding.scheme_name,
        "folio_number": holding.folio_number,
        "units": float(holding.units),
        "message": "Holding added successfully",
    }
