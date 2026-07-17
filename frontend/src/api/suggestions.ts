import { api } from './client'

export interface SuggestionSet {
  field: string
  values: string[]
  synonyms: Record<string, string>
}

// Ein Fetch pro Feld und Session (Listen sind klein; Filterung passiert lokal).
// Fehler leeren den Cache-Slot, damit der nächste Versuch neu lädt.
const cache = new Map<string, Promise<SuggestionSet>>()

export function getSuggestions(field: string): Promise<SuggestionSet> {
  let p = cache.get(field)
  if (!p) {
    p = api.get('/suggestions', { params: { field, limit: 200 } }).then((r) => r.data)
    p.catch(() => cache.delete(field))
    cache.set(field, p)
  }
  return p
}
