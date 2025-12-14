import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Search } from 'lucide-react'

import { api } from '../../lib/api'
import { formatCurrencyINR } from '../../lib/format'
import { type Portfolio } from '../../types/domain'
import { useAppStore } from '../../store/appStore'
import { Card } from '../components/Card'

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
      selectedPortfolioId === null ? portfolios : portfolios.filter((p) => p.id === selectedPortfolioId)

    return filteredPortfolios.flatMap((p) =>
      (p.assets ?? []).map((a) => {
        const qty = Number(a.quantity)
        const ltp = Number(a.current_price)
        const avg = Number(a.purchase_price)
        return {
          ...a,
          quantity: qty,
          current_price: ltp,
          purchase_price: avg,
          portfolioName: p.name,
          marketValue: qty * ltp,
        }
      }),
    )
  }, [portfolios])

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
      const ltp = Number(currentPrice || purchasePrice)
      if (!symbol.trim()) throw new Error('Symbol is required')
      if (!name.trim()) throw new Error('Name is required')
      if (!Number.isFinite(qty) || qty <= 0) throw new Error('Quantity must be > 0')
      if (!Number.isFinite(avg) || avg <= 0) throw new Error('Purchase price must be > 0')
      if (!Number.isFinite(ltp) || ltp <= 0) throw new Error('Current price must be > 0')

      await api.post(`/portfolio/${effectivePortfolioId}/assets`, {
        symbol: symbol.trim().toUpperCase(),
        name: name.trim(),
        quantity: qty,
        purchase_price: avg,
        current_price: ltp,
      })
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

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-sm text-muted">Portfolio</div>
          <h1 className="text-2xl font-semibold tracking-tight">Holdings</h1>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <select
            className="rounded-xl border border-border bg-bg px-3 py-2 text-sm"
            value={selectedPortfolioId ?? ''}
            onChange={(e) => setSelectedPortfolioId(e.target.value ? Number(e.target.value) : null)}
            title="Filter holdings by portfolio"
          >
            <option value="">All portfolios</option>
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <div className="relative w-full sm:w-[280px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              className="w-full rounded-xl border border-border bg-bg px-9 py-2 text-sm outline-none ring-primary focus:ring-2"
              placeholder="Search holdings..."
              type="search"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsCreateOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-bg px-4 py-2 text-sm font-semibold hover:bg-surface"
            >
              <Plus className="h-4 w-4" />
              Create portfolio
            </button>
            <button
              type="button"
              onClick={() => setIsAddOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-fg shadow-soft disabled:opacity-60"
              disabled={portfolios.length === 0}
              title={portfolios.length === 0 ? 'Create a portfolio first' : 'Add a holding manually'}
            >
              <Plus className="h-4 w-4" />
              Add holding
            </button>
          </div>
        </div>
      </div>

      {query.isLoading ? (
        <div className="h-[240px] animate-pulse rounded-xl border border-border bg-surface" />
      ) : query.isError ? (
        <Card>
          <div className="text-sm text-danger">Failed to load holdings.</div>
        </Card>
      ) : holdings.length === 0 ? (
        <Card>
          <div className="text-sm font-semibold">No holdings yet</div>
          <div className="mt-1 text-sm text-muted">
            Create a portfolio, add holdings manually, or go to Brokers and sync Zerodha holdings.
          </div>
        </Card>
      ) : (
        <Card className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] border-collapse">
              <thead className="sticky top-0 bg-surface">
                <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wide text-muted">
                  <th className="px-4 py-3">Symbol</th>
                  <th className="px-4 py-3">Qty</th>
                  <th className="px-4 py-3">Avg Cost</th>
                  <th className="px-4 py-3">LTP</th>
                  <th className="px-4 py-3">Market Value</th>
                  <th className="px-4 py-3">Portfolio</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => (
                  <tr key={`${h.portfolio_id}-${h.id}`} className="border-b border-border hover:bg-bg">
                    <td className="px-4 py-3">
                      <div className="font-semibold">{h.symbol}</div>
                      <div className="text-xs text-muted">{h.name}</div>
                    </td>
                    <td className="px-4 py-3 text-sm">{Number(h.quantity).toFixed(2)}</td>
                    <td className="px-4 py-3 text-sm">{formatCurrencyINR(h.purchase_price)}</td>
                    <td className="px-4 py-3 text-sm">{formatCurrencyINR(h.current_price)}</td>
                    <td className="px-4 py-3 text-sm font-semibold">{formatCurrencyINR(h.marketValue)}</td>
                    <td className="px-4 py-3 text-sm text-muted">{h.portfolioName}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {(isCreateOpen || isAddOpen) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-surface p-5 shadow-softLg">
            {isCreateOpen ? (
              <>
                <div className="text-lg font-semibold">Create portfolio</div>
                <div className="mt-1 text-sm text-muted">Portfolios are required for holdings and broker sync.</div>

                <div className="mt-4 space-y-3">
                  <div>
                    <label className="text-sm font-medium">Name</label>
                    <input
                      className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm"
                      value={createName}
                      onChange={(e) => setCreateName(e.target.value)}
                      placeholder="e.g., Long-term"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Description (optional)</label>
                    <textarea
                      className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm"
                      value={createDesc}
                      onChange={(e) => setCreateDesc(e.target.value)}
                      rows={3}
                    />
                  </div>

                  {createPortfolio.isError ? (
                    <div className="rounded-xl bg-danger/10 px-3 py-2 text-sm text-danger">
                      {(createPortfolio.error as Error).message}
                    </div>
                  ) : null}

                  <div className="flex gap-2 pt-1">
                    <button
                      className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-fg disabled:opacity-60"
                      disabled={createPortfolio.isPending}
                      onClick={() => createPortfolio.mutate()}
                    >
                      {createPortfolio.isPending ? 'Creating…' : 'Create'}
                    </button>
                    <button
                      className="flex-1 rounded-xl border border-border bg-bg px-4 py-2 text-sm font-semibold"
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
                <div className="text-lg font-semibold">Add holding</div>
                <div className="mt-1 text-sm text-muted">Manually add an asset to a portfolio.</div>

                <div className="mt-4 space-y-3">
                  <div>
                    <label className="text-sm font-medium">Portfolio</label>
                    <select
                      className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm"
                      value={addPortfolioId || selectedPortfolioId || ''}
                      onChange={(e) => setAddPortfolioId(e.target.value ? Number(e.target.value) : '')}
                    >
                      <option value="">Select portfolio</option>
                      {portfolios.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div>
                      <label className="text-sm font-medium">Symbol</label>
                      <input
                        className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm"
                        value={symbol}
                        onChange={(e) => setSymbol(e.target.value)}
                        placeholder="e.g., INFY"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Name</label>
                      <input
                        className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="e.g., Infosys Ltd"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Quantity</label>
                      <input
                        className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm"
                        value={quantity}
                        onChange={(e) => setQuantity(e.target.value)}
                        inputMode="decimal"
                        placeholder="e.g., 10"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Avg cost</label>
                      <input
                        className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm"
                        value={purchasePrice}
                        onChange={(e) => setPurchasePrice(e.target.value)}
                        inputMode="decimal"
                        placeholder="e.g., 1450"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="text-sm font-medium">Current price</label>
                      <input
                        className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm"
                        value={currentPrice}
                        onChange={(e) => setCurrentPrice(e.target.value)}
                        inputMode="decimal"
                        placeholder="Optional (defaults to avg cost)"
                      />
                    </div>
                  </div>

                  {addHolding.isError ? (
                    <div className="rounded-xl bg-danger/10 px-3 py-2 text-sm text-danger">
                      {(addHolding.error as Error).message}
                    </div>
                  ) : null}

                  <div className="flex gap-2 pt-1">
                    <button
                      className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-fg disabled:opacity-60"
                      disabled={addHolding.isPending}
                      onClick={() => addHolding.mutate()}
                    >
                      {addHolding.isPending ? 'Adding…' : 'Add holding'}
                    </button>
                    <button
                      className="flex-1 rounded-xl border border-border bg-bg px-4 py-2 text-sm font-semibold"
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
    </div>
  )
}
