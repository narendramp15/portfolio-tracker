import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, TrendingUp, Shield, Zap, PieChart, LineChart, ArrowRight, CheckCircle, Play, Sparkles, IndianRupee, Lock, Github, Linkedin, Code2, ShieldCheck, KeyRound, EyeOff, Gift, Crown, Rocket, Mail, Send, MessageSquare, Menu, X } from 'lucide-react'

export function LandingPage() {
    const navigate = useNavigate()
    const [contactForm, setContactForm] = useState({ name: '', email: '', subject: '', message: '' })
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle')
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

    const scrollToSection = (id: string) => {
        const element = document.getElementById(id)
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' })
        }
        setMobileMenuOpen(false)
    }

    const handleContactSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsSubmitting(true)

        // Create mailto link with form data
        const mailtoLink = `mailto:futurestation.in@gmail.com?subject=${encodeURIComponent(`[QuantLeap] ${contactForm.subject}`)}&body=${encodeURIComponent(`Name: ${contactForm.name}\nEmail: ${contactForm.email}\n\nMessage:\n${contactForm.message}`)}`

        // Open email client
        window.location.href = mailtoLink

        // Show success message
        setTimeout(() => {
            setIsSubmitting(false)
            setSubmitStatus('success')
            setContactForm({ name: '', email: '', subject: '', message: '' })

            // Reset status after 5 seconds
            setTimeout(() => setSubmitStatus('idle'), 5000)
        }, 500)
    }

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

                    {/* Desktop Menu */}
                    <div className="hidden md:flex items-center gap-6">
                        <button onClick={() => scrollToSection('features')} className="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors">
                            Features
                        </button>
                        <button onClick={() => scrollToSection('security')} className="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors">
                            Security
                        </button>
                        <button onClick={() => scrollToSection('pricing')} className="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors">
                            Pricing
                        </button>
                        <button onClick={() => scrollToSection('about')} className="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors">
                            About
                        </button>
                        <button onClick={() => scrollToSection('contact')} className="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors">
                            Contact
                        </button>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => navigate('/login')}
                            className="hidden sm:block px-4 py-2 text-sm font-medium text-text hover:text-indigo-600 transition-colors"
                        >
                            Login
                        </button>
                        <button
                            onClick={() => navigate('/register')}
                            className="px-6 py-2 text-sm font-medium text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg hover:shadow-lg transition-all"
                        >
                            Get Started
                        </button>
                        {/* Mobile Menu Button */}
                        <button
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            className="md:hidden p-2 text-slate-600 hover:text-indigo-600 transition-colors"
                        >
                            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
                        </button>
                    </div>
                </div>

                {/* Mobile Menu Dropdown */}
                {mobileMenuOpen && (
                    <div className="md:hidden border-t border-slate-100 bg-white/95 backdrop-blur-sm">
                        <div className="container mx-auto px-4 py-4 flex flex-col gap-2">
                            <button onClick={() => scrollToSection('features')} className="px-4 py-3 text-left text-sm font-medium text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition-colors">
                                Features
                            </button>
                            <button onClick={() => scrollToSection('security')} className="px-4 py-3 text-left text-sm font-medium text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition-colors">
                                Security
                            </button>
                            <button onClick={() => scrollToSection('pricing')} className="px-4 py-3 text-left text-sm font-medium text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition-colors">
                                Pricing
                            </button>
                            <button onClick={() => scrollToSection('about')} className="px-4 py-3 text-left text-sm font-medium text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition-colors">
                                About
                            </button>
                            <button onClick={() => scrollToSection('contact')} className="px-4 py-3 text-left text-sm font-medium text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition-colors">
                                Contact
                            </button>
                            <hr className="my-2 border-slate-100" />
                            <button
                                onClick={() => { navigate('/login'); setMobileMenuOpen(false) }}
                                className="px-4 py-3 text-left text-sm font-medium text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition-colors"
                            >
                                Login
                            </button>
                        </div>
                    </div>
                )}
            </nav>

            {/* Hero Section */}
            <section className="container mx-auto px-4 pt-16 pb-24">
                <div className="max-w-6xl mx-auto">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        {/* Left: Copy */}
                        <div className="text-left">
                            {/* Built By Badge - Honest Founder Credentials */}
                            <div className="inline-flex items-center gap-3 mb-6 px-4 py-2 bg-gradient-to-r from-slate-50 to-indigo-50 border border-slate-200 rounded-full">
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-sm text-white font-bold">
                                    P
                                </div>
                                <div className="text-sm">
                                    <span className="text-slate-600">Built by </span>
                                    <span className="font-semibold text-slate-800">Priya</span>
                                    <span className="text-slate-500"> • Founder of QuantLeap</span>
                                </div>
                                <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
                                    <a href="https://github.com/priyaprasadblr" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-slate-700 transition-colors">
                                        <Github className="h-4 w-4" />
                                    </a>
                                    <a href="https://www.linkedin.com/in/priya-prasad-0299b33a9" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-blue-600 transition-colors">
                                        <Linkedin className="h-4 w-4" />
                                    </a>
                                </div>
                            </div>

                            {/* Headline */}
                            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold leading-tight mb-6">
                                <span className="text-text">Track all your investments in </span>
                                <span className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                                    one intelligent dashboard
                                </span>
                            </h1>

                            {/* Subheadline with specific benefits */}
                            <p className="text-xl text-muted mb-8 leading-relaxed">
                                Connect <span className="font-semibold text-text">Zerodha, Angel & 5Paisa</span> in seconds.
                                Get live P&L, AI-powered insights, and tax-ready reports —
                                <span className="font-semibold text-text"> all automatically synced</span>.
                            </p>

                            {/* CTAs */}
                            <div className="flex flex-col sm:flex-row gap-4 mb-6">
                                <button
                                    onClick={() => navigate('/register')}
                                    className="group px-8 py-4 text-lg font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl shadow-lg shadow-indigo-500/30 hover:shadow-xl hover:shadow-indigo-500/40 transition-all flex items-center justify-center gap-2"
                                >
                                    <Sparkles className="h-5 w-5" />
                                    Start Free — No Card Required
                                    <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
                                </button>
                                <button
                                    onClick={() => window.open('https://youtu.be/demo', '_blank')}
                                    className="px-8 py-4 text-lg font-semibold text-indigo-700 bg-indigo-50 border-2 border-indigo-100 rounded-xl hover:bg-indigo-100 hover:border-indigo-200 transition-all flex items-center justify-center gap-2"
                                >
                                    <Play className="h-5 w-5 fill-indigo-600" />
                                    Watch 2-min Demo
                                </button>
                            </div>

                            {/* Trust Signals */}
                            <div className="flex flex-wrap items-center gap-6 text-sm text-muted">
                                <div className="flex items-center gap-2">
                                    <Lock className="h-4 w-4 text-emerald-500" />
                                    <span>Bank-grade encryption</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <IndianRupee className="h-4 w-4 text-indigo-500" />
                                    <span>Made for India</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <CheckCircle className="h-4 w-4 text-emerald-500" />
                                    <span>Free forever plan</span>
                                </div>
                            </div>
                        </div>

                        {/* Right: Product Visual / Dashboard Mockup */}
                        <div className="relative">
                            {/* Glow effect */}
                            <div className="absolute -inset-4 bg-gradient-to-r from-indigo-500/20 via-purple-500/20 to-pink-500/20 rounded-3xl blur-2xl" />

                            {/* Dashboard Preview Card */}
                            <div className="relative bg-slate-900 rounded-2xl shadow-2xl border border-slate-700/50 overflow-hidden">
                                {/* Browser Chrome */}
                                <div className="flex items-center gap-2 px-4 py-3 bg-slate-800 border-b border-slate-700">
                                    <div className="flex gap-1.5">
                                        <div className="w-3 h-3 rounded-full bg-rose-500" />
                                        <div className="w-3 h-3 rounded-full bg-amber-500" />
                                        <div className="w-3 h-3 rounded-full bg-emerald-500" />
                                    </div>
                                    <div className="flex-1 mx-4">
                                        <div className="bg-slate-700 rounded-md px-3 py-1 text-xs text-slate-400 text-center">
                                            app.quantleap.in/dashboard
                                        </div>
                                    </div>
                                </div>

                                {/* Dashboard Content Preview */}
                                <div className="p-6 space-y-4">
                                    {/* Stats Row */}
                                    <div className="grid grid-cols-3 gap-3">
                                        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                                            <div className="text-xs text-slate-400 mb-1">Portfolio Value</div>
                                            <div className="text-xl font-bold text-white">₹24,56,890</div>
                                            <div className="text-xs text-emerald-400 flex items-center gap-1 mt-1">
                                                <TrendingUp className="h-3 w-3" /> +12.4%
                                            </div>
                                        </div>
                                        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                                            <div className="text-xs text-slate-400 mb-1">Today's P&L</div>
                                            <div className="text-xl font-bold text-emerald-400">+₹8,450</div>
                                            <div className="text-xs text-emerald-400/70 mt-1">+0.34%</div>
                                        </div>
                                        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                                            <div className="text-xs text-slate-400 mb-1">Total Gain</div>
                                            <div className="text-xl font-bold text-emerald-400">+₹4,56,890</div>
                                            <div className="text-xs text-emerald-400/70 mt-1">+22.8%</div>
                                        </div>
                                    </div>

                                    {/* Holdings Preview */}
                                    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
                                        <div className="px-4 py-3 border-b border-slate-700/50">
                                            <div className="text-sm font-semibold text-white">Top Holdings</div>
                                        </div>
                                        <div className="divide-y divide-slate-700/50">
                                            {[
                                                { symbol: 'RELIANCE', price: '₹2,456', change: '+2.3%', up: true },
                                                { symbol: 'TCS', price: '₹3,890', change: '+1.1%', up: true },
                                                { symbol: 'INFY', price: '₹1,567', change: '-0.8%', up: false },
                                            ].map((stock) => (
                                                <div key={stock.symbol} className="flex items-center justify-between px-4 py-3">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center text-xs font-bold text-indigo-300">
                                                            {stock.symbol.slice(0, 2)}
                                                        </div>
                                                        <span className="text-sm font-medium text-white">{stock.symbol}</span>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="text-sm font-medium text-white">{stock.price}</div>
                                                        <div className={`text-xs ${stock.up ? 'text-emerald-400' : 'text-rose-400'}`}>
                                                            {stock.change}
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* AI Insight Badge */}
                                    <div className="bg-gradient-to-r from-indigo-500/10 to-purple-500/10 rounded-xl p-4 border border-indigo-500/20">
                                        <div className="flex items-start gap-3">
                                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
                                                <Sparkles className="h-4 w-4 text-white" />
                                            </div>
                                            <div>
                                                <div className="text-xs font-semibold text-indigo-300 mb-1">AI Insight</div>
                                                <div className="text-sm text-slate-300">
                                                    Your portfolio is overweight in IT sector by 15%. Consider diversifying into banking.
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Floating Badges */}
                            <div className="absolute -left-4 top-1/4 bg-white rounded-xl shadow-lg px-4 py-3 border border-slate-100 animate-bounce" style={{ animationDuration: '3s' }}>
                                <div className="flex items-center gap-2">
                                    <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
                                        <CheckCircle className="h-4 w-4 text-emerald-600" />
                                    </div>
                                    <div>
                                        <div className="text-xs text-muted">Zerodha synced</div>
                                        <div className="text-sm font-semibold text-text">12 holdings imported</div>
                                    </div>
                                </div>
                            </div>

                            <div className="absolute -right-4 bottom-1/4 bg-white rounded-xl shadow-lg px-4 py-3 border border-slate-100 animate-bounce" style={{ animationDuration: '4s', animationDelay: '1s' }}>
                                <div className="flex items-center gap-2">
                                    <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
                                        <TrendingUp className="h-4 w-4 text-amber-600" />
                                    </div>
                                    <div>
                                        <div className="text-xs text-muted">XIRR calculated</div>
                                        <div className="text-sm font-semibold text-emerald-600">+18.4% returns</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Broker Logos */}
                    <div className="mt-20 text-center">
                        <p className="text-sm text-muted mb-6">Seamlessly connects with your favorite brokers</p>
                        <div className="flex flex-wrap items-center justify-center gap-8 opacity-60">
                            <div className="flex items-center gap-2 text-lg font-semibold text-slate-600">
                                <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center p-1.5">
                                    <img src="https://kite.zerodha.com/static/images/kite-logo.svg" alt="Zerodha" className="w-full h-full object-contain" />
                                </div>
                                Zerodha
                            </div>
                            <div className="flex items-center gap-2 text-lg font-semibold text-slate-600">
                                <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600 font-bold">A</div>
                                Angel One
                            </div>
                            <div className="flex items-center gap-2 text-lg font-semibold text-slate-600">
                                <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center text-purple-600 font-bold">5</div>
                                5Paisa
                            </div>
                            <div className="flex items-center gap-2 text-lg font-semibold text-slate-400">
                                <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-400 font-bold">+</div>
                                More coming
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Security & Trust Section */}
            <section id="security" className="bg-slate-900 py-16">
                <div className="container mx-auto px-4">
                    <div className="max-w-5xl mx-auto">
                        <div className="text-center mb-12">
                            <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                                <span className="text-sm font-medium text-emerald-400">Security First</span>
                            </div>
                            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Your Data is Safe With Us</h2>
                            <p className="text-lg text-slate-400 max-w-2xl mx-auto">
                                We never store your broker passwords. All connections use official OAuth2 APIs.
                            </p>
                        </div>

                        <div className="grid md:grid-cols-3 gap-6">
                            {/* OAuth2 Badge */}
                            <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 hover:border-indigo-500/30 transition-colors">
                                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center mb-4">
                                    <KeyRound className="h-6 w-6 text-indigo-400" />
                                </div>
                                <h3 className="text-lg font-semibold text-white mb-2">OAuth2 Authentication</h3>
                                <p className="text-slate-400 text-sm leading-relaxed">
                                    Connect brokers using their official OAuth flow. We never see or store your trading passwords.
                                </p>
                                <div className="mt-4 flex items-center gap-2 text-xs text-emerald-400">
                                    <CheckCircle className="h-3.5 w-3.5" />
                                    Industry standard
                                </div>
                            </div>

                            {/* Encryption Badge */}
                            <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 hover:border-emerald-500/30 transition-colors">
                                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center mb-4">
                                    <Lock className="h-6 w-6 text-emerald-400" />
                                </div>
                                <h3 className="text-lg font-semibold text-white mb-2">AES-256 Encryption</h3>
                                <p className="text-slate-400 text-sm leading-relaxed">
                                    All sensitive data encrypted at rest using bank-grade AES-256 encryption with secure key management.
                                </p>
                                <div className="mt-4 flex items-center gap-2 text-xs text-emerald-400">
                                    <CheckCircle className="h-3.5 w-3.5" />
                                    Bank-grade security
                                </div>
                            </div>

                            {/* No Credential Storage */}
                            <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 hover:border-amber-500/30 transition-colors">
                                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center mb-4">
                                    <EyeOff className="h-6 w-6 text-amber-400" />
                                </div>
                                <h3 className="text-lg font-semibold text-white mb-2">No Password Storage</h3>
                                <p className="text-slate-400 text-sm leading-relaxed">
                                    We only store OAuth tokens with limited permissions. Your broker credentials never touch our servers.
                                </p>
                                <div className="mt-4 flex items-center gap-2 text-xs text-emerald-400">
                                    <CheckCircle className="h-3.5 w-3.5" />
                                    Zero knowledge
                                </div>
                            </div>
                        </div>

                        {/* Open Source Badge */}
                        <div className="mt-8 text-center">
                            <div className="inline-flex items-center gap-3 px-6 py-3 bg-slate-800/50 rounded-xl border border-slate-700/50">
                                <Code2 className="h-5 w-5 text-slate-400" />
                                <span className="text-sm text-slate-300">
                                    Open source on <a href="https://github.com/priyaprasadblr/portfolio-tracker" target="_blank" rel="noopener noreferrer" className="font-medium text-indigo-400 hover:text-indigo-300 transition-colors">GitHub</a> — audit the code yourself
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features + Benefits Grid */}
            <section id="features" className="container mx-auto px-4 py-16">
                <div className="text-center mb-12">
                    <h2 className="text-3xl md:text-4xl font-bold mb-4">Stop Guessing. Start Knowing.</h2>
                    <p className="text-lg text-muted max-w-2xl mx-auto">
                        Every feature is designed to save you time and help you make smarter investment decisions.
                    </p>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
                    <FeatureBenefitCard
                        icon={<TrendingUp className="h-7 w-7" />}
                        iconBg="bg-emerald-100"
                        iconColor="text-emerald-600"
                        feature="Real-Time P&L"
                        benefit="Know exactly what you're making or losing — instantly"
                        description="Live portfolio value, today's change, and total gains updated automatically. No more logging into multiple broker apps."
                    />
                    <FeatureBenefitCard
                        icon={<Zap className="h-7 w-7" />}
                        iconBg="bg-purple-100"
                        iconColor="text-purple-600"
                        feature="One-Click Broker Sync"
                        benefit="No manual uploads. Zero data entry. Ever."
                        description="Connect Zerodha, Angel One, or 5Paisa in seconds. Your holdings sync automatically via secure OAuth2."
                    />
                    <FeatureBenefitCard
                        icon={<LineChart className="h-7 w-7" />}
                        iconBg="bg-blue-100"
                        iconColor="text-blue-600"
                        feature="AI Technical Signals"
                        benefit="Spot trends early with RSI, MACD & moving average alerts"
                        description="Get actionable buy/sell signals powered by technical analysis. Know when your stocks are overbought or oversold."
                    />
                    <FeatureBenefitCard
                        icon={<PieChart className="h-7 w-7" />}
                        iconBg="bg-indigo-100"
                        iconColor="text-indigo-600"
                        feature="Multi-Portfolio Tracking"
                        benefit="Separate trading, long-term, and family portfolios"
                        description="Create unlimited portfolios for different strategies. See each one's performance independently or combined."
                    />
                    <FeatureBenefitCard
                        icon={<Shield className="h-7 w-7" />}
                        iconBg="bg-rose-100"
                        iconColor="text-rose-600"
                        feature="Bank-Grade Security"
                        benefit="Sleep easy knowing your data is protected"
                        description="AES-256 encryption, OAuth2 authentication, and zero password storage. We can't access your broker even if we wanted to."
                    />
                    <FeatureBenefitCard
                        icon={<BarChart3 className="h-7 w-7" />}
                        iconBg="bg-amber-100"
                        iconColor="text-amber-600"
                        feature="Tax-Ready Reports"
                        benefit="One click to download your capital gains statement"
                        description="Calculate STCG/LTCG automatically. Export transaction history for ITR filing. Save hours during tax season."
                    />
                </div>
            </section>

            {/* Social Proof Stats */}
            <section className="bg-gradient-to-r from-indigo-600 to-purple-600 py-12">
                <div className="container mx-auto px-4">
                    <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center text-white">
                        <div>
                            <div className="text-3xl md:text-4xl font-bold mb-1">100%</div>
                            <div className="text-indigo-200 text-sm">Free Forever Plan</div>
                        </div>
                        <div>
                            <div className="text-3xl md:text-4xl font-bold mb-1">&lt;2s</div>
                            <div className="text-indigo-200 text-sm">Broker Sync Time</div>
                        </div>
                        <div>
                            <div className="text-3xl md:text-4xl font-bold mb-1">3</div>
                            <div className="text-indigo-200 text-sm">Brokers Supported</div>
                        </div>
                        <div>
                            <div className="text-3xl md:text-4xl font-bold mb-1">Open</div>
                            <div className="text-indigo-200 text-sm">Source Code</div>
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

            {/* Pricing Section */}
            <section id="pricing" className="container mx-auto px-4 py-16">
                <div className="text-center mb-12">
                    <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 bg-emerald-100 border border-emerald-200 rounded-full">
                        <Gift className="h-4 w-4 text-emerald-600" />
                        <span className="text-sm font-medium text-emerald-700">Limited Time Offer</span>
                    </div>
                    <h2 className="text-3xl md:text-4xl font-bold mb-4">Simple, Transparent Pricing</h2>
                    <p className="text-lg text-muted max-w-2xl mx-auto">
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
                            <h3 className="text-2xl font-bold text-slate-900 mb-2">Free Forever</h3>
                            <div className="flex items-baseline justify-center gap-1">
                                <span className="text-5xl font-bold text-slate-900">₹0</span>
                                <span className="text-slate-500">/month</span>
                            </div>
                            <p className="text-sm text-emerald-600 font-medium mt-2">
                                No credit card required
                            </p>
                        </div>

                        <ul className="space-y-4 mb-8">
                            <PricingFeature text="Unlimited portfolios" included />
                            <PricingFeature text="Connect all 3 brokers (Zerodha, Angel, 5Paisa)" included />
                            <PricingFeature text="Real-time P&L tracking" included />
                            <PricingFeature text="Technical indicators (RSI, MACD)" included />
                            <PricingFeature text="Tax reports (STCG/LTCG)" included />
                            <PricingFeature text="Export to CSV/Excel" included />
                            <PricingFeature text="Email support" included />
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
                            <h3 className="text-2xl font-bold text-slate-900 mb-2">Pro</h3>
                            <div className="flex items-baseline justify-center gap-1">
                                <span className="text-5xl font-bold text-slate-400">₹199</span>
                                <span className="text-slate-400">/month</span>
                            </div>
                            <p className="text-sm text-amber-600 font-medium mt-2">
                                Coming Q2 2026
                            </p>
                        </div>

                        <ul className="space-y-4 mb-8 opacity-70">
                            <PricingFeature text="Everything in Free, plus:" included />
                            <PricingFeature text="Price alerts (email + push)" coming />
                            <PricingFeature text="Advanced AI recommendations" coming />
                            <PricingFeature text="Mutual fund tracking" coming />
                            <PricingFeature text="Goal-based investing" coming />
                            <PricingFeature text="Family portfolio linking" coming />
                            <PricingFeature text="Priority support" coming />
                        </ul>

                        <button
                            disabled
                            className="w-full py-4 text-lg font-semibold text-slate-400 bg-slate-200 rounded-xl cursor-not-allowed"
                        >
                            Coming Soon
                        </button>
                    </div>
                </div>

                {/* FAQ-style reassurance */}
                <div className="max-w-2xl mx-auto mt-12 text-center">
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
                        <p className="text-amber-800 font-medium">
                            🎁 <strong>Early Adopter Promise:</strong> Sign up now and you'll get the Pro features free for 6 months when they launch.
                        </p>
                    </div>
                </div>
            </section>

            {/* Built By / About Section */}
            <section id="about" className="container mx-auto px-4 py-16">
                <div className="max-w-4xl mx-auto">
                    <div className="text-center mb-10">
                        <h2 className="text-3xl md:text-4xl font-bold mb-4">Built by an Investor, for Investors</h2>
                        <p className="text-lg text-muted">
                            I built QuantLeap because I was frustrated with existing portfolio trackers.
                        </p>
                    </div>

                    <div className="bg-gradient-to-br from-slate-50 to-indigo-50 rounded-2xl p-8 border border-slate-200">
                        <div className="flex flex-col md:flex-row items-center gap-8">
                            {/* Founder Avatar */}
                            <div className="flex-shrink-0">
                                <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-4xl text-white font-bold shadow-lg shadow-indigo-500/30">
                                    P
                                </div>
                            </div>

                            {/* Story */}
                            <div className="flex-1 text-center md:text-left">
                                <blockquote className="text-lg text-slate-700 mb-4 leading-relaxed">
                                    "I use Zerodha for trading but hated logging in just to check my portfolio. I wanted something that auto-syncs, shows me real P&L, and doesn't try to sell me mutual funds. So I built QuantLeap."
                                </blockquote>
                                <div className="flex flex-col md:flex-row md:items-center gap-3">
                                    <div>
                                        <div className="font-semibold text-slate-900">Priya Prasad</div>
                                        <div className="text-sm text-slate-500">Founder of QuantLeap</div>
                                    </div>
                                    <div className="flex items-center gap-3 md:ml-auto">
                                        <a
                                            href="https://github.com/priyaprasadblr"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 text-white text-sm rounded-lg hover:bg-slate-800 transition-colors"
                                        >
                                            <Github className="h-4 w-4" />
                                            GitHub
                                        </a>
                                        <a
                                            href="https://www.linkedin.com/in/priya-prasad-0299b33a9"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                                        >
                                            <Linkedin className="h-4 w-4" />
                                            LinkedIn
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="container mx-auto px-4 py-16">
                <div className="max-w-3xl mx-auto text-center bg-gradient-to-br from-indigo-100 to-purple-100 rounded-2xl p-12 border border-indigo-200">
                    <Sparkles className="h-16 w-16 text-indigo-600 mx-auto mb-4" />
                    <h2 className="text-3xl md:text-4xl font-bold mb-4">Ready to Try It?</h2>
                    <p className="text-lg text-muted mb-8">
                        Start tracking your portfolio today. Free forever — no credit card needed.
                    </p>
                    <button
                        onClick={() => navigate('/register')}
                        className="px-10 py-4 text-lg font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl hover:shadow-2xl transition-all"
                    >
                        Get Started Free
                    </button>
                </div>
            </section>

            {/* Contact Us Section */}
            <section id="contact" className="bg-slate-50 py-16">
                <div className="container mx-auto px-4">
                    <div className="max-w-4xl mx-auto">
                        <div className="text-center mb-12">
                            <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 bg-indigo-100 border border-indigo-200 rounded-full">
                                <MessageSquare className="h-4 w-4 text-indigo-600" />
                                <span className="text-sm font-medium text-indigo-700">Get in Touch</span>
                            </div>
                            <h2 className="text-3xl md:text-4xl font-bold mb-4">Contact Us</h2>
                            <p className="text-lg text-muted max-w-2xl mx-auto">
                                Have questions, feedback, or feature requests? We'd love to hear from you.
                            </p>
                        </div>

                        <div className="grid md:grid-cols-5 gap-8">
                            {/* Contact Info */}
                            <div className="md:col-span-2 space-y-6">
                                <div className="bg-white rounded-2xl p-6 border border-slate-200">
                                    <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center mb-4">
                                        <Mail className="h-6 w-6 text-indigo-600" />
                                    </div>
                                    <h3 className="text-lg font-semibold text-slate-900 mb-2">Email Us</h3>
                                    <a
                                        href="mailto:futurestation.in@gmail.com"
                                        className="text-indigo-600 hover:text-indigo-700 transition-colors font-medium"
                                    >
                                        futurestation.in@gmail.com
                                    </a>
                                    <p className="text-sm text-slate-500 mt-2">
                                        We typically respond within 24 hours
                                    </p>
                                </div>

                                <div className="bg-white rounded-2xl p-6 border border-slate-200">
                                    <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center mb-4">
                                        <Github className="h-6 w-6 text-emerald-600" />
                                    </div>
                                    <h3 className="text-lg font-semibold text-slate-900 mb-2">Open Source</h3>
                                    <a
                                        href="https://github.com/priyaprasadblr/portfolio-tracker"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-emerald-600 hover:text-emerald-700 transition-colors font-medium"
                                    >
                                        Report issues on GitHub
                                    </a>
                                    <p className="text-sm text-slate-500 mt-2">
                                        Found a bug? Submit a GitHub issue
                                    </p>
                                </div>
                            </div>

                            {/* Contact Form */}
                            <div className="md:col-span-3">
                                <form onSubmit={handleContactSubmit} className="bg-white rounded-2xl p-6 md:p-8 border border-slate-200 shadow-sm">
                                    {submitStatus === 'success' && (
                                        <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3">
                                            <CheckCircle className="h-5 w-5 text-emerald-600 flex-shrink-0" />
                                            <p className="text-emerald-700 text-sm font-medium">
                                                Email client opened! Please send the email to complete your message.
                                            </p>
                                        </div>
                                    )}

                                    <div className="grid md:grid-cols-2 gap-4 mb-4">
                                        <div>
                                            <label htmlFor="name" className="block text-sm font-medium text-slate-700 mb-2">
                                                Your Name
                                            </label>
                                            <input
                                                type="text"
                                                id="name"
                                                required
                                                value={contactForm.name}
                                                onChange={(e) => setContactForm(prev => ({ ...prev, name: e.target.value }))}
                                                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                                                placeholder="John Doe"
                                            />
                                        </div>
                                        <div>
                                            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
                                                Email Address
                                            </label>
                                            <input
                                                type="email"
                                                id="email"
                                                required
                                                value={contactForm.email}
                                                onChange={(e) => setContactForm(prev => ({ ...prev, email: e.target.value }))}
                                                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                                                placeholder="john@example.com"
                                            />
                                        </div>
                                    </div>

                                    <div className="mb-4">
                                        <label htmlFor="subject" className="block text-sm font-medium text-slate-700 mb-2">
                                            Subject
                                        </label>
                                        <input
                                            type="text"
                                            id="subject"
                                            required
                                            value={contactForm.subject}
                                            onChange={(e) => setContactForm(prev => ({ ...prev, subject: e.target.value }))}
                                            className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                                            placeholder="Feature request, bug report, general inquiry..."
                                        />
                                    </div>

                                    <div className="mb-6">
                                        <label htmlFor="message" className="block text-sm font-medium text-slate-700 mb-2">
                                            Message
                                        </label>
                                        <textarea
                                            id="message"
                                            required
                                            rows={5}
                                            value={contactForm.message}
                                            onChange={(e) => setContactForm(prev => ({ ...prev, message: e.target.value }))}
                                            className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors resize-none"
                                            placeholder="Tell us what's on your mind..."
                                        />
                                    </div>

                                    <button
                                        type="submit"
                                        disabled={isSubmitting}
                                        className="w-full py-4 text-lg font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl hover:shadow-lg hover:shadow-indigo-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                    >
                                        {isSubmitting ? (
                                            <>
                                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                Opening Email...
                                            </>
                                        ) : (
                                            <>
                                                <Send className="h-5 w-5" />
                                                Send Message
                                            </>
                                        )}
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>
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

function FeatureBenefitCard({
    icon,
    iconBg,
    iconColor,
    feature,
    benefit,
    description
}: {
    icon: React.ReactNode
    iconBg: string
    iconColor: string
    feature: string
    benefit: string
    description: string
}) {
    return (
        <div className="group p-6 bg-white rounded-2xl border border-slate-200 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-500/10 transition-all duration-300">
            {/* Icon */}
            <div className={`w-14 h-14 ${iconBg} ${iconColor} rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                {icon}
            </div>

            {/* Feature Label */}
            <div className="text-xs font-semibold text-indigo-600 uppercase tracking-wider mb-2">
                {feature}
            </div>

            {/* Benefit (Main Headline) */}
            <h3 className="text-lg font-bold text-slate-900 mb-3 leading-snug">
                {benefit}
            </h3>

            {/* Description */}
            <p className="text-slate-500 text-sm leading-relaxed">
                {description}
            </p>
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

function PricingFeature({ text, included, coming }: { text: string; included?: boolean; coming?: boolean }) {
    return (
        <li className="flex items-start gap-3">
            {included && (
                <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
            )}
            {coming && (
                <div className="w-5 h-5 rounded-full border-2 border-slate-300 flex-shrink-0 mt-0.5" />
            )}
            <span className={`text-sm ${coming ? 'text-slate-500' : 'text-slate-700'}`}>
                {text}
                {coming && <span className="ml-1 text-xs text-amber-600">(coming)</span>}
            </span>
        </li>
    )
}
