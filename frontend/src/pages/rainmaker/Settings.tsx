import Toggle from '../../components/Toggle'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import PageHeader from '../../components/PageHeader'
import FormField from '../../components/FormField'
import LoadingIndicator from '../../components/LoadingIndicator'
import DeleteDialog from '../../components/DeleteDialog'
import RainmakerNav from './RainmakerNav'
import {
  getRainmakerSettings, updateRainmakerSettings,
  getRainmakerTemplates, createRainmakerTemplate, updateRainmakerTemplate, deleteRainmakerTemplate,
  getRainmakerGoals, seedRainmakerGoals, createRainmakerGoal, updateRainmakerGoal, deleteRainmakerGoal,
} from '../../api/rainmaker'
import type {
  RainmakerSettings, RainmakerReminderChannel,
  RainmakerTemplate, RainmakerTemplateChannel,
  RainmakerGoal, RainmakerActivityType,
} from '../../types'
import { ACTIVITY_TYPE_LABELS } from './constants'

const TYPE_OPTIONS = (Object.keys(ACTIVITY_TYPE_LABELS) as RainmakerActivityType[]).map((v) => ({ value: v, label: ACTIVITY_TYPE_LABELS[v] }))

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
const emptyGoal = { name: '', suggested_type: 'call' as RainmakerActivityType, daily_target: 3 }

export default function RainmakerSettingsPage() {
  const [settings, setSettings] = useState<RainmakerSettings | null>(null)
  const [templates, setTemplates] = useState<RainmakerTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [savingSettings, setSavingSettings] = useState(false)
  const [tplForm, setTplForm] = useState<{ id?: string; channel: RainmakerTemplateChannel; name: string; subject: string; body: string }>(emptyTpl)
  const [savingTpl, setSavingTpl] = useState(false)
  const [deleteTplId, setDeleteTplId] = useState<string | null>(null)
  const [goals, setGoals] = useState<RainmakerGoal[]>([])
  const [goalForm, setGoalForm] = useState<{ id?: string; name: string; suggested_type: RainmakerActivityType; daily_target: number }>(emptyGoal)
  const [savingGoal, setSavingGoal] = useState(false)
  const [deleteGoalId, setDeleteGoalId] = useState<string | null>(null)

  const loadTemplates = () => getRainmakerTemplates().then(setTemplates).catch(() => {})
  const loadGoals = () => getRainmakerGoals().then(setGoals).catch(() => {})

  useEffect(() => {
    Promise.all([getRainmakerSettings(), getRainmakerTemplates(), getRainmakerGoals()])
      .then(([s, t, g]) => { setSettings(s); setTemplates(t); setGoals(g) })
      .catch(() => toast.error('Einstellungen konnten nicht geladen werden.'))
      .finally(() => setLoading(false))
  }, [])

  const handleSeedGoals = async () => {
    try { setGoals(await seedRainmakerGoals()); toast.success('Default-Ziele angelegt.') }
    catch { toast.error('Konnte nicht anlegen.') }
  }

  const saveGoal = async () => {
    if (!goalForm.name) { toast.error('Name ist erforderlich.'); return }
    setSavingGoal(true)
    try {
      const payload = { name: goalForm.name, suggested_type: goalForm.suggested_type, daily_target: goalForm.daily_target }
      if (goalForm.id) await updateRainmakerGoal(goalForm.id, payload)
      else await createRainmakerGoal(payload)
      toast.success(goalForm.id ? 'Ziel aktualisiert.' : 'Ziel erstellt.')
      setGoalForm(emptyGoal)
      loadGoals()
    } catch { toast.error('Speichern fehlgeschlagen.') }
    setSavingGoal(false)
  }

  const toggleGoalActive = async (g: RainmakerGoal) => {
    try { await updateRainmakerGoal(g.id, { active: !g.active }); loadGoals() }
    catch { toast.error('Konnte nicht ändern.') }
  }

  const handleDeleteGoal = async () => {
    if (!deleteGoalId) return
    try {
      await deleteRainmakerGoal(deleteGoalId)
      setDeleteGoalId(null)
      if (goalForm.id === deleteGoalId) setGoalForm(emptyGoal)
      loadGoals()
    } catch { toast.error('Löschen fehlgeschlagen.') }
  }

  const saveSettings = async () => {
    if (!settings) return
    setSavingSettings(true)
    try {
      const saved = await updateRainmakerSettings({
        daily_quota: settings.daily_quota,
        reminder_enabled: settings.reminder_enabled,
        reminder_time: settings.reminder_time.length === 5 ? settings.reminder_time + ':00' : settings.reminder_time,
        reminder_channel: settings.reminder_channel,
        freezes_per_month: settings.freezes_per_month,
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
          <div>
            <label className="block text-xs text-text-muted mb-2">Freeze-Tage / Monat</label>
            <input type="number" min="0" max="15" value={settings.freezes_per_month}
              onChange={(e) => setSettings({ ...settings, freezes_per_month: Number(e.target.value) })} className="w-full" />
          </div>
        </div>
        <p className="text-xs text-text-muted">Der Streak zählt nur Werktage (Mo–Fr) — Wochenenden brechen ihn nicht. Freeze-Tage puffern verpasste Werktage (Urlaub/krank), bevor er zurückgesetzt wird.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
          <FormField label="Erinnerungs-Kanal" name="reminder_channel" type="select"
            value={settings.reminder_channel}
            onChange={(e) => setSettings({ ...settings, reminder_channel: e.target.value as RainmakerReminderChannel })}
            options={CHANNEL_OPTIONS} />
          <div className="pb-1">
            <Toggle
              checked={settings.reminder_enabled}
              onChange={(v) => setSettings({ ...settings, reminder_enabled: v })}
              label="Tägliche Erinnerungs-Mail"
              hint={settings.reminder_enabled
                ? `Wird an Werktagen um ${settings.reminder_time.slice(0, 5)} Uhr gesendet, wenn das Pensum noch offen ist.`
                : 'Aus — es werden keine Erinnerungen verschickt.'}
            />
          </div>
        </div>
        <p className="text-xs text-text-muted">Aktuell ist nur der Kanal „E-Mail" aktiv (via konfiguriertem SMTP).</p>
        <div className="flex justify-end">
          <button onClick={saveSettings} disabled={savingSettings} className="btn-primary">
            {savingSettings ? 'Speichern…' : 'Speichern'}
          </button>
        </div>
      </div>

      {/* Goals */}
      <div className="bg-surface-container border border-border rounded-card p-6 mb-6 space-y-5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text">Akquise-Ziele</h3>
          {goals.length === 0 && (
            <button onClick={handleSeedGoals} className="btn-secondary text-xs !py-1.5 !px-4">Default-Ziele anlegen</button>
          )}
        </div>

        {goals.length > 0 && (
          <div className="space-y-2">
            {goals.map((g) => (
              <div key={g.id} className={`flex items-center gap-3 p-3 rounded-lg bg-surface-high ${!g.active ? 'opacity-50' : ''}`}>
                <span className="text-sm text-text flex-1 truncate">{g.name}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent/15 text-accent shrink-0">{ACTIVITY_TYPE_LABELS[g.suggested_type]}</span>
                <span className="text-xs text-text-muted tabular-nums shrink-0">{g.daily_target}/Tag</span>
                <button onClick={() => toggleGoalActive(g)} className="md-state text-xs text-text-muted hover:text-text px-2 py-1 rounded-full" title={g.active ? 'Deaktivieren' : 'Aktivieren'}>{g.active ? 'Aktiv' : 'Inaktiv'}</button>
                <button onClick={() => setGoalForm({ id: g.id, name: g.name, suggested_type: g.suggested_type, daily_target: g.daily_target })} className="md-state text-xs text-text-muted hover:text-accent px-2 py-1 rounded-full">Bearbeiten</button>
                <button onClick={() => setDeleteGoalId(g.id)} className="md-state text-xs text-text-muted hover:text-danger px-2 py-1 rounded-full">Löschen</button>
              </div>
            ))}
          </div>
        )}

        <div className="border-t border-border pt-5 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-text">{goalForm.id ? 'Ziel bearbeiten' : 'Neues Ziel'}</p>
            {goalForm.id && <button onClick={() => setGoalForm(emptyGoal)} className="text-xs text-text-muted hover:text-text">+ Neues stattdessen</button>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-1">
              <label className="block text-xs text-text-muted mb-2">Name</label>
              <input type="text" value={goalForm.name} onChange={(e) => setGoalForm({ ...goalForm, name: e.target.value })} className="w-full" placeholder="z. B. Neukunden Telefon-Akquise" />
            </div>
            <FormField label="Vorgeschlagener Typ" name="goal_type" type="select" value={goalForm.suggested_type}
              onChange={(e) => setGoalForm({ ...goalForm, suggested_type: e.target.value as RainmakerActivityType })} options={TYPE_OPTIONS} />
            <div>
              <label className="block text-xs text-text-muted mb-2">Tagesziel</label>
              <input type="number" min="1" max="50" value={goalForm.daily_target} onChange={(e) => setGoalForm({ ...goalForm, daily_target: Number(e.target.value) })} className="w-full" />
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={saveGoal} disabled={savingGoal} className="btn-primary">
              {savingGoal ? 'Speichern…' : goalForm.id ? 'Aktualisieren' : 'Ziel anlegen'}
            </button>
          </div>
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


      <DeleteDialog
        isOpen={!!deleteTplId}
        onClose={() => setDeleteTplId(null)}
        onConfirm={handleDeleteTpl}
        title="Vorlage löschen"
        message="Diese Vorlage wirklich löschen?"
      />
      <DeleteDialog
        isOpen={!!deleteGoalId}
        onClose={() => setDeleteGoalId(null)}
        onConfirm={handleDeleteGoal}
        title="Ziel löschen"
        message="Dieses Akquise-Ziel wirklich löschen? Verknüpfte Aktivitäten bleiben erhalten (ohne Ziel)."
      />
    </div>
  )
}
