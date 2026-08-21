"""The ledger: an append-only event store and the pure fold over it.

Everything a portfolio manager needs to answer is one fold with a different
reducer, rather than three features that drift apart:

    from portfolio_tracker.ledger import fold

    book = fold(events)
    book.open_lots      # holdings, per (ISIN, demat account)
    book.disposals      # capital gains, already matched lot by lot
    book.cash_flows     # dated flows for XIRR
    book.dividends      # income, per instrument
    book.unmatched      # what could not be explained, and why

Design rules worth keeping:

* Identity is the ISIN. Symbols are display and market-data lookup only -
  "RELIANCE" and "RELIANCE.NS" are one instrument.
* Events are immutable. Corrections are appended, never edited, so a filed tax
  figure cannot silently change.
* The fold is pure. No session, no clock, no network - so it is testable and
  cacheable.
* FIFO is applied per demat account, per CBDT Circular 768.
* A transfer between the investor's own accounts preserves cost basis and
  acquisition date. It is not a disposal.
* Anything that cannot be explained lands in ``unmatched`` rather than being
  quietly absorbed into a number.
"""

from portfolio_tracker.ledger.events import (
    CASH_FLOW_TYPES,
    INFLOW_TYPES,
    OUTFLOW_TYPES,
    TAXABLE_DISPOSAL_TYPES,
    EventType,
    LedgerEvent,
)
from portfolio_tracker.ledger.instruments import (
    canonical_symbol,
    is_valid_isin,
    normalise_isin,
)
from portfolio_tracker.ledger.lots import (
    Disposal,
    Lot,
    LotBook,
    fold,
    holding_period_end,
    market_value,
    unrealised,
)
from portfolio_tracker.ledger.sources import (
    ParseContext,
    ParseResult,
    SourceAdapter,
    SourceKind,
    register,
    synthetic_ref,
)

__all__ = [
    # events
    "EventType",
    "LedgerEvent",
    "INFLOW_TYPES",
    "OUTFLOW_TYPES",
    "CASH_FLOW_TYPES",
    "TAXABLE_DISPOSAL_TYPES",
    # instruments
    "normalise_isin",
    "is_valid_isin",
    "canonical_symbol",
    # lots
    "fold",
    "Lot",
    "LotBook",
    "Disposal",
    "unrealised",
    "market_value",
    "holding_period_end",
    # sources
    "SourceAdapter",
    "SourceKind",
    "ParseContext",
    "ParseResult",
    "register",
    "synthetic_ref",
]
