import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import PageHeader from '../../components/PageHeader'
import FormField from '../../components/FormField'
import LoadingIndicator from '../../components/LoadingIndicator'
import DeleteDialog from '../../components/DeleteDialog'
import RainmakerNav from './RainmakerNav'
import RainmakerFooter from './RainmakerFooter'
import {
  getRainmakerSettings, updateRainmakerSettings,
  getRainmakerTemplates, createRainmakerTemplate, updateRainmakerTemplate, deleteRainmakerTemplate,
} from '../../api/rainmaker'
import type {
  RainmakerSettings, RainmakerReminderChannel,
  RainmakerTemplate, RainmakerTemplateChannel,
} from '../../types'

const CHANNEL_OPTIONS = [
  { value: 'email', label: 'E-Mail' },
  { value: 'telegram', label: 'Telegram' },
  { value: 'push', label: 'Push' },
]
const TPL_CHANNEL_OPTIONS = [
  { value: 'email', label: 'E-Mail' },
  { value: 'message', label: 'Nachricht' },
]

const emptyTpl = { channel: 'email' as RainmakerTemplateChannel, name: '', subject: '', body: '' }

export default function RainmakerSettingsPage() {
  const [settings, setSettings] = useState<RainmakerSettings | null>(null)
  const [templates, setTemplates] = useState<RainmakerTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [savingSettings, setSavingSettings] = useState(false)
  const [tplForm, setTplForm] = useState<{ id?: string; channel: RainmakerTemplateChannel; name: string; subject: string; body: string }>(emptyTpl)
  const [savingTpl, setSavingTpl] = useState(false)
  const [deleteTplId, setDeleteTplId] = useState<string | null>(null)

  const loadTemplates = () => getRainmakerTemplates().then(setTemplates).catch(() => {})

  useEffect(() => {
    Promise.all([getRainmakerSettings(), getRainmakerTemplates()])
      .then(([s, t]) => { setSettings(s); setTemplates(t) })
      .catch(() => toast.error('Einstellungen konnten nicht geladen werden.'))
      .finally(() => setLoading(false))
  }, [])

  const saveSettings = async () => {
    if (!settings) return
    setSavingSettings(true)
    try {
      const saved = await updateRainmakerSettings({
        daily_quota: settings.daily_quota,
        reminder_enabled: settings.reminder_enabled,
        reminder_time: settings.reminder_time.length === 5 ? settings.reminder_time + ':00' : settings.reminder_time,
        reminder_channel: settings.reminder_channel,
      })
      setSettings(saved)
      toast.success('Einstellungen gespeichert.')
    } catch {
      toast.error('Speichern fehlgeschlagen.')
    }
    setSavingSettings(false)
  }

  const saveTpl = async () => {
    if (!tplForm.name || !tplForm.body) { toast.error('Name und Inhalt sind erforderlich.'); return }
    setSavingTpl(true)
    try {
      const payload = { channel: tplForm.channel, name: tplForm.name, subject: tplForm.subject || null, body: tplForm.body }
      if (tplForm.id) await updateRainmakerTemplate(tplForm.id, payload)
      else await createRainmakerTemplate(payload)
      toast.success(tplForm.id ? 'Vorlage aktualisiert.' : 'Vorlage erstellt.')
      setTplForm(emptyTpl)
      loadTemplates()
    } catch {
      toast.error('Speichern fehlgeschlagen.')
    }
    setSavingTpl(false)
  }

  const handleDeleteTpl = async () => {
    if (!deleteTplId) return
    try {
      await deleteRainmakerTemplate(deleteTplId)
      setDeleteTplId(null)
      if (tplForm.id === deleteTplId) setTplForm(emptyTpl)
      loadTemplates()
    } catch {
      toast.error('Löschen fehlgeschlagen.')
    }
  }

  if (loading || !settings) {
    return <div><PageHeader title="Einstellungen" /><RainmakerNav /><LoadingIndicator /></div>
  }

  return (
    <div className="max-w-3xl">
      <PageHeader title="Einstellungen" />
      <RainmakerNav />

      {/* Pensum & Reminder */}
      <div className="bg-surface-container border border-border rounded-card p-6 mb-6 space-y-5">
        <h3 className="text-sm font-semibold text-text">Pensum &amp; Erinnerung</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-text-muted mb-2">Tägliches Pensum (Aktionen)</label>
            <input type="number" min="1" max="50" value={settings.daily_quota}
              onChange={(e) => setSettings({ ...settings, daily_quota: Number(e.target.value) })} className="w-full" />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-2">Erinnerungszeit</label>
            <input type="time" value={settings.reminder_time.slice(0, 5)}
              onChange={(e) => setSettings({ ...settings, reminder_time: e.target.value })} className="w-full" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
          <FormField label="Erinnerungs-Kanal" name="reminder_channel" type="select"
            value={settings.reminder_channel}
            onChange={(e) => setSettings({ ...settings, reminder_channel: e.target.value as RainmakerReminderChannel })}
            options={CHANNEL_OPTIONS} />
          <FormField label="Erinnerung aktiv" name="reminder_enabled" type="checkbox"
            value={settings.reminder_enabled}
            onChange={(e) => setSettings({ ...settings, reminder_enabled: (e.target as HTMLInputElement).checked })} />
        </div>
        <p className="text-xs text-text-muted">Aktuell ist nur der Kanal „E-Mail" aktiv (via konfiguriertem SMTP).</p>
        <div className="flex justify-end">
          <button onClick={saveSettings} disabled={savingSettings} className="btn-primary">
            {savingSettings ? 'Speichern…' : 'Speichern'}
          </button>
        </div>
      </div>

      {/* Templates */}
      <div className="bg-surface-container border border-border rounded-card p-6 space-y-5">
        <h3 className="text-sm font-semibold text-text">Vorlagen</h3>

        {templates.length > 0 && (
          <div className="space-y-2">
            {templates.map((t) => (
              <div key={t.id} className="flex items-center gap-3 p-3 rounded-lg bg-surface-high">
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent/15 text-accent shrink-0">{t.channel === 'email' ? 'E-Mail' : 'Nachricht'}</span>
                <span className="text-sm text-text flex-1 truncate">{t.name}</span>
                <button onClick={() => setTplForm({ id: t.id, channel: t.channel, name: t.name, subject: t.subject || '', body: t.body })} className="md-state text-xs text-text-muted hover:text-accent px-2 py-1 rounded-full">Bearbeiten</button>
                <button onClick={() => setDeleteTplId(t.id)} className="md-state text-xs text-text-muted hover:text-danger px-2 py-1 rounded-full">Löschen</button>
              </div>
            ))}
          </div>
        )}

        {/* Editor */}
        <div className="border-t border-border pt-5 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-text">{tplForm.id ? 'Vorlage bearbeiten' : 'Neue Vorlage'}</p>
            {tplForm.id && <button onClick={() => setTplForm(emptyTpl)} className="text-xs text-text-muted hover:text-text">+ Neue stattdessen</button>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Kanal" name="tpl_channel" type="select" value={tplForm.channel}
              onChange={(e) => setTplForm({ ...tplForm, channel: e.target.value as RainmakerTemplateChannel })} options={TPL_CHANNEL_OPTIONS} />
            <div>
              <label className="block text-xs text-text-muted mb-2">Name</label>
              <input type="text" value={tplForm.name} onChange={(e) => setTplForm({ ...tplForm, name: e.target.value })} className="w-full" placeholder="z. B. Erstkontakt Kaltakquise" />
            </div>
          </div>
          {tplForm.channel === 'email' && (
            <div>
              <label className="block text-xs text-text-muted mb-2">Betreff</label>
              <input type="text" value={tplForm.subject} onChange={(e) => setTplForm({ ...tplForm, subject: e.target.value })} className="w-full" placeholder="Betreff mit {company}" />
            </div>
          )}
          <div>
            <label className="block text-xs text-text-muted mb-2">Inhalt</label>
            <textarea value={tplForm.body} onChange={(e) => setTplForm({ ...tplForm, body: e.target.value })} rows={5} className="w-full" placeholder="Hallo {contact_name}, …" />
            <p className="text-[10px] text-text-muted mt-1.5">Platzhalter: {'{company}'} · {'{contact_name}'} · {'{role}'}</p>
          </div>
          <div className="flex justify-end">
            <button onClick={saveTpl} disabled={savingTpl} className="btn-primary">
              {savingTpl ? 'Speichern…' : tplForm.id ? 'Aktualisieren' : 'Vorlage anlegen'}
            </button>
          </div>
        </div>
      </div>

      <RainmakerFooter />

      <DeleteDialog
        isOpen={!!deleteTplId}
        onClose={() => setDeleteTplId(null)}
        onConfirm={handleDeleteTpl}
        title="Vorlage löschen"
        message="Diese Vorlage wirklich löschen?"
      />
    </div>
  )
}
