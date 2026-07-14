// Quelle-Badge für Lead-Karten: kompaktes Label + Farbton je Herkunft.
export interface SourceBadge {
  label: string
  color: string   // Hex für Hintergrund/Text-Tönung
}

export function sourceBadge(source: string | null | undefined): SourceBadge {
  const s = (source || '').trim().toLowerCase()
  if (!s) return { label: 'Manuell', color: '#9aa6b5' }
  if (s.includes('ki-recherche') || s.includes('ki ')) return { label: '✨ KI', color: '#b3c5ff' }
  if (s.includes('linkedin')) return { label: 'LinkedIn', color: '#0a66c2' }
  if (s.includes('openstreetmap') || s === 'osm') return { label: 'OSM', color: '#57d98a' }
  if (s.includes('google')) return { label: 'Google', color: '#ea4335' }
  if (s.includes('empfehlung')) return { label: 'Empfehlung', color: '#f0b429' }
  if (s.includes('messe')) return { label: 'Messe', color: '#a371f7' }
  // Freitext-Quelle: gekürzt anzeigen
  const label = (source || '').trim()
  return { label: label.length > 16 ? label.slice(0, 15) + '…' : label, color: '#7cb0ff' }
}

/** Kanonischer Filter-Schlüssel, damit gleichartige Quellen zusammenfallen. */
export function sourceKey(source: string | null | undefined): string {
  return sourceBadge(source).label
}
