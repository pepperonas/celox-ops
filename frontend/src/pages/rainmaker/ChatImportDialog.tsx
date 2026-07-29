// „Aus Chat aktualisieren": Gesprächsmaterial einwerfen, KI schlägt vor, Mensch
// entscheidet. Es wird NICHTS geschrieben, bevor der Haken gesetzt und
// „Übernehmen" geklickt ist; danach ist der ganze Lauf widerrufbar.
//
// Screenshots werden im Browser verkleinert (utils/imageDownscale) — weniger
// Upload und EXIF/GPS fällt beim Re-Encode weg.
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import {
  chatImportApply,
  chatImportPreview,
  chatImportUndo,
  type ChatImportPreview as Preview,
} from '../../api/rainmaker'
import type { RainmakerLead } from '../../types'
import { ACTIVITY_TYPE_LABELS } from './constants'
import { downscaleImage, isAcceptedImage, MAX_EDGE_PX } from '../../utils/imageDownscale'
import { toastWithUndo } from '../../utils/undoToast'
import Icon from '../../components/Icon'

const MAX_IMAGES = 6
const eur = (n: number) =>
  n.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) + ' €'

interface Props {
  lead: RainmakerLead
  onClose: () => void
  onApplied: () => void
}

/** Eine auswählbare Vorschlagszeile. */
function Row({ checked, onToggle, children, muted = false }: {
  checked: boolean
  onToggle: () => void
  children: React.ReactNode
  muted?: boolean
}) {
  return (
    <label className={`flex gap-2.5 items-start px-2 py-1.5 rounded-sm cursor-pointer
                       hover:bg-surface-container ${muted ? 'opacity-60' : ''}`}>
      <input type="checkbox" checked={checked} onChange={onToggle} className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1 text-sm">{children}</div>
    </label>
  )
}

export default function ChatImportDialog({ lead, onClose, onApplied }: Props) {
  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [preview, setPreview] = useState<Preview | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !loading && !applying) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [loading, applying, onClose])

  const addFiles = async (incoming: FileList | File[]) => {
    const accepted = Array.from(incoming).filter(isAcceptedImage)
    const rejected = Array.from(incoming).length - accepted.length
    if (rejected > 0) toast.error(`${rejected} Datei(en) übersprungen — nur PNG, JPEG, WebP, GIF.`)
    const room = MAX_IMAGES - files.length
    if (room <= 0) { toast.error(`Maximal ${MAX_IMAGES} Screenshots.`); return }
    const shrunk = await Promise.all(accepted.slice(0, room).map((f) => downscaleImage(f)))
    setFiles((prev) => [...prev, ...shrunk])
  }

  const run = async () => {
    if (loading) return
    if (!text.trim() && files.length === 0) {
      setError('Bitte einen Chat-Verlauf einfügen oder Screenshots hochladen.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await chatImportPreview(lead.id, text, files)
      setPreview(res)
      const p = res.proposal
      setSelected(new Set([
        ...p.notes.filter((n) => n.preselected).map((n) => n.key),
        ...p.activities.filter((a) => a.preselected).map((a) => a.key),
        ...p.fields.filter((f) => f.preselected).map((f) => f.key),
        ...(p.next_action?.preselected ? [p.next_action.key] : []),
      ]))
    } catch (err) {
      const res = (err as { response?: { data?: { detail?: string } } })?.response
      setError(res?.data?.detail || 'Die KI-Auswertung ist fehlgeschlagen.')
    }
    setLoading(false)
  }

  const toggle = (key: string) => setSelected((prev) => {
    const next = new Set(prev)
    if (next.has(key)) next.delete(key); else next.add(key)
    return next
  })

  const total = useMemo(() => {
    if (!preview) return 0
    const p = preview.proposal
    return p.notes.length + p.activities.length + p.fields.length + (p.next_action ? 1 : 0)
  }, [preview])

  const apply = async () => {
    if (!preview || applying || selected.size === 0) return
    setApplying(true)
    try {
      const importId = preview.import_id
      const res = await chatImportApply(lead.id, importId, [...selected])
      const bits = [
        res.applied_activities ? `${res.applied_activities} Aktivität(en)` : '',
        res.applied_notes ? `${res.applied_notes} Notizzeile(n)` : '',
        res.applied_fields.length ? `${res.applied_fields.length} Feld(er)` : '',
        res.planned_next ? 'nächster Schritt' : '',
      ].filter(Boolean)
      toastWithUndo(`Übernommen: ${bits.join(' · ') || 'nichts'}.`, async () => {
        await chatImportUndo(lead.id, importId)
        onApplied()
      })
      onApplied()
      onClose()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Übernehmen fehlgeschlagen.')
      setApplying(false)
    }
  }

  const p = preview?.proposal

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={() => { if (!loading && !applying) onClose() }} />
      <div
        className={`relative bg-surface-high rounded-dialog shadow-elev-3 p-5 sm:p-7 max-w-[820px]
                    w-full mx-4 animate-modal-in max-h-[88vh] flex flex-col
                    ${dragOver ? 'ring-2 ring-accent' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files) }}
      >
        <h3 className="text-lg font-semibold text-text mb-1"><Icon name="sparkle" size={16} className="mr-1 -mt-0.5" /> Aus Chat aktualisieren</h3>
        <p className="text-xs text-text-muted mb-4">
          Verlauf einfügen und/oder Screenshots ablegen. Die KI schlägt vor —{' '}
          <strong className="text-text">geschrieben wird nur, was du anhakst</strong>.
        </p>

        {!p && (
          <div className="flex-1 min-h-0 overflow-y-auto space-y-3">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={8}
              placeholder="Chat-, WhatsApp- oder E-Mail-Verlauf hier einfügen …"
              className="w-full bg-surface-container border border-border rounded-lg px-3 py-2
                         text-sm text-text placeholder:text-text-muted resize-y"
            />
            <div className="border border-dashed border-border rounded-card p-4">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <button onClick={() => fileRef.current?.click()} className="btn-secondary text-xs"
                        disabled={files.length >= MAX_IMAGES}>
                  Screenshots wählen
                </button>
                <span className="text-[11px] text-text-muted">
                  oder hierher ziehen · max. {MAX_IMAGES} · werden auf {MAX_EDGE_PX} px verkleinert
                </span>
              </div>
              <input ref={fileRef} type="file" multiple accept="image/png,image/jpeg,image/webp,image/gif"
                     className="hidden"
                     onChange={(e) => { if (e.target.files) addFiles(e.target.files) }} />
              {files.length > 0 && (
                <ul className="space-y-1">
                  {files.map((f, i) => (
                    <li key={i} className="flex items-center gap-2 text-xs text-text-muted">
                      <span className="truncate flex-1">{f.name}</span>
                      <span className="tabular-nums shrink-0">{Math.round(f.size / 1024)} KB</span>
                      <button onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                              className="md-state w-6 h-6 grid place-items-center rounded-full
                                         hover:text-danger shrink-0" title="entfernen">×</button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <p className="text-[11px] text-text-muted">
              Hinweis: Text und Bilder werden zur Auswertung an Anthropic übertragen und können
              Daten Dritter enthalten. <strong className="text-text">Gespeichert wird das
              Rohmaterial nicht</strong> — nur die von dir übernommenen Auszüge landen am Lead.
            </p>
            {error && <p className="text-sm text-danger">{error}</p>}
          </div>
        )}

        {p && (
          <div className="flex-1 min-h-0 overflow-y-auto">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-3 text-xs">
              {p.summary && <span className="text-text">{p.summary}</span>}
              <span className="text-text-muted">{selected.size} von {total} gewählt</span>
              <span className="ml-auto text-text-muted" title="Kosten dieses Laufs">
                {preview?.cached ? 'aus Cache (0 €)' : eur(preview?.run.cost_eur ?? 0)}
                {' · Budget übrig: '}{eur(preview?.budget.remaining_eur ?? 0)}
              </span>
            </div>

            {p.activities.length > 0 && (
              <section className="mb-4">
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-1">
                  Aktivitäten ({p.activities.length})
                </h4>
                {p.activities.map((a) => (
                  <Row key={a.key} checked={selected.has(a.key)} onToggle={() => toggle(a.key)}
                       muted={a.duplicate}>
                    <div className="flex flex-wrap items-baseline gap-x-2">
                      <span className="text-text font-medium">
                        {ACTIVITY_TYPE_LABELS[a.type as keyof typeof ACTIVITY_TYPE_LABELS] || a.type}
                      </span>
                      <span className="text-text-muted tabular-nums">{a.day}</span>
                      {a.direction && <span className="text-text-muted">· {a.direction}</span>}
                      {a.duplicate && (
                        <span className="text-warning text-[11px]" title="Fingerprint schon am Lead">
                          bereits vorhanden
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-text-muted line-clamp-2">{a.excerpt}</p>
                  </Row>
                ))}
              </section>
            )}

            {p.next_action && (
              <section className="mb-4">
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-1">
                  Nächster Schritt
                </h4>
                <Row checked={selected.has(p.next_action.key)}
                     onToggle={() => toggle(p.next_action!.key)}>
                  <span className="text-text font-medium">
                    {ACTIVITY_TYPE_LABELS[p.next_action.type as keyof typeof ACTIVITY_TYPE_LABELS]
                      || p.next_action.type}
                  </span>{' '}
                  <span className="text-text-muted tabular-nums">bis {p.next_action.due_date}</span>
                  {p.next_action.reason && (
                    <p className="text-[11px] text-text-muted">{p.next_action.reason}</p>
                  )}
                </Row>
              </section>
            )}

            {p.notes.length > 0 && (
              <section className="mb-4">
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-1">
                  Notizen — werden angefügt, nichts ersetzt
                </h4>
                {p.notes.map((n) => (
                  <Row key={n.key} checked={selected.has(n.key)} onToggle={() => toggle(n.key)}>
                    <span className="text-text">{n.text}</span>
                  </Row>
                ))}
              </section>
            )}

            {p.fields.length > 0 && (
              <section className="mb-4">
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-1">
                  Stammdaten ({p.fields.length})
                </h4>
                {p.fields.map((f) => (
                  <Row key={f.key} checked={selected.has(f.key)} onToggle={() => toggle(f.key)}>
                    <div className="flex flex-wrap items-baseline gap-x-2">
                      <span className="text-text-muted">{f.label}:</span>
                      <span className="text-text-muted line-through break-words">{f.old}</span>
                      <span className="text-text-muted">→</span>
                      <span className="text-text font-medium break-words">{f.new}</span>
                      {f.field === 'status' && (
                        <span className="text-warning text-[11px]">bewusst nicht vorgewählt</span>
                      )}
                    </div>
                    {f.evidence && (
                      <p className="text-[11px] text-text-muted italic break-words">
                        Beleg: „{f.evidence}"
                      </p>
                    )}
                  </Row>
                ))}
              </section>
            )}

            {p.ignored.length > 0 && (
              <details className="mb-2 rounded-md border border-border">
                <summary className="px-2 py-1.5 text-xs text-text-muted cursor-pointer md-state">
                  {p.ignored.length} Vorschlag/Vorschläge ignoriert — Grund anzeigen
                </summary>
                <ul className="px-3 pb-2 space-y-0.5">
                  {p.ignored.map((ig, i) => (
                    <li key={i} className="text-[11px] text-text-muted">
                      <span className="text-text">{ig.label}</span>: {ig.reason}
                    </li>
                  ))}
                </ul>
              </details>
            )}

            {total === 0 && (
              <p className="text-sm text-text-muted py-6 text-center">
                Aus dem Material ließ sich nichts Belegbares ableiten.
              </p>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="btn-secondary" disabled={loading || applying}>
            Abbrechen
          </button>
          {!p ? (
            <button onClick={run} className="btn-primary" disabled={loading}>
              {loading ? 'KI wertet aus…' : 'Auswerten'}
            </button>
          ) : (
            <button onClick={apply} className="btn-primary"
                    disabled={selected.size === 0 || applying}>
              {applying ? 'Übernehme…' : `${selected.size} übernehmen`}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
