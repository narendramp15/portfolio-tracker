import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'

export function AuthCallbackPage() {
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()

    useEffect(() => {
        const token = searchParams.get('token')
        const error = searchParams.get('error')

        if (error) {
            // Redirect to login with error message
            navigate('/login?error=google_auth_failed', { replace: true })
            return
        }

        if (token) {
            // Store the JWT token
            localStorage.setItem('access_token', token)

            // Redirect to dashboard
            setTimeout(() => {
                navigate('/app/dashboard', { replace: true })
            }, 500)
        } else {
            // No token, redirect to login
            navigate('/login', { replace: true })
        }
    }, [navigate, searchParams])

    return (
        <div className="min-h-full bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center px-4">
            <div className="text-center">
                <Loader2 className="h-12 w-12 animate-spin text-blue-400 mx-auto mb-4" />
                <p className="text-lg font-semibold text-white">Completing sign in...</p>
                <p className="text-sm text-blue-400/70 mt-2">Please wait while we redirect you</p>
            </div>
        </div>
    )
}
