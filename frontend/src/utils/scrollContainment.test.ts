import { describe, it, expect } from 'vitest'
import { containmentClass, needsContainment } from './scrollContainment'

describe('needsContainment', () => {
  it('kappt nicht, wenn der Container gar nicht scrollen kann', () => {
    // Der gemeldete Fehler: leere Spalte, 70vh hoch -> Mausrad tat nichts.
    expect(needsContainment(604, 604)).toBe(false)
    expect(needsContainment(41, 604)).toBe(false)   // Inhalt kleiner als Box
  })

  it('kappt, wenn der Inhalt wirklich ueberlaeuft', () => {
    expect(needsContainment(1134, 604)).toBe(true)
  })

  it('ignoriert Sub-Pixel-Rundung', () => {
    expect(needsContainment(605, 604)).toBe(false)
    expect(needsContainment(606, 604)).toBe(false)
    expect(needsContainment(607, 604)).toBe(true)
  })

  it('liefert die passende Klasse', () => {
    expect(containmentClass(true)).toBe('overscroll-contain')
    expect(containmentClass(false)).toBe('overscroll-auto')
  })
})
