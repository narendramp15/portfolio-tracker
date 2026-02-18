import { useNavigate } from 'react-router-dom'
import { CheckCircle, X, Rocket, Crown, Gift } from 'lucide-react'

interface PricingFeatureProps {
    text: string
    included: boolean
    coming?: boolean
}

function PricingFeature({ text, included, coming }: PricingFeatureProps) {
    return (
        <li className="flex items-start gap-3">
            {included ? (
                <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
            ) : (
                <X className="h-5 w-5 text-slate-300 flex-shrink-0 mt-0.5" />
            )}
            <span className={`text-sm ${included ? 'text-slate-700' : 'text-slate-400'}`}>
                {text}
                {coming && <span className="ml-2 text-xs text-amber-600 font-medium">(Coming Soon)</span>}
            </span>
        </li>
    )
}

export function PricingPage() {
    const navigate = useNavigate()

    return (
        <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
            {/* Simple Header */}
            <nav className="border-b border-slate-200 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
                <div className="container mx-auto px-4 py-4 flex items-center justify-between">
                    <button
                        onClick={() => navigate('/')}
                        className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent hover:opacity-80 transition-opacity"
                    >
                        QuantLeap
                    </button>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => navigate('/login')}
                            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors"
                        >
                            Login
                        </button>
                        <button
                            onClick={() => navigate('/register')}
                            className="px-6 py-2 text-sm font-medium text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg hover:shadow-lg transition-all"
                        >
                            Get Started
                        </button>
                    </div>
                </div>
            </nav>

            {/* Pricing Section */}
            <section className="container mx-auto px-4 py-16">
                <div className="text-center mb-12">
                    <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 bg-emerald-100 border border-emerald-200 rounded-full">
                        <Gift className="h-4 w-4 text-emerald-600" />
                        <span className="text-sm font-medium text-emerald-700">Limited Time Offer</span>
                    </div>
                    <h1 className="text-4xl md:text-5xl font-bold mb-4">Simple, Transparent Pricing</h1>
                    <p className="text-xl text-slate-600 max-w-2xl mx-auto">
                        No hidden fees. No surprises. Start free and upgrade when you're ready.
                    </p>
                </div>

                <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-8">
                    {/* Free Tier */}
                    <div className="relative bg-white rounded-2xl border-2 border-indigo-500 shadow-xl shadow-indigo-500/10 p-8">
                        {/* Popular Badge */}
                        <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-sm font-semibold px-4 py-1 rounded-full">
                                Most Popular
                            </div>
                        </div>

                        <div className="text-center mb-6">
                            <div className="w-16 h-16 mx-auto mb-4 bg-indigo-100 rounded-2xl flex items-center justify-center">
                                <Rocket className="h-8 w-8 text-indigo-600" />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-900 mb-2">Free Forever</h2>
                            <div className="flex items-baseline justify-center gap-1">
                                <span className="text-5xl font-bold text-slate-900">₹0</span>
                                <span className="text-slate-500">/month</span>
                            </div>
                            <p className="text-sm text-emerald-600 font-medium mt-2">No credit card required</p>
                        </div>

                        <ul className="space-y-4 mb-8">
                            <PricingFeature text="Unlimited portfolios" included />
                            <PricingFeature text="Connect 2 brokers (Zerodha, 5Paisa)" included />
                            <PricingFeature text="Manual sync only" included />
                            <PricingFeature text="Real-time P&L tracking" included />
                            <PricingFeature text="Basic analytics (P&L, sector breakdown)" included />
                            <PricingFeature text="Technical indicators (RSI, MACD)" included />
                            <PricingFeature text="Tax reports (1 FY export/month)" included />
                            <PricingFeature text="CSV exports (3/month)" included />
                            <PricingFeature text="Historical data (90 days)" included />
                            <PricingFeature text="Community support" included />
                            <PricingFeature text="Hourly auto-sync" included={false} />
                            <PricingFeature text="Price alerts" included={false} />
                            <PricingFeature text="Advanced analytics" included={false} />
                            <PricingFeature text="Mutual fund tracking" included={false} />
                        </ul>

                        <button
                            onClick={() => navigate('/register')}
                            className="w-full py-4 text-lg font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl hover:shadow-lg hover:shadow-indigo-500/30 transition-all"
                        >
                            Get Started Free
                        </button>
                    </div>

                    {/* Pro Tier (Coming Soon) */}
                    <div className="relative bg-slate-50 rounded-2xl border border-slate-200 p-8">
                        <div className="text-center mb-6">
                            <div className="w-16 h-16 mx-auto mb-4 bg-amber-100 rounded-2xl flex items-center justify-center">
                                <Crown className="h-8 w-8 text-amber-600" />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-900 mb-2">Pro</h2>
                            <div className="flex items-baseline justify-center gap-1">
                                <span className="text-5xl font-bold text-slate-400">₹199</span>
                                <span className="text-slate-400">/month</span>
                            </div>
                            <p className="text-sm text-amber-600 font-medium mt-2">Coming Q2 2026</p>
                        </div>

                        <ul className="space-y-4 mb-8 opacity-70">
                            <PricingFeature text="Everything in Free, plus:" included />
                            <PricingFeature text="Connect 5+ brokers (Zerodha, 5Paisa, Angel, Upstox)" coming included />
                            <PricingFeature text="Hourly auto-sync" coming included />
                            <PricingFeature text="Price alerts (email + SMS)" coming included />
                            <PricingFeature text="Advanced technical indicators (Bollinger, VWAP, custom)" coming included />
                            <PricingFeature text="Unlimited tax reports & CSV exports" coming included />
                            <PricingFeature text="Portfolio rebalancing (AI-powered)" coming included />
                            <PricingFeature text="Mutual fund tracking" coming included />
                            <PricingFeature text="Historical data (3 years)" coming included />
                            <PricingFeature text="Email support (24h response)" coming included />
                        </ul>

                        <button
                            disabled
                            className="w-full py-4 text-lg font-semibold text-slate-400 bg-slate-200 rounded-xl cursor-not-allowed"
                        >
                            Coming Soon
                        </button>
                    </div>
                </div>

                {/* Early Adopter Promise */}
                <div className="max-w-2xl mx-auto mt-12 text-center">
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
                        <p className="text-amber-800 font-medium">
                            🎁 <strong>Early Adopter Promise:</strong> Sign up now and you'll get the Pro features free for 6 months
                            when they launch.
                        </p>
                    </div>
                </div>

                {/* FAQ */}
                <div className="max-w-3xl mx-auto mt-16">
                    <h2 className="text-2xl font-bold text-center mb-8">Frequently Asked Questions</h2>
                    <div className="space-y-6">
                        <div className="bg-white rounded-lg p-6 border border-slate-200">
                            <h3 className="font-semibold text-slate-900 mb-2">Can I upgrade or downgrade anytime?</h3>
                            <p className="text-sm text-slate-600">
                                Yes! Once Pro is available, you can upgrade or downgrade anytime. No questions asked.
                            </p>
                        </div>
                        <div className="bg-white rounded-lg p-6 border border-slate-200">
                            <h3 className="font-semibold text-slate-900 mb-2">Is my data safe?</h3>
                            <p className="text-sm text-slate-600">
                                Absolutely. We use bank-grade AES-256 encryption and never store your broker passwords. All connections
                                use official OAuth2 APIs.
                            </p>
                        </div>
                        <div className="bg-white rounded-lg p-6 border border-slate-200">
                            <h3 className="font-semibold text-slate-900 mb-2">What payment methods do you accept?</h3>
                            <p className="text-sm text-slate-600">
                                Once Pro launches, we'll accept all major credit/debit cards, UPI, and net banking via Razorpay.
                            </p>
                        </div>
                        <div className="bg-white rounded-lg p-6 border border-slate-200">
                            <h3 className="font-semibold text-slate-900 mb-2">Do you offer refunds?</h3>
                            <p className="text-sm text-slate-600">
                                Yes. We offer a 7-day money-back guarantee. If you're not satisfied, email us for a full refund.
                            </p>
                        </div>
                    </div>
                </div>

                {/* CTA */}
                <div className="max-w-2xl mx-auto mt-16 text-center">
                    <h2 className="text-3xl font-bold mb-4">Ready to Get Started?</h2>
                    <p className="text-lg text-slate-600 mb-6">
                        Join hundreds of investors tracking their portfolios with QuantLeap.
                    </p>
                    <button
                        onClick={() => navigate('/register')}
                        className="px-10 py-4 text-lg font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl hover:shadow-2xl transition-all"
                    >
                        Sign Up Free
                    </button>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-slate-200 bg-white py-8">
                <div className="container mx-auto px-4 text-center text-sm text-slate-500">
                    <p>
                        © 2026 QuantLeap. Made with ❤️ for Indian investors. |{' '}
                        <button onClick={() => navigate('/')} className="hover:text-indigo-600">
                            Home
                        </button>{' '}
                        |{' '}
                        <button onClick={() => navigate('/login')} className="hover:text-indigo-600">
                            Login
                        </button>
                    </p>
                </div>
            </footer>
        </div>
    )
}
