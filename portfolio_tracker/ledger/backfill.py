"""Convert the existing tables into ledger events.

The transactions table is already an event log in all but name - it just lacks
identity (no ISIN), attribution (no demat account) and provenance. This builds
events from it so the ledger becomes usable immediately, before any statement
has been imported.

Two honest limitations, both surfaced rather than papered over:

* **ISINs are mostly unknown.** The existing schema never stored them. Where a
  symbol cannot be resolved, the event is keyed on a marked placeholder
  (``SYM:RELIANCE``) so the history stays usable and it is obvious in the data
  which rows still need a real ISIN. Importing a CAS later resolves them.

* **Demat accounts are mostly unknown.** Transactions predating broker sync
  carry no account. They land in a single ``"unknown"`` bucket, which means
  account-wise FIFO degrades to pooled FIFO for them - the same behaviour as
  today, no worse, and it improves as soon as real accounts are known.

A holding that the transactions cannot explain becomes an OPENING_BALANCE, so
broker-synced positions with no trade history are still valued and taxed, and
are visibly flagged as having an inferred cost basis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_tracker.ledger.events import EventType, LedgerEvent
from portfolio_tracker.ledger.instruments import instrument_key, is_placeholder_key
from portfolio_tracker.ledger.repository import append_events
from portfolio_tracker.ledger.sources import synthetic_ref
from portfolio_tracker.models import AssetModel, PortfolioModel, TransactionModel

logger = logging.getLogger(__name__)

#: Source name for events derived from this app's own tables, as opposed to an
#: imported statement. Lets the whole backfill be replaced later in one call.
BACKFILL_SOURCE = "legacy_transactions"
OPENING_SOURCE = "legacy_holdings"

#: Where an asset carries no demat account. Kept explicit rather than blank so
#: it is obvious in a tax report which lots could not be attributed.
UNKNOWN_ACCOUNT = "unknown"


@dataclass
class BackfillReport:
    """What the backfill produced, and what it could not resolve."""

    transaction_events: int = 0
    opening_events: int = 0
    added: int = 0
    skipped_duplicate: int = 0
    #: Symbols with no ISIN, keyed on the placeholder used instead.
    unresolved_symbols: set[str] = field(default_factory=set)
    #: Assets whose quantity the ledger could not explain.
    opening_balances: list[tuple[str, Decimal]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def total_events(self) -> int:
        return self.transaction_events + self.opening_events


def _account_for(asset: AssetModel) -> str:
    return (getattr(asset, "demat_account", None) or "").strip() or UNKNOWN_ACCOUNT


def _key_for(asset: AssetModel) -> str:
    return instrument_key(getattr(asset, "isin", None), asset.symbol)


def build_events(db: Session, user_id: int) -> tuple[list[LedgerEvent], BackfillReport]:
    """Derive events from a user's transactions and holdings. Reads only."""
    report = BackfillReport()

    portfolio_ids = list(
        db.execute(
            select(PortfolioModel.id).where(PortfolioModel.user_id == user_id)
        ).scalars()
    )
    if not portfolio_ids:
        return [], report

    rows = db.execute(
        select(TransactionModel, AssetModel)
        .join(AssetModel, TransactionModel.asset_id == AssetModel.id)
        .where(TransactionModel.portfolio_id.in_(portfolio_ids))
        .order_by(TransactionModel.transaction_date, TransactionModel.id)
    ).all()

    events: list[LedgerEvent] = []
    #: Net quantity the ledger accounts for, per (key, account).
    explained: dict[tuple[str, str], Decimal] = {}
    #: Earliest recorded trade per (key, account). An opening balance cannot be
    #: dated later than the first trade against it - you cannot sell in
    #: December something the record says you acquired in January.
    first_activity: dict[tuple[str, str], object] = {}

    for txn, asset in rows:
        key = _key_for(asset)
        if not key:
            report.notes.append(f"transaction {txn.id}: asset has neither ISIN nor symbol")
            continue
        if is_placeholder_key(key):
            report.unresolved_symbols.add(asset.symbol)

        account = _account_for(asset)
        kind = EventType.BUY if (txn.type or "").lower() == "buy" else EventType.SELL
        quantity = Decimal(str(txn.quantity or 0))

        events.append(
            LedgerEvent(
                isin=key,
                event_type=kind,
                trade_date=txn.transaction_date,
                account=account,
                quantity=quantity,
                price=Decimal(str(txn.price or 0)),
                brokerage=Decimal(str(getattr(txn, "brokerage", 0) or 0)),
                stt=Decimal(str(getattr(txn, "stt", 0) or 0)),
                other_charges=Decimal(str(getattr(txn, "other_charges", 0) or 0)),
                source=BACKFILL_SOURCE,
                # The transaction's own id is already a stable reference, so a
                # repeated backfill is naturally idempotent.
                source_ref=f"txn:{txn.id}",
                symbol=asset.symbol,
                notes=txn.notes or "",
            )
        )
        report.transaction_events += 1

        delta = quantity if kind is EventType.BUY else -quantity
        explained[(key, account)] = explained.get((key, account), Decimal("0")) + delta

        # Earliest activity per instrument, used to date an opening balance.
        bucket = (key, account)
        when = txn.transaction_date
        if when is not None and (
            bucket not in first_activity or when < first_activity[bucket]
        ):
            first_activity[bucket] = when

    # Holdings the transactions cannot account for: broker syncs that imported
    # positions without their trade history. Without these the ledger would
    # under-report the portfolio against what the user can see in their app.
    assets = db.execute(
        select(AssetModel).where(AssetModel.portfolio_id.in_(portfolio_ids))
    ).scalars().all()

    held: dict[tuple[str, str], Decimal] = {}
    earliest: dict[tuple[str, str], object] = {}
    basis: dict[tuple[str, str], Decimal] = {}
    labels: dict[tuple[str, str], str] = {}

    for asset in assets:
        key = _key_for(asset)
        if not key:
            continue
        if is_placeholder_key(key):
            report.unresolved_symbols.add(asset.symbol)
        account = _account_for(asset)
        bucket = (key, account)

        held[bucket] = held.get(bucket, Decimal("0")) + Decimal(str(asset.quantity or 0))
        labels.setdefault(bucket, asset.symbol)

        when = asset.purchase_date
        if when is not None and (bucket not in earliest or when < earliest[bucket]):
            earliest[bucket] = when
        price = Decimal(str(asset.purchase_price or 0))
        if price and not basis.get(bucket):
            basis[bucket] = price

    for bucket, quantity in held.items():
        unexplained = quantity - explained.get(bucket, Decimal("0"))
        if unexplained <= 0:
            continue
        key, account = bucket
        when = earliest.get(bucket)
        traded = first_activity.get(bucket)

        # `purchase_date` on a broker-synced asset is a sync timestamp, not a
        # real acquisition date, and it is often later than trades already on
        # record. Take the earlier of the two so the opening balance exists
        # before anything is sold out of it.
        if traded is not None and (when is None or traded < when):
            when = traded
            report.notes.append(
                f"{labels.get(bucket, key)}: opening balance dated from first "
                f"recorded trade ({traded:%Y-%m-%d}), not the asset's sync date"
            )

        if when is None:
            report.notes.append(f"{labels.get(bucket, key)}: no purchase date; opening balance skipped")
            continue

        events.append(
            LedgerEvent(
                isin=key,
                event_type=EventType.OPENING_BALANCE,
                trade_date=when,
                account=account,
                quantity=unexplained,
                price=basis.get(bucket, Decimal("0")),
                source=OPENING_SOURCE,
                source_ref=synthetic_ref(key, account, str(unexplained), str(when)),
                symbol=labels.get(bucket, ""),
                notes="quantity held that the transaction history does not explain",
            )
        )
        report.opening_events += 1
        report.opening_balances.append((labels.get(bucket, key), unexplained))

    return events, report


def backfill_user(db: Session, user_id: int, commit: bool = True) -> BackfillReport:
    """Derive events for one user and append them idempotently."""
    events, report = build_events(db, user_id)
    if not events:
        return report

    result = append_events(db, user_id, events, commit=commit)
    report.added = result.added
    report.skipped_duplicate = result.skipped_duplicate
    for event, reason in result.skipped_invalid:
        report.notes.append(f"{event.symbol or event.isin}: {reason}")

    return report


def backfill_all(db: Session, commit: bool = True) -> dict[int, BackfillReport]:
    """Backfill every user that has a portfolio."""
    user_ids = list(db.execute(select(PortfolioModel.user_id).distinct()).scalars())
    return {uid: backfill_user(db, uid, commit=commit) for uid in sorted(user_ids)}
