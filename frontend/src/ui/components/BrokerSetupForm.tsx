import { useState, type FormEvent } from 'react'
import { Loader2, Plus, X } from 'lucide-react'

import { api } from '../../lib/api'
import { Card } from './Card'

type BrokerType = 'zerodha' | 'angel' | 'fivepaisa'

interface BrokerSetupFormProps {
    brokerType: BrokerType
    brokerName: string
    onSuccess?: () => void
}

const brokerIcons: Record<BrokerType, string> = {
    zerodha: '📊',
    angel: '💼',
    fivepaisa: '💰',
}

const brokerColors: Record<BrokerType, string> = {
    zerodha: 'from-purple-600 to-purple-700',
    angel: 'from-pink-600 to-pink-700',
    fivepaisa: 'from-cyan-600 to-cyan-700',
}

export function BrokerSetupForm({ brokerType, brokerName, onSuccess }: BrokerSetupFormProps) {
    const [isOpen, setIsOpen] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [apiKey, setApiKey] = useState('')
    const [apiSecret, setApiSecret] = useState('')

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError(null)
        setIsLoading(true)

        try {
            const response = await api.post(`/broker/${brokerType}/setup`, undefined, {
                params: {
                    api_key: apiKey,
                    api_secret: apiSecret,
                },
            })

            if (response.data.success) {
                const loginUrl = response.data.login_url as string | undefined

                setApiKey('')
                setApiSecret('')
                setIsOpen(false)
                onSuccess?.()

                if (brokerType === 'zerodha' && loginUrl) {
                    window.location.href = loginUrl
                }
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to setup broker')
        } finally {
            setIsLoading(false)
        }
    }

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className={`inline-flex items-center gap-2 rounded-lg bg-gradient-to-r ${brokerColors[brokerType]} px-4 py-2 text-sm font-semibold text-white hover:shadow-lg transition-all`}
            >
                <Plus className="h-4 w-4" />
                Connect
            </button>
        )
    }

    return (
        <Card className="fixed inset-0 m-auto h-fit max-w-md">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <span className="text-2xl">{brokerIcons[brokerType]}</span>
                    <div>
                        <h3 className="font-semibold text-text">{brokerName}</h3>
                        <p className="text-xs text-muted">Enter your API credentials</p>
                    </div>
                </div>
                <button
                    onClick={() => setIsOpen(false)}
                    className="rounded-lg hover:bg-surface p-1 text-muted hover:text-text transition"
                >
                    <X className="h-5 w-5" />
                </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
                <div>
                    <label className="block text-xs font-semibold text-muted mb-1">API Key</label>
                    <input
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder="Enter your API key"
                        className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text placeholder-muted focus:border-primary focus:outline-none"
                        required
                        disabled={isLoading}
                    />
                </div>

                <div>
                    <label className="block text-xs font-semibold text-muted mb-1">API Secret</label>
                    <input
                        type="password"
                        value={apiSecret}
                        onChange={(e) => setApiSecret(e.target.value)}
                        placeholder="Enter your API secret"
                        className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text placeholder-muted focus:border-primary focus:outline-none"
                        required
                        disabled={isLoading}
                    />
                </div>

                {error && <div className="rounded-lg bg-danger/15 px-3 py-2 text-xs text-danger">{error}</div>}

                <div className="flex gap-2 pt-2">
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="flex-1 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50 transition flex items-center justify-center gap-2"
                    >
                        {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                        {isLoading ? 'Connecting...' : 'Connect'}
                    </button>
                    <button
                        type="button"
                        onClick={() => setIsOpen(false)}
                        className="px-3 py-2 rounded-lg border border-border hover:bg-surface transition text-sm font-semibold"
                        disabled={isLoading}
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </Card>
    )
}
