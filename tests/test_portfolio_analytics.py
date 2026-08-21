"""Tests for the portfolio performance metrics.

The point of these is that every function refuses to answer rather than
guessing: a series too short to annualise, cash flows with no sign change, or
a portfolio with no starting capital all return ``None``, because a wrong
return figure is worse than a blank one.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from portfolio_tracker.services.portfolio_analytics import (
    annualise,
    annualised_volatility,
    max_drawdown,
    twr,
    xirr,
)

# ─────────────────────────────────────────────────────────────────────────────
# XIRR
# ─────────────────────────────────────────────────────────────────────────────

def test_xirr_of_a_simple_doubling_over_one_year():
    flows = [
        (datetime(2024, 1, 1), Decimal("-100000")),
        (datetime(2025, 1, 1), Decimal("200000")),
    ]

    assert xirr(flows) == pytest.approx(1.0, abs=0.01)


def test_xirr_of_a_flat_holding_is_zero():
    flows = [
        (datetime(2024, 1, 1), Decimal("-50000")),
        (datetime(2025, 1, 1), Decimal("50000")),
    ]

    assert xirr(flows) == pytest.approx(0.0, abs=1e-6)


def test_xirr_of_a_loss_is_negative():
    flows = [
        (datetime(2024, 1, 1), Decimal("-100000")),
        (datetime(2025, 1, 1), Decimal("80000")),
    ]

    result = xirr(flows)

    assert result is not None
    assert result == pytest.approx(-0.2, abs=0.01)


def test_xirr_handles_staggered_contributions():
    """The whole point of XIRR: later money earns for less time."""
    flows = [
        (datetime(2024, 1, 1), Decimal("-100000")),
        (datetime(2024, 7, 1), Decimal("-100000")),
        (datetime(2025, 1, 1), Decimal("220000")),
    ]

    result = xirr(flows)

    assert result is not None
    # A naive (220000-200000)/200000 would read 10%; money-weighted is higher
    # because half the capital was only deployed for six months.
    assert result > 0.13


def test_xirr_solves_an_irregular_flow_schedule():
    """Four flows at irregular dates, both directions.

    The expected rate is the root of the NPV equation for these flows, checked
    below by asserting the NPV actually vanishes there - so this test pins the
    answer to the mathematics rather than to a copied constant.
    """
    flows = [
        (datetime(2023, 1, 1), Decimal("-10000")),
        (datetime(2023, 6, 15), Decimal("-5000")),
        (datetime(2024, 3, 1), Decimal("3000")),
        (datetime(2024, 12, 31), Decimal("15000")),
    ]

    result = xirr(flows)

    assert result is not None
    assert result == pytest.approx(0.11270856, abs=1e-5)

    # The rate is only correct if it discounts the flows to zero.
    t0 = flows[0][0]
    npv = sum(
        float(amount) / (1 + result) ** ((when - t0).days / 365.0)
        for when, amount in flows
    )
    assert npv == pytest.approx(0.0, abs=1e-3)


def test_xirr_returns_none_without_a_sign_change():
    """All money in and none out has no rate of return."""
    flows = [
        (datetime(2024, 1, 1), Decimal("-100")),
        (datetime(2025, 1, 1), Decimal("-100")),
    ]

    assert xirr(flows) is None


def test_xirr_returns_none_for_a_span_too_short_to_annualise():
    """A 2% move over five days is not a 300% annual return."""
    flows = [
        (datetime(2024, 1, 1), Decimal("-100000")),
        (datetime(2024, 1, 6), Decimal("102000")),
    ]

    assert xirr(flows) is None


def test_xirr_returns_none_for_a_single_flow():
    assert xirr([(datetime(2024, 1, 1), Decimal("-100"))]) is None


def test_xirr_returns_none_for_no_flows():
    assert xirr([]) is None


def test_xirr_survives_a_total_loss():
    """A wipeout must return -100% or None, never raise."""
    flows = [
        (datetime(2024, 1, 1), Decimal("-100000")),
        (datetime(2025, 1, 1), Decimal("1")),
    ]

    result = xirr(flows)

    assert result is None or result < -0.9


def test_xirr_accepts_unordered_flows():
    ordered = [
        (datetime(2024, 1, 1), Decimal("-100000")),
        (datetime(2025, 1, 1), Decimal("200000")),
    ]
    shuffled = list(reversed(ordered))

    assert xirr(shuffled) == pytest.approx(xirr(ordered), abs=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# TWR
# ─────────────────────────────────────────────────────────────────────────────

def test_twr_compounds_period_returns():
    # +10% then +10% = +21%
    periods = [(100.0, 110.0, 0.0), (110.0, 121.0, 0.0)]

    assert twr(periods) == pytest.approx(0.21, abs=1e-6)


def test_twr_removes_the_effect_of_a_contribution():
    """A deposit is not performance, and must not read as a gain."""
    # Started at 100, added 50 at period end, ended at 150: zero return.
    periods = [(100.0, 150.0, 50.0)]

    assert twr(periods) == pytest.approx(0.0, abs=1e-9)


def test_twr_removes_the_effect_of_a_withdrawal():
    periods = [(100.0, 50.0, -50.0)]

    assert twr(periods) == pytest.approx(0.0, abs=1e-9)


def test_twr_ignores_periods_with_no_starting_capital():
    """Money that was not yet invested cannot have earned a return."""
    periods = [(0.0, 100.0, 100.0), (100.0, 110.0, 0.0)]

    assert twr(periods) == pytest.approx(0.10, abs=1e-6)


def test_twr_returns_none_when_no_period_had_capital():
    assert twr([(0.0, 0.0, 0.0)]) is None
    assert twr([]) is None


def test_twr_and_xirr_agree_when_there_are_no_interim_flows():
    """With a single lump sum the two measures must not diverge."""
    periods = [(100.0, 110.0, 0.0), (110.0, 132.0, 0.0)]
    time_weighted = twr(periods)

    flows = [
        (datetime(2024, 1, 1), Decimal("-100")),
        (datetime(2025, 1, 1), Decimal("132")),
    ]

    assert time_weighted == pytest.approx(0.32, abs=1e-6)
    assert xirr(flows) == pytest.approx(0.32, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Annualisation
# ─────────────────────────────────────────────────────────────────────────────

def test_annualise_leaves_a_one_year_return_alone():
    assert annualise(0.20, 365) == pytest.approx(0.20, abs=1e-6)


def test_annualise_scales_up_a_six_month_return():
    result = annualise(0.10, 182)

    assert result is not None
    assert result == pytest.approx(0.21, abs=0.01)


def test_annualise_refuses_very_short_windows():
    assert annualise(0.02, 5) is None


def test_annualise_refuses_a_total_loss():
    assert annualise(-1.0, 365) is None


# ─────────────────────────────────────────────────────────────────────────────
# Drawdown and volatility
# ─────────────────────────────────────────────────────────────────────────────

def test_max_drawdown_finds_the_worst_peak_to_trough():
    values = [100.0, 120.0, 90.0, 130.0, 110.0]

    result = max_drawdown(values)

    assert result is not None
    # Worst is 120 -> 90, i.e. -25%.
    assert result["drawdown"] == pytest.approx(-0.25, abs=1e-6)
    assert result["peak"] == pytest.approx(120.0)
    assert result["trough"] == pytest.approx(90.0)


def test_max_drawdown_of_a_monotonic_rise_is_zero():
    assert max_drawdown([100.0, 110.0, 120.0])["drawdown"] == pytest.approx(0.0)


def test_max_drawdown_needs_at_least_two_points():
    assert max_drawdown([100.0]) is None
    assert max_drawdown([]) is None


def test_max_drawdown_tolerates_a_zero_start():
    """A portfolio that begins empty must not divide by zero."""
    result = max_drawdown([0.0, 100.0, 50.0])

    assert result is not None
    assert result["drawdown"] == pytest.approx(-0.5, abs=1e-6)


def test_volatility_of_a_flat_series_is_zero():
    assert annualised_volatility([100.0, 100.0, 100.0, 100.0]) == pytest.approx(0.0, abs=1e-9)


def test_volatility_rises_with_dispersion():
    steady = annualised_volatility([100.0, 101.0, 102.0, 103.0, 104.0])
    choppy = annualised_volatility([100.0, 120.0, 90.0, 130.0, 85.0])

    assert steady is not None and choppy is not None
    assert choppy > steady


def test_volatility_needs_enough_points():
    assert annualised_volatility([100.0, 110.0]) is None
    assert annualised_volatility([100.0]) is None


# ─────────────────────────────────────────────────────────────────────────────
# Ledger reconstruction
# ─────────────────────────────────────────────────────────────────────────────

from portfolio_tracker.services.portfolio_analytics import (  # noqa: E402
    _net_flow_between,
    _quantities_as_of,
)


def _txn(symbol, kind, qty, price, when):
    return {
        "symbol": symbol,
        "date": when,
        "type": kind,
        "quantity": Decimal(qty),
        "price": Decimal(price),
    }


def test_quantities_as_of_replays_only_trades_up_to_that_date():
    txns = [
        _txn("A", "buy", "10", "100", datetime(2024, 1, 1)),
        _txn("A", "buy", "5", "100", datetime(2024, 6, 1)),
        _txn("A", "sell", "3", "100", datetime(2024, 9, 1)),
    ]

    assert _quantities_as_of(txns, {}, datetime(2024, 3, 1)) == {"A": Decimal("10")}
    assert _quantities_as_of(txns, {}, datetime(2024, 7, 1)) == {"A": Decimal("15")}
    assert _quantities_as_of(txns, {}, datetime(2024, 12, 1)) == {"A": Decimal("12")}


def test_quantities_as_of_excludes_fully_sold_positions():
    txns = [
        _txn("A", "buy", "10", "100", datetime(2024, 1, 1)),
        _txn("A", "sell", "10", "150", datetime(2024, 6, 1)),
    ]

    assert _quantities_as_of(txns, {}, datetime(2024, 12, 1)) == {}


def test_opening_balances_cover_broker_holdings_with_no_trade_history():
    """A synced holding with no transactions must still appear in the series."""
    opening = {
        "B": {"quantity": Decimal("7"), "price": Decimal("500"), "since": datetime(2024, 2, 1)}
    }

    assert _quantities_as_of([], opening, datetime(2024, 1, 1)) == {}
    assert _quantities_as_of([], opening, datetime(2024, 3, 1)) == {"B": Decimal("7")}


def test_opening_balance_and_ledger_trades_combine():
    opening = {
        "A": {"quantity": Decimal("10"), "price": Decimal("100"), "since": datetime(2024, 1, 1)}
    }
    txns = [_txn("A", "buy", "5", "120", datetime(2024, 6, 1))]

    assert _quantities_as_of(txns, opening, datetime(2024, 7, 1)) == {"A": Decimal("15")}


def test_net_flow_counts_buys_positive_and_sells_negative():
    txns = [
        _txn("A", "buy", "10", "100", datetime(2024, 2, 1)),
        _txn("A", "sell", "5", "200", datetime(2024, 3, 1)),
        _txn("A", "buy", "1", "100", datetime(2024, 9, 1)),  # outside the window
    ]

    flow = _net_flow_between(txns, datetime(2024, 1, 1), datetime(2024, 6, 1))

    assert flow == pytest.approx(0.0)  # 1000 in, 1000 out


def test_net_flow_window_is_half_open_at_the_start():
    """A trade exactly on the window's opening boundary belongs to the prior period."""
    txns = [_txn("A", "buy", "10", "100", datetime(2024, 1, 1))]

    assert _net_flow_between(txns, datetime(2024, 1, 1), datetime(2024, 2, 1)) == pytest.approx(0.0)
    assert _net_flow_between(txns, datetime(2023, 12, 1), datetime(2024, 2, 1)) == pytest.approx(1000.0)
