"""CAS (Consolidated Account Statement) PDF parser.

Parses CAMS and KFintech CAS PDFs to extract mutual fund folios,
holdings (current units + NAV), and transaction history.

CAS PDFs have a predictable text layout:
  - Header block with PAN, email, statement period
  - Per-folio blocks separated by AMC name headers
  - Each folio: folio number, scheme name, registrar
  - Transaction rows: date | description | amount | units | nav | balance
  - Closing balance row with latest units + valuation

This parser uses regex-based text extraction (pdfplumber) and is tolerant
of minor format variations between CAMS and KFintech statements.
"""

import io
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes for parsed output
# ---------------------------------------------------------------------------


@dataclass
class CASTransaction:
    date: datetime
    description: str
    amount: Optional[Decimal] = None
    units: Optional[Decimal] = None
    nav: Optional[Decimal] = None
    balance_units: Optional[Decimal] = None
    tx_type: str = "purchase"  # purchase / redemption / switch_in / switch_out / dividend


@dataclass
class CASFolio:
    folio_number: str
    scheme_name: str
    amc: str = ""
    isin: str = ""
    registrar: str = ""  # CAMS / KFintech
    closing_units: Decimal = Decimal("0")
    closing_nav: Optional[Decimal] = None
    cost_value: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    transactions: list[CASTransaction] = field(default_factory=list)


@dataclass
class CASParseResult:
    pan: str = ""
    email: str = ""
    statement_from: Optional[datetime] = None
    statement_to: Optional[datetime] = None
    folios: list[CASFolio] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    registrar: str = ""  # CAMS or KFintech as detected from content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dec(value: str) -> Optional[Decimal]:
    """Parse a numeric string to Decimal (strips commas, parens for negative)."""
    raw = value.strip().replace(",", "")
    if not raw or raw == "--" or raw == "-":
        return None
    # Handle parenthesised negatives: (1234.56) → -1234.56
    if raw.startswith("(") and raw.endswith(")"):
        raw = "-" + raw[1:-1]
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _parse_date_cas(text: str) -> Optional[datetime]:
    """Parse dates commonly seen in CAS: DD-MMM-YYYY or DD/MM/YYYY."""
    text = text.strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


_RE_PAN = re.compile(r"\bPAN\s*:\s*([A-Z]{5}\d{4}[A-Z])\b", re.IGNORECASE)
_RE_EMAIL = re.compile(r"\bEmail\s*(?:Id|Address)?\s*:\s*([\w.+-]+@[\w-]+\.[\w.]+)", re.IGNORECASE)
_RE_STATEMENT_PERIOD = re.compile(
    r"(\d{2}[-/]\w{3,9}[-/]\d{4})\s+to\s+(\d{2}[-/]\w{3,9}[-/]\d{4})", re.IGNORECASE
)

# AMC header: line that starts with an AMC name (all caps, possibly with "Mutual Fund")
_RE_AMC_HEADER = re.compile(
    r"^([\w\s&]+(?:Mutual\s+Fund|Asset\s+Management|AMC)[\w\s&]*)",
    re.IGNORECASE | re.MULTILINE,
)

# Folio number patterns
_RE_FOLIO = re.compile(
    r"Folio\s+No\s*[:\-]?\s*([\w/ ]+?)(?:\s+PAN|$)", re.IGNORECASE
)

# Scheme name + ISIN on same/next line
_RE_SCHEME = re.compile(
    r"^(.+?)\s*[-–]\s*ISIN\s*:\s*([A-Z0-9]{12})",
    re.IGNORECASE | re.MULTILINE,
)
_RE_SCHEME_NO_ISIN = re.compile(
    r"^(.+?(?:Growth|Dividend|IDCW|Direct|Regular|Fund|Plan).+?)$",
    re.IGNORECASE | re.MULTILINE,
)

# Transaction row: DD-Mon-YYYY  description  amount(₹)  units  nav  balance
_RE_TX_ROW = re.compile(
    r"(\d{2}-\w{3}-\d{4})\s+"          # date
    r"(.+?)\s+"                          # description
    r"([\d,]+\.?\d*|\(.+?\)|--)\s+"      # amount
    r"([\d,]+\.?\d*|\(.+?\)|--)\s+"      # units
    r"([\d,]+\.?\d*|--)\s+"              # nav
    r"([\d,]+\.?\d*)",                   # balance units
)

# Valuation/closing row
_RE_VALUATION = re.compile(
    r"Valuation\s+on.*?:\s*([\d,]+\.?\d*)\s+.*?NAV.*?:\s*([\d,]+\.?\d*)",
    re.IGNORECASE,
)
_RE_CLOSING_UNITS = re.compile(
    r"Closing\s+Unit\s+Balance\s*[:\-]?\s*([\d,]+\.?\d*)", re.IGNORECASE
)
_RE_COST_VALUE = re.compile(
    r"Cost\s+Value\s*[:\-]?\s*(?:INR)?\s*([\d,]+\.?\d*)", re.IGNORECASE
)
_RE_CURRENT_VALUE = re.compile(
    r"(?:Market|Current)\s+Value\s*[:\-]?\s*(?:INR)?\s*([\d,]+\.?\d*)", re.IGNORECASE
)
_RE_NAV_VALUE = re.compile(
    r"NAV\s+on.*?:\s*(?:INR)?\s*([\d,]+\.?\d*)", re.IGNORECASE
)


# Registrar detection
_RE_CAMS = re.compile(r"CAMS|Computer\s+Age\s+Management", re.IGNORECASE)
_RE_KFINTECH = re.compile(r"KFin|Karvy|KFintech", re.IGNORECASE)


def _classify_tx(description: str) -> str:
    d = description.lower()
    if "redemption" in d or "redeem" in d:
        return "redemption"
    if "switch" in d and "out" in d:
        return "switch_out"
    if "switch" in d and "in" in d:
        return "switch_in"
    if "dividend" in d or "idcw" in d or "payout" in d:
        return "dividend"
    return "purchase"


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def parse_cas_pdf(file_bytes: bytes, password: str | None = None) -> CASParseResult:
    """Parse a CAMS or KFintech CAS PDF.

    Args:
        file_bytes: Raw bytes of the uploaded PDF.
        password: PDF password (CAS PDFs are often password-protected with
                  PAN + DOB, e.g., "ABCDE1234F01011990").

    Returns:
        CASParseResult with folios, transactions, and any errors.
    """
    try:
        import pdfplumber
    except ImportError:
        return CASParseResult(errors=[
            "PDF parsing requires the 'pdfplumber' library. "
            "Install with: pip install pdfplumber"
        ])

    result = CASParseResult()

    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes), password=password)
    except Exception as exc:
        err_str = str(exc).lower()
        if "password" in err_str or "encrypted" in err_str:
            result.errors.append(
                "This PDF is password-protected. Please provide the password "
                "(usually your PAN + Date of Birth, e.g., ABCDE1234F01011990)."
            )
        else:
            result.errors.append(f"Could not open PDF: {exc}")
        return result

    # Extract all text
    full_text = ""
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
    pdf.close()

    if not full_text.strip():
        result.errors.append("No text could be extracted from this PDF. It may be scanned/image-based.")
        return result

    # Detect registrar
    if _RE_CAMS.search(full_text):
        result.registrar = "CAMS"
    elif _RE_KFINTECH.search(full_text):
        result.registrar = "KFintech"

    # Extract PAN
    m = _RE_PAN.search(full_text)
    if m:
        result.pan = m.group(1).upper()

    # Extract email
    m = _RE_EMAIL.search(full_text)
    if m:
        result.email = m.group(1)

    # Statement period
    m = _RE_STATEMENT_PERIOD.search(full_text)
    if m:
        result.statement_from = _parse_date_cas(m.group(1))
        result.statement_to = _parse_date_cas(m.group(2))

    # --- Parse folio blocks ---
    # Strategy: split text by folio markers, then within each block extract
    # scheme name, transactions, and closing balance.

    # Find all folio positions
    folio_matches = list(_RE_FOLIO.finditer(full_text))
    if not folio_matches:
        result.errors.append(
            "No folio numbers found in this PDF. "
            "Please ensure you upload a CAS (Consolidated Account Statement) from CAMS or KFintech."
        )
        return result

    # Track current AMC from headers above each folio
    amc_positions = [(m.start(), m.group(1).strip()) for m in _RE_AMC_HEADER.finditer(full_text)]

    def _get_amc_for_pos(pos: int) -> str:
        """Find the nearest AMC header before a given position."""
        amc = ""
        for amc_pos, amc_name in amc_positions:
            if amc_pos < pos:
                amc = amc_name
            else:
                break
        return amc

    for idx, folio_match in enumerate(folio_matches):
        folio_num = folio_match.group(1).strip().rstrip("/")

        # Get text block for this folio (up to next folio or end)
        start = folio_match.start()
        end = folio_matches[idx + 1].start() if idx + 1 < len(folio_matches) else len(full_text)
        block = full_text[start:end]

        amc = _get_amc_for_pos(start)

        # Extract scheme name + ISIN
        scheme_name = ""
        isin = ""
        sm = _RE_SCHEME.search(block)
        if sm:
            scheme_name = sm.group(1).strip()
            isin = sm.group(2).strip()
        else:
            sm = _RE_SCHEME_NO_ISIN.search(block)
            if sm:
                scheme_name = sm.group(1).strip()

        if not scheme_name:
            # Fallback: use first non-empty line after folio header
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if len(lines) > 1:
                scheme_name = lines[1][:200]

        folio = CASFolio(
            folio_number=folio_num,
            scheme_name=scheme_name,
            amc=amc,
            isin=isin,
            registrar=result.registrar,
        )

        # Extract transactions
        for tx_match in _RE_TX_ROW.finditer(block):
            dt = _parse_date_cas(tx_match.group(1))
            if not dt:
                continue
            desc = tx_match.group(2).strip()
            amount = _dec(tx_match.group(3))
            units = _dec(tx_match.group(4))
            nav = _dec(tx_match.group(5))
            balance = _dec(tx_match.group(6))

            folio.transactions.append(CASTransaction(
                date=dt,
                description=desc,
                amount=amount,
                units=units,
                nav=nav,
                balance_units=balance,
                tx_type=_classify_tx(desc),
            ))

        # Extract closing balance / valuation
        vm = _RE_VALUATION.search(block)
        if vm:
            folio.closing_units = _dec(vm.group(1)) or Decimal("0")
            folio.closing_nav = _dec(vm.group(2))
        else:
            cm = _RE_CLOSING_UNITS.search(block)
            if cm:
                folio.closing_units = _dec(cm.group(1)) or Decimal("0")

        nm = _RE_NAV_VALUE.search(block)
        if nm and folio.closing_nav is None:
            folio.closing_nav = _dec(nm.group(1))

        cv = _RE_COST_VALUE.search(block)
        if cv:
            folio.cost_value = _dec(cv.group(1))

        mv = _RE_CURRENT_VALUE.search(block)
        if mv:
            folio.current_value = _dec(mv.group(1))

        # If closing_units is still zero but we have transactions, use last balance
        if folio.closing_units == Decimal("0") and folio.transactions:
            last_balance = folio.transactions[-1].balance_units
            if last_balance and last_balance > 0:
                folio.closing_units = last_balance

        result.folios.append(folio)

    logger.info(
        "CAS parsed: registrar=%s folios=%d total_txns=%d",
        result.registrar,
        len(result.folios),
        sum(len(f.transactions) for f in result.folios),
    )
    return result
