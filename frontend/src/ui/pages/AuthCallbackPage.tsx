import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { api } from '../../lib/api'
import type { User } from '../../types/domain'

export function AuthCallbackPage() {
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const token = searchParams.get('token')
        const errorParam = searchParams.get('error')

        if (errorParam) {
            // Redirect to login with error message
            navigate('/login?error=google_auth_failed', { replace: true })
            return
        }

        if (token) {
            // Store the JWT token first (for the axios interceptor)
            localStorage.setItem('access_token', token)

            // Fetch user info from /auth/me endpoint
            api.get<User>('/auth/me')
                .then(response => {
                    // Store user info in both localStorage and AuthProvider state
                    localStorage.setItem('user', JSON.stringify(response.data))

                    // Force reload the page to reinitialize AuthProvider with new data
                    // This ensures the auth state is properly synced
                    window.location.href = '/app/dashboard'
                })
                .catch(err => {
                    console.error('Failed to fetch user info:', err)
                    setError('Failed to complete sign in. Please try again.')
                    // Clear invalid token
                    localStorage.removeItem('access_token')
                    setTimeout(() => {
                        navigate('/login', { replace: true })
                    }, 2000)
                })
        } else {
            // No token, redirect to login
            navigate('/login', { replace: true })
        }
    }, [navigate, searchParams])

    return (
        <div className="min-h-full bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center px-4">
            <div className="text-center">
                <Loader2 className="h-12 w-12 animate-spin text-blue-400 mx-auto mb-4" />
                <p className="text-lg font-semibold text-white">
                    {error ? 'Sign in failed' : 'Completing sign in...'}
                </p>
                <p className="text-sm text-blue-400/70 mt-2">
                    {error || 'Please wait while we redirect you'}
                </p>
            </div>
        </div>
    )
}