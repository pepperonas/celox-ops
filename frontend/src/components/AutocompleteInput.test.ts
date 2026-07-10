import { describe, it, expect } from 'vitest'
import { POSITION_SUGGESTIONS, TITLE_SUGGESTIONS, DISCOUNT_REASON_SUGGESTIONS } from './AutocompleteInput'

describe('POSITION_SUGGESTIONS', () => {
  it('is a sizable list (>= 700 entries)', () => {
    expect(Array.isArray(POSITION_SUGGESTIONS)).toBe(true)
    expect(POSITION_SUGGESTIONS.length).toBeGreaterThanOrEqual(700)
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
    expect(has('Managed Server')).toBe(true)
    expect(has('WooCommerce')).toBe(true)
    expect(has('Ollama')).toBe(true)
  })
})

describe('TITLE_SUGGESTIONS', () => {
  it('is a sizable list (>= 480 entries)', () => {
    expect(Array.isArray(TITLE_SUGGESTIONS)).toBe(true)
    expect(TITLE_SUGGESTIONS.length).toBeGreaterThanOrEqual(480)
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

describe('DISCOUNT_REASON_SUGGESTIONS', () => {
  it('is a sizable list (>= 270 entries)', () => {
    expect(Array.isArray(DISCOUNT_REASON_SUGGESTIONS)).toBe(true)
    expect(DISCOUNT_REASON_SUGGESTIONS.length).toBeGreaterThanOrEqual(270)
  })

  it('contains no duplicates (Set-wrapped)', () => {
    expect(new Set(DISCOUNT_REASON_SUGGESTIONS).size).toBe(DISCOUNT_REASON_SUGGESTIONS.length)
  })

  it('has only non-empty, trimmed strings', () => {
    for (const s of DISCOUNT_REASON_SUGGESTIONS) {
      expect(typeof s).toBe('string')
      expect(s.length).toBeGreaterThan(0)
      expect(s).toBe(s.trim())
    }
  })

  it('keeps the legacy reasons and covers the new themes', () => {
    const has = (needle: string) =>
      DISCOUNT_REASON_SUGGESTIONS.some((s) => s.toLowerCase().includes(needle.toLowerCase()))
    // Bestand
    expect(has('Treuerabatt')).toBe(true)
    expect(has('Kulanz')).toBe(true)
    // Neu (explizit gewünscht + Themen)
    expect(has('Freundschaftsrabatt')).toBe(true)
    expect(has('Skonto')).toBe(true)
    expect(has('Preismatch')).toBe(true)
    expect(has('Barter')).toBe(true)
    expect(has('Start-up')).toBe(true)
    expect(has('Gemeinnützige')).toBe(true)
    expect(has('Funktionsrabatt')).toBe(true)
    expect(has('KI-Effizienzvorteil')).toBe(true)
    expect(has('SLA-Gutschrift')).toBe(true)
  })
})
