/**
 * Format a rupee amount.
 *
 * @param fractionDigits number of decimals to show. Defaults to 0, which is
 *   right for portfolio totals but WRONG for per-unit prices and cost basis:
 *   at 0 digits every value below ₹1 renders as "₹0". Pass 2 for anything
 *   quoted per share or per unit.
 */
export function formatCurrencyINR(value: number | string, fractionDigits = 0) {
  const numeric = Number(value) || 0
  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    }).format(numeric)
  } catch {
    return `₹${numeric.toLocaleString('en-IN', {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    })}`
  }
}

/** Per-unit prices, cost basis and anything else where paise are meaningful. */
export function formatPriceINR(value: number | string) {
  return formatCurrencyINR(value, 2)
}

export function formatPercent(value: number | string) {
  const numeric = Number(value) || 0
  const sign = numeric > 0 ? '+' : ''
  return `${sign}${numeric.toFixed(2)}%`
}
