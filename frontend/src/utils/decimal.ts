/** Parst eine Dezimaleingabe mit Komma ODER Punkt als Trenner (z.B. "0,45" oder "0.45").
 *  Whitespace wird ignoriert; ungültige/leere Eingaben ergeben 0. */
export function parseDecimalInput(raw: string): number {
  const cleaned = raw.replace(/\s/g, '').replace(/,/g, '.')
  const n = parseFloat(cleaned)
  return Number.isFinite(n) ? n : 0
}
