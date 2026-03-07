import { useState } from 'react'
import { Crown, Zap, CheckCircle, XCircle, RefreshCw, AlertTriangle } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { Card } from '../components/Card'
import { UpgradeModal } from '../components/UpgradeModal'
import { useSubscription } from '../../hooks/useSubscription'
import { api } from '../../lib/api'

const PLAN_DETAILS = {
    free: {
        label: 'Free',
        color: 'text-muted',
        icon: <Zap className="w-5 h-5 text-muted" />,
        description: 'Get started tracking your portfolio',
        features: [
            '2 broker connections',
            '3 CSV exports per month',
            'Daily auto-sync',
            'Tax reports (STCG/LTCG)',
            'Technical analysis (RSI, MACD)',
        ],
    },
    pro: {
        label: 'Pro',
        color: 'text-indigo-400',
        icon: <Crown className="w-5 h-5 text-indigo-400" />,
        description: 'For serious investors — ₹199/month',
        features: [
            '5 broker connections',
            'Unlimited CSV exports',
            'Hourly auto-sync',
            'All Free features',
            'Priority support',
        ],
    },
    teams: {
        label: 'Teams',
        color: 'text-purple-400',
        icon: <Crown className="w-5 h-5 text-purple-400" />,
        description: 'For family offices and advisors — ₹999/month',
        features: [
            'Unlimited brokers',
            'Unlimited exports',
            'Multi-user access',
            'White-label reports',
            'API access',
        ],
    },
}

export function BillingPage() {
    const { subscription, tier, isPro, usedExports, maxExports, isLoading, invalidate } = useSubscription()
    const [showUpgrade, setShowUpgrade] = useState(false)
    const queryClient = useQueryClient()

    const cancelMutation = useMutation({
        mutationFn: async () => {
            const { data } = await api.post('/billing/cancel')
            return data
        },
        onSuccess: () => {
            invalidate()
            queryClient.invalidateQueries({ queryKey: ['subscription'] })
        },
    })

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <RefreshCw className="w-6 h-6 animate-spin text-muted" />
            </div>
        )
    }

    const plan = PLAN_DETAILS[tier] ?? PLAN_DETAILS.free
    const isCancelled = subscription?.status === 'cancelled'

    return (
        <div className="space-y-6 max-w-2xl">
            <div>
                <div className="text-sm text-muted">Account</div>
                <h1 className="text-2xl font-semibold tracking-tight">Billing & Subscription</h1>
            </div>

            {/* Current plan */}
            <Card>
                <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                        {plan.icon}
                        <div>
                            <div className="flex items-center gap-2">
                                <span className={`text-base font-bold ${plan.color}`}>{plan.label} Plan</span>
                                {isCancelled && (
                                    <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-400 border border-amber-500/30">
                                        Cancels at period end
                                    </span>
                                )}
                                {!isCancelled && isPro && (
                                    <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-xs text-green-400 border border-green-500/30">
                                        Active
                                    </span>
                                )}
                            </div>
                            <div className="text-sm text-muted mt-0.5">{plan.description}</div>
                            {subscription?.expires_at && (
                                <div className="text-xs text-muted mt-1">
                                    {isCancelled ? 'Access until' : 'Renews'}: {new Date(subscription.expires_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                                </div>
                            )}
                        </div>
                    </div>

                    {!isPro ? (
                        <button
                            onClick={() => setShowUpgrade(true)}
                            className="rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-2 text-sm font-semibold text-white hover:from-indigo-500 hover:to-purple-500 transition-all shadow-lg shadow-indigo-500/20 whitespace-nowrap"
                        >
                            Upgrade to Pro
                        </button>
                    ) : (
                        !isCancelled && (
                            <button
                                onClick={() => {
                                    if (confirm("Are you sure you want to cancel? You'll keep Pro access until the end of your billing period.")) {
                                        cancelMutation.mutate()
                                    }
                                }}
                                disabled={cancelMutation.isPending}
                                className="rounded-xl border border-border px-4 py-2 text-sm text-muted hover:text-text hover:border-red-500/50 transition-all"
                            >
                                {cancelMutation.isPending ? 'Cancelling…' : 'Cancel Plan'}
                            </button>
                        )
                    )}
                </div>

                {/* Usage meters */}
                <div className="mt-4 space-y-3 border-t border-border pt-4">
                    {/* Export usage */}
                    <div>
                        <div className="flex items-center justify-between text-xs text-muted mb-1">
                            <span>CSV Exports this month</span>
                            <span>
                                {usedExports} / {maxExports === null ? '∞' : maxExports}
                            </span>
                        </div>
                        {!isPro && maxExports !== null && (
                            <div className="h-1.5 rounded-full bg-border overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all ${usedExports >= maxExports ? 'bg-red-500' : 'bg-indigo-500'
                                        }`}
                                    style={{ width: `${Math.min(100, (usedExports / maxExports) * 100)}%` }}
                                />
                            </div>
                        )}
                    </div>

                    {/* Broker connections */}
                    <div className="flex items-center justify-between text-xs text-muted">
                        <span>Broker connections allowed</span>
                        <span className="font-medium text-text">
                            {subscription?.limits.max_brokers === null ? 'Unlimited' : `Up to ${subscription?.limits.max_brokers}`}
                        </span>
                    </div>

                    {/* Auto-sync */}
                    <div className="flex items-center justify-between text-xs text-muted">
                        <span>Auto-sync frequency</span>
                        <span className="font-medium text-text capitalize">{subscription?.limits.auto_sync ?? 'daily'}</span>
                    </div>
                </div>
            </Card >

            {/* Plan comparison */}
            < div >
                <h2 className="text-sm font-semibold text-muted mb-3 uppercase tracking-wide">Plans</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {(['free', 'pro'] as const).map((p) => {
                        const pd = PLAN_DETAILS[p]
                        const isCurrentPlan = tier === p
                        return (
                            <Card key={p} className={isCurrentPlan ? 'ring-1 ring-indigo-500/50' : ''}>
                                <div className="flex items-center gap-2 mb-3">
                                    {pd.icon}
                                    <span className={`font-bold ${pd.color}`}>{pd.label}</span>
                                    {isCurrentPlan && (
                                        <span className="ml-auto rounded-full bg-indigo-500/10 px-2 py-0.5 text-xs text-indigo-400 border border-indigo-500/30">
                                            Current
                                        </span>
                                    )}
                                </div>
                                <ul className="space-y-2">
                                    {pd.features.map((f) => (
                                        <li key={f} className="flex items-center gap-2 text-xs text-muted">
                                            <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
                                            {f}
                                        </li>
                                    ))}
                                </ul>
                                {p === 'pro' && !isPro && (
                                    <button
                                        onClick={() => setShowUpgrade(true)}
                                        className="mt-4 w-full rounded-lg bg-indigo-600 py-2 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors"
                                    >
                                        Upgrade — ₹199/month
                                    </button>
                                )}
                            </Card>
                        )
                    })}
                </div>
            </div >

            {/* Cancel feedback */}
            {
                cancelMutation.isError && (
                    <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
                        <XCircle className="w-4 h-4" />
                        Failed to cancel subscription. Please try again or contact support.
                    </div>
                )
            }
            {
                cancelMutation.isSuccess && (
                    <div className="flex items-center gap-2 rounded-lg bg-green-500/10 border border-green-500/30 px-4 py-3 text-sm text-green-400">
                        <CheckCircle className="w-4 h-4" />
                        Subscription cancelled. Your Pro access continues until the end of the billing period.
                    </div>
                )
            }

            <UpgradeModal open={showUpgrade} onClose={() => setShowUpgrade(false)} />

            {/* Razorpay note */}
            {
                !subscription?.razorpay_key_id && (
                    <div className="flex items-start gap-2 rounded-lg bg-amber-500/10 border border-amber-500/30 px-4 py-3 text-xs text-amber-400">
                        <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        <span>Payment gateway is not yet configured. Set <code>RAZORPAY_KEY_ID</code> and <code>RAZORPAY_KEY_SECRET</code> in your <code>.env</code> to enable payments.</span>
                    </div>
                )
            }
        </div >
    )
}
