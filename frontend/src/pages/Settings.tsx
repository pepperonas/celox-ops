import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../api/client'

interface TrackerConfig {
  base_url: string
  connected: boolean
  projects_count: number
  shares_count: number
}

export default function Settings() {
  const [config, setConfig] = useState<TrackerConfig | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const [projectsRes, sharesRes] = await Promise.allSettled([
        api.get('/token-tracker/projects'),
        api.get('/token-tracker/shares'),
      ])
      setConfig({
        base_url: 'Konfiguriert',
        connected: projectsRes.status === 'fulfilled',
        projects_count: projectsRes.status === 'fulfilled' ? projectsRes.value.data.length : 0,
        shares_count: sharesRes.status === 'fulfilled' ? sharesRes.value.data.length : 0,
      })
    } catch {
      setConfig({ base_url: '', connected: false, projects_count: 0, shares_count: 0 })
    }
    setLoading(false)
  }

  const [exporting, setExporting] = useState(false)

  const handleExport = async () => {
    setExporting(true)
    try {
      const response = await api.get('/backup/export', { responseType: 'blob' })
      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      const disposition = response.headers['content-disposition'] || ''
      const match = disposition.match(/filename="(.+)"/)
      a.download = match ? match[1] : 'celox-ops-backup.json'
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Datenbank-Backup heruntergeladen.')
    } catch {
      toast.error('Fehler beim Exportieren.')
    }
    setExporting(false)
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold text-text mb-6">Einstellungen</h2>

      <div className="bg-surface border border-border rounded-[12px] p-5 mb-6">
        <h3 className="text-sm font-semibold text-text mb-4">Token Tracker Verbindung</h3>
        <p className="text-text-muted text-sm mb-4">
          Der Token Tracker liefert KI-Nutzungsdaten für die Kundenansicht.
          Die Konfiguration erfolgt über Umgebungsvariablen auf dem Server.
        </p>

        {loading ? (
          <div className="text-text-muted text-sm">Prüfe Verbindung...</div>
        ) : config?.connected ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-success inline-block"></span>
              <span className="text-sm text-success font-medium">Verbunden</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-surface-2 rounded-lg p-3">
                <p className="text-xs uppercase tracking-wider text-text-muted mb-1">Projekte</p>
                <p className="text-xl font-bold tabular-nums text-text">{config.projects_count}</p>
              </div>
              <div className="bg-surface-2 rounded-lg p-3">
                <p className="text-xs uppercase tracking-wider text-text-muted mb-1">Aktive Shares</p>
                <p className="text-xl font-bold tabular-nums text-text">{config.shares_count}</p>
              </div>
            </div>
            <div className="bg-surface-2 border border-border rounded-lg p-3 mt-3">
              <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Konfiguration</p>
              <p className="text-xs text-text-muted">
                <code className="text-text">TOKEN_TRACKER_BASE_URL</code> und <code className="text-text">TOKEN_TRACKER_ADMIN_KEY</code> sind in der <code className="text-text">.env</code> konfiguriert.
              </p>
              <p className="text-xs text-text-muted mt-2">
                Den Share Admin Key findest du im Token Tracker unter <strong>Einstellungen → Share API</strong>.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-danger inline-block"></span>
              <span className="text-sm text-danger font-medium">Nicht verbunden</span>
            </div>
            <div className="bg-surface-2 border border-border rounded-lg p-3">
              <p className="text-xs text-text-muted mb-2">So konfigurierst du die Verbindung:</p>
              <ol className="text-xs text-text-muted space-y-1 list-decimal list-inside">
                <li>Öffne den Token Tracker → Einstellungen → Share API</li>
                <li>Kopiere die <strong>Tracker URL</strong> und den <strong>Share Admin Key</strong></li>
                <li>Trage sie in die <code className="text-text">.env</code> Datei von celox ops ein:
                  <pre className="mt-1 p-2 bg-bg rounded text-[11px] text-text-muted overflow-x-auto">
{`TOKEN_TRACKER_BASE_URL=https://tracker.example.com
TOKEN_TRACKER_ADMIN_KEY=dein-key-hier`}
                  </pre>
                </li>
                <li>Starte den Backend-Container neu</li>
              </ol>
            </div>
          </div>
        )}
      </div>
      {/* Database Backup */}
      <div className="bg-surface border border-border rounded-[12px] p-5 mb-6">
        <h3 className="text-sm font-semibold text-text mb-4">Datenbank-Backup</h3>
        <p className="text-text-muted text-sm mb-4">
          Exportiert die gesamte Datenbank als JSON-Datei: Kunden, Aufträge, Verträge, Rechnungen, Leads, Zeiteinträge, Ausgaben und Aktivitäten.
        </p>
        <button onClick={handleExport} disabled={exporting} className="btn-primary">
          {exporting ? 'Exportiere...' : 'Datenbank herunterladen'}
        </button>
      </div>
    </div>
  )
}
