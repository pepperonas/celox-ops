// Wann darf ein Klick auf einen In-App-Link NICHT abgefangen werden?
//
// Ein Link, der immer `preventDefault()` ruft, nimmt dem Nutzer „In neuem Tab
// öffnen" (Cmd/Ctrl+Klick, Mittelklick) und „In neuem Fenster" (Shift) weg —
// genau die Gesten, mit denen man aus einer Liste heraus arbeitet. Die Prüfung
// ist leicht unvollständig zu schreiben (Mittelklick wird gern vergessen),
// deshalb steht sie hier einmal und ist getestet.

/** Nur die Felder, die wir brauchen — so ist die Funktion ohne DOM testbar. */
export interface ClickLike {
  metaKey?: boolean
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  button?: number
}

/**
 * True, wenn der Browser den Klick selbst behandeln soll (neuer Tab/Fenster,
 * Download). Dann kein `preventDefault`, keine SPA-Navigation.
 */
export function isModifiedClick(e: ClickLike): boolean {
  return Boolean(
    e.metaKey || e.ctrlKey || e.shiftKey || e.altKey ||
    (e.button !== undefined && e.button !== 0),
  )
}
