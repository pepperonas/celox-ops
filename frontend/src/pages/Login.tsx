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
          // Der echte GIS-Button liegt unsichtbar über dem eigenen MD3-Button
          // (Klicks treffen Google, Optik bleibt App-nativ).
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
          {/* Eigener MD3-Button; der echte GIS-Button liegt (fast) unsichtbar
              darüber und empfängt die Klicks — Flow bleibt 100 % Google. */}
          <div className="group relative h-11 rounded-full overflow-hidden">
            <div
              aria-hidden
              className="absolute inset-0 flex items-center justify-center gap-3 rounded-full border border-border bg-surface-container text-text text-sm font-medium transition-all duration-short group-hover:border-accent group-hover:bg-accent/10 group-hover:shadow-elev-1 pointer-events-none"
            >
              <svg className="w-[18px] h-[18px]" viewBox="0 0 48 48">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
              </svg>
              Mit Google anmelden
            </div>
            <div ref={googleBtnRef} className="absolute inset-0 flex justify-center opacity-[0.02]" />
          </div>
        </div>
      </div>
    </div>
  )
}
