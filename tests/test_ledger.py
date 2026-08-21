"""Tests for the ledger fold.

The two rules that are easy to get wrong and expensive when wrong:

* FIFO is applied per demat account (CBDT Circular 768), so a sale in one
  account must not consume a cheaper lot sitting in another.
* A transfer between the investor's own accounts preserves cost basis and
  acquisition date. Booked as a sale plus a purchase it invents a capital gain
  and turns a long-term holding short-term.

No database here on purpose - the fold is pure, which is what makes this
possible at all.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_tracker.ledger import (
    EventType,
    LedgerEvent,
    canonical_symbol,
    fold,
    is_valid_isin,
    market_value,
    normalise_isin,
    unrealised,
)
from portfolio_tracker.ledger.instruments import instrument_key, is_placeholder_key
from portfolio_tracker.ledger.sources import synthetic_ref

RELIANCE = "INE002A01018"
TCS = "INE467B01029"


def ev(
    kind: EventType,
    qty: str = "0",
    price: str = "0",
    date: datetime = None,
    account: str = "zerodha",
    isin: str = RELIANCE,
    **kwargs,
) -> LedgerEvent:
    return LedgerEvent(
        isin=isin,
        event_type=kind,
        trade_date=date or datetime(2024, 1, 1),
        account=account,
        quantity=Decimal(qty),
        price=Decimal(price),
        **kwargs,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Event invariants
# ─────────────────────────────────────────────────────────────────────────────

def test_an_event_requires_an_isin():
    """Symbols are not identity, so an event without an ISIN is unusable."""
    with pytest.raises(ValueError, match="ISIN"):
        LedgerEvent(isin="", event_type=EventType.BUY, trade_date=datetime(2024, 1, 1))


def test_quantity_must_be_unsigned():
    """Direction comes from the event type, never from a negative quantity."""
    with pytest.raises(ValueError, match="unsigned"):
        LedgerEvent(
            isin=RELIANCE,
            event_type=EventType.BUY,
            trade_date=datetime(2024, 1, 1),
            quantity=Decimal("-5"),
        )


def test_stt_is_not_deductible():
    event = ev(EventType.SELL, "10", "100", brokerage=Decimal("20"),
               other_charges=Decimal("5"), stt=Decimal("50"))

    assert event.deductible_charges == Decimal("25")


def test_events_are_immutable():
    """Corrections are appended, never edited, so a filed tax figure cannot
    silently change afterwards."""
    from dataclasses import FrozenInstanceError

    event = ev(EventType.BUY, "10", "100")

    with pytest.raises(FrozenInstanceError):
        event.quantity = Decimal("20")


# ─────────────────────────────────────────────────────────────────────────────
# Basic folding
# ─────────────────────────────────────────────────────────────────────────────

def test_a_buy_creates_a_lot():
    book = fold([ev(EventType.BUY, "10", "100")])

    assert book.quantity(RELIANCE) == Decimal("10")
    assert book.cost(RELIANCE) == Decimal("1000")


def test_purchase_charges_join_the_cost_basis():
    book = fold([ev(EventType.BUY, "10", "100", brokerage=Decimal("50"))])

    # 100 + 5/unit
    assert book.cost(RELIANCE) == Decimal("1050")


def test_a_sale_consumes_the_oldest_lot_first():
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1)),
        ev(EventType.BUY, "10", "200", date=datetime(2024, 6, 1)),
        ev(EventType.SELL, "10", "300", date=datetime(2024, 8, 1)),
    ])

    assert len(book.disposals) == 1
    assert book.disposals[0].cost_per_unit == Decimal("100")
    assert book.disposals[0].gain == Decimal("2000")
    assert book.quantity(RELIANCE) == Decimal("10")


def test_a_sale_spanning_two_lots_produces_two_disposals():
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1)),
        ev(EventType.BUY, "10", "200", date=datetime(2024, 2, 1)),
        ev(EventType.SELL, "15", "300", date=datetime(2024, 8, 1)),
    ])

    assert len(book.disposals) == 2
    assert sum(d.gain for d in book.disposals) == Decimal("2500")
    assert book.quantity(RELIANCE) == Decimal("5")


def test_selling_charges_reduce_the_gain():
    book = fold([
        ev(EventType.BUY, "10", "100"),
        ev(EventType.SELL, "10", "200", date=datetime(2024, 6, 1),
           brokerage=Decimal("30")),
    ])

    assert book.disposals[0].gain == Decimal("970")


def test_a_same_day_buy_and_sell_match():
    """Inflows settle before outflows on the same date, so an intraday round
    trip matches instead of reporting a phantom short."""
    same_day = datetime(2024, 5, 1)
    book = fold([
        ev(EventType.SELL, "10", "110", date=same_day),
        ev(EventType.BUY, "10", "100", date=same_day),
    ])

    assert book.disposals[0].gain == Decimal("100")
    assert book.unmatched == []


def test_a_sale_with_no_acquisition_is_reported_not_absorbed():
    """Booking the whole proceeds as gain would be silently wrong."""
    book = fold([ev(EventType.SELL, "10", "200")])

    assert len(book.unmatched) == 1
    assert "no acquisition on record" in book.unmatched[0][1]
    assert book.disposals[0].basis_inferred is True


# ─────────────────────────────────────────────────────────────────────────────
# Account-wise FIFO (CBDT Circular 768)
# ─────────────────────────────────────────────────────────────────────────────

def test_fifo_does_not_cross_demat_accounts():
    """A cheap lot in another account cannot be construed as sold."""
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1), account="zerodha"),
        ev(EventType.BUY, "10", "500", date=datetime(2024, 2, 1), account="groww"),
        ev(EventType.SELL, "10", "600", date=datetime(2024, 8, 1), account="groww"),
    ])

    # Must match the 500 lot in groww, not the older 100 lot in zerodha.
    assert len(book.disposals) == 1
    assert book.disposals[0].cost_per_unit == Decimal("500")
    assert book.disposals[0].gain == Decimal("1000")
    assert book.quantity(RELIANCE, account="zerodha") == Decimal("10")
    assert book.quantity(RELIANCE, account="groww") == Decimal("0")


def test_quantity_aggregates_across_accounts_for_display():
    book = fold([
        ev(EventType.BUY, "10", "100", account="zerodha"),
        ev(EventType.BUY, "5", "100", account="groww"),
    ])

    assert book.quantity(RELIANCE) == Decimal("15")
    assert book.quantity(RELIANCE, account="zerodha") == Decimal("10")


def test_a_sale_in_an_empty_account_does_not_raid_another():
    book = fold([
        ev(EventType.BUY, "10", "100", account="zerodha"),
        ev(EventType.SELL, "10", "200", date=datetime(2024, 6, 1), account="groww"),
    ])

    assert book.quantity(RELIANCE, account="zerodha") == Decimal("10")
    assert len(book.unmatched) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Transfers between own accounts
# ─────────────────────────────────────────────────────────────────────────────

def test_a_transfer_is_not_a_disposal():
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1), account="zerodha"),
        ev(EventType.TRANSFER_OUT, "10", date=datetime(2024, 6, 1), account="zerodha"),
        ev(EventType.TRANSFER_IN, "10", date=datetime(2024, 6, 2), account="groww"),
    ])

    assert book.disposals == []
    assert book.quantity(RELIANCE, account="zerodha") == Decimal("0")
    assert book.quantity(RELIANCE, account="groww") == Decimal("10")


def test_a_transfer_preserves_the_cost_basis():
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1), account="zerodha"),
        ev(EventType.TRANSFER_OUT, "10", date=datetime(2024, 6, 1), account="zerodha"),
        ev(EventType.TRANSFER_IN, "10", date=datetime(2024, 6, 2), account="groww"),
    ])

    assert book.cost(RELIANCE, account="groww") == Decimal("1000")


def test_a_transfer_preserves_the_acquisition_date():
    """The holding period keeps running from the original purchase - otherwise
    consolidating accounts silently converts long-term gains into short-term."""
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2023, 1, 1), account="zerodha"),
        ev(EventType.TRANSFER_OUT, "10", date=datetime(2024, 6, 1), account="zerodha"),
        ev(EventType.TRANSFER_IN, "10", date=datetime(2024, 6, 2), account="groww"),
        ev(EventType.SELL, "10", "300", date=datetime(2024, 7, 1), account="groww"),
    ])

    disposal = book.disposals[0]
    assert disposal.acquired == datetime(2023, 1, 1)
    assert disposal.holding_days > 365
    assert disposal.cost_per_unit == Decimal("100")


def test_a_transferred_lot_keeps_its_place_in_the_fifo_queue():
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2023, 1, 1), account="zerodha"),
        ev(EventType.BUY, "10", "400", date=datetime(2024, 1, 1), account="groww"),
        ev(EventType.TRANSFER_OUT, "10", date=datetime(2024, 6, 1), account="zerodha"),
        ev(EventType.TRANSFER_IN, "10", date=datetime(2024, 6, 2), account="groww"),
        ev(EventType.SELL, "10", "500", date=datetime(2024, 7, 1), account="groww"),
    ])

    # groww's own 400 lot was acquired first, so it goes first.
    assert book.disposals[0].cost_per_unit == Decimal("400")


def test_an_unpaired_inbound_transfer_is_flagged():
    """Shares arrived and we never saw them leave: basis has to be inferred,
    and the user needs to know that."""
    book = fold([ev(EventType.TRANSFER_IN, "10", "150", account="groww")])

    assert book.quantity(RELIANCE, account="groww") == Decimal("10")
    assert len(book.unmatched) == 1
    assert "no matching outbound" in book.unmatched[0][1]
    assert book.open_lots[0].basis_inferred is True


def test_an_unpaired_outbound_transfer_does_not_lose_the_shares():
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1), account="zerodha"),
        ev(EventType.TRANSFER_OUT, "10", date=datetime(2024, 6, 1), account="zerodha"),
    ])

    assert book.quantity(RELIANCE) == Decimal("10")
    assert any("no matching inbound" in reason for _, reason in book.unmatched)


def test_transfers_far_apart_are_not_paired():
    """Two unrelated movements months apart are not one transfer."""
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1), account="zerodha"),
        ev(EventType.TRANSFER_OUT, "10", date=datetime(2024, 2, 1), account="zerodha"),
        ev(EventType.TRANSFER_IN, "10", "150", date=datetime(2024, 9, 1), account="groww"),
    ])

    assert len(book.unmatched) == 2


def test_a_transfer_is_not_a_cash_flow():
    """Moving your own shares is not a contribution, so XIRR must ignore it."""
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1), account="zerodha"),
        ev(EventType.TRANSFER_OUT, "10", date=datetime(2024, 6, 1), account="zerodha"),
        ev(EventType.TRANSFER_IN, "10", date=datetime(2024, 6, 2), account="groww"),
    ])

    assert len(book.cash_flows) == 1
    assert book.cash_flows[0][1] == Decimal("-1000")


# ─────────────────────────────────────────────────────────────────────────────
# Corporate actions
# ─────────────────────────────────────────────────────────────────────────────

def test_a_split_scales_quantity_and_cost_without_changing_value():
    book = fold([
        ev(EventType.BUY, "10", "1000", date=datetime(2024, 1, 1)),
        ev(EventType.SPLIT, date=datetime(2024, 6, 1), ratio=Decimal("5")),
    ])

    assert book.quantity(RELIANCE) == Decimal("50")
    assert book.cost(RELIANCE) == Decimal("10000")


def test_a_split_does_not_restart_the_holding_period():
    book = fold([
        ev(EventType.BUY, "10", "1000", date=datetime(2023, 1, 1)),
        ev(EventType.SPLIT, date=datetime(2024, 6, 1), ratio=Decimal("5")),
        ev(EventType.SELL, "50", "300", date=datetime(2024, 7, 1)),
    ])

    assert book.disposals[0].holding_days > 365


def test_a_bonus_issue_has_nil_cost():
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1)),
        ev(EventType.BONUS, "10", date=datetime(2024, 6, 1)),
    ])

    assert book.quantity(RELIANCE) == Decimal("20")
    assert book.cost(RELIANCE) == Decimal("1000")


def test_a_bonus_holding_period_runs_from_allotment():
    """Bonus shares are acquired when allotted, not when the original was."""
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2023, 1, 1)),
        ev(EventType.BONUS, "10", date=datetime(2024, 6, 1)),
        ev(EventType.SELL, "20", "200", date=datetime(2024, 7, 1)),
    ])

    by_cost = sorted(book.disposals, key=lambda d: d.cost_per_unit)
    assert by_cost[0].cost_per_unit == Decimal("0")
    assert by_cost[0].holding_days < 365   # the bonus shares
    assert by_cost[1].holding_days > 365   # the original purchase


def test_a_zero_split_ratio_is_rejected_not_applied():
    book = fold([
        ev(EventType.BUY, "10", "100"),
        ev(EventType.SPLIT, date=datetime(2024, 6, 1), ratio=Decimal("0")),
    ])

    assert book.quantity(RELIANCE) == Decimal("10")
    assert any("ratio" in reason for _, reason in book.unmatched)


def test_a_demerger_is_surfaced_rather_than_silently_ignored():
    book = fold([
        ev(EventType.BUY, "10", "100"),
        ev(EventType.DEMERGER, date=datetime(2024, 6, 1)),
    ])

    assert any("demerger" in reason for _, reason in book.unmatched)


# ─────────────────────────────────────────────────────────────────────────────
# Dividends and cash flows
# ─────────────────────────────────────────────────────────────────────────────

def test_a_dividend_is_income_not_a_holding_change():
    book = fold([
        ev(EventType.BUY, "100", "100", date=datetime(2024, 1, 1)),
        ev(EventType.DIVIDEND, date=datetime(2024, 6, 1), amount=Decimal("800")),
    ])

    assert book.quantity(RELIANCE) == Decimal("100")
    assert book.dividend_total(RELIANCE) == Decimal("800")


def test_a_dividend_counts_as_a_positive_cash_flow():
    book = fold([
        ev(EventType.BUY, "100", "100", date=datetime(2024, 1, 1)),
        ev(EventType.DIVIDEND, date=datetime(2024, 6, 1), amount=Decimal("800")),
    ])

    assert (datetime(2024, 6, 1), Decimal("800")) in book.cash_flows


def test_dividends_are_totalled_per_instrument():
    book = fold([
        ev(EventType.DIVIDEND, date=datetime(2024, 6, 1), amount=Decimal("500")),
        ev(EventType.DIVIDEND, date=datetime(2024, 9, 1), amount=Decimal("300")),
        ev(EventType.DIVIDEND, date=datetime(2024, 9, 1), amount=Decimal("100"), isin=TCS),
    ])

    assert book.dividend_total(RELIANCE) == Decimal("800")
    assert book.dividend_total(TCS) == Decimal("100")
    assert book.dividend_total() == Decimal("900")


def test_cash_flows_are_signed_from_the_investors_view():
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1)),
        ev(EventType.SELL, "10", "150", date=datetime(2024, 6, 1)),
    ])

    assert book.cash_flows[0][1] < 0
    assert book.cash_flows[1][1] > 0


# ─────────────────────────────────────────────────────────────────────────────
# Valuation
# ─────────────────────────────────────────────────────────────────────────────

def test_market_value_and_unrealised_use_open_lots():
    book = fold([ev(EventType.BUY, "10", "100")])
    prices = {RELIANCE: Decimal("150")}

    assert market_value(book, prices) == Decimal("1500")
    assert unrealised(book, prices) == Decimal("500")


def test_an_unpriced_instrument_is_excluded_rather_than_guessed():
    book = fold([ev(EventType.BUY, "10", "100")])

    assert market_value(book, {}) == Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# Opening balances
# ─────────────────────────────────────────────────────────────────────────────

def test_an_opening_balance_is_flagged_as_inferred():
    book = fold([ev(EventType.OPENING_BALANCE, "10", "100")])

    assert book.quantity(RELIANCE) == Decimal("10")
    assert book.open_lots[0].basis_inferred is True


def test_an_opening_balance_is_not_a_cash_flow():
    """It is history we could not source, not money the investor just put in."""
    book = fold([ev(EventType.OPENING_BALANCE, "10", "100")])

    assert book.cash_flows == []


def test_a_disposal_from_an_opening_balance_carries_the_flag():
    book = fold([
        ev(EventType.OPENING_BALANCE, "10", "100", date=datetime(2024, 1, 1)),
        ev(EventType.SELL, "10", "200", date=datetime(2024, 6, 1)),
    ])

    assert book.disposals[0].basis_inferred is True


# ─────────────────────────────────────────────────────────────────────────────
# Mixed / robustness
# ─────────────────────────────────────────────────────────────────────────────

def test_naive_and_aware_dates_can_be_mixed():
    book = fold([
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1, tzinfo=UTC)),
        ev(EventType.SELL, "10", "200", date=datetime(2024, 6, 1)),
    ])

    assert book.disposals[0].gain == Decimal("1000")


def test_instruments_are_kept_separate():
    book = fold([
        ev(EventType.BUY, "10", "100", isin=RELIANCE),
        ev(EventType.BUY, "5", "3000", isin=TCS),
    ])

    assert book.quantity(RELIANCE) == Decimal("10")
    assert book.quantity(TCS) == Decimal("5")


def test_folding_nothing_yields_an_empty_book():
    book = fold([])

    assert book.open_lots == []
    assert book.disposals == []
    assert book.cash_flows == []


def test_events_are_replayed_in_date_order_regardless_of_input_order():
    shuffled = [
        ev(EventType.SELL, "10", "300", date=datetime(2024, 8, 1)),
        ev(EventType.BUY, "10", "200", date=datetime(2024, 6, 1)),
        ev(EventType.BUY, "10", "100", date=datetime(2024, 1, 1)),
    ]

    book = fold(shuffled)

    assert book.disposals[0].cost_per_unit == Decimal("100")


# ─────────────────────────────────────────────────────────────────────────────
# Instrument identity
# ─────────────────────────────────────────────────────────────────────────────

def test_real_isins_validate():
    assert is_valid_isin("INE002A01018")   # Reliance
    assert is_valid_isin("INE467B01029")   # TCS
    assert is_valid_isin("ine002a01018")   # case insensitive


def test_a_mistyped_isin_fails_the_checksum():
    """Transcription errors from PDF statements must not create a phantom
    instrument that silently splits a holding."""
    assert not is_valid_isin("INE002A01019")
    assert not is_valid_isin("INE002A0101")
    assert not is_valid_isin("RELIANCE")
    assert not is_valid_isin("")


def test_normalise_isin_strips_whitespace():
    assert normalise_isin("  ine002a01018 ") == "INE002A01018"
    assert normalise_isin("INE 002A010 18") == "INE002A01018"


def test_canonical_symbol_collapses_ticker_variants():
    for variant in ("RELIANCE", "RELIANCE.NS", "RELIANCE.BO", "RELIANCE-EQ", "reliance.ns"):
        assert canonical_symbol(variant) == "RELIANCE"


def test_canonical_symbol_leaves_index_tickers_alone():
    assert canonical_symbol("^NSEI") == "^NSEI"


def test_instrument_key_prefers_the_isin():
    assert instrument_key(RELIANCE, "RELIANCE.NS") == RELIANCE
    assert not is_placeholder_key(instrument_key(RELIANCE, "RELIANCE.NS"))


def test_instrument_key_falls_back_to_a_marked_symbol():
    """Un-ISINed history stays usable, and obviously incomplete in the data."""
    key = instrument_key(None, "RELIANCE.NS")

    assert key == "SYM:RELIANCE"
    assert is_placeholder_key(key)


def test_an_invalid_isin_falls_back_rather_than_being_trusted():
    key = instrument_key("INE002A01019", "RELIANCE.NS")

    assert key == "SYM:RELIANCE"


# ─────────────────────────────────────────────────────────────────────────────
# Idempotent ingestion
# ─────────────────────────────────────────────────────────────────────────────

def test_synthetic_ref_is_stable_for_the_same_row():
    """Re-importing the same statement must be a no-op."""
    a = synthetic_ref(RELIANCE, "2024-03-14", "250", "buy")
    b = synthetic_ref(RELIANCE, "2024-03-14", "250", "buy")

    assert a == b


def test_synthetic_ref_differs_for_different_rows():
    a = synthetic_ref(RELIANCE, "2024-03-14", "250", "buy")
    b = synthetic_ref(RELIANCE, "2024-03-14", "251", "buy")

    assert a != b


def test_synthetic_ref_tolerates_missing_fields():
    assert synthetic_ref(RELIANCE, None, "250") == synthetic_ref(RELIANCE, None, "250")


def test_dedup_key_pairs_source_with_reference():
    event = ev(EventType.BUY, "10", "100", source="cas_nsdl", source_ref="abc")

    assert event.dedup_key == ("cas_nsdl", "abc")


def test_an_over_long_instrument_key_is_rejected_not_truncated():
    """The storage column is 24 characters and MariaDB truncates silently
    rather than erroring. A truncated key folds into lots nothing else can
    match - in production it reported seventeen holdings as zero against a
    non-zero assets table. Fail at construction, where the cause is visible.
    """
    with pytest.raises(ValueError, match="truncated"):
        LedgerEvent(
            isin="SYM:" + "X" * 21,
            event_type=EventType.BUY,
            trade_date=datetime(2024, 1, 1),
        )


def test_a_placeholder_key_for_a_long_symbol_still_fits():
    """The longest real NSE symbols must survive the SYM: prefix."""
    key = instrument_key(None, "HAPPSTMNDS.NS")

    assert key == "SYM:HAPPSTMNDS"
    # Constructing an event with it must not raise.
    assert LedgerEvent(
        isin=key, event_type=EventType.BUY, trade_date=datetime(2024, 1, 1)
    ).isin == key


def test_a_real_isin_is_comfortably_within_the_limit():
    from portfolio_tracker.ledger.events import MAX_INSTRUMENT_KEY_LENGTH

    assert len(RELIANCE) == 12
    assert MAX_INSTRUMENT_KEY_LENGTH >= 12
