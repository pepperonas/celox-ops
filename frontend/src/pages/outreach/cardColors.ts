// Karten-Farben wie in Google Keep: frei wählbar, ohne feste Bedeutung.
//
// **Keine Pastelltöne.** Keeps helle Gelb-/Rosatöne würden im dunklen Theme wie
// Fremdkörper wirken. Stattdessen tonale Tints aus den vorhandenen Theme-Tokens:
// gleiche Sättigung, gleiche Deckkraft, nur ein anderer Farbton. Damit bleibt die
// Karte eine Karte und ist trotzdem auf einen Blick unterscheidbar.
//
// **Warum sieben und nicht zwölf:** Die Farbe muss aus einem Token kommen (Regel
// in `.claude/rules/frontend-m3e.md`: nie Hex in Komponenten). Das Theme hat
// sechs Farbtöne plus neutral — mehr wären erfundene Werte, die bei einem
// Theme-Wechsel nicht mitgehen. Sieben unterscheidbare Farben reichen zum
// Gruppieren; ab etwa zehn kann sich ohnehin niemand die Bedeutung merken.
//
// Die Klassen stehen als vollständige Zeichenketten da, weil Tailwind den Code
// statisch durchsucht — `bg-${farbe}/10` würde nie erzeugt.
//
// Deckkraft 10 % Fläche + 50 % Rahmen: Bei 5 % waren die Farben auf dem dunklen
// Grund im Browser praktisch nicht zu unterscheiden — eine Farbe, die man nicht
// sieht, ist keine.

export interface CardColor {
  key: string
  label: string
  /** Rahmen + Flächen-Tint der Karte. */
  card: string
  /** Punkt in der Farbauswahl. */
  dot: string
}

export const CARD_COLORS: CardColor[] = [
  { key: 'neutral', label: 'Ohne Farbe', card: 'border-border bg-surface-high', dot: 'bg-surface-2 border border-border' },
  { key: 'blau', label: 'Blau', card: 'border-accent/50 bg-accent/10', dot: 'bg-accent' },
  { key: 'gruen', label: 'Grün', card: 'border-success/50 bg-success/10', dot: 'bg-success' },
  { key: 'gelb', label: 'Gelb', card: 'border-warning/50 bg-warning/10', dot: 'bg-warning' },
  { key: 'rot', label: 'Rot', card: 'border-danger/50 bg-danger/10', dot: 'bg-danger' },
  { key: 'violett', label: 'Violett', card: 'border-purple/50 bg-purple/10', dot: 'bg-purple' },
  { key: 'cyan', label: 'Cyan', card: 'border-cyan/50 bg-cyan/10', dot: 'bg-cyan' },
]

const BY_KEY = new Map(CARD_COLORS.map((c) => [c.key, c]))

/**
 * Farbe zu einem gespeicherten Schlüssel. Unbekanntes und `null` ergeben neutral —
 * eine entfernte Farbe darf keine Karte unsichtbar oder ungestylt zurücklassen.
 */
export function cardColor(key: string | null | undefined): CardColor {
  return BY_KEY.get((key || '').trim()) ?? CARD_COLORS[0]
}

/** Der Wert, der gespeichert wird: neutral wird als „keine Farbe" abgelegt. */
export function colorToStore(key: string): string | null {
  return key === 'neutral' ? null : key
}
