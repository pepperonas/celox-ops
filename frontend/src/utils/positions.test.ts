import { describe, it, expect } from 'vitest'
import { isAutoPosition } from './positions'

const pos = (beschreibung: string, auto?: boolean) => ({ beschreibung, auto })

describe('isAutoPosition', () => {
  it('flags positions explicitly marked auto', () => {
    expect(isAutoPosition(pos('Irgendwas', true))).toBe(true)
  })

  it('flags the infrastructure line', () => {
    expect(isAutoPosition(pos('Technische Infrastruktur & externe Systemkosten'))).toBe(true)
  })

  it('flags a title carrying a period stamp (legacy auto)', () => {
    expect(isAutoPosition(pos('Anzeige von Flyern (inkl. Admin-Zugang) (2026-04-30 – 2026-06-24)'))).toBe(true)
    // hyphen variant, not en-dash
    expect(isAutoPosition(pos('Entwicklung (2026-01-01 - 2026-01-31)'))).toBe(true)
  })

  it('flags KI- prefixed descriptions', () => {
    expect(isAutoPosition(pos('KI-Arbeitszeit März'))).toBe(true)
  })

  it('keeps manual positions (no flag, no period stamp)', () => {
    expect(isAutoPosition(pos('Email Datensicherung einrichten (lokal/Cloud)'))).toBe(false)
    expect(isAutoPosition(pos('Sicherheitsaudit und Härtung'))).toBe(false)
    // parenthetical that is NOT a date range must not match
    expect(isAutoPosition(pos('Anzeige von Flyern (inkl. Admin-Zugang)'))).toBe(false)
    expect(isAutoPosition(pos(''))).toBe(false)
  })
})
