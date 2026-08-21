"""Instrument identity.

An ISIN is the only stable identifier for an Indian security. Tickers get
renamed (Zomato became ETERNAL), differ by exchange (``.NS`` / ``.BO``), and
differ again by broker (``RELIANCE-EQ``). This module is the one place that
decides what counts as the same instrument.
"""

from __future__ import annotations

import re

#: ISIN: two-letter country code, nine alphanumeric characters, one check digit.
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

#: Exchange suffixes used by Yahoo Finance for Indian listings.
_YAHOO_SUFFIXES = (".NS", ".BO")

#: Segment suffixes brokers append to a tradingsymbol.
_BROKER_SUFFIXES = ("-EQ", "-BE", "-BZ", "-SM", "-ST", "-IQ")


def normalise_isin(value: str | None) -> str:
    """Upper-case and strip an ISIN, returning "" if there is nothing usable."""
    if not value:
        return ""
    return re.sub(r"\s+", "", value).upper()


def is_valid_isin(value: str | None) -> bool:
    """Structural and checksum validation.

    The checksum matters: ISINs get transcribed by hand out of PDF statements,
    and a single wrong character would otherwise create a phantom instrument
    that silently splits a holding in two.
    """
    isin = normalise_isin(value)
    if not _ISIN_RE.match(isin):
        return False

    # Luhn over the digits, with letters expanded to their ordinal position
    # offset by 9 (A=10 ... Z=35), per ISO 6166.
    digits: list[int] = []
    for char in isin:
        if char.isdigit():
            digits.append(int(char))
        else:
            expanded = ord(char) - ord("A") + 10
            digits.extend((expanded // 10, expanded % 10))

    total = 0
    # Double every second digit counting from the right, excluding the check
    # digit itself.
    for index, digit in enumerate(reversed(digits[:-1])):
        if index % 2 == 0:
            doubled = digit * 2
            total += doubled - 9 if doubled > 9 else doubled
        else:
            total += digit

    check = (10 - (total % 10)) % 10
    return check == digits[-1]


def canonical_symbol(symbol: str | None) -> str:
    """Strip exchange and segment suffixes so ticker variants collapse.

    A fallback for identity when no ISIN is available - good enough to merge
    ``RELIANCE``, ``RELIANCE.NS`` and ``RELIANCE-EQ``, but not a substitute for
    an ISIN, since two companies can share a ticker across exchanges.

    Index tickers (``^NSEI``) are returned untouched.
    """
    if not symbol:
        return ""
    upper = symbol.strip().upper()
    if upper.startswith("^"):
        return upper
    for suffix in _YAHOO_SUFFIXES + _BROKER_SUFFIXES:
        if upper.endswith(suffix):
            return upper[: -len(suffix)]
    # Anything else with a dot: take the part before the first one.
    return upper.split(".")[0]


def instrument_key(isin: str | None, symbol: str | None = None) -> str:
    """The key a holding is grouped under.

    Prefers a valid ISIN. Falls back to a canonical symbol prefixed so it can
    never be mistaken for one, which keeps un-ISINed history usable while
    making it obvious in the data which rows still need resolving.
    """
    normalised = normalise_isin(isin)
    if is_valid_isin(normalised):
        return normalised
    canonical = canonical_symbol(symbol)
    return f"SYM:{canonical}" if canonical else ""


def is_placeholder_key(key: str) -> bool:
    """Whether a key is a symbol fallback rather than a real ISIN."""
    return key.startswith("SYM:")
