import toast from 'react-hot-toast'
import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect on session-expired 401s — NOT on login attempts (so 2FA/wrong-pw
    // errors stay visible in the form) and not on already-being-on /login.
    const url: string = error?.config?.url || ''
    const isLoginRequest = url.includes('/auth/login')
    const onLoginPage = window.location.pathname === '/login'
    if (error.response?.status === 401 && !isLoginRequest && !onLoginPage) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    // 403 = fehlende Berechtigung (z. B. Rolle „Mitarbeiter“ darf nicht löschen).
    // Der Server begründet es im Klartext — sonst sähe der Nutzer nur die
    // generische „Fehler beim …“-Meldung des Aufrufers. Feste id = keine Flut.
    if (error.response?.status === 403) {
      const detail = error.response?.data?.detail
      if (typeof detail === 'string' && detail) {
        toast.error(detail, { id: 'forbidden', duration: 5000 })
      }
    }
    return Promise.reject(error)
  },
)
