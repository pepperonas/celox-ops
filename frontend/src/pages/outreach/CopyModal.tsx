import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import type { OutreachTemplate, RainmakerLead } from '../../types'
import { getRainmakerLeads } from '../../api/rainmaker'
import { markOutreachCopied } from '../../api/outreach'
import { copyText } from '../../utils/clipboard'
import { extractPlaceholders, fillPlaceholders } from '../../utils/placeholders'
import { PLACEHOLDERS, PLACEHOLDER_LABEL, brancheFromTags } from './constants'
import PhoneGuide from './PhoneGuide'

interface Props {
  template: OutreachTemplate
  onClose: () => void
  onCopied?: (id: string) => void
}

export default function CopyModal({ template, onClose, onCopied }: Props) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [leads, setLeads] = useState<RainmakerLead[]>([])
  const [leadId, setLeadId] = useState('')
  const [copiedOnce, setCopiedOnce] = useState(false)

  // Platzhalter aus Betreff + Body, in der Reihenfolge des Katalogs (Unbekannte hinten).
  const keys = useMemo(() => {
    const found = new Set(extractPlaceholders(`${template.subject || ''}\n${template.body}`))
    const ordered = PLACEHOLDERS.map((p) => p.key).filter((k) => found.has(k))
    const extra = [...found].filter((k) => !ordered.includes(k))
    return [...ordered, ...extra]
  }, [template])

  useEffect(() => {
    getRainmakerLeads({ page_size: 1000 }).then((r) => setLeads(r.items)).catch(() => {})
  }, [])

  const applyLead = (id: string) => {
    setLeadId(id)
    const lead = leads.find((l) => l.id === id)
    if (!lead) return
    setValues((v) => ({
      ...v,
      name: lead.contact_name || v.name || '',
      firma: lead.company || v.firma || '',
      branche: brancheFromTags(lead.tags) || v.branche || '',
    }))
  }

  const filledSubject = fillPlaceholders(template.subject || '', values)
  const filledBody = fillPlaceholders(template.body, values)
  const missing = [...new Set([...filledSubject.missing, ...filledBody.missing])]

  const doCopy = async (text: string, label: string) => {
    const ok = await copyText(text)
    if (!ok) { toast.error('Kopieren nicht möglich.'); return }
    if (missing.length > 0) {
      toast(`Kopiert – aber ${missing.length} Platzhalter noch offen: ${missing.map((k) => PLACEHOLDER_LABEL[k] || k).join(', ')}`, { icon: '⚠️' })
    } else {
      toast.success(`${label} in Zwischenablage kopiert ✓`)
    }
    if (!copiedOnce) {
      setCopiedOnce(true)
      markOutreachCopied(template.id).then((t) => onCopied?.(t.id)).catch(() => {})
    }
  }

  const copyRaw = () => doCopy(
    template.channel === 'email' ? `${template.subject || ''}\n\n${template.body}` : template.body,
    'Rohtext',
  )

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade p-4">
      <div className="fixed inset-0" onClick={onClose} />
      <div className="relative bg-surface-high rounded-xl shadow-elev-3 p-6 max-w-[720px] w-full max-h-[90vh] flex flex-col animate-modal-in">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <h3 className="text-lg font-semibold text-text">{template.title}</h3>
            <p className="text-xs text-text-muted">Platzhalter befüllen, dann kopieren</p>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text text-sm">Schließen</button>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto space-y-4">
          {/* Optional: aus Rainmaker-Lead befüllen */}
          {keys.some((k) => ['name', 'firma', 'branche'].includes(k)) && (
            <div>
              <label className="block text-xs text-text-muted mb-1.5">Aus Pipeline-Lead befüllen (optional)</label>
              <select value={leadId} onChange={(e) => applyLead(e.target.value)} className="w-full">
                <option value="">— Lead wählen —</option>
                {leads.map((l) => (
                  <option key={l.id} value={l.id}>{l.company}{l.contact_name ? ` · ${l.contact_name}` : ''}</option>
                ))}
              </select>
            </div>
          )}

          {/* Platzhalter-Felder */}
          {keys.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {keys.map((k) => {
                const meta = PLACEHOLDERS.find((p) => p.key === k)
                const open = !(values[k] ?? '').trim()
                return (
                  <div key={k}>
                    <label className="block text-xs mb-1 flex items-center gap-1.5">
                      <span className="text-text-muted">{PLACEHOLDER_LABEL[k] || k}</span>
                      {open && <span className="text-warning text-[10px]">offen</span>}
                    </label>
                    <input
                      value={values[k] ?? ''}
                      onChange={(e) => setValues((v) => ({ ...v, [k]: e.target.value }))}
                      placeholder={meta?.example || `{{${k}}}`}
                      className={`w-full ${open ? 'border-warning/50' : ''}`}
                    />
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-xs text-text-muted">Dieses Template enthält keine Platzhalter.</p>
          )}

          {/* Vorschau */}
          <div>
            <label className="block text-xs text-text-muted mb-1.5">Vorschau</label>
            {template.channel === 'email' && template.subject && (
              <div className="mb-2 rounded-lg border border-border bg-surface-container px-3 py-2">
                <span className="text-[10px] uppercase tracking-wide text-text-muted">Betreff</span>
                <p className="text-sm text-text">{filledSubject.text}</p>
              </div>
            )}
            {template.channel === 'phone' ? (
              <PhoneGuide body={filledBody.text} onCopy={doCopy} />
            ) : (
              <pre className="whitespace-pre-wrap text-sm text-text font-sans rounded-lg border border-border bg-surface-container p-3">{filledBody.text}</pre>
            )}
          </div>
        </div>

        {/* Aktionen */}
        <div className="flex flex-wrap items-center justify-end gap-2 pt-4 mt-2 border-t border-border">
          <button onClick={copyRaw} className="btn-secondary !text-xs" title="Mit Platzhaltern {{…}} kopieren">
            Roh kopieren
          </button>
          <div className="flex-1" />
          {template.channel === 'email' ? (
            <>
              <button onClick={() => doCopy(filledSubject.text, 'Betreff')} className="btn-secondary">Betreff</button>
              <button onClick={() => doCopy(filledBody.text, 'Body')} className="btn-secondary">Body</button>
              <button onClick={() => doCopy(`${filledSubject.text}\n\n${filledBody.text}`, 'Betreff + Body')} className="btn-primary">Beides kopieren</button>
            </>
          ) : template.channel === 'phone' ? (
            <button onClick={() => doCopy(filledBody.text, 'Leitfaden')} className="btn-primary">Ganzen Leitfaden kopieren</button>
          ) : (
            <button onClick={() => doCopy(filledBody.text, 'Nachricht')} className="btn-primary">Kopieren</button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
