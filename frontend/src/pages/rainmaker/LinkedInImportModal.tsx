import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import { previewLinkedInImport, importLinkedInLeads } from '../../api/rainmaker'
import type { LinkedInPreviewRow } from '../../types'
import { STATUS_LABELS } from './constants'

interface Props {
  onClose: () => void
  onImported: (created: number) => void
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
  const [sourceFilter, setSourceFilter] = useState<'all' | 'connection' | 'invitation'>('all')
  const [dragOver, setDragOver] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  // Solange der Dialog offen ist, verhindern, dass ein daneben abgelegtes ZIP
  // vom Browser geöffnet wird (Standardverhalten = zur Datei navigieren).
  useEffect(() => {
    const prevent = (e: DragEvent) => { e.preventDefault() }
    window.addEventListener('dragover', prevent)
    window.addEventListener('drop', prevent)
    return () => {
      window.removeEventListener('dragover', prevent)
      window.removeEventListener('drop', prevent)
    }
  }, [])

  // Gemeinsamer Drop-Handler für Panel + Button.
  const handleDroppedFile = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (!file) return
    const name = file.name.toLowerCase()
    if (!name.endsWith('.csv') && !name.endsWith('.zip')) {
      toast.error('Bitte das Export-ZIP oder die Connections.csv ablegen.')
      return
    }
    handleFile(file)
  }

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
      // Bestätigte Kontakte vorauswählen; offene Anfragen abgewählt.
      // Duplikate MIT Nachrichtenverlauf ebenfalls vorwählen — die werden nicht
      // doppelt angelegt, sondern angereichert (Status + Verlauf nachgezogen).
      setSelected(new Set(preview.map((r, i) => {
        if (r.duplicate) return r.message_count > 0 ? i : -1
        return r.source === 'connection' ? i : -1
      }).filter((i) => i >= 0)))
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
        const r = rows[i]
        if (sourceFilter !== 'all' && r.source !== sourceFilter) return false
        if (!q) return true
        return `${r.first_name} ${r.last_name} ${r.company} ${r.position}`.toLowerCase().includes(q)
      })
  }, [rows, filter, sourceFilter])

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
        (result.enriched > 0 ? ` · ${result.enriched} bestehende angereichert` : '') +
        (result.activities_created > 0 ? ` · ${result.activities_created} Nachrichten als Aktivitäten` : '') +
        (result.skipped_duplicates > 0 ? ` · ${result.skipped_duplicates} unverändert` : '') + '.'
      )
      onImported(result.created)
    } catch {
      toast.error('Import fehlgeschlagen.')
      setImporting(false)
    }
  }

  const dupCount = rows?.filter((r) => r.duplicate).length ?? 0
  const connCount = rows?.filter((r) => r.source === 'connection').length ?? 0
  const invCount = rows?.filter((r) => r.source === 'invitation').length ?? 0
  const msgCount = rows?.filter((r) => r.message_count > 0).length ?? 0

  // Portal an <body>: hält `position: fixed` viewport-relativ, unabhängig von
  // transform-Vorfahren (Seiten-Übergang `.page-enter`).
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={onClose} />
      <div
        className={`relative bg-surface-high rounded-xl shadow-elev-3 p-7 max-w-[900px] w-full mx-4 animate-modal-in max-h-[85vh] flex flex-col transition-all duration-short ${
          !rows && dragOver ? 'ring-2 ring-accent ring-offset-2 ring-offset-black/60' : ''
        }`}
        onDragOver={!rows ? (e) => { e.preventDefault(); setDragOver(true) } : undefined}
        onDragLeave={!rows ? (e) => {
          // Nur zurücksetzen, wenn der Cursor das Panel wirklich verlässt
          if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOver(false)
        } : undefined}
        onDrop={!rows ? handleDroppedFile : undefined}
      >
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
                  „Ihre Daten herunterladen"
                </a>{' '}
                öffnen (Einstellungen → Datenschutz).
              </li>
              <li>
                Das <strong>größere Datenarchiv</strong> (erste Option, enthält die Kontakte) wählen → „Archiv anfordern".
                Falls in der „Bestimmte Daten"-Auswahl <strong>Kontakte</strong> angeboten wird, reicht auch das.
              </li>
              <li>Nach ca. 10–20 Minuten kommt eine E-Mail mit dem Download-Link (bei großen Archiven bis 24 h).</li>
              <li>Das <strong>komplette ZIP direkt hochladen</strong> (kein Entpacken nötig) — daraus liest ops Kontakte, offene Kontaktanfragen und den Nachrichtenverlauf. Alternativ geht auch die einzelne <code className="text-xs bg-surface-container px-1.5 py-0.5 rounded">Connections.csv</code>:</li>
            </ol>
            <input
              ref={fileInput}
              type="file"
              accept=".zip,.csv,application/zip,text/csv"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            <button
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDrop={handleDroppedFile}
              className={`w-full border-2 border-dashed rounded-xl py-10 text-sm transition-colors duration-short ${
                dragOver
                  ? 'border-accent bg-accent/10 text-text'
                  : 'border-border text-text-muted hover:border-accent hover:text-text'
              }`}
            >
              {uploading
                ? 'Wird gelesen…'
                : dragOver
                  ? '📥 Loslassen zum Hochladen'
                  : '📦 Export-ZIP oder Connections.csv hierher ziehen — oder klicken'}
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
            <div className="flex flex-wrap items-center gap-2 mb-3">
              {([
                ['all', `Alle (${rows.length})`],
                ['connection', `Kontakte (${connCount})`],
                ['invitation', `Anfragen offen (${invCount})`],
              ] as const).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setSourceFilter(key)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition-colors duration-short ${
                    sourceFilter === key ? 'border-accent bg-accent/15 text-text' : 'border-border text-text-muted hover:text-text'
                  }`}
                >
                  {label}
                </button>
              ))}
              <span className="text-xs text-text-muted">
                {msgCount > 0 && <>💬 {msgCount} im Gespräch · </>}
                {dupCount > 0 && <>{dupCount} bereits vorhanden</>}
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
                    <th className="px-2 py-2">Status</th>
                    <th className="px-2 py-2 w-24"></th>
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
                        <td className="px-2 py-1.5 text-text-muted truncate max-w-[160px]">{r.position || '–'}</td>
                        <td className="px-2 py-1.5 text-xs text-text-muted whitespace-nowrap">
                          {STATUS_LABELS[r.status]}
                          {r.message_count > 0 && <span className="ml-1" title={`${r.message_count} Nachrichten`}>💬{r.message_count}</span>}
                        </td>
                        <td className="px-2 py-1.5 text-[10px]">
                          {r.duplicate && (
                            <span className={r.message_count > 0 ? 'text-accent font-medium' : 'text-warning font-medium'}>
                              {r.message_count > 0 ? 'wird angereichert' : 'Duplikat'}
                            </span>
                          )}
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
    </div>,
    document.body,
  )
}
