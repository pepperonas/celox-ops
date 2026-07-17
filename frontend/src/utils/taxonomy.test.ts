import { describe, it, expect } from 'vitest'
import { foldKey, canonicalize, dedupeCanonical, splitTags, rankSuggestions } from './taxonomy'

const VALUES = ['Geschäftsführung', 'Hausverwaltung', 'DSGVO', 'IT-Leitung']
const SYNONYMS = { GF: 'Geschäftsführung', dsvgo: 'DSGVO', 'it leiter': 'IT-Leitung' }

describe('foldKey', () => {
  it('trim + lowercase + Diakritika-Folding', () => {
    expect(foldKey('  Geschäftsführung ')).toBe('geschaftsfuhrung')
    expect(foldKey('Café')).toBe('cafe')
    expect(foldKey('')).toBe('')
  })
})

describe('canonicalize', () => {
  it('Synonym → kanonische Schreibweise (case-insensitiv)', () => {
    expect(canonicalize('gf', VALUES, SYNONYMS)).toBe('Geschäftsführung')
    expect(canonicalize('DSVGO', VALUES, SYNONYMS)).toBe('DSGVO')
    expect(canonicalize('IT Leiter', VALUES, SYNONYMS)).toBe('IT-Leitung')
  })
  it('Case-Variante eines bekannten Werts → dessen Schreibweise', () => {
    expect(canonicalize('hausverwaltung', VALUES, SYNONYMS)).toBe('Hausverwaltung')
  })
  it('creatable: Unbekanntes bleibt (getrimmt)', () => {
    expect(canonicalize('  Hofnarr  ', VALUES, SYNONYMS)).toBe('Hofnarr')
    expect(canonicalize('', VALUES, SYNONYMS)).toBe('')
  })
})

describe('dedupeCanonical', () => {
  it('kanonisiert + entfernt fold-Dubletten, Reihenfolge bleibt', () => {
    expect(dedupeCanonical(['hausverwaltung', 'Hausverwaltung', 'DSVGO', 'Neu'], VALUES, SYNONYMS))
      .toEqual(['Hausverwaltung', 'DSGVO', 'Neu'])
  })
  it('leere Einträge fliegen raus', () => {
    expect(dedupeCanonical(['', '  ', 'DSGVO'], VALUES, SYNONYMS)).toEqual(['DSGVO'])
  })
})

describe('splitTags', () => {
  it('Komma, Semikolon, Zeilenumbruch; trimmt; leere raus', () => {
    expect(splitTags('a, b ;c\nd,,  ')).toEqual(['a', 'b', 'c', 'd'])
  })
  it('einzelner Wert ohne Separator', () => {
    expect(splitTags('  Webshop ')).toEqual(['Webshop'])
  })
  it('leerer String → leere Liste', () => {
    expect(splitTags('')).toEqual([])
  })
})

describe('rankSuggestions', () => {
  const pool = ['Hausverwaltung', 'Handwerksbetrieb', 'Hotellerie', 'Steuerberater']
  it('leere Eingabe → Pool-Reihenfolge, limitiert', () => {
    expect(rankSuggestions(pool, '', 2)).toEqual(['Hausverwaltung', 'Handwerksbetrieb'])
  })
  it('filtert + rankt nach Match-Qualität', () => {
    const r = rankSuggestions(pool, 'haus')
    expect(r[0]).toBe('Hausverwaltung')
    expect(r).not.toContain('Steuerberater')
  })
  it('kein Treffer → leer', () => {
    expect(rankSuggestions(pool, 'xyz')).toEqual([])
  })
})
