import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { BarChart3, CheckCircle2 } from 'lucide-react'

const schema = z.object({
    token: z.string().min(1, 'Token is required'),
    new_password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string().min(8, 'Please confirm your password'),
}).refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
})

type FormValues = z.infer<typeof schema>

export function ResetPasswordPage() {
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)

    const form = useForm<FormValues>({
        resolver: zodResolver(schema),
        defaultValues: {
            token: searchParams.get('token') || '',
            new_password: '',
            confirm_password: '',
        },
    })

    const handleSubmit = async (values: FormValues) => {
        setError(null)

        try {
            const response = await fetch('/api/auth/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: values.token,
                    new_password: values.new_password,
                }),
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to reset password')
            }

            setSuccess(true)
            setTimeout(() => {
                navigate('/login')
            }, 3000)
        } catch (err: any) {
            setError(err.message || 'Failed to reset password. Please try again.')
        }
    }

    if (success) {
        return (
            <div className="min-h-full bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center px-4 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl -z-10 animate-pulse" />
                <div className="absolute bottom-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl -z-10 animate-pulse" />

                <div className="w-full max-w-md">
                    <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-900/50 to-slate-900/50 backdrop-blur-xl shadow-2xl p-8 text-center">
                        <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 mb-4">
                            <CheckCircle2 className="h-8 w-8" />
                        </div>
                        <h2 className="text-2xl font-black text-white mb-2">Password Reset Successful!</h2>
                        <p className="text-emerald-300/70 text-sm">
                            Your password has been changed. Redirecting to login...
                        </p>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-full bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center px-4 relative overflow-hidden">
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
                            <div className="text-2xl font-black tracking-tight bg-gradient-to-r from-blue-300 to-cyan-300 bg-clip-text text-transparent">Reset Password</div>
                            <div className="text-sm text-blue-400/70">Create a new password</div>
                        </div>
                    </div>

                    {error && (
                        <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-900/20 px-4 py-3 text-sm font-medium text-rose-300">
                            {error}
                        </div>
                    )}

                    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-5">
                        <div>
                            <label className="text-sm font-semibold text-blue-300">Reset Token</label>
                            <input
                                className="mt-2 w-full rounded-lg border border-blue-500/30 bg-blue-950/50 px-4 py-2.5 text-sm text-blue-50 placeholder-blue-400/50 outline-none transition-all duration-200 focus:border-blue-400 focus:bg-blue-900/70 focus:ring-2 focus:ring-blue-500/30"
                                type="text"
                                placeholder="Enter the token from your email"
                                {...form.register('token')}
                            />
                            {form.formState.errors.token && (
                                <div className="mt-1.5 text-xs font-medium text-rose-400">{form.formState.errors.token.message}</div>
                            )}
                        </div>

                        <div>
                            <label className="text-sm font-semibold text-blue-300">New Password</label>
                            <input
                                className="mt-2 w-full rounded-lg border border-blue-500/30 bg-blue-950/50 px-4 py-2.5 text-sm text-blue-50 placeholder-blue-400/50 outline-none transition-all duration-200 focus:border-blue-400 focus:bg-blue-900/70 focus:ring-2 focus:ring-blue-500/30"
                                type="password"
                                placeholder="••••••••"
                                autoComplete="new-password"
                                {...form.register('new_password')}
                            />
                            {form.formState.errors.new_password && (
                                <div className="mt-1.5 text-xs font-medium text-rose-400">{form.formState.errors.new_password.message}</div>
                            )}
                        </div>

                        <div>
                            <label className="text-sm font-semibold text-blue-300">Confirm Password</label>
                            <input
                                className="mt-2 w-full rounded-lg border border-blue-500/30 bg-blue-950/50 px-4 py-2.5 text-sm text-blue-50 placeholder-blue-400/50 outline-none transition-all duration-200 focus:border-blue-400 focus:bg-blue-900/70 focus:ring-2 focus:ring-blue-500/30"
                                type="password"
                                placeholder="••••••••"
                                autoComplete="new-password"
                                {...form.register('confirm_password')}
                            />
                            {form.formState.errors.confirm_password && (
                                <div className="mt-1.5 text-xs font-medium text-rose-400">{form.formState.errors.confirm_password.message}</div>
                            )}
                        </div>

                        <button
                            className="w-full rounded-lg bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-600 px-4 py-3 text-sm font-bold text-white shadow-lg hover:shadow-2xl hover:shadow-blue-500/20 disabled:opacity-60 transition-all duration-200 mt-6 hover:scale-105 active:scale-95"
                            type="submit"
                            disabled={form.formState.isSubmitting}
                        >
                            {form.formState.isSubmitting ? 'Resetting...' : 'Reset Password'}
                        </button>
                    </form>

                    <div className="mt-6 text-center text-sm text-blue-400/70">
                        Remember your password?{' '}
                        <Link className="font-semibold text-blue-400 hover:text-blue-300 transition-colors" to="/login">
                            Sign in
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    )
}
