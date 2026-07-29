import { describe, it, expect } from 'vitest'
import {
  brancheFromTags,
  CATEGORIES,
  CATEGORY_AXIS,
  CATEGORY_LABEL,
  CHANNELS,
  isOfferCategory,
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
  it('jede Rubrik liegt auf genau einer Achse — keine fällt aus der Leiste', () => {
    // Die Filterleiste rendert zwei Reihen, gefiltert nach CATEGORY_AXIS. Eine
    // Rubrik ohne Achse wäre unsichtbar: ihre Vorlagen ließen sich nicht mehr
    // filtern. Der Record ist total, TS fängt Fehlendes — dieser Test fängt den
    // Fall, dass die Ableitung der Reihen selbst nicht mehr alles abdeckt.
    const axisKeys = Object.keys(CATEGORY_AXIS).sort()
    const chipKeys = CATEGORIES.map((c) => c.value as string).sort()
    expect(axisKeys).toEqual(chipKeys)
    const anlass = CATEGORIES.filter((c) => CATEGORY_AXIS[c.value] === 'anlass')
    const angebot = CATEGORIES.filter((c) => CATEGORY_AXIS[c.value] === 'angebot')
    expect(anlass.length + angebot.length).toBe(CATEGORIES.length)
    expect(anlass.length).toBeGreaterThan(0)
    expect(angebot.length).toBeGreaterThan(0)
  })

  it('die drei Produktlinien zählen als Angebot, die Phasen nicht', () => {
    for (const c of ['datenschutz_dsms', 'portal_assessment', 'bcsbook_zeit',
                     'security_audit', 'ki_automatisierung'] as const) {
      expect(isOfferCategory(c), `${c} sollte ein Angebot sein`).toBe(true)
    }
    for (const c of ['kaltakquise', 'followup', 'reaktivierung', 'empfehlung',
                     'angebot_nachfassen'] as const) {
      expect(isOfferCategory(c), `${c} ist ein Anlass, kein Angebot`).toBe(false)
    }
  })

  it('nur name/firma/branche/mitarbeiter sind aus dem Lead befüllbar', () => {
    // Die Liste ist absichtlich eng: Jeder Eintrag braucht eine Entsprechung in
    // CopyModal (Lead-Feld → Platzhalter). Ein Key ohne Mapping bliebe leer und
    // die Nachricht ginge mit einem sichtbaren {{platzhalter}} raus.
    const fromLead = PLACEHOLDERS.filter((p) => p.fromLead).map((p) => p.key).sort()
    expect(fromLead).toEqual(['branche', 'firma', 'mitarbeiter', 'name'])
  })
})
