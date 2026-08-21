"""Source adapters: one contract for every place events come from.

Adding a broker, a statement format or a new depository should mean writing one
adapter and registering it - never touching the lot engine, the tax calculator
or the API. That is the whole point of this seam.

An adapter's only job is to turn some input into ``LedgerEvent`` objects and
resolve identity to an ISIN. It does no persistence, no deduplication and no
folding; ``ingest`` and ``lots`` own those. Keeping adapters pure means a new
one is testable from a fixture file with no database at all.

    class MyBrokerTradebook:
        name = "mybroker_tradebook"
        kind = SourceKind.TRADEBOOK

        def parse(self, payload, context):
            yield LedgerEvent(...)

    register(MyBrokerTradebook())
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from portfolio_tracker.ledger.events import LedgerEvent


class SourceKind(str, Enum):
    """What a source is authoritative for.

    This drives conflict resolution. When two sources describe the same trade,
    the one that is authoritative for the field wins: a depository statement
    knows a transfer happened, a tradebook knows what it cost. Neither is
    "better" - they are authoritative for different columns.
    """

    #: Depository consolidated statement. Authoritative for what moved, when,
    #: in which account, across every demat under a PAN. Carries no prices.
    DEPOSITORY = "depository"

    #: Broker trade export. Authoritative for execution price and charges,
    #: for one broker only.
    TRADEBOOK = "tradebook"

    #: Live broker API. Authoritative for current holdings; on most Indian
    #: brokers it can only see the current day's trades.
    BROKER_API = "broker_api"

    #: Registrar statement for mutual funds (CAMS / KFintech).
    REGISTRAR = "registrar"

    #: Annual Information Statement from the tax portal. Authoritative for
    #: dividends actually received, and for TDS.
    TAX_STATEMENT = "tax_statement"

    #: Exchange or vendor corporate-action feed.
    CORPORATE_ACTIONS = "corporate_actions"

    #: Typed in or uploaded by the user. Lowest precedence, but never silently
    #: overwritten - a person correcting their own record should win over a
    #: guess, and only lose to an authoritative statement.
    MANUAL = "manual"


#: Which kind wins when two sources disagree about a field, highest first.
#: Read as: prices come from a tradebook before a depository guess; movements
#: come from the depository before a broker's partial view.
PRICE_PRECEDENCE = (
    SourceKind.TRADEBOOK,
    SourceKind.BROKER_API,
    SourceKind.MANUAL,
    SourceKind.REGISTRAR,
    SourceKind.DEPOSITORY,
)

MOVEMENT_PRECEDENCE = (
    SourceKind.DEPOSITORY,
    SourceKind.TRADEBOOK,
    SourceKind.BROKER_API,
    SourceKind.REGISTRAR,
    SourceKind.MANUAL,
)

DIVIDEND_PRECEDENCE = (
    SourceKind.TAX_STATEMENT,
    SourceKind.DEPOSITORY,
    SourceKind.BROKER_API,
    SourceKind.MANUAL,
    SourceKind.CORPORATE_ACTIONS,
)


@dataclass
class ParseContext:
    """Everything an adapter may need that is not in the payload itself.

    Passed in rather than looked up so adapters stay pure and testable.
    """

    user_id: int | None = None
    #: Maps a broker/DP identifier to the account label events should carry.
    account_hint: str = ""
    #: Symbol to ISIN, for sources that give no ISIN (most tradebooks).
    isin_by_symbol: dict[str, str] = field(default_factory=dict)
    #: Password for an encrypted statement PDF.
    password: str | None = None
    options: dict = field(default_factory=dict)


@dataclass
class ParseResult:
    """What an adapter produced, plus what it could not."""

    events: list[LedgerEvent] = field(default_factory=list)
    #: Rows that could not be turned into events, with a reason. Reported to
    #: the user rather than dropped: a skipped row is a hole in their history.
    skipped: list[tuple[str, str]] = field(default_factory=list)
    #: Symbols the adapter could not resolve to an ISIN.
    unresolved_symbols: set[str] = field(default_factory=set)
    detected_format: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.events)


@runtime_checkable
class SourceAdapter(Protocol):
    """The contract. Implement, register, done."""

    #: Stable identifier, stored on every event as ``source``.
    name: str
    kind: SourceKind

    def sniff(self, payload: bytes | str) -> bool:
        """Cheaply decide whether this adapter recognises the payload.

        Lets the API accept "here is a file" without the user having to say
        which of a dozen formats it is.
        """
        ...

    def parse(self, payload: bytes | str, context: ParseContext) -> ParseResult:
        """Turn the payload into events. Pure: no I/O, no persistence."""
        ...


_REGISTRY: dict[str, SourceAdapter] = {}


def register(adapter: SourceAdapter) -> SourceAdapter:
    """Add an adapter to the registry. Usable as a decorator."""
    if adapter.name in _REGISTRY:
        raise ValueError(f"source adapter {adapter.name!r} is already registered")
    _REGISTRY[adapter.name] = adapter
    return adapter


def get(name: str) -> SourceAdapter | None:
    return _REGISTRY.get(name)


def all_adapters() -> list[SourceAdapter]:
    return list(_REGISTRY.values())


def adapters_of_kind(kind: SourceKind) -> list[SourceAdapter]:
    return [a for a in _REGISTRY.values() if a.kind is kind]


def detect(payload: bytes | str) -> SourceAdapter | None:
    """Find the adapter that recognises this payload, if any."""
    for adapter in _REGISTRY.values():
        try:
            if adapter.sniff(payload):
                return adapter
        except Exception:  # a broken sniffer must not block the others
            continue
    return None


def clear_registry() -> None:
    """Empty the registry. For tests only."""
    _REGISTRY.clear()


def synthetic_ref(*parts) -> str:
    """A stable dedup reference for sources with no natural identifier.

    Most statements have no order id, so identity has to come from the content
    of the row. Hashing the meaningful fields means re-importing the same
    statement is a no-op, while a genuinely different row still lands.
    """
    joined = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:32]
