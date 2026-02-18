import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { type PropsWithChildren } from 'react'

import { api } from '../../lib/api'
import { type TokenResponse, type User } from '../../types/domain'

type AuthContextValue = {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  authReady: boolean
  login: (email: string, password: string) => Promise<void>
  register: (payload: { email: string; username: string; password: string; full_name?: string }) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function loadUserFromStorage(): User | null {
  const raw = localStorage.getItem('user')
  if (!raw) return null
  try {
    return JSON.parse(raw) as User
  } catch {
    return null
  }
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'))
  const [user, setUser] = useState<User | null>(() => loadUserFromStorage())

  // authReady indicates we've validated the stored token (if present).
  // If there's no stored token we mark ready immediately.
  const [authReady, setAuthReady] = useState<boolean>(() => (localStorage.getItem('access_token') ? false : true))

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
    setAuthReady(true)
  }, [])

  const applyTokenResponse = useCallback((data: TokenResponse) => {
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
    setAuthReady(true)
  }, [])

  // Validate stored token on mount (prevents stale-token UI)
  useEffect(() => {
    let mounted = true
    async function validate() {
      const stored = localStorage.getItem('access_token')
      if (!stored) {
        if (mounted) setAuthReady(true)
        return
      }

      try {
        const resp = await api.get<User>('/auth/me')
        if (!mounted) return
        setUser(resp.data)
        localStorage.setItem('user', JSON.stringify(resp.data))
        setToken(stored)
      } catch (err: any) {
        // On 401 or other errors, clear auth state
        if (err?.response?.status === 401) {
          logout()
        } else {
          // Treat other errors as unauthenticated to be safe
          logout()
        }
      } finally {
        if (mounted) setAuthReady(true)
      }
    }

    validate()
    return () => {
      mounted = false
    }
  }, [logout])

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await api.post<TokenResponse>('/auth/login', { email, password })
      applyTokenResponse(response.data)
    },
    [applyTokenResponse],
  )

  const register = useCallback(
    async (payload: { email: string; username: string; password: string; full_name?: string }) => {
      const response = await api.post<TokenResponse>('/auth/register', payload)
      applyTokenResponse(response.data)
    },
    [applyTokenResponse],
  )

  const value = useMemo(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token),
      authReady,
      login,
      register,
      logout,
    }),
    [token, user, authReady, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

