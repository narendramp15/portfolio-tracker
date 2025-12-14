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

  const from = useMemo(() => {
    const state = location.state as { from?: string } | null
    return state?.from ?? '/app/dashboard'
  }, [location.state])

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', password: '' },
  })

  return (
    <div className="min-h-full bg-gradient-to-br from-bg to-surface">
      <div className="mx-auto flex min-h-full max-w-md items-center px-4 py-12">
        <div className="w-full rounded-xl border border-border bg-surface p-6 shadow-softLg">
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-fg">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold tracking-tight">Welcome back</div>
              <div className="text-sm text-muted">Sign in to continue</div>
            </div>
          </div>

          {error ? (
            <div className="mb-4 rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
              {error}
            </div>
          ) : null}

          <form
            className="space-y-4"
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
              <label className="text-sm font-medium">Email</label>
              <input
                className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm outline-none ring-primary focus:ring-2"
                type="email"
                autoComplete="email"
                {...form.register('email')}
              />
              {form.formState.errors.email ? (
                <div className="mt-1 text-xs text-danger">{form.formState.errors.email.message}</div>
              ) : null}
            </div>

            <div>
              <label className="text-sm font-medium">Password</label>
              <input
                className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm outline-none ring-primary focus:ring-2"
                type="password"
                autoComplete="current-password"
                {...form.register('password')}
              />
              {form.formState.errors.password ? (
                <div className="mt-1 text-xs text-danger">{form.formState.errors.password.message}</div>
              ) : null}
            </div>

            <button
              className="inline-flex w-full items-center justify-center rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-fg shadow-soft hover:opacity-95 disabled:opacity-60"
              type="submit"
              disabled={form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="mt-5 text-center text-sm text-muted">
            Don’t have an account?{' '}
            <Link className="font-semibold text-primary hover:underline" to="/register">
              Create one
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

