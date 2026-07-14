import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import { importDiscoveredLeads } from '../../api/rainmaker'
import type { DiscoveredCandidate } from '../../types'
import { emailStatusInfo } from './emailStatus'
import { matchBriefs } from './briefSuggestions'
import type { AiLeadRun } from './aiLeadRun'

interface Props {
  run: AiLeadRun
  onClose: () => void
  onDiscard: () => void
  onImported: (created: number) => void
}

const REASON_LABEL: Record<string, string> = { email: 'E-Mail', website: 'Website', name: 'Name' }
const eur = (n: number) => n.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) + ' €'

export default function AiLeadModal({ run, onClose, onDiscard, onImported }: Props) {
  // Suchzustand kommt aus dem globalen Store (überlebt Minimieren + Seitenwechsel); nur UI-State ist lokal.
  const { brief, setBrief, useWeb, setUseWeb, running, ranWeb, res, elapsed, phase, phaseLabels } = run
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [importing, setImporting] = useState(false)
  const [showSug, setShowSug] = useState(false)
  const suggestions = useMemo(() => matchBriefs(brief, 6), [brief])

  // Ergebnis kann aus einem Hintergrundlauf kommen (Dialog war zu) → Auswahl
  // beim (Wieder-)Auftauchen von Kandidaten neu setzen: Nicht-Duplikate vorwählen.
  useEffect(() => {
    if (!res) { setSelected(new Set()); return }
    setSelected(new Set(res.candidates.map((c, i) => (c.duplicate ? -1 : i)).filter((i) => i >= 0)))
  }, [res])

  const toggle = (i: number) => setSelected((prev) => {
    const n = new Set(prev); n.has(i) ? n.delete(i) : n.add(i); return n
  })

  const doImport = async () => {
    if (!res || selected.size === 0 || importing) return
    setImporting(true)
    try {
      const rows: DiscoveredCandidate[] = [...selected].map((i) => res.candidates[i])
      // Kein Batch-Segment: die Branche steckt pro Kandidat in `segment` (→ Lead-Tag).
      const r = await importDiscoveredLeads(rows)
      toast.success(`${r.created} Lead${r.created === 1 ? '' : 's'} importiert`
        + (r.skipped_duplicates > 0 ? ` · ${r.skipped_duplicates} Duplikate übersprungen` : '') + '.')
      onImported(r.created)
    } catch {
      toast.error('Import fehlgeschlagen.')
      setImporting(false)
    }
  }

  const dupCount = useMemo(() => res?.candidates.filter((c) => c.duplicate).length ?? 0, [res])
  const hasResults = !!res && res.candidates.length > 0

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={() => { if (!importing) onClose() }} />
      <div className="relative bg-surface-high rounded-xl shadow-elev-3 p-7 max-w-[900px] w-full mx-4 animate-modal-in max-h-[88vh] flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-text">✨ KI-Lead-Suche</h3>
          {res && (
            <span className="text-xs text-text-muted" title="Kosten dieses Laufs (aus der API-Nutzung berechnet)">
              Lauf: <strong className="text-text">{eur(res.run.cost_eur)}</strong>
              {' · '}Budget übrig: {eur(res.budget.remaining_eur)}
              {res.budget.warn && <span className="text-warning"> ⚠</span>}
            </span>
          )}
        </div>

        <div className="relative mb-2">
          <textarea
            value={brief}
            onChange={(e) => { setBrief(e.target.value); setShowSug(true) }}
            onFocus={() => setShowSug(true)}
            onBlur={() => setTimeout(() => setShowSug(false), 150)}
            placeholder="Beschreibe deine Wunschkunden, z. B.: „10 mittelständische Hausverwaltungen in Berlin mit E-Mail und Website“ — oder tippen und einen Vorschlag wählen."
            rows={3}
            className="w-full bg-surface-container border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-muted resize-none"
          />
          {showSug && !running && suggestions.length > 0 && (
            <ul className="absolute z-10 left-0 right-0 mt-1 bg-surface-high border border-border rounded-lg shadow-elev-3 max-h-60 overflow-y-auto">
              <li className="px-3 pt-2 pb-1 text-[10px] uppercase tracking-wide text-text-muted">Vorschläge</li>
              {suggestions.map((s, i) => (
                <li key={i}>
                  <button
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => { setBrief(s); setShowSug(false) }}
                    className="w-full text-left px-3 py-2 text-sm text-text hover:bg-surface-container transition-colors duration-short"
                  >
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <button onClick={run.run} disabled={running || !brief.trim()} className="btn-primary text-sm disabled:opacity-40">
            {running ? 'KI recherchiert…' : 'Leads finden'}
          </button>
          <label className="flex items-center gap-1.5 text-xs text-text-muted cursor-pointer" title="Zusätzlich das Web durchsuchen — findet mehr, kostet aber API-Geld (~0,30–0,60 $/Lauf).">
            <input type="checkbox" checked={useWeb} onChange={(e) => setUseWeb(e.target.checked)} />
            auch Web durchsuchen <span className="text-[10px]">(kostet mehr)</span>
          </label>
          <span className="text-xs text-text-muted">OSM{useWeb ? ' + Web' : ''} · Website &amp; E-Mail geprüft · Fit-Ranking durch Claude.</span>
        </div>

        {running && (
          <div className="rounded-lg bg-surface-container border border-border p-3 mb-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-text font-medium">KI-Recherche läuft…</span>
              <span className="text-xs text-text-muted tabular-nums">{elapsed}s</span>
            </div>
            <ol className="space-y-1.5">
              {phaseLabels.map((label, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  {i < phase
                    ? <span className="text-success w-3.5 text-center">✓</span>
                    : i === phase
                      ? <span className="inline-block w-3.5 h-3.5 rounded-full border-2 border-accent border-t-transparent animate-spin" />
                      : <span className="inline-block w-3.5 h-3.5 rounded-full border border-border" />}
                  <span className={i < phase ? 'text-text-muted' : i === phase ? 'text-text font-medium' : 'text-text-muted opacity-60'}>{label}</span>
                </li>
              ))}
            </ol>
            {ranWeb && <p className="text-[11px] text-text-muted mt-2">Die Web-Suche kann bis zu ~1 Minute dauern.</p>}
            <p className="text-[11px] text-accent mt-2">Du kannst den Dialog schließen — die Suche läuft im Hintergrund weiter und öffnet sich bei Fertigstellung wieder.</p>
          </div>
        )}

        {res?.notes?.length ? (
          <div className="text-xs text-warning mb-2">{res.notes.join(' · ')}</div>
        ) : null}

        {res && res.candidates.length > 0 && (
          <>
            <div className="flex flex-wrap items-center gap-3 mb-2 text-sm">
              <span className="text-text"><strong>{res.candidates.length}</strong> Kandidaten</span>
              <span className="text-success text-xs">✓ geprüft</span>
              {dupCount > 0 && <span className="text-text-muted">· {dupCount} bereits als Lead</span>}
              <span className="ml-auto text-text-muted text-xs">{selected.size} ausgewählt</span>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto border border-border rounded-lg">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface-container">
                  <tr className="text-left text-xs text-text-muted">
                    <th className="px-3 py-2 w-8"></th>
                    <th className="px-2 py-2">Firma</th>
                    <th className="px-2 py-2">Fit</th>
                    <th className="px-2 py-2">Website</th>
                    <th className="px-2 py-2">E-Mail</th>
                    <th className="px-2 py-2 w-16"></th>
                  </tr>
                </thead>
                <tbody>
                  {res.candidates.map((c, i) => {
                    const info = emailStatusInfo(c.email_status)
                    return (
                      <tr key={i} onClick={() => !c.duplicate && toggle(i)}
                          className={`border-t border-border ${c.duplicate ? 'opacity-50' : 'cursor-pointer hover:bg-surface-container'}`}>
                        <td className="px-3 py-1.5">
                          <input type="checkbox" checked={selected.has(i)} disabled={c.duplicate}
                                 onChange={() => toggle(i)} onClick={(e) => e.stopPropagation()} />
                        </td>
                        <td className="px-2 py-1.5 text-text truncate max-w-[160px]">{c.name}</td>
                        <td className="px-2 py-1.5 text-text-muted truncate max-w-[220px]" title={c.fit_reason || ''}>{c.fit_reason || '–'}</td>
                        <td className="px-2 py-1.5 text-text-muted truncate max-w-[140px]">{c.website?.replace(/^https?:\/\//, '').replace(/\/$/, '') || '–'}</td>
                        <td className="px-2 py-1.5 text-text-muted truncate max-w-[150px]">
                          {c.email}{info && <span className={`ml-1 text-[10px] ${info.cls}`}>·{info.label}</span>}
                        </td>
                        <td className="px-2 py-1.5 text-[10px]">
                          {c.duplicate && <span className="text-warning font-medium" title={`vorhanden (${REASON_LABEL[c.duplicate_reason || ''] || 'Treffer'})`}>vorhanden</span>}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
        {res && res.candidates.length === 0 && (
          <p className="text-sm text-text-muted py-6 text-center">Keine passenden Treffer. Brief anpassen und erneut versuchen.</p>
        )}

        <div className="flex justify-end gap-2 mt-4">
          {hasResults && (
            <button onClick={onDiscard} className="btn-secondary !text-danger" disabled={importing} title="Ergebnisse endgültig verwerfen">
              Verwerfen
            </button>
          )}
          <button onClick={onClose} className="btn-secondary" disabled={importing}
                  title={hasResults || running ? 'Dialog schließen — Ergebnisse bleiben erhalten (Pill unten rechts)' : undefined}>
            {running || hasResults ? 'Minimieren' : 'Schließen'}
          </button>
          {hasResults && (
            <button onClick={doImport} className="btn-primary" disabled={selected.size === 0 || importing}>
              {importing ? 'Importiere…' : `${selected.size} importieren`}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
