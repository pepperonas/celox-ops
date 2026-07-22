import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import { draftLeadEmail, sendLeadEmail } from '../../api/rainmaker'
import type { RainmakerLead } from '../../types'

interface Props {
  lead: RainmakerLead
  onClose: () => void
  onSent?: () => void
}

const SENDER = 'martin.pfeffer@celox.io'

/**
 * Akquise-Mail an einen Lead: öffnet mit einem KI-Entwurf (aus Target + Infos),
 * der jederzeit editierbar ist. Gesendet wird erst nach manueller Bestätigung,
 * Absender fest martin.pfeffer@celox.io. createPortal wegen `.page-enter`
 * (Transform-Ancestor-Regel).
 */
export default function LeadEmailDialog({ lead, onClose, onSent }: Props) {
  const [to, setTo] = useState(lead.email ?? '')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [product, setProduct] = useState<string | null>(null)
  const [drafting, setDrafting] = useState(false)
  const [sending, setSending] = useState(false)
  const [cost, setCost] = useState<string | null>(null)

  const generate = useCallback(async (force = false) => {
    setDrafting(true)
    try {
      const d = await draftLeadEmail(lead.id, force)
      setSubject(d.subject)
      setBody(d.body)
      setProduct(d.product)
      setCost(d.cached
        ? `Aus Cache (0 €) · Budget ${d.budget.spent_eur.toFixed(2)}/${d.budget.budget_eur.toFixed(0)} €`
        : `KI-Kosten: ${d.run.cost_eur.toFixed(3)} € · Budget ${d.budget.spent_eur.toFixed(2)}/${d.budget.budget_eur.toFixed(0)} €`)
    } catch (e: unknown) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'KI-Entwurf fehlgeschlagen.')
    }
    setDrafting(false)
  }, [lead.id])

  // Beim Öffnen genau EINMAL laden — nutzt den Cache (0 Tokens, wenn unverändert).
  // Regenerieren nur auf Klick (force=true umgeht den Cache).
  useEffect(() => { generate(false) }, [generate])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && !sending) onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose, sending])

  const send = async () => {
    if (!to.trim()) { toast.error('Keine Empfänger-E-Mail.'); return }
    if (!subject.trim() || !body.trim()) { toast.error('Betreff und Text dürfen nicht leer sein.'); return }
    setSending(true)
    try {
      await sendLeadEmail(lead.id, { to_email: to.trim(), subject, message: body })
      toast.success(`E-Mail an ${to.trim()} gesendet.`)
      onSent?.()
      onClose()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Versand fehlgeschlagen.')
    }
    setSending(false)
  }

  return createPortal(
    <div className="fixed inset-0 bg-black/85 flex items-center justify-center z-50 p-4" onClick={() => !sending && onClose()}>
      <div
        className="bg-surface border border-border rounded-dialog p-6 w-full max-w-2xl max-h-[92vh] overflow-y-auto animate-modal-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 mb-1">
          <h3 className="text-lg font-semibold text-text">E-Mail an {lead.company}</h3>
          {product && (
            <span className="text-xs px-2 py-1 rounded-full bg-accent/15 text-accent shrink-0" title="Von der KI empfohlenes Produkt">
              🎯 {product}
            </span>
          )}
        </div>
        <p className="text-xs text-text-muted mb-4">
          KI-Vorschlag aus Target &amp; Infos — frei editierbar, wird erst nach deiner Bestätigung gesendet. Absender: {SENDER}
        </p>

        <div className="space-y-3">
          <div>
            <label htmlFor="lead-mail-to" className="block text-xs text-text-muted mb-1">An</label>
            <input id="lead-mail-to" type="email" value={to} onChange={(e) => setTo(e.target.value)} className="w-full" placeholder="empfaenger@firma.de" />
          </div>
          <div>
            <label htmlFor="lead-mail-subject" className="block text-xs text-text-muted mb-1">Betreff</label>
            <input id="lead-mail-subject" value={subject} onChange={(e) => setSubject(e.target.value)} disabled={drafting}
                   className="w-full" placeholder={drafting ? 'KI schreibt…' : ''} />
          </div>
          <div>
            <label htmlFor="lead-mail-body" className="block text-xs text-text-muted mb-1">Nachricht</label>
            <div className="relative">
              <textarea id="lead-mail-body" value={body} onChange={(e) => setBody(e.target.value)} disabled={drafting}
                        rows={12} className="w-full resize-y font-sans" placeholder={drafting ? '' : ''} />
              {drafting && (
                <div className="absolute inset-0 grid place-items-center bg-surface/70 rounded-md">
                  <div className="flex items-center gap-2 text-sm text-text-muted">
                    <span className="md-spinner !w-4 !h-4 !border-2" /> KI erstellt den Entwurf…
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-4">
          <button type="button" onClick={() => generate(true)} disabled={drafting || sending} className="btn-secondary text-sm">
            {drafting ? '…' : '✨ KI neu vorschlagen'}
          </button>
          {cost && <span className="text-[11px] text-text-muted">{cost}</span>}
          <div className="ml-auto flex gap-2">
            <button type="button" onClick={onClose} disabled={sending} className="btn-secondary">Abbrechen</button>
            <button type="button" onClick={send} disabled={sending || drafting} className="btn-primary">
              {sending ? 'Sende…' : 'Senden'}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
