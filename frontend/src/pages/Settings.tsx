import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import {
  getEmailTemplates,
  createEmailTemplate,
  updateEmailTemplate,
  deleteEmailTemplate,
  seedEmailTemplates,
} from '../api/emailTemplates'
import type { EmailTemplate, EmailTemplateCreate } from '../types'

interface TrackerConfig {
  base_url: string
  connected: boolean
  projects_count: number
  shares_count: number
}

const TEMPLATE_CATEGORIES = [
  { value: 'rechnung', label: 'Rechnung' },
  { value: 'angebot', label: 'Angebot' },
  { value: 'mahnung', label: 'Mahnung' },
  { value: 'akquise', label: 'Akquise' },
  { value: 'allgemein', label: 'Allgemein' },
]

export default function Settings() {
  const [config, setConfig] = useState<TrackerConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(true)
  const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | null>(null)
  const [showTemplateForm, setShowTemplateForm] = useState(false)
  const [templateForm, setTemplateForm] = useState<EmailTemplateCreate>({
    name: '',
    subject: '',
    body: '',
    category: 'allgemein',
  })

  useEffect(() => {
    loadConfig()
    loadTemplates()
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

  const loadTemplates = async () => {
    setTemplatesLoading(true)
    try {
      const data = await getEmailTemplates()
      setTemplates(data)
    } catch {
      // ignore
    }
    setTemplatesLoading(false)
  }

  const handleSeedTemplates = async () => {
    try {
      const data = await seedEmailTemplates()
      setTemplates(data)
      toast.success('Standard-Vorlagen wurden erstellt.')
    } catch {
      toast.error('Vorlagen existieren bereits oder Fehler beim Erstellen.')
    }
  }

  const handleSaveTemplate = async () => {
    try {
      if (editingTemplate) {
        await updateEmailTemplate(editingTemplate.id, templateForm)
        toast.success('Vorlage aktualisiert.')
      } else {
        await createEmailTemplate(templateForm)
        toast.success('Vorlage erstellt.')
      }
      setShowTemplateForm(false)
      setEditingTemplate(null)
      setTemplateForm({ name: '', subject: '', body: '', category: 'allgemein' })
      await loadTemplates()
    } catch {
      toast.error('Fehler beim Speichern der Vorlage.')
    }
  }

  const handleEditTemplate = (template: EmailTemplate) => {
    setEditingTemplate(template)
    setTemplateForm({
      name: template.name,
      subject: template.subject,
      body: template.body,
      category: template.category,
    })
    setShowTemplateForm(true)
  }

  const handleDeleteTemplate = async (id: string) => {
    if (!confirm('Vorlage wirklich löschen?')) return
    try {
      await deleteEmailTemplate(id)
      toast.success('Vorlage gelöscht.')
      await loadTemplates()
    } catch {
      toast.error('Fehler beim Löschen.')
    }
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
    <div className="max-w-3xl">
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

      {/* Email Templates */}
      <div className="bg-surface border border-border rounded-[12px] p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-text">E-Mail-Vorlagen</h3>
          <div className="flex gap-2">
            {templates.length === 0 && (
              <button onClick={handleSeedTemplates} className="btn-secondary text-sm">
                Standard-Vorlagen erstellen
              </button>
            )}
            <button
              onClick={() => {
                setEditingTemplate(null)
                setTemplateForm({ name: '', subject: '', body: '', category: 'allgemein' })
                setShowTemplateForm(true)
              }}
              className="btn-primary text-sm"
            >
              Neue Vorlage
            </button>
          </div>
        </div>
        <p className="text-text-muted text-sm mb-4">
          Vorlagen werden im E-Mail-Dialog als Dropdown angezeigt. Platzhalter: <code className="text-text">{'{nr}'}</code>, <code className="text-text">{'{kunde}'}</code>, <code className="text-text">{'{betrag}'}</code>, <code className="text-text">{'{firma}'}</code>
        </p>

        {templatesLoading ? (
          <div className="text-text-muted text-sm">Laden...</div>
        ) : templates.length === 0 ? (
          <div className="text-text-muted text-sm">Keine Vorlagen vorhanden.</div>
        ) : (
          <div className="space-y-2">
            {templates.map((t) => (
              <div key={t.id} className="flex items-center justify-between bg-surface-2 rounded-lg p-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text">{t.name}</span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-accent/10 text-accent">
                      {t.category}
                    </span>
                  </div>
                  <p className="text-xs text-text-muted mt-0.5 truncate">{t.subject}</p>
                </div>
                <div className="flex gap-1 ml-3">
                  <button
                    onClick={() => handleEditTemplate(t)}
                    className="text-text-muted hover:text-text text-sm px-2 py-1"
                  >
                    Bearbeiten
                  </button>
                  <button
                    onClick={() => handleDeleteTemplate(t.id)}
                    className="text-danger hover:text-danger/80 text-sm px-2 py-1"
                  >
                    Löschen
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Template Form */}
        {showTemplateForm && (
          <div className="mt-4 pt-4 border-t border-border space-y-3">
            <h4 className="text-sm font-medium text-text">
              {editingTemplate ? 'Vorlage bearbeiten' : 'Neue Vorlage'}
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">Name</label>
                <input
                  type="text"
                  value={templateForm.name}
                  onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                  className="input w-full"
                  placeholder="z.B. Rechnung versenden"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">Kategorie</label>
                <select
                  value={templateForm.category}
                  onChange={(e) => setTemplateForm({ ...templateForm, category: e.target.value })}
                  className="input w-full"
                >
                  {TEMPLATE_CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-text-muted mb-1">Betreff</label>
              <input
                type="text"
                value={templateForm.subject}
                onChange={(e) => setTemplateForm({ ...templateForm, subject: e.target.value })}
                className="input w-full"
                placeholder="z.B. Rechnung {nr} — {firma}"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-muted mb-1">Nachricht</label>
              <textarea
                value={templateForm.body}
                onChange={(e) => setTemplateForm({ ...templateForm, body: e.target.value })}
                rows={6}
                className="input w-full resize-y"
                placeholder="Sehr geehrte Damen und Herren, ..."
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowTemplateForm(false)
                  setEditingTemplate(null)
                }}
                className="btn-secondary text-sm"
              >
                Abbrechen
              </button>
              <button
                onClick={handleSaveTemplate}
                disabled={!templateForm.name || !templateForm.subject || !templateForm.body}
                className="btn-primary text-sm"
              >
                {editingTemplate ? 'Aktualisieren' : 'Erstellen'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
