import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { discoverLeadsPreview, importDiscoveredLeads } from '../../api/rainmaker'
import type { DiscoveredCandidate } from '../../types'

interface Props {
  onClose: () => void
  onImported: () => void
}

// Segment-Presets (spiegeln SEGMENT_OSM_TAGS im Backend).
const SEGMENTS: { key: string; label: string }[] = [
  { key: 'hausverwaltung', label: 'Hausverwaltung' },
  { key: 'steuerkanzlei', label: 'Steuerkanzlei' },
  { key: 'makler_finanzberater', label: 'Makler / Finanzberater' },
  { key: 'agentur', label: 'Agentur / IT-Dienstleister' },
  { key: 'anwalt', label: 'Anwaltskanzlei' },
  { key: 'arzt_praxis', label: 'Arzt-/Zahnarztpraxis' },
  { key: 'handwerk', label: 'Handwerksbetrieb' },
]

/**
 * Automatische Lead-Suche: Branche + Ort → Vorschau (Duplikate markiert) →
 * Auswahl → Import. Quelle OpenStreetMap (kostenlos) oder Google Places
 * (falls serverseitig ein Key hinterlegt ist — sonst 503, Hinweis unten).
 */
export default function LeadDiscoveryModal({ onClose, onImported }: Props) {
  const [source, setSource] = useState<'osm' | 'google'>('osm')
  const [segment, setSegment] = useState('steuerkanzlei')
  const [location, setLocation] = useState('Berlin')
  const [rows, setRows] = useState<DiscoveredCandidate[] | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [searching, setSearching] = useState(false)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const search = async () => {
    if (!location.trim() || searching) return
    setSearching(true)
    try {
      const res = await discoverLeadsPreview({ source, category: segment, location: location.trim(), limit: 60 })
      if (res.length === 0) {
        toast.error('Keine Treffer. Anderen Ort oder andere Branche versuchen.')
      }
      setRows(res)
      // Neue (nicht-Duplikate) vorauswählen
      setSelected(new Set(res.map((r, i) => (r.duplicate ? -1 : i)).filter((i) => i >= 0)))
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Suche fehlgeschlagen.')
    }
    setSearching(false)
  }

  const toggle = (i: number) => setSelected((prev) => {
    const next = new Set(prev)
    next.has(i) ? next.delete(i) : next.add(i)
    return next
  })

  const allNewSelected = useMemo(() => {
    if (!rows) return false
    const newIdx = rows.map((r, i) => (r.duplicate ? -1 : i)).filter((i) => i >= 0)
    return newIdx.length > 0 && newIdx.every((i) => selected.has(i))
  }, [rows, selected])

  const toggleAll = () => {
    if (!rows) return
    setSelected((prev) => {
      const next = new Set(prev)
      const newIdx = rows.map((r, i) => (r.duplicate ? -1 : i)).filter((i) => i >= 0)
      if (allNewSelected) newIdx.forEach((i) => next.delete(i))
      else newIdx.forEach((i) => next.add(i))
      return next
    })
  }

  const doImport = async () => {
    if (!rows || selected.size === 0 || importing) return
    setImporting(true)
    try {
      const chosen = [...selected].map((i) => rows[i])
      const result = await importDiscoveredLeads(chosen, segment)
      toast.success(
        `${result.created} Lead${result.created === 1 ? '' : 's'} importiert` +
        (result.skipped_duplicates > 0 ? ` · ${result.skipped_duplicates} Duplikate übersprungen` : '') + '.'
      )
      onImported()
    } catch {
      toast.error('Import fehlgeschlagen.')
      setImporting(false)
    }
  }

  const dupCount = rows?.filter((r) => r.duplicate).length ?? 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={onClose} />
      <div className="relative bg-surface-high rounded-xl shadow-elev-3 p-7 max-w-[860px] w-full mx-4 animate-md-scale max-h-[85vh] flex flex-col">
        <h3 className="text-xl font-semibold text-text mb-1">Leads finden</h3>
        <p className="text-xs text-text-muted mb-5">
          Passende Firmen automatisch nach Branche und Ort suchen — kostenlos über OpenStreetMap.
        </p>

        {/* Suchformular */}
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <div>
            <label className="block text-xs text-text-muted mb-1">Branche</label>
            <select value={segment} onChange={(e) => setSegment(e.target.value)} className="text-sm">
              {SEGMENTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Ort / Bezirk</label>
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') search() }}
              placeholder="z. B. Berlin, Pankow, München"
              className="text-sm w-48"
            />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Quelle</label>
            <select value={source} onChange={(e) => setSource(e.target.value as 'osm' | 'google')} className="text-sm">
              <option value="osm">OpenStreetMap</option>
              <option value="google">Google Places</option>
            </select>
          </div>
          <button onClick={search} disabled={searching || !location.trim()} className="btn-primary text-sm">
            {searching ? 'Suche…' : 'Suchen'}
          </button>
        </div>

        {rows && (
          <>
            <div className="flex items-center gap-3 mb-2 text-sm">
              <span className="text-text"><strong>{rows.length}</strong> Treffer</span>
              {dupCount > 0 && <span className="text-text-muted">· {dupCount} bereits als Lead</span>}
              <span className="ml-auto text-text-muted text-xs">{selected.size} ausgewählt</span>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto border border-border rounded-lg">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface-container">
                  <tr className="text-left text-xs text-text-muted">
                    <th className="px-3 py-2 w-8"><input type="checkbox" checked={allNewSelected} onChange={toggleAll} /></th>
                    <th className="px-2 py-2">Firma</th>
                    <th className="px-2 py-2">Adresse</th>
                    <th className="px-2 py-2">Website</th>
                    <th className="px-2 py-2 w-20"></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} onClick={() => toggle(i)}
                        className={`border-t border-border cursor-pointer hover:bg-surface-container ${r.duplicate ? 'opacity-50' : ''}`}>
                      <td className="px-3 py-1.5">
                        <input type="checkbox" checked={selected.has(i)} onChange={() => toggle(i)} onClick={(e) => e.stopPropagation()} />
                      </td>
                      <td className="px-2 py-1.5 text-text whitespace-nowrap max-w-[220px] truncate">{r.name}</td>
                      <td className="px-2 py-1.5 text-text-muted truncate max-w-[200px]">{r.address || '–'}</td>
                      <td className="px-2 py-1.5 text-text-muted truncate max-w-[160px]">
                        {r.website ? r.website.replace(/^https?:\/\//, '') : '–'}
                      </td>
                      <td className="px-2 py-1.5 text-[10px]">
                        {r.duplicate && <span className="text-warning font-medium">vorhanden</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        <p className="text-[11px] text-text-muted mt-3">
          Hinweis: Nicht jede Firma hat in OpenStreetMap Website/Telefon hinterlegt — diese Felder ergänzt
          du später beim Lead. „Google Places" braucht einen serverseitigen API-Key.
        </p>
        <div className="flex justify-between gap-2 mt-5">
          {rows
            ? <button onClick={() => { setRows(null); setSelected(new Set()) }} className="btn-secondary" disabled={importing}>Neue Suche</button>
            : <span />}
          <div className="flex gap-2">
            <button onClick={onClose} className="btn-secondary" disabled={importing}>Abbrechen</button>
            {rows && (
              <button onClick={doImport} className="btn-primary" disabled={selected.size === 0 || importing}>
                {importing ? 'Importiere…' : `${selected.size} als Leads anlegen`}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
