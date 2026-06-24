import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  getComplianceOverview,
  markCompliance,
  uploadSignedDocument,
  setTemplateRequired,
  type ComplianceOverview,
  type ComplianceCustomer,
  type ComplianceItem,
} from '../api/compliance'
import { getDocumentTemplates, generateDocument, type DocumentTemplate } from '../api/documents'
import { downloadAttachment } from '../api/attachments'

const CATEGORY_LABELS: Record<string, string> = {
  datenschutz: 'Datenschutz',
  dienstleistung: 'Dienstleistung',
  allgemein: 'Allgemein',
}

export default function Compliance() {
  const [overview, setOverview] = useState<ComplianceOverview | null>(null)
  const [templates, setTemplates] = useState<DocumentTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [onlyGaps, setOnlyGaps] = useState(true)
  const [showConfig, setShowConfig] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)

  const load = async () => {
    try {
      const [ov, tpls] = await Promise.all([getComplianceOverview(), getDocumentTemplates()])
      setOverview(ov)
      setTemplates(tpls)
    } catch {
      toast.error('Fehler beim Laden der Compliance-Daten.')
    }
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  const key = (c: string, t: string) => `${c}:${t}`

  const handleGenerate = async (customerId: string, templateId: string, name: string) => {
    setBusy(key(customerId, templateId))
    try {
      await generateDocument(templateId, customerId)
      toast.success(`${name} erstellt.`)
    } catch {
      toast.error('PDF-Erstellung fehlgeschlagen.')
    }
    setBusy(null)
  }

  const pickAndUpload = (customerId: string, templateId: string) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.pdf,application/pdf,image/*'
    input.onchange = async () => {
      const file = input.files?.[0]
      if (!file) return
      setBusy(key(customerId, templateId))
      try {
        await uploadSignedDocument(file, customerId, templateId)
        toast.success('Unterschriebenes Dokument hochgeladen.')
        await load()
      } catch {
        toast.error('Upload fehlgeschlagen.')
      }
      setBusy(null)
    }
    input.click()
  }

  const handleMark = async (customerId: string, templateId: string, signed: boolean) => {
    setBusy(key(customerId, templateId))
    try {
      await markCompliance({ customer_id: customerId, template_id: templateId, signed })
      toast.success(signed ? 'Als unterschrieben markiert.' : 'Markierung entfernt.')
      await load()
    } catch {
      toast.error('Aktion fehlgeschlagen.')
    }
    setBusy(null)
  }

  const handleToggleRequired = async (templateId: string, required: boolean) => {
    try {
      await setTemplateRequired(templateId, required)
      await load()
    } catch {
      toast.error('Konnte Pflicht-Status nicht ändern.')
    }
  }

  if (loading) {
    return <div className="text-text-muted text-sm">Lade Compliance-Übersicht...</div>
  }

  const customers = overview?.customers ?? []
  const visible = onlyGaps ? customers.filter((c) => !c.complete) : customers
  const summary = overview?.summary
  const requiredTemplates = overview?.required_templates ?? []

  return (
    <div className="max-w-5xl">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-text tracking-tight">Rechtsdokumente</h2>
          <p className="text-text-muted text-sm mt-1">
            Unterschriebene Pflichtdokumente (Datenschutz/AVV, AGB) je Kunde – Status & fehlende Unterlagen.
          </p>
        </div>
        <button onClick={() => setShowConfig((v) => !v)} className="btn-secondary text-sm">
          {showConfig ? 'Konfiguration schließen' : 'Pflichtdokumente konfigurieren'}
        </button>
      </div>

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <StatCard label="Kunden" value={summary.total_customers} />
          <StatCard label="Vollständig" value={summary.fully_compliant} tone="success" />
          <StatCard label="Mit Lücken" value={summary.with_gaps} tone={summary.with_gaps > 0 ? 'danger' : 'success'} />
          <StatCard label="Fehlende Docs" value={summary.total_missing} tone={summary.total_missing > 0 ? 'danger' : 'success'} />
        </div>
      )}

      {/* Config */}
      {showConfig && (
        <div className="bg-surface border border-border rounded-card p-5 mb-6">
          <h3 className="text-sm font-semibold text-text mb-1">Pflichtdokumente</h3>
          <p className="text-text-muted text-xs mb-4">
            Lege fest, welche Vorlagen jeder Kunde unterschrieben vorliegen haben muss.
          </p>
          <div className="space-y-2">
            {templates.map((t) => (
              <label key={t.id} className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={t.compliance_required === true}
                  onChange={(e) => handleToggleRequired(t.id, e.target.checked)}
                  style={{ accentColor: 'var(--md-primary)' }}
                  className="w-[18px] h-[18px] rounded cursor-pointer"
                />
                <span className="text-sm text-text">{t.name}</span>
                <span className="text-[11px] text-text-muted">{CATEGORY_LABELS[t.category] || t.category}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {requiredTemplates.length === 0 ? (
        <div className="bg-surface border border-border rounded-card p-8 text-center text-text-muted text-sm">
          Keine Pflichtdokumente definiert. Öffne „Pflichtdokumente konfigurieren" und wähle die nötigen Vorlagen aus.
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 mb-4">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-text-muted">
              <input
                type="checkbox"
                checked={onlyGaps}
                onChange={(e) => setOnlyGaps(e.target.checked)}
                style={{ accentColor: 'var(--md-primary)' }}
                className="w-[16px] h-[16px] rounded cursor-pointer"
              />
              Nur Kunden mit Lücken
            </label>
          </div>

          {visible.length === 0 ? (
            <div className="bg-surface border border-border rounded-card p-8 text-center text-success text-sm">
              🎉 Alle Kunden haben alle Pflichtdokumente unterschrieben vorliegen.
            </div>
          ) : (
            <div className="space-y-4">
              {visible.map((c) => (
                <CustomerCard
                  key={c.customer_id}
                  customer={c}
                  busyKey={busy}
                  onGenerate={handleGenerate}
                  onUpload={pickAndUpload}
                  onMark={handleMark}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function StatCard({ label, value, tone }: { label: string; value: number; tone?: 'success' | 'danger' }) {
  const color = tone === 'success' ? 'text-success' : tone === 'danger' ? 'text-danger' : 'text-text'
  return (
    <div className="bg-surface border border-border rounded-card p-4">
      <p className="text-xs text-text-muted mb-1">{label}</p>
      <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
    </div>
  )
}

function CustomerCard({
  customer,
  busyKey,
  onGenerate,
  onUpload,
  onMark,
}: {
  customer: ComplianceCustomer
  busyKey: string | null
  onGenerate: (c: string, t: string, name: string) => void
  onUpload: (c: string, t: string) => void
  onMark: (c: string, t: string, signed: boolean) => void
}) {
  return (
    <div className="bg-surface border border-border rounded-card p-5">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-text">
            {customer.company || customer.name}
          </h3>
          {customer.company && <p className="text-xs text-text-muted">{customer.name}</p>}
        </div>
        {customer.complete ? (
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-success/10 text-success">
            ✓ vollständig
          </span>
        ) : (
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-danger/10 text-danger">
            {customer.missing_count} von {customer.total_required} offen
          </span>
        )}
      </div>
      <div className="space-y-2">
        {customer.items.map((item) => (
          <DocRow
            key={item.template_id}
            customerId={customer.customer_id}
            item={item}
            busy={busyKey === `${customer.customer_id}:${item.template_id}`}
            onGenerate={onGenerate}
            onUpload={onUpload}
            onMark={onMark}
          />
        ))}
      </div>
    </div>
  )
}

function DocRow({
  customerId,
  item,
  busy,
  onGenerate,
  onUpload,
  onMark,
}: {
  customerId: string
  item: ComplianceItem
  busy: boolean
  onGenerate: (c: string, t: string, name: string) => void
  onUpload: (c: string, t: string) => void
  onMark: (c: string, t: string, signed: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 border-t border-border first:border-t-0 flex-wrap">
      <div className="flex items-center gap-2 min-w-0">
        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${item.signed ? 'bg-success' : 'bg-danger'}`} />
        <span className="text-sm text-text truncate">{item.name}</span>
        {item.signed && (
          <span className="text-[11px] text-text-muted shrink-0">
            {item.method === 'upload' ? 'hochgeladen' : 'manuell'}
            {item.signed_at ? ` · ${new Date(item.signed_at).toLocaleDateString('de-DE')}` : ''}
          </span>
        )}
      </div>
      <div className="flex items-center gap-1.5 flex-wrap">
        {item.signed ? (
          <>
            {item.attachment_id && (
              <button
                onClick={() => downloadAttachment(item.attachment_id!, `${item.name}.pdf`)}
                className="text-xs px-2 py-1 rounded-lg text-accent hover:bg-accent/10"
              >
                Anzeigen
              </button>
            )}
            <button
              onClick={() => onMark(customerId, item.template_id, false)}
              disabled={busy}
              className="text-xs px-2 py-1 rounded-lg text-text-muted hover:bg-danger/10 hover:text-danger disabled:opacity-50"
            >
              Zurücksetzen
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => onGenerate(customerId, item.template_id, item.name)}
              disabled={busy}
              className="text-xs px-2.5 py-1 rounded-lg bg-accent/10 text-accent hover:bg-accent/20 disabled:opacity-50"
            >
              {busy ? '…' : 'PDF erstellen'}
            </button>
            <button
              onClick={() => onUpload(customerId, item.template_id)}
              disabled={busy}
              className="text-xs px-2.5 py-1 rounded-lg bg-surface-2 text-text hover:bg-border disabled:opacity-50"
            >
              Hochladen
            </button>
            <button
              onClick={() => onMark(customerId, item.template_id, true)}
              disabled={busy}
              className="text-xs px-2.5 py-1 rounded-lg text-success hover:bg-success/10 disabled:opacity-50"
            >
              Abhaken
            </button>
          </>
        )}
      </div>
    </div>
  )
}
