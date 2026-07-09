import { useEffect, useMemo, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { previewLinkedInImport, importLinkedInLeads } from '../../api/rainmaker'
import type { LinkedInPreviewRow } from '../../types'

interface Props {
  onClose: () => void
  onImported: () => void
}

const EXPORT_URL = 'https://www.linkedin.com/mypreferences/d/download-my-data'

/**
 * Importiert LinkedIn-Kontakte als Rainmaker-Leads — über LinkedIns
 * offiziellen, kostenlosen Datenexport (Connections.csv), ohne API.
 * Schritt 1: Anleitung + Upload. Schritt 2: Vorschau mit Auswahl
 * (Duplikate erkannt und standardmäßig abgewählt).
 */
export default function LinkedInImportModal({ onClose, onImported }: Props) {
  const [rows, setRows] = useState<LinkedInPreviewRow[] | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [uploading, setUploading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [filter, setFilter] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleFile = async (file: File | undefined) => {
    if (!file) return
    setUploading(true)
    try {
      const preview = await previewLinkedInImport(file)
      if (preview.length === 0) {
        toast.error('Keine Kontakte in der Datei gefunden.')
        setUploading(false)
        return
      }
      setRows(preview)
      // Neue Kontakte vorauswählen, Duplikate abgewählt
      setSelected(new Set(preview.map((r, i) => (r.duplicate ? -1 : i)).filter((i) => i >= 0)))
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Datei konnte nicht gelesen werden. Ist es die Connections.csv aus dem LinkedIn-Export?')
    }
    setUploading(false)
  }

  const visibleIdx = useMemo(() => {
    if (!rows) return []
    const q = filter.trim().toLowerCase()
    return rows
      .map((_, i) => i)
      .filter((i) => {
        if (!q) return true
        const r = rows[i]
        return `${r.first_name} ${r.last_name} ${r.company} ${r.position}`.toLowerCase().includes(q)
      })
  }, [rows, filter])

  const toggle = (i: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  const allVisibleSelected = visibleIdx.length > 0 && visibleIdx.every((i) => selected.has(i))
  const toggleAllVisible = () => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (allVisibleSelected) visibleIdx.forEach((i) => next.delete(i))
      else visibleIdx.forEach((i) => next.add(i))
      return next
    })
  }

  const handleImport = async () => {
    if (!rows || selected.size === 0 || importing) return
    setImporting(true)
    try {
      const chosen = [...selected].map((i) => rows[i])
      const result = await importLinkedInLeads(chosen)
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
      <div className="relative bg-surface-high rounded-xl shadow-elev-3 p-7 max-w-[680px] w-full mx-4 animate-md-scale max-h-[85vh] flex flex-col">
        <h3 className="text-xl font-semibold text-text mb-1">LinkedIn-Kontakte importieren</h3>
        <p className="text-xs text-text-muted mb-5">
          Über LinkedIns offiziellen Datenexport — kostenlos, ohne API, DSGVO-konform.
        </p>

        {!rows ? (
          <>
            <ol className="text-sm text-text space-y-2.5 mb-6 list-decimal list-inside">
              <li>
                Auf LinkedIn{' '}
                <a href={EXPORT_URL} target="_blank" rel="noreferrer" className="text-accent underline underline-offset-2">
                  „Kopie deiner Daten anfordern"
                </a>{' '}
                öffnen (Einstellungen → Datenschutz).
              </li>
              <li>„Bestimmte Daten" wählen und <strong>Kontakte / Connections</strong> ankreuzen → Archiv anfordern.</li>
              <li>Nach ca. 10–20 Minuten kommt eine E-Mail mit dem Download (ZIP mit <code className="text-xs bg-surface-container px-1.5 py-0.5 rounded">Connections.csv</code>).</li>
              <li>Die <code className="text-xs bg-surface-container px-1.5 py-0.5 rounded">Connections.csv</code> hier hochladen:</li>
            </ol>
            <input
              ref={fileInput}
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            <button
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
              className="w-full border-2 border-dashed border-border rounded-xl py-10 text-sm text-text-muted hover:border-accent hover:text-text transition-colors duration-short"
            >
              {uploading ? 'Wird gelesen…' : '📄 Connections.csv auswählen'}
            </button>
            <p className="text-[11px] text-text-muted mt-3">
              Hinweis: E-Mail-Adressen sind nur enthalten, wenn der Kontakt den Export erlaubt hat (meist leer).
              Kontakte ohne Firma werden mit dem Personennamen als Firma angelegt.
            </p>
            <div className="flex justify-end mt-6">
              <button onClick={onClose} className="btn-secondary">Abbrechen</button>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3 mb-3">
              <span className="text-sm text-text">
                <strong>{rows.length}</strong> Kontakte
                {dupCount > 0 && <span className="text-text-muted"> · {dupCount} bereits vorhanden</span>}
              </span>
              <input
                type="search"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filtern…"
                className="ml-auto text-sm w-44"
              />
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto border border-border rounded-lg">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface-container">
                  <tr className="text-left text-xs text-text-muted">
                    <th className="px-3 py-2 w-8">
                      <input type="checkbox" checked={allVisibleSelected} onChange={toggleAllVisible} />
                    </th>
                    <th className="px-2 py-2">Name</th>
                    <th className="px-2 py-2">Firma</th>
                    <th className="px-2 py-2">Position</th>
                    <th className="px-2 py-2 w-20"></th>
                  </tr>
                </thead>
                <tbody>
                  {visibleIdx.map((i) => {
                    const r = rows[i]
                    return (
                      <tr
                        key={i}
                        onClick={() => toggle(i)}
                        className={`border-t border-border cursor-pointer hover:bg-surface-container ${r.duplicate ? 'opacity-50' : ''}`}
                      >
                        <td className="px-3 py-1.5">
                          <input type="checkbox" checked={selected.has(i)} onChange={() => toggle(i)} onClick={(e) => e.stopPropagation()} />
                        </td>
                        <td className="px-2 py-1.5 text-text whitespace-nowrap">{r.first_name} {r.last_name}</td>
                        <td className="px-2 py-1.5 text-text-muted truncate max-w-[180px]">{r.company || '–'}</td>
                        <td className="px-2 py-1.5 text-text-muted truncate max-w-[180px]">{r.position || '–'}</td>
                        <td className="px-2 py-1.5 text-[10px]">
                          {r.duplicate && <span className="text-warning font-medium">Duplikat</span>}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between gap-2 mt-5">
              <button onClick={() => { setRows(null); setSelected(new Set()); setFilter('') }} className="btn-secondary" disabled={importing}>
                Andere Datei
              </button>
              <div className="flex gap-2">
                <button onClick={onClose} className="btn-secondary" disabled={importing}>Abbrechen</button>
                <button onClick={handleImport} className="btn-primary" disabled={selected.size === 0 || importing}>
                  {importing ? 'Importiere…' : `${selected.size} als Leads importieren`}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
