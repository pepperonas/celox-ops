import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const login = useAuthStore((s) => s.login)
  const loading = useAuthStore((s) => s.loading)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await login(username, password)
      navigate('/')
    } catch {
      setError('Anmeldung fehlgeschlagen. Bitte prüfen Sie Ihre Zugangsdaten.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="bg-surface border border-border rounded-[16px] p-12 w-full max-w-[400px] text-center">
        <div className="w-12 h-12 bg-accent rounded-[12px] inline-flex items-center justify-center text-2xl font-bold text-white mb-6">
          C
        </div>
        <h1 className="text-xl font-semibold text-text mb-2">celox ops</h1>
        <p className="text-text-muted text-sm mb-8">Verwaltungssystem</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="text-left">
            <label htmlFor="username" className="block text-xs uppercase tracking-wider text-text-muted mb-1.5">
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
            />
          </div>

          <div className="text-left">
            <label htmlFor="password" className="block text-xs uppercase tracking-wider text-text-muted mb-1.5">
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
            />
          </div>

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
      </div>
    </div>
  )
}
