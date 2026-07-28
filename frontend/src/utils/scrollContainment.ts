// Wann darf ein eigener Scroll-Container die Scroll-Verkettung zur Seite kappen?
//
// **Der Fehler:** `overscroll-behavior: contain` blockt das Weiterscrollen zur
// Seite auch dann, wenn der Container überhaupt nicht scrollen kann (leere oder
// kurze Pipeline-Spalte). Das Mausrad über so einer Spalte tat dann gar nichts —
// gemessen: Wheel über eine leere 70-vh-Spalte bewegte die Seite um 0 px, ohne
// `contain` um 300 px. Eine kleinere Höhe hilft nicht, sie verkleinert nur die
// tote Zone.
//
// **Die Regel:** Containment nur, solange es etwas zu halten gibt. Kann die
// Spalte scrollen, bleibt man beim Scrollen in ihr (kein Sprung der Seite am
// Spaltenende). Kann sie es nicht, scrollt die Seite weiter.

/** Toleranz gegen Sub-Pixel-Rundung: 1 px „Überlauf" ist keiner. */
export const OVERFLOW_TOLERANCE_PX = 2

/**
 * Soll `overscroll-behavior: contain` aktiv sein?
 * `true` nur, wenn der Inhalt den Container wirklich überläuft.
 */
export function needsContainment(scrollHeight: number, clientHeight: number): boolean {
  return scrollHeight - clientHeight > OVERFLOW_TOLERANCE_PX
}

/** Tailwind-Klasse passend zum Zustand (eine Stelle, damit es nicht driftet). */
export function containmentClass(scrollable: boolean): string {
  return scrollable ? 'overscroll-contain' : 'overscroll-auto'
}
