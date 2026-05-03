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
    return Promise.reject(error)
  },
)
