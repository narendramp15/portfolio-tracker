import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link2, RefreshCcw, Trash2 } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { api } from '../../lib/api'
import { Card } from '../components/Card'
import { BrokerSetupForm } from '../components/BrokerSetupForm'
import { type Portfolio } from '../../types/domain'
import { useAppStore } from '../../store/appStore'

type BrokerConfig = {
  id: number
  user_id: number
  broker_name: string
  broker_user_id: string
  is_active: boolean
  last_synced?: string | null
}

async function fetchBrokerConfigs() {
  const { data } = await api.get<BrokerConfig[]>('/broker/configs')
  return data
}

const brokers = [
  { key: 'zerodha', name: 'Zerodha', icon: '📊' },
  { key: 'angel', name: 'Angel Broking', icon: '💼' },
  { key: 'fivepaisa', name: '5Paisa', icon: '💰' },
]

export function BrokersPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { selectedPortfolioId, setSelectedPortfolioId } = useAppStore()
  const [syncBrokerName, setSyncBrokerName] = useState<string>('zerodha')

  const query = useQuery({
    queryKey: ['brokers', 'configs'],
    queryFn: fetchBrokerConfigs,
  })

  const handleDisconnect = async (id: number) => {
    try {
      await api.delete(`/broker/configs/${id}`)
      queryClient.invalidateQueries({ queryKey: ['brokers', 'configs'] })
    } catch (err) {
      console.error('Failed to disconnect broker:', err)
    }
  }

  const portfoliosQuery = useQuery({
    queryKey: ['portfolios'],
    queryFn: async () => {
      const { data } = await api.get<Portfolio[]>('/portfolio/')
      return data
    },
  })

  const availablePortfolios = portfoliosQuery.data ?? []
  const resolvedPortfolioId = useMemo(() => {
    if (selectedPortfolioId) return Number(selectedPortfolioId)
    if (availablePortfolios.length === 1) return availablePortfolios[0].id
    return null
  }, [selectedPortfolioId, availablePortfolios])

  const syncHoldings = useMutation({
    mutationFn: async (brokerName: string) => {
      if (!resolvedPortfolioId) throw new Error('Select a portfolio first')
      const { data } = await api.post(`/broker/${brokerName}/sync-holdings`, undefined, {
        params: { portfolio_id: resolvedPortfolioId },
      })
      return data
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })

  const syncTrades = useMutation({
    mutationFn: async () => {
      if (!resolvedPortfolioId) throw new Error('Select a portfolio first')
      const { data } = await api.post('/broker/zerodha/sync-transactions', undefined, {
        params: { portfolio_id: resolvedPortfolioId },
      })
      return data
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })

  const connectedBrokers = new Set(query.data?.map((c) => c.broker_name) ?? [])
  const connectedBrokerList = query.data ?? []

  useEffect(() => {
    if (!connectedBrokerList.length) return
    if (connectedBrokerList.some((c) => c.broker_name === syncBrokerName)) return
    setSyncBrokerName(connectedBrokerList[0].broker_name)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectedBrokerList.length])

  const completeZerodha = useMutation({
    mutationFn: async (requestToken: string) => {
      const { data } = await api.post('/broker/zerodha/callback', undefined, {
        params: { request_token: requestToken },
      })
      return data
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['brokers', 'configs'] })
      navigate('/app/brokers', { replace: true })
    },
  })

  useEffect(() => {
    const requestToken = searchParams.get('request_token')
    if (requestToken) {
      completeZerodha.mutate(requestToken)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm text-muted">Integrations</div>
        <h1 className="text-2xl font-semibold tracking-tight">Brokers</h1>
      </div>

      <Card>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-semibold">Sync to a portfolio</div>
            <div className="mt-1 text-sm text-muted">
              Select a broker and portfolio, then sync holdings (and trades where supported).
            </div>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <select
              className="rounded-xl border border-border bg-bg px-3 py-2 text-sm"
              value={syncBrokerName}
              onChange={(e) => setSyncBrokerName(e.target.value)}
              disabled={connectedBrokerList.length === 0}
              title="Broker to sync"
            >
              {connectedBrokerList.length === 0 ? (
                <option value="zerodha">Connect a broker first</option>
              ) : (
                connectedBrokerList.map((b) => (
                  <option key={b.id} value={b.broker_name}>
                    {b.broker_name.toUpperCase()}
                  </option>
                ))
              )}
            </select>

            <select
              className="rounded-xl border border-border bg-bg px-3 py-2 text-sm"
              value={resolvedPortfolioId ?? ''}
              onChange={(e) => setSelectedPortfolioId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="" disabled>
                {availablePortfolios.length ? 'Select portfolio' : 'No portfolios'}
              </option>
              {availablePortfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>

            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-fg shadow-soft disabled:opacity-60"
              disabled={!resolvedPortfolioId || syncHoldings.isPending}
              onClick={() => syncHoldings.mutate(syncBrokerName)}
            >
              <RefreshCcw className="h-4 w-4" />
              {syncHoldings.isPending ? 'Syncing…' : 'Sync holdings'}
            </button>

            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-bg px-4 py-2 text-sm font-semibold disabled:opacity-60"
              disabled={!resolvedPortfolioId || syncTrades.isPending || syncBrokerName !== 'zerodha'}
              onClick={() => syncTrades.mutate()}
              title={
                syncBrokerName !== 'zerodha'
                  ? 'Trades sync is currently only available for Zerodha'
                  : 'Imports recent Zerodha trades into Transactions'
              }
            >
              <RefreshCcw className="h-4 w-4" />
              {syncTrades.isPending ? 'Syncing…' : 'Sync trades'}
            </button>
          </div>
        </div>

        {availablePortfolios.length === 0 ? (
          <div className="mt-3 text-sm text-muted">
            Create a portfolio first in{' '}
            <Link className="font-semibold text-primary hover:underline" to="/app/holdings">
              Holdings
            </Link>{' '}
            (then come back here to sync).
          </div>
        ) : null}

        {(syncHoldings.isError || syncTrades.isError) && (
          <div className="mt-3 text-sm text-danger">
            {(syncHoldings.error as any)?.response?.data?.detail ??
              (syncTrades.error as any)?.response?.data?.detail ??
              (syncHoldings.error as Error)?.message ??
              (syncTrades.error as Error)?.message ??
              'Sync failed'}
          </div>
        )}

        {(syncHoldings.isSuccess || syncTrades.isSuccess) && (
          <div className="mt-3 text-sm text-success">Sync completed.</div>
        )}
      </Card>

      {completeZerodha.isError ? (
        <Card>
          <div className="text-sm text-danger">
            {(completeZerodha.error as any)?.response?.data?.detail ?? (completeZerodha.error as Error).message}
          </div>
          <div className="mt-1 text-sm text-muted">
            If Zerodha redirected back here, we need the saved config id. Re-run “Connect Zerodha” if needed.
          </div>
        </Card>
      ) : null}

      {/* Setup Section */}
      <div>
        <h2 className="text-sm font-semibold mb-3 text-muted">Connect a Broker</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {brokers.map((broker) => {
            const isConnected = connectedBrokers.has(broker.key)
            return (
              <Card key={broker.key} className={isConnected ? 'opacity-50' : ''}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{broker.icon}</span>
                    <div>
                      <div className="font-semibold text-sm">{broker.name}</div>
                      <div className="text-xs text-muted">{isConnected ? 'Connected' : 'Not connected'}</div>
                    </div>
                  </div>
                  {!isConnected && (
                    <BrokerSetupForm
                      brokerType={broker.key as any}
                      brokerName={broker.name}
                      onSuccess={() => queryClient.invalidateQueries({ queryKey: ['brokers', 'configs'] })}
                    />
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Connections Section */}
      <div>
        <h2 className="text-sm font-semibold mb-3 text-muted">Connected Brokers</h2>

        {query.isLoading ? (
          <div className="h-[220px] animate-pulse rounded-xl border border-border bg-surface" />
        ) : query.isError ? (
          <Card>
            <div className="text-sm text-danger">Failed to load broker configurations.</div>
            <div className="mt-1 text-sm text-muted">
              If you are running the SPA dev server (`:5173`), make sure the backend is running on `:8000`.
            </div>
          </Card>
        ) : (query.data?.length ?? 0) === 0 ? (
          <Card>
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-xl border border-border bg-bg p-2 text-muted">
                <Link2 className="h-4 w-4" />
              </div>
              <div>
                <div className="text-sm font-semibold">No brokers connected</div>
                <div className="mt-1 text-sm text-muted">Connect a broker above to get started.</div>
              </div>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {query.data!.map((c) => (
              <Card key={c.id}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold">{c.broker_name.toUpperCase()}</div>
                    <div className="mt-1 text-sm text-muted">
                      User ID: <span className="font-medium text-text">{c.broker_user_id || '—'}</span>
                    </div>
                    <div className="mt-1 text-xs text-muted">
                      Last synced: {c.last_synced ? new Date(c.last_synced).toLocaleString('en-IN') : 'Never'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={
                        'inline-flex rounded-full px-3 py-1 text-xs font-semibold ' +
                        (c.is_active ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger')
                      }
                    >
                      {c.is_active ? 'Connected' : 'Disconnected'}
                    </span>
                    <button
                      onClick={() => handleDisconnect(c.id)}
                      className="rounded-lg p-2 hover:bg-danger/10 text-danger transition"
                      title="Disconnect broker"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
