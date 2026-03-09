import { useState } from 'react'
import { CheckCircle, Zap, Crown, Lock, RefreshCw } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { Card } from '../components/Card'
import { api } from '../../lib/api'

/* ─── Types ──────────────────────────────────────────────────────────────── */
interface UsageData {
    tier: 'starter' | 'pro' | 'elite'
    tier_label: string
    credits: number
    analyses_today: number
    daily_limit: number
    circuit_breaker_hit: boolean
    allowed_types: string[]
    credits_per_analysis: Record<string, number>
}

interface PlanDef {
    id: 'starter' | 'pro' | 'elite'
    label: string
    price: string
    daily: number
    color: string
    ringColor: string
    features: string[]
    allowed: string[]
}

interface CreditPack {
    id: string
    label: string
    price: number
    credits: number
    bonus?: string
}

/* ─── Static data ────────────────────────────────────────────────────────── */
const PLANS: PlanDef[] = [
    {
        id: 'free' as any,
        label: 'Free',
        price: 'Free forever',
        daily: 5,
        color: 'text-slate-400',
        ringColor: 'ring-slate-500/40',
        features: [
            '5 lifetime analyses',
            '⚡ Quick analysis only',
            '2-minute cooldown between calls',
            'Live market data fetch',
        ],
        allowed: ['quick'],
    },
    {
        id: 'starter',
        label: 'Starter',
        price: '₹99/mo',
        daily: 10,
        color: 'text-emerald-400',
        ringColor: 'ring-emerald-500/40',
        features: [
            '10 analyses/day',
            '⚡ Quick analysis only',
            '1-minute cooldown between calls',
            'Live market data fetch',
        ],
        allowed: ['quick'],
    },
    {
        id: 'pro',
        label: 'Pro',
        price: '₹299/mo',
        daily: 30,
        color: 'text-violet-400',
        ringColor: 'ring-violet-500/40',
        features: [
            '30 analyses/day',
            '⚡ Quick + 📊 Full Report',
            'Prompt caching (90% cheaper)',
            'Priority queue',
        ],
        allowed: ['quick', 'full'],
    },
    {
        id: 'elite',
        label: 'Elite',
        price: '₹799/mo',
        daily: 50,
        color: 'text-amber-400',
        ringColor: 'ring-amber-500/40',
        features: [
            '50 analyses/day',
            '⚡ Quick + 📊 Full + 🔬 Advanced',
            'Deepest model tier',
            'All Pro features',
        ],
        allowed: ['quick', 'full', 'advanced'],
    },
]

const CREDIT_PACKS: CreditPack[] = [
    { id: 'starter_pack', label: 'Starter Pack', price: 99, credits: 10 },
    { id: 'growth_pack', label: 'Growth Pack', price: 299, credits: 40, bonus: 'Best value' },
    { id: 'power_pack', label: 'Power Pack', price: 749, credits: 120, bonus: 'Save 38%' },
]

/* ─── Component ──────────────────────────────────────────────────────────── */
const STARTER_PAYMENT_LINK = 'https://rzp.io/rzp/y3LwB3p'

export function OptionsBillingPage() {
    const queryClient = useQueryClient()
    const [upgradeMsg, setUpgradeMsg] = useState('')
    const [upgradeError, setUpgradeError] = useState('')
    const [showStarterVerify, setShowStarterVerify] = useState(false)
    const [starterPaymentId, setStarterPaymentId] = useState('')

    const { data: usage, isLoading } = useQuery<UsageData>({
        queryKey: ['options-usage'],
        queryFn: async () => {
            const { data } = await api.get('/ai/usage')
            return data
        },
        staleTime: 30_000,
    })

    const upgradeMutation = useMutation({
        mutationFn: async (targetTier: string) => {
            const { data } = await api.post('/billing/options-upgrade', { tier: targetTier })
            return data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['options-usage'] })
            setUpgradeMsg('Upgrade successful! Your tier has been updated.')
            setUpgradeError('')
        },
        onError: (e: any) => {
            setUpgradeError(e?.response?.data?.detail || 'Upgrade failed. Please try again.')
            setUpgradeMsg('')
        },
    })

    const starterActivateMutation = useMutation({
        mutationFn: async (paymentId: string) => {
            const { data } = await api.post('/billing/options-starter-activate', { payment_id: paymentId })
            return data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['options-usage'] })
            setUpgradeMsg('🎉 Starter plan activated! Your account has been upgraded.')
            setUpgradeError('')
            setShowStarterVerify(false)
            setStarterPaymentId('')
        },
        onError: (e: any) => {
            setUpgradeError(e?.response?.data?.detail || 'Verification failed. Please check your Payment ID and try again.')
            setUpgradeMsg('')
        },
    })

    const creditMutation = useMutation({
        mutationFn: async (packId: string) => {
            const { data } = await api.post('/billing/options-credits', { pack_id: packId })
            return data
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['options-usage'] })
            // Razorpay checkout if order returned
            if (data.razorpay_order_id && data.razorpay_key) {
                const options = {
                    key: data.razorpay_key,
                    amount: data.amount,
                    currency: 'INR',
                    name: 'QuantLeap Options Analyzer',
                    description: 'Credit pack purchase',
                    order_id: data.razorpay_order_id,
                    handler: () => {
                        queryClient.invalidateQueries({ queryKey: ['options-usage'] })
                        setUpgradeMsg('Credits added to your account!')
                    },
                }
                // @ts-expect-error Razorpay loaded via CDN
                const rz = new window.Razorpay(options)
                rz.open()
            } else if (data.credits_added) {
                setUpgradeMsg(`${data.credits_added} credits added!`)
            }
        },
        onError: (e: any) => {
            setUpgradeError(e?.response?.data?.detail || 'Purchase failed. Please try again.')
        },
    })

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <RefreshCw className="w-6 h-6 animate-spin text-muted" />
            </div>
        )
    }

    const currentTier = usage?.tier ?? 'starter'

    return (
        <div className="space-y-6 max-w-3xl">
            <div>
                <div className="text-sm text-muted">Options Analyzer</div>
                <h1 className="text-2xl font-semibold tracking-tight">Plans &amp; Credits</h1>
            </div>

            {/* Current usage snapshot */}
            {usage && (
                <Card>
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            {currentTier === 'elite' ? (
                                <Crown className="w-5 h-5 text-amber-400" />
                            ) : currentTier === 'pro' ? (
                                <Crown className="w-5 h-5 text-violet-400" />
                            ) : (
                                <Zap className="w-5 h-5 text-emerald-400" />
                            )}
                            <span className="font-bold">{usage.tier_label}</span>
                            <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-xs text-green-400 border border-green-500/30">
                                Active
                            </span>
                        </div>
                        <div className="text-xs text-muted">
                            {usage.analyses_today} / {usage.daily_limit} analyses today
                        </div>
                    </div>

                    {/* Daily usage bar */}
                    <div className="h-1.5 rounded-full bg-border overflow-hidden mb-4">
                        <div
                            className={`h-full rounded-full transition-all ${usage.analyses_today >= usage.daily_limit ? 'bg-red-500' : 'bg-emerald-500'}`}
                            style={{ width: `${Math.min(100, (usage.analyses_today / usage.daily_limit) * 100)}%` }}
                        />
                    </div>

                    <div className="flex flex-wrap gap-6 text-xs text-muted">
                        <div>
                            <span>Credits remaining </span>
                            <span className={`font-bold ${(usage.credits ?? 0) < 3 ? 'text-red-400' : 'text-emerald-400'}`}>
                                {usage.credits ?? 0}
                            </span>
                        </div>
                        <div>
                            <span>Allowed analysis types </span>
                            <span className="font-bold text-text">
                                {usage.allowed_types.join(', ')}
                            </span>
                        </div>
                        {usage.circuit_breaker_hit && (
                            <div className="text-amber-400 flex items-center gap-1">
                                <Lock className="w-3 h-3" />
                                Monthly cost limit reached — resets next month
                            </div>
                        )}
                    </div>
                </Card>
            )}

            {/* Plan cards */}
            <div>
                <h2 className="text-sm font-semibold text-muted mb-3 uppercase tracking-wide">Plans</h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {PLANS.map((plan) => {
                        const isCurrent = currentTier === plan.id
                        const isDowngrade = PLANS.findIndex(p => p.id === plan.id) < PLANS.findIndex(p => p.id === currentTier)
                        return (
                            <Card
                                key={plan.id}
                                className={isCurrent ? `ring-1 ${plan.ringColor}` : ''}
                            >
                                <div className="flex items-center gap-2 mb-1">
                                    {plan.id === 'elite' ? (
                                        <Crown className={`w-4 h-4 ${plan.color}`} />
                                    ) : plan.id === 'pro' ? (
                                        <Crown className={`w-4 h-4 ${plan.color}`} />
                                    ) : (
                                        <Zap className={`w-4 h-4 ${plan.color}`} />
                                    )}
                                    <span className={`font-bold ${plan.color}`}>{plan.label}</span>
                                    {isCurrent && (
                                        <span className="ml-auto rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-400 border border-emerald-500/30">
                                            Current
                                        </span>
                                    )}
                                </div>
                                <div className="text-xl font-bold mb-3">{plan.price}</div>
                                <ul className="space-y-2 mb-4">
                                    {plan.features.map((f) => (
                                        <li key={f} className="flex items-start gap-2 text-xs text-muted">
                                            <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0 mt-0.5" />
                                            {f}
                                        </li>
                                    ))}
                                </ul>
                                {!isCurrent && !isDowngrade && (
                                    plan.id === 'starter' ? (
                                        <div>
                                            <button
                                                onClick={() => {
                                                    window.open(STARTER_PAYMENT_LINK, '_blank', 'noopener,noreferrer')
                                                    setShowStarterVerify(true)
                                                }}
                                                className="w-full rounded-lg py-2 text-xs font-semibold text-white transition-colors bg-emerald-600 hover:bg-emerald-500"
                                            >
                                                Pay ₹99 — Upgrade to Starter
                                            </button>
                                            {showStarterVerify && (
                                                <div className="mt-3 space-y-2 rounded-lg bg-emerald-500/5 border border-emerald-500/20 p-3">
                                                    <p className="text-xs text-muted">After payment, paste your Payment ID from the confirmation screen or email:</p>
                                                    <input
                                                        type="text"
                                                        placeholder="pay_XXXXXXXXXXXXXXXX"
                                                        value={starterPaymentId}
                                                        onChange={(e) => setStarterPaymentId(e.target.value)}
                                                        className="w-full rounded-md bg-bg border border-border px-3 py-1.5 text-xs font-mono focus:outline-none focus:border-emerald-500/50"
                                                    />
                                                    <button
                                                        onClick={() => starterActivateMutation.mutate(starterPaymentId)}
                                                        disabled={starterActivateMutation.isPending || !starterPaymentId.startsWith('pay_')}
                                                        className="w-full rounded-md bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 py-1.5 text-xs font-semibold text-white transition-colors"
                                                    >
                                                        {starterActivateMutation.isPending ? 'Verifying…' : 'Verify & Activate'}
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <button
                                            onClick={() => upgradeMutation.mutate(plan.id)}
                                            disabled={upgradeMutation.isPending}
                                            className={`w-full rounded-lg py-2 text-xs font-semibold text-white transition-colors ${plan.id === 'elite'
                                                ? 'bg-amber-600 hover:bg-amber-500'
                                                : 'bg-violet-600 hover:bg-violet-500'
                                                }`}
                                        >
                                            {upgradeMutation.isPending ? 'Processing…' : `Upgrade to ${plan.label}`}
                                        </button>
                                    )
                                )}
                            </Card>
                        )
                    })}
                </div>
            </div>

            {/* Credit packs */}
            <div>
                <h2 className="text-sm font-semibold text-muted mb-3 uppercase tracking-wide">Buy Credits</h2>
                <p className="text-xs text-muted mb-3">
                    Credits let you run analyses beyond your daily limit. Each analysis costs 1 credit.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {CREDIT_PACKS.map((pack) => (
                        <Card key={pack.id} className="relative">
                            {pack.bonus && (
                                <span className="absolute top-3 right-3 rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-400 border border-amber-500/30">
                                    {pack.bonus}
                                </span>
                            )}
                            <div className="font-semibold mb-1">{pack.label}</div>
                            <div className="text-2xl font-bold mb-1">₹{pack.price}</div>
                            <div className="text-xs text-muted mb-4">{pack.credits} credits</div>
                            <button
                                onClick={() => creditMutation.mutate(pack.id)}
                                disabled={creditMutation.isPending}
                                className="w-full rounded-lg bg-emerald-700 hover:bg-emerald-600 py-2 text-xs font-semibold text-white transition-colors"
                            >
                                {creditMutation.isPending ? 'Processing…' : 'Buy Now'}
                            </button>
                        </Card>
                    ))}
                </div>
            </div>

            {/* Feedback */}
            {upgradeMsg && (
                <div className="flex items-center gap-2 rounded-lg bg-green-500/10 border border-green-500/30 px-4 py-3 text-sm text-green-400">
                    <CheckCircle className="w-4 h-4" />
                    {upgradeMsg}
                </div>
            )}
            {upgradeError && (
                <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
                    {upgradeError}
                </div>
            )}
        </div>
    )
}
