import { describe, it, expect } from 'vitest'
import { sourceBadge, sourceKey } from './leadSources'

describe('sourceBadge', () => {
  it('leere Quelle → Manuell', () => {
    expect(sourceBadge(null).label).toBe('Manuell')
    expect(sourceBadge('').label).toBe('Manuell')
  })

  it('erkennt die Import-Quellen', () => {
    expect(sourceBadge('LinkedIn-Import').label).toBe('LinkedIn')
    expect(sourceBadge('OpenStreetMap').label).toBe('OSM')
    expect(sourceBadge('Google Places').label).toBe('Google')
  })

  it('kürzt lange Freitext-Quellen', () => {
    const b = sourceBadge('Kaltakquise Telefonliste 2026 Q1')
    expect(b.label.endsWith('…')).toBe(true)
    expect(b.label.length).toBeLessThanOrEqual(16)
  })

  it('sourceKey fasst gleichartige Quellen zusammen', () => {
    expect(sourceKey('OpenStreetMap')).toBe(sourceKey('osm'))
  })
})
