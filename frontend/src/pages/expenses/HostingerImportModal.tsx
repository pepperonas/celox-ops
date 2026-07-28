// Laufende Hostinger-Kosten (VPS, Domains) als Ausgaben übernehmen.
//
// Die Hostinger-API liefert **Verträge, keine Belege** — es gibt keinen
// Rechnungs-Endpunkt. Übernommen wird deshalb der Ist-Stand: je aktivem Abo eine
// wiederkehrende Ausgabe, datiert auf die letzte Abrechnung. Was übersprungen
// wurde, steht sichtbar darunter; geschrieben wird nur, was angehakt ist.
import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import {
  hostingerImport,
  hostingerPreview,
  type HostingerPreview as Preview,
} from '../../api/hostinger'
import { formatCurrency, formatDate } from '../../utils/formatters'

const CATEGORY_LABEL: Record<string, string> = {
  hosting: 'Hosting', domain: 'Domain', software: 'Software', lizenz: 'Lizenz',
  hardware: 'Hardware', ki_api: 'KI-API', werbung: 'Werbung', buero: 'Büro',
  reise: 'Reise', sonstige: 'Sonstige',
}

interface Props {
  onClose: () => void
  onImported: () => void
}

export default function HostingerImportModal({ onClose, onImported }: Props) {
  const [preview, setPreview] = useState<Preview | null>(null)
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSkipped, setShowSkipped] = useState(false)
  const [openNotes, setOpenNotes] = useState<string | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !loading && !saving) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [loading, saving, onClose])

  useEffect(() => {
    let alive = true
    hostingerPreview()
      .then((res) => {
        if (!alive) return
        setPreview(res)
        // Schon importierte Zeiträume nicht vorwählen.
        setPicked(new Set(res.drafts.filter((d) => !d.duplicate).map((d) => d.external_ref)))
      })
      .catch((err) => {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        if (alive) setError(detail || 'Die Hostinger-Abfrage ist fehlgeschlagen.')
      })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  const toggle = (ref: string) => setPicked((prev) => {
    const next = new Set(prev)
    if (next.has(ref)) next.delete(ref); else next.add(ref)
    return next
  })

  const sum = useMemo(() => (preview?.drafts || [])
    .filter((d) => picked.has(d.external_ref))
    .reduce((acc, d) => acc + Number(d.amount), 0), [preview, picked])

  const run = async () => {
    if (saving || picked.size === 0) return
    setSaving(true)
    try {
      const res = await hostingerImport([...picked])
      const bits = [
        `${res.created} Ausgabe${res.created === 1 ? '' : 'n'}`,
        `${formatCurrency(Number(res.total))}`,
        res.skipped_duplicates ? `${res.skipped_duplicates} Duplikat(e) übersprungen` : '',
      ].filter(Boolean)
      toast.success(`Übernommen: ${bits.join(' · ')}.`)
      onImported()
      onClose()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Übernehmen fehlgeschlagen.')
      setSaving(false)
    }
  }

  const drafts = preview?.drafts || []

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={() => { if (!loading && !saving) onClose() }} />
      <div className="relative bg-surface-high rounded-dialog shadow-elev-3 p-5 sm:p-7
                      max-w-[900px] w-full mx-4 animate-modal-in max-h-[88vh] flex flex-col">
        <h3 className="text-lg font-semibold text-text mb-1">Hostinger-Kosten übernehmen</h3>
        <p className="text-xs text-text-muted mb-4">
          Je <strong className="text-text">aktivem Abo</strong> eine wiederkehrende Ausgabe,
          datiert auf die letzte Abrechnung. Die Hostinger-API liefert Verträge, keine
          Rechnungsbelege — vergangene Perioden werden deshalb nicht hochgerechnet.
        </p>

        {loading && (
          <div className="py-10 text-center text-sm text-text-muted">
            <span className="inline-block w-4 h-4 rounded-full border-2 border-accent
                             border-t-transparent animate-spin mr-2 align-middle" />
            Frage Hostinger ab…
          </div>
        )}

        {error && <p className="text-sm text-danger py-4">{error}</p>}

        {preview && !loading && (
          <>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-3 text-xs text-text-muted">
              <span>{preview.counts.subscriptions ?? 0} Abos im Konto</span>
              <span>· {drafts.length} übernehmbar</span>
              {preview.already_imported > 0 && (
                <span>· {preview.already_imported} schon importiert</span>
              )}
              {preview.skipped.length > 0 && <span>· {preview.skipped.length} übersprungen</span>}
              <span className="ml-auto text-text">
                Auswahl: <strong>{formatCurrency(sum)}</strong>
              </span>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto border border-border rounded-lg">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface-container">
                  <tr className="text-left text-xs text-text-muted">
                    <th className="px-3 py-2 w-8"></th>
                    <th className="px-2 py-2">Beschreibung</th>
                    <th className="px-2 py-2">Kategorie</th>
                    <th className="px-2 py-2">Letzte Abrechnung</th>
                    <th className="px-2 py-2 text-right">Betrag</th>
                    <th className="px-2 py-2 w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {drafts.map((d) => (
                    <>
                      <tr key={d.external_ref}
                          onClick={() => !d.duplicate && toggle(d.external_ref)}
                          className={`border-t border-border ${d.duplicate
                            ? 'opacity-50' : 'cursor-pointer hover:bg-surface-container'}`}>
                        <td className="px-3 py-1.5">
                          <input type="checkbox" checked={picked.has(d.external_ref)}
                                 disabled={d.duplicate}
                                 onChange={() => toggle(d.external_ref)}
                                 onClick={(e) => e.stopPropagation()} />
                        </td>
                        <td className="px-2 py-1.5 text-text">
                          {d.description}
                          {d.duplicate && (
                            <span className="ml-2 text-[10px] text-warning"
                                  title="Dieser Abrechnungszeitraum ist schon als Ausgabe erfasst">
                              bereits importiert
                            </span>
                          )}
                        </td>
                        <td className="px-2 py-1.5 text-text-muted">
                          {CATEGORY_LABEL[d.category] || d.category}
                        </td>
                        <td className="px-2 py-1.5 text-text-muted tabular-nums">
                          {formatDate(d.date)}
                        </td>
                        <td className="px-2 py-1.5 text-right text-text tabular-nums">
                          {formatCurrency(Number(d.amount))}
                        </td>
                        <td className="px-2 py-1.5">
                          {d.notes && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                setOpenNotes(openNotes === d.external_ref ? null : d.external_ref)
                              }}
                              title="Details zum Abo"
                              className="md-state w-6 h-6 grid place-items-center rounded-full
                                         text-text-muted hover:text-text text-xs">
                              {openNotes === d.external_ref ? '▴' : 'ⓘ'}
                            </button>
                          )}
                        </td>
                      </tr>
                      {openNotes === d.external_ref && d.notes && (
                        <tr key={`${d.external_ref}-notes`} className="border-t border-border">
                          <td />
                          <td colSpan={5} className="px-2 pb-2 pt-0">
                            <pre className="text-[11px] text-text-muted whitespace-pre-wrap
                                            font-sans">{d.notes}</pre>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                  {drafts.length === 0 && (
                    <tr><td colSpan={6} className="px-3 py-6 text-center text-sm text-text-muted">
                      Keine übernehmbaren Abos gefunden.
                    </td></tr>
                  )}
                </tbody>
              </table>

              {preview.skipped.length > 0 && (
                <details className="border-t border-border" open={showSkipped}
                         onToggle={(e) => setShowSkipped((e.target as HTMLDetailsElement).open)}>
                  <summary className="px-3 py-2 text-xs text-text-muted cursor-pointer md-state">
                    {preview.skipped.length} nicht übernommen — Grund anzeigen
                  </summary>
                  <ul className="px-3 pb-2 space-y-0.5">
                    {preview.skipped.map((line, i) => (
                      <li key={i} className="text-[11px] text-text-muted">• {line}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          </>
        )}

        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="btn-secondary" disabled={saving}>
            Abbrechen
          </button>
          {preview && drafts.length > 0 && (
            <button onClick={run} className="btn-primary" disabled={picked.size === 0 || saving}>
              {saving ? 'Übernehme…' : `${picked.size} übernehmen`}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
