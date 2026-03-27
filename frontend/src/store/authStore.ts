import { create } from 'zustand'
import { api } from '../api/client'
import type { AuthResponse } from '../types'

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  initialize: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,
  loading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ loading: true, error: null })
    try {
      const formData = new URLSearchParams()
      formData.append('username', username)
      formData.append('password', password)

      const response = await api.post<AuthResponse>('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      set({ token: access_token, isAuthenticated: true, loading: false })
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Anmeldung fehlgeschlagen. Bitte prüfen Sie Ihre Zugangsdaten.'
      set({ error: message, loading: false })
      throw err
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ token: null, isAuthenticated: false })
  },

  initialize: () => {
    const token = localStorage.getItem('token')
    if (token) {
      set({ token, isAuthenticated: true })
    }
  },
}))
