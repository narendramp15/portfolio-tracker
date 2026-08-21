"""Tests for the capital gains engine.

This module feeds numbers a user puts on an ITR filing, so the cases below
pin down the boundaries rather than just the happy path: the exact 365-day
STCG/LTCG line, FIFO vs LIFO lot consumption, financial-year windowing across
already-consumed lots, the exemption threshold, loss handling, deductible
charges, and the Section 112A step-up.
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from portfolio_tracker.services import grandfathering
from portfolio_tracker.services.tax_calculator import TaxCalculator


class FakeAsset:
    """Minimal stand-in for AssetModel - the calculator only reads these."""

    def __init__(self, symbol: str, name: str = None, current_price: Decimal = Decimal("0")):
        self.symbol = symbol
        self.name = name or symbol
        self.current_price = current_price


class FakeTxn:
    """Minimal stand-in for TransactionModel."""

    _next_id = 1

    def __init__(
        self,
        asset: FakeAsset,
        type: str,
        quantity: str,
        price: str,
        date: datetime,
        brokerage: str = "0",
        stt: str = "0",
        other_charges: str = "0",
    ):
        self.id = FakeTxn._next_id
        FakeTxn._next_id += 1
        self.asset = asset
        self.type = type
        self.quantity = Decimal(quantity)
        self.price = Decimal(price)
        self.transaction_date = date
        self.brokerage = Decimal(brokerage)
        self.stt = Decimal(stt)
        self.other_charges = Decimal(other_charges)


@pytest.fixture
def reliance():
    return FakeAsset("RELIANCE.NS", "Reliance Industries", Decimal("1500"))


@pytest.fixture(autouse=True)
def clean_fmv_cache():
    """Keep the FMV table isolated between tests."""
    grandfathering.reset_cache()
    yield
    grandfathering.reset_cache()


# ─────────────────────────────────────────────────────────────────────────────
# STCG / LTCG boundary
# ─────────────────────────────────────────────────────────────────────────────

def test_holding_exactly_365_days_is_long_term(reliance):
    """365 days is the threshold itself, and counts as long-term."""
    buy_date = datetime(2023, 4, 10)
    txns = [
        FakeTxn(reliance, "buy", "100", "1000", buy_date),
        FakeTxn(reliance, "sell", "100", "1200", buy_date + timedelta(days=365)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_ltcg"] == pytest.approx(20000.0)
    assert result["summary"]["total_stcg"] == pytest.approx(0.0)


def test_holding_364_days_is_short_term(reliance):
    """One day short of the threshold falls on the STCG side."""
    buy_date = datetime(2023, 4, 10)
    txns = [
        FakeTxn(reliance, "buy", "100", "1000", buy_date),
        FakeTxn(reliance, "sell", "100", "1200", buy_date + timedelta(days=364)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_stcg"] == pytest.approx(20000.0)
    assert result["summary"]["total_ltcg"] == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Lot consumption
# ─────────────────────────────────────────────────────────────────────────────

def test_fifo_consumes_the_oldest_lot_first(reliance):
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2023, 1, 1)),
        FakeTxn(reliance, "buy", "10", "200", datetime(2023, 6, 1)),
        FakeTxn(reliance, "sell", "10", "300", datetime(2023, 8, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns, method="FIFO")

    # Oldest lot at 100 -> gain of 200/share on 10 shares.
    assert result["summary"]["total_stcg"] == pytest.approx(2000.0)


def test_lifo_consumes_the_newest_lot_first(reliance):
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2023, 1, 1)),
        FakeTxn(reliance, "buy", "10", "200", datetime(2023, 6, 1)),
        FakeTxn(reliance, "sell", "10", "300", datetime(2023, 8, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns, method="LIFO")

    # Newest lot at 200 -> gain of 100/share on 10 shares.
    assert result["summary"]["total_stcg"] == pytest.approx(1000.0)


def test_partial_sell_splits_across_lots(reliance):
    """A sell larger than the first lot spills into the next one."""
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2023, 1, 1)),
        FakeTxn(reliance, "buy", "10", "200", datetime(2023, 2, 1)),
        FakeTxn(reliance, "sell", "15", "300", datetime(2023, 8, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns, method="FIFO")

    # 10 @ (300-100) + 5 @ (300-200) = 2000 + 500
    assert result["summary"]["total_stcg"] == pytest.approx(2500.0)
    assert result["by_symbol"]["RELIANCE.NS"]["realized_count"] == 2


def test_a_sell_can_span_the_stcg_ltcg_boundary(reliance):
    """One sell against two lots of different ages splits across both buckets."""
    sell_date = datetime(2024, 6, 1)
    txns = [
        FakeTxn(reliance, "buy", "10", "100", sell_date - timedelta(days=500)),
        FakeTxn(reliance, "buy", "10", "100", sell_date - timedelta(days=100)),
        FakeTxn(reliance, "sell", "20", "150", sell_date),
    ]

    result = TaxCalculator.calculate_capital_gains(txns, method="FIFO")

    assert result["summary"]["total_ltcg"] == pytest.approx(500.0)
    assert result["summary"]["total_stcg"] == pytest.approx(500.0)


# ─────────────────────────────────────────────────────────────────────────────
# Financial year windowing
# ─────────────────────────────────────────────────────────────────────────────

def _realized(result) -> float:
    """Total realized gain across both buckets.

    Used where a test is about which financial year a sell lands in, not about
    which side of the 365-day line it falls on.
    """
    return result["summary"]["total_stcg"] + result["summary"]["total_ltcg"]


def test_fy_filter_reports_only_that_years_sells(reliance):
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2023, 5, 1)),
        FakeTxn(reliance, "buy", "10", "100", datetime(2023, 5, 2)),
        FakeTxn(reliance, "sell", "10", "150", datetime(2023, 9, 1)),   # FY 2023-24
        FakeTxn(reliance, "sell", "10", "200", datetime(2024, 9, 1)),   # FY 2024-25
    ]

    fy23 = TaxCalculator.calculate_capital_gains(txns, financial_year="2023-24")
    fy24 = TaxCalculator.calculate_capital_gains(txns, financial_year="2024-25")

    assert _realized(fy23) == pytest.approx(500.0)
    assert _realized(fy24) == pytest.approx(1000.0)
    # The FY 2023-24 sell is 4 months old (short-term); the FY 2024-25 one is
    # 16 months old, so it lands on the long-term side.
    assert fy23["summary"]["total_stcg"] == pytest.approx(500.0)
    assert fy24["summary"]["total_ltcg"] == pytest.approx(1000.0)


def test_fy_boundary_dates_land_in_the_right_year(reliance):
    """31 March and 1 April fall either side of the FY line."""
    txns = [
        FakeTxn(reliance, "buy", "20", "100", datetime(2023, 1, 1)),
        FakeTxn(reliance, "sell", "10", "150", datetime(2024, 3, 31)),  # FY 2023-24
        FakeTxn(reliance, "sell", "10", "150", datetime(2024, 4, 1)),   # FY 2024-25
    ]

    fy23 = TaxCalculator.calculate_capital_gains(txns, financial_year="2023-24")
    fy24 = TaxCalculator.calculate_capital_gains(txns, financial_year="2024-25")

    assert _realized(fy23) == pytest.approx(500.0)
    assert _realized(fy24) == pytest.approx(500.0)


def test_earlier_fy_sells_still_consume_lots(reliance):
    """Lots sold in an earlier year must not be re-matched in a later one."""
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2022, 5, 1)),
        FakeTxn(reliance, "buy", "10", "500", datetime(2023, 5, 1)),
        FakeTxn(reliance, "sell", "10", "200", datetime(2023, 6, 1)),   # eats the 100 lot
        FakeTxn(reliance, "sell", "10", "600", datetime(2024, 6, 1)),   # must hit the 500 lot
    ]

    fy24 = TaxCalculator.calculate_capital_gains(txns, financial_year="2024-25")

    # If the cheap lot were reused this would be 5000, not 1000.
    assert _realized(fy24) == pytest.approx(1000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Rates, exemption, losses
# ─────────────────────────────────────────────────────────────────────────────

def test_ltcg_below_the_exemption_attracts_no_tax(reliance):
    buy_date = datetime(2022, 1, 1)
    txns = [
        FakeTxn(reliance, "buy", "100", "1000", buy_date),
        FakeTxn(reliance, "sell", "100", "2000", buy_date + timedelta(days=400)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    # 1,00,000 gain, under the 1.25L exemption.
    assert result["summary"]["total_ltcg"] == pytest.approx(100000.0)
    assert result["summary"]["total_ltcg_tax"] == pytest.approx(0.0)


def test_ltcg_above_the_exemption_is_taxed_on_the_excess_only(reliance):
    buy_date = datetime(2022, 1, 1)
    txns = [
        FakeTxn(reliance, "buy", "100", "1000", buy_date),
        FakeTxn(reliance, "sell", "100", "3250", buy_date + timedelta(days=400)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    # 2,25,000 gain - 1,25,000 exemption = 1,00,000 taxed at 12.5%.
    assert result["summary"]["total_ltcg"] == pytest.approx(225000.0)
    assert result["summary"]["total_ltcg_tax"] == pytest.approx(12500.0)


def test_stcg_is_taxed_at_twenty_percent(reliance):
    txns = [
        FakeTxn(reliance, "buy", "100", "1000", datetime(2024, 1, 1)),
        FakeTxn(reliance, "sell", "100", "1500", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_stcg"] == pytest.approx(50000.0)
    assert result["summary"]["total_stcg_tax"] == pytest.approx(10000.0)


def test_a_net_short_term_loss_is_not_a_negative_tax(reliance):
    """Losses carry forward; they must never render as a tax refund."""
    txns = [
        FakeTxn(reliance, "buy", "100", "2000", datetime(2024, 1, 1)),
        FakeTxn(reliance, "sell", "100", "1500", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_stcg"] == pytest.approx(-50000.0)
    assert result["summary"]["total_stcg_tax"] == pytest.approx(0.0)
    assert result["summary"]["total_tax"] >= 0


def test_a_long_term_loss_produces_no_tax(reliance):
    buy_date = datetime(2022, 1, 1)
    txns = [
        FakeTxn(reliance, "buy", "100", "2000", buy_date),
        FakeTxn(reliance, "sell", "100", "1500", buy_date + timedelta(days=400)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_ltcg"] == pytest.approx(-50000.0)
    assert result["summary"]["total_ltcg_tax"] == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Charges
# ─────────────────────────────────────────────────────────────────────────────

def test_brokerage_on_both_legs_reduces_the_gain(reliance):
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2024, 1, 1), brokerage="20"),
        FakeTxn(reliance, "sell", "10", "200", datetime(2024, 6, 1), brokerage="30"),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    # Raw gain 1000, less 20 buy-side and 30 sell-side brokerage.
    assert result["summary"]["total_stcg"] == pytest.approx(950.0)
    assert result["summary"]["total_charges"] == pytest.approx(50.0)


def test_stt_is_not_deductible(reliance):
    """STT is expressly excluded from deductible expenses under Section 48."""
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2024, 1, 1), stt="15"),
        FakeTxn(reliance, "sell", "10", "200", datetime(2024, 6, 1), stt="25"),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_stcg"] == pytest.approx(1000.0)
    assert result["summary"]["total_charges"] == pytest.approx(0.0)


def test_other_charges_are_deductible(reliance):
    """Stamp duty, turnover charges, SEBI fee and GST all reduce the gain."""
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2024, 1, 1), other_charges="10"),
        FakeTxn(reliance, "sell", "10", "200", datetime(2024, 6, 1), other_charges="10"),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_stcg"] == pytest.approx(980.0)


def test_charges_are_apportioned_across_a_partially_sold_lot(reliance):
    """Half a lot sold carries half that lot's purchase charges."""
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2024, 1, 1), brokerage="100"),
        FakeTxn(reliance, "sell", "5", "200", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    # 5 shares @ (200 - (100 + 10 per-unit brokerage)) = 450
    assert result["summary"]["total_stcg"] == pytest.approx(450.0)


def test_transactions_without_charge_fields_still_work(reliance):
    """Rows predating the charges migration have no attributes to read."""

    class LegacyTxn:
        def __init__(self, asset, type, quantity, price, date):
            self.id = 1
            self.asset = asset
            self.type = type
            self.quantity = Decimal(quantity)
            self.price = Decimal(price)
            self.transaction_date = date

    txns = [
        LegacyTxn(reliance, "buy", "10", "100", datetime(2024, 1, 1)),
        LegacyTxn(reliance, "sell", "10", "200", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_stcg"] == pytest.approx(1000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Section 112A grandfathering
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def fmv_table(tmp_path, monkeypatch):
    """Point the grandfathering module at a temporary FMV file."""

    def _write(values: dict):
        path = tmp_path / "fmv_31jan2018.json"
        path.write_text(json.dumps(values), encoding="utf-8")
        monkeypatch.setattr(grandfathering, "_FMV_DATA_FILE", path)
        grandfathering.reset_cache()
        return path

    return _write


def test_pre_2018_lot_gets_the_cost_stepped_up_to_fmv(reliance, fmv_table):
    fmv_table({"RELIANCE": "960"})

    txns = [
        FakeTxn(reliance, "buy", "10", "400", datetime(2015, 6, 1)),
        FakeTxn(reliance, "sell", "10", "1500", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    # Cost steps up 400 -> 960, so the gain is 540/share, not 1100.
    assert result["summary"]["total_ltcg"] == pytest.approx(5400.0)
    assert "RELIANCE.NS" in result["summary"]["grandfathered_symbols"]


def test_step_up_is_capped_at_the_sale_price(reliance, fmv_table):
    """Where FMV exceeds the sale price, the sale price caps the step-up."""
    fmv_table({"RELIANCE": "2000"})

    txns = [
        FakeTxn(reliance, "buy", "10", "400", datetime(2015, 6, 1)),
        FakeTxn(reliance, "sell", "10", "900", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    # min(FMV 2000, sale 900) = 900, so cost = max(400, 900) = 900 -> zero gain.
    assert result["summary"]["total_ltcg"] == pytest.approx(0.0)


def test_step_up_never_lowers_the_cost_below_actual(reliance, fmv_table):
    """An FMV below actual cost gives no benefit and no penalty."""
    fmv_table({"RELIANCE": "300"})

    txns = [
        FakeTxn(reliance, "buy", "10", "400", datetime(2015, 6, 1)),
        FakeTxn(reliance, "sell", "10", "1500", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_ltcg"] == pytest.approx(11000.0)


def test_post_cutoff_purchases_are_not_grandfathered(reliance, fmv_table):
    fmv_table({"RELIANCE": "960"})

    txns = [
        FakeTxn(reliance, "buy", "10", "400", datetime(2018, 2, 1)),
        FakeTxn(reliance, "sell", "10", "1500", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_ltcg"] == pytest.approx(11000.0)
    assert result["summary"]["grandfathered_symbols"] == []


def test_short_term_lots_are_never_grandfathered(reliance, fmv_table):
    """The step-up only exists to shelter long-term gains."""
    fmv_table({"RELIANCE": "960"})

    txns = [
        FakeTxn(reliance, "buy", "10", "400", datetime(2018, 1, 1)),
        FakeTxn(reliance, "sell", "10", "1500", datetime(2018, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_stcg"] == pytest.approx(11000.0)


def test_missing_fmv_is_reported_rather_than_silently_skipped(reliance, fmv_table):
    """An eligible lot with no FMV on file must surface as a known gap."""
    fmv_table({"TCS": "3000"})

    txns = [
        FakeTxn(reliance, "buy", "10", "400", datetime(2015, 6, 1)),
        FakeTxn(reliance, "sell", "10", "1500", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["symbols_missing_fmv"] == ["RELIANCE.NS"]
    # Gain is computed without the benefit, i.e. overstated - which is exactly
    # why it is flagged.
    assert result["summary"]["total_ltcg"] == pytest.approx(11000.0)


def test_fmv_lookup_ignores_the_exchange_suffix(fmv_table):
    fmv_table({"RELIANCE": "960"})

    assert grandfathering.get_fmv("RELIANCE.NS") == Decimal("960")
    assert grandfathering.get_fmv("RELIANCE.BO") == Decimal("960")
    assert grandfathering.get_fmv("reliance") == Decimal("960")
    assert grandfathering.get_fmv("UNKNOWN") is None


# ─────────────────────────────────────────────────────────────────────────────
# Mixed inputs and edge cases
# ─────────────────────────────────────────────────────────────────────────────

def test_naive_and_aware_dates_can_be_mixed(reliance):
    """Manual entries are naive, broker imports are aware; both must compare."""
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2024, 1, 1, tzinfo=timezone.utc)),
        FakeTxn(reliance, "sell", "10", "200", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_stcg"] == pytest.approx(1000.0)


def test_multiple_symbols_are_kept_separate(reliance):
    tcs = FakeAsset("TCS.NS", "Tata Consultancy Services", Decimal("4000"))
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2024, 1, 1)),
        FakeTxn(reliance, "sell", "10", "200", datetime(2024, 6, 1)),
        FakeTxn(tcs, "buy", "5", "1000", datetime(2024, 1, 1)),
        FakeTxn(tcs, "sell", "5", "1100", datetime(2024, 6, 1)),
    ]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["by_symbol"]["RELIANCE.NS"]["stcg_gain"] == pytest.approx(1000.0)
    assert result["by_symbol"]["TCS.NS"]["stcg_gain"] == pytest.approx(500.0)
    assert result["summary"]["total_stcg"] == pytest.approx(1500.0)


def test_a_sell_with_no_matching_buy_does_not_crash(reliance):
    """Corrupt or partial history must degrade, not raise."""
    txns = [FakeTxn(reliance, "sell", "10", "200", datetime(2024, 6, 1))]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_stcg"] == pytest.approx(0.0)


def test_unsold_holdings_produce_no_realized_gain(reliance):
    txns = [FakeTxn(reliance, "buy", "10", "100", datetime(2024, 1, 1))]

    result = TaxCalculator.calculate_capital_gains(txns)

    assert result["summary"]["total_stcg"] == pytest.approx(0.0)
    assert result["summary"]["total_ltcg"] == pytest.approx(0.0)


def test_unrealized_gain_uses_the_same_cost_basis_as_a_sale(reliance):
    """A lot's unrealized gain must not jump the moment it is sold."""
    txns = [FakeTxn(reliance, "buy", "10", "1000", datetime(2024, 1, 1), brokerage="100")]

    result = TaxCalculator.calculate_capital_gains(txns, include_unrealized=True)

    # Current price 1500, cost 1000 + 10/unit brokerage = 1010.
    assert result["by_symbol"]["RELIANCE.NS"]["unrealized_gain"] == pytest.approx(4900.0)


def test_empty_transaction_list_returns_a_zeroed_report():
    result = TaxCalculator.calculate_capital_gains([])

    assert result["summary"]["total_tax"] == pytest.approx(0.0)
    assert result["by_symbol"] == {}


def test_available_financial_years_are_newest_first(reliance):
    txns = [
        FakeTxn(reliance, "buy", "10", "100", datetime(2022, 5, 1)),
        FakeTxn(reliance, "sell", "10", "200", datetime(2024, 2, 1)),  # FY 2023-24
    ]

    years = TaxCalculator.get_available_financial_years(txns)

    assert years == ["2023-24", "2022-23"]


def test_charges_from_another_fy_are_not_counted_in_this_ones_total(reliance):
    """An earlier year's trading costs belong to that year's report."""
    txns = [
        FakeTxn(reliance, "buy", "20", "100", datetime(2023, 1, 1), brokerage="200"),
        FakeTxn(reliance, "sell", "10", "150", datetime(2023, 6, 1), brokerage="50"),
        FakeTxn(reliance, "sell", "10", "150", datetime(2024, 6, 1), brokerage="70"),
    ]

    fy23 = TaxCalculator.calculate_capital_gains(txns, financial_year="2023-24")
    fy24 = TaxCalculator.calculate_capital_gains(txns, financial_year="2024-25")

    # Each year sees half the buy-side brokerage plus its own sell-side cost.
    assert fy23["summary"]["total_charges"] == pytest.approx(150.0)
    assert fy24["summary"]["total_charges"] == pytest.approx(170.0)
