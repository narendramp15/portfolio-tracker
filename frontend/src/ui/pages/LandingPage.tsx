import { useNavigate } from 'react-router-dom'
import { BarChart3, TrendingUp, Shield, Zap, PieChart, LineChart, Users, ArrowRight, CheckCircle } from 'lucide-react'

export function LandingPage() {
    const navigate = useNavigate()

    return (
        <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
            {/* Navigation */}
            <nav className="border-b border-border bg-white/80 backdrop-blur-sm sticky top-0 z-50">
                <div className="container mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <BarChart3 className="h-8 w-8 text-indigo-600" />
                        <span className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            QuantLeap
                        </span>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => navigate('/login')}
                            className="px-4 py-2 text-sm font-medium text-text hover:text-indigo-600 transition-colors"
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

            {/* Hero Section */}
            <section className="container mx-auto px-4 py-20 text-center">
                <div className="max-w-4xl mx-auto">
                    <div className="inline-block mb-4 px-4 py-2 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium">
                        🚀 Track, Analyze & Grow Your Investments
                    </div>
                    <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                        Investment Tracking Made Simple
                    </h1>
                    <p className="text-xl text-muted mb-8 max-w-2xl mx-auto">
                        Unified portfolio management across all your brokers. Real-time analytics, AI-powered insights,
                        and beautiful dashboards - all in one place.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                        <button
                            onClick={() => navigate('/register')}
                            className="px-8 py-4 text-lg font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl hover:shadow-2xl transition-all flex items-center gap-2"
                        >
                            Start Free Today <ArrowRight className="h-5 w-5" />
                        </button>
                        <button
                            onClick={() => navigate('/login')}
                            className="px-8 py-4 text-lg font-semibold text-indigo-600 bg-white border-2 border-indigo-200 rounded-xl hover:border-indigo-400 transition-all"
                        >
                            Sign In
                        </button>
                    </div>
                    <p className="text-sm text-muted mt-4">No credit card required • Free forever</p>
                </div>
            </section>

            {/* Features Grid */}
            <section className="container mx-auto px-4 py-16">
                <div className="text-center mb-12">
                    <h2 className="text-3xl md:text-4xl font-bold mb-4">Everything You Need to Manage Your Portfolio</h2>
                    <p className="text-lg text-muted max-w-2xl mx-auto">
                        Powerful features designed for serious investors who want clarity and control.
                    </p>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
                    <FeatureCard
                        icon={<PieChart className="h-8 w-8 text-indigo-600" />}
                        title="Multi-Portfolio Management"
                        description="Organize investments across multiple portfolios. Track different strategies, goals, or family accounts separately."
                    />
                    <FeatureCard
                        icon={<TrendingUp className="h-8 w-8 text-emerald-600" />}
                        title="Real-Time Analytics"
                        description="Live P&L tracking, gain/loss metrics, and performance charts updated in real-time across all holdings."
                    />
                    <FeatureCard
                        icon={<Zap className="h-8 w-8 text-purple-600" />}
                        title="Broker Integration"
                        description="Connect Zerodha, Angel One, and 5Paisa. Import holdings automatically with secure OAuth2 authentication."
                    />
                    <FeatureCard
                        icon={<LineChart className="h-8 w-8 text-blue-600" />}
                        title="Technical Analysis"
                        description="AI-powered technical indicators, RSI, MACD, moving averages, and actionable trading signals."
                    />
                    <FeatureCard
                        icon={<Shield className="h-8 w-8 text-red-600" />}
                        title="Bank-Grade Security"
                        description="Encrypted credentials, JWT authentication, and secure API connections. Your data stays private."
                    />
                    <FeatureCard
                        icon={<BarChart3 className="h-8 w-8 text-orange-600" />}
                        title="Beautiful Dashboards"
                        description="Interactive charts, intuitive UI, and responsive design. Track your wealth from any device."
                    />
                </div>
            </section>

            {/* Benefits Section */}
            <section className="bg-gradient-to-r from-indigo-600 to-purple-600 py-16">
                <div className="container mx-auto px-4">
                    <div className="max-w-4xl mx-auto text-center text-white">
                        <h2 className="text-3xl md:text-4xl font-bold mb-8">Why Choose QuantLeap?</h2>
                        <div className="grid md:grid-cols-2 gap-6 text-left">
                            <BenefitItem text="Unified view across all broker accounts" />
                            <BenefitItem text="Zero manual data entry - auto-sync holdings" />
                            <BenefitItem text="Track historical transactions and P&L" />
                            <BenefitItem text="AI-generated insights and recommendations" />
                            <BenefitItem text="Export reports for tax filing" />
                            <BenefitItem text="Mobile-responsive design" />
                        </div>
                    </div>
                </div>
            </section>

            {/* How It Works */}
            <section className="container mx-auto px-4 py-16">
                <div className="text-center mb-12">
                    <h2 className="text-3xl md:text-4xl font-bold mb-4">Get Started in 3 Simple Steps</h2>
                </div>
                <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-8">
                    <StepCard
                        number="1"
                        title="Create Account"
                        description="Sign up with your email in 30 seconds. No credit card required."
                    />
                    <StepCard
                        number="2"
                        title="Connect Brokers"
                        description="Link your Zerodha, Angel, or 5Paisa accounts securely via OAuth."
                    />
                    <StepCard
                        number="3"
                        title="Track & Grow"
                        description="View unified dashboard, analyze performance, and make smarter decisions."
                    />
                </div>
            </section>

            {/* CTA Section */}
            <section className="container mx-auto px-4 py-16">
                <div className="max-w-3xl mx-auto text-center bg-gradient-to-br from-indigo-100 to-purple-100 rounded-2xl p-12 border border-indigo-200">
                    <Users className="h-16 w-16 text-indigo-600 mx-auto mb-4" />
                    <h2 className="text-3xl md:text-4xl font-bold mb-4">Ready to Take Control?</h2>
                    <p className="text-lg text-muted mb-8">
                        Join thousands of investors tracking their portfolios smarter with QuantLeap.
                    </p>
                    <button
                        onClick={() => navigate('/register')}
                        className="px-10 py-4 text-lg font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl hover:shadow-2xl transition-all"
                    >
                        Start Free Now
                    </button>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-border bg-surface py-8">
                <div className="container mx-auto px-4 text-center text-sm text-muted">
                    <p>&copy; 2026 QuantLeap. Built for Indian investors. All rights reserved.</p>
                    <p className="mt-2">Powered by FastAPI & React</p>
                </div>
            </footer>
        </div>
    )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
    return (
        <div className="p-6 bg-white rounded-xl border border-border hover:shadow-lg transition-all">
            <div className="mb-4">{icon}</div>
            <h3 className="text-xl font-semibold mb-2">{title}</h3>
            <p className="text-muted">{description}</p>
        </div>
    )
}

function BenefitItem({ text }: { text: string }) {
    return (
        <div className="flex items-start gap-3">
            <CheckCircle className="h-6 w-6 flex-shrink-0 mt-0.5" />
            <span className="text-lg">{text}</span>
        </div>
    )
}

function StepCard({ number, title, description }: { number: string; title: string; description: string }) {
    return (
        <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-full flex items-center justify-center text-2xl font-bold">
                {number}
            </div>
            <h3 className="text-xl font-semibold mb-2">{title}</h3>
            <p className="text-muted">{description}</p>
        </div>
    )
}
