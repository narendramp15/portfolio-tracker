import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { type PropsWithChildren } from 'react'

import { api } from '../../lib/api'
import { type TokenResponse, type User } from '../../types/domain'

type AuthContextValue = {
  token: string | null
  user: User | null
  isAuthenticated: boolean
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

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }, [])

  const applyTokenResponse = useCallback((data: TokenResponse) => {
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
  }, [])

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
      login,
      register,
      logout,
    }),
    [token, user, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

