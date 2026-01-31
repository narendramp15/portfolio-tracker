import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Download, RefreshCw, TrendingUp, TrendingDown, Wallet, PieChart, ArrowUpRight, ArrowDownRight, Briefcase, BarChart3, Pencil, Trash2 } from 'lucide-react'

import { api } from '../../lib/api'
import { formatCurrencyINR } from '../../lib/format'
import { type Portfolio } from '../../types/domain'
import { useAppStore } from '../../store/appStore'
import { Card } from '../components/Card'
import { StockSearch } from '../components/StockSearch'

async function fetchPortfolios() {
  const { data } = await api.get<Portfolio[]>('/portfolio/')
  return data
}

export function HoldingsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['portfolios'], queryFn: fetchPortfolios })
  const { selectedPortfolioId, setSelectedPortfolioId } = useAppStore()

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isAddOpen, setIsAddOpen] = useState(false)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [editingAsset, setEditingAsset] = useState<typeof holdings[number] | null>(null)

  const [createName, setCreateName] = useState('')
  const [createDesc, setCreateDesc] = useState('')

  const [addPortfolioId, setAddPortfolioId] = useState<number | ''>('')
  const [symbol, setSymbol] = useState('')
  const [name, setName] = useState('')
  const [quantity, setQuantity] = useState('')
  const [purchasePrice, setPurchasePrice] = useState('')
  const [currentPrice, setCurrentPrice] = useState('')

  const portfolios = query.data ?? []

  const holdings = useMemo(() => {
    const filteredPortfolios =
      selectedPortfolioId === null ? portfolios : portfolios.filter((p: Portfolio) => p.id === selectedPortfolioId)

    return filteredPortfolios.flatMap((p: Portfolio) =>
      (p.assets ?? []).map((a: Portfolio['assets'][number]) => {
        const qty = Number(a.quantity)
        const ltp = Number(a.current_price)
        const avg = Number(a.purchase_price)
        const previousClose = Number((a as any).previous_close) || null
        const marketValue = qty * ltp
        const invested = qty * avg
        const pnl = marketValue - invested
        const pnlPercent = invested > 0 ? (pnl / invested) * 100 : 0
        const dayChange = previousClose ? (ltp - previousClose) * qty : null
        const dayChangePercent = previousClose && previousClose > 0 ? ((ltp - previousClose) / previousClose) * 100 : null

        return {
          ...a,
          quantity: qty,
          current_price: ltp,
          purchase_price: avg,
          previous_close: previousClose,
          portfolioName: p.name,
          marketValue,
          invested,
          pnl,
          pnlPercent,
          dayChange,
          dayChangePercent,
        }
      }),
    )
  }, [portfolios, selectedPortfolioId])

  // Calculate totals for the summary
  const totals = useMemo(() => {
    const totalMarketValue = holdings.reduce((sum, h) => sum + h.marketValue, 0)
    const totalInvested = holdings.reduce((sum, h) => sum + h.invested, 0)
    const totalPnl = holdings.reduce((sum, h) => sum + h.pnl, 0)
    const totalDayChange = holdings.reduce((sum, h) => sum + (h.dayChange ?? 0), 0)
    const totalPreviousValue = holdings.reduce((sum, h) => {
      if (h.previous_close && h.previous_close > 0) {
        return sum + (h.previous_close * h.quantity)
      }
      return sum
    }, 0)

    return {
      marketValue: totalMarketValue,
      invested: totalInvested,
      pnl: totalPnl,
      pnlPercent: totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0,
      dayChange: totalDayChange,
      dayChangePercent: totalPreviousValue > 0 ? (totalDayChange / totalPreviousValue) * 100 : 0,
      hasAnyDayChange: holdings.some(h => h.dayChange !== null),
    }
  }, [holdings])

  const createPortfolio = useMutation({
    mutationFn: async () => {
      const trimmed = createName.trim()
      if (!trimmed) throw new Error('Portfolio name is required')
      const payload: any = { name: trimmed }
      if (createDesc.trim()) payload.description = createDesc.trim()
      const { data } = await api.post<Portfolio>('/portfolio/', payload)
      return data
    },
    onSuccess: async (created) => {
      setIsCreateOpen(false)
      setCreateName('')
      setCreateDesc('')
      if (created?.id) {
        setSelectedPortfolioId(created.id)
      }
      await queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })

  const addHolding = useMutation({
    mutationFn: async () => {
      const effectivePortfolioId = addPortfolioId || selectedPortfolioId
      if (!effectivePortfolioId) throw new Error('Select a portfolio')
      const qty = Number(quantity)
      const avg = Number(purchasePrice)
      if (!symbol.trim()) throw new Error('Symbol is required')
      if (!Number.isFinite(qty) || qty <= 0) throw new Error('Quantity must be > 0')
      if (!Number.isFinite(avg) || avg <= 0) throw new Error('Purchase price must be > 0')

      // Name and current_price are now optional - backend will auto-fill
      const payload: any = {
        symbol: symbol.trim().toUpperCase(),
        quantity: qty,
        purchase_price: avg,
      }

      if (name.trim()) {
        payload.name = name.trim()
      }

      if (currentPrice && Number(currentPrice) > 0) {
        payload.current_price = Number(currentPrice)
      }

      await api.post(`/portfolio/${effectivePortfolioId}/assets`, payload)
    },
    onSuccess: async () => {
      setIsAddOpen(false)
      // Keep portfolio selection for subsequent adds
      setSymbol('')
      setName('')
      setQuantity('')
      setPurchasePrice('')
      setCurrentPrice('')
      await queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })

  const updateHolding = useMutation({
    mutationFn: async () => {
      if (!editingAsset) throw new Error('No asset selected')
      const qty = Number(quantity)
      const avg = Number(purchasePrice)
      if (!Number.isFinite(qty) || qty <= 0) throw new Error('Quantity must be > 0')
      if (!Number.isFinite(avg) || avg <= 0) throw new Error('Purchase price must be > 0')

      const payload: any = {
        quantity: qty,
        purchase_price: avg,
      }

      if (currentPrice && Number(currentPrice) > 0) {
        payload.current_price = Number(currentPrice)
      }

      await api.put(`/portfolio/${editingAsset.portfolio_id}/assets/${editingAsset.id}`, payload)
    },
    onSuccess: async () => {
      setIsEditOpen(false)
      setEditingAsset(null)
      setQuantity('')
      setPurchasePrice('')
      setCurrentPrice('')
      await queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })

  const deleteHolding = useMutation({
    mutationFn: async (asset: typeof holdings[number]) => {
      await api.delete(`/portfolio/${asset.portfolio_id}/assets/${asset.id}`)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })

  const handleEditAsset = (asset: typeof holdings[number]) => {
    setEditingAsset(asset)
    setQuantity(String(asset.quantity))
    setPurchasePrice(String(asset.purchase_price))
    setCurrentPrice(String(asset.current_price))
    setIsEditOpen(true)
  }

  const handleDeleteAsset = async (asset: typeof holdings[number]) => {
    if (confirm(`Are you sure you want to delete ${asset.symbol} from ${asset.portfolioName}?`)) {
      deleteHolding.mutate(asset)
    }
  }

  const handleExportCSV = async (portfolioId?: number) => {
    try {
      const url = portfolioId ? `/portfolio/${portfolioId}/export` : null
      if (!url) return

      const response = await api.get(url, { responseType: 'blob' })
      const blob = new Blob([response.data], { type: 'text/csv' })
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = `portfolio_${portfolioId}_holdings.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Failed to export CSV')
    }
  }

  const handleRefreshPrices = async () => {
    if (!selectedPortfolioId) {
      alert('Please select a portfolio first')
      return
    }

    try {
      const response = await api.post(`/market/portfolios/${selectedPortfolioId}/refresh-prices`)
      await queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      alert(`Prices updated! ${response.data.updated} assets refreshed, ${response.data.failed} failed`)
    } catch (error) {
      console.error('Refresh failed:', error)
      alert('Failed to refresh prices')
    }
  }

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-indigo-400/70 flex items-center gap-2">
            <span className="inline-block w-8 h-0.5 bg-gradient-to-r from-indigo-500 to-transparent rounded-full"></span>
            Portfolio
          </div>
          <h1 className="mt-3 text-4xl font-black tracking-tight bg-gradient-to-r from-indigo-400 via-purple-300 to-indigo-500 bg-clip-text text-transparent">
            Holdings
          </h1>
          <p className="mt-1 text-sm text-muted">Track and manage your investment positions</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            className="h-10 rounded-xl border border-border bg-surface px-4 text-sm font-medium transition-all hover:border-indigo-500/50 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            value={selectedPortfolioId ?? ''}
            onChange={(e) => setSelectedPortfolioId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">All portfolios</option>
            {portfolios.map((p: Portfolio) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>

          {selectedPortfolioId && (
            <>
              <button
                type="button"
                onClick={handleRefreshPrices}
                className="inline-flex h-10 items-center gap-2 rounded-xl border border-border bg-surface px-4 text-sm font-semibold transition-all hover:border-emerald-500/50 hover:bg-emerald-500/10 hover:text-emerald-400"
              >
                <RefreshCw className="h-4 w-4" />
                <span className="hidden sm:inline">Refresh</span>
              </button>
              <button
                type="button"
                onClick={() => handleExportCSV(selectedPortfolioId)}
                className="inline-flex h-10 items-center gap-2 rounded-xl border border-border bg-surface px-4 text-sm font-semibold transition-all hover:border-sky-500/50 hover:bg-sky-500/10 hover:text-sky-400"
              >
                <Download className="h-4 w-4" />
                <span className="hidden sm:inline">Export</span>
              </button>
            </>
          )}

          <button
            type="button"
            onClick={() => setIsCreateOpen(true)}
            className="inline-flex h-10 items-center gap-2 rounded-xl border border-border bg-surface px-4 text-sm font-semibold transition-all hover:border-purple-500/50 hover:bg-purple-500/10 hover:text-purple-400"
          >
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">New Portfolio</span>
          </button>

          <button
            type="button"
            onClick={() => setIsAddOpen(true)}
            className="inline-flex h-10 items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all hover:shadow-indigo-500/40 hover:scale-[1.02] disabled:opacity-50 disabled:hover:scale-100"
            disabled={portfolios.length === 0}
          >
            <Plus className="h-4 w-4" />
            Add Holding
          </button>
        </div>
      </div>

      {query.isLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-2xl border border-border bg-surface/50" />
          ))}
        </div>
      ) : query.isError ? (
        <Card className="border-rose-500/30 bg-rose-500/5">
          <div className="text-sm font-medium text-rose-400">Failed to load holdings. Please try again.</div>
        </Card>
      ) : holdings.length === 0 ? (
        <Card className="py-16 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-indigo-500/10">
            <Wallet className="h-8 w-8 text-indigo-400" />
          </div>
          <div className="text-lg font-semibold">No holdings yet</div>
          <div className="mt-2 text-sm text-muted max-w-sm mx-auto">
            Create a portfolio and add your first holding, or connect your broker to sync automatically.
          </div>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={() => setIsCreateOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25"
            >
              <Plus className="h-4 w-4" />
              Create Portfolio
            </button>
          </div>
        </Card>
      ) : (
        <>
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {/* Market Value */}
            <div className="group relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-surface to-surface/50 p-5 transition-all hover:border-indigo-500/30 hover:shadow-lg hover:shadow-indigo-500/5">
              <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-indigo-500/5 blur-2xl transition-all group-hover:bg-indigo-500/10" />
              <div className="relative">
                <div className="flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/10">
                    <Wallet className="h-4 w-4 text-indigo-400" />
                  </div>
                  <span className="text-xs font-bold uppercase tracking-wider text-muted">Current Value</span>
                </div>
                <div className="mt-3 text-2xl font-black tracking-tight">{formatCurrencyINR(totals.marketValue)}</div>
              </div>
            </div>

            {/* Invested */}
            <div className="group relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-surface to-surface/50 p-5 transition-all hover:border-purple-500/30 hover:shadow-lg hover:shadow-purple-500/5">
              <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-purple-500/5 blur-2xl transition-all group-hover:bg-purple-500/10" />
              <div className="relative">
                <div className="flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-500/10">
                    <PieChart className="h-4 w-4 text-purple-400" />
                  </div>
                  <span className="text-xs font-bold uppercase tracking-wider text-muted">Invested</span>
                </div>
                <div className="mt-3 text-2xl font-black tracking-tight">{formatCurrencyINR(totals.invested)}</div>
              </div>
            </div>

            {/* Total P&L */}
            <div className={`group relative overflow-hidden rounded-2xl border p-5 transition-all hover:shadow-lg ${totals.pnl >= 0
              ? 'border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-surface/50 hover:border-emerald-500/40 hover:shadow-emerald-500/5'
              : 'border-rose-500/20 bg-gradient-to-br from-rose-500/5 to-surface/50 hover:border-rose-500/40 hover:shadow-rose-500/5'
              }`}>
              <div className={`absolute -right-4 -top-4 h-24 w-24 rounded-full blur-2xl transition-all ${totals.pnl >= 0 ? 'bg-emerald-500/5 group-hover:bg-emerald-500/10' : 'bg-rose-500/5 group-hover:bg-rose-500/10'}`} />
              <div className="relative">
                <div className="flex items-center gap-2">
                  <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${totals.pnl >= 0 ? 'bg-emerald-500/10' : 'bg-rose-500/10'}`}>
                    {totals.pnl >= 0 ? <TrendingUp className="h-4 w-4 text-emerald-400" /> : <TrendingDown className="h-4 w-4 text-rose-400" />}
                  </div>
                  <span className="text-xs font-bold uppercase tracking-wider text-muted">Total P&L</span>
                </div>
                <div className={`mt-3 text-2xl font-black tracking-tight ${totals.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {totals.pnl >= 0 ? '+' : ''}{formatCurrencyINR(totals.pnl)}
                </div>
                <div className={`mt-1 flex items-center gap-1 text-sm font-semibold ${totals.pnl >= 0 ? 'text-emerald-400/80' : 'text-rose-400/80'}`}>
                  {totals.pnl >= 0 ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
                  {totals.pnl >= 0 ? '+' : ''}{totals.pnlPercent.toFixed(2)}%
                </div>
              </div>
            </div>

            {/* Day Change */}
            <div className={`group relative overflow-hidden rounded-2xl border p-5 transition-all hover:shadow-lg ${!totals.hasAnyDayChange
              ? 'border-border bg-gradient-to-br from-surface to-surface/50'
              : totals.dayChange >= 0
                ? 'border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-surface/50 hover:border-emerald-500/40 hover:shadow-emerald-500/5'
                : 'border-rose-500/20 bg-gradient-to-br from-rose-500/5 to-surface/50 hover:border-rose-500/40 hover:shadow-rose-500/5'
              }`}>
              <div className={`absolute -right-4 -top-4 h-24 w-24 rounded-full blur-2xl transition-all ${!totals.hasAnyDayChange ? 'bg-slate-500/5' : totals.dayChange >= 0 ? 'bg-emerald-500/5 group-hover:bg-emerald-500/10' : 'bg-rose-500/5 group-hover:bg-rose-500/10'
                }`} />
              <div className="relative">
                <div className="flex items-center gap-2">
                  <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${!totals.hasAnyDayChange ? 'bg-slate-500/10' : totals.dayChange >= 0 ? 'bg-emerald-500/10' : 'bg-rose-500/10'
                    }`}>
                    <BarChart3 className={`h-4 w-4 ${!totals.hasAnyDayChange ? 'text-slate-400' : totals.dayChange >= 0 ? 'text-emerald-400' : 'text-rose-400'}`} />
                  </div>
                  <span className="text-xs font-bold uppercase tracking-wider text-muted">Day Change</span>
                </div>
                {totals.hasAnyDayChange ? (
                  <>
                    <div className={`mt-3 text-2xl font-black tracking-tight ${totals.dayChange >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {totals.dayChange >= 0 ? '+' : ''}{formatCurrencyINR(totals.dayChange)}
                    </div>
                    <div className={`mt-1 flex items-center gap-1 text-sm font-semibold ${totals.dayChange >= 0 ? 'text-emerald-400/80' : 'text-rose-400/80'}`}>
                      {totals.dayChange >= 0 ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
                      {totals.dayChange >= 0 ? '+' : ''}{totals.dayChangePercent.toFixed(2)}%
                    </div>
                  </>
                ) : (
                  <>
                    <div className="mt-3 text-2xl font-black tracking-tight text-muted">—</div>
                    <div className="mt-1 text-xs text-muted">Click Refresh to update</div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Holdings Table */}
          <div className="rounded-2xl border border-border bg-surface/50 overflow-hidden">
            {/* Table Header */}
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div className="flex items-center gap-3">
                <h2 className="text-sm font-bold uppercase tracking-wider text-muted">All Holdings</h2>
                <span className="rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-xs font-bold text-indigo-400">
                  {holdings.length}
                </span>
              </div>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                <input
                  className="h-9 w-[200px] rounded-xl border border-border bg-bg pl-9 pr-3 text-sm outline-none transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                  placeholder="Search holdings..."
                  type="search"
                />
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1000px]">
                <thead>
                  <tr className="border-b border-border bg-bg/50">
                    <th className="px-5 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted">Stock</th>
                    <th className="px-4 py-3 text-right text-xs font-bold uppercase tracking-wider text-muted">Qty</th>
                    <th className="px-4 py-3 text-right text-xs font-bold uppercase tracking-wider text-muted">Avg Cost</th>
                    <th className="px-4 py-3 text-right text-xs font-bold uppercase tracking-wider text-muted">LTP</th>
                    <th className="px-4 py-3 text-right text-xs font-bold uppercase tracking-wider text-muted">Value</th>
                    <th className="px-4 py-3 text-right text-xs font-bold uppercase tracking-wider text-muted">P&L</th>
                    <th className="px-4 py-3 text-right text-xs font-bold uppercase tracking-wider text-muted">Day</th>
                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted">Portfolio</th>
                    <th className="px-5 py-3 text-center text-xs font-bold uppercase tracking-wider text-muted">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {holdings.map((h: typeof holdings[number]) => {
                    const isPnlUp = h.pnl >= 0
                    const isDayUp = h.dayChange !== null && h.dayChange >= 0
                    return (
                      <tr
                        key={`${h.portfolio_id}-${h.id}`}
                        className="group transition-colors hover:bg-indigo-500/5"
                      >
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 text-xs font-bold text-indigo-300">
                              {h.symbol.slice(0, 2)}
                            </div>
                            <div>
                              <div className="font-semibold text-text group-hover:text-indigo-400 transition-colors">{h.symbol}</div>
                              <div className="text-xs text-muted truncate max-w-[150px]">{h.name}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <span className="font-mono text-sm">{h.quantity.toFixed(2)}</span>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <span className="font-mono text-sm text-muted">{formatCurrencyINR(h.purchase_price)}</span>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <span className="font-mono text-sm font-semibold">{formatCurrencyINR(h.current_price)}</span>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <span className="font-mono text-sm font-semibold">{formatCurrencyINR(h.marketValue)}</span>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div className={`inline-flex flex-col items-end rounded-lg px-2 py-1 ${isPnlUp ? 'bg-emerald-500/10' : 'bg-rose-500/10'}`}>
                            <span className={`font-mono text-sm font-bold ${isPnlUp ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {isPnlUp ? '+' : ''}{formatCurrencyINR(h.pnl)}
                            </span>
                            <span className={`text-xs ${isPnlUp ? 'text-emerald-400/70' : 'text-rose-400/70'}`}>
                              {isPnlUp ? '+' : ''}{h.pnlPercent.toFixed(2)}%
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-right">
                          {h.dayChange !== null ? (
                            <div className={`inline-flex flex-col items-end rounded-lg px-2 py-1 ${isDayUp ? 'bg-emerald-500/10' : 'bg-rose-500/10'}`}>
                              <span className={`font-mono text-sm font-bold ${isDayUp ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {isDayUp ? '+' : ''}{formatCurrencyINR(h.dayChange)}
                              </span>
                              <span className={`text-xs ${isDayUp ? 'text-emerald-400/70' : 'text-rose-400/70'}`}>
                                {isDayUp ? '+' : ''}{h.dayChangePercent?.toFixed(2)}%
                              </span>
                            </div>
                          ) : (
                            <span className="text-xs text-muted">—</span>
                          )}
                        </td>
                        <td className="px-4 py-4">
                          <span className="inline-flex items-center rounded-full bg-slate-500/10 px-2.5 py-1 text-xs font-medium text-slate-400">
                            {h.portfolioName}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center justify-center gap-1">
                            <button
                              onClick={() => handleEditAsset(h)}
                              className="rounded-lg p-2 text-muted transition-all hover:bg-indigo-500/10 hover:text-indigo-400"
                              title="Edit holding"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteAsset(h)}
                              disabled={deleteHolding.isPending}
                              className="rounded-lg p-2 text-muted transition-all hover:bg-rose-500/10 hover:text-rose-400 disabled:opacity-50"
                              title="Delete holding"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {(isCreateOpen || isAddOpen || isEditOpen) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl">
            {isCreateOpen ? (
              <>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10">
                    <Briefcase className="h-5 w-5 text-purple-400" />
                  </div>
                  <div>
                    <div className="text-lg font-bold">Create Portfolio</div>
                    <div className="text-xs text-muted">Organize your investments</div>
                  </div>
                </div>

                <div className="mt-6 space-y-4">
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-muted">Portfolio Name</label>
                    <input
                      className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                      value={createName}
                      onChange={(e) => setCreateName(e.target.value)}
                      placeholder="e.g., Long-term Investments"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-muted">Description (optional)</label>
                    <textarea
                      className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                      value={createDesc}
                      onChange={(e) => setCreateDesc(e.target.value)}
                      rows={3}
                      placeholder="Describe your investment strategy..."
                    />
                  </div>

                  {createPortfolio.isError ? (
                    <div className="rounded-xl bg-rose-500/10 border border-rose-500/20 px-4 py-3 text-sm font-medium text-rose-400">
                      {(createPortfolio.error as Error).message}
                    </div>
                  ) : null}

                  <div className="flex gap-3 pt-2">
                    <button
                      className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all hover:shadow-indigo-500/40 disabled:opacity-60"
                      disabled={createPortfolio.isPending}
                      onClick={() => createPortfolio.mutate()}
                    >
                      {createPortfolio.isPending ? 'Creating…' : 'Create Portfolio'}
                    </button>
                    <button
                      className="flex-1 rounded-xl border border-border bg-bg px-4 py-3 text-sm font-semibold transition-all hover:bg-surface"
                      onClick={() => setIsCreateOpen(false)}
                      disabled={createPortfolio.isPending}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10">
                    <Plus className="h-5 w-5 text-indigo-400" />
                  </div>
                  <div>
                    <div className="text-lg font-bold">Add Holding</div>
                    <div className="text-xs text-muted">Add a stock to your portfolio</div>
                  </div>
                </div>

                <div className="mt-6 space-y-4">
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-muted">Portfolio</label>
                    <select
                      className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                      value={addPortfolioId || selectedPortfolioId || ''}
                      onChange={(e) => setAddPortfolioId(e.target.value ? Number(e.target.value) : '')}
                    >
                      <option value="">Select portfolio</option>
                      {portfolios.map((p: Portfolio) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-muted">Search Stock</label>
                    <div className="mt-2">
                      <StockSearch
                        market="IN"
                        placeholder="Search by symbol or company name..."
                        onSelect={(stock) => {
                          setSymbol(stock.symbol)
                          setName(stock.name)
                          if (stock.current_price) {
                            setCurrentPrice(String(stock.current_price))
                            // Pre-fill purchase price with current price if empty
                            if (!purchasePrice) {
                              setPurchasePrice(String(stock.current_price))
                            }
                          }
                        }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label className="text-xs font-bold uppercase tracking-wider text-muted">Symbol</label>
                      <input
                        className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                        value={symbol}
                        onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                        placeholder="e.g., INFY.NS or TCS.NS"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-bold uppercase tracking-wider text-muted">Name <span className="text-xs text-muted/60">(optional)</span></label>
                      <input
                        className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Auto-filled from symbol"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-bold uppercase tracking-wider text-muted">Quantity</label>
                      <input
                        className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                        value={quantity}
                        onChange={(e) => setQuantity(e.target.value)}
                        inputMode="decimal"
                        placeholder="e.g., 10"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-bold uppercase tracking-wider text-muted">Avg Cost</label>
                      <input
                        className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                        value={purchasePrice}
                        onChange={(e) => setPurchasePrice(e.target.value)}
                        inputMode="decimal"
                        placeholder="e.g., 1450"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-muted">Current Price <span className="text-xs text-muted/60">(optional)</span></label>
                      <input
                        className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                        value={currentPrice}
                        onChange={(e) => setCurrentPrice(e.target.value)}
                        inputMode="decimal"
                        placeholder="Auto-fetched from live market data"
                      />
                    </div>
                  </div>

                  {addHolding.isError ? (
                    <div className="rounded-xl bg-rose-500/10 border border-rose-500/20 px-4 py-3 text-sm font-medium text-rose-400">
                      {(addHolding.error as Error).message}
                    </div>
                  ) : null}

                  <div className="flex gap-3 pt-2">
                    <button
                      className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all hover:shadow-indigo-500/40 disabled:opacity-60"
                      disabled={addHolding.isPending}
                      onClick={() => addHolding.mutate()}
                    >
                      {addHolding.isPending ? 'Adding…' : 'Add Holding'}
                    </button>
                    <button
                      className="flex-1 rounded-xl border border-border bg-bg px-4 py-3 text-sm font-semibold transition-all hover:bg-surface"
                      onClick={() => setIsAddOpen(false)}
                      disabled={addHolding.isPending}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Edit Holding Modal */}
      {isEditOpen && editingAsset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10">
                <Pencil className="h-5 w-5 text-amber-400" />
              </div>
              <div>
                <div className="text-lg font-bold">Edit Holding</div>
                <div className="text-xs text-muted">Update {editingAsset.symbol}</div>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="rounded-xl bg-bg/50 border border-border p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 text-xs font-bold text-indigo-300">
                    {editingAsset.symbol.slice(0, 2)}
                  </div>
                  <div>
                    <div className="font-semibold">{editingAsset.symbol}</div>
                    <div className="text-xs text-muted">{editingAsset.name}</div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-muted">Quantity</label>
                  <input
                    className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    inputMode="decimal"
                    placeholder="e.g., 10"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-muted">Avg Cost</label>
                  <input
                    className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                    value={purchasePrice}
                    onChange={(e) => setPurchasePrice(e.target.value)}
                    inputMode="decimal"
                    placeholder="e.g., 1450"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-muted">Current Price <span className="text-xs text-muted/60">(optional)</span></label>
                <input
                  className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  value={currentPrice}
                  onChange={(e) => setCurrentPrice(e.target.value)}
                  inputMode="decimal"
                  placeholder="Leave empty to keep current"
                />
              </div>

              {updateHolding.isError ? (
                <div className="rounded-xl bg-rose-500/10 border border-rose-500/20 px-4 py-3 text-sm font-medium text-rose-400">
                  {(updateHolding.error as Error).message}
                </div>
              ) : null}

              <div className="flex gap-3 pt-2">
                <button
                  className="flex-1 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-amber-500/25 transition-all hover:shadow-amber-500/40 disabled:opacity-60"
                  disabled={updateHolding.isPending}
                  onClick={() => updateHolding.mutate()}
                >
                  {updateHolding.isPending ? 'Saving…' : 'Save Changes'}
                </button>
                <button
                  className="flex-1 rounded-xl border border-border bg-bg px-4 py-3 text-sm font-semibold transition-all hover:bg-surface"
                  onClick={() => {
                    setIsEditOpen(false)
                    setEditingAsset(null)
                    setQuantity('')
                    setPurchasePrice('')
                    setCurrentPrice('')
                  }}
                  disabled={updateHolding.isPending}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
