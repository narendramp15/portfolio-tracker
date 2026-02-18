import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '../providers/auth/AuthProvider'

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, authReady } = useAuth()
  const location = useLocation()

  // While auth status is being validated, don't render protected routes
  if (!authReady) return null

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <>{children}</>
}

