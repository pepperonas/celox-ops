import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import { discoverLeadsPreview, importDiscoveredLeads } from '../../api/rainmaker'
import {
  hasEmail, mergeCandidates, parseLocations, sortByQuality,
  type BatchCandidate,
} from './discoveryBatch'

interface Props {
  onClose: () => void
  onImported: () => void
}

const SEGMENTS: { key: string; label: string }[] = [
  { key: 'hausverwaltung', label: 'Hausverwaltung' },
  { key: 'steuerkanzlei', label: 'Steuerkanzlei' },
  { key: 'makler_finanzberater', label: 'Makler / Finanzberater' },
  { key: 'agentur', label: 'Agentur / IT-Dienstleister' },
  { key: 'anwalt', label: 'Anwaltskanzlei' },
  { key: 'arzt_praxis', label: 'Arzt-/Zahnarztpraxis' },
  { key: 'handwerk', label: 'Handwerksbetrieb' },
]
const LABEL = Object.fromEntries(SEGMENTS.map((s) => [s.key, s.label]))
const DELAY_MS = 800  // höfliche Pause zwischen Overpass-Abfragen

type ComboStatus = 'pending' | 'running' | 'done' | 'error'
interface Combo {
  segment: string
  location: string
  status: ComboStatus
  count?: number
  error?: string
}

/**
 * Batch-Lead-Suche: mehrere Branchen × mehrere Städte. Zieht alle Kombinationen
 * nacheinander (Live-Fortschritt), führt die Treffer mit Cross-Kombi-Dedup
 * zusammen und zeigt sie sortiert (kontaktfähige zuerst) zur Auswahl.
 */
export default function LeadDiscoveryModal({ onClose, onImported }: Props) {
  const [segments, setSegments] = useState<Set<string>>(new Set(['steuerkanzlei']))
  const [locationsInput, setLocationsInput] = useState('Berlin')
  const [limit, setLimit] = useState(50)
  const [source, setSource] = useState<'osm' | 'google'>('osm')

  const [combos, setCombos] = useState<Combo[] | null>(null)
  const [candidates, setCandidates] = useState<BatchCandidate[]>([])
  const [running, setRunning] = useState(false)
  const [onlyEmail, setOnlyEmail] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [importing, setImporting] = useState(false)
  const cancelRef = useRef(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape' && !running) onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose, running])

  const toggleSegment = (key: string) => setSegments((prev) => {
    const next = new Set(prev)
    next.has(key) ? next.delete(key) : next.add(key)
    return next
  })

  const run = async () => {
    const segs = [...segments]
    const locs = parseLocations(locationsInput)
    if (segs.length === 0 || locs.length === 0) {
      toast.error('Mindestens eine Branche und einen Ort wählen.')
      return
    }
    const plan: Combo[] = []
    for (const s of segs) for (const l of locs) plan.push({ segment: s, location: l, status: 'pending' })
    cancelRef.current = false
    setCombos(plan)
    setCandidates([])
    setSelected(new Set())
    setRunning(true)

    let acc: BatchCandidate[] = []
    for (let i = 0; i < plan.length; i++) {
      if (cancelRef.current) break
      setCombos((prev) => prev!.map((c, idx) => idx === i ? { ...c, status: 'running' } : c))
      try {
        const res = await discoverLeadsPreview({
          source, category: plan[i].segment, location: plan[i].location, limit,
        })
        acc = mergeCandidates(acc, res, plan[i].segment, `${LABEL[plan[i].segment] || plan[i].segment} · ${plan[i].location}`)
        setCandidates(acc)
        setCombos((prev) => prev!.map((c, idx) => idx === i ? { ...c, status: 'done', count: res.length } : c))
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        setCombos((prev) => prev!.map((c, idx) => idx === i ? { ...c, status: 'error', error: detail || 'Fehler' } : c))
      }
      if (i < plan.length - 1 && !cancelRef.current) await new Promise((r) => setTimeout(r, DELAY_MS))
    }
    // Nicht-Duplikate vorauswählen.
    setSelected(new Set(acc.filter((c) => !c.duplicate).map((c) => c._key)))
    setRunning(false)
  }

  const visible = useMemo(() => {
    const list = onlyEmail ? candidates.filter(hasEmail) : candidates
    return sortByQuality(list)
  }, [candidates, onlyEmail])

  const toggle = (key: string) => setSelected((prev) => {
    const next = new Set(prev)
    next.has(key) ? next.delete(key) : next.add(key)
    return next
  })

  const allVisibleSelected = visible.length > 0 && visible.every((c) => c.duplicate || selected.has(c._key))
  const toggleAll = () => setSelected((prev) => {
    const next = new Set(prev)
    const sel = visible.filter((c) => !c.duplicate)
    if (allVisibleSelected) sel.forEach((c) => next.delete(c._key))
    else sel.forEach((c) => next.add(c._key))
    return next
  })

  const doImport = async () => {
    if (selected.size === 0 || importing) return
    setImporting(true)
    try {
      const chosen = candidates.filter((c) => selected.has(c._key))
      // Pro Branche gruppieren, damit der richtige Segment-Tag gesetzt wird.
      const bySeg = new Map<string, BatchCandidate[]>()
      for (const c of chosen) (bySeg.get(c._segment) ?? bySeg.set(c._segment, []).get(c._segment)!).push(c)
      let created = 0, skipped = 0
      for (const [seg, rows] of bySeg) {
        const r = await importDiscoveredLeads(rows, seg)
        created += r.created
        skipped += r.skipped_duplicates
      }
      toast.success(`${created} Lead${created === 1 ? '' : 's'} importiert` +
        (skipped > 0 ? ` · ${skipped} Duplikate übersprungen` : '') + '.')
      onImported()
    } catch {
      toast.error('Import fehlgeschlagen.')
      setImporting(false)
    }
  }

  const done = combos !== null && !running
  const dupCount = candidates.filter((c) => c.duplicate).length
  const progress = combos ? combos.filter((c) => c.status === 'done' || c.status === 'error').length : 0

  // Per Portal an <body>, damit `position: fixed` immer relativ zum Viewport
  // liegt — ein transform-Vorfahre (Seiten-Übergang `.page-enter`) würde sonst
  // zum Bezugspunkt und das Panel verschieben/klippen (Dialog „unsichtbar" bis
  // Refresh).
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={() => { if (!running) onClose() }} />
      <div className="relative bg-surface-high rounded-xl shadow-elev-3 p-7 max-w-[880px] w-full mx-4 animate-modal-in max-h-[88vh] flex flex-col">
        <h3 className="text-xl font-semibold text-text mb-1">Leads finden</h3>
        <p className="text-xs text-text-muted mb-4">
          Mehrere Branchen und Orte auf einmal — kostenlos über OpenStreetMap.
        </p>

        {/* Konfiguration */}
        <div className="space-y-3 mb-4">
          <div>
            <label className="block text-xs text-text-muted mb-1.5">Branchen</label>
            <div className="flex flex-wrap gap-2">
              {SEGMENTS.map((s) => (
                <button key={s.key} onClick={() => toggleSegment(s.key)} disabled={running}
                  className={`text-xs px-3 py-1.5 rounded-full border transition-colors duration-short ${
                    segments.has(s.key) ? 'border-accent bg-accent/15 text-text' : 'border-border text-text-muted hover:text-text'
                  }`}>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[220px]">
              <label className="block text-xs text-text-muted mb-1.5">Orte / Bezirke (mehrere durch Komma)</label>
              <input value={locationsInput} onChange={(e) => setLocationsInput(e.target.value)} disabled={running}
                onKeyDown={(e) => { if (e.key === 'Enter' && !running) run() }}
                placeholder="Berlin, Potsdam, München" className="text-sm w-full" />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1.5">Max. je Suche</label>
              <select value={limit} onChange={(e) => setLimit(Number(e.target.value))} disabled={running} className="text-sm">
                {[25, 50, 100, 200].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1.5">Quelle</label>
              <select value={source} onChange={(e) => setSource(e.target.value as 'osm' | 'google')} disabled={running} className="text-sm">
                <option value="osm">OpenStreetMap</option>
                <option value="google">Google Places</option>
              </select>
            </div>
            {running
              ? <button onClick={() => { cancelRef.current = true }} className="btn-secondary text-sm">Stoppen</button>
              : <button onClick={run} className="btn-primary text-sm">
                  {combos ? 'Neu suchen' : 'Suchen'} ({segments.size}×{parseLocations(locationsInput).length})
                </button>}
          </div>
        </div>

        {/* Fortschritt pro Kombination */}
        {combos && (
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs text-text-muted mb-1.5">
              <span>{running ? 'Suche läuft…' : 'Suche abgeschlossen'}</span>
              <span>{progress}/{combos.length} Kombinationen · {candidates.length} Treffer</span>
            </div>
            <div className="h-1.5 bg-surface-container rounded-full overflow-hidden mb-2">
              <div className="h-full bg-accent transition-all duration-short" style={{ width: `${(progress / combos.length) * 100}%` }} />
            </div>
            <div className="max-h-24 overflow-y-auto text-xs space-y-0.5 pr-1">
              {combos.map((c, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-text-muted">
                    {c.status === 'done' ? '✓' : c.status === 'running' ? '◷' : c.status === 'error' ? '✕' : '·'}{' '}
                    {LABEL[c.segment] || c.segment} · {c.location}
                  </span>
                  <span className={c.status === 'error' ? 'text-danger' : 'text-text-muted'}>
                    {c.status === 'done' ? `${c.count} gefunden` : c.status === 'error' ? (c.error || 'Fehler')
                      : c.status === 'running' ? 'läuft…' : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Ergebnis-Tabelle */}
        {done && candidates.length > 0 && (
          <>
            <div className="flex flex-wrap items-center gap-3 mb-2 text-sm">
              <span className="text-text"><strong>{candidates.length}</strong> Firmen</span>
              <span className="text-success text-xs" title="Nur Firmen mit erreichbarer Website (Live-Check); OSM zusätzlich mit E-Mail. Keine Karteileichen.">✓ geprüft</span>
              {dupCount > 0 && <span className="text-text-muted">· {dupCount} bereits als Lead</span>}
              <label className="flex items-center gap-1.5 text-xs text-text-muted cursor-pointer">
                <input type="checkbox" checked={onlyEmail} onChange={(e) => setOnlyEmail(e.target.checked)} />
                nur mit E-Mail
              </label>
              <span className="ml-auto text-text-muted text-xs">{selected.size} ausgewählt</span>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto border border-border rounded-lg">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface-container">
                  <tr className="text-left text-xs text-text-muted">
                    <th className="px-3 py-2 w-8"><input type="checkbox" checked={allVisibleSelected} onChange={toggleAll} /></th>
                    <th className="px-2 py-2">Firma</th>
                    <th className="px-2 py-2">Branche · Ort</th>
                    <th className="px-2 py-2">Website</th>
                    <th className="px-2 py-2">E-Mail</th>
                    <th className="px-2 py-2 w-16"></th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((c) => (
                    <tr key={c._key} onClick={() => !c.duplicate && toggle(c._key)}
                        className={`border-t border-border ${c.duplicate ? 'opacity-50' : 'cursor-pointer hover:bg-surface-container'}`}>
                      <td className="px-3 py-1.5">
                        <input type="checkbox" checked={selected.has(c._key)} disabled={c.duplicate}
                               onChange={() => toggle(c._key)} onClick={(e) => e.stopPropagation()} />
                      </td>
                      <td className="px-2 py-1.5 text-text truncate max-w-[200px]">{c.name}</td>
                      <td className="px-2 py-1.5 text-text-muted truncate max-w-[150px]">{c._combo}</td>
                      <td className="px-2 py-1.5 text-text-muted truncate max-w-[150px]">
                        {c.website ? c.website.replace(/^https?:\/\//, '').replace(/\/$/, '') : (c.phone || '–')}
                      </td>
                      <td className="px-2 py-1.5 text-text-muted truncate max-w-[150px]">
                        {c.email ? <span className="text-success">✉ {c.email}</span> : <span className="opacity-50">–</span>}
                      </td>
                      <td className="px-2 py-1.5 text-[10px]">
                        {c.duplicate && <span className="text-warning font-medium">vorhanden</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {done && candidates.length === 0 && (
          <p className="text-sm text-text-muted py-6 text-center">Keine Treffer. Andere Branchen oder Orte versuchen.</p>
        )}

        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="btn-secondary" disabled={running || importing}>
            {done && candidates.length ? 'Abbrechen' : 'Schließen'}
          </button>
          {done && candidates.length > 0 && (
            <button onClick={doImport} className="btn-primary" disabled={selected.size === 0 || importing}>
              {importing ? 'Importiere…' : `${selected.size} als Leads anlegen`}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
