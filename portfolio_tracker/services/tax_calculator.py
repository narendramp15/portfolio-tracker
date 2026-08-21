"""Tax calculation service for capital gains (STCG/LTCG)."""

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from portfolio_tracker.services import grandfathering


def _deductible_charges(txn) -> Decimal:
    """Charges on a transaction that reduce the taxable gain.

    Brokerage and other transfer expenses (stamp duty, exchange turnover
    charge, SEBI fee, GST) are deductible under Section 48. STT explicitly is
    not, so it is excluded here even though it is stored on the row.
    """
    total = Decimal("0")
    for field in ("brokerage", "other_charges"):
        value = getattr(txn, field, None)
        if value:
            total += Decimal(str(value))
    return total


def _charges_per_unit(txn) -> Decimal:
    """Deductible charges apportioned across the units in the transaction."""
    quantity = Decimal(str(txn.quantity or 0))
    if quantity <= 0:
        return Decimal("0")
    return _deductible_charges(txn) / quantity


class TaxCalculator:
    """
    Calculate Short-Term and Long-Term Capital Gains for Indian tax purposes.
    
    Tax Rules (Post July 23, 2024):
    - Listed Equity/Equity Mutual Funds (LTCG > 1 year): 12.5% with ₹1.25L exemption
    - STCG (< 1 year): 20% flat rate
    - Unlisted Shares: 24 months for LTCG classification
    - No indexation benefits under 12.5% LTCG regime
    - STT (Securities Transaction Tax): Applicable on equity transactions
    - Non-Residents: 20% STCG on listed shares/funds
    """
    
    # India tax rules: < 1 year = STCG, >= 1 year = LTCG (for equity)
    # Updated rates as per Budget 2024 (from July 23, 2024)
    STCG_HOLDING_DAYS = 365  # < 1 year = short-term
    LTCG_HOLDING_DAYS_UNLISTED = 730  # > 2 years = long-term for unlisted shares
    
    STCG_TAX_RATE = Decimal("0.20")  # 20% for equity STCG (resident)
    STCG_TAX_RATE_NON_RESIDENT = Decimal("0.20")  # 20% for non-residents (listed shares)
    
    LTCG_TAX_RATE = Decimal("0.125")  # 12.5% for listed equity LTCG (no indexation)
    LTCG_EXEMPTION = Decimal("125000")  # ₹1,25,000 exemption per financial year (increased from ₹1L)
    
    @staticmethod
    def _to_naive(dt):
        """Drop tzinfo so naive (manual) and aware (imported) dates compare/subtract."""
        if dt is None:
            return None
        return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt

    @staticmethod
    def _fy_bounds(financial_year: Optional[str]):
        """Return naive (start, end) datetimes for an Indian FY string, or None."""
        if not financial_year:
            return None
        fy = financial_year.replace('FY', '').strip()
        start_year, end_year = map(int, fy.split('-'))
        if end_year < 100:
            end_year = 2000 + end_year
        if start_year < 100:
            start_year = 2000 + start_year
        return datetime(start_year, 4, 1), datetime(end_year, 3, 31, 23, 59, 59)

    @staticmethod
    def calculate_capital_gains(
        transactions: List,
        method: str = 'FIFO',
        include_unrealized: bool = False,
        financial_year: Optional[str] = None
    ) -> Dict:
        """
        Calculate realized and optionally unrealized capital gains.

        Args:
            transactions: List of TransactionModel objects with asset relationship.
                Pass the FULL history (all financial years); do NOT pre-filter by
                FY, or already-consumed FIFO lots will be mismatched.
            method: 'FIFO' (First In First Out) or 'LIFO' (Last In First Out)
            include_unrealized: Whether to include unrealized gains from current holdings
            financial_year: Optional FY (e.g. "2024-25"). When given, FIFO still runs
                over the entire history but only sells settled within that FY are
                aggregated into the reported gains.

        Returns:
            Dict with comprehensive tax report including STCG/LTCG breakdown by symbol
        """
        fy_bounds = TaxCalculator._fy_bounds(financial_year)

        # Group transactions by symbol
        symbol_txns = defaultdict(list)
        for txn in transactions:
            if not hasattr(txn, 'asset') or not txn.asset:
                continue
            symbol_txns[txn.asset.symbol].append(txn)

        results = {}
        summary = {
            'total_stcg': Decimal("0"),
            'total_ltcg': Decimal("0"),
            'total_stcg_tax': Decimal("0"),
            'total_ltcg_tax': Decimal("0"),
            'total_tax': Decimal("0"),
            'total_charges': Decimal("0"),
            'grandfathered_symbols': [],
            'symbols_missing_fmv': [],
            'symbols': []
        }
        
        for symbol, txns in symbol_txns.items():
            symbol_result = TaxCalculator._process_symbol(
                txns, method, include_unrealized, fy_bounds, symbol=symbol
            )
            results[symbol] = symbol_result

            # Aggregate summary
            summary['total_stcg'] += Decimal(str(symbol_result['stcg_gain']))
            summary['total_ltcg'] += Decimal(str(symbol_result['ltcg_gain']))
            summary['total_charges'] += Decimal(str(symbol_result['charges_deducted']))
            if symbol_result['grandfathering_applied']:
                summary['grandfathered_symbols'].append(symbol)
            summary['symbols_missing_fmv'].extend(symbol_result['fmv_missing'])
            summary['symbols'].append({
                'symbol': symbol,
                'name': txns[0].asset.name if txns[0].asset else symbol,
                'stcg': symbol_result['stcg_gain'],
                'ltcg': symbol_result['ltcg_gain'],
                'total_gain': symbol_result['stcg_gain'] + symbol_result['ltcg_gain']
            })
        
        # Calculate total taxes after applying exemptions. A net short-term loss
        # is not a negative tax (it is carried forward), so floor STCG tax at zero.
        stcg_taxable = max(summary['total_stcg'], Decimal("0"))
        summary['total_stcg_tax'] = stcg_taxable * TaxCalculator.STCG_TAX_RATE
        ltcg_taxable = max(summary['total_ltcg'] - TaxCalculator.LTCG_EXEMPTION, Decimal("0"))
        summary['total_ltcg_tax'] = ltcg_taxable * TaxCalculator.LTCG_TAX_RATE
        summary['total_tax'] = summary['total_stcg_tax'] + summary['total_ltcg_tax']
        
        # Convert to float for JSON serialization
        summary['total_stcg'] = float(summary['total_stcg'])
        summary['total_ltcg'] = float(summary['total_ltcg'])
        summary['total_stcg_tax'] = float(summary['total_stcg_tax'])
        summary['total_ltcg_tax'] = float(summary['total_ltcg_tax'])
        summary['total_tax'] = float(summary['total_tax'])
        summary['total_charges'] = float(summary['total_charges'])
        summary['ltcg_exemption_used'] = float(min(summary['total_ltcg'], TaxCalculator.LTCG_EXEMPTION))
        # Deduplicate: a symbol can lack an FMV across several matched lots.
        summary['symbols_missing_fmv'] = sorted(set(summary['symbols_missing_fmv']))
        
        return {
            'summary': summary,
            'by_symbol': results,
            'method': method
        }
    
    @staticmethod
    def _process_symbol(
        txns: List,
        method: str,
        include_unrealized: bool,
        fy_bounds=None,
        symbol: str = "",
    ) -> Dict:
        """
        Process all transactions for a single symbol.

        Args:
            txns: List of transactions for one symbol
            method: FIFO or LIFO
            include_unrealized: Whether to calculate unrealized gains
            fy_bounds: Optional (start, end) naive datetimes; when set, only sells
                settled in that window contribute to the reported gains, while
                FIFO still consumes lots across the whole history.
            symbol: Ticker for this group, needed to look up the 31-Jan-2018
                fair market value for Section 112A grandfathering.

        Returns:
            Dict with realized and optionally unrealized gains breakdown
        """
        # Sort transactions by date (oldest first); strip tz so mixed naive/aware rows don't crash
        def _naive(dt):
            if dt is None:
                return datetime.min
            return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt

        sorted_txns = sorted(txns, key=lambda t: _naive(t.transaction_date))
        
        buy_queue = []  # List of buy lots: [{'qty': Decimal, 'price': Decimal, 'date': datetime}, ...]
        stcg_total = Decimal("0")
        ltcg_total = Decimal("0")
        stcg_transactions = []
        ltcg_transactions = []
        charges_deducted = Decimal("0")
        # Lots that qualified for the 112A step-up but had no FMV on file. These
        # are reported so the user can see which gains are overstated.
        symbols_missing_fmv = set()
        
        for txn in sorted_txns:
            if txn.type.lower() == 'buy':
                buy_queue.append({
                    'qty': Decimal(str(txn.quantity)),
                    'price': Decimal(str(txn.price)),
                    # Purchase brokerage forms part of the cost of acquisition.
                    'charges_per_unit': _charges_per_unit(txn),
                    'date': txn.transaction_date,
                    'transaction_id': txn.id
                })

            elif txn.type.lower() == 'sell':
                sell_qty = Decimal(str(txn.quantity))
                sell_price = Decimal(str(txn.price))
                # Selling costs are expenses on transfer, deducted from the
                # sale consideration before the gain is computed.
                sell_charges_per_unit = _charges_per_unit(txn)
                sell_date = txn.transaction_date
                sell_date_naive = _naive(sell_date)

                # Only sells settled within the requested FY are reported, but the
                # lots they consume are still removed so later-FY reports see the
                # correct remaining cost basis.
                in_scope = (
                    fy_bounds is None
                    or (sell_date_naive is not None and fy_bounds[0] <= sell_date_naive <= fy_bounds[1])
                )

                # Apply FIFO or LIFO
                if method == 'LIFO':
                    queue_to_process = list(reversed(buy_queue))
                else:  # FIFO
                    queue_to_process = buy_queue

                remaining_sell_qty = sell_qty
                lots_to_remove = []

                for i, lot in enumerate(queue_to_process):
                    if remaining_sell_qty <= 0:
                        break

                    matched_qty = min(lot['qty'], remaining_sell_qty)

                    # Calculate holding period (tz-normalized so mixed rows don't crash)
                    holding_days = (sell_date_naive - _naive(lot['date'])).days
                    is_long_term = holding_days >= TaxCalculator.STCG_HOLDING_DAYS

                    # Net sale consideration and cost of acquisition, both after
                    # deductible charges (STT is excluded by _charges_per_unit).
                    net_sell_price = sell_price - sell_charges_per_unit
                    cost_per_unit = lot['price'] + lot.get('charges_per_unit', Decimal("0"))

                    # Section 112A: step the cost up to the 31-Jan-2018 FMV for
                    # long-term lots acquired before 1 Feb 2018.
                    grandfathered = False
                    fmv_missing = False
                    if grandfathering.is_eligible(
                        lot['date'], holding_days, TaxCalculator.STCG_HOLDING_DAYS
                    ):
                        if grandfathering.get_fmv(symbol) is None:
                            fmv_missing = True
                            symbols_missing_fmv.add(symbol)
                        else:
                            cost_per_unit, grandfathered = grandfathering.stepped_up_cost(
                                symbol, cost_per_unit, net_sell_price
                            )

                    gain = matched_qty * (net_sell_price - cost_per_unit)
                    lot_charges = matched_qty * (
                        sell_charges_per_unit + lot.get('charges_per_unit', Decimal("0"))
                    )

                    if in_scope:
                        # Only charges against reported sells count toward the
                        # reported total; an earlier FY's costs belong to that
                        # year's report, not this one.
                        charges_deducted += lot_charges
                        transaction_detail = {
                            'buy_date': lot['date'].strftime('%Y-%m-%d'),
                            'sell_date': sell_date.strftime('%Y-%m-%d'),
                            'quantity': float(matched_qty),
                            'buy_price': float(lot['price']),
                            'sell_price': float(sell_price),
                            'cost_basis_per_unit': float(cost_per_unit),
                            'net_sell_price': float(net_sell_price),
                            'charges': float(lot_charges),
                            'gain': float(gain),
                            'holding_days': holding_days,
                            'grandfathered': grandfathered,
                            'fmv_missing': fmv_missing,
                            'buy_transaction_id': lot['transaction_id'],
                            'sell_transaction_id': txn.id
                        }

                        if not is_long_term:
                            stcg_total += gain
                            stcg_transactions.append(transaction_detail)
                        else:
                            ltcg_total += gain
                            ltcg_transactions.append(transaction_detail)

                    # Update lot quantity
                    lot['qty'] -= matched_qty
                    remaining_sell_qty -= matched_qty

                    if lot['qty'] == 0:
                        lots_to_remove.append(lot)
                
                # Remove fully consumed lots from buy_queue
                for lot in lots_to_remove:
                    if lot in buy_queue:
                        buy_queue.remove(lot)
        
        # Calculate taxes (without exemption at symbol level)
        stcg_tax = stcg_total * TaxCalculator.STCG_TAX_RATE
        ltcg_tax_without_exemption = ltcg_total * TaxCalculator.LTCG_TAX_RATE
        
        result = {
            'stcg_gain': float(stcg_total),
            'ltcg_gain': float(ltcg_total),
            'stcg_tax': float(stcg_tax),
            'ltcg_tax_without_exemption': float(ltcg_tax_without_exemption),
            'stcg_transactions': stcg_transactions,
            'ltcg_transactions': ltcg_transactions,
            'realized_count': len(stcg_transactions) + len(ltcg_transactions),
            'charges_deducted': float(charges_deducted),
            'grandfathering_applied': any(
                t.get('grandfathered') for t in ltcg_transactions
            ),
            'fmv_missing': sorted(symbols_missing_fmv),
        }
        
        # Calculate unrealized gains if requested
        if include_unrealized and buy_queue:
            unrealized_gain = Decimal("0")
            current_holdings = []
            
            # Get current price from the asset (assuming latest transaction has it)
            current_price = None
            if txns and hasattr(txns[-1], 'asset') and txns[-1].asset:
                current_price = Decimal(str(txns[-1].asset.current_price))
            
            for lot in buy_queue:
                if current_price:
                    # Same cost basis the realized path uses, so a lot's
                    # unrealized gain does not jump when it is sold.
                    cost_per_unit = lot['price'] + lot.get('charges_per_unit', Decimal("0"))
                    lot_gain = lot['qty'] * (current_price - cost_per_unit)
                    unrealized_gain += lot_gain

                    holding_days = (datetime.now() - _naive(lot['date'])).days

                    current_holdings.append({
                        'buy_date': lot['date'].strftime('%Y-%m-%d'),
                        'quantity': float(lot['qty']),
                        'buy_price': float(lot['price']),
                        'cost_basis_per_unit': float(cost_per_unit),
                        'current_price': float(current_price),
                        'unrealized_gain': float(lot_gain),
                        'holding_days': holding_days,
                        'gain_type': 'LTCG' if holding_days >= TaxCalculator.STCG_HOLDING_DAYS else 'STCG'
                    })
            
            result['unrealized_gain'] = float(unrealized_gain)
            result['current_holdings'] = current_holdings
        
        return result
    
    @staticmethod
    def filter_by_financial_year(
        transactions: List,
        financial_year: str
    ) -> List:
        """
        Filter transactions by Indian financial year (April 1 - March 31).
        
        Args:
            transactions: List of TransactionModel objects
            financial_year: Format "2024-25" or "FY2024-25"
        
        Returns:
            Filtered list of transactions
        """
        # Parse financial year
        fy = financial_year.replace('FY', '').strip()
        start_year, end_year = map(int, fy.split('-'))
        
        # Handle 2-digit year format
        if end_year < 100:
            end_year = 2000 + end_year
        if start_year < 100:
            start_year = 2000 + start_year
        
        # Indian FY: April 1 to March 31
        fy_start = datetime(start_year, 4, 1)
        fy_end = datetime(end_year, 3, 31, 23, 59, 59)
        
        filtered = []
        for txn in transactions:
            # Normalise: strip tzinfo so comparison is always offset-naive
            txn_date = txn.transaction_date
            if txn_date is not None and txn_date.tzinfo is not None:
                txn_date = txn_date.replace(tzinfo=None)
            # Only filter sell transactions (they trigger capital gains)
            if txn.type.lower() == 'sell':
                if txn_date is not None and fy_start <= txn_date <= fy_end:
                    filtered.append(txn)
            else:
                # Always include buy transactions (needed for cost basis)
                filtered.append(txn)
        
        return filtered
    
    @staticmethod
    def get_available_financial_years(transactions: List) -> List[str]:
        """
        Get list of financial years that have transactions.
        
        Args:
            transactions: List of TransactionModel objects
        
        Returns:
            List of financial year strings like ["2024-25", "2023-24"]
        """
        if not transactions:
            return []
        
        years_set = set()
        for txn in transactions:
            date = txn.transaction_date
            # Determine which FY this transaction belongs to
            if date.month >= 4:  # April onwards = current FY
                fy = f"{date.year}-{str(date.year + 1)[-2:]}"
            else:  # Jan-Mar = previous FY
                fy = f"{date.year - 1}-{str(date.year)[-2:]}"
            years_set.add(fy)
        
        # Sort in descending order (most recent first)
        return sorted(list(years_set), reverse=True)
