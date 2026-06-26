import { describe, it, expect } from 'vitest'
import { POSITION_SUGGESTIONS } from './AutocompleteInput'

describe('POSITION_SUGGESTIONS', () => {
  it('is a sizable list (>= 300 entries)', () => {
    expect(Array.isArray(POSITION_SUGGESTIONS)).toBe(true)
    expect(POSITION_SUGGESTIONS.length).toBeGreaterThanOrEqual(300)
  })

  it('contains no duplicates', () => {
    expect(new Set(POSITION_SUGGESTIONS).size).toBe(POSITION_SUGGESTIONS.length)
  })

  it('has only non-empty, trimmed strings', () => {
    for (const s of POSITION_SUGGESTIONS) {
      expect(typeof s).toBe('string')
      expect(s.length).toBeGreaterThan(0)
      expect(s).toBe(s.trim())
    }
  })

  it('covers the key themes (admin/mail, marketing, DSGVO, security)', () => {
    const has = (needle: string) =>
      POSITION_SUGGESTIONS.some((s) => s.toLowerCase().includes(needle.toLowerCase()))
    expect(has('E-Mail-Backup aller Postfächer')).toBe(true)
    expect(has('AGB')).toBe(true)
    expect(has('DSGVO')).toBe(true)
    expect(has('Penetrationstest')).toBe(true)
    expect(has('Newsletter')).toBe(true)
    expect(has('Auftragsverarbeitungsvertrag')).toBe(true)
  })
})
