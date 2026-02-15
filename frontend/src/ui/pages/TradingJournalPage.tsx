import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { tradingJournalApi } from '../../lib/trading-journal-api'
import { TradingJournalForm } from '../components/TradingJournalForm'
import type { TradingJournalEntry, TradingJournalSummary, TradingJournalCreate, TradingJournalUpdate } from '../../types/domain'
import { useAppStore } from '../../store/appStore'
import axios from 'axios'

export function TradingJournalPage() {
    const { portfolioId } = useParams<{ portfolioId: string }>()
    const navigate = useNavigate()
    const { selectedPortfolioId, setSelectedPortfolioId } = useAppStore()
    const [entries, setEntries] = useState<TradingJournalEntry[]>([])
    const [summary, setSummary] = useState<TradingJournalSummary | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [showForm, setShowForm] = useState(false)
    const [editingEntry, setEditingEntry] = useState<TradingJournalEntry | null>(null)
    const [formLoading, setFormLoading] = useState(false)

    const pid = portfolioId ? parseInt(portfolioId) : 0

    // Sync URL portfolio ID with store (URL is source of truth)
    useEffect(() => {
        if (pid && pid !== selectedPortfolioId) {
            setSelectedPortfolioId(pid)
        }
    }, [pid])

    // Redirect to selected portfolio if accessing /app/journal without ID
    useEffect(() => {
        if (!portfolioId && selectedPortfolioId) {
            navigate(`/app/journal/${selectedPortfolioId}`, { replace: true })
        }
    }, [portfolioId, selectedPortfolioId, navigate])

    useEffect(() => {
        if (pid) {
            loadData()
        }
    }, [pid])

    const loadData = async () => {
        try {
            setLoading(true)
            setError(null)
            const [entriesData, statsData] = await Promise.all([
                tradingJournalApi.getEntries(pid),
                tradingJournalApi.getStats(pid)
            ])
            setEntries(entriesData)
            setSummary(statsData)
        } catch (err) {
            if (axios.isAxiosError(err) && err.response?.status === 403) {
                setError('This portfolio does not belong to you. Please select your own portfolio.')
                // Redirect to holdings after 3 seconds
                setTimeout(() => navigate('/app/holdings'), 3000)
            } else {
                setError(err instanceof Error ? err.message : 'Failed to load trading journal')
            }
        } finally {
            setLoading(false)
        }
    }

    const handleCreate = async (data: Record<string, unknown>) => {
        try {
            setFormLoading(true)
            await tradingJournalApi.createEntry(pid, data as TradingJournalCreate)
            setShowForm(false)
            loadData()
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to create entry')
        } finally {
            setFormLoading(false)
        }
    }

    const handleUpdate = async (data: Record<string, unknown>) => {
        if (!editingEntry) return
        try {
            setFormLoading(true)
            await tradingJournalApi.updateEntry(pid, editingEntry.id, data as TradingJournalUpdate)
            setEditingEntry(null)
            loadData()
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to update entry')
        } finally {
            setFormLoading(false)
        }
    }

    const handleDelete = async (entry: TradingJournalEntry) => {
        if (!confirm(`Delete trade for ${entry.symbol}?`)) return
        try {
            await tradingJournalApi.deleteEntry(pid, entry.id)
            loadData()
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to delete entry')
        }
    }

    const formatCurrency = (value: number | string | null | undefined) => {
        if (value === null || value === undefined) return '-'
        const num = typeof value === 'string' ? parseFloat(value) : value
        return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(num)
    }

    const formatDate = (dateStr: string | null | undefined) => {
        if (!dateStr) return '-'
        return new Date(dateStr).toLocaleDateString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    if (!pid) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-4">
                <div className="text-lg text-muted">No portfolio selected</div>
                <div className="text-sm text-muted/70">Please select a portfolio from Holdings to view your trading journal</div>
                <button
                    onClick={() => navigate('/app/holdings')}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                >
                    Go to Holdings
                </button>
            </div>
        )
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-gray-500">Loading trading journal...</div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                <div className="text-red-800">{error}</div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Trading Journal</h1>
                <button
                    onClick={() => setShowForm(true)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                    Add Trade
                </button>
            </div>

            {summary && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                        <div className="text-sm text-gray-500 dark:text-gray-400">Total Trades</div>
                        <div className="text-2xl font-bold text-gray-900 dark:text-white">{summary.total_trades}</div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                        <div className="text-sm text-gray-500 dark:text-gray-400">Win Rate</div>
                        <div className="text-2xl font-bold text-gray-900 dark:text-white">{summary.win_rate.toFixed(1)}%</div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                        <div className="text-sm text-gray-500 dark:text-gray-400">Total P/L</div>
                        <div className={`text-2xl font-bold ${Number(summary.total_profit_loss) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(summary.total_profit_loss)}
                        </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                        <div className="text-sm text-gray-500 dark:text-gray-400">Avg P/L</div>
                        <div className={`text-2xl font-bold ${Number(summary.average_profit_loss) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(summary.average_profit_loss)}
                        </div>
                    </div>
                </div>
            )}

            {showForm && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                    <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">New Trade</h2>
                    <TradingJournalForm
                        onSubmit={handleCreate}
                        onCancel={() => setShowForm(false)}
                        isLoading={formLoading}
                        mode="create"
                    />
                </div>
            )}

            {editingEntry && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                    <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Edit Trade</h2>
                    <TradingJournalForm
                        initialData={editingEntry}
                        onSubmit={handleUpdate}
                        onCancel={() => setEditingEntry(null)}
                        isLoading={formLoading}
                        mode="update"
                    />
                </div>
            )}

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Symbol</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Entry</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Exit</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Qty</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">P/L</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Date</th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                        {entries.map(entry => (
                            <tr key={entry.id}>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">{entry.symbol}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">{formatCurrency(entry.entry_price)}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">{formatCurrency(entry.exit_price)}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">{entry.quantity}</td>
                                <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${entry.profit_loss && Number(entry.profit_loss) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {formatCurrency(entry.profit_loss)}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">{formatDate(entry.entry_date)}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                    <button
                                        onClick={() => setEditingEntry(entry)}
                                        className="text-blue-600 hover:text-blue-900 mr-4"
                                    >
                                        Edit
                                    </button>
                                    <button
                                        onClick={() => handleDelete(entry)}
                                        className="text-red-600 hover:text-red-900"
                                    >
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {entries.length === 0 && (
                            <tr>
                                <td colSpan={7} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                                    No trades recorded yet. Add your first trade to get started.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
