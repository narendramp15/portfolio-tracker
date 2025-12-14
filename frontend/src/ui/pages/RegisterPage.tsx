import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { BarChart3 } from 'lucide-react'

import { useAuth } from '../../providers/auth/AuthProvider'

const schema = z.object({
  email: z.string().email(),
  username: z.string().min(3),
  full_name: z.string().optional(),
  password: z.string().min(8, 'Min 8 characters'),
})

type FormValues = z.infer<typeof schema>

export function RegisterPage() {
  const { register: registerUser } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', username: '', full_name: '', password: '' },
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
              <div className="text-lg font-semibold tracking-tight">Create your account</div>
              <div className="text-sm text-muted">Get started in a minute</div>
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
                await registerUser({
                  email: values.email,
                  username: values.username,
                  password: values.password,
                  full_name: values.full_name || undefined,
                })
                navigate('/app/dashboard', { replace: true })
              } catch (e: any) {
                setError(e?.response?.data?.detail ?? 'Registration failed. Please try again.')
              }
            })}
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
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
                <label className="text-sm font-medium">Username</label>
                <input
                  className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm outline-none ring-primary focus:ring-2"
                  {...form.register('username')}
                />
                {form.formState.errors.username ? (
                  <div className="mt-1 text-xs text-danger">{form.formState.errors.username.message}</div>
                ) : null}
              </div>

              <div>
                <label className="text-sm font-medium">Full name</label>
                <input
                  className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm outline-none ring-primary focus:ring-2"
                  {...form.register('full_name')}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-sm font-medium">Password</label>
                <input
                  className="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm outline-none ring-primary focus:ring-2"
                  type="password"
                  autoComplete="new-password"
                  {...form.register('password')}
                />
                {form.formState.errors.password ? (
                  <div className="mt-1 text-xs text-danger">{form.formState.errors.password.message}</div>
                ) : null}
              </div>
            </div>

            <button
              className="inline-flex w-full items-center justify-center rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-fg shadow-soft hover:opacity-95 disabled:opacity-60"
              type="submit"
              disabled={form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? 'Creating…' : 'Create account'}
            </button>
          </form>

          <div className="mt-5 text-center text-sm text-muted">
            Already have an account?{' '}
            <Link className="font-semibold text-primary hover:underline" to="/login">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

