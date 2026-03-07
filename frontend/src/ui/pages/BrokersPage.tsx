import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Crown, Link2, RefreshCcw, Trash2 } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { api } from '../../lib/api'
import { Card } from '../components/Card'
import { BrokerSetupForm } from '../components/BrokerSetupForm'
import { UpgradeModal } from '../components/UpgradeModal'
import { useSubscription } from '../../hooks/useSubscription'
import { type Portfolio } from '../../types/domain'
import { useAppStore } from '../../store/appStore'

type BrokerConfig = {
  id: number
  user_id: number
  broker_name: string
  broker_user_id: string
  is_active: boolean
  is_authorized: boolean
  last_synced?: string | null
}

async function fetchBrokerConfigs() {
  const { data } = await api.get<BrokerConfig[]>('/broker/configs')
  return data
}

const brokers = [
  { key: 'zerodha', name: 'Zerodha', icon: '📊', implemented: true },
  { key: 'groww', name: 'Groww', icon: '🌱', implemented: true },
  { key: 'dhan', name: 'Dhan', icon: '🔷', implemented: true },
  { key: 'angel', name: 'Angel Broking', icon: '💼', implemented: false },
  { key: 'fivepaisa', name: '5Paisa', icon: '💰', implemented: true },
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

  const syncHistoricalTrades = useMutation({
    mutationFn: async () => {
      if (!resolvedPortfolioId) throw new Error('Select a portfolio first')
      const { data } = await api.post('/broker/zerodha/sync-transactions', undefined, {
        params: { portfolio_id: resolvedPortfolioId, historical: true },
      })
      return data
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })

  const connectedBrokerList = query.data ?? []
  const { isPro, maxBrokers } = useSubscription()
  const [showUpgrade, setShowUpgrade] = useState(false)
  const atBrokerLimit = !isPro && connectedBrokerList.filter(c => c.is_active).length >= maxBrokers

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

  const completeFivepaisa = useMutation({
    mutationFn: async (requestToken: string) => {
      const { data } = await api.post('/broker/fivepaisa/callback', undefined, {
        params: { request_token: requestToken },
      })
      return data
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['brokers', 'configs'] })
      navigate('/app/brokers', { replace: true })
    },
  })

  const completeGroww = useMutation({
    mutationFn: async (code: string) => {
      const { data } = await api.post('/broker/groww/callback', undefined, {
        params: { request_token: code },
      })
      return data
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['brokers', 'configs'] })
      navigate('/app/brokers', { replace: true })
    },
  })

  useEffect(() => {
    // Check for request_token in URL (used by both Zerodha and 5Paisa)
    const requestToken = searchParams.get('request_token')

    // Groww OAuth uses ?code= param
    const growwCode = searchParams.get('code')
    if (growwCode) {
      completeGroww.mutate(growwCode)
      return
    }

    // Handle 5Paisa callback - token is a JWT (starts with eyJ)
    const fivepaisaToken = searchParams.get('RequestToken') || searchParams.get('accessToken')
    if (fivepaisaToken) {
      completeFivepaisa.mutate(fivepaisaToken)
      return
    }

    if (requestToken) {
      // 5Paisa tokens are JWTs that start with 'eyJ'
      if (requestToken.startsWith('eyJ')) {
        completeFivepaisa.mutate(requestToken)
      } else {
        // Zerodha tokens are shorter alphanumeric strings
        completeZerodha.mutate(requestToken)
      }
      return
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
                connectedBrokerList
                  .filter((b) => brokers.find((br) => br.key === b.broker_name)?.implemented)
                  .map((b) => (
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
                  : 'Imports recent Zerodha trades (last ~2 weeks) into Transactions'
              }
            >
              <RefreshCcw className="h-4 w-4" />
              {syncTrades.isPending ? 'Syncing…' : 'Sync trades'}
            </button>

            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-amber-600/40 bg-amber-500/10 px-4 py-2 text-sm font-semibold text-amber-600 hover:bg-amber-500/20 disabled:opacity-60"
              disabled={!resolvedPortfolioId || syncHistoricalTrades.isPending || syncBrokerName !== 'zerodha'}
              onClick={() => syncHistoricalTrades.mutate()}
              title={
                syncBrokerName !== 'zerodha'
                  ? 'Historical trades sync is currently only available for Zerodha'
                  : 'Imports ALL historical trades from Zerodha (potentially years of data)'
              }
            >
              <RefreshCcw className="h-4 w-4" />
              {syncHistoricalTrades.isPending ? 'Syncing…' : 'Sync all trades'}
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

        {(syncHoldings.isError || syncTrades.isError || syncHistoricalTrades.isError) && (
          <div className="mt-3 text-sm text-danger">
            {(syncHoldings.error as any)?.response?.data?.detail ??
              (syncTrades.error as any)?.response?.data?.detail ??
              (syncHistoricalTrades.error as any)?.response?.data?.detail ??
              (syncHoldings.error as Error)?.message ??
              (syncTrades.error as Error)?.message ??
              (syncHistoricalTrades.error as Error)?.message ??
              'Sync failed'}
          </div>
        )}

        {(syncHoldings.isSuccess || syncTrades.isSuccess || syncHistoricalTrades.isSuccess) && (
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
      {completeFivepaisa.isError ? (
        <Card>
          <div className="text-sm text-danger">
            {(completeFivepaisa.error as any)?.response?.data?.detail ?? (completeFivepaisa.error as Error).message}
          </div>
          <div className="mt-1 text-sm text-muted">
            If 5Paisa redirected back here, we need the saved config id. Re-run "Connect 5Paisa" if needed.
          </div>
        </Card>
      ) : null}
      {completeGroww.isError ? (
        <Card>
          <div className="text-sm text-danger">
            {(completeGroww.error as any)?.response?.data?.detail ?? (completeGroww.error as Error).message}
          </div>
          <div className="mt-1 text-sm text-muted">
            If Groww redirected back here, re-run "Connect Groww" if needed.
          </div>
        </Card>
      ) : null}
      {/* Setup Section */}
      <div>
        <h2 className="text-sm font-semibold mb-3 text-muted">Connect a Broker</h2>

        {/* Broker limit banner for free users */}
        {atBrokerLimit && (
          <div className="mb-3 flex items-center gap-3 rounded-xl bg-amber-500/10 border border-amber-500/30 px-4 py-3">
            <Crown className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <div className="flex-1 text-sm text-amber-300">
              You've reached the <strong>Free plan limit</strong> of {maxBrokers} broker connections.
            </div>
            <button
              onClick={() => setShowUpgrade(true)}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-indigo-500 transition-colors whitespace-nowrap"
            >
              Upgrade to Pro
            </button>
          </div>
        )}
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {brokers.map((broker) => {
            const config = connectedBrokerList.find(c => c.broker_name === broker.key)
            const isConnected = !!config
            const isAuthorized = config?.is_authorized ?? false

            // For non-implemented brokers, show "Coming Soon"
            if (!broker.implemented) {
              return (
                <Card key={broker.key} className="opacity-50 cursor-not-allowed pointer-events-none">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl grayscale">{broker.icon}</span>
                      <div>
                        <div className="font-semibold text-sm text-muted">{broker.name}</div>
                        <div className="text-xs text-muted">Coming soon</div>
                      </div>
                    </div>
                    <span className="rounded-full bg-muted/20 px-3 py-1 text-xs font-medium text-muted">
                      Coming Soon
                    </span>
                  </div>
                </Card>
              )
            }

            const statusText = isConnected
              ? (isAuthorized ? 'Authorized ✓' : 'Needs login')
              : 'Not connected'
            const statusColor = isConnected
              ? (isAuthorized ? 'text-green-500' : 'text-amber-500')
              : 'text-muted'
            return (
              <Card key={broker.key} className="">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{broker.icon}</span>
                    <div>
                      <div className="font-semibold text-sm">{broker.name}</div>
                      <div className={`text-xs ${statusColor}`}>{statusText}</div>
                    </div>
                  </div>
                  {!isConnected && (
                    <BrokerSetupForm
                      brokerType={broker.key as any}
                      brokerName={broker.name}
                      onSuccess={() => queryClient.invalidateQueries({ queryKey: ['brokers', 'configs'] })}
                    />
                  )}
                  {isConnected && !isAuthorized && (broker.key === 'zerodha' || broker.key === 'fivepaisa' || broker.key === 'groww') && (
                    <button
                      onClick={async () => {
                        try {
                          const { data } = await api.get<{ login_url: string }>(`/broker/${broker.key}/login-url`)
                          window.location.href = data.login_url
                        } catch (err) {
                          console.error('Failed to get login URL:', err)
                        }
                      }}
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 px-4 py-2 text-sm font-bold text-white hover:shadow-lg transition-all"
                    >
                      Login to {broker.name}
                    </button>
                  )}
                  {isConnected && isAuthorized && (broker.key === 'zerodha' || broker.key === 'fivepaisa' || broker.key === 'groww') && (
                    <button
                      onClick={async () => {
                        try {
                          const { data } = await api.get<{ login_url: string }>(`/broker/${broker.key}/login-url`)
                          window.location.href = data.login_url
                        } catch (err) {
                          console.error('Failed to get login URL:', err)
                        }
                      }}
                      className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-fg hover:shadow-lg transition-all"
                      title="Get fresh access token (especially useful if token expired)"
                    >
                      <RefreshCcw className="h-4 w-4" />
                      Reconnect
                    </button>
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
      <UpgradeModal
        open={showUpgrade}
        onClose={() => setShowUpgrade(false)}
        reason={`You've reached the Free plan limit of ${maxBrokers} broker connections. Upgrade to Pro to connect up to 5 brokers.`}
      />
    </div>
  )
}
