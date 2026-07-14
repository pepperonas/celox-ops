import { describe, it, expect } from 'vitest'
import { BRIEF_SUGGESTIONS, matchBriefs } from './briefSuggestions'

describe('BRIEF_SUGGESTIONS', () => {
  it('hat 20 Vorschläge, 3 mit Darmstadt, Rest Berlin', () => {
    expect(BRIEF_SUGGESTIONS).toHaveLength(20)
    const darmstadt = BRIEF_SUGGESTIONS.filter((s) => s.includes('Darmstadt'))
    expect(darmstadt).toHaveLength(3)
    expect(BRIEF_SUGGESTIONS.filter((s) => s.includes('Berlin'))).toHaveLength(17)
  })
  it('bildet Mittelstand + bekannte Branchen ab', () => {
    const joined = BRIEF_SUGGESTIONS.join(' ').toLowerCase()
    for (const w of ['hausverwaltung', 'steuer', 'anwalt', 'it-dienstleister', 'agentur', 'makler', 'zahnarzt', 'elektro'])
      expect(joined).toContain(w)
  })
})

describe('matchBriefs', () => {
  it('leere/kurze Eingabe → Standardliste', () => {
    expect(matchBriefs('')).toHaveLength(6)
    expect(matchBriefs('a')).toHaveLength(6)
  })
  it('Token-Treffer priorisiert passende Branche+Stadt', () => {
    const r = matchBriefs('steuer berlin')
    expect(r[0].toLowerCase()).toContain('steuer')
    expect(r[0]).toContain('Berlin')
  })
  it('findet Darmstadt', () => {
    expect(matchBriefs('darmstadt').every((s) => s.includes('Darmstadt'))).toBe(true)
  })
  it('Fuzzy: Tippfehler wird toleriert', () => {
    // "hausverwltung" (fehlt a) → Trigramm-Ähnlichkeit greift
    const r = matchBriefs('hausverwltung')
    expect(r.some((s) => s.toLowerCase().includes('hausverwaltung'))).toBe(true)
  })
  it('respektiert das Limit', () => {
    expect(matchBriefs('berlin', 3)).toHaveLength(3)
  })
})
