"""Portfolio performance analytics.

Everything in this module is derived from the transaction ledger and real
historical prices. Nothing here simulates, extrapolates, or fills gaps with
assumed growth rates: when the inputs are insufficient the functions return
``None`` or an empty series so the caller can render an honest empty state.

Provides:
    * ``xirr``            - money-weighted return over dated cash flows
    * ``twr``             - time-weighted return, contribution-timing neutral
    * ``max_drawdown``    - largest peak-to-trough decline in a value series
    * ``annualised_volatility``
    * ``build_valuation_series`` - month-end portfolio value vs. Nifty 50
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from portfolio_tracker.constants import BENCHMARK_SYMBOL
from portfolio_tracker.models import AssetModel, PortfolioModel, TransactionModel

logger = logging.getLogger(__name__)

# Kept as an alias so the benchmark ticker has one definition shared with the
# price-history layer that seeds it.
NIFTY_SYMBOL = BENCHMARK_SYMBOL

# Annualising a return over a very short window produces absurd numbers
# (a 2% gain over 5 days annualises to >300%). Below this span we decline
# to report an annualised figure at all.
MIN_DAYS_FOR_ANNUALISED = 30

# Fraction of today's portfolio value that must be priceable for a historical
# series to be worth showing. Below this the series would misrepresent the
# portfolio badly enough that an empty chart is the better answer.
MIN_COVERAGE = 0.80

DAYS_PER_YEAR = 365.0


# ─────────────────────────────────────────────────────────────────────────────
# Return metrics
# ─────────────────────────────────────────────────────────────────────────────

def xirr(
    flows: Sequence[tuple[datetime, Decimal | float]],
    guess: float = 0.1,
) -> float | None:
    """Money-weighted annualised return (the spreadsheet XIRR).

    Args:
        flows: ``(date, amount)`` pairs. Amounts are signed from the investor's
            perspective: negative for money put in (buys), positive for money
            taken out (sells) and for the terminal market value of what is
            still held.
        guess: Starting point for Newton-Raphson.

    Returns:
        The annualised rate as a decimal (``0.184`` = 18.4%), or ``None`` when
        the cash flows cannot yield a meaningful rate - fewer than two flows,
        no sign change, a span shorter than ``MIN_DAYS_FOR_ANNUALISED``, or a
        solver that fails to converge.
    """
    if not flows or len(flows) < 2:
        return None

    ordered = sorted(flows, key=lambda f: _naive(f[0]))
    t0 = _naive(ordered[0][0])
    span_days = (_naive(ordered[-1][0]) - t0).days
    if span_days < MIN_DAYS_FOR_ANNUALISED:
        return None

    amounts = [float(amount) for _, amount in ordered]
    days = [(_naive(when) - t0).days for when, _ in ordered]

    # An IRR only exists where money both goes in and comes out.
    if not (any(a > 0 for a in amounts) and any(a < 0 for a in amounts)):
        return None

    def npv(rate: float) -> float:
        base = 1.0 + rate
        return sum(a / base ** (t / DAYS_PER_YEAR) for a, t in zip(amounts, days, strict=True))

    def d_npv(rate: float) -> float:
        base = 1.0 + rate
        return sum(
            -(t / DAYS_PER_YEAR) * a / base ** (t / DAYS_PER_YEAR + 1.0)
            for a, t in zip(amounts, days, strict=True)
        )

    # Newton-Raphson first - fast when it works.
    rate = guess
    for _ in range(100):
        if rate <= -0.9999:
            break
        try:
            value = npv(rate)
            if abs(value) < 1e-7:
                return rate
            slope = d_npv(rate)
            if abs(slope) < 1e-12:
                break
            step = value / slope
            rate -= step
            if abs(step) < 1e-9:
                return rate if abs(npv(rate)) < 1e-4 else None
        except (OverflowError, ZeroDivisionError, ValueError):
            break

    return _bisect_irr(npv)


def _bisect_irr(npv, low: float = -0.9999, high: float = 100.0) -> float | None:
    """Bracket-and-halve fallback for when Newton-Raphson diverges."""
    try:
        f_low, f_high = npv(low), npv(high)
    except (OverflowError, ZeroDivisionError, ValueError):
        return None

    if f_low * f_high > 0:
        # No sign change in the bracket - no root to find here.
        return None

    for _ in range(200):
        mid = (low + high) / 2.0
        try:
            f_mid = npv(mid)
        except (OverflowError, ZeroDivisionError, ValueError):
            return None
        if abs(f_mid) < 1e-7 or (high - low) < 1e-9:
            return mid
        if f_low * f_mid < 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return None


def twr(periods: Sequence[tuple[float, float, float]]) -> float | None:
    """Time-weighted return, which strips out the effect of contribution timing.

    XIRR answers "how did my rupees do"; TWR answers "how did the holdings do",
    and TWR is the only one of the two that is fair to compare against an index.

    Args:
        periods: ``(start_value, end_value, net_flow)`` per sub-period, where
            ``net_flow`` is money added (positive) or withdrawn (negative)
            during the period. Flows are assumed to land at period end.

    Returns:
        Cumulative return as a decimal, or ``None`` if no period had a
        valuable starting balance to compound from.
    """
    compounded = 1.0
    used = 0

    for start_value, end_value, net_flow in periods:
        if start_value <= 0:
            # No capital at risk at the start of the period; the period cannot
            # contribute a return, only a starting balance for the next one.
            continue
        period_return = (end_value - net_flow) / start_value
        if period_return <= 0:
            # A total wipeout would zero the chain; clamp so one bad data point
            # cannot make every later period meaningless.
            period_return = max(period_return, 1e-9)
        compounded *= period_return
        used += 1

    if used == 0:
        return None
    return compounded - 1.0


def annualise(total_return: float, days: int) -> float | None:
    """Convert a cumulative return over ``days`` into an annual rate."""
    if days < MIN_DAYS_FOR_ANNUALISED or total_return <= -1.0:
        return None
    return (1.0 + total_return) ** (DAYS_PER_YEAR / days) - 1.0


def max_drawdown(values: Sequence[float]) -> dict[str, float] | None:
    """Largest peak-to-trough decline in a value series.

    Returns a dict with ``drawdown`` (negative decimal), ``peak`` and
    ``trough``, or ``None`` for a series too short to have a drawdown.
    """
    if len(values) < 2:
        return None

    peak = values[0]
    peak_index = 0
    worst = 0.0
    worst_peak = values[0]
    worst_trough = values[0]
    worst_peak_index = 0
    worst_trough_index = 0

    for i, value in enumerate(values):
        if value > peak:
            peak, peak_index = value, i
        if peak > 0:
            decline = (value - peak) / peak
            if decline < worst:
                worst = decline
                worst_peak, worst_trough = peak, value
                worst_peak_index, worst_trough_index = peak_index, i

    return {
        "drawdown": worst,
        "peak": worst_peak,
        "trough": worst_trough,
        "peak_index": worst_peak_index,
        "trough_index": worst_trough_index,
    }


def annualised_volatility(values: Sequence[float], periods_per_year: int = 12) -> float | None:
    """Standard deviation of period returns, annualised.

    Defaults to monthly data (12 periods a year); pass ``252`` for daily.
    """
    if len(values) < 3:
        return None

    returns = []
    for previous, current in zip(values, values[1:], strict=False):
        if previous > 0:
            returns.append(current / previous - 1.0)

    if len(returns) < 2:
        return None

    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return (variance ** 0.5) * (periods_per_year ** 0.5)


# ─────────────────────────────────────────────────────────────────────────────
# Ledger reconstruction
# ─────────────────────────────────────────────────────────────────────────────

def _naive(value: datetime) -> datetime:
    """Drop tzinfo so ledger rows (mixed naive/aware) compare without crashing."""
    if value is None:
        return datetime.min
    return value.replace(tzinfo=None) if value.tzinfo is not None else value


class _PriceLookup:
    """Historical closes for one symbol, queryable as of any date.

    Holds an ascending ``(date, close)`` list and answers with the most recent
    close on or before the requested date - which is what valuing a holding on
    a weekend or exchange holiday requires.
    """

    def __init__(self, points: list[dict]):
        self._points = sorted(
            ((_naive(p["date"]), float(p["close"])) for p in points if p.get("close")),
            key=lambda p: p[0],
        )

    def __bool__(self) -> bool:
        return bool(self._points)

    def as_of(self, when: datetime) -> float | None:
        when = _naive(when)
        found = None
        for point_date, close in self._points:
            if point_date > when:
                break
            found = close
        return found


def _load_prices(db: Session, symbols: Sequence[str], start: datetime, end: datetime) -> dict[str, _PriceLookup]:
    """Fetch a price series per symbol, tolerating per-symbol failures."""
    from portfolio_tracker.services.price_history import get_price_history_service

    service = get_price_history_service(db)
    days = max((end - start).days + 1, 1)
    lookups: dict[str, _PriceLookup] = {}

    for symbol in symbols:
        try:
            points = service.get_price_history(symbol, days=days, start_date=start, end_date=end)
        except Exception:
            # Say "lookup failed", not "no history": the two are very different
            # and the wording matters. A bug in the lookup once made a fully
            # populated table look like an empty one in every log line.
            logger.warning(
                "Price history lookup FAILED for %s; excluding from series", symbol, exc_info=True
            )
            points = []
        else:
            if not points:
                logger.info("No stored price history for %s; excluding from series", symbol)
        lookups[symbol] = _PriceLookup(points or [])

    return lookups


def _load_prices_for(
    db: Session,
    keys: Sequence[str],
    variants: dict[str, list[str]],
    start: datetime,
    end: datetime,
) -> dict[str, _PriceLookup]:
    """Price series per canonical key, trying each raw ticker it was seen as.

    A security folded from "RELIANCE" and "RELIANCE.NS" may only have stored
    history under one of them, so each variant is tried until one yields data.
    """
    lookups: dict[str, _PriceLookup] = {}
    for key in keys:
        candidates = variants.get(key) or [key]
        for raw in candidates:
            lookup = _load_prices(db, [raw], start, end).get(raw)
            if lookup:
                lookups[key] = lookup
                break
        else:
            lookups[key] = _PriceLookup([])
    return lookups


def _month_end_points(months: int) -> list[datetime]:
    """Anchor dates for the series: month ends going back, then today."""
    today = datetime.now(UTC).replace(tzinfo=None)
    points = []
    for offset in range(months, 0, -1):
        anchor = today - relativedelta(months=offset)
        # Last day of that month.
        month_end = (anchor.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)
        points.append(month_end.replace(hour=23, minute=59, second=59, microsecond=0))
    points.append(today)
    return points


def _canonical(symbol: str) -> str:
    """Collapse a ticker's exchange suffix so variants name one security.

    The same holding can sit under two asset rows - a bare "RELIANCE" left by
    an earlier import and a normalised "RELIANCE.NS" from a broker sync - with
    the trade history on one and the live quantity on the other. Valuing them
    separately counts the position twice, so both fold onto one key.

    Index tickers ("^NSEI") are returned untouched: they carry no exchange
    suffix and must not be split on a dot they do not have.
    """
    if not symbol:
        return ""
    upper = symbol.upper().strip()
    if upper.startswith("^"):
        return upper
    return upper.split(".")[0]


def _collect_ledger(db: Session, user_id: int) -> tuple[list[dict], dict[str, dict], dict[str, list[str]]]:
    """Read every transaction and asset for a user, keyed by canonical symbol.

    Returns ``(transactions, opening_balances, variants)``.

    Symbols are folded onto a canonical key so a security held under two asset
    rows ("RELIANCE" and "RELIANCE.NS") is one position rather than two.
    ``variants`` maps each canonical key back to the raw tickers seen, so the
    price lookup can try whichever form actually has history.

    An opening balance covers quantity a user holds that the ledger cannot
    explain - typically holdings imported by a broker sync without their trade
    history - so the series does not silently under-report the portfolio.
    """
    portfolio_ids = [
        row[0] for row in db.query(PortfolioModel.id).filter(PortfolioModel.user_id == user_id).all()
    ]
    if not portfolio_ids:
        return [], {}, {}

    rows = (
        db.query(TransactionModel, AssetModel)
        .join(AssetModel, TransactionModel.asset_id == AssetModel.id)
        .filter(TransactionModel.portfolio_id.in_(portfolio_ids))
        .order_by(TransactionModel.transaction_date)
        .all()
    )

    variants: dict[str, list[str]] = {}

    def note_variant(raw: str) -> str:
        """Record a raw ticker under its canonical key and return that key."""
        key = _canonical(raw)
        seen = variants.setdefault(key, [])
        if raw and raw not in seen:
            # Suffixed forms first: they are the ones Yahoo can price.
            seen.append(raw)
            seen.sort(key=lambda s: (("." not in s and not s.startswith("^")), s))
        return key

    transactions = [
        {
            "symbol": note_variant(asset.symbol),
            "date": _naive(txn.transaction_date),
            "type": (txn.type or "").lower(),
            "quantity": Decimal(str(txn.quantity)),
            "price": Decimal(str(txn.price)),
        }
        for txn, asset in rows
    ]

    ledger_quantity: dict[str, Decimal] = {}
    for txn in transactions:
        delta = txn["quantity"] if txn["type"] == "buy" else -txn["quantity"]
        ledger_quantity[txn["symbol"]] = ledger_quantity.get(txn["symbol"], Decimal("0")) + delta

    assets = db.query(AssetModel).filter(AssetModel.portfolio_id.in_(portfolio_ids)).all()

    # Sum the live quantity per security first. Splitting it across variants
    # and reconciling each one separately would book an opening balance for
    # the row holding the position while the row holding the ledger keeps its
    # own quantity - the same shares counted twice.
    held_by_symbol: dict[str, Decimal] = {}
    basis: dict[str, dict] = {}
    for asset in assets:
        key = note_variant(asset.symbol)
        quantity = Decimal(str(asset.quantity or 0))
        held_by_symbol[key] = held_by_symbol.get(key, Decimal("0")) + quantity

        since = _naive(asset.purchase_date) if asset.purchase_date else datetime.min
        price = Decimal(str(asset.purchase_price or 0))
        current = basis.get(key)
        # Keep the earliest acquisition date, and a price from a row that has
        # one, so an opening balance is dated and valued sensibly.
        if current is None:
            basis[key] = {"since": since, "price": price}
        else:
            current["since"] = min(current["since"], since)
            if not current["price"]:
                current["price"] = price

    opening: dict[str, dict] = {}
    for key, held in held_by_symbol.items():
        unexplained = held - ledger_quantity.get(key, Decimal("0"))
        if unexplained > 0:
            opening[key] = {
                "quantity": unexplained,
                "price": basis[key]["price"],
                "since": basis[key]["since"],
            }

    return transactions, opening, variants


def _quantities_as_of(
    transactions: Sequence[dict],
    opening: dict[str, dict],
    when: datetime,
) -> dict[str, Decimal]:
    """Holding quantity per symbol as at ``when``, from the ledger."""
    quantities: dict[str, Decimal] = {}

    for symbol, balance in opening.items():
        if balance["since"] <= when:
            quantities[symbol] = quantities.get(symbol, Decimal("0")) + balance["quantity"]

    for txn in transactions:
        if txn["date"] > when:
            break
        delta = txn["quantity"] if txn["type"] == "buy" else -txn["quantity"]
        quantities[txn["symbol"]] = quantities.get(txn["symbol"], Decimal("0")) + delta

    return {symbol: qty for symbol, qty in quantities.items() if qty > 0}


def _net_flow_between(
    transactions: Sequence[dict],
    start: datetime,
    end: datetime,
    opening: dict[str, dict] | None = None,
    prices: dict[str, _PriceLookup] | None = None,
) -> float:
    """Money added (positive) or withdrawn (negative) in a half-open window.

    Opening balances count too. They are positions the ledger cannot explain -
    typically a broker sync that imported holdings without their trade history
    - and they enter the series on their acquisition date. Treating that entry
    as anything other than a contribution makes a portfolio appearing all at
    once look like a spectacular gain: one real account here jumped from
    122k to 1.26m in a month and reported a four-figure percentage return.
    """
    total = Decimal("0")
    for txn in transactions:
        if start < txn["date"] <= end:
            amount = txn["quantity"] * txn["price"]
            total += amount if txn["type"] == "buy" else -amount

    for key, balance in (opening or {}).items():
        if start < balance["since"] <= end:
            total += _opening_entry_value(key, balance, prices, end)

    return float(total)


def _opening_entry_value(
    key: str,
    balance: dict,
    prices: dict[str, _PriceLookup] | None,
    when: datetime,
) -> Decimal:
    """What an opening balance is worth as it enters the tracked portfolio.

    Market value on the entry date, not original cost. These positions were
    often bought years before this window and only became visible when a
    broker sync imported them, so their purchase price bears no relation to
    what arrived. Booking the cost basis leaves the gap between cost and
    market looking like a return earned inside the window - one real account
    reported +326% for the month its holdings were imported.
    """
    lookup = (prices or {}).get(key)
    close = lookup.as_of(when) if lookup else None
    if close is not None:
        return balance["quantity"] * Decimal(str(close))
    return balance["quantity"] * balance["price"]


def _period_returns(
    series: Sequence[dict],
    anchors: Sequence[datetime],
    transactions: Sequence[dict],
    opening: dict[str, dict] | None = None,
    prices: dict[str, _PriceLookup] | None = None,
) -> list[float]:
    """Flow-adjusted return for each sub-period of a valuation series.

    This is the basis for TWR, volatility and drawdown alike. Computing any of
    them from raw values instead would read every deposit as a gain.
    """
    returns = []
    for index in range(1, len(series)):
        start_value = series[index - 1]["value"]
        if start_value <= 0:
            continue
        end_value = series[index]["value"]
        net_flow = _net_flow_between(
            transactions, anchors[index - 1], anchors[index], opening, prices
        )
        returns.append((end_value - net_flow) / start_value - 1.0)
    return returns


def _index_from_returns(returns: Sequence[float], base: float = 100.0) -> list[float]:
    """Compound period returns into a growth index starting at ``base``.

    Drawdown has to be measured on this, not on account value: a portfolio
    that only ever grew because money was paid into it has no drawdown, but
    its value series dips look like one.
    """
    index = [base]
    for period_return in returns:
        index.append(index[-1] * max(1.0 + period_return, 1e-9))
    return index


# ─────────────────────────────────────────────────────────────────────────────
# Series construction
# ─────────────────────────────────────────────────────────────────────────────

class _SeriesContext:
    """Everything one dashboard request needs, gathered once.

    The ledger read, the price fetch and the anchor dates were previously
    repeated by each public entry point - three ledger reads per request. They
    are also mutually dependent: flows have to be valued with the same prices
    the series is built from, or a position entering the window gets counted
    at a stale cost basis and the difference reads as return.
    """

    __slots__ = ("series", "prices", "transactions", "opening", "anchors")

    def __init__(self, series, prices, transactions, opening, anchors):
        self.series = series
        self.prices = prices
        self.transactions = transactions
        self.opening = opening
        self.anchors = anchors


def _build_series_context(db: Session, user_id: int, months: int = 12) -> _SeriesContext:
    """Build the valuation series and keep the inputs it was derived from."""
    empty = _SeriesContext([], {}, [], {}, [])

    transactions, opening, variants = _collect_ledger(db, user_id)
    if not transactions and not opening:
        return empty

    anchors = _month_end_points(months)
    window_start = anchors[0] - timedelta(days=7)  # padding for the first close
    window_end = anchors[-1]

    symbols = sorted({txn["symbol"] for txn in transactions} | set(opening))
    if not symbols:
        return empty

    prices = _load_prices_for(db, symbols, variants, window_start, window_end)
    nifty = _load_prices(db, [NIFTY_SYMBOL], window_start, window_end).get(NIFTY_SYMBOL)

    # Coverage is judged against today's holdings: a symbol we cannot price
    # today is a symbol whose weight in the series is simply missing.
    latest_quantities = _quantities_as_of(transactions, opening, anchors[-1])
    priced_value = 0.0
    total_value = 0.0
    for symbol, quantity in latest_quantities.items():
        close = prices[symbol].as_of(anchors[-1]) if prices.get(symbol) else None
        if close is not None:
            priced_value += float(quantity) * close
            total_value += float(quantity) * close
        else:
            # Fall back to the stored current price purely to size the gap.
            total_value += float(quantity) * _stored_price(db, user_id, symbol)

    coverage = (priced_value / total_value) if total_value > 0 else 0.0
    if coverage < MIN_COVERAGE:
        logger.info(
            "Growth series suppressed for user %s: only %.0f%% of portfolio value is priceable",
            user_id,
            coverage * 100,
        )
        return empty

    series: list[dict] = []
    for anchor in anchors:
        quantities = _quantities_as_of(transactions, opening, anchor)
        value = 0.0
        for symbol, quantity in quantities.items():
            lookup = prices.get(symbol)
            close = lookup.as_of(anchor) if lookup else None
            if close is not None:
                value += float(quantity) * close

        series.append(
            {
                "year": anchor.year,
                "month": anchor.month,
                "value": round(value, 2),
                "nifty_close": nifty.as_of(anchor) if nifty else None,
                "label": anchor.strftime("%b %Y"),
                "coverage": round(coverage, 4),
            }
        )

    # Drop leading points from before the portfolio existed so the chart does
    # not open on a flat zero run. Anchors are trimmed in step so the two stay
    # aligned for flow attribution.
    while len(series) > 2 and series[0]["value"] == 0 and series[1]["value"] == 0:
        series.pop(0)
    aligned_anchors = anchors[-len(series):] if series else []

    _rebase_benchmark(series)
    return _SeriesContext(series, prices, transactions, opening, aligned_anchors)


def build_valuation_series(db: Session, user_id: int, months: int = 12) -> list[dict]:
    """Month-end portfolio value over the trailing window, against Nifty 50.

    Every point is the ledger's holdings on that date valued at that date's
    actual closing prices. Where prices cannot be obtained for enough of the
    portfolio the whole series is dropped rather than partially reported.

    Returns a list of points, or ``[]`` when the portfolio has no history or
    prices are unavailable.
    """
    return _build_series_context(db, user_id, months=months).series


def _stored_price(db: Session, user_id: int, symbol: str) -> float:
    """Last known price from the assets table, used only to size price gaps.

    ``symbol`` is a canonical key, so every asset row for the user is matched
    on its own canonical form rather than compared literally.
    """
    assets = (
        db.query(AssetModel)
        .join(PortfolioModel, AssetModel.portfolio_id == PortfolioModel.id)
        .filter(PortfolioModel.user_id == user_id)
        .all()
    )
    for asset in assets:
        if _canonical(asset.symbol) == symbol and asset.current_price:
            return float(asset.current_price)
    return 0.0


def _rebase_benchmark(series: list[dict]) -> None:
    """Scale the index onto the portfolio's axis so the two are comparable.

    Both lines start at the same value; from there the index line shows what
    the same starting capital would have done tracking Nifty 50. Points with
    no index close carry ``None`` rather than a guess.
    """
    baseline_value = next((p["value"] for p in series if p["value"] > 0), 0.0)
    baseline_nifty = next(
        (p["nifty_close"] for p in series if p["nifty_close"] and p["value"] > 0), None
    )

    for point in series:
        close = point.pop("nifty_close", None)
        if baseline_nifty and baseline_value > 0 and close:
            point["nifty_value"] = round((close / baseline_nifty) * baseline_value, 2)
        else:
            point["nifty_value"] = None


def build_cash_flows(db: Session, user_id: int) -> tuple[list[tuple[datetime, Decimal]], Decimal]:
    """Dated cash flows for XIRR, terminated by current market value.

    Returns ``(flows, current_value)``. Buys are negative, sells positive, and
    the closing market value is appended as a final positive flow.
    """
    transactions, opening, _variants = _collect_ledger(db, user_id)

    flows: list[tuple[datetime, Decimal]] = []
    for balance in opening.values():
        if balance["quantity"] > 0 and balance["price"] > 0:
            flows.append((balance["since"], -(balance["quantity"] * balance["price"])))

    for txn in transactions:
        amount = txn["quantity"] * txn["price"]
        flows.append((txn["date"], -amount if txn["type"] == "buy" else amount))

    portfolio_ids = [
        row[0] for row in db.query(PortfolioModel.id).filter(PortfolioModel.user_id == user_id).all()
    ]
    current_value = Decimal("0")
    if portfolio_ids:
        for asset in db.query(AssetModel).filter(AssetModel.portfolio_id.in_(portfolio_ids)).all():
            current_value += Decimal(str(asset.quantity or 0)) * Decimal(str(asset.current_price or 0))

    if current_value > 0:
        flows.append((datetime.now(UTC).replace(tzinfo=None), current_value))

    return flows, current_value


def compute_returns(db: Session, user_id: int, months: int = 12) -> dict:
    """Headline performance metrics for a user's whole portfolio.

    Every field is ``None`` when it cannot be computed honestly, so the caller
    renders a dash rather than a fabricated number.
    """
    flows, current_value = build_cash_flows(db, user_id)
    money_weighted = xirr(flows) if flows else None

    context = _build_series_context(db, user_id, months=months)
    series = context.series

    time_weighted = None
    time_weighted_annualised = None
    drawdown = None
    volatility = None
    benchmark_return = None

    if len(series) >= 2:
        anchors = context.anchors

        # One flow-adjusted return series feeds TWR, volatility and drawdown.
        # Reading any of them off raw account value would count every deposit
        # as performance.
        returns = _period_returns(
            series, anchors, context.transactions, context.opening, context.prices
        )

        if returns:
            compounded = 1.0
            for period_return in returns:
                compounded *= max(1.0 + period_return, 1e-9)
            time_weighted = compounded - 1.0

            span_days = (anchors[-1] - anchors[0]).days
            time_weighted_annualised = annualise(time_weighted, span_days)

            # Drawdown and volatility on the growth index, not on the balance.
            growth_index = _index_from_returns(returns)
            drawdown = max_drawdown(growth_index)
            volatility = annualised_volatility(growth_index)

        first_bench = next((p["nifty_value"] for p in series if p["nifty_value"]), None)
        last_bench = series[-1]["nifty_value"]
        if first_bench and last_bench:
            benchmark_return = last_bench / first_bench - 1.0

    return {
        "xirr": money_weighted,
        "twr": time_weighted,
        "twr_annualised": time_weighted_annualised,
        "benchmark_return": benchmark_return,
        "alpha": (
            time_weighted - benchmark_return
            if time_weighted is not None and benchmark_return is not None
            else None
        ),
        "max_drawdown": drawdown["drawdown"] if drawdown else None,
        "volatility": volatility,
        "current_value": float(current_value),
        "data_points": len(series),
    }
