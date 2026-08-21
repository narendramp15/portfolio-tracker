"""The lot engine: fold events into holdings, disposals and cash flows.

Pure by design. No database, no network, no clock - everything comes in as
arguments and comes out as values. That is what makes account-wise FIFO,
basis-preserving transfers and corporate actions testable at all, and it means
the result can be cached or snapshotted without dragging a session around.

The three things every caller wants come out of one fold:

    book = fold(events)
    book.open_lots      -> holdings, and the input to XIRR's terminal value
    book.disposals      -> capital gains, already matched lot by lot
    book.cash_flows     -> dated flows for XIRR

Two rules drive most of the complexity here, and both are easy to get wrong:

* **FIFO is applied per demat account.** For dematerialised securities, where
  an investor holds more than one account, shares in one account cannot be
  construed as sold when another account is debited (CBDT Circular 768). Lots
  are therefore keyed on ``(isin, account)``.

* **A transfer preserves cost basis and acquisition date.** Moving shares
  between your own demats is not a disposal, and the holding period continues
  to run from the original purchase. Recording it as a sale plus a purchase
  invents a gain and resets the clock - turning a long-term holding into a
  short-term one.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from portfolio_tracker.ledger.events import (
    CASH_FLOW_TYPES,
    EventType,
    LedgerEvent,
)

logger = logging.getLogger(__name__)

#: A transfer out and the matching transfer in are separate statement rows,
#: often dated a day or two apart. Within this window, and for the same ISIN
#: and quantity, they are treated as two halves of one movement.
TRANSFER_PAIRING_DAYS = 7


def _naive(value: datetime) -> datetime:
    """Strip tzinfo so mixed naive/aware rows compare without raising."""
    if value is None:
        return datetime.min
    return value.replace(tzinfo=None) if value.tzinfo else value


@dataclass
class Lot:
    """A parcel of shares acquired at one cost, in one account.

    ``acquired`` is the date that governs the holding period, which survives
    transfers between accounts. ``basis_inferred`` marks a lot whose cost came
    from an opening balance rather than a real trade, so a tax report can say
    so instead of implying precision it does not have.
    """

    isin: str
    account: str
    quantity: Decimal
    #: Cost per unit including deductible acquisition charges.
    cost_per_unit: Decimal
    acquired: datetime
    source: str = ""
    basis_inferred: bool = False
    symbol: str = ""

    @property
    def cost(self) -> Decimal:
        return self.quantity * self.cost_per_unit

    def take(self, quantity: Decimal) -> Lot:
        """Split off ``quantity`` units, reducing this lot in place."""
        if quantity > self.quantity:
            raise ValueError(f"cannot take {quantity} from a lot of {self.quantity}")
        self.quantity -= quantity
        return Lot(
            isin=self.isin,
            account=self.account,
            quantity=quantity,
            cost_per_unit=self.cost_per_unit,
            acquired=self.acquired,
            source=self.source,
            basis_inferred=self.basis_inferred,
            symbol=self.symbol,
        )


@dataclass
class Disposal:
    """One sale matched against one lot - the unit a gain is computed from."""

    isin: str
    account: str
    quantity: Decimal
    acquired: datetime
    disposed: datetime
    cost_per_unit: Decimal
    #: Sale price per unit, net of expenses on transfer.
    net_proceeds_per_unit: Decimal
    charges: Decimal = Decimal("0")
    stt: Decimal = Decimal("0")
    basis_inferred: bool = False
    symbol: str = ""

    @property
    def holding_days(self) -> int:
        return (_naive(self.disposed) - _naive(self.acquired)).days

    @property
    def gain(self) -> Decimal:
        return self.quantity * (self.net_proceeds_per_unit - self.cost_per_unit)


@dataclass
class LotBook:
    """The result of folding a stream of events."""

    #: Open lots keyed by (isin, account), each list in acquisition order.
    lots: dict[tuple[str, str], list[Lot]] = field(default_factory=dict)
    disposals: list[Disposal] = field(default_factory=list)
    #: (date, signed amount) from the investor's perspective: negative in.
    cash_flows: list[tuple[datetime, Decimal]] = field(default_factory=list)
    dividends: list[tuple[datetime, str, Decimal]] = field(default_factory=list)
    #: Events that could not be applied, with the reason, for reporting back.
    unmatched: list[tuple[LedgerEvent, str]] = field(default_factory=list)

    @property
    def open_lots(self) -> list[Lot]:
        return [lot for parcel in self.lots.values() for lot in parcel if lot.quantity > 0]

    def quantity(self, isin: str, account: str | None = None) -> Decimal:
        """Units held, in one account or across all of them."""
        total = Decimal("0")
        for (lot_isin, lot_account), parcel in self.lots.items():
            if lot_isin != isin:
                continue
            if account is not None and lot_account != account:
                continue
            total += sum((lot.quantity for lot in parcel), Decimal("0"))
        return total

    def cost(self, isin: str, account: str | None = None) -> Decimal:
        """Cost basis of what is still held."""
        total = Decimal("0")
        for (lot_isin, lot_account), parcel in self.lots.items():
            if lot_isin != isin:
                continue
            if account is not None and lot_account != account:
                continue
            total += sum((lot.cost for lot in parcel), Decimal("0"))
        return total

    def dividend_total(self, isin: str | None = None) -> Decimal:
        return sum(
            (amount for _, div_isin, amount in self.dividends if isin in (None, div_isin)),
            Decimal("0"),
        )


def _key(event: LedgerEvent) -> tuple[str, str]:
    return (event.isin, event.account)


def _consume_fifo(parcel: list[Lot], quantity: Decimal) -> list[Lot]:
    """Remove ``quantity`` units from the oldest lots first.

    Returns the taken slices. Consumes as much as is available and no more -
    the caller decides whether a shortfall is an error or an inferred lot.
    """
    taken: list[Lot] = []
    remaining = quantity
    for lot in parcel:
        if remaining <= 0:
            break
        if lot.quantity <= 0:
            continue
        matched = min(lot.quantity, remaining)
        taken.append(lot.take(matched))
        remaining -= matched
    parcel[:] = [lot for lot in parcel if lot.quantity > 0]
    return taken


def _pair_transfers(events: Sequence[LedgerEvent]) -> dict[int, int]:
    """Match each TRANSFER_OUT to the TRANSFER_IN that completes it.

    Returns a map of ``id(out_event) -> id(in_event)``. Pairing lets the
    incoming side inherit the outgoing side's lots, which is the whole point:
    cost basis and acquisition date have to survive the move.
    """
    outs = [e for e in events if e.event_type is EventType.TRANSFER_OUT]
    ins = [e for e in events if e.event_type is EventType.TRANSFER_IN]
    pairs: dict[int, int] = {}
    claimed: set[int] = set()

    for out in outs:
        for incoming in ins:
            if id(incoming) in claimed:
                continue
            if incoming.isin != out.isin or incoming.quantity != out.quantity:
                continue
            gap = abs((_naive(incoming.trade_date) - _naive(out.trade_date)).days)
            if gap > TRANSFER_PAIRING_DAYS:
                continue
            if incoming.account == out.account:
                continue
            pairs[id(out)] = id(incoming)
            claimed.add(id(incoming))
            break

    return pairs


def fold(events: Iterable[LedgerEvent]) -> LotBook:
    """Replay events in date order into lots, disposals and cash flows.

    Events are sorted by trade date, with inflows settled before outflows on
    the same date so a same-day buy-then-sell matches rather than reporting a
    phantom short.
    """
    ordered = sorted(
        events,
        key=lambda e: (_naive(e.trade_date), 0 if e.is_inflow else 1),
    )
    book = LotBook()
    transfer_pairs = _pair_transfers(ordered)
    #: Lots lifted out by a TRANSFER_OUT, waiting for their TRANSFER_IN.
    in_flight: dict[int, list[Lot]] = {}

    for event in ordered:
        key = _key(event)
        parcel = book.lots.setdefault(key, [])
        kind = event.event_type

        if kind in (EventType.BUY, EventType.OPENING_BALANCE):
            charges_per_unit = (
                event.deductible_charges / event.quantity if event.quantity else Decimal("0")
            )
            parcel.append(
                Lot(
                    isin=event.isin,
                    account=event.account,
                    quantity=event.quantity,
                    cost_per_unit=event.price + charges_per_unit,
                    acquired=event.trade_date,
                    source=event.source,
                    basis_inferred=kind is EventType.OPENING_BALANCE,
                    symbol=event.symbol,
                )
            )

        elif kind is EventType.BONUS:
            # Free shares. Cost of acquisition is nil; the holding period runs
            # from the allotment date, not from the original purchase.
            parcel.append(
                Lot(
                    isin=event.isin,
                    account=event.account,
                    quantity=event.quantity,
                    cost_per_unit=Decimal("0"),
                    acquired=event.trade_date,
                    source=event.source,
                    symbol=event.symbol,
                )
            )

        elif kind is EventType.RIGHTS:
            parcel.append(
                Lot(
                    isin=event.isin,
                    account=event.account,
                    quantity=event.quantity,
                    cost_per_unit=event.price,
                    acquired=event.trade_date,
                    source=event.source,
                    symbol=event.symbol,
                )
            )

        elif kind is EventType.SPLIT:
            # Quantity scales up, cost per unit scales down, and critically the
            # acquisition date is untouched: a split does not restart the
            # holding period.
            # `or` would be wrong here: Decimal("0") is falsy, so a zero ratio
            # would silently become 1 and skip the guard below.
            ratio = event.ratio if event.ratio is not None else Decimal("1")
            if ratio <= 0:
                book.unmatched.append((event, "split ratio must be positive"))
                continue
            for lot in parcel:
                lot.quantity *= ratio
                lot.cost_per_unit /= ratio

        elif kind is EventType.SELL:
            taken = _consume_fifo(parcel, event.quantity)
            matched = sum((lot.quantity for lot in taken), Decimal("0"))
            if matched < event.quantity:
                # More sold than the ledger can account for. Rather than
                # silently booking the whole proceeds as gain, record an
                # inferred zero-cost lot and say so.
                shortfall = event.quantity - matched
                book.unmatched.append(
                    (event, f"{shortfall} units sold with no acquisition on record")
                )
                taken.append(
                    Lot(
                        isin=event.isin,
                        account=event.account,
                        quantity=shortfall,
                        cost_per_unit=Decimal("0"),
                        acquired=event.trade_date,
                        basis_inferred=True,
                        symbol=event.symbol,
                    )
                )

            charges_per_unit = (
                event.deductible_charges / event.quantity if event.quantity else Decimal("0")
            )
            for lot in taken:
                share = (lot.quantity / event.quantity) if event.quantity else Decimal("0")
                book.disposals.append(
                    Disposal(
                        isin=event.isin,
                        account=event.account,
                        quantity=lot.quantity,
                        acquired=lot.acquired,
                        disposed=event.trade_date,
                        cost_per_unit=lot.cost_per_unit,
                        net_proceeds_per_unit=event.price - charges_per_unit,
                        charges=event.deductible_charges * share,
                        stt=event.stt * share,
                        basis_inferred=lot.basis_inferred,
                        symbol=event.symbol or lot.symbol,
                    )
                )

        elif kind is EventType.TRANSFER_OUT:
            taken = _consume_fifo(parcel, event.quantity)
            matched = sum((lot.quantity for lot in taken), Decimal("0"))
            if matched < event.quantity:
                shortfall = event.quantity - matched
                taken.append(
                    Lot(
                        isin=event.isin,
                        account=event.account,
                        quantity=shortfall,
                        cost_per_unit=event.price,
                        acquired=event.trade_date,
                        basis_inferred=True,
                        symbol=event.symbol,
                    )
                )
                book.unmatched.append(
                    (event, f"{shortfall} units transferred out with no acquisition on record")
                )
            # Held until the matching TRANSFER_IN claims them. Deliberately no
            # disposal is recorded: the shares are still owned.
            in_flight[id(event)] = taken

        elif kind is EventType.TRANSFER_IN:
            inherited: list[Lot] = []
            for out_id, in_id in transfer_pairs.items():
                if in_id == id(event) and out_id in in_flight:
                    inherited = in_flight.pop(out_id)
                    break

            if inherited:
                for lot in inherited:
                    # Same cost, same acquisition date, new account.
                    lot.account = event.account
                    parcel.append(lot)
            else:
                # An unpaired inbound transfer: shares arrived and we never saw
                # them leave. Best available basis is whatever the source gave,
                # flagged as inferred.
                parcel.append(
                    Lot(
                        isin=event.isin,
                        account=event.account,
                        quantity=event.quantity,
                        cost_per_unit=event.price,
                        acquired=event.trade_date,
                        source=event.source,
                        basis_inferred=True,
                        symbol=event.symbol,
                    )
                )
                book.unmatched.append(
                    (event, "inbound transfer with no matching outbound; cost basis inferred")
                )

        elif kind is EventType.DIVIDEND:
            amount = event.amount
            if amount is None:
                amount = event.quantity * event.price
            book.dividends.append((event.trade_date, event.isin, amount))

        elif kind in (EventType.DEMERGER, EventType.MERGER):
            # Needs the resulting instrument and a cost-apportionment ratio,
            # which the current sources do not carry. Surfaced rather than
            # applied, so a portfolio containing one is visibly incomplete
            # instead of quietly wrong.
            book.unmatched.append((event, f"{kind.value} not yet applied"))

        # Cash flows, for XIRR. Transfers are excluded on purpose: moving your
        # own shares between your own accounts is not a contribution.
        if kind in CASH_FLOW_TYPES:
            if kind is EventType.BUY:
                book.cash_flows.append(
                    (event.trade_date, -(event.quantity * event.price + event.deductible_charges))
                )
            elif kind is EventType.SELL:
                book.cash_flows.append(
                    (event.trade_date, event.quantity * event.price - event.deductible_charges)
                )
            elif kind is EventType.DIVIDEND:
                amount = event.amount if event.amount is not None else event.quantity * event.price
                book.cash_flows.append((event.trade_date, amount))

    # Anything still in flight left an account and never arrived anywhere.
    for out_id, lots in in_flight.items():
        book.unmatched.append(
            (
                next(e for e in ordered if id(e) == out_id),
                "outbound transfer with no matching inbound; shares unaccounted for",
            )
        )
        # Keep them somewhere rather than losing them from the portfolio.
        for lot in lots:
            book.lots.setdefault((lot.isin, lot.account), []).append(lot)

    return book


def unrealised(book: LotBook, prices: dict[str, Decimal]) -> Decimal:
    """Mark open lots to market. ``prices`` is keyed on ISIN."""
    total = Decimal("0")
    for lot in book.open_lots:
        price = prices.get(lot.isin)
        if price is not None:
            total += lot.quantity * (price - lot.cost_per_unit)
    return total


def market_value(book: LotBook, prices: dict[str, Decimal]) -> Decimal:
    """Current value of open lots, for XIRR's terminal flow."""
    total = Decimal("0")
    for lot in book.open_lots:
        price = prices.get(lot.isin)
        if price is not None:
            total += lot.quantity * price
    return total


def holding_period_end(acquired: datetime, days: int = 365) -> datetime:
    """When a lot crosses into long-term. Useful for a 'wait N days' prompt."""
    return _naive(acquired) + timedelta(days=days)
