import { useEffect } from 'react'
import { useAuthStore } from '../store/authStore'

export function useAuth() {
  const { token, isAuthenticated, loading, error, login, logout, initialize } =
    useAuthStore()

  useEffect(() => {
    initialize()
  }, [initialize])

  return { token, isAuthenticated, loading, error, login, logout }
}
