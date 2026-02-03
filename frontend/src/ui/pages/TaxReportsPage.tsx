import { useState, useEffect } from 'react'
import { FileText, TrendingUp, Calculator, Download, AlertCircle, Info } from 'lucide-react'
import { api } from '../../lib/api'
import { useAppStore } from '../../store/appStore'
import { formatCurrencyINR, formatPercent } from '../../lib/format'

interface SymbolGain {
    symbol: string
    name: string
    stcg: number
    ltcg: number
    total_gain: number
}

interface TransactionDetail {
    buy_date: string
    sell_date: string
    quantity: number
    buy_price: number
    sell_price: number
    gain: number
    holding_days: number
}

interface SymbolReport {
    stcg_gain: number
    ltcg_gain: number
    stcg_tax: number
    ltcg_tax_without_exemption: number
    stcg_transactions: TransactionDetail[]
    ltcg_transactions: TransactionDetail[]
    realized_count: number
    unrealized_gain?: number
    current_holdings?: any[]
}

interface TaxReport {
    portfolio_id: number
    portfolio_name: string
    financial_year: string
    method: string
    summary: {
        total_stcg: number
        total_ltcg: number
        total_stcg_tax: number
        total_ltcg_tax: number
        total_tax: number
        ltcg_exemption_used: number
        symbols: SymbolGain[]
    }
    by_symbol: Record<string, SymbolReport>
    available_financial_years: string[]
}

export default function TaxReportsPage() {
    const { selectedPortfolioId } = useAppStore()
    const [taxReport, setTaxReport] = useState<TaxReport | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [financialYear, setFinancialYear] = useState<string>('All Time')
    const [method, setMethod] = useState<'FIFO' | 'LIFO'>('FIFO')
    const [includeUnrealized, setIncludeUnrealized] = useState(false)
    const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null)

    useEffect(() => {
        if (selectedPortfolioId) {
            fetchTaxReport()
        }
    }, [selectedPortfolioId, financialYear, method, includeUnrealized])

    const fetchTaxReport = async () => {
        if (!selectedPortfolioId) return

        setLoading(true)
        setError(null)

        try {
            const params = new URLSearchParams({
                method,
                include_unrealized: includeUnrealized.toString(),
            })

            if (financialYear !== 'All Time') {
                params.append('financial_year', financialYear)
            }

            const response = await api.get(
                `/tax-reports/portfolios/${selectedPortfolioId}/capital-gains?${params}`
            )
            setTaxReport(response.data)

            // Set default FY if not set
            if (financialYear === 'All Time' && response.data.available_financial_years.length > 0) {
                setFinancialYear(response.data.available_financial_years[0])
            }
        } catch (err: any) {
            console.error('Error fetching tax report:', err)
            setError(err.response?.data?.detail || 'Failed to fetch tax report')
        } finally {
            setLoading(false)
        }
    }

    const handleDownloadCSV = () => {
        if (!taxReport) return

        // Generate CSV content
        let csvContent = 'Symbol,Name,Buy Date,Sell Date,Quantity,Buy Price,Sell Price,Gain,Holding Days,Type\n'

        Object.entries(taxReport.by_symbol).forEach(([symbol, data]) => {
            const symbolName = taxReport.summary.symbols.find(s => s.symbol === symbol)?.name || symbol

            data.stcg_transactions.forEach(tx => {
                csvContent += `${symbol},${symbolName},${tx.buy_date},${tx.sell_date},${tx.quantity},${tx.buy_price},${tx.sell_price},${tx.gain},${tx.holding_days},STCG\n`
            })

            data.ltcg_transactions.forEach(tx => {
                csvContent += `${symbol},${symbolName},${tx.buy_date},${tx.sell_date},${tx.quantity},${tx.buy_price},${tx.sell_price},${tx.gain},${tx.holding_days},LTCG\n`
            })
        })

        // Download
        const blob = new Blob([csvContent], { type: 'text/csv' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `tax-report-${taxReport.portfolio_name}-${taxReport.financial_year}.csv`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
    }

    if (!selectedPortfolioId) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="text-center">
                    <AlertCircle className="w-12 h-12 text-muted mx-auto mb-4" />
                    <p className="text-muted">Please select a portfolio to view tax reports</p>
                </div>
            </div>
        )
    }

    if (loading && !taxReport) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                    <p className="text-muted">Loading tax report...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <FileText className="w-8 h-8 text-primary" />
                    <div>
                        <h1 className="text-3xl font-bold text-text">Tax Reports</h1>
                        <p className="text-muted">Capital gains (STCG/LTCG) calculation for ITR filing</p>
                    </div>
                </div>
            </div>

            {/* Controls */}
            <div className="bg-surface border border-border rounded-lg p-6">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* Financial Year */}
                    <div>
                        <label className="block text-sm font-medium text-text mb-2">
                            Financial Year
                        </label>
                        <select
                            value={financialYear}
                            onChange={(e) => setFinancialYear(e.target.value)}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-text focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                            <option value="All Time">All Time</option>
                            {taxReport?.available_financial_years.map((fy) => (
                                <option key={fy} value={fy}>
                                    FY {fy}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Method */}
                    <div>
                        <label className="block text-sm font-medium text-text mb-2">
                            Cost Basis Method
                        </label>
                        <select
                            value={method}
                            onChange={(e) => setMethod(e.target.value as 'FIFO' | 'LIFO')}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-text focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                            <option value="FIFO">FIFO (First In First Out)</option>
                            <option value="LIFO">LIFO (Last In First Out)</option>
                        </select>
                    </div>

                    {/* Include Unrealized */}
                    <div className="flex items-end">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={includeUnrealized}
                                onChange={(e) => setIncludeUnrealized(e.target.checked)}
                                className="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary"
                            />
                            <span className="text-sm text-text">Include unrealized gains</span>
                        </label>
                    </div>

                    {/* Download */}
                    <div className="flex items-end">
                        <button
                            onClick={handleDownloadCSV}
                            disabled={!taxReport}
                            className="w-full bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <Download className="w-4 h-4" />
                            Export CSV
                        </button>
                    </div>
                </div>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/50 text-red-600 px-4 py-3 rounded-lg flex items-center gap-2">
                    <AlertCircle className="w-5 h-5" />
                    {error}
                </div>
            )}

            {taxReport && (
                <>
                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="bg-surface border border-border rounded-lg p-6">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm text-muted">Short-Term (STCG)</span>
                                <TrendingUp className="w-4 h-4 text-orange-500" />
                            </div>
                            <div className="text-2xl font-bold text-text mb-1">
                                {formatCurrencyINR(taxReport.summary.total_stcg)}
                            </div>
                            <div className="text-xs text-muted">
                                Tax @ 20%: {formatCurrencyINR(taxReport.summary.total_stcg_tax)}
                            </div>
                        </div>

                        <div className="bg-surface border border-border rounded-lg p-6">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm text-muted">Long-Term (LTCG)</span>
                                <TrendingUp className="w-4 h-4 text-green-500" />
                            </div>
                            <div className="text-2xl font-bold text-text mb-1">
                                {formatCurrencyINR(taxReport.summary.total_ltcg)}
                            </div>
                            <div className="text-xs text-muted">
                                Tax @ 12.5%: {formatCurrencyINR(taxReport.summary.total_ltcg_tax)}
                            </div>
                        </div>

                        <div className="bg-surface border border-border rounded-lg p-6">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm text-muted">LTCG Exemption</span>
                                <Info className="w-4 h-4 text-blue-500" />
                            </div>
                            <div className="text-2xl font-bold text-blue-600 mb-1">
                                {formatCurrencyINR(taxReport.summary.ltcg_exemption_used)}
                            </div>
                            <div className="text-xs text-muted">
                                of ₹1,25,000 used
                            </div>
                        </div>

                        <div className="bg-surface border border-border rounded-lg p-6">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm text-muted">Total Tax Liability</span>
                                <Calculator className="w-4 h-4 text-red-500" />
                            </div>
                            <div className="text-2xl font-bold text-red-600 mb-1">
                                {formatCurrencyINR(taxReport.summary.total_tax)}
                            </div>
                            <div className="text-xs text-muted">
                                {taxReport.financial_year}
                            </div>
                        </div>
                    </div>

                    {/* Info Banner */}
                    <div className="bg-blue-500/10 border border-blue-500/50 rounded-lg p-4 flex items-start gap-3">
                        <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                        <div className="text-sm text-blue-900 dark:text-blue-100">
                            <p className="font-semibold mb-1">India Tax Rules (Listed Equity) - Post Budget 2024</p>
                            <ul className="list-disc list-inside space-y-1 text-xs">
                                <li><strong>STCG</strong> (&lt; 1 year): 20% flat rate</li>
                                <li><strong>LTCG</strong> (≥ 1 year): 12.5% with ₹1.25L annual exemption</li>
                                <li>No indexation benefits under 12.5% LTCG regime</li>
                                <li>STT (Securities Transaction Tax) applies to all equity trades</li>
                                <li>Method: {method} (can switch to see impact)</li>
                            </ul>
                        </div>
                    </div>

                    {/* By Symbol Breakdown */}
                    <div className="bg-surface border border-border rounded-lg overflow-hidden">
                        <div className="px-6 py-4 border-b border-border">
                            <h2 className="text-xl font-bold text-text">Gains by Symbol</h2>
                        </div>

                        {taxReport.summary.symbols.length === 0 ? (
                            <div className="p-8 text-center text-muted">
                                No realized capital gains for the selected period.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-background">
                                        <tr>
                                            <th className="px-6 py-4 text-left text-xs font-semibold text-text uppercase">
                                                Symbol
                                            </th>
                                            <th className="px-6 py-4 text-right text-xs font-semibold text-text uppercase">
                                                STCG
                                            </th>
                                            <th className="px-6 py-4 text-right text-xs font-semibold text-text uppercase">
                                                LTCG
                                            </th>
                                            <th className="px-6 py-4 text-right text-xs font-semibold text-text uppercase">
                                                Total Gain
                                            </th>
                                            <th className="px-6 py-4 text-center text-xs font-semibold text-text uppercase">
                                                Details
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border">
                                        {taxReport.summary.symbols.map((symbolData) => {
                                            const isExpanded = expandedSymbol === symbolData.symbol
                                            const details = taxReport.by_symbol[symbolData.symbol]

                                            return (
                                                <>
                                                    <tr key={symbolData.symbol} className="hover:bg-surface/80">
                                                        <td className="px-6 py-4">
                                                            <div className="font-semibold text-text">{symbolData.symbol}</div>
                                                            <div className="text-sm text-muted">{symbolData.name}</div>
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            <span className="text-orange-600 font-medium">
                                                                {formatCurrencyINR(symbolData.stcg)}
                                                            </span>
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            <span className="text-green-600 font-medium">
                                                                {formatCurrencyINR(symbolData.ltcg)}
                                                            </span>
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            <span className={`font-bold ${symbolData.total_gain >= 0 ? 'text-green-600' : 'text-red-600'
                                                                }`}>
                                                                {formatCurrencyINR(symbolData.total_gain)}
                                                            </span>
                                                        </td>
                                                        <td className="px-6 py-4 text-center">
                                                            <button
                                                                onClick={() => setExpandedSymbol(isExpanded ? null : symbolData.symbol)}
                                                                className="text-primary hover:text-primary/80 text-sm font-medium"
                                                            >
                                                                {isExpanded ? 'Hide' : 'Show'} ({details.realized_count})
                                                            </button>
                                                        </td>
                                                    </tr>

                                                    {isExpanded && (
                                                        <tr>
                                                            <td colSpan={5} className="px-6 py-4 bg-background/50">
                                                                <div className="space-y-4">
                                                                    {details.stcg_transactions.length > 0 && (
                                                                        <div>
                                                                            <h4 className="text-sm font-semibold text-orange-600 mb-2">
                                                                                STCG Transactions ({details.stcg_transactions.length})
                                                                            </h4>
                                                                            <div className="space-y-2">
                                                                                {details.stcg_transactions.map((tx, idx) => (
                                                                                    <div key={idx} className="text-xs text-text bg-surface rounded p-2">
                                                                                        <span className="font-medium">{tx.buy_date}</span> → {tx.sell_date} |
                                                                                        Qty: {tx.quantity} | ₹{tx.buy_price} → ₹{tx.sell_price} |
                                                                                        Gain: <span className={tx.gain >= 0 ? 'text-green-600' : 'text-red-600'}>
                                                                                            ₹{tx.gain.toFixed(2)}
                                                                                        </span> |
                                                                                        {tx.holding_days} days
                                                                                    </div>
                                                                                ))}
                                                                            </div>
                                                                        </div>
                                                                    )}

                                                                    {details.ltcg_transactions.length > 0 && (
                                                                        <div>
                                                                            <h4 className="text-sm font-semibold text-green-600 mb-2">
                                                                                LTCG Transactions ({details.ltcg_transactions.length})
                                                                            </h4>
                                                                            <div className="space-y-2">
                                                                                {details.ltcg_transactions.map((tx, idx) => (
                                                                                    <div key={idx} className="text-xs text-text bg-surface rounded p-2">
                                                                                        <span className="font-medium">{tx.buy_date}</span> → {tx.sell_date} |
                                                                                        Qty: {tx.quantity} | ₹{tx.buy_price} → ₹{tx.sell_price} |
                                                                                        Gain: <span className={tx.gain >= 0 ? 'text-green-600' : 'text-red-600'}>
                                                                                            ₹{tx.gain.toFixed(2)}
                                                                                        </span> |
                                                                                        {tx.holding_days} days
                                                                                    </div>
                                                                                ))}
                                                                            </div>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    )}
                                                </>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    )
}
