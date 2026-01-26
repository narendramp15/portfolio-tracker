export function formatCurrencyINR(value: number | string) {
  const numeric = Number(value) || 0
  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(numeric)
  } catch {
    return `₹${Math.round(numeric).toLocaleString('en-IN')}`
  }
}

export function formatPercent(value: number | string) {
  const numeric = Number(value) || 0
  const sign = numeric > 0 ? '+' : ''
  return `${sign}${numeric.toFixed(2)}%`
}
