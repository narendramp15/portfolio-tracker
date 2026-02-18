import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

// Mock the api module used by AuthProvider
vi.mock('../../../src/lib/api', () => ({
    api: {
        get: vi.fn(),
        post: vi.fn(),
    },
}))

import { api } from '../../../src/lib/api'
import { AuthProvider } from '../../../src/providers/auth/AuthProvider'
import { RequireAuth } from '../../../src/router/RequireAuth'

beforeEach(() => {
    localStorage.clear()
        ; (api.get as unknown as ReturnType<typeof vi.fn>).mockReset?.()
})

test('no token -> authReady true immediately and protected content renders', async () => {
    render(
        <AuthProvider>
            <MemoryRouter initialEntries={["/protected"]}>
                <Routes>
                    <Route
                        path="/protected"
                        element={
                            <RequireAuth>
                                <div>protected-content</div>
                            </RequireAuth>
                        }
                    />
                </Routes>
            </MemoryRouter>
        </AuthProvider>,
    )

    // Since there is no token, authReady should be immediate and protected child rendered
    await waitFor(() => expect(screen.getByText('protected-content')).toBeInTheDocument())
})

test('valid stored token -> AuthProvider fetches /auth/me and allows access', async () => {
    localStorage.setItem('access_token', 'valid-token')

        ; (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { id: 1, email: 'a@b.com', username: 'u' } })

    render(
        <AuthProvider>
            <MemoryRouter initialEntries={["/protected"]}>
                <Routes>
                    <Route
                        path="/protected"
                        element={
                            <RequireAuth>
                                <div>protected-ok</div>
                            </RequireAuth>
                        }
                    />
                </Routes>
            </MemoryRouter>
        </AuthProvider>,
    )

    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/auth/me'))
    await waitFor(() => expect(screen.getByText('protected-ok')).toBeInTheDocument())
    expect(localStorage.getItem('user')).toBeTruthy()
})

test('expired/stale token -> /auth/me returns 401 -> logged out and redirected to /login', async () => {
    localStorage.setItem('access_token', 'stale-token')

    const err = { response: { status: 401 } }
        ; (api.get as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(err)

    render(
        <AuthProvider>
            <MemoryRouter initialEntries={["/protected"]}>
                <Routes>
                    <Route path="/login" element={<div>login-page</div>} />
                    <Route
                        path="/protected"
                        element={
                            <RequireAuth>
                                <div>should-not-see</div>
                            </RequireAuth>
                        }
                    />
                </Routes>
            </MemoryRouter>
        </AuthProvider>,
    )

    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/auth/me'))
    await waitFor(() => expect(screen.getByText('login-page')).toBeInTheDocument())
    expect(localStorage.getItem('access_token')).toBeNull()
})