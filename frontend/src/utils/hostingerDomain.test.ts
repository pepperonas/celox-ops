import { describe, expect, it } from 'vitest'
import { domainHint, humanGap, shortDescription } from './hostingerDomain'

describe('humanGap', () => {
  it('nennt Sekunden, Minuten, Stunden und Tage', () => {
    expect(humanGap(1)).toBe('1 s')
    expect(humanGap(89)).toBe('89 s')
    expect(humanGap(92)).toBe('2 min')
    expect(humanGap(10149)).toBe('3 h')
    expect(humanGap(433828)).toBe('5 Tage')
  })

  it('behauptet ohne Wert keine Zahl', () => {
    expect(humanGap(null)).toBe('unbekannter Abstand')
    expect(humanGap(undefined)).toBe('unbekannter Abstand')
  })
})

describe('domainHint', () => {
  it('bestaetigte Zuordnung braucht keine Pruefung', () => {
    const h = domainHint('confirmed', 1)
    expect(h.check).toBe(false)
    expect(h.tone).toBe('ok')
    expect(h.title).toMatch(/bestätigt/)
  })

  it('gleiche Bestellung wird begruendet, nicht behauptet', () => {
    const h = domainHint('same_order', 3)
    expect(h.check).toBe(false)
    expect(h.title).toContain('3 s')
    expect(h.title).toMatch(/dieselbe Bestellung/)
  })

  it('reine Reihenfolge-Ableitung verlangt einen Blick', () => {
    const h = domainHint('sequence', 433828)
    expect(h.check).toBe(true)
    expect(h.tone).toBe('warn')
    expect(h.title).toContain('5 Tage')
  })

  it('ohne Zuordnung wird zur Auswahl aufgefordert', () => {
    const h = domainHint('unmatched', null)
    expect(h.check).toBe(true)
    expect(h.title).toMatch(/auswählen/)
    // Auch ein fehlender Wert darf nicht als gesichert durchgehen.
    expect(domainHint(null, null).check).toBe(true)
  })
})

describe('shortDescription', () => {
  it('entfernt den Domainnamen, weil ihn die eigene Spalte zeigt', () => {
    expect(shortDescription('Domain mapsmate.de (Hostinger)', 'mapsmate.de'))
      .toBe('Domain (Hostinger)')
  })

  it('laesst alles stehen, wenn keine Domain zugeordnet ist', () => {
    expect(shortDescription('Domain .de (Hostinger)', null))
      .toBe('Domain .de (Hostinger)')
    expect(shortDescription('VPS KVM 4 · celox.server (Hostinger)', null))
      .toBe('VPS KVM 4 · celox.server (Hostinger)')
  })
})
