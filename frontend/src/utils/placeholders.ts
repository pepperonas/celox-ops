/**
 * Platzhalter-System für Outreach-Templates. Syntax: {{key}} (z. B. {{firma}}).
 * Rein & testbar — keine DOM-/React-Abhängigkeit.
 */
export const PLACEHOLDER_RE = /\{\{\s*([a-z0-9_]+)\s*\}\}/gi

/** Alle im Text vorkommenden Platzhalter-Keys (einmalig, klein geschrieben). */
export function extractPlaceholders(text: string): string[] {
  const set = new Set<string>()
  for (const m of text.matchAll(PLACEHOLDER_RE)) set.add(m[1].toLowerCase())
  return [...set]
}

export interface FillResult {
  text: string
  /** Platzhalter, die (noch) leer sind — bleiben als {{key}} sichtbar. */
  missing: string[]
}

/**
 * Ersetzt {{key}} durch values[key]. Leere/fehlende Werte bleiben als {{key}}
 * stehen und landen in `missing` (für die Warnung „N Platzhalter noch offen").
 */
export function fillPlaceholders(text: string, values: Record<string, string>): FillResult {
  const missing = new Set<string>()
  const out = text.replace(PLACEHOLDER_RE, (_full, keyRaw) => {
    const key = String(keyRaw).toLowerCase()
    const v = (values[key] ?? '').trim()
    if (!v) {
      missing.add(key)
      return `{{${key}}}`
    }
    return v
  })
  return { text: out, missing: [...missing] }
}
