/**
 * Client-Seite des Taxonomie-Systems: Fold-Matching, Kanonisierung (Synonyme
 * kommen vom Server mit), Tag-Splitting, Vorschlags-Ranking. Rein & testbar.
 */
import { fuzzyScore } from './fuzzy'

/** Vergleichs-Schlüssel: trim, lowercase, Diakritika weg (Spiegel von backend fold()). */
export function foldKey(s: string): string {
  return (s || '').trim().toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
}

/**
 * Kanonische Schreibweise: Synonym-Treffer → kanonisch; Case-/Diakritika-Variante
 * eines bekannten Werts → dessen Schreibweise; sonst Original (getrimmt) — creatable.
 */
export function canonicalize(value: string, values: string[], synonyms: Record<string, string>): string {
  const v = (value || '').trim()
  if (!v) return v
  const key = foldKey(v)
  for (const [syn, canon] of Object.entries(synonyms)) {
    if (foldKey(syn) === key) return canon
  }
  for (const known of values) {
    if (foldKey(known) === key) return known
  }
  return v
}

/** Kanonisiert eine Liste und entfernt fold-Dubletten (Reihenfolge bleibt). */
export function dedupeCanonical(items: string[], values: string[], synonyms: Record<string, string>): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const raw of items) {
    const canon = canonicalize(raw, values, synonyms)
    if (!canon) continue
    const key = foldKey(canon)
    if (!seen.has(key)) {
      seen.add(key)
      out.push(canon)
    }
  }
  return out
}

/** 'a, b,, c' / Zeilenumbrüche / Semikolons → ['a','b','c'] (für Tag-Paste). */
export function splitTags(raw: string): string[] {
  return raw.split(/[,;\n]/).map((t) => t.trim()).filter(Boolean)
}

/** Vorschläge zur Eingabe ranken (fuzzy); leere Eingabe → Pool-Reihenfolge. */
export function rankSuggestions(pool: string[], query: string, limit = 8): string[] {
  const q = query.trim()
  if (!q) return pool.slice(0, limit)
  return pool
    .map((s) => ({ s, score: fuzzyScore(q, s) }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((x) => x.s)
}
