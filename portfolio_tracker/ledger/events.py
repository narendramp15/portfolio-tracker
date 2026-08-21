"""Ledger events - the immutable record everything else is derived from.

A position is not stored. It is what the events say it is, folded in date
order. That inversion is what makes full history, per-stock XIRR, account-wise
capital gains and dividend attribution the same computation with different
reducers, instead of three features that drift apart.

Every event carries its provenance (``source`` and ``source_ref``) because the
same trade legitimately arrives from more than one place - a depository CAS
knows a transfer happened, a broker tradebook knows what it cost - and the
ledger has to merge those without double-counting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

#: Storage width of the instrument-key column. Keys longer than this are
#: rejected on construction, because the database truncates rather than errors.
MAX_INSTRUMENT_KEY_LENGTH = 24


class EventType(str, Enum):
    """What happened. Str-valued so it round-trips through the database."""

    # Cash-for-shares, the only two that move money in or out.
    BUY = "buy"
    SELL = "sell"

    # Income. Paid to a bank account, not the demat, which is why it needs its
    # own event rather than being inferred from a holding change.
    DIVIDEND = "dividend"

    # Movement between the investor's own demat accounts. Emphatically NOT a
    # sale: recorded as sell-plus-buy it invents a capital gain and resets the
    # cost basis to the transfer-day price.
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"

    # Corporate actions. Quantity and cost change; no money moves.
    SPLIT = "split"
    BONUS = "bonus"
    RIGHTS = "rights"
    DEMERGER = "demerger"
    MERGER = "merger"

    # History that predates anything we can source, or a broker-synced holding
    # whose trades were never available. Carries a cost basis so it can be
    # taxed, and is flagged so the UI can say the basis is inferred.
    OPENING_BALANCE = "opening_balance"


#: Events that increase the holding.
INFLOW_TYPES = frozenset(
    {
        EventType.BUY,
        EventType.TRANSFER_IN,
        EventType.BONUS,
        EventType.RIGHTS,
        EventType.OPENING_BALANCE,
    }
)

#: Events that decrease the holding.
OUTFLOW_TYPES = frozenset({EventType.SELL, EventType.TRANSFER_OUT})

#: Events that realise a taxable gain. A transfer out does not - the shares
#: are still owned, just held elsewhere.
TAXABLE_DISPOSAL_TYPES = frozenset({EventType.SELL})

#: Events that represent money the investor put in or took out, for XIRR.
#: Transfers are excluded: moving your own shares is not a contribution.
CASH_FLOW_TYPES = frozenset({EventType.BUY, EventType.SELL, EventType.DIVIDEND})


@dataclass(frozen=True)
class LedgerEvent:
    """One thing that happened to one instrument in one demat account.

    Frozen because the ledger is append-only. Correcting a mistake means
    appending a reversal, not editing history - otherwise a tax figure can
    change after it was filed, with no record of why.
    """

    isin: str
    event_type: EventType
    trade_date: datetime

    #: Which demat account. Load-bearing for tax: FIFO is applied account-wise
    #: for dematerialised securities (CBDT Circular 768), so lots must not be
    #: pooled across accounts.
    account: str = ""

    quantity: Decimal = Decimal("0")
    price: Decimal = Decimal("0")

    #: Deductible under Sec 48 as cost of acquisition or expense on transfer.
    brokerage: Decimal = Decimal("0")
    other_charges: Decimal = Decimal("0")
    #: Stored for reporting and expressly NOT deductible.
    stt: Decimal = Decimal("0")

    #: Ratio for corporate actions: 5 for a 1:5 split, so 1 share becomes 5.
    ratio: Decimal | None = None

    #: Total cash for a DIVIDEND, where per-share times quantity is not
    #: reliable (partial holdings across accounts, rounding by the registrar).
    amount: Decimal | None = None

    #: Where this came from, e.g. "cas_nsdl_2026_03" or "zerodha_tradebook".
    source: str = ""
    #: Stable identity within that source, for idempotent re-import. A broker
    #: order id, or a hash of the statement row.
    source_ref: str = ""

    symbol: str = ""  # display only; never an identity
    notes: str = ""
    metadata: dict = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if not self.isin:
            raise ValueError("LedgerEvent requires an ISIN - symbols are not identity")
        if len(self.isin) > MAX_INSTRUMENT_KEY_LENGTH:
            # The storage column is this wide. MariaDB truncates silently
            # rather than erroring, and a truncated key folds into lots that
            # nothing else can match - it once reported seventeen holdings as
            # zero. Fail here, where the cause is still visible.
            raise ValueError(
                f"instrument key {self.isin!r} exceeds "
                f"{MAX_INSTRUMENT_KEY_LENGTH} characters and would be truncated"
            )
        if self.quantity < 0:
            raise ValueError(
                f"quantity must be unsigned ({self.quantity}); direction comes "
                f"from event_type"
            )

    @property
    def deductible_charges(self) -> Decimal:
        """Charges that reduce a taxable gain. Excludes STT by statute."""
        return self.brokerage + self.other_charges

    @property
    def is_inflow(self) -> bool:
        return self.event_type in INFLOW_TYPES

    @property
    def is_outflow(self) -> bool:
        return self.event_type in OUTFLOW_TYPES

    @property
    def dedup_key(self) -> tuple[str, str]:
        """Identity for idempotent ingestion.

        Two imports of the same statement must not create two events. Where a
        source gives no stable reference, the caller is expected to synthesise
        one (see ``ingest.synthetic_ref``) rather than leave it blank.
        """
        return (self.source, self.source_ref)

    def replace(self, **changes) -> LedgerEvent:
        """Return a copy with fields changed, since events are frozen."""
        from dataclasses import replace as _replace

        return _replace(self, **changes)
