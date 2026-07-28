// Laufende Hostinger-Kosten (VPS, Domains) als Ausgaben übernehmen.
//
// Die Hostinger-API liefert **Verträge, keine Belege** — es gibt keinen
// Rechnungs-Endpunkt. Übernommen wird deshalb der Ist-Stand: je aktivem Abo eine
// wiederkehrende Ausgabe, datiert auf die letzte Abrechnung. Was übersprungen
// wurde, steht sichtbar darunter; geschrieben wird nur, was angehakt ist.
import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import Select from '../../components/Select'
import {
  hostingerImport,
  hostingerPreview,
  hostingerRelabel,
  type DomainConfidence,
  type HostingerDraft,
  type HostingerPreview as Preview,
} from '../../api/hostinger'
import { formatCurrency, formatDate } from '../../utils/formatters'
import { domainHint, shortDescription } from '../../utils/hostingerDomain'

const CATEGORY_LABEL: Record<string, string> = {
  hosting: 'Hosting', domain: 'Domain', software: 'Software', lizenz: 'Lizenz',
  hardware: 'Hardware', ki_api: 'KI-API', werbung: 'Werbung', buero: 'Büro',
  reise: 'Reise', sonstige: 'Sonstige',
}

interface Props {
  onClose: () => void
  onImported: () => void
}

/**
 * Domain der Zeile — mit Herkunft und Korrekturmöglichkeit.
 *
 * Bewusst kein reiner Text: die Zuordnung ist **abgeleitet** (die API verknüpft
 * Abo und Domain nicht), also muss sie sichtbar begründet und korrigierbar sein.
 * Eine Korrektur merkt sich der Server für künftige Läufe.
 */
function DomainCell({ draft, value, onPick, options }: {
  draft: HostingerDraft
  value: string
  onPick: (domain: string) => void
  options: string[]
}) {
  const [edit, setEdit] = useState(false)
  const changed = value !== (draft.domain ?? '')
  const hint = domainHint(
    changed ? 'confirmed' : (draft.domain_confidence as DomainConfidence | null),
    draft.domain_delta_seconds)
  const tone = hint.tone === 'ok' ? 'text-success'
    : hint.tone === 'warn' ? 'text-warning' : 'text-text-muted'
  // Domains derselben TLD zuerst — die Zuordnung wechselt praktisch nie die TLD.
  const choices = draft.domain_candidates.length
    ? [...draft.domain_candidates, ...options.filter((o) => !draft.domain_candidates.includes(o))]
    : options

  if (edit) {
    return (
      <Select
        compact
        value={value}
        options={choices.map((o) => ({ value: o, label: o }))}
        placeholder="— keine —"
        aria-label="Domain zuordnen"
        onChange={(e) => { onPick(e.target.value); setEdit(false) }}
      />
    )
  }
  return (
    <button type="button" onClick={() => setEdit(true)}
            title={`${hint.title} Klicken zum Ändern.`}
            className="md-state text-left rounded-xs px-1 -mx-1 max-w-[15rem] truncate">
      <span className={`mr-1 ${tone}`} aria-hidden>{hint.mark}</span>
      <span className={value ? 'text-text' : 'text-text-muted italic'}>
        {value || 'nicht zugeordnet'}
      </span>
    </button>
  )
}

export default function HostingerImportModal({ onClose, onImported }: Props) {
  const [preview, setPreview] = useState<Preview | null>(null)
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSkipped, setShowSkipped] = useState(false)
  const [openNotes, setOpenNotes] = useState<string | null>(null)
  // Korrekturen der Domain-Zuordnung: {subscription_id: domain}
  const [fixes, setFixes] = useState<Record<string, string>>({})

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !loading && !saving) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [loading, saving, onClose])

  const load = useCallback(async (): Promise<void> => {
    setLoading(true)
    try {
      const res = await hostingerPreview()
      setPreview(res)
      // Schon importierte Zeiträume nicht vorwählen.
      setPicked(new Set(res.drafts.filter((d) => !d.duplicate).map((d) => d.external_ref)))
      setFixes({})
      setError(null)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || 'Die Hostinger-Abfrage ist fehlgeschlagen.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

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
      const res = await hostingerImport([...picked], fixes)
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
  // Zeilen, deren Zuordnung nur über die Reihenfolge kam und die der Nutzer nicht
  // schon bestätigt hat.
  const needCheck = drafts.filter((d) => d.category === 'domain'
    && !fixes[d.subscription_id || '']
    && domainHint(d.domain_confidence, d.domain_delta_seconds).check).length
  // Bereits importierte Buchungen, deren gespeicherter Text vom aktuellen abweicht
  // (typisch: „Domain .de", bevor die Zuordnung möglich war).
  const stale = drafts.filter((d) => d.duplicate && d.imported_description
    && d.imported_description !== d.description)

  const relabel = async () => {
    if (saving || stale.length === 0) return
    setSaving(true)
    try {
      const res = await hostingerRelabel(stale.map((d) => d.external_ref), fixes)
      toast.success(`${res.updated} Buchung${res.updated === 1 ? '' : 'en'} umbenannt.`)
      onImported()
      await load()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Umbenennen fehlgeschlagen.')
    } finally {
      setSaving(false)
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={() => { if (!loading && !saving) onClose() }} />
      <div className="relative bg-surface-high rounded-dialog shadow-elev-3 p-5 sm:p-7
                      max-w-[900px] w-full mx-4 animate-modal-in max-h-[88vh] flex flex-col">
        <h3 className="text-lg font-semibold text-text mb-1">Hostinger-Kosten übernehmen</h3>
        <p className="text-xs text-text-muted mb-2">
          Je <strong className="text-text">aktivem Abo</strong> eine wiederkehrende Ausgabe,
          datiert auf die letzte Abrechnung. Die Hostinger-API liefert Verträge, keine
          Rechnungsbelege — vergangene Perioden werden deshalb nicht hochgerechnet.
        </p>
        <p className="text-xs text-text-muted mb-4">
          Die API sagt nicht, welche Domain zu welchem Abo gehört. Die Zuordnung ist
          <strong className="text-text"> aus der Bestellreihenfolge abgeleitet</strong>:
          <span className="text-success"> ≈</span> = Domain wenige Sekunden nach dem Abo
          registriert, also dieselbe Bestellung ·<span className="text-warning"> ?</span> =
          großer Abstand, bitte prüfen. Klick auf den Namen ändert die Zuordnung; die
          Korrektur wird für künftige Läufe gemerkt.
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
              {needCheck > 0 && (
                <span className="text-warning">· {needCheck} Zuordnung(en) prüfen</span>
              )}
              <span className="ml-auto text-text">
                Auswahl: <strong>{formatCurrency(sum)}</strong>
              </span>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto border border-border rounded-lg">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface-container">
                  <tr className="text-left text-xs text-text-muted">
                    <th className="px-3 py-2 w-8"></th>
                    <th className="px-2 py-2">Position</th>
                    <th className="px-2 py-2">Domain / Zuordnung</th>
                    <th className="px-2 py-2">Letzte Abrechnung</th>
                    <th className="px-2 py-2 text-right">Betrag</th>
                    <th className="px-2 py-2 w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {/* Key gehört auf das Fragment: es ist das Listenelement, nicht
                      die <tr> darin. Sonst warnt React und verliert beim
                      Auf-/Zuklappen der Notizen die Zeilenidentität. */}
                  {drafts.map((d) => (
                    <Fragment key={d.external_ref}>
                      <tr onClick={() => !d.duplicate && toggle(d.external_ref)}
                          className={`border-t border-border ${d.duplicate
                            ? 'opacity-50' : 'cursor-pointer hover:bg-surface-container'}`}>
                        <td className="px-3 py-1.5">
                          <input type="checkbox" checked={picked.has(d.external_ref)}
                                 disabled={d.duplicate}
                                 onChange={() => toggle(d.external_ref)}
                                 onClick={(e) => e.stopPropagation()} />
                        </td>
                        <td className="px-2 py-1.5 text-text">
                          {shortDescription(d.description, d.domain)}
                          <span className="ml-2 text-[10px] text-text-muted">
                            {CATEGORY_LABEL[d.category] || d.category}
                          </span>
                          {d.duplicate && (
                            <span className="ml-2 text-[10px] text-warning"
                                  title="Dieser Abrechnungszeitraum ist schon als Ausgabe erfasst">
                              bereits importiert
                            </span>
                          )}
                          {d.duplicate && d.imported_description
                           && d.imported_description !== d.description && (
                            <div className="text-[10px] text-text-muted mt-0.5">
                              gebucht als „{d.imported_description}" → wird
                              „{d.description}"
                            </div>
                          )}
                        </td>
                        <td className="px-2 py-1.5" onClick={(e) => e.stopPropagation()}>
                          {d.category === 'domain' ? <DomainCell
                            draft={d}
                            value={fixes[d.subscription_id || ''] ?? d.domain ?? ''}
                            onPick={(dom) => setFixes((prev) => ({
                              ...prev, [d.subscription_id || '']: dom }))}
                            options={preview.all_domains}
                          /> : <span className="text-text-muted">—</span>}
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
                        <tr className="border-t border-border">
                          <td />
                          <td colSpan={5} className="px-2 pb-2 pt-0">
                            <pre className="text-[11px] text-text-muted whitespace-pre-wrap
                                            font-sans">{d.notes}</pre>
                          </td>
                        </tr>
                      )}
                    </Fragment>
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
          {stale.length > 0 && (
            <button onClick={relabel} className="btn-secondary" disabled={saving}
                    title="Ändert nur Beschreibung und Notiz — Betrag, Datum und
                           Kategorie bleiben unverändert.">
              {saving ? 'Arbeite…' : `${stale.length} umbenennen`}
            </button>
          )}
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
