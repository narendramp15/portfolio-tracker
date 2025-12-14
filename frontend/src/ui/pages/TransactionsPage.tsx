import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Filter, Search } from 'lucide-react'

import { api } from '../../lib/api'
import { formatCurrencyINR } from '../../lib/format'
import { type TransactionRow } from '../../types/domain'
import { Card } from '../components/Card'

async function fetchTransactions() {
  const { data } = await api.get<TransactionRow[]>('/transactions/')
  return data
}

export function TransactionsPage() {
  const query = useQuery({ queryKey: ['transactions'], queryFn: fetchTransactions })
  const [type, setType] = useState<string>('all')
  const [q, setQ] = useState('')

  const rows = useMemo(() => {
    const list = query.data ?? []
    return list
      .filter((r) => (type === 'all' ? true : r.transaction_type?.toLowerCase() === type))
      .filter((r) => {
        if (!q.trim()) return true
        const needle = q.trim().toLowerCase()
        return (
          r.asset_name?.toLowerCase().includes(needle) ||
          r.asset_symbol?.toLowerCase().includes(needle) ||
          r.portfolio_name?.toLowerCase().includes(needle)
        )
      })
  }, [query.data, type, q])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-sm text-muted">Activity</div>
          <h1 className="text-2xl font-semibold tracking-tight">Transactions</h1>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="relative w-full sm:w-[280px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              className="w-full rounded-xl border border-border bg-bg px-9 py-2 text-sm outline-none ring-primary focus:ring-2"
              placeholder="Search…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted" />
            <select
              className="rounded-xl border border-border bg-bg px-3 py-2 text-sm"
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="all">All</option>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </div>
        </div>
      </div>

      {query.isLoading ? (
        <div className="h-[240px] animate-pulse rounded-xl border border-border bg-surface" />
      ) : query.isError ? (
        <Card>
          <div className="text-sm text-danger">Failed to load transactions.</div>
        </Card>
      ) : rows.length === 0 ? (
        <Card>
          <div className="text-sm font-semibold">No transactions yet</div>
          <div className="mt-1 text-sm text-muted">Add a transaction or import a CSV (coming soon).</div>
        </Card>
      ) : (
        <Card className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] border-collapse">
              <thead className="bg-surface">
                <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wide text-muted">
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Asset</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Qty</th>
                  <th className="px-4 py-3">Price</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">Portfolio</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((t) => (
                  <tr key={t.id} className="border-b border-border hover:bg-bg">
                    <td className="px-4 py-3 text-sm text-muted">
                      {new Date(t.transaction_date).toLocaleDateString('en-IN')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold">{t.asset_symbol}</div>
                      <div className="text-xs text-muted">{t.asset_name}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={
                          'inline-flex rounded-full px-3 py-1 text-xs font-semibold ' +
                          (t.transaction_type?.toLowerCase() === 'buy'
                            ? 'bg-success/15 text-success'
                            : 'bg-danger/15 text-danger')
                        }
                      >
                        {t.transaction_type?.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">{t.quantity.toFixed(2)}</td>
                    <td className="px-4 py-3 text-sm">{formatCurrencyINR(t.price_per_unit)}</td>
                    <td className="px-4 py-3 text-sm font-semibold">
                      {formatCurrencyINR(t.quantity * t.price_per_unit)}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted">{t.portfolio_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}

