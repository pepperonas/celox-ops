import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { api } from '../api/client'

// Google Identity Services (GIS): der Button rendert nur, wenn das Backend
// eine GOOGLE_CLIENT_ID konfiguriert hat (auth/info liefert sie zur Laufzeit —
// kein Rebuild bei Konfig-Änderung nötig). Das ID-Token geht an /auth/google.
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (r: { credential: string }) => void }) => void
          renderButton: (el: HTMLElement, options: Record<string, unknown>) => void
        }
      }
    }
  }
}

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [totp, setTotp] = useState('')
  const [showTotp, setShowTotp] = useState(false)
  const [error, setError] = useState('')
  const login = useAuthStore((s) => s.login)
  const loginWithGoogle = useAuthStore((s) => s.loginWithGoogle)
  const loading = useAuthStore((s) => s.loading)
  const navigate = useNavigate()
  const googleBtnRef = useRef<HTMLDivElement>(null)
  const [googleReady, setGoogleReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    api.get<{ google_client_id: string | null }>('/auth/info')
      .then(({ data }) => {
        if (cancelled || !data.google_client_id) return
        const clientId = data.google_client_id
        const init = () => {
          if (cancelled || !window.google || !googleBtnRef.current) return
          window.google.accounts.id.initialize({
            client_id: clientId,
            callback: async ({ credential }) => {
              setError('')
              try {
                await loginWithGoogle(credential)
                navigate('/')
              } catch (err: unknown) {
                const e = err as { response?: { status?: number; data?: { detail?: string } } }
                setError(e?.response?.data?.detail || 'Google-Anmeldung fehlgeschlagen.')
              }
            },
          })
          window.google.accounts.id.renderButton(googleBtnRef.current, {
            theme: 'filled_black', size: 'large', width: 304, text: 'signin_with', locale: 'de',
          })
          setGoogleReady(true)
        }
        if (window.google) { init(); return }
        const script = document.createElement('script')
        script.src = 'https://accounts.google.com/gsi/client'
        script.async = true
        script.onload = init
        document.head.appendChild(script)
      })
      .catch(() => {})
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await login(username, password, totp || undefined)
      navigate('/')
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: string } } }
      const detail = e?.response?.data?.detail || ''
      const status = e?.response?.status
      console.warn('[Login] failed:', status, detail)
      if (detail.toLowerCase().includes('2fa') || detail.toLowerCase().includes('totp')) {
        setShowTotp(true)
        setError(detail || 'Bitte 2FA-Code eingeben.')
      } else if (status === 429) {
        setError('Zu viele Login-Versuche. Bitte 1 Minute warten.')
      } else if (status === 401) {
        setError('Benutzername oder Passwort falsch.')
      } else {
        setError(detail || `Fehler ${status || ''}: Anmeldung fehlgeschlagen.`)
      }
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="bg-surface-high rounded-xl shadow-elev-3 p-12 w-full max-w-[400px] text-center animate-md-scale">
        <div className="w-16 h-16 bg-md-primary rounded-lg inline-flex items-center justify-center text-3xl font-bold text-on-primary mb-6 shadow-elev-1 animate-md-pop">
          C
        </div>
        <h1 className="text-2xl font-semibold text-text mb-2">celox ops</h1>
        <p className="text-text-muted text-sm mb-8">Verwaltungssystem</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="text-left">
            <label htmlFor="username" className="block text-xs text-text-muted mb-1.5">
              Benutzername
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Benutzername eingeben"
              className="input-field w-full"
              required
              autoFocus
              autoComplete="username"
            />
          </div>

          <div className="text-left">
            <label htmlFor="password" className="block text-xs text-text-muted mb-1.5">
              Passwort
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Passwort eingeben"
              className="input-field w-full"
              required
              autoComplete="current-password"
            />
          </div>

          {showTotp && (
            <div className="text-left">
              <label htmlFor="totp" className="block text-xs text-text-muted mb-1.5">
                2FA-Code
              </label>
              <input
                id="totp"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={totp}
                onChange={(e) => setTotp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="6-stelliger Code aus Authenticator"
                className="input-field w-full font-mono tracking-wider"
                maxLength={6}
                autoFocus
                autoComplete="one-time-code"
              />
            </div>
          )}

          {error && (
            <p className="text-danger text-xs mt-2">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-2.5"
          >
            {loading ? 'Anmelden...' : 'Anmelden'}
          </button>
        </form>

        {/* Google-Login (nur wenn serverseitig konfiguriert) */}
        <div className={googleReady ? 'mt-6' : 'hidden'}>
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-px bg-border" />
            <span className="text-[11px] text-text-muted">oder</span>
            <div className="flex-1 h-px bg-border" />
          </div>
          <div ref={googleBtnRef} className="flex justify-center" />
        </div>
      </div>
    </div>
  )
}
