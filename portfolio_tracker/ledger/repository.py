"""Persistence for the ledger: load events, append events, never mutate.

The seam between the pure fold and the database. Everything above this line
works in ``LedgerEvent`` objects and knows nothing about SQLAlchemy;
everything below is rows.

Appends are idempotent on ``(user_id, source, source_ref)``. That is what makes
re-importing the same statement a no-op instead of a duplicate, and it is what
lets an import be retried safely after a timeout halfway through.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from portfolio_tracker.ledger.events import EventType, LedgerEvent
from portfolio_tracker.models import PortfolioEventModel

logger = logging.getLogger(__name__)


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def to_event(row: PortfolioEventModel) -> LedgerEvent:
    """Rehydrate a stored row into a domain event."""
    return LedgerEvent(
        isin=row.isin,
        event_type=EventType(row.event_type),
        trade_date=row.trade_date,
        account=row.account or "",
        quantity=_to_decimal(row.quantity),
        price=_to_decimal(row.price),
        brokerage=_to_decimal(row.brokerage),
        other_charges=_to_decimal(row.other_charges),
        stt=_to_decimal(row.stt),
        ratio=Decimal(str(row.ratio)) if row.ratio is not None else None,
        amount=Decimal(str(row.amount)) if row.amount is not None else None,
        source=row.source or "",
        source_ref=row.source_ref or "",
        symbol=row.symbol or "",
        notes=row.notes or "",
    )


def to_row(event: LedgerEvent, user_id: int, portfolio_id: int | None = None) -> PortfolioEventModel:
    """Turn a domain event into a storable row."""
    return PortfolioEventModel(
        user_id=user_id,
        portfolio_id=portfolio_id,
        isin=event.isin,
        symbol=event.symbol or None,
        account=event.account or "",
        event_type=event.event_type.value,
        trade_date=event.trade_date,
        quantity=event.quantity,
        price=event.price,
        brokerage=event.brokerage,
        stt=event.stt,
        other_charges=event.other_charges,
        ratio=event.ratio,
        amount=event.amount,
        source=event.source or "",
        source_ref=event.source_ref or "",
        notes=event.notes or None,
    )


def load_events(
    db: Session,
    user_id: int,
    isin: str | None = None,
    account: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[LedgerEvent]:
    """Read a user's events, optionally narrowed, in trade-date order.

    Note that narrowing by date is only safe for reporting. Folding a window
    in isolation would start from no lots and mismatch every disposal in it -
    the fold needs the full history to know what was held. Pass ``since`` only
    when you want the raw events, not a fold.
    """
    conditions = [PortfolioEventModel.user_id == user_id]
    if isin:
        conditions.append(PortfolioEventModel.isin == isin)
    if account is not None:
        conditions.append(PortfolioEventModel.account == account)
    if since:
        conditions.append(PortfolioEventModel.trade_date >= since)
    if until:
        conditions.append(PortfolioEventModel.trade_date <= until)

    rows = (
        db.execute(
            select(PortfolioEventModel)
            .where(and_(*conditions))
            .order_by(PortfolioEventModel.trade_date, PortfolioEventModel.id)
        )
        .scalars()
        .all()
    )
    return [to_event(row) for row in rows]


def existing_refs(db: Session, user_id: int, source: str) -> set[str]:
    """Every ``source_ref`` already stored for one source.

    Read once before an import rather than queried per row: a statement can
    carry thousands of lines and a per-row existence check turns one import
    into thousands of round trips.
    """
    rows = db.execute(
        select(PortfolioEventModel.source_ref).where(
            and_(
                PortfolioEventModel.user_id == user_id,
                PortfolioEventModel.source == source,
            )
        )
    ).scalars()
    return {ref for ref in rows if ref}


class AppendResult:
    """What an append actually did, so a caller can report it honestly."""

    __slots__ = ("added", "skipped_duplicate", "skipped_invalid")

    def __init__(self) -> None:
        self.added: int = 0
        self.skipped_duplicate: int = 0
        self.skipped_invalid: list[tuple[LedgerEvent, str]] = []

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return (
            f"AppendResult(added={self.added}, "
            f"skipped_duplicate={self.skipped_duplicate}, "
            f"skipped_invalid={len(self.skipped_invalid)})"
        )

    @property
    def total_seen(self) -> int:
        return self.added + self.skipped_duplicate + len(self.skipped_invalid)


def append_events(
    db: Session,
    user_id: int,
    events: Iterable[LedgerEvent],
    portfolio_id: int | None = None,
    commit: bool = True,
) -> AppendResult:
    """Append events, skipping any already stored under the same reference.

    Deduplication happens in two places on purpose: against what is already in
    the database, and against the batch itself. A statement can legitimately
    repeat a line, and the unique constraint would otherwise abort the whole
    import on the second occurrence.
    """
    result = AppendResult()
    candidates = list(events)
    if not candidates:
        return result

    sources = {e.source for e in candidates if e.source}
    seen: set[tuple[str, str]] = set()
    for source in sources:
        seen |= {(source, ref) for ref in existing_refs(db, user_id, source)}

    rows: list[PortfolioEventModel] = []
    for event in candidates:
        if not event.source_ref:
            # Without a stable reference an import cannot be repeated safely,
            # so refuse rather than create something undeduplicatable.
            result.skipped_invalid.append((event, "missing source_ref"))
            continue
        if event.dedup_key in seen:
            result.skipped_duplicate += 1
            continue
        seen.add(event.dedup_key)
        rows.append(to_row(event, user_id=user_id, portfolio_id=portfolio_id))

    if rows:
        db.add_all(rows)
        if commit:
            db.commit()
        else:
            db.flush()
        result.added = len(rows)

    return result


def delete_source(db: Session, user_id: int, source: str, commit: bool = True) -> int:
    """Remove every event from one source, for re-importing it cleanly.

    The only sanctioned deletion. It exists because a parser bug produces a
    whole bad batch, and the alternative - appending corrections for thousands
    of wrong rows - is worse. Scoped to one source and one user so it cannot
    take out anything else.
    """
    rows = (
        db.execute(
            select(PortfolioEventModel).where(
                and_(
                    PortfolioEventModel.user_id == user_id,
                    PortfolioEventModel.source == source,
                )
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        db.delete(row)
    if commit:
        db.commit()
    return len(rows)


def source_summary(db: Session, user_id: int) -> list[dict]:
    """Per-source event counts and date ranges, for an import history view."""
    from sqlalchemy import func

    rows = db.execute(
        select(
            PortfolioEventModel.source,
            func.count(PortfolioEventModel.id),
            func.min(PortfolioEventModel.trade_date),
            func.max(PortfolioEventModel.trade_date),
        )
        .where(PortfolioEventModel.user_id == user_id)
        .group_by(PortfolioEventModel.source)
    ).all()

    return [
        {"source": row[0], "events": row[1], "first": row[2], "last": row[3]}
        for row in rows
    ]


def distinct_isins(db: Session, user_id: int) -> list[str]:
    rows = db.execute(
        select(PortfolioEventModel.isin)
        .where(PortfolioEventModel.user_id == user_id)
        .distinct()
    ).scalars()
    return sorted(isin for isin in rows if isin)


def fold_user(db: Session, user_id: int, isin: str | None = None):
    """Load a user's full history and fold it.

    Deliberately loads everything even when narrowed to one ISIN: the fold has
    to see every event for that instrument to match lots correctly, and
    narrowing by date would silently produce wrong disposals.
    """
    from portfolio_tracker.ledger.lots import fold

    return fold(load_events(db, user_id, isin=isin))
