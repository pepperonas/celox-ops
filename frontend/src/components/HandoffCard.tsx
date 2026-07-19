import { useCallback, useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import {
  getHandoffStatus,
  pushHandoff,
  type HandoffStatusResponse,
  type HandoffTarget,
} from '../api/handoff'
import { PORTAL_PRODUCTS } from '../utils/handoffCatalog'
import { buttonLabel, statusLabel, statusTone } from '../utils/handoffStatus'
import type { Customer } from '../types'

const TARGET_META: Record<HandoffTarget, { title: string; hint: string }> = {
  portal: { title: 'celox Portal', hint: 'Assessments & Schulungen (portal.celox.io)' },
  datenschutz: { title: 'Datenschutz-DSMS', hint: 'DSB-Mandat (datenschutz.celox.io)' },
}

function toneDot(tone: 'ok' | 'error' | 'none') {
  if (tone === 'ok') return 'bg-success'
  if (tone === 'error') return 'bg-danger'
  return 'bg-border'
}

interface Props {
  customerId: string
  customer: Customer
}

export default function HandoffCard({ customerId, customer }: Props) {
  const [data, setData] = useState<HandoffStatusResponse | null>(null)
  const [dialogTarget, setDialogTarget] = useState<HandoffTarget | null>(null)
  const [entitlements, setEntitlements] = useState<Set<string>>(new Set())
  const [sendOnboarding, setSendOnboarding] = useState(false)
  const [inviteContact, setInviteContact] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(() => {
    getHandoffStatus(customerId).then(setData).catch(() => {})
  }, [customerId])

  useEffect(() => { load() }, [load])

  const companyName = (customer.company || '').trim() || customer.name
  const alreadyPushed = dialogTarget ? statusTone(data?.[dialogTarget]?.status) === 'ok' : false

  const grouped = useMemo(() => ({
    audits: PORTAL_PRODUCTS.filter((p) => p.kind === 'audit'),
    trainings: PORTAL_PRODUCTS.filter((p) => p.kind === 'training'),
  }), [])

  if (!data || (!data.portal.configured && !data.datenschutz.configured)) return null

  const openDialog = (target: HandoffTarget) => {
    setEntitlements(new Set())
    setSendOnboarding(false)
    setInviteContact(true)
    setDialogTarget(target)
  }

  const handlePush = async () => {
    if (!dialogTarget) return
    setSubmitting(true)
    try {
      const result = await pushHandoff(customerId, {
        target: dialogTarget,
        ...(dialogTarget === 'portal'
          ? { entitlements: Array.from(entitlements), send_onboarding: sendOnboarding }
          : { invite_contact: inviteContact }),
      })
      toast.success(
        result.created
          ? `Kunde an ${TARGET_META[dialogTarget].title} übergeben (neu angelegt).`
          : `Kunde erneut übergeben — im Ziel angereichert (Enrich-only).`
      )
      setDialogTarget(null)
      load()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Übergabe fehlgeschlagen.')
      load() // Fehler-Status wird auch persistiert — Anzeige aktualisieren
    }
    setSubmitting(false)
  }

  const row = (target: HandoffTarget) => {
    const t = data[target]
    if (!t.configured) return null
    const tone = statusTone(t.status)
    return (
      <div key={target} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
        <div className="flex items-start gap-3 min-w-0">
          <span className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${toneDot(tone)}`} />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-text">{TARGET_META[target].title}</p>
            <p className="text-xs text-text-muted break-words">
              {statusLabel(t.status)} · {TARGET_META[target].hint}
            </p>
          </div>
        </div>
        <button
          onClick={() => openDialog(target)}
          disabled={data.email_missing}
          title={data.email_missing ? 'Ohne E-Mail-Adresse ist keine Übergabe möglich.' : undefined}
          className={tone === 'ok' ? 'btn-secondary' : 'btn-primary'}
        >
          {buttonLabel(t.status)}
        </button>
      </div>
    )
  }

  const preview = data.datenschutz.address_preview
  const addressUnsure = preview != null && !preview.postal_code

  return (
    <div className="bg-surface border border-border rounded-card p-5 mb-6">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-text">Übergeben an…</h3>
        {data.email_missing && (
          <span className="text-xs text-danger">E-Mail fehlt — Übergabe nicht möglich</span>
        )}
      </div>
      <div className="divide-y divide-border">
        {row('portal')}
        {row('datenschutz')}
      </div>

      {dialogTarget && createPortal(
        <div className="fixed inset-0 bg-black/85 flex items-center justify-center z-50 p-4" onClick={() => !submitting && setDialogTarget(null)}>
          <div className="bg-surface border border-border rounded-dialog p-6 sm:p-8 w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-text mb-1">
              An {TARGET_META[dialogTarget].title} übergeben
            </h3>
            <p className="text-text-muted text-sm mb-5">
              {alreadyPushed
                ? 'Erneute Übergabe füllt nur leere Felder im Ziel (Enrich-only) — dort gepflegte Daten bleiben unangetastet.'
                : 'Legt den Kunden in der Ziel-App an. Es werden nur die unten gelisteten Felder übertragen.'}
            </p>

            {/* Datenvorschau — exakt die übertragenen Felder (Datensparsamkeit) */}
            <div className="bg-surface-2 border border-border rounded-lg p-4 mb-5 text-sm space-y-1.5">
              <p><span className="text-text-muted">Firma:</span> <span className="text-text">{companyName}</span></p>
              <p><span className="text-text-muted">{dialogTarget === 'portal' ? 'Leitungs-Konto:' : 'Ansprechpartner:'}</span>{' '}
                <span className="text-text break-words">{customer.name} · {customer.email}</span></p>
              {dialogTarget === 'datenschutz' && (
                <>
                  {customer.phone && (
                    <p><span className="text-text-muted">Telefon:</span> <span className="text-text">{customer.phone}</span></p>
                  )}
                  {preview && (
                    <p className="break-words">
                      <span className="text-text-muted">Adresse:</span>{' '}
                      <span className="text-text">
                        {addressUnsure
                          ? `${preview.street} (nicht eindeutig zerlegbar — geht ungeparst mit)`
                          : `${preview.street}, ${preview.postal_code} ${preview.city}, ${preview.country}`}
                      </span>
                    </p>
                  )}
                  {customer.website && (
                    <p className="break-words"><span className="text-text-muted">Website:</span> <span className="text-text">{customer.website}</span></p>
                  )}
                </>
              )}
              <p className="text-xs text-text-muted pt-1.5">
                {dialogTarget === 'portal'
                  ? 'Nicht übertragen: Telefon, Adresse, Website, Notizen, Finanzdaten.'
                  : 'Nicht übertragen: Notizen, GitHub-Repos, KI-Tracker, Finanzdaten.'}
              </p>
            </div>

            {dialogTarget === 'portal' && (
              <>
                <p className="text-xs text-text-muted mb-2">Buchungen (Entitlements) — optional{alreadyPushed ? '; bei bestehender Firma werden Buchungen NICHT verändert' : ''}:</p>
                <div className="max-h-56 overflow-y-auto border border-border rounded-lg p-3 mb-4 space-y-3">
                  {(['audits', 'trainings'] as const).map((group) => (
                    <div key={group}>
                      <p className="text-[11px] font-semibold text-text-muted uppercase tracking-wide mb-1.5">
                        {group === 'audits' ? 'Audits' : 'Schulungen'}
                      </p>
                      <div className="space-y-1">
                        {grouped[group].map((p) => (
                          <label key={p.key} className="flex items-center gap-2 text-sm text-text cursor-pointer">
                            <input
                              type="checkbox"
                              checked={entitlements.has(p.key)}
                              onChange={(e) => {
                                const next = new Set(entitlements)
                                if (e.target.checked) next.add(p.key)
                                else next.delete(p.key)
                                setEntitlements(next)
                              }}
                            />
                            <span>{p.label}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <label className={`flex items-center gap-2 text-sm mb-5 ${alreadyPushed ? 'text-text-muted cursor-not-allowed' : 'text-text cursor-pointer'}`}>
                  <input
                    type="checkbox"
                    checked={sendOnboarding}
                    disabled={alreadyPushed}
                    onChange={(e) => setSendOnboarding(e.target.checked)}
                  />
                  <span>Onboarding-Mail sofort senden{alreadyPushed ? ' (bei bestehender Firma nur übers portal-Admin-Panel)' : ' (sonst später im portal-Admin-Panel)'}</span>
                </label>
              </>
            )}

            {dialogTarget === 'datenschutz' && (
              <label className="flex items-center gap-2 text-sm text-text cursor-pointer mb-5">
                <input
                  type="checkbox"
                  checked={inviteContact}
                  onChange={(e) => setInviteContact(e.target.checked)}
                />
                <span>Ansprechpartner per E-Mail ins DSMS einladen (14 Tage gültig)</span>
              </label>
            )}

            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setDialogTarget(null)} disabled={submitting} className="btn-secondary">
                Abbrechen
              </button>
              <button type="button" onClick={handlePush} disabled={submitting} className="btn-primary">
                {submitting ? 'Übergebe…' : alreadyPushed ? 'Erneut übergeben' : 'Übergeben'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}
