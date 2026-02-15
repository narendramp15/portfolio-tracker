import { useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { BarChart3 } from 'lucide-react'

import { useAuth } from '../../providers/auth/AuthProvider'

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
})

type FormValues = z.infer<typeof schema>

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)
  const [showResetModal, setShowResetModal] = useState(false)
  const [resetEmail, setResetEmail] = useState('')
  const [resetMessage, setResetMessage] = useState<string | null>(null)
  const [resetLoading, setResetLoading] = useState(false)

  const from = useMemo(() => {
    const state = location.state as { from?: string } | null
    return state?.from ?? '/app/dashboard'
  }, [location.state])

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', password: '' },
  })

  const handleForgotPassword = async () => {
    if (!resetEmail) {
      setResetMessage('Please enter your email address')
      return
    }

    setResetLoading(true)
    setResetMessage(null)

    try {
      const response = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: resetEmail }),
      })

      const data = await response.json()
      setResetMessage(data.message || 'Reset instructions sent! Check the console for the token (dev mode).')
    } catch (err) {
      setResetMessage('Failed to send reset request. Please try again.')
    } finally {
      setResetLoading(false)
    }
  }

  return (
    <div className="min-h-full bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center px-4 relative overflow-hidden">
      {/* Decorative gradient blobs */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl -z-10 animate-pulse" />
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl -z-10 animate-pulse" />
      <div className="absolute top-1/2 left-1/3 w-72 h-72 bg-blue-400/5 rounded-full blur-3xl -z-10" />

      <div className="w-full max-w-md">
        <div className="rounded-2xl border border-blue-500/30 bg-gradient-to-br from-blue-900/50 to-slate-900/50 backdrop-blur-xl shadow-2xl p-8 hover:border-blue-400/50 transition-all duration-300">
          <div className="mb-8 flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-lg hover:shadow-2xl transition-all duration-300">
              <BarChart3 className="h-7 w-7" />
            </div>
            <div>
              <div className="text-2xl font-black tracking-tight bg-gradient-to-r from-blue-300 to-cyan-300 bg-clip-text text-transparent">Quantleap</div>
              <div className="text-sm text-blue-400/70">Portfolio Tracker</div>
            </div>
          </div>

          {error ? (
            <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-900/20 px-4 py-3 text-sm font-medium text-rose-300">
              {error}
            </div>
          ) : null}

          <form
            className="space-y-5"
            onSubmit={form.handleSubmit(async (values) => {
              setError(null)
              try {
                await login(values.email, values.password)
                navigate(from, { replace: true })
              } catch (e: any) {
                setError(e?.response?.data?.detail ?? 'Login failed. Please try again.')
              }
            })}
          >
            <div>
              <label className="text-sm font-semibold text-blue-300">Email Address</label>
              <input
                className="mt-2 w-full rounded-lg border border-blue-500/30 bg-blue-950/50 px-4 py-2.5 text-sm text-blue-50 placeholder-blue-400/50 outline-none transition-all duration-200 focus:border-blue-400 focus:bg-blue-900/70 focus:ring-2 focus:ring-blue-500/30"
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
                {...form.register('email')}
              />
              {form.formState.errors.email ? (
                <div className="mt-1.5 text-xs font-medium text-rose-400">{form.formState.errors.email.message}</div>
              ) : null}
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-blue-300">Password</label>
                <button
                  type="button"
                  onClick={() => setShowResetModal(true)}
                  className="text-xs font-medium text-blue-400 hover:text-blue-300 transition-colors"
                >
                  Forgot password?
                </button>
              </div>
              <input
                className="mt-2 w-full rounded-lg border border-blue-500/30 bg-blue-950/50 px-4 py-2.5 text-sm text-blue-50 placeholder-blue-400/50 outline-none transition-all duration-200 focus:border-blue-400 focus:bg-blue-900/70 focus:ring-2 focus:ring-blue-500/30"
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                {...form.register('password')}
              />
              {form.formState.errors.password ? (
                <div className="mt-1.5 text-xs font-medium text-rose-400">{form.formState.errors.password.message}</div>
              ) : null}
            </div>

            <button
              className="w-full rounded-lg bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-600 px-4 py-3 text-sm font-bold text-white shadow-lg hover:shadow-2xl hover:shadow-blue-500/20 disabled:opacity-60 transition-all duration-200 mt-6 hover:scale-105 active:scale-95"
              type="submit"
              disabled={form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-blue-500/20" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="bg-gradient-to-br from-blue-900/50 to-slate-900/50 px-4 text-blue-400/70">Or continue with</span>
            </div>
          </div>

          {/* Google Sign In Button */}
          <button
            type="button"
            onClick={() => {
              const backendUrl = import.meta.env.VITE_API_URL || '/api'
              const baseUrl = backendUrl.replace(/\/api$/, '') // Remove trailing /api if present
              window.location.href = `${baseUrl}/api/auth/google/login`
            }}
            className="w-full flex items-center justify-center gap-3 rounded-lg border border-blue-500/30 bg-white/10 px-4 py-3 text-sm font-semibold text-white hover:bg-white/20 hover:border-blue-400/50 transition-all duration-200"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Sign in with Google
          </button>

          <div className="mt-6 text-center text-sm text-blue-400/70">
            Don't have an account?{' '}
            <Link className="font-semibold text-blue-400 hover:text-blue-300 transition-colors" to="/register">
              Create one
            </Link>
          </div>
        </div>
      </div>

      {/* Password Reset Modal */}
      {showResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md mx-4">
            <div className="rounded-2xl border border-blue-500/30 bg-gradient-to-br from-blue-900/90 to-slate-900/90 backdrop-blur-xl shadow-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-white">Reset Password</h3>
                <button
                  onClick={() => {
                    setShowResetModal(false)
                    setResetMessage(null)
                    setResetEmail('')
                  }}
                  className="text-blue-400 hover:text-blue-300 transition-colors"
                >
                  ✕
                </button>
              </div>

              <p className="text-sm text-blue-300/70 mb-4">
                Enter your email address and we'll generate a reset token for you.
              </p>

              {resetMessage && (
                <div className="mb-4 rounded-lg border border-blue-500/30 bg-blue-900/30 px-4 py-3 text-sm text-blue-200">
                  {resetMessage}
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className="text-sm font-semibold text-blue-300">Email Address</label>
                  <input
                    className="mt-2 w-full rounded-lg border border-blue-500/30 bg-blue-950/50 px-4 py-2.5 text-sm text-blue-50 placeholder-blue-400/50 outline-none transition-all duration-200 focus:border-blue-400 focus:bg-blue-900/70 focus:ring-2 focus:ring-blue-500/30"
                    type="email"
                    placeholder="you@example.com"
                    value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)}
                  />
                </div>

                <button
                  onClick={handleForgotPassword}
                  disabled={resetLoading}
                  className="w-full rounded-lg bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-600 px-4 py-3 text-sm font-bold text-white shadow-lg hover:shadow-2xl hover:shadow-blue-500/20 disabled:opacity-60 transition-all duration-200 hover:scale-105 active:scale-95"
                >
                  {resetLoading ? 'Sending...' : 'Send Reset Token'}
                </button>

                <div className="text-center">
                  <p className="text-xs text-blue-400/50 mb-2">
                    Dev mode: Check the backend console for the reset token
                  </p>
                  <Link
                    to="/reset-password"
                    onClick={() => setShowResetModal(false)}
                    className="text-sm font-semibold text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    Already have a token? Reset password →
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
