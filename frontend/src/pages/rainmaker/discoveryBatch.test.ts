import { describe, it, expect } from 'vitest'
import {
  candidateKey, hasContact, mergeCandidates, parseLocations, sortByContact,
  type BatchCandidate,
} from './discoveryBatch'
import type { DiscoveredCandidate } from '../../types'

const cand = (over: Partial<DiscoveredCandidate>): DiscoveredCandidate => ({
  name: 'X', website: null, phone: null, address: null,
  source: 'OpenStreetMap', source_ref: null, duplicate: false, ...over,
})

describe('parseLocations', () => {
  it('trennt an Komma/Semikolon/Zeilenumbruch und dedupliziert', () => {
    expect(parseLocations('Berlin, Potsdam\nBerlin; München')).toEqual(['Berlin', 'Potsdam', 'München'])
  })
  it('ignoriert Leerzeichen und Leereinträge', () => {
    expect(parseLocations('  Berlin ,, ')).toEqual(['Berlin'])
  })
})

describe('candidateKey', () => {
  it('nutzt die normalisierte Domain', () => {
    expect(candidateKey(cand({ website: 'https://www.Firma.de/impressum' }))).toBe('w:firma.de')
  })
  it('fällt auf den Namen zurück', () => {
    expect(candidateKey(cand({ name: 'Muster GmbH' }))).toBe('n:muster gmbh')
  })
})

describe('mergeCandidates', () => {
  it('dedupliziert über Kombinationen hinweg', () => {
    let acc: BatchCandidate[] = []
    acc = mergeCandidates(acc, [cand({ name: 'A', website: 'https://a.de' })], 'steuerkanzlei', 'Steuerkanzlei · Berlin')
    acc = mergeCandidates(acc, [cand({ name: 'A GmbH', website: 'http://www.a.de' })], 'hausverwaltung', 'Hausverwaltung · Berlin')
    expect(acc).toHaveLength(1)
    expect(acc[0]._segment).toBe('steuerkanzlei')  // erster Fund gewinnt
  })
  it('behält duplicate=true, wenn ein späterer Treffer es setzt', () => {
    let acc: BatchCandidate[] = []
    acc = mergeCandidates(acc, [cand({ name: 'B', website: 'https://b.de', duplicate: false })], 's', 'c1')
    acc = mergeCandidates(acc, [cand({ name: 'B', website: 'https://b.de', duplicate: true })], 's', 'c2')
    expect(acc[0].duplicate).toBe(true)
  })
})

describe('hasContact / sortByContact', () => {
  it('erkennt Kontaktweg', () => {
    expect(hasContact(cand({ website: 'https://x.de' }))).toBe(true)
    expect(hasContact(cand({ phone: '030-1' }))).toBe(true)
    expect(hasContact(cand({}))).toBe(false)
  })
  it('sortiert kontaktfähige nach vorn', () => {
    const merged = mergeCandidates([], [
      cand({ name: 'Ohne' }),
      cand({ name: 'Mit', website: 'https://mit.de' }),
    ], 's', 'c')
    const sorted = sortByContact(merged)
    expect(sorted[0].name).toBe('Mit')
    expect(sorted[1].name).toBe('Ohne')
  })
})
