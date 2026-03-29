"""CSV import service for broker trade reports and manual uploads.

Supports:
- Zerodha tradebook (downloaded from Console → Trade book)
- Groww trade report
- 5Paisa trade report
- Generic / manual CSV (QuantLeap standard format)

Each parser normalises rows to a common dict:
    {symbol, type, quantity, price, date, notes}
"""

import csv
import io
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def _dec(value: str) -> Decimal:
    """Parse a string to Decimal, stripping commas and whitespace."""
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _parse_date(value: str, formats: list[str] | None = None) -> Optional[datetime]:
    """Try several date formats; return None on failure."""
    formats = formats or [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
    ]
    raw = value.strip()
    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Detector – guess which broker format the CSV is
# ---------------------------------------------------------------------------

_ZERODHA_MARKERS = {"tradingsymbol", "trade_type", "quantity", "price"}
_GROWW_MARKERS = {"stock_symbol", "action", "quantity", "price"}
_FIVEPAISA_MARKERS = {"scripname", "buysell", "qty", "rate"}
_GENERIC_MARKERS = {"symbol", "type", "quantity", "price"}


def detect_format(headers: list[str]) -> str:
    """Return one of 'zerodha', 'groww', 'fivepaisa', 'generic', 'unknown'."""
    lower = {h.strip().lower().replace(" ", "_") for h in headers}
    if _ZERODHA_MARKERS <= lower:
        return "zerodha"
    if _GROWW_MARKERS <= lower:
        return "groww"
    if _FIVEPAISA_MARKERS <= lower:
        return "fivepaisa"
    if _GENERIC_MARKERS <= lower:
        return "generic"
    return "unknown"


# ---------------------------------------------------------------------------
# Per-broker row normalisers
# ---------------------------------------------------------------------------

def _normalise_zerodha(row: dict) -> Optional[dict]:
    """Zerodha Console tradebook CSV columns:
    symbol / tradingsymbol, trade_type, quantity, price, trade_date / order_execution_time
    """
    symbol = (row.get("tradingsymbol") or row.get("symbol") or "").strip()
    if not symbol:
        return None

    raw_type = (row.get("trade_type") or row.get("transaction_type") or "").strip().lower()
    tx_type = "buy" if raw_type in {"buy", "b"} else "sell" if raw_type in {"sell", "s"} else None
    if tx_type is None:
        return None

    qty = _dec(row.get("quantity", "0"))
    price = _dec(row.get("price") or row.get("average_price", "0"))
    if qty <= 0 or price <= 0:
        return None

    date_str = (
        row.get("trade_date")
        or row.get("order_execution_time")
        or row.get("fill_timestamp")
        or ""
    )
    dt = _parse_date(date_str)

    trade_id = row.get("trade_id") or row.get("order_id") or ""
    notes = f"CSV import – Zerodha trade {trade_id}" if trade_id else "CSV import – Zerodha"

    return {
        "symbol": symbol,
        "type": tx_type,
        "quantity": qty,
        "price": price,
        "date": dt,
        "notes": notes,
    }


def _normalise_groww(row: dict) -> Optional[dict]:
    symbol = (row.get("stock_symbol") or row.get("symbol") or "").strip()
    if not symbol:
        return None

    raw_type = (row.get("action") or row.get("type") or "").strip().lower()
    tx_type = "buy" if raw_type in {"buy", "b"} else "sell" if raw_type in {"sell", "s"} else None
    if tx_type is None:
        return None

    qty = _dec(row.get("quantity", "0"))
    price = _dec(row.get("price") or row.get("avg_price", "0"))
    if qty <= 0 or price <= 0:
        return None

    date_str = row.get("date") or row.get("trade_date") or ""
    dt = _parse_date(date_str)

    return {
        "symbol": symbol,
        "type": tx_type,
        "quantity": qty,
        "price": price,
        "date": dt,
        "notes": "CSV import – Groww",
    }


def _normalise_fivepaisa(row: dict) -> Optional[dict]:
    symbol = (row.get("scripname") or row.get("symbol") or "").strip()
    if not symbol:
        return None

    raw_type = (row.get("buysell") or row.get("type") or "").strip().lower()
    tx_type = "buy" if raw_type in {"buy", "b"} else "sell" if raw_type in {"sell", "s"} else None
    if tx_type is None:
        return None

    qty = _dec(row.get("qty") or row.get("quantity", "0"))
    price = _dec(row.get("rate") or row.get("price", "0"))
    if qty <= 0 or price <= 0:
        return None

    date_str = row.get("date") or row.get("trade_date") or ""
    dt = _parse_date(date_str)

    return {
        "symbol": symbol,
        "type": tx_type,
        "quantity": qty,
        "price": price,
        "date": dt,
        "notes": "CSV import – 5Paisa",
    }


def _normalise_generic(row: dict) -> Optional[dict]:
    """QuantLeap standard CSV:
    symbol, type, quantity, price, date, notes
    """
    symbol = (row.get("symbol") or "").strip()
    if not symbol:
        return None

    raw_type = (row.get("type") or "").strip().lower()
    tx_type = "buy" if raw_type in {"buy", "b"} else "sell" if raw_type in {"sell", "s"} else None
    if tx_type is None:
        return None

    qty = _dec(row.get("quantity", "0"))
    price = _dec(row.get("price", "0"))
    if qty <= 0 or price <= 0:
        return None

    date_str = row.get("date") or row.get("trade_date") or ""
    dt = _parse_date(date_str)

    notes = (row.get("notes") or "").strip() or "CSV import – manual"

    return {
        "symbol": symbol,
        "type": tx_type,
        "quantity": qty,
        "price": price,
        "date": dt,
        "notes": notes,
    }


_PARSERS = {
    "zerodha": _normalise_zerodha,
    "groww": _normalise_groww,
    "fivepaisa": _normalise_fivepaisa,
    "generic": _normalise_generic,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class CSVImportResult:
    __slots__ = ("rows", "skipped", "errors", "detected_format")

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.skipped: int = 0
        self.errors: list[str] = []
        self.detected_format: str = "unknown"


def parse_csv(file_bytes: bytes, broker_hint: str | None = None) -> CSVImportResult:
    """Parse a CSV file and return normalised trade rows.

    Args:
        file_bytes: Raw bytes of the uploaded CSV.
        broker_hint: Optional hint ('zerodha', 'groww', 'fivepaisa', 'generic').
                     If None, format is auto-detected from headers.

    Returns:
        CSVImportResult with .rows, .skipped, .errors, .detected_format.
    """
    result = CSVImportResult()

    try:
        text = file_bytes.decode("utf-8-sig")  # handles BOM if present
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("latin-1")
        except Exception:
            result.errors.append("Could not decode file. Please use UTF-8 encoding.")
            return result

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        result.errors.append("CSV file has no header row.")
        return result

    # Normalise header names (lowercase, strip, underscores for spaces)
    clean_fields = [f.strip().lower().replace(" ", "_") for f in reader.fieldnames]
    reader.fieldnames = clean_fields

    fmt = broker_hint or detect_format(clean_fields)
    result.detected_format = fmt

    parser = _PARSERS.get(fmt)
    if parser is None:
        result.errors.append(
            f"Unrecognised CSV format. Detected headers: {clean_fields[:10]}. "
            "Use the QuantLeap standard format: symbol, type, quantity, price, date, notes"
        )
        return result

    for line_no, row in enumerate(reader, start=2):  # line 1 = header
        try:
            normalised = parser(row)
            if normalised is None:
                result.skipped += 1
                continue
            result.rows.append(normalised)
        except Exception as exc:
            result.skipped += 1
            result.errors.append(f"Line {line_no}: {exc}")

    logger.info(
        "CSV parse complete: format=%s rows=%d skipped=%d errors=%d",
        fmt, len(result.rows), result.skipped, len(result.errors),
    )
    return result
