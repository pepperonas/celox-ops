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
import { getSettings, updateSettings } from '../api/settings'
import { getAiUsage } from '../api/rainmaker'
import { changeOwnPassword, getMyIcalToken, getMe, init2fa, enable2fa, disable2fa } from '../api/users'
import type { EmailTemplate, EmailTemplateCreate, AiUsageResponse } from '../types'

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

  const [defaultPrice, setDefaultPrice] = useState('')
  const [invoicePrefix, setInvoicePrefix] = useState('')
  const [curPw, setCurPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [icalUrl, setIcalUrl] = useState('')
  const [twofaEnabled, setTwofaEnabled] = useState<boolean | null>(null)
  const [twofaSetup, setTwofaSetup] = useState<{ secret: string; qr: string } | null>(null)
  const [twofaCode, setTwofaCode] = useState('')
  const [twofaBusy, setTwofaBusy] = useState(false)

  useEffect(() => {
    getMyIcalToken()
      .then((t) => setIcalUrl(`${window.location.origin}/api/ical?token=${t}`))
      .catch(() => {})
    getMe().then((m) => setTwofaEnabled(m.totp_enabled)).catch(() => {})
  }, [])

  const handleStart2fa = async () => {
    setTwofaBusy(true)
    try {
      const { secret, qr } = await init2fa()
      setTwofaSetup({ secret, qr })
      setTwofaCode('')
    } catch {
      toast.error('2FA-Setup konnte nicht gestartet werden.')
    }
    setTwofaBusy(false)
  }

  const handleEnable2fa = async () => {
    if (!twofaSetup) return
    setTwofaBusy(true)
    try {
      await enable2fa(twofaSetup.secret, twofaCode.trim())
      toast.success('Zwei-Faktor-Authentifizierung aktiviert.')
      setTwofaSetup(null); setTwofaCode(''); setTwofaEnabled(true)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Code ungültig.')
    }
    setTwofaBusy(false)
  }

  const handleDisable2fa = async () => {
    const code = window.prompt('Aktuellen 6-stelligen 2FA-Code zum Deaktivieren eingeben:')
    if (!code) return
    setTwofaBusy(true)
    try {
      await disable2fa(code.trim())
      toast.success('Zwei-Faktor-Authentifizierung deaktiviert.')
      setTwofaEnabled(false)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Code ungültig.')
    }
    setTwofaBusy(false)
  }
  const [savingPrice, setSavingPrice] = useState(false)
  // Google Places (Lead-Suche)
  const [placesConfigured, setPlacesConfigured] = useState(false)
  const [placesHint, setPlacesHint] = useState<string | null>(null)
  const [placesCalls, setPlacesCalls] = useState(0)
  const [placesKeyInput, setPlacesKeyInput] = useState('')
  const [placesSaving, setPlacesSaving] = useState(false)
  const [placesGuideOpen, setPlacesGuideOpen] = useState(false)
  // KI-Lead-Suche
  const [aiModel, setAiModel] = useState('claude-sonnet-5')
  const [aiBudget, setAiBudget] = useState('20')
  const [aiSaving, setAiSaving] = useState(false)
  const [aiUsage, setAiUsage] = useState<AiUsageResponse | null>(null)

  const applySettings = (s: { default_unit_price?: number; invoice_prefix?: string
    google_places_configured?: boolean; google_places_key_hint?: string | null
    google_places_calls_this_month?: number; ai_model?: string; ai_monthly_budget_eur?: number }) => {
    if (s.default_unit_price != null) setDefaultPrice(String(s.default_unit_price))
    if (s.invoice_prefix != null) setInvoicePrefix(s.invoice_prefix)
    setPlacesConfigured(Boolean(s.google_places_configured))
    setPlacesHint(s.google_places_key_hint ?? null)
    setPlacesCalls(s.google_places_calls_this_month ?? 0)
    if (s.ai_model != null) setAiModel(s.ai_model)
    if (s.ai_monthly_budget_eur != null) setAiBudget(String(s.ai_monthly_budget_eur))
  }

  const loadAiUsage = () => { getAiUsage().then(setAiUsage).catch(() => {}) }

  useEffect(() => {
    loadConfig()
    loadTemplates()
    getSettings().then(applySettings).catch(() => {})
    loadAiUsage()
  }, [])

  const handleSaveAi = async () => {
    setAiSaving(true)
    try {
      applySettings(await updateSettings({ ai_model: aiModel, ai_monthly_budget_eur: Number(aiBudget.replace(',', '.')) || 0 }))
      loadAiUsage()
      toast.success('KI-Einstellungen gespeichert.')
    } catch {
      toast.error('Speichern fehlgeschlagen.')
    }
    setAiSaving(false)
  }

  const handleSavePlacesKey = async () => {
    const key = placesKeyInput.trim()
    if (!key) { toast.error('Bitte einen API-Key eingeben.'); return }
    setPlacesSaving(true)
    try {
      applySettings(await updateSettings({ google_places_api_key: key }))
      setPlacesKeyInput('')
      toast.success('Google-Places-Key gespeichert.')
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setPlacesSaving(false)
  }

  const handleRemovePlacesKey = async () => {
    if (!window.confirm('Google-Places-Key wirklich entfernen?')) return
    setPlacesSaving(true)
    try {
      applySettings(await updateSettings({ google_places_api_key: '' }))
      toast.success('Key entfernt.')
    } catch {
      toast.error('Fehler beim Entfernen.')
    }
    setPlacesSaving(false)
  }

  const handleSavePrice = async () => {
    const value = parseFloat(defaultPrice.replace(',', '.'))
    if (!Number.isFinite(value) || value < 0) {
      toast.error('Bitte einen gültigen Preis eingeben.')
      return
    }
    const prefix = invoicePrefix.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 10)
    if (!prefix) {
      toast.error('Bitte ein gültiges Rechnungspräfix eingeben (A–Z, 0–9).')
      return
    }
    setSavingPrice(true)
    try {
      const s = await updateSettings({ default_unit_price: value, invoice_prefix: prefix })
      setDefaultPrice(String(s.default_unit_price))
      setInvoicePrefix(s.invoice_prefix)
      toast.success('Rechnungseinstellungen gespeichert.')
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setSavingPrice(false)
  }

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
      <h2 className="text-2xl font-semibold text-text tracking-tight mb-6">Einstellungen</h2>

      {/* Konto / Passwort */}
      <div className="bg-surface border border-border rounded-card p-5 mb-6">
        <h3 className="text-sm font-semibold text-text mb-4">Passwort ändern</h3>
        <form
          onSubmit={async (e) => {
            e.preventDefault()
            if (newPw.length < 8) { toast.error('Neues Passwort min. 8 Zeichen.'); return }
            setPwSaving(true)
            try {
              await changeOwnPassword(curPw, newPw)
              toast.success('Passwort geändert.')
              setCurPw(''); setNewPw('')
            } catch (err: any) {
              toast.error(err?.response?.data?.detail || 'Passwortänderung fehlgeschlagen.')
            }
            setPwSaving(false)
          }}
          className="grid gap-3 sm:grid-cols-2 sm:max-w-md"
        >
          <input type="password" autoComplete="current-password" placeholder="Aktuelles Passwort" value={curPw} onChange={(e) => setCurPw(e.target.value)} required className="w-full" />
          <input type="password" autoComplete="new-password" placeholder="Neues Passwort (min. 8)" value={newPw} onChange={(e) => setNewPw(e.target.value)} required minLength={8} className="w-full" />
          <div className="sm:col-span-2">
            <button type="submit" disabled={pwSaving} className="btn-primary">{pwSaving ? 'Speichere…' : 'Passwort ändern'}</button>
          </div>
        </form>
      </div>

      {/* Zwei-Faktor-Authentifizierung */}
      <div className="bg-surface border border-border rounded-card p-5 mb-6">
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
          <h3 className="text-sm font-semibold text-text">Zwei-Faktor-Authentifizierung (2FA)</h3>
          {twofaEnabled !== null && (
            <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${twofaEnabled ? 'bg-success/10 text-success' : 'bg-surface-2 text-text-muted'}`}>
              {twofaEnabled ? '✓ aktiv' : 'inaktiv'}
            </span>
          )}
        </div>
        <p className="text-text-muted text-sm mb-4">
          Zusätzlicher Schutz per Authenticator-App (TOTP) beim Login.
        </p>
        {twofaEnabled ? (
          <button onClick={handleDisable2fa} disabled={twofaBusy} className="btn-danger">2FA deaktivieren</button>
        ) : twofaSetup ? (
          <div className="space-y-3">
            <p className="text-sm text-text">1. QR-Code in deiner Authenticator-App scannen:</p>
            <img src={twofaSetup.qr} alt="2FA QR-Code" width={160} height={160} className="rounded-lg bg-white p-2" />
            <p className="text-xs text-text-muted">Oder Schlüssel manuell eingeben: <code className="text-text font-mono break-all">{twofaSetup.secret}</code></p>
            <p className="text-sm text-text">2. Aktuellen 6-stelligen Code bestätigen:</p>
            <div className="flex items-center gap-2 flex-wrap">
              <input value={twofaCode} onChange={(e) => setTwofaCode(e.target.value.replace(/\D/g, '').slice(0, 6))} inputMode="numeric" placeholder="123456" className="w-32 font-mono !text-base tracking-widest" />
              <button onClick={handleEnable2fa} disabled={twofaBusy || twofaCode.length < 6} className="btn-primary">Aktivieren</button>
              <button onClick={() => { setTwofaSetup(null); setTwofaCode('') }} className="btn-secondary text-sm">Abbrechen</button>
            </div>
          </div>
        ) : (
          <button onClick={handleStart2fa} disabled={twofaBusy} className="btn-primary">2FA aktivieren</button>
        )}
      </div>

      {/* Kalender-Abo (iCal) */}
      {icalUrl && (
        <div className="bg-surface border border-border rounded-card p-5 mb-6">
          <h3 className="text-sm font-semibold text-text mb-2">Kalender-Abo (iCal)</h3>
          <p className="text-text-muted text-sm mb-3">
            Persönlicher Feed mit deinen Rechnungsfristen und Vertragsterminen — in Apple/Google Kalender abonnieren.
            Der Link ist geheim und zeigt nur <strong>deine</strong> Daten.
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <input readOnly value={icalUrl} onClick={(e) => (e.target as HTMLInputElement).select()} className="flex-1 min-w-0 !text-xs font-mono" />
            <button
              onClick={() => { navigator.clipboard.writeText(icalUrl); toast.success('Link kopiert.') }}
              className="btn-secondary text-sm shrink-0"
            >
              Kopieren
            </button>
          </div>
        </div>
      )}

      {/* Rechnungen */}
      <div className="bg-surface border border-border rounded-card p-5 mb-6">
        <h3 className="text-sm font-semibold text-text mb-4">Rechnungen</h3>
        <p className="text-text-muted text-sm mb-4">
          Standard-Einzelpreis für neue Rechnungspositionen. Wird beim Anlegen einer Rechnung
          automatisch vorbelegt (auch als Stundensatz beim KI-Import) und bleibt überschreibbar.
        </p>
        <div className="flex items-end gap-3 flex-wrap">
          <div>
            <label htmlFor="default-price" className="block text-xs text-text-muted mb-2">
              Standard-Einzelpreis (€)
            </label>
            <input
              id="default-price"
              type="text"
              inputMode="decimal"
              value={defaultPrice}
              onChange={(e) => setDefaultPrice(e.target.value)}
              placeholder="z.B. 95"
              className="w-40"
            />
          </div>
          <div>
            <label htmlFor="invoice-prefix" className="block text-xs text-text-muted mb-2">
              Rechnungspräfix
            </label>
            <input
              id="invoice-prefix"
              type="text"
              value={invoicePrefix}
              onChange={(e) => setInvoicePrefix(e.target.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 10))}
              placeholder="CO"
              className="w-28 font-mono uppercase"
            />
            <p className="text-[11px] text-text-muted mt-1">→ {invoicePrefix || 'CO'}-{new Date().getFullYear()}-0001</p>
          </div>
          <button onClick={handleSavePrice} disabled={savingPrice} className="btn-primary">
            {savingPrice ? 'Speichere...' : 'Speichern'}
          </button>
        </div>
      </div>

      {/* Google Places (Lead-Suche) */}
      <div className="bg-surface border border-border rounded-card p-5 mb-6">
        <h3 className="text-sm font-semibold text-text mb-1">Google Places (Lead-Suche)</h3>
        <p className="text-text-muted text-sm mb-4">
          Optional. Mit einem Google-Places-API-Key findet die Lead-Suche (Rainmaker → Pipeline →
          „Leads finden") zusätzlich zu OpenStreetMap auch über Google. Ohne Key läuft die Suche
          weiterhin kostenlos über OpenStreetMap.
        </p>

        {/* Status */}
        <div className="flex items-center gap-2 mb-4">
          <span className={`w-2.5 h-2.5 rounded-full inline-block ${placesConfigured ? 'bg-success' : 'bg-text-muted'}`}></span>
          <span className="text-sm">
            {placesConfigured
              ? <>Key hinterlegt <span className="text-text-muted font-mono">({placesHint})</span></>
              : <span className="text-text-muted">Kein Key hinterlegt</span>}
          </span>
          {placesConfigured && (
            <button onClick={handleRemovePlacesKey} disabled={placesSaving}
                    className="ml-2 text-xs text-danger hover:underline">entfernen</button>
          )}
        </div>

        {/* Eingabe */}
        <div className="flex items-end gap-3 flex-wrap mb-4">
          <div className="flex-1 min-w-[260px]">
            <label htmlFor="places-key" className="block text-xs text-text-muted mb-2">
              {placesConfigured ? 'Neuen Key eintragen (ersetzt den bestehenden)' : 'API-Key'}
            </label>
            <input
              id="places-key"
              type="password"
              autoComplete="off"
              value={placesKeyInput}
              onChange={(e) => setPlacesKeyInput(e.target.value)}
              placeholder="AIza…"
              className="w-full font-mono"
            />
          </div>
          <button onClick={handleSavePlacesKey} disabled={placesSaving || !placesKeyInput.trim()} className="btn-primary">
            {placesSaving ? 'Speichere…' : 'Key speichern'}
          </button>
        </div>

        {/* Nutzung */}
        <div className="rounded-lg bg-surface-container border border-border p-3 mb-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-text-muted">Von ops ausgelöste Places-Suchen diesen Monat</span>
            <span className="text-text font-semibold tabular-nums">{placesCalls}</span>
          </div>
          <p className="text-[11px] text-text-muted mt-1.5">
            Das ist der Zähler von ops. Das echte Restkontingent und die Kosten siehst du in der{' '}
            <a href="https://console.cloud.google.com/apis/api/places-backend.googleapis.com/quotas"
               target="_blank" rel="noreferrer" className="text-accent underline underline-offset-2">
              Google Cloud Console → Places API → Kontingente</a> bzw. unter{' '}
            <a href="https://console.cloud.google.com/billing" target="_blank" rel="noreferrer"
               className="text-accent underline underline-offset-2">Abrechnung</a>.
          </p>
        </div>

        {/* Anleitung */}
        <button onClick={() => setPlacesGuideOpen((o) => !o)}
                className="text-sm text-accent hover:underline underline-offset-2">
          {placesGuideOpen ? '▾ Anleitung ausblenden' : '▸ Wie erstelle ich einen Key?'}
        </button>
        {placesGuideOpen && (
          <div className="mt-3 text-sm text-text-muted space-y-2 border-l-2 border-border pl-4">
            <ol className="list-decimal list-inside space-y-1.5">
              <li><a href="https://console.cloud.google.com/" target="_blank" rel="noreferrer" className="text-accent underline underline-offset-2">Google Cloud Console</a> öffnen und ein Projekt anlegen (oder auswählen).</li>
              <li>Ein <strong>Rechnungskonto verknüpfen</strong> (Places verlangt das, auch im kostenlosen Kontingent).</li>
              <li>Unter <em>APIs &amp; Dienste → Bibliothek</em> die <strong>„Places API"</strong> aktivieren.</li>
              <li>Unter <em>APIs &amp; Dienste → Anmeldedaten → Anmeldedaten erstellen → API-Schlüssel</em> einen Key erzeugen.</li>
              <li>Den Key hier oben einfügen und speichern.</li>
            </ol>
            <p className="font-medium text-text pt-1">Worauf du achten solltest:</p>
            <ul className="list-disc list-inside space-y-1">
              <li><strong>Key einschränken</strong> (Anmeldedaten → Key → „API-Einschränkungen"): nur die <em>Places API</em> zulassen — begrenzt den Schaden, falls der Key mal abhandenkommt.</li>
              <li><strong>Budget-Alarm setzen</strong> (Abrechnung → Budgets): z. B. 10 €/Monat mit E-Mail-Benachrichtigung, damit keine Überraschungen entstehen.</li>
              <li><strong>Key geheim halten</strong> — nicht in E-Mails/Screenshots teilen. ops zeigt ihn nur maskiert und gibt ihn nie im Klartext zurück.</li>
            </ul>
          </div>
        )}
      </div>

      {/* KI-Lead-Suche */}
      <div className="bg-surface border border-border rounded-card p-5 mb-6">
        <h3 className="text-sm font-semibold text-text mb-1">✨ KI-Lead-Suche</h3>
        <p className="text-text-muted text-sm mb-4">
          Freitext-Brief → Claude recherchiert, verifiziert (Website + E-Mail) und rankt Leads
          (Rainmaker → Pipeline → „✨ KI-Leads"). Der Anthropic-API-Key liegt server-seitig in der
          <span className="font-mono"> .env</span>.
        </p>

        {/* Status */}
        <div className="flex items-center gap-2 mb-4">
          <span className={`w-2.5 h-2.5 rounded-full inline-block ${aiUsage?.configured ? 'bg-success' : 'bg-text-muted'}`}></span>
          <span className="text-sm">
            {aiUsage?.configured
              ? <>Aktiv <span className="text-text-muted">(Modell {aiModel.replace('claude-', '')})</span></>
              : <span className="text-text-muted">ANTHROPIC_API_KEY fehlt in der .env — Feature deaktiviert</span>}
          </span>
        </div>

        {/* Modell + Budget */}
        <div className="flex items-end gap-3 flex-wrap mb-4">
          <div>
            <label htmlFor="ai-model" className="block text-xs text-text-muted mb-2">Modell</label>
            <select id="ai-model" value={aiModel} onChange={(e) => setAiModel(e.target.value)}
                    className="bg-surface-container border border-border rounded-lg px-3 py-2 text-sm">
              <option value="claude-sonnet-5">Sonnet (empfohlen)</option>
              <option value="claude-haiku-4-5">Haiku (günstiger)</option>
              <option value="claude-opus-4-8">Opus (teurer)</option>
            </select>
          </div>
          <div>
            <label htmlFor="ai-budget" className="block text-xs text-text-muted mb-2">Monatsbudget (€)</label>
            <input id="ai-budget" type="number" min={0} step="1" value={aiBudget}
                   onChange={(e) => setAiBudget(e.target.value)} className="w-28" />
          </div>
          <button onClick={handleSaveAi} disabled={aiSaving} className="btn-primary">
            {aiSaving ? 'Speichere…' : 'Speichern'}
          </button>
        </div>

        {/* Kosten-Übersicht */}
        {aiUsage && (
          <div className="rounded-lg bg-surface-container border border-border p-3 text-sm">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-text-muted">Verbraucht diesen Monat</span>
              <span className="text-text font-semibold tabular-nums">
                {aiUsage.budget.spent_eur.toFixed(2)} € / {aiUsage.budget.budget_eur.toFixed(2)} €
              </span>
            </div>
            <div className="h-2 rounded-full bg-surface-high overflow-hidden mb-2">
              <div className={`h-full ${aiUsage.budget.warn ? 'bg-warning' : 'bg-accent'}`}
                   style={{ width: `${aiUsage.budget.budget_eur > 0 ? Math.min(100, (aiUsage.budget.spent_eur / aiUsage.budget.budget_eur) * 100) : 0}%` }} />
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-[11px] text-text-muted">
              <span>{aiUsage.runs_this_month} Läufe</span>
              <span>Ø {aiUsage.avg_cost_eur.toFixed(3)} €/Lauf</span>
              <span>${aiUsage.spent_usd.toFixed(2)} (Basis USD)</span>
              <span title="Preise werden dynamisch aus einer gepflegten Tabelle geladen; „Fallback“ = hinterlegte Konstanten.">
                Preise: {aiUsage.pricing_source === 'live' ? <span className="text-success">live ✓</span> : 'Fallback'}
              </span>
              {aiUsage.budget.warn && <span className="text-warning">⚠ Budget zu ≥80 % verbraucht</span>}
            </div>
            {aiUsage.recent.length > 0 && (
              <div className="mt-3 border-t border-border pt-2 space-y-1">
                {aiUsage.recent.slice(0, 5).map((r) => (
                  <div key={r.id} className="flex items-center justify-between text-[11px] text-text-muted">
                    <span className="truncate max-w-[60%]" title={r.brief}>{r.brief}</span>
                    <span className="tabular-nums">{r.candidates_found} Treffer · {r.cost_eur.toFixed(3)} €</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="bg-surface border border-border rounded-card p-5 mb-6">
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
                <p className="text-xs text-text-muted mb-1">Projekte</p>
                <p className="text-xl font-bold tabular-nums text-text">{config.projects_count}</p>
              </div>
              <div className="bg-surface-2 rounded-lg p-3">
                <p className="text-xs text-text-muted mb-1">Aktive Shares</p>
                <p className="text-xl font-bold tabular-nums text-text">{config.shares_count}</p>
              </div>
            </div>
            <div className="bg-surface-2 border border-border rounded-lg p-3 mt-3">
              <p className="text-xs text-text-muted mb-2">Konfiguration</p>
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
      <div className="bg-surface border border-border rounded-card p-5 mb-6">
        <h3 className="text-sm font-semibold text-text mb-4">Datenbank-Backup</h3>
        <p className="text-text-muted text-sm mb-4">
          Exportiert die gesamte Datenbank als JSON-Datei: Kunden, Aufträge, Verträge, Rechnungen, Leads, Zeiteinträge, Ausgaben und Aktivitäten.
        </p>
        <button onClick={handleExport} disabled={exporting} className="btn-primary">
          {exporting ? 'Exportiere...' : 'Datenbank herunterladen'}
        </button>
      </div>

      {/* Email Templates */}
      <div className="bg-surface border border-border rounded-card p-5 mb-6">
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
