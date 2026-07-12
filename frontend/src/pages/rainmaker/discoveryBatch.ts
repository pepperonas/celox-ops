import type { DiscoveredCandidate } from '../../types'

// Kandidat mit Batch-Herkunft (Branche + Kombi-Label), clientseitig angereichert.
export interface BatchCandidate extends DiscoveredCandidate {
  _key: string        // stabiler Dedup-/Auswahl-Schlüssel
  _segment: string    // Branchen-Key (für den Import-Tag)
  _combo: string      // "Steuerkanzlei · Berlin" (für die Anzeige)
}

/** Freitext (Komma/Zeilenumbruch/Semikolon) → Liste eindeutiger Orte. */
export function parseLocations(input: string): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const raw of (input || '').split(/[,;\n]/)) {
    const loc = raw.trim()
    const key = loc.toLowerCase()
    if (loc && !seen.has(key)) {
      seen.add(key)
      out.push(loc)
    }
  }
  return out
}

/** Dedup-Schlüssel: normalisierte Website-Domain, sonst Firmenname. */
export function candidateKey(c: DiscoveredCandidate): string {
  const w = (c.website || '').trim().toLowerCase()
  if (w) {
    const dom = w.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0].replace(/\.+$/, '')
    if (dom) return 'w:' + dom
  }
  return 'n:' + (c.name || '').trim().toLowerCase()
}

export function hasContact(c: DiscoveredCandidate): boolean {
  return Boolean((c.website || '').trim() || (c.phone || '').trim())
}

/**
 * Führt neue Treffer in den Bestand ein — Cross-Kombi-Dedup über candidateKey.
 * Erster Fund gewinnt; ein späterer Duplikat-Treffer (bereits als Lead) hebt
 * das duplicate-Flag aber auf true (konservativ). Rückgabe: neuer Bestand.
 */
export function mergeCandidates(
  existing: BatchCandidate[],
  incoming: DiscoveredCandidate[],
  segment: string,
  combo: string,
): BatchCandidate[] {
  const byKey = new Map(existing.map((c) => [c._key, c]))
  for (const c of incoming) {
    const key = candidateKey(c)
    const prev = byKey.get(key)
    if (prev) {
      if (c.duplicate) prev.duplicate = true
      continue
    }
    byKey.set(key, { ...c, _key: key, _segment: segment, _combo: combo })
  }
  return [...byKey.values()]
}

/** Kontaktfähige (Website/Telefon) zuerst; innerhalb stabil nach Name. */
export function sortByContact(cands: BatchCandidate[]): BatchCandidate[] {
  return [...cands].sort((a, b) => {
    const ca = hasContact(a) ? 0 : 1
    const cb = hasContact(b) ? 0 : 1
    if (ca !== cb) return ca - cb
    return (a.name || '').localeCompare(b.name || '')
  })
}
