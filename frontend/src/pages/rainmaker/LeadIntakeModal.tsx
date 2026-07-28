// „Aus Chat/Screenshot": Material einwerfen, die KI macht Lead-Entwürfe daraus,
// der Mensch bestätigt. Zwei Schritte — Schritt 2 schreibt nur, was angehakt ist.
//
// Abgrenzung: der Chat-Import im Lead-Detail AKTUALISIERT einen bestehenden Lead;
// hier entstehen NEUE Leads (auch mehrere aus einem Material).
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import { leadIntakeCommit, leadIntakePreview } from '../../api/rainmaker'
import type { LeadIntakeDraft, LeadIntakeResponse } from '../../types'
import { downscaleToDataUrl, isAcceptedImage, MAX_EDGE_PX } from '../../utils/imageDownscale'
import { ACTIVITY_TYPE_LABELS, STATUS_LABELS } from './constants'

const MAX_IMAGES = 6
const eur = (n: number) =>
  n.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) + ' €'

interface Props {
  onClose: () => void
  onImported: (created: number) => void
}

interface Shot { id: string; dataUrl: string; name: string; kb: number }

export default function LeadIntakeModal({ onClose, onImported }: Props) {
  const [text, setText] = useState('')
  const [hint, setHint] = useState('')
  const [website, setWebsite] = useState('')
  const [description, setDescription] = useState('')
  const [shots, setShots] = useState<Shot[]>([])
  const [res, setRes] = useState<LeadIntakeResponse | null>(null)
  const [drafts, setDrafts] = useState<LeadIntakeDraft[]>([])
  const [picked, setPicked] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showIgnored, setShowIgnored] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const addFiles = useCallback(async (incoming: FileList | File[] | null) => {
    const list = Array.from(incoming || [])
    if (list.length === 0) return
    const images = list.filter(isAcceptedImage)
    if (images.length < list.length) {
      toast.error(`${list.length - images.length} Datei(en) übersprungen — nur PNG, JPEG, WebP, GIF.`)
    }
    setShots((prev) => {
      if (prev.length >= MAX_IMAGES) {
        toast.error(`Maximal ${MAX_IMAGES} Screenshots.`)
        return prev
      }
      return prev
    })
    const room = MAX_IMAGES - shots.length
    if (room <= 0) return
    const added: Shot[] = []
    for (const file of images.slice(0, room)) {
      const dataUrl = await downscaleToDataUrl(file)
      if (!dataUrl) { toast.error(`„${file.name}" konnte nicht gelesen werden.`); continue }
      added.push({
        id: `${file.name}-${file.lastModified}-${Math.round(dataUrl.length / 7)}`,
        dataUrl, name: file.name || 'Screenshot',
        kb: Math.round((dataUrl.length * 3) / 4 / 1024),
      })
    }
    if (added.length) setShots((prev) => [...prev, ...added].slice(0, MAX_IMAGES))
  }, [shots.length])

  // Einfügen per Strg/⌘+V — der schnellste Weg von der Zwischenablage hierher.
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const files = Array.from(e.clipboardData?.files || []).filter(isAcceptedImage)
      if (files.length) { e.preventDefault(); addFiles(files) }
    }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  }, [addFiles])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !loading && !saving) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [loading, saving, onClose])

  const run = async () => {
    if (loading) return
    if (!text.trim() && shots.length === 0 && !website.trim() && !description.trim()) {
      setError('Bitte mindestens eine Quelle angeben: Text, Screenshot, Website oder Beschreibung.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const out = await leadIntakePreview({
        text, hint, website, description, images: shots.map((s) => s.dataUrl),
      })
      setRes(out)
      setDrafts(out.leads)
      // Duplikate NICHT vorauswählen — sie entstehen sonst versehentlich doppelt.
      setPicked(new Set(out.leads.map((l, i) => (l.duplicate ? -1 : i)).filter((i) => i >= 0)))
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || 'Die KI-Auswertung ist fehlgeschlagen.')
    }
    setLoading(false)
  }

  const patch = (i: number, change: Partial<LeadIntakeDraft>) =>
    setDrafts((prev) => prev.map((d, j) => (j === i ? { ...d, ...change } : d)))

  const patchActivity = (i: number, k: number, change: Partial<LeadIntakeDraft['activities'][0]>) =>
    setDrafts((prev) => prev.map((d, j) => (j === i
      ? { ...d, activities: d.activities.map((a, m) => (m === k ? { ...a, ...change } : a)) }
      : d)))

  const toggle = (i: number) => setPicked((prev) => {
    const next = new Set(prev)
    if (next.has(i)) next.delete(i); else next.add(i)
    return next
  })

  const chosen = useMemo(() => [...picked].sort((a, b) => a - b).map((i) => drafts[i])
    .filter(Boolean), [picked, drafts])

  const commit = async () => {
    if (saving || chosen.length === 0) return
    setSaving(true)
    try {
      // force nur, wenn bewusst ein Duplikat angehakt wurde.
      const force = chosen.some((d) => d.duplicate)
      const out = await leadIntakeCommit(chosen, force)
      const bits = [
        `${out.created} Lead${out.created === 1 ? '' : 's'}`,
        out.activities_created ? `${out.activities_created} Aktion(en)` : '',
        out.skipped_duplicates ? `${out.skipped_duplicates} Duplikat(e) übersprungen` : '',
      ].filter(Boolean)
      toast.success(`Angelegt: ${bits.join(' · ')}.`)
      onImported(out.created)
      onClose()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Anlegen fehlgeschlagen.')
      setSaving(false)
    }
  }

  const back = () => { setRes(null); setDrafts([]); setPicked(new Set()) }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={() => { if (!loading && !saving) onClose() }} />
      <div
        className={`relative bg-surface-high rounded-dialog shadow-elev-3 p-5 sm:p-7 max-w-[900px]
                    w-full mx-4 animate-modal-in max-h-[88vh] flex flex-col
                    ${dragOver ? 'ring-2 ring-accent' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files) }}
      >
        <div className="flex items-baseline justify-between gap-3 mb-1">
          <h3 className="text-lg font-semibold text-text">✨ Aus Chat/Screenshot</h3>
          {res && (
            <span className="text-xs text-text-muted" title="Kosten dieses Laufs">
              {eur(res.cost.cost_eur)}
            </span>
          )}
        </div>
        <p className="text-xs text-text-muted mb-4">
          {res
            ? <>Entwürfe prüfen und anpassen — <strong className="text-text">angelegt wird nur,
              was angehakt ist</strong>.</>
            : <>Eine Quelle genügt: Verlauf einfügen, Screenshots anhängen
              (<kbd className="px-1 rounded bg-surface-container">Strg/⌘+V</kbd>) — oder einfach
              eine Website angeben und beschreiben, worum es geht.</>}
        </p>

        {/* ---------- Schritt 1: Material ---------- */}
        {!res && (
          <div className="flex-1 min-h-0 overflow-y-auto space-y-3">
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
              <div>
                <label htmlFor="intake-website" className="block text-xs text-text-muted mb-1">
                  Website der Firma
                </label>
                <input
                  id="intake-website"
                  type="url"
                  inputMode="url"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  placeholder="muster-elektro.de"
                  className="w-full bg-surface-container border border-border rounded-lg px-3 py-2
                             text-sm text-text placeholder:text-text-muted"
                />
                <p className="text-[11px] text-text-muted mt-1">
                  Wird abgerufen — <strong className="text-text">Startseite und
                  Impressum/Kontakt</strong>. Dort stehen Firmenname, Adresse,
                  Geschäftsführung und Kontaktdaten.
                </p>
              </div>
              <div>
                <label htmlFor="intake-description" className="block text-xs text-text-muted mb-1">
                  Beschreibung
                </label>
                <textarea
                  id="intake-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  placeholder="z. B. Zahnarztpraxis in Kreuzberg, Website von 2014 — Kandidat für Relaunch"
                  className="w-full bg-surface-container border border-border rounded-lg px-3 py-2
                             text-sm text-text placeholder:text-text-muted resize-y"
                />
                <p className="text-[11px] text-text-muted mt-1">
                  Deine Einordnung: Branche, Anlass, Bedarf. Darf Fakten liefern, die auf der
                  Seite nicht stehen.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="h-px flex-1 bg-border" />
              <span className="text-[10px] uppercase tracking-wide text-text-muted">
                oder Gesprächsmaterial
              </span>
              <span className="h-px flex-1 bg-border" />
            </div>

            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={6}
              placeholder="Chatverlauf, E-Mail-Text, Impressum, Notiz …"
              className="w-full bg-surface-container border border-border rounded-lg px-3 py-2
                         text-sm text-text placeholder:text-text-muted resize-y"
            />

            <div className="border border-dashed border-border rounded-card p-4">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <button onClick={() => fileRef.current?.click()} className="btn-secondary text-xs"
                        disabled={shots.length >= MAX_IMAGES}>
                  Screenshots wählen
                </button>
                <span className="text-[11px] text-text-muted">
                  max. {MAX_IMAGES} · werden auf {MAX_EDGE_PX} px verkleinert
                </span>
              </div>
              <input ref={fileRef} type="file" multiple className="hidden"
                     accept="image/png,image/jpeg,image/webp,image/gif"
                     onChange={(e) => { addFiles(e.target.files); e.target.value = '' }} />
              {shots.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {shots.map((s, i) => (
                    <div key={s.id} className="relative group">
                      <img src={s.dataUrl} alt={s.name}
                           className="w-24 h-24 object-cover rounded-md border border-border" />
                      <span className="absolute bottom-0 left-0 right-0 text-[9px] text-center
                                       bg-black/60 text-white rounded-b-md tabular-nums">
                        {s.kb} KB
                      </span>
                      <button onClick={() => setShots((p) => p.filter((_, j) => j !== i))}
                              title="entfernen"
                              className="absolute -top-1.5 -right-1.5 w-5 h-5 grid place-items-center
                                         rounded-full bg-surface-high border border-border
                                         text-text-muted hover:text-danger text-xs">×</button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label htmlFor="intake-hint" className="block text-xs text-text-muted mb-1">
                Dein Hinweis (optional)
              </label>
              <input
                id="intake-hint"
                value={hint}
                onChange={(e) => setHint(e.target.value)}
                placeholder="z. B. „kenne ich von der Messe, Budget 20k, nur die Berliner Firma"
                className="w-full bg-surface-container border border-border rounded-lg px-3 py-2
                           text-sm text-text placeholder:text-text-muted"
              />
              <p className="text-[11px] text-text-muted mt-1">
                Dein Hinweis hat <strong className="text-text">Vorrang vor dem Material</strong>:
                er darf fehlende Fakten ergänzen, Targets vorgeben und die Auswahl einschränken.
                Widersprüche werden in den Notizen vermerkt.
              </p>
            </div>

            <p className="text-[11px] text-text-muted">
              Material, Bilder und abgerufener Seitentext gehen zur Auswertung an Anthropic und
              können Daten Dritter enthalten. <strong className="text-text">Gespeichert wird das Rohmaterial
              nicht</strong> — nur die Entwürfe, die du bestätigst.
            </p>
            {error && <p className="text-sm text-danger">{error}</p>}
          </div>
        )}

        {/* ---------- Schritt 2: Entwürfe ---------- */}
        {res && (
          <div className="flex-1 min-h-0 overflow-y-auto space-y-3">
            {drafts.length === 0 && (
              <p className="text-sm text-text-muted py-6 text-center">
                Aus dem Material ließ sich kein Lead ableiten.
              </p>
            )}

            {drafts.map((d, i) => (
              <div key={i}
                   className={`rounded-card border p-3 ${picked.has(i)
                     ? 'border-accent bg-accent/5' : 'border-border bg-surface-container'}`}>
                <div className="flex items-start gap-2.5">
                  <input type="checkbox" checked={picked.has(i)} onChange={() => toggle(i)}
                         className="mt-1.5 shrink-0" />
                  <div className="min-w-0 flex-1 space-y-1.5">
                    <input
                      value={d.company}
                      onChange={(e) => patch(i, { company: e.target.value })}
                      aria-label="Firmenname"
                      className="w-full bg-surface border border-border rounded-md px-2 py-1
                                 text-sm font-medium text-text"
                    />

                    <div className="text-xs text-text-muted break-words">
                      {[d.contact_name, d.role, d.email, d.phone].filter(Boolean).join(' · ') || '—'}
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                      <span className="px-1.5 py-0.5 rounded-full bg-surface text-text-muted">
                        {STATUS_LABELS[d.status as keyof typeof STATUS_LABELS] || d.status}
                      </span>
                      {d.target && (
                        <span className="px-1.5 py-0.5 rounded-full bg-surface text-accent">
                          🎯 {d.target}
                        </span>
                      )}
                      {d.value_estimate != null && d.value_estimate !== '' && (
                        <span className="px-1.5 py-0.5 rounded-full bg-surface text-text"
                              title="Genannter Betrag (Budget/Angebotssumme)">
                          {/* Decimal kommt als String — erst durch Number(). */}
                          💰 {Number(d.value_estimate).toLocaleString('de-DE')} €
                        </span>
                      )}
                      {d.confidence != null && (
                        <span className="px-1.5 py-0.5 rounded-full bg-surface text-text-muted"
                              title="Sicherheit der KI">
                          {Math.round(d.confidence * 100)} %
                        </span>
                      )}
                      {d.duplicate && (
                        <span className="px-1.5 py-0.5 rounded-full bg-warning/15 text-warning"
                              title={`Bereits vorhanden: ${d.existing_company || ''} (${d.duplicate_reason || ''})`}>
                          Duplikat: {d.existing_company}
                        </span>
                      )}
                    </div>

                    {d.unclear.length > 0 && (
                      <p className="text-[11px] text-warning">
                        Bitte prüfen: {d.unclear.join(', ')}
                      </p>
                    )}

                    <textarea
                      value={d.notes || ''}
                      onChange={(e) => patch(i, { notes: e.target.value })}
                      rows={Math.min(6, Math.max(2, (d.notes || '').split('\n').length))}
                      aria-label="Notizen"
                      placeholder="Notizen"
                      className="w-full bg-surface border border-border rounded-md px-2 py-1
                                 text-xs text-text resize-y"
                    />

                    {d.activities.length > 0 && (
                      <div className="space-y-1">
                        {d.activities.map((a, k) => (
                          <div key={k} className="flex flex-wrap items-center gap-1.5">
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface
                                             text-text-muted shrink-0">
                              {ACTIVITY_TYPE_LABELS[a.type as keyof typeof ACTIVITY_TYPE_LABELS] || a.type}
                            </span>
                            <input
                              value={a.notes || ''}
                              onChange={(e) => patchActivity(i, k, { notes: e.target.value })}
                              aria-label="Aktion"
                              className="flex-1 min-w-[150px] bg-surface border border-border
                                         rounded-md px-2 py-1 text-xs text-text"
                            />
                            <input
                              type="date"
                              value={a.due_date || ''}
                              onChange={(e) => patchActivity(i, k, { due_date: e.target.value || null })}
                              aria-label="Fällig am"
                              className="bg-surface border border-border rounded-md px-2 py-1
                                         text-xs text-text shrink-0"
                            />
                          </div>
                        ))}
                      </div>
                    )}

                    {d.evidence && (
                      <p className="text-[11px] text-text-muted italic break-words">
                        Beleg: „{d.evidence}"
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {res.ignored.length > 0 && (
              <div className="rounded-md border border-border">
                <button onClick={() => setShowIgnored((v) => !v)}
                        className="w-full text-left px-3 py-2 text-xs text-text-muted md-state">
                  {showIgnored ? '▾' : '▸'} Nicht übernommen ({res.ignored.length})
                </button>
                {showIgnored && (
                  <ul className="px-3 pb-2 space-y-0.5">
                    {res.ignored.map((line, i) => (
                      <li key={i} className="text-[11px] text-text-muted">• {line}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-2 mt-4">
          {res && drafts.length > 0 && (
            <span className="text-xs text-text-muted">
              {picked.size} von {drafts.length} gewählt
            </span>
          )}
          <div className="ml-auto flex gap-2">
            {res ? (
              <>
                <button onClick={back} className="btn-secondary" disabled={saving}>Zurück</button>
                <button onClick={commit} className="btn-primary"
                        disabled={picked.size === 0 || saving}>
                  {saving ? 'Lege an…' : `${picked.size} übernehmen`}
                </button>
              </>
            ) : (
              <>
                <button onClick={onClose} className="btn-secondary" disabled={loading}>
                  Abbrechen
                </button>
                <button onClick={run} className="btn-primary" disabled={loading}>
                  {loading ? 'KI wertet aus…' : 'Auswerten'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
