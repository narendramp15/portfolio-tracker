import { createBrowserRouter, Navigate } from 'react-router-dom'

import { RequireAuth } from './RequireAuth'
import { AppShell } from '../ui/layout/AppShell'
import { DashboardPage } from '../ui/pages/DashboardPage'
import { HoldingsPage } from '../ui/pages/HoldingsPage'
import { BrokersPage } from '../ui/pages/BrokersPage'
import { LandingPage } from '../ui/pages/LandingPage'
import { LoginPage } from '../ui/pages/LoginPage'
import { NotFoundPage } from '../ui/pages/NotFoundPage'
import { RegisterPage } from '../ui/pages/RegisterPage'
import { ResetPasswordPage } from '../ui/pages/ResetPasswordPage'
import { SettingsPage } from '../ui/pages/SettingsPage'
import TechnicalAnalysisPage from '../ui/pages/TechnicalAnalysisPage'
import TaxReportsPage from '../ui/pages/TaxReportsPage'
import { TransactionsPage } from '../ui/pages/TransactionsPage'
import { AuthCallbackPage } from '../ui/pages/AuthCallbackPage'

export const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/broker-settings', element: <Navigate to="/app/brokers" replace /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  { path: '/reset-password', element: <ResetPasswordPage /> },
  { path: '/auth/callback', element: <AuthCallbackPage /> },
  {
    path: '/app',
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/app/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'holdings', element: <HoldingsPage /> },
      { path: 'transactions', element: <TransactionsPage /> },
      { path: 'analysis', element: <TechnicalAnalysisPage /> },
      { path: 'tax-reports', element: <TaxReportsPage /> },
      { path: 'brokers', element: <BrokersPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])
