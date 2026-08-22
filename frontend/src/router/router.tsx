import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'

import { RequireAuth } from './RequireAuth'
import { AppShell } from '../ui/layout/AppShell'

// Every route is code-split. Previously all 24 pages were imported eagerly, so
// a first-time visitor to the landing page downloaded the options analyser, the
// screeners and the whole authenticated app before anything painted.
const LandingPage = lazy(() => import('../ui/pages/LandingPage').then(m => ({ default: m.LandingPage })))
const LoginPage = lazy(() => import('../ui/pages/LoginPage').then(m => ({ default: m.LoginPage })))
const RegisterPage = lazy(() => import('../ui/pages/RegisterPage').then(m => ({ default: m.RegisterPage })))
const ResetPasswordPage = lazy(() => import('../ui/pages/ResetPasswordPage').then(m => ({ default: m.ResetPasswordPage })))
const AuthCallbackPage = lazy(() => import('../ui/pages/AuthCallbackPage').then(m => ({ default: m.AuthCallbackPage })))
const PricingPage = lazy(() => import('../ui/pages/PricingPage').then(m => ({ default: m.PricingPage })))
const NotFoundPage = lazy(() => import('../ui/pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })))

const DashboardPage = lazy(() => import('../ui/pages/DashboardPage').then(m => ({ default: m.DashboardPage })))
const HoldingsPage = lazy(() => import('../ui/pages/HoldingsPage').then(m => ({ default: m.HoldingsPage })))
const MutualFundsPage = lazy(() => import('../ui/pages/MutualFundsPage').then(m => ({ default: m.MutualFundsPage })))
const TransactionsPage = lazy(() => import('../ui/pages/TransactionsPage').then(m => ({ default: m.TransactionsPage })))
const BrokersPage = lazy(() => import('../ui/pages/BrokersPage').then(m => ({ default: m.BrokersPage })))
const SettingsPage = lazy(() => import('../ui/pages/SettingsPage').then(m => ({ default: m.SettingsPage })))
const BillingPage = lazy(() => import('../ui/pages/BillingPage').then(m => ({ default: m.BillingPage })))
const OptionsBillingPage = lazy(() => import('../ui/pages/OptionsBillingPage').then(m => ({ default: m.OptionsBillingPage })))

// Default exports.
const TechnicalAnalysisPage = lazy(() => import('../ui/pages/TechnicalAnalysisPage'))
const TaxReportsPage = lazy(() => import('../ui/pages/TaxReportsPage'))
const NiftyOptionsAnalyzerPage = lazy(() => import('../ui/pages/NiftyOptionsAnalyzerPage'))
const StockScreenerPage = lazy(() => import('../ui/pages/StockScreenerPage'))
const BeginnerScreenerPage = lazy(() => import('../ui/pages/BeginnerScreenerPage'))

function RouteFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center" role="status" aria-live="polite">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
      <span className="sr-only">Loading…</span>
    </div>
  )
}

/** Wrap a lazily-loaded route element in its own Suspense boundary. */
function page(element: ReactNode) {
  return <Suspense fallback={<RouteFallback />}>{element}</Suspense>
}

export const router = createBrowserRouter([
  { path: '/', element: page(<LandingPage />) },
  { path: '/broker-settings', element: <Navigate to="/app/brokers" replace /> },
  { path: '/pricing', element: page(<PricingPage />) },
  { path: '/login', element: page(<LoginPage />) },
  { path: '/register', element: page(<RegisterPage />) },
  { path: '/reset-password', element: page(<ResetPasswordPage />) },
  { path: '/auth/callback', element: page(<AuthCallbackPage />) },
  { path: '/options-analyzer', element: page(<NiftyOptionsAnalyzerPage />) },
  {
    path: '/app',
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/app/dashboard" replace /> },
      { path: 'dashboard', element: page(<DashboardPage />) },
      { path: 'holdings', element: page(<HoldingsPage />) },
      { path: 'mutual-funds', element: page(<MutualFundsPage />) },
      { path: 'transactions', element: page(<TransactionsPage />) },
      { path: 'analysis', element: page(<TechnicalAnalysisPage />) },
      { path: 'tax-reports', element: page(<TaxReportsPage />) },
      { path: 'brokers', element: page(<BrokersPage />) },
      { path: 'settings', element: page(<SettingsPage />) },
      { path: 'billing', element: page(<BillingPage />) },
      { path: 'options-billing', element: page(<OptionsBillingPage />) },
      { path: 'options-analyzer', element: page(<NiftyOptionsAnalyzerPage />) },
      { path: 'stock-screener', element: page(<StockScreenerPage />) },
      { path: 'beginner-screener', element: page(<BeginnerScreenerPage />) },
    ],
  },
  { path: '*', element: page(<NotFoundPage />) },
])
