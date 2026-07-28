import { memo, useCallback, useEffect, useRef, useState } from 'react'
import type { RainmakerLead, RainmakerLeadStatus } from '../../types'
import type { LeadSort } from './leadSort'
import LeadCard from './LeadCard'
import { countLabel, visibleCount } from './pipelineColumns'
import { containmentClass, needsContainment } from '../../utils/scrollContainment'

/**
 * „Mehr laden"-Sentinel am Spaltenende. Der IntersectionObserver beobachtet
 * **innerhalb des Spalten-Scroll-Containers** (`root`), nicht im Viewport — sonst
 * lädt langes Seiten-Scrollen ungewollt alle Spalten voll. Bleibt zusätzlich ein
 * klickbarer Button (Tastatur / falls der Observer nicht feuert).
 */
function LoadMore({ remaining, onMore, rootRef }: {
  remaining: number
  onMore: () => void
  rootRef: React.RefObject<HTMLDivElement | null>
}) {
  const ref = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el || remaining <= 0) return
    const io = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) onMore() },
      { root: rootRef.current ?? null, rootMargin: '200px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [onMore, remaining, rootRef])
  return (
    <button ref={ref} onClick={onMore}
            className="w-full text-xs text-accent hover:underline underline-offset-2 py-2">
      +{remaining} weitere laden
    </button>
  )
}

interface Props {
  statusKey: RainmakerLeadStatus
  label: string
  color: string
  /** Vollständige, sortierte Spaltenliste (Slice passiert hier). */
  leads: RainmakerLead[]
  visible: number
  isOver: boolean
  draggingId: string | null
  sortMode: LeadSort
  onMore: (statusKey: RainmakerLeadStatus, total: number) => void
  onShowAll: (statusKey: RainmakerLeadStatus, total: number) => void
  onDragOverColumn: (statusKey: RainmakerLeadStatus, e: React.DragEvent) => void
  onDragLeaveColumn: () => void
  onDropColumn: (e: React.DragEvent, statusKey: RainmakerLeadStatus) => void
  onOpenLead: (lead: RainmakerLead) => void
  onTogglePin: (lead: RainmakerLead) => void
  onCardDragStart: (lead: RainmakerLead, e: React.DragEvent) => void
  onCardDragEnd: () => void
}

/**
 * Eine Pipeline-Spalte mit **eigenem Scroll-Container**: die Höhe ist auf ~70 vh
 * gedeckelt (ab `sm` fix, damit das Raster gleich hoch ist; mobil wächst sie bis
 * zum Deckel mit dem Inhalt). Dadurch bleibt die Seite kurz und ALLE Phasen sind
 * erreichbar — vorher bestimmte die höchste Spalte die Grid-Zeilenhöhe und schob
 * die übrigen Phasen tausende Pixel nach unten.
 *
 * Nachgeladen wird nur beim Scrollen *in dieser Spalte* (Sentinel-Root = Container).
 * Memoisiert; alle Callbacks sind stabil und bekommen `statusKey`/`lead` als Argument.
 */
function PipelineColumnBase({
  statusKey, label, color, leads, visible, isOver, draggingId, sortMode,
  onMore, onShowAll, onDragOverColumn, onDragLeaveColumn, onDropColumn,
  onOpenLead, onTogglePin, onCardDragStart, onCardDragEnd,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const shown = visibleCount(visible, leads.length)
  const hidden = leads.length - shown
  const label2 = countLabel(shown, leads.length)

  // Scroll-Verkettung nur kappen, wenn die Spalte wirklich scrollen kann —
  // sonst schluckt eine leere/kurze Spalte das Mausrad und die Seite steht
  // (siehe utils/scrollContainment).
  const [scrollable, setScrollable] = useState(false)
  const measure = useCallback(() => {
    const el = scrollRef.current
    if (el) setScrollable(needsContainment(el.scrollHeight, el.clientHeight))
  }, [])

  // Inhalt geändert (Filter, Nachladen, Drag&Drop) …
  useEffect(measure, [measure, leads, shown])
  // … und Boxgröße geändert (Viewport/70vh, Zoom, Sortierleiste).
  useEffect(() => {
    const el = scrollRef.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [measure])

  return (
    <div
      className="min-w-0 flex flex-col"
      onDragOver={(e) => onDragOverColumn(statusKey, e)}
      onDragLeave={onDragLeaveColumn}
      onDrop={(e) => onDropColumn(e, statusKey)}
    >
      <div className="rounded-t-lg px-4 py-2.5 flex items-center justify-between gap-2"
           style={{ backgroundColor: color + '20', borderTop: `3px solid ${color}` }}>
        <span className="text-sm font-semibold truncate" style={{ color }}>{label}</span>
        <div className="flex items-center gap-1.5 shrink-0">
          {label2 && (
            <span className="text-[10px] text-text-muted tabular-nums" title={`${shown} von ${leads.length} geladen`}>
              {label2}
            </span>
          )}
          <span className="text-xs font-medium px-2 py-0.5 rounded-full tabular-nums"
                style={{ backgroundColor: color + '25', color }}>
            {leads.length}
          </span>
        </div>
      </div>

      {/* Eigener Scroll-Container: hält die Seite kurz und begrenzt das DOM. */}
      <div
        ref={scrollRef}
        className={`max-h-[70vh] sm:h-[70vh] sm:max-h-[820px] overflow-y-auto ${containmentClass(scrollable)} bg-surface-container border border-border rounded-b-lg p-3 space-y-3 transition-all duration-short ${
          isOver ? 'border-accent border-dashed bg-accent/5' : ''
        }`}
      >
        {leads.length === 0 ? (
          <div className="text-center text-text-muted text-xs py-8">Keine Leads</div>
        ) : (
          leads.slice(0, shown).map((lead) => (
            <LeadCard
              key={lead.id}
              lead={lead}
              color={color}
              sortMode={sortMode}
              dragging={draggingId === lead.id}
              onOpen={onOpenLead}
              onTogglePin={onTogglePin}
              onDragStart={onCardDragStart}
              onDragEnd={onCardDragEnd}
            />
          ))
        )}
        {hidden > 0 && (
          <>
            <LoadMore remaining={hidden} onMore={() => onMore(statusKey, leads.length)} rootRef={scrollRef} />
            <button onClick={() => onShowAll(statusKey, leads.length)}
                    title="Alle Karten dieser Spalte rendern (z. B. für die Browser-Suche)"
                    className="w-full text-[11px] text-text-muted hover:text-text py-1">
              alle {leads.length} laden
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default memo(PipelineColumnBase)
