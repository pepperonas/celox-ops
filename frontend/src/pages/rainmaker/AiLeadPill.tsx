import { createPortal } from 'react-dom'
import type { AiLeadRun } from './aiLeadRun'

/**
 * Minimiertes Overlay der KI-Lead-Suche: erscheint, wenn der Dialog geschlossen
 * ist, während eine Suche läuft ODER ein Ergebnis auf Ansicht wartet (z. B. weil
 * die Suche fertig wurde, während man auf einer anderen Seite war). Klick öffnet
 * den Dialog (und navigiert nötigenfalls zur Pipeline). Ergebnisse gehen hier NIE
 * verloren — Verwerfen nur über das explizite ✕ (nur im Fertig-Zustand).
 */
export default function AiLeadPill({
  run,
  count,
  onOpen,
  onDiscard,
}: {
  run: AiLeadRun
  count?: number // Anzahl Treffer, wenn fertig
  onOpen: () => void
  onDiscard?: () => void
}) {
  const done = !run.running
  return createPortal(
    <div className="fixed bottom-5 right-5 z-40 flex items-center bg-surface-high border border-border rounded-full shadow-elev-3 animate-md-fade">
      <button
        onClick={onOpen}
        title={done ? 'KI-Recherche fertig — klicken zum Ansehen & Importieren' : 'KI-Recherche läuft im Hintergrund — klicken zum Öffnen'}
        className="flex items-center gap-3 pl-4 pr-4 py-3 rounded-l-full hover:bg-surface-container transition-colors duration-short"
      >
        {done
          ? <span className="text-success text-lg leading-none shrink-0">✓</span>
          : <span className="inline-block w-4 h-4 rounded-full border-2 border-accent border-t-transparent animate-spin shrink-0" />}
        <span className="flex flex-col items-start leading-tight">
          <span className="text-sm text-text font-medium">
            {done ? '✨ KI-Recherche fertig' : '✨ KI-Recherche läuft…'}
          </span>
          <span className="text-[11px] text-text-muted">
            {done ? `${count ?? 0} Treffer` : run.phaseLabels[run.phase]}
          </span>
        </span>
        {!done && <span className="text-xs text-text-muted tabular-nums">{run.elapsed}s</span>}
        <span className="text-xs text-accent font-medium">{done ? 'ansehen' : 'öffnen'}</span>
      </button>
      {done && onDiscard && (
        <button
          onClick={onDiscard}
          title="Ergebnisse verwerfen"
          aria-label="Ergebnisse verwerfen"
          className="pr-4 pl-2 py-3 text-text-muted hover:text-danger transition-colors duration-short rounded-r-full"
        >
          ✕
        </button>
      )}
    </div>,
    document.body,
  )
}
