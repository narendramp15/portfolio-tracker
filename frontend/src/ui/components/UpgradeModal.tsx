import { useEffect, useRef, useState } from 'react'
import { X, Zap, Check } from 'lucide-react'

import { api } from '../../lib/api'
import { useSubscription } from '../../hooks/useSubscription'

type Props = {
    open: boolean
    onClose: () => void
    /** Optional context message shown above feature list (e.g. "You've used all 3 exports") */
    reason?: string
}

declare global {
    interface Window {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        Razorpay: any
    }
}

const PRO_FEATURES = [
    'Unlimited CSV exports (transactions + tax reports)',
    'Connect up to 5 brokers simultaneously',
    'Hourly auto-sync for connected brokers',
    'Priority support',
]

export function UpgradeModal({ open, onClose, reason }: Props) {
    const { razorpayKeyId, invalidate } = useSubscription()
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)
    const scriptLoaded = useRef(false)

    // Lazy-load the Razorpay checkout script
    useEffect(() => {
        if (scriptLoaded.current || !open) return
        const script = document.createElement('script')
        script.src = 'https://checkout.razorpay.com/v1/checkout.js'
        script.async = true
        script.onload = () => { scriptLoaded.current = true }
        document.body.appendChild(script)
    }, [open])

    if (!open) return null

    async function handleUpgrade() {
        if (!razorpayKeyId) {
            setError('Payment gateway is not configured yet. Please contact support.')
            return
        }
        setLoading(true)
        setError(null)
        try {
            const { data: order } = await api.post('/billing/create-order')
            const options = {
                key: order.razorpay_key_id,
                amount: order.amount,
                currency: order.currency,
                name: 'QuantLeap Financial',
                description: 'Pro Plan — ₹199/month',
                order_id: order.order_id,
                prefill: {
                    email: order.user_email,
                    name: order.user_name,
                },
                theme: { color: '#6366f1' },
                handler: async (response: { razorpay_payment_id: string; razorpay_order_id: string; razorpay_signature: string }) => {
                    try {
                        await api.post('/billing/verify-payment', null, {
                            params: {
                                payment_id: response.razorpay_payment_id,
                                order_id: response.razorpay_order_id,
                                signature: response.razorpay_signature,
                            },
                        })
                        invalidate()
                        setSuccess(true)
                    } catch {
                        setError('Payment verification failed. Please contact support with your payment ID.')
                    } finally {
                        setLoading(false)
                    }
                },
                modal: {
                    ondismiss: () => setLoading(false),
                },
            }
            if (!window.Razorpay) {
                setError('Payment script failed to load. Please refresh and try again.')
                setLoading(false)
                return
            }
            const rzp = new window.Razorpay(options)
            rzp.open()
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to start payment'
            setError(msg)
            setLoading(false)
        }
    }

    if (success) {
        return (
            <Overlay onClose={onClose}>
                <div className="text-center py-6 space-y-4">
                    <div className="mx-auto w-14 h-14 rounded-full bg-green-500/20 flex items-center justify-center">
                        <Check className="w-7 h-7 text-green-400" />
                    </div>
                    <h2 className="text-xl font-bold">You're now on Pro! 🎉</h2>
                    <p className="text-sm text-muted">All Pro features are unlocked. Enjoy unlimited exports and more.</p>
                    <button
                        onClick={onClose}
                        className="mt-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
                    >
                        Continue
                    </button>
                </div>
            </Overlay>
        )
    }

    return (
        <Overlay onClose={onClose}>
            {/* Header */}
            <div className="flex items-start justify-between gap-3 mb-5">
                <div className="flex items-center gap-2">
                    <div className="rounded-lg bg-indigo-500/20 p-2">
                        <Zap className="w-5 h-5 text-indigo-400" />
                    </div>
                    <h2 className="text-lg font-bold">Upgrade to Pro</h2>
                </div>
                <button onClick={onClose} className="text-muted hover:text-text transition-colors">
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Reason banner */}
            {reason && (
                <div className="mb-4 rounded-lg bg-amber-500/10 border border-amber-500/30 px-4 py-3 text-sm text-amber-400">
                    {reason}
                </div>
            )}

            {/* Price */}
            <div className="mb-5 rounded-xl bg-gradient-to-br from-indigo-600/20 via-purple-600/10 to-transparent border border-indigo-500/30 p-4 text-center">
                <div className="text-3xl font-extrabold">₹199<span className="text-base font-normal text-muted">/month</span></div>
                <p className="text-xs text-muted mt-1">Cancel anytime. No hidden fees.</p>
            </div>

            {/* Feature list */}
            <ul className="space-y-2.5 mb-6">
                {PRO_FEATURES.map((f) => (
                    <li key={f} className="flex items-center gap-3 text-sm">
                        <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
                        <span>{f}</span>
                    </li>
                ))}
            </ul>

            {/* Error */}
            {error && (
                <p className="mb-3 rounded-lg bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-red-400">
                    {error}
                </p>
            )}

            {/* CTA Button */}
            <button
                disabled={loading}
                onClick={handleUpgrade}
                className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 py-3 text-sm font-bold text-white hover:from-indigo-500 hover:to-purple-500 transition-all disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/25"
            >
                {loading ? 'Processing…' : 'Upgrade Now — ₹199/month'}
            </button>

            <p className="mt-3 text-center text-xs text-muted">Powered by Razorpay. Secure payment.</p>
        </Overlay>
    )
}

function Overlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
            <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl">
                {children}
            </div>
        </div>
    )
}
