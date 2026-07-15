/**
 * Leichtgewichtiges Fuzzy-Matching für Autocomplete-Listen (z. B. Lead-Suche).
 * Höherer Score = besserer Treffer; 0 = kein Treffer. Rein & testbar.
 */
function norm(s: string): string {
  return s.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '').trim()
}

export function fuzzyScore(query: string, text: string): number {
  const q = norm(query)
  const t = norm(text)
  if (!q) return 1 // leere Query matcht alles (schwach)
  if (!t) return 0

  // 1) Substring (bestes Signal), Bonus für Wortanfang
  const idx = t.indexOf(q)
  if (idx !== -1) return 100 - idx * 0.3 + (idx === 0 ? 20 : 0)

  // 2) alle Query-Tokens als Substrings enthalten (Mehrwort-Suche)
  const tokens = q.split(/\s+/).filter(Boolean)
  if (tokens.length > 1 && tokens.every((tok) => t.includes(tok))) return 70

  // 3) Subsequenz (Buchstaben in Reihenfolge)
  const qc = q.replace(/\s+/g, '')
  let ti = 0
  for (const ch of qc) {
    const at = t.indexOf(ch, ti)
    if (at === -1) return 0
    ti = at + 1
  }
  return 30 - (ti - qc.length) * 0.2
}

/** Rankt Elemente nach dem besten Fuzzy-Score über mehrere Textfelder. */
export function fuzzyRank<T>(
  items: T[],
  query: string,
  keys: (item: T) => string[],
  limit = 8,
): T[] {
  if (!query.trim()) return items.slice(0, limit)
  return items
    .map((item) => ({ item, score: Math.max(0, ...keys(item).map((k) => fuzzyScore(query, k))) }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((x) => x.item)
}
