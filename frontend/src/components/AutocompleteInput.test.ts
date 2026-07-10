import { describe, it, expect } from 'vitest'
import { POSITION_SUGGESTIONS, TITLE_SUGGESTIONS } from './AutocompleteInput'

describe('POSITION_SUGGESTIONS', () => {
  it('is a sizable list (>= 550 entries)', () => {
    expect(Array.isArray(POSITION_SUGGESTIONS)).toBe(true)
    expect(POSITION_SUGGESTIONS.length).toBeGreaterThanOrEqual(550)
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

  it('covers the celox portfolio themes (KI-Automatisierung, E-Rechnung, NIS2, M365)', () => {
    const has = (needle: string) =>
      POSITION_SUGGESTIONS.some((s) => s.toLowerCase().includes(needle.toLowerCase()))
    expect(has('RAG')).toBe(true)
    expect(has('Prompt')).toBe(true)
    expect(has('ZUGFeRD')).toBe(true)
    expect(has('NIS2')).toBe(true)
    expect(has('SharePoint')).toBe(true)
    expect(has('Phishing-Simulation')).toBe(true)
    expect(has('Externer Datenschutzbeauftragter')).toBe(true)
  })
})

describe('TITLE_SUGGESTIONS', () => {
  it('is a sizable list (>= 380 entries)', () => {
    expect(Array.isArray(TITLE_SUGGESTIONS)).toBe(true)
    expect(TITLE_SUGGESTIONS.length).toBeGreaterThanOrEqual(380)
  })

  it('contains no duplicates (Set-wrapped)', () => {
    expect(new Set(TITLE_SUGGESTIONS).size).toBe(TITLE_SUGGESTIONS.length)
  })

  it('has only non-empty, trimmed strings', () => {
    for (const s of TITLE_SUGGESTIONS) {
      expect(typeof s).toBe('string')
      expect(s.length).toBeGreaterThan(0)
      expect(s).toBe(s.trim())
    }
  })

  it('covers project-level celox themes (KI, Security, DSGVO, Betrieb)', () => {
    const has = (needle: string) =>
      TITLE_SUGGESTIONS.some((s) => s.toLowerCase().includes(needle.toLowerCase()))
    expect(has('KI-Automatisierung')).toBe(true)
    expect(has('KI-Reifegrad')).toBe(true)
    expect(has('Penetrationstest')).toBe(true)
    expect(has('Phishing-Simulation')).toBe(true)
    expect(has('E-Rechnung')).toBe(true)
    expect(has('Externer Datenschutzbeauftragter')).toBe(true)
    expect(has('Managed IT')).toBe(true)
    expect(has('BFSG')).toBe(true)
  })
})
