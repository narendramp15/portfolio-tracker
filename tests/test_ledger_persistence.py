"""Tests for storing events and backfilling them from the existing tables.

The property that matters most here is idempotence. An import runs against a
statement the user will upload again next month, and a partially-failed import
gets retried - so appending the same events twice has to be a no-op rather
than a duplicate or a constraint violation.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from portfolio_tracker import models
from portfolio_tracker.crud import create_asset, create_portfolio
from portfolio_tracker.ledger import EventType, LedgerEvent, fold
from portfolio_tracker.ledger.backfill import (
    BACKFILL_SOURCE,
    OPENING_SOURCE,
    UNKNOWN_ACCOUNT,
    backfill_user,
    build_events,
)
from portfolio_tracker.ledger.instruments import is_placeholder_key
from portfolio_tracker.ledger.repository import (
    append_events,
    delete_source,
    distinct_isins,
    fold_user,
    load_events,
    source_summary,
)

RELIANCE = "INE002A01018"
TCS = "INE467B01029"


def event(
    kind: EventType = EventType.BUY,
    qty: str = "10",
    price: str = "100",
    date: datetime = None,
    isin: str = RELIANCE,
    ref: str = "r1",
    account: str = "zerodha",
    source: str = "test_source",
) -> LedgerEvent:
    return LedgerEvent(
        isin=isin,
        event_type=kind,
        trade_date=date or datetime(2024, 1, 1),
        account=account,
        quantity=Decimal(qty),
        price=Decimal(price),
        source=source,
        source_ref=ref,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Round trip
# ─────────────────────────────────────────────────────────────────────────────

def test_an_event_survives_a_round_trip(db_session, test_user):
    append_events(db_session, test_user["id"], [event()])

    stored = load_events(db_session, test_user["id"])

    assert len(stored) == 1
    assert stored[0].isin == RELIANCE
    assert stored[0].event_type is EventType.BUY
    assert stored[0].quantity == Decimal("10")
    assert stored[0].account == "zerodha"


def test_charges_and_ratio_survive_the_round_trip(db_session, test_user):
    rich = LedgerEvent(
        isin=RELIANCE,
        event_type=EventType.SELL,
        trade_date=datetime(2024, 6, 1),
        account="groww",
        quantity=Decimal("5"),
        price=Decimal("250"),
        brokerage=Decimal("12.50"),
        stt=Decimal("31.25"),
        other_charges=Decimal("3.75"),
        source="test_source",
        source_ref="rich",
    )
    append_events(db_session, test_user["id"], [rich])

    stored = load_events(db_session, test_user["id"])[0]

    assert stored.brokerage == Decimal("12.5000")
    assert stored.stt == Decimal("31.2500")
    assert stored.deductible_charges == Decimal("16.2500")


def test_a_split_ratio_survives_the_round_trip(db_session, test_user):
    split = LedgerEvent(
        isin=RELIANCE,
        event_type=EventType.SPLIT,
        trade_date=datetime(2024, 6, 1),
        ratio=Decimal("5"),
        source="test_source",
        source_ref="split1",
    )
    append_events(db_session, test_user["id"], [split])

    assert load_events(db_session, test_user["id"])[0].ratio == Decimal("5")


def test_events_load_in_trade_date_order(db_session, test_user):
    append_events(db_session, test_user["id"], [
        event(date=datetime(2024, 6, 1), ref="b"),
        event(date=datetime(2024, 1, 1), ref="a"),
    ])

    stored = load_events(db_session, test_user["id"])

    assert [e.source_ref for e in stored] == ["a", "b"]


# ─────────────────────────────────────────────────────────────────────────────
# Idempotence
# ─────────────────────────────────────────────────────────────────────────────

def test_appending_the_same_event_twice_is_a_no_op(db_session, test_user):
    """Re-uploading last month's statement must not duplicate it."""
    first = append_events(db_session, test_user["id"], [event()])
    second = append_events(db_session, test_user["id"], [event()])

    assert first.added == 1
    assert second.added == 0
    assert second.skipped_duplicate == 1
    assert len(load_events(db_session, test_user["id"])) == 1


def test_a_duplicate_inside_one_batch_is_collapsed(db_session, test_user):
    """A statement can repeat a line; the unique constraint would otherwise
    abort the whole import on the second occurrence."""
    result = append_events(db_session, test_user["id"], [event(), event()])

    assert result.added == 1
    assert result.skipped_duplicate == 1


def test_an_event_without_a_reference_is_refused(db_session, test_user):
    """Without a stable ref an import cannot be repeated safely."""
    result = append_events(db_session, test_user["id"], [event(ref="")])

    assert result.added == 0
    assert result.skipped_invalid
    assert "source_ref" in result.skipped_invalid[0][1]


def test_the_same_reference_from_a_different_source_is_kept(db_session, test_user):
    """Two sources numbering their rows 1, 2, 3 must not collide."""
    append_events(db_session, test_user["id"], [event(source="cas", ref="1")])
    append_events(db_session, test_user["id"], [event(source="tradebook", ref="1")])

    assert len(load_events(db_session, test_user["id"])) == 2


def test_a_partial_import_can_be_retried(db_session, test_user):
    """Half the batch landed, then it failed. Re-running finishes the job."""
    batch = [event(ref="a"), event(ref="b"), event(ref="c")]
    append_events(db_session, test_user["id"], batch[:1])

    retry = append_events(db_session, test_user["id"], batch)

    assert retry.added == 2
    assert retry.skipped_duplicate == 1
    assert len(load_events(db_session, test_user["id"])) == 3


def test_appending_nothing_is_harmless(db_session, test_user):
    result = append_events(db_session, test_user["id"], [])

    assert result.added == 0
    assert result.total_seen == 0


# ─────────────────────────────────────────────────────────────────────────────
# Isolation and queries
# ─────────────────────────────────────────────────────────────────────────────

def test_one_users_events_are_invisible_to_another(db_session, test_user):
    other = models.UserModel(
        email="other@example.com", username="other",
        hashed_password="x", is_active=True,
    )
    db_session.add(other)
    db_session.commit()

    append_events(db_session, test_user["id"], [event()])

    assert load_events(db_session, other.id) == []


def test_events_can_be_narrowed_by_instrument_and_account(db_session, test_user):
    append_events(db_session, test_user["id"], [
        event(isin=RELIANCE, account="zerodha", ref="a"),
        event(isin=TCS, account="zerodha", ref="b"),
        event(isin=RELIANCE, account="groww", ref="c"),
    ])

    assert len(load_events(db_session, test_user["id"], isin=RELIANCE)) == 2
    assert len(load_events(db_session, test_user["id"], account="groww")) == 1


def test_distinct_isins_lists_what_is_held(db_session, test_user):
    append_events(db_session, test_user["id"], [
        event(isin=RELIANCE, ref="a"),
        event(isin=TCS, ref="b"),
        event(isin=RELIANCE, ref="c"),
    ])

    assert distinct_isins(db_session, test_user["id"]) == sorted([RELIANCE, TCS])


def test_source_summary_reports_per_source_ranges(db_session, test_user):
    append_events(db_session, test_user["id"], [
        event(source="cas", ref="a", date=datetime(2024, 1, 1)),
        event(source="cas", ref="b", date=datetime(2024, 6, 1)),
        event(source="tradebook", ref="a", date=datetime(2024, 3, 1)),
    ])

    summary = {row["source"]: row for row in source_summary(db_session, test_user["id"])}

    assert summary["cas"]["events"] == 2
    assert summary["tradebook"]["events"] == 1


def test_a_bad_import_can_be_removed_by_source(db_session, test_user):
    """A parser bug produces a whole bad batch; appending corrections for
    thousands of wrong rows is worse than dropping the source."""
    append_events(db_session, test_user["id"], [
        event(source="cas", ref="a"),
        event(source="tradebook", ref="b"),
    ])

    removed = delete_source(db_session, test_user["id"], "cas")

    assert removed == 1
    remaining = load_events(db_session, test_user["id"])
    assert len(remaining) == 1
    assert remaining[0].source == "tradebook"


def test_stored_events_fold_correctly(db_session, test_user):
    """The point of all of this: persistence must not change the answer."""
    append_events(db_session, test_user["id"], [
        event(EventType.BUY, "10", "100", date=datetime(2024, 1, 1), ref="a"),
        event(EventType.SELL, "10", "150", date=datetime(2024, 6, 1), ref="b"),
    ])

    book = fold_user(db_session, test_user["id"])

    assert book.disposals[0].gain == Decimal("500")


# ─────────────────────────────────────────────────────────────────────────────
# Backfill from the existing tables
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def legacy_portfolio(db_session, test_user):
    """A portfolio shaped like the production data: symbols, no ISINs."""
    portfolio = create_portfolio(
        db_session, user_id=test_user["id"], name="Legacy", description=""
    )
    asset = create_asset(
        db_session,
        portfolio_id=portfolio.id,
        symbol="RELIANCE.NS",
        name="Reliance",
        quantity=Decimal("10"),
        purchase_price=Decimal("100"),
        current_price=Decimal("150"),
    )
    db_session.add(models.TransactionModel(
        portfolio_id=portfolio.id, asset_id=asset.id, type="buy",
        quantity=Decimal("10"), price=Decimal("100"),
        transaction_date=datetime(2024, 1, 1),
    ))
    db_session.commit()
    return {"portfolio": portfolio, "asset": asset}


def test_backfill_turns_transactions_into_events(db_session, test_user, legacy_portfolio):
    report = backfill_user(db_session, test_user["id"])

    assert report.transaction_events == 1
    assert report.added == 1
    stored = load_events(db_session, test_user["id"])
    assert stored[0].event_type is EventType.BUY
    assert stored[0].source == BACKFILL_SOURCE


def test_backfill_is_idempotent(db_session, test_user, legacy_portfolio):
    """It will be re-run after ISINs are resolved; that must not duplicate."""
    backfill_user(db_session, test_user["id"])
    second = backfill_user(db_session, test_user["id"])

    assert second.added == 0
    assert second.skipped_duplicate >= 1


def test_backfill_marks_symbols_with_no_isin(db_session, test_user, legacy_portfolio):
    """Un-ISINed history stays usable and obviously incomplete."""
    report = backfill_user(db_session, test_user["id"])

    assert "RELIANCE.NS" in report.unresolved_symbols
    assert is_placeholder_key(load_events(db_session, test_user["id"])[0].isin)


def test_backfill_collapses_symbol_variants_onto_one_key(db_session, test_user):
    """The production bug: RELIANCE holds the ledger, RELIANCE.NS the quantity."""
    portfolio = create_portfolio(db_session, user_id=test_user["id"], name="P", description="")
    bare = create_asset(
        db_session, portfolio_id=portfolio.id, symbol="RELIANCE", name="Reliance",
        quantity=Decimal("0"), purchase_price=Decimal("100"), current_price=Decimal("150"),
    )
    create_asset(
        db_session, portfolio_id=portfolio.id, symbol="RELIANCE.NS", name="Reliance",
        quantity=Decimal("10"), purchase_price=Decimal("100"), current_price=Decimal("150"),
    )
    db_session.add(models.TransactionModel(
        portfolio_id=portfolio.id, asset_id=bare.id, type="buy",
        quantity=Decimal("10"), price=Decimal("100"),
        transaction_date=datetime(2024, 1, 1),
    ))
    db_session.commit()

    events, report = build_events(db_session, test_user["id"])

    # One instrument, not two, so the ledger explains the position and no
    # phantom opening balance is created on top of it.
    assert len({e.isin for e in events}) == 1
    assert report.opening_events == 0


def test_an_unexplained_holding_becomes_an_opening_balance(db_session, test_user):
    """A broker-synced position with no trade history must still be valued."""
    portfolio = create_portfolio(db_session, user_id=test_user["id"], name="P", description="")
    create_asset(
        db_session, portfolio_id=portfolio.id, symbol="TCS.NS", name="TCS",
        quantity=Decimal("5"), purchase_price=Decimal("3000"), current_price=Decimal("3500"),
    )
    db_session.commit()

    events, report = build_events(db_session, test_user["id"])

    assert report.opening_events == 1
    opening = [e for e in events if e.event_type is EventType.OPENING_BALANCE][0]
    assert opening.quantity == Decimal("5")
    assert opening.source == OPENING_SOURCE


def test_an_opening_balance_is_flagged_as_inferred_after_folding(db_session, test_user):
    portfolio = create_portfolio(db_session, user_id=test_user["id"], name="P", description="")
    create_asset(
        db_session, portfolio_id=portfolio.id, symbol="TCS.NS", name="TCS",
        quantity=Decimal("5"), purchase_price=Decimal("3000"), current_price=Decimal("3500"),
    )
    db_session.commit()
    backfill_user(db_session, test_user["id"])

    book = fold_user(db_session, test_user["id"])

    assert book.open_lots[0].basis_inferred is True


def test_a_fully_explained_holding_gets_no_opening_balance(db_session, test_user, legacy_portfolio):
    _, report = build_events(db_session, test_user["id"])

    assert report.opening_events == 0


def test_transactions_without_an_account_land_in_a_named_bucket(db_session, test_user, legacy_portfolio):
    """Explicit rather than blank, so a tax report can say which lots could
    not be attributed to a demat."""
    events, _ = build_events(db_session, test_user["id"])

    assert events[0].account == UNKNOWN_ACCOUNT


def test_backfill_of_an_empty_account_is_harmless(db_session, test_user):
    report = backfill_user(db_session, test_user["id"])

    assert report.total_events == 0
    assert report.added == 0


def test_backfilled_events_reproduce_the_holding(db_session, test_user, legacy_portfolio):
    """The check that matters: the fold must agree with what the user sees."""
    backfill_user(db_session, test_user["id"])

    book = fold_user(db_session, test_user["id"])
    key = load_events(db_session, test_user["id"])[0].isin

    assert book.quantity(key) == Decimal("10")
    assert book.cost(key) == Decimal("1000")


def test_an_opening_balance_cannot_postdate_a_sale(db_session, test_user):
    """A broker-synced asset's purchase_date is a sync timestamp, often later
    than trades already on record. Dating the opening balance from it makes the
    fold see a sale with nothing held - which is exactly what production did:
    ETERNAL sold 2025-12-02 against an asset stamped 2026-01-31.
    """
    portfolio = create_portfolio(db_session, user_id=test_user["id"], name="P", description="")
    bare = create_asset(
        db_session, portfolio_id=portfolio.id, symbol="ETERNAL", name="Eternal",
        quantity=Decimal("0"), purchase_price=Decimal("290"), current_price=Decimal("299"),
    )
    # The synced row, stamped later than the sale below.
    synced = create_asset(
        db_session, portfolio_id=portfolio.id, symbol="ETERNAL.NS", name="Eternal",
        quantity=Decimal("86"), purchase_price=Decimal("290"), current_price=Decimal("299"),
    )
    synced.purchase_date = datetime(2026, 1, 31)
    db_session.add(models.TransactionModel(
        portfolio_id=portfolio.id, asset_id=bare.id, type="sell",
        quantity=Decimal("100"), price=Decimal("299"),
        transaction_date=datetime(2025, 12, 2),
    ))
    db_session.commit()

    events, report = build_events(db_session, test_user["id"])
    book = fold(events)

    assert book.unmatched == []
    # 186 opening less 100 sold leaves the 86 actually held.
    key = events[0].isin
    assert book.quantity(key) == Decimal("86")
    assert any("first recorded trade" in note for note in report.notes)


def test_the_opening_balance_keeps_the_asset_date_when_it_is_earlier(db_session, test_user):
    """The fix takes the earlier of the two, so a genuine purchase date wins."""
    portfolio = create_portfolio(db_session, user_id=test_user["id"], name="P", description="")
    asset = create_asset(
        db_session, portfolio_id=portfolio.id, symbol="TCS.NS", name="TCS",
        quantity=Decimal("10"), purchase_price=Decimal("3000"), current_price=Decimal("3500"),
    )
    asset.purchase_date = datetime(2023, 1, 1)
    db_session.add(models.TransactionModel(
        portfolio_id=portfolio.id, asset_id=asset.id, type="buy",
        quantity=Decimal("5"), price=Decimal("3200"),
        transaction_date=datetime(2024, 6, 1),
    ))
    db_session.commit()

    events, _ = build_events(db_session, test_user["id"])
    opening = [e for e in events if e.event_type is EventType.OPENING_BALANCE][0]

    assert opening.trade_date == datetime(2023, 1, 1)
