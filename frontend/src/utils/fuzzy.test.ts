import { describe, it, expect } from 'vitest'
import { fuzzyScore, fuzzyRank } from './fuzzy'

describe('fuzzyScore', () => {
  it('Substring schlägt Subsequenz', () => {
    expect(fuzzyScore('kanzlei', 'Muster Steuerkanzlei')).toBeGreaterThan(
      fuzzyScore('kzli', 'Muster Steuerkanzlei'),
    )
  })
  it('Wortanfang bekommt Bonus', () => {
    expect(fuzzyScore('muster', 'Muster GmbH')).toBeGreaterThan(fuzzyScore('muster', 'Alte Muster GmbH'))
  })
  it('Mehrwort-Query matcht über Tokens', () => {
    expect(fuzzyScore('muster kanzlei', 'Muster Steuerkanzlei Berlin')).toBeGreaterThan(0)
  })
  it('kein Treffer → 0', () => {
    expect(fuzzyScore('xyz', 'Muster GmbH')).toBe(0)
  })
  it('diakritik-insensitiv', () => {
    expect(fuzzyScore('koln', 'Kölner Kanzlei')).toBeGreaterThan(0)
  })
})

describe('fuzzyRank', () => {
  const items = [
    { company: 'Muster Steuerkanzlei', contact: 'Anna Meier' },
    { company: 'Berliner Beratung', contact: 'Bernd Muster' },
    { company: 'Nord GmbH', contact: '' },
  ]
  it('rankt über mehrere Felder und filtert Nicht-Treffer', () => {
    const r = fuzzyRank(items, 'muster', (i) => [i.company, i.contact])
    expect(r.length).toBe(2)
    expect(r[0].company).toBe('Muster Steuerkanzlei') // Wortanfang gewinnt
  })
  it('leere Query → erste N unverändert', () => {
    expect(fuzzyRank(items, '', (i) => [i.company], 2).length).toBe(2)
  })
})
