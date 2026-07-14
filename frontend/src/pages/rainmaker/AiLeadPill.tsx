import { createPortal } from 'react-dom'
import type { AiLeadRun } from './useAiLeadRun'

/**
 * Minimiertes Overlay: erscheint, wenn der KI-Lead-Dialog während einer laufenden
 * Suche geschlossen (minimiert) wurde. Zeigt Fortschritt; Klick öffnet den Dialog.
 */
export default function AiLeadPill({ run, onOpen }: { run: AiLeadRun; onOpen: () => void }) {
  return createPortal(
    <button
      onClick={onOpen}
      title="KI-Recherche läuft im Hintergrund — klicken zum Öffnen"
      className="fixed bottom-5 right-5 z-40 flex items-center gap-3 bg-surface-high border border-border rounded-full shadow-elev-3 pl-4 pr-5 py-3 hover:bg-surface-container transition-colors duration-short animate-md-fade"
    >
      <span className="inline-block w-4 h-4 rounded-full border-2 border-accent border-t-transparent animate-spin shrink-0" />
      <span className="flex flex-col items-start leading-tight">
        <span className="text-sm text-text font-medium">✨ KI-Recherche läuft…</span>
        <span className="text-[11px] text-text-muted">{run.phaseLabels[run.phase]}</span>
      </span>
      <span className="text-xs text-text-muted tabular-nums">{run.elapsed}s</span>
      <span className="text-xs text-accent font-medium">öffnen</span>
    </button>,
    document.body,
  )
}
