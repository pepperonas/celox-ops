import { api } from './client'

export interface SuggestionSet {
  field: string
  values: string[]
  synonyms: Record<string, string>
  /** Nur bei expense_description: Beschreibung → Kategorie. */
  categories?: Record<string, string>
}

// Ein Fetch pro Feld und Session (Listen sind klein; Filterung passiert lokal).
// Fehler leeren den Cache-Slot, damit der nächste Versuch neu lädt.
const cache = new Map<string, Promise<SuggestionSet>>()

export function getSuggestions(field: string): Promise<SuggestionSet> {
  let p = cache.get(field)
  if (!p) {
    const limit = field === 'expense_description' ? 500 : 200
    p = api.get('/suggestions', { params: { field, limit } }).then((r) => r.data)
    p.catch(() => cache.delete(field))
    cache.set(field, p)
  }
  return p
}

// Nach Verwaltungsänderungen (umbenennen/löschen/anlegen) den Cache verwerfen,
// damit Autocomplete sofort die neuen Werte lädt. `tag` und `branche` teilen sich
// die Bestandswerte → beide leeren, wenn eins betroffen ist.
export function invalidateSuggestions(field?: string): void {
  if (!field) { cache.clear(); return }
  cache.delete(field)
  if (field === 'tag' || field === 'branche') { cache.delete('tag'); cache.delete('branche') }
}
