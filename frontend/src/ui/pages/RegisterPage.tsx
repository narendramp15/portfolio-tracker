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
    <div className="min-h-full bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center px-4 relative overflow-hidden">
      {/* Decorative gradient blobs */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl -z-10 animate-pulse" />
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl -z-10 animate-pulse" />
      <div className="absolute top-1/2 right-1/3 w-72 h-72 bg-violet-400/5 rounded-full blur-3xl -z-10" />

      <div className="w-full max-w-xl">
        <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-900/50 to-slate-900/50 backdrop-blur-xl shadow-2xl p-8 hover:border-indigo-400/50 transition-all duration-300">
          <div className="mb-8 flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-lg hover:shadow-2xl transition-all duration-300">
              <BarChart3 className="h-7 w-7" />
            </div>
            <div>
              <div className="text-2xl font-black tracking-tight bg-gradient-to-r from-indigo-300 to-purple-300 bg-clip-text text-transparent">Quatleap</div>
              <div className="text-sm text-indigo-400/70">Create Your Account</div>
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
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="text-sm font-semibold text-indigo-300">Email Address</label>
                <input
                  className="mt-2 w-full rounded-lg border border-indigo-500/30 bg-indigo-950/50 px-4 py-2.5 text-sm text-indigo-50 placeholder-indigo-400/50 outline-none transition-all duration-200 focus:border-indigo-400 focus:bg-indigo-900/70 focus:ring-2 focus:ring-indigo-500/30"
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
                <label className="text-sm font-semibold text-indigo-300">Username</label>
                <input
                  className="mt-2 w-full rounded-lg border border-indigo-500/30 bg-indigo-950/50 px-4 py-2.5 text-sm text-indigo-50 placeholder-indigo-400/50 outline-none transition-all duration-200 focus:border-indigo-400 focus:bg-indigo-900/70 focus:ring-2 focus:ring-indigo-500/30"
                  placeholder="johndoe"
                  {...form.register('username')}
                />
                {form.formState.errors.username ? (
                  <div className="mt-1.5 text-xs font-medium text-rose-400">{form.formState.errors.username.message}</div>
                ) : null}
              </div>

              <div>
                <label className="text-sm font-semibold text-indigo-300">Full Name</label>
                <input
                  className="mt-2 w-full rounded-lg border border-indigo-500/30 bg-indigo-950/50 px-4 py-2.5 text-sm text-indigo-50 placeholder-indigo-400/50 outline-none transition-all duration-200 focus:border-indigo-400 focus:bg-indigo-900/70 focus:ring-2 focus:ring-indigo-500/30"
                  placeholder="John Doe"
                  {...form.register('full_name')}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-sm font-semibold text-indigo-300">Password</label>
                <input
                  className="mt-2 w-full rounded-lg border border-indigo-500/30 bg-indigo-950/50 px-4 py-2.5 text-sm text-indigo-50 placeholder-indigo-400/50 outline-none transition-all duration-200 focus:border-indigo-400 focus:bg-indigo-900/70 focus:ring-2 focus:ring-indigo-500/30"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="new-password"
                  {...form.register('password')}
                />
                {form.formState.errors.password ? (
                  <div className="mt-1.5 text-xs font-medium text-rose-400">{form.formState.errors.password.message}</div>
                ) : null}
              </div>
            </div>

            <button
              className="w-full rounded-lg bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 px-4 py-3 text-sm font-bold text-white shadow-lg hover:shadow-2xl hover:shadow-indigo-500/20 disabled:opacity-60 transition-all duration-200 mt-6 hover:scale-105 active:scale-95"
              type="submit"
              disabled={form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? 'Creating…' : 'Create Account'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-indigo-400/70">
            Already have an account?{' '}
            <Link className="font-semibold text-indigo-400 hover:text-indigo-300 transition-colors" to="/login">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

