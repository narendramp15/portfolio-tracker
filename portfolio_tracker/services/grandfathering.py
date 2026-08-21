"""Section 112A grandfathering: the 31 January 2018 cost step-up.

When LTCG on listed equity became taxable from 1 April 2018, gains that had
already accrued up to 31 January 2018 were grandfathered. For anything bought
before 1 February 2018, the cost of acquisition becomes:

    higher of:
        (a) actual cost, and
        (b) lower of:
              (i)  fair market value on 31 Jan 2018, and
              (ii) the sale consideration

The FMV is the highest quoted price on 31 Jan 2018 (or the last trading day
before it, for a scrip not traded that day). It is a fixed historical figure,
so it lives in a static table rather than a live feed.

Symbols missing from the table get no step-up and are reported as such: a
silently un-grandfathered lot overstates the gain, and the user needs to know
which holdings that applied to so they can correct the figure before filing.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

# Grandfathering applies to acquisitions strictly before this date.
CUTOFF_DATE = datetime(2018, 2, 1)

# The valuation date whose price is used for the step-up.
VALUATION_DATE = datetime(2018, 1, 31)

# FMV table, supplied as data rather than code. Maps a bare symbol
# ("RELIANCE") to its 31-Jan-2018 fair market value as a decimal string.
#
# This ships EMPTY on purpose. The correct values are the highest quoted price
# for each scrip in the NSE/BSE bhavcopy for 31 January 2018 - authoritative,
# freely published, and unforgiving of transcription error. Hardcoding
# approximate figures here would put wrong numbers on a tax filing, which is
# worse than applying no step-up and saying so.
#
# To populate: download the 31-Jan-2018 bhavcopy, and write
# portfolio_tracker/data/fmv_31jan2018.json as {"RELIANCE": "961.85", ...}
_FMV_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "fmv_31jan2018.json"

_SEED_FMV: dict[str, str] = {}

_fmv_cache: dict[str, Decimal] | None = None


def _base_symbol(symbol: str) -> str:
    """Strip the Yahoo exchange suffix so RELIANCE.NS and RELIANCE both hit."""
    if not symbol:
        return ""
    return symbol.upper().split(".")[0].strip()


def _load_fmv_table() -> dict[str, Decimal]:
    """Seed table merged with the optional JSON override file."""
    global _fmv_cache
    if _fmv_cache is not None:
        return _fmv_cache

    table = {symbol: Decimal(value) for symbol, value in _SEED_FMV.items()}

    if _FMV_DATA_FILE.exists():
        try:
            with _FMV_DATA_FILE.open(encoding="utf-8") as handle:
                extra = json.load(handle)
            for symbol, value in extra.items():
                try:
                    table[_base_symbol(symbol)] = Decimal(str(value))
                except (TypeError, ArithmeticError):
                    logger.warning("Skipping unparseable FMV for %s: %r", symbol, value)
        except (OSError, json.JSONDecodeError):
            logger.warning("Could not read FMV table at %s", _FMV_DATA_FILE, exc_info=True)

    _fmv_cache = table
    return table


def reset_cache() -> None:
    """Drop the memoised table. Used by tests that write the override file."""
    global _fmv_cache
    _fmv_cache = None


def get_fmv(symbol: str) -> Decimal | None:
    """Fair market value per share on 31 Jan 2018, or ``None`` if unknown."""
    return _load_fmv_table().get(_base_symbol(symbol))


def is_eligible(buy_date: datetime, holding_days: int, ltcg_threshold_days: int) -> bool:
    """Whether a lot qualifies for the step-up.

    Grandfathering only helps a long-term gain on something acquired before
    1 Feb 2018; short-term lots and later acquisitions are unaffected.
    """
    if buy_date is None:
        return False
    naive = buy_date.replace(tzinfo=None) if buy_date.tzinfo else buy_date
    return naive < CUTOFF_DATE and holding_days >= ltcg_threshold_days


def stepped_up_cost(
    symbol: str,
    actual_cost: Decimal,
    sale_price: Decimal,
) -> tuple[Decimal, bool]:
    """Apply the Section 112A cost step-up to a single share's cost.

    Args:
        symbol: Ticker, with or without an exchange suffix.
        actual_cost: What the share actually cost, per share.
        sale_price: Sale consideration per share.

    Returns:
        ``(cost, applied)`` - the cost of acquisition to use, and whether the
        step-up changed it. ``applied`` is ``False`` both when no FMV is known
        and when the FMV gives no benefit, so callers can distinguish "no data"
        by checking :func:`get_fmv` separately.
    """
    fmv = get_fmv(symbol)
    if fmv is None:
        return actual_cost, False

    # Lower of FMV and sale consideration, then higher of that and actual cost.
    candidate = min(fmv, sale_price)
    stepped = max(actual_cost, candidate)
    return stepped, stepped != actual_cost
