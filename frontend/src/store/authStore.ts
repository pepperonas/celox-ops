import { create } from 'zustand'
import { api } from '../api/client'
import type { AuthResponse } from '../types'

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  username: string | null
  role: string | null
  loading: boolean
  error: string | null
  login: (username: string, password: string, totp?: string) => Promise<void>
  loginWithGoogle: (credential: string) => Promise<void>
  logout: () => void
  initialize: () => void
  fetchMe: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  isAuthenticated: false,
  username: null,
  role: null,
  loading: false,
  error: null,

  login: async (username: string, password: string, totp?: string) => {
    set({ loading: true, error: null })
    try {
      const formData = new URLSearchParams()
      formData.append('username', username)
      formData.append('password', password)
      if (totp) formData.append('scope', totp)

      const response = await api.post<AuthResponse>('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      set({ token: access_token, isAuthenticated: true, loading: false })
      await get().fetchMe()
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Anmeldung fehlgeschlagen. Bitte prüfen Sie Ihre Zugangsdaten.'
      set({ error: message, loading: false })
      throw err
    }
  },

  loginWithGoogle: async (credential: string) => {
    set({ loading: true, error: null })
    try {
      const response = await api.post<AuthResponse>('/auth/google', { credential })
      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      set({ token: access_token, isAuthenticated: true, loading: false })
      await get().fetchMe()
    } catch (err: unknown) {
      set({ error: 'Google-Anmeldung fehlgeschlagen.', loading: false })
      throw err
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ token: null, isAuthenticated: false, username: null, role: null })
  },

  initialize: () => {
    const token = localStorage.getItem('token')
    if (token) {
      set({ token, isAuthenticated: true })
      get().fetchMe()
    }
  },

  fetchMe: async () => {
    try {
      const res = await api.get<{ username: string; role: string }>('/auth/me')
      set({ username: res.data.username, role: res.data.role })
    } catch {
      // 401 is handled by the axios interceptor (redirect to /login)
    }
  },
}))
