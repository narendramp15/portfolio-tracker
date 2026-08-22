import axios, { AxiosError } from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** Endpoints where a 401 is a legitimate answer, not an expired session. */
const AUTH_ENDPOINTS = ['/auth/login', '/auth/register', '/auth/forgot-password', '/auth/reset-password']

function isAuthEndpoint(url?: string) {
  if (!url) return false
  return AUTH_ENDPOINTS.some((path) => url.includes(path))
}

/** Pull the human-readable message out of a FastAPI error response. */
function extractDetail(error: AxiosError): string | undefined {
  const data = error.response?.data as unknown
  if (typeof data === 'string') return data
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    // 422 bodies are a list of validation errors.
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined
      if (first?.msg) return first.msg
    }
  }
  return undefined
}

/**
 * Error shape every caller can rely on.
 *
 * Without this, a failed request surfaced as an unhandled rejection and the
 * page rendered its empty state — a 401 or a 500 both showed a portfolio worth
 * ₹0, which is indistinguishable from a genuinely empty portfolio.
 */
export type ApiError = AxiosError & { userMessage: string }

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status
    const detail = extractDetail(error)
    let userMessage: string

    if (!error.response) {
      userMessage = 'Could not reach the server. Check your connection and try again.'
    } else if (status === 401 && !isAuthEndpoint(error.config?.url)) {
      // The session is gone. Clear it and bounce to login rather than letting
      // the page render zeros against a dead token.
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      userMessage = 'Your session has expired. Please sign in again.'
      const onLoginPage = window.location.pathname.startsWith('/login')
      if (!onLoginPage) {
        const next = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.href = `/login?expired=1&next=${next}`
      }
    } else if (status === 402) {
      // Quota / plan-limit responses carry a message worth showing verbatim.
      userMessage = detail ?? 'You have reached your plan limit. Upgrade to continue.'
    } else if (status === 429) {
      userMessage = detail ?? 'Too many requests. Please wait a moment and try again.'
    } else if (status && status >= 500) {
      userMessage = 'Something went wrong on our side. Please try again in a moment.'
    } else {
      userMessage = detail ?? 'Request failed. Please try again.'
    }

    return Promise.reject(Object.assign(error, { userMessage }))
  },
)

/** Safe accessor for use in catch blocks, where the value is typed unknown. */
export function apiErrorMessage(error: unknown, fallback = 'Request failed. Please try again.'): string {
  if (error && typeof error === 'object' && 'userMessage' in error) {
    const message = (error as { userMessage: unknown }).userMessage
    if (typeof message === 'string') return message
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}
