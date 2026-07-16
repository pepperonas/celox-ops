import { describe, it, expect } from 'vitest'
import {
  brancheFromTags,
  CATEGORIES,
  CATEGORY_LABEL,
  CHANNELS,
  PLACEHOLDERS,
} from './constants'

describe('brancheFromTags', () => {
  it('erster nicht-generischer Tag', () => {
    expect(brancheFromTags(['discovery', 'Steuerberater'])).toBe('Steuerberater')
    expect(brancheFromTags(['ki-recherche', 'Hausverwaltung', 'x'])).toBe('Hausverwaltung')
  })
  it('nur generische Tags → leer', () => {
    expect(brancheFromTags(['discovery', 'linkedin', 'rainmaker', 'ki-recherche', 'vorgemerkt'])).toBe('')
  })
  it('null / leer → leer', () => {
    expect(brancheFromTags(null)).toBe('')
    expect(brancheFromTags([])).toBe('')
  })
  it('case-insensitiv bei generisch, aber Original-Schreibweise zurück', () => {
    expect(brancheFromTags(['LinkedIn', 'Immobilien'])).toBe('Immobilien')
  })
})

describe('constants Integrität', () => {
  it('CATEGORY_LABEL deckt alle CATEGORIES ab', () => {
    for (const c of CATEGORIES) {
      expect(CATEGORY_LABEL[c.value]).toBe(c.label)
    }
  })
  it('3 Kanäle mit Icon + Label', () => {
    expect(CHANNELS.map((c) => c.value)).toEqual(['email', 'linkedin', 'phone'])
    expect(CHANNELS.every((c) => c.icon && c.label)).toBe(true)
  })
  it('Platzhalter-Keys sind eindeutig und enthalten die Kern-Platzhalter', () => {
    const keys = PLACEHOLDERS.map((p) => p.key)
    expect(new Set(keys).size).toBe(keys.length)
    for (const k of ['anrede', 'name', 'firma', 'branche', 'risiko_branche', 'zielsystem', 'audit_preis']) {
      expect(keys).toContain(k)
    }
  })
  it('nur name/firma/branche sind aus dem Lead befüllbar', () => {
    const fromLead = PLACEHOLDERS.filter((p) => p.fromLead).map((p) => p.key).sort()
    expect(fromLead).toEqual(['branche', 'firma', 'name'])
  })
})
