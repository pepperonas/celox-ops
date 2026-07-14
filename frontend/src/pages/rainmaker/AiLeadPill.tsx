import { createPortal } from 'react-dom'
import type { AiLeadRun } from './aiLeadRun'

/**
 * Minimiertes Overlay der KI-Lead-Suche: erscheint, wenn der Dialog geschlossen
 * ist, während eine Suche läuft ODER ein Ergebnis auf Ansicht wartet (z. B. weil
 * die Suche fertig wurde, während man auf einer anderen Seite war). Klick öffnet
 * den Dialog (und navigiert nötigenfalls zur Pipeline).
 */
export default function AiLeadPill({
  run,
  count,
  onOpen,
}: {
  run: AiLeadRun
  count?: number // Anzahl Treffer, wenn fertig
  onOpen: () => void
}) {
  const done = !run.running
  return createPortal(
    <button
      onClick={onOpen}
      title={done ? 'KI-Recherche fertig — klicken zum Ansehen' : 'KI-Recherche läuft im Hintergrund — klicken zum Öffnen'}
      className="fixed bottom-5 right-5 z-40 flex items-center gap-3 bg-surface-high border border-border rounded-full shadow-elev-3 pl-4 pr-5 py-3 hover:bg-surface-container transition-colors duration-short animate-md-fade"
    >
      {done
        ? <span className="text-success text-lg leading-none shrink-0">✓</span>
        : <span className="inline-block w-4 h-4 rounded-full border-2 border-accent border-t-transparent animate-spin shrink-0" />}
      <span className="flex flex-col items-start leading-tight">
        <span className="text-sm text-text font-medium">
          {done ? '✨ KI-Recherche fertig' : '✨ KI-Recherche läuft…'}
        </span>
        <span className="text-[11px] text-text-muted">
          {done ? `${count ?? 0} Treffer${count ? '' : ''}` : run.phaseLabels[run.phase]}
        </span>
      </span>
      {!done && <span className="text-xs text-text-muted tabular-nums">{run.elapsed}s</span>}
      <span className="text-xs text-accent font-medium">{done ? 'ansehen' : 'öffnen'}</span>
    </button>,
    document.body,
  )
}
