import { useState, type FormEvent } from 'react'
import { Loader2, Plus, X } from 'lucide-react'

import { api } from '../../lib/api'
import { Card } from './Card'

type BrokerType = 'zerodha' | 'angel' | 'fivepaisa' | 'groww' | 'dhan'

interface BrokerSetupFormProps {
    brokerType: BrokerType
    brokerName: string
    onSuccess?: () => void
}

const brokerIcons: Record<BrokerType, string> = {
    zerodha: '📊',
    angel: '💼',
    fivepaisa: '💰',
    groww: '🌱',
    dhan: '🔷',
}

const brokerColors: Record<BrokerType, string> = {
    zerodha: 'from-purple-600 via-purple-500 to-violet-600',
    angel: 'from-pink-600 via-pink-500 to-rose-600',
    fivepaisa: 'from-cyan-600 via-cyan-500 to-blue-600',
    groww: 'from-green-600 via-emerald-500 to-teal-600',
    dhan: 'from-blue-600 via-blue-500 to-indigo-600',
}

export function BrokerSetupForm({ brokerType, brokerName, onSuccess }: BrokerSetupFormProps) {
    const [isOpen, setIsOpen] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [apiKey, setApiKey] = useState('')
    const [apiSecret, setApiSecret] = useState('')
    // Additional 5Paisa fields
    const [appName, setAppName] = useState('')
    const [appSource, setAppSource] = useState('')
    const [userId5p, setUserId5p] = useState('')
    const [password5p, setPassword5p] = useState('')
    const [consentGiven, setConsentGiven] = useState(false)

    const isFivePaisa = brokerType === 'fivepaisa'
    const isDhan = brokerType === 'dhan'

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError(null)
        setIsLoading(true)

        try {
            // Build params based on broker type
            const params: Record<string, string> = isFivePaisa
                ? {
                    user_key: apiKey,
                    encryption_key: apiSecret,
                    app_name: appName,
                    app_source: appSource,
                    user_id_5p: userId5p,
                    password: password5p,
                    consent_given: consentGiven.toString(),
                }
                : isDhan
                    ? {
                        client_id: apiKey,
                        access_token: apiSecret,
                        consent_given: consentGiven.toString(),
                    }
                    : {
                        api_key: apiKey,
                        api_secret: apiSecret,
                        consent_given: consentGiven.toString(),
                    }

            const response = await api.post(`/broker/${brokerType}/setup`, undefined, { params })

            if (response.data.success) {
                const loginUrl = response.data.login_url as string | undefined

                // Reset all fields
                setApiKey('')
                setApiSecret('')
                setAppName('')
                setAppSource('')
                setUserId5p('')
                setPassword5p('')
                setConsentGiven(false)
                setIsOpen(false)
                onSuccess?.()

                // Redirect for OAuth login
                // Dhan is authorized immediately — no OAuth redirect needed
                if (loginUrl && !isDhan) {
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
                className={`inline-flex items-center gap-2 rounded-xl bg-gradient-to-r ${brokerColors[brokerType]} px-5 py-2.5 text-sm font-bold text-white hover:shadow-xl hover:shadow-purple-500/20 transition-all duration-300 hover:scale-105 active:scale-95`}
            >
                <Plus className="h-4 w-4" />
                Connect
            </button>
        )
    }

    return (
        <Card className="fixed inset-0 m-auto h-fit max-w-md z-50 overflow-y-auto max-h-[90vh]">
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
                    <label className="block text-xs font-semibold text-muted mb-1">
                        {isFivePaisa ? 'User Key (Vendor Key)' : isDhan ? 'Client ID' : 'API Key'}
                    </label>
                    <input
                        type={isDhan ? 'text' : 'password'}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={isFivePaisa ? 'Enter your User Key' : isDhan ? 'Enter your Dhan Client ID' : 'Enter your API key'}
                        className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text placeholder-muted focus:border-primary focus:outline-none"
                        required
                        disabled={isLoading}
                    />
                </div>

                <div>
                    <label className="block text-xs font-semibold text-muted mb-1">
                        {isFivePaisa ? 'Encryption Key' : isDhan ? 'Access Token' : 'API Secret'}
                    </label>
                    <input
                        type="password"
                        value={apiSecret}
                        onChange={(e) => setApiSecret(e.target.value)}
                        placeholder={isFivePaisa ? 'Enter your Encryption Key' : isDhan ? 'Enter your Dhan Access Token' : 'Enter your API secret'}
                        className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text placeholder-muted focus:border-primary focus:outline-none"
                        required
                        disabled={isLoading}
                    />
                </div>

                {/* Additional 5Paisa fields */}
                {isFivePaisa && (
                    <>
                        <div>
                            <label className="block text-xs font-semibold text-muted mb-1">App Name</label>
                            <input
                                type="text"
                                value={appName}
                                onChange={(e) => setAppName(e.target.value)}
                                placeholder="Enter your App Name"
                                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text placeholder-muted focus:border-primary focus:outline-none"
                                required
                                disabled={isLoading}
                            />
                        </div>

                        <div>
                            <label className="block text-xs font-semibold text-muted mb-1">App Source</label>
                            <input
                                type="text"
                                value={appSource}
                                onChange={(e) => setAppSource(e.target.value)}
                                placeholder="Enter your App Source (number)"
                                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text placeholder-muted focus:border-primary focus:outline-none"
                                required
                                disabled={isLoading}
                            />
                        </div>

                        <div>
                            <label className="block text-xs font-semibold text-muted mb-1">5Paisa User ID</label>
                            <input
                                type="text"
                                value={userId5p}
                                onChange={(e) => setUserId5p(e.target.value)}
                                placeholder="Enter your 5Paisa User ID"
                                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text placeholder-muted focus:border-primary focus:outline-none"
                                required
                                disabled={isLoading}
                            />
                        </div>

                        <div>
                            <label className="block text-xs font-semibold text-muted mb-1">5Paisa Password</label>
                            <input
                                type="password"
                                value={password5p}
                                onChange={(e) => setPassword5p(e.target.value)}
                                placeholder="Enter your 5Paisa Password"
                                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text placeholder-muted focus:border-primary focus:outline-none"
                                required
                                disabled={isLoading}
                            />
                        </div>

                        <p className="text-xs text-muted bg-surface/50 p-2 rounded-lg">
                            💡 You can find these credentials in your 5Paisa Developer Console under API Keys section.
                        </p>
                    </>
                )}

                {error && <div className="rounded-lg bg-danger/15 px-3 py-2 text-xs text-danger">{error}</div>}

                <div className="flex items-start gap-2">
                    <input
                        type="checkbox"
                        id="consent"
                        checked={consentGiven}
                        onChange={(e) => setConsentGiven(e.target.checked)}
                        className="mt-0.5"
                        required
                    />
                    <label htmlFor="consent" className="text-xs text-muted">
                        I consent to the collection and processing of my financial data from {brokerName} for portfolio tracking purposes. I understand my data will be encrypted and used only as described in the{' '}
                        <a href="/docs/terms-and-conditions.html" target="_blank" rel="noopener noreferrer" className="text-primary underline">
                            Terms and Conditions
                        </a>
                        . I can withdraw this consent at any time.
                    </label>
                </div>

                <div className="flex gap-2 pt-2">
                    <button
                        type="submit"
                        disabled={isLoading || !consentGiven}
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
