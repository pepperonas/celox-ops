// Kontoauszug einlesen und Zahlungen zuordnen. Der Dialog zeigt ausschließlich
// VORSCHLÄGE — gebucht wird erst auf Bestätigung, und das Ergebnis ist über den
// bestehenden Zahlungsstand-Undo widerrufbar.
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import {
  applyBankMatches,
  previewBankStatement,
  restorePaymentState,
  type BankImportPreview,
  type BankMatchProposal,
} from '../../api/invoices'
import { formatCurrency, formatDate } from '../../utils/formatters'
import { toastWithUndo } from '../../utils/undoToast'

interface Props {
  onClose: () => void
  onApplied: () => void
}

const CONFIDENCE: Record<string, { label: string; cls: string; title: string }> = {
  exact: { label: 'sicher', cls: 'text-success',
           title: 'Rechnungsnummer im Verwendungszweck und Betrag stimmen überein' },
  number: { label: 'Betrag prüfen', cls: 'text-warning',
            title: 'Rechnungsnummer erkannt, der Betrag weicht vom offenen Rest ab' },
  amount: { label: 'nur Betrag', cls: 'text-warning',
            title: 'Keine Rechnungsnummer gefunden — Zuordnung allein über den eindeutigen Betrag' },
}

export default function BankImportModal({ onClose, onApplied }: Props) {
  const [preview, setPreview] = useState<BankImportPreview | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && !applying) onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [applying, onClose])

  const load = async (file: File) => {
    setLoading(true)
    setError(null)
    try {
      const res = await previewBankStatement(file)
      setPreview(res)
      // Nur zweifelsfreie Treffer vorwählen — alles andere bewusst bestätigen.
      setSelected(new Set(res.proposals
        .map((p, i) => (p.confidence === 'exact' ? i : -1)).filter((i) => i >= 0)))
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || 'Die Datei konnte nicht gelesen werden.')
      setPreview(null)
    }
    setLoading(false)
  }

  const toggle = (i: number) => setSelected((prev) => {
    const next = new Set(prev)
    if (next.has(i)) next.delete(i); else next.add(i)
    return next
  })

  const chosen = useMemo(
    () => [...selected].map((i) => preview?.proposals[i]).filter(Boolean) as BankMatchProposal[],
    [selected, preview],
  )
  const sum = chosen.reduce((acc, p) => acc + Number(p.amount), 0)

  const apply = async () => {
    if (!chosen.length || applying) return
    setApplying(true)
    try {
      const res = await applyBankMatches(chosen)
      const snapshot = res.applied
      toastWithUndo(
        `${snapshot.length} Zahlung${snapshot.length === 1 ? '' : 'en'} gebucht`
        + (res.skipped.length ? ` · ${res.skipped.length} übersprungen` : '') + '.',
        async () => {
          // Undo über den bestehenden Zahlungsstand-Endpunkt: jede Rechnung
          // zurück auf den Stand VOR dem Import.
          await Promise.all(snapshot.map((row) => restorePaymentState(
            row.invoice_id, row.previous_amount_paid, row.previous_status as never)))
          onApplied()
        },
      )
      if (res.skipped.length) toast.error(res.skipped.join(' · '), { duration: 8000 })
      onApplied()
      onClose()
    } catch {
      toast.error('Buchen fehlgeschlagen.')
      setApplying(false)
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={() => { if (!applying) onClose() }} />
      <div
        className={`relative bg-surface-high rounded-dialog shadow-elev-3 p-7 max-w-[900px] w-full mx-4
                    animate-modal-in max-h-[88vh] flex flex-col
                    ${dragOver ? 'ring-2 ring-accent' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          const file = e.dataTransfer.files?.[0]
          if (file) load(file)
        }}
      >
        <h3 className="text-lg font-semibold text-text mb-1">Kontoauszug einlesen</h3>
        <p className="text-xs text-text-muted mb-4">
          camt.053-XML oder CSV-Export aus dem Online-Banking. Zahlungen werden den offenen
          Rechnungen zugeordnet — <strong className="text-text">gebucht wird nur, was du bestätigst</strong>.
        </p>

        {!preview && (
          <div className="border border-dashed border-border rounded-card p-8 text-center">
            <p className="text-sm text-text-muted mb-3">Datei hierher ziehen oder auswählen</p>
            <input
              ref={fileRef}
              type="file"
              accept=".xml,.csv,.txt,text/csv,text/xml,application/xml"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) load(f) }}
            />
            <button onClick={() => fileRef.current?.click()} className="btn-primary text-sm"
                    disabled={loading}>
              {loading ? 'Lese ein…' : 'Datei auswählen'}
            </button>
            {error && <p className="text-sm text-danger mt-4">{error}</p>}
          </div>
        )}

        {preview && (
          <>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-muted mb-3">
              <span>{preview.transactions_total} Buchungen gelesen</span>
              <span>· {preview.proposals.length} zugeordnet</span>
              <span>· {preview.unmatched.length} offen</span>
              {preview.ignored_debits > 0 && <span>· {preview.ignored_debits} Belastungen ignoriert</span>}
              <span>· {preview.open_invoices} offene Rechnungen im Bestand</span>
              <button onClick={() => { setPreview(null); setSelected(new Set()) }}
                      className="ml-auto text-accent hover:underline">
                andere Datei
              </button>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto border border-border rounded-lg">
              {preview.proposals.length > 0 ? (
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-surface-container">
                    <tr className="text-left text-xs text-text-muted">
                      <th className="px-3 py-2 w-8"></th>
                      <th className="px-2 py-2">Buchung</th>
                      <th className="px-2 py-2">Rechnung</th>
                      <th className="px-2 py-2 text-right">Betrag</th>
                      <th className="px-2 py-2">Sicherheit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.proposals.map((p, i) => {
                      const c = CONFIDENCE[p.confidence] ?? CONFIDENCE.amount
                      return (
                        <tr key={i} onClick={() => toggle(i)}
                            className="border-t border-border cursor-pointer hover:bg-surface-container">
                          <td className="px-3 py-1.5">
                            <input type="checkbox" checked={selected.has(i)}
                                   onChange={() => toggle(i)} onClick={(e) => e.stopPropagation()} />
                          </td>
                          <td className="px-2 py-1.5">
                            <div className="text-text">{formatDate(p.booking_date)}
                              {p.counterparty && <span className="text-text-muted"> · {p.counterparty}</span>}
                            </div>
                            <div className="text-[11px] text-text-muted line-clamp-1" title={p.purpose}>
                              {p.purpose || '–'}
                            </div>
                          </td>
                          <td className="px-2 py-1.5">
                            <div className="text-text">{p.invoice_number}</div>
                            <div className="text-[11px] text-text-muted">
                              {p.customer_name} · offen {formatCurrency(p.invoice_open)}
                            </div>
                          </td>
                          <td className="px-2 py-1.5 text-right text-text tabular-nums">
                            {formatCurrency(p.amount)}
                          </td>
                          <td className={`px-2 py-1.5 text-xs ${c.cls}`} title={c.title}>
                            {c.label}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              ) : (
                <p className="text-sm text-text-muted p-6 text-center">
                  Keine Buchung konnte einer offenen Rechnung zugeordnet werden.
                </p>
              )}

              {preview.unmatched.length > 0 && (
                <details className="border-t border-border">
                  <summary className="px-3 py-2 text-xs text-text-muted cursor-pointer md-state">
                    {preview.unmatched.length} nicht zugeordnete Gutschriften anzeigen
                  </summary>
                  <ul className="px-3 pb-3 space-y-1">
                    {preview.unmatched.map((u, i) => (
                      <li key={i} className="text-[11px] text-text-muted flex gap-2">
                        <span className="tabular-nums shrink-0">{formatDate(u.booking_date)}</span>
                        <span className="tabular-nums shrink-0">{formatCurrency(u.amount)}</span>
                        <span className="truncate">{u.counterparty || u.purpose || '–'}</span>
                        <span className="ml-auto shrink-0 opacity-70">{u.reason}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          </>
        )}

        <div className="flex items-center gap-2 mt-4">
          {preview && chosen.length > 0 && (
            <span className="text-xs text-text-muted">
              {chosen.length} ausgewählt · {formatCurrency(sum)}
            </span>
          )}
          <div className="ml-auto flex gap-2">
            <button onClick={onClose} className="btn-secondary" disabled={applying}>
              Abbrechen
            </button>
            {preview && preview.proposals.length > 0 && (
              <button onClick={apply} className="btn-primary"
                      disabled={chosen.length === 0 || applying}>
                {applying ? 'Buche…' : `${chosen.length} Zahlung${chosen.length === 1 ? '' : 'en'} buchen`}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
