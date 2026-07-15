/**
 * Tageszeitabhängige Anrede + Namens-Fallback für Outreach-Platzhalter.
 * Rein & testbar (Date injizierbar).
 */
export function timeGreeting(date: Date = new Date()): string {
  const h = date.getHours()
  if (h >= 5 && h < 11) return 'Guten Morgen'
  if (h >= 11 && h < 18) return 'Guten Tag'
  return 'Guten Abend' // abends & nachts (18–4 Uhr) — „Gute Nacht" ist ein Abschied
}

// Sinnvoller {{name}}-Fallback, wenn kein Ansprechpartner bekannt ist
// („alles besser als leer" → z. B. „Guten Tag zusammen,").
export const FALLBACK_NAME = 'zusammen'
