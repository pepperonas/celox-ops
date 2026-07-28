import { describe, expect, it } from 'vitest'
import { applyFrozenOrder, flipDeltas, orderSnapshot } from './listOrder'

const item = (id: string) => ({ id })

describe('applyFrozenOrder', () => {
  it('haelt die eingefrorene Reihenfolge, auch wenn die Sortierung anders will', () => {
    // Natuerlich sortiert waere c, a, b (z. B. weil c jetzt hohe Prio hat).
    const natural = [item('c'), item('a'), item('b')]
    const frozen = ['a', 'b', 'c']
    expect(applyFrozenOrder(natural, frozen).map((i) => i.id)).toEqual(['a', 'b', 'c'])
  })

  it('ohne Aufnahme bleibt die natuerliche Sortierung', () => {
    const natural = [item('c'), item('a')]
    expect(applyFrozenOrder(natural, null).map((i) => i.id)).toEqual(['c', 'a'])
    expect(applyFrozenOrder(natural, []).map((i) => i.id)).toEqual(['c', 'a'])
  })

  it('neue Eintraege bleiben, wohin die Sortierung sie gesetzt hat', () => {
    // „neu" wurde gerade angelegt und steht natuerlich zwischen a und b —
    // es darf nicht ans Ende rutschen, nur weil eine Prio geaendert wurde.
    const natural = [item('a'), item('neu'), item('b')]
    expect(applyFrozenOrder(natural, ['a', 'b']).map((i) => i.id))
      .toEqual(['a', 'neu', 'b'])
  })

  it('ein neuer Eintrag ganz vorn bleibt vorn', () => {
    const natural = [item('neu'), item('a'), item('b')]
    expect(applyFrozenOrder(natural, ['a', 'b']).map((i) => i.id))
      .toEqual(['neu', 'a', 'b'])
  })

  it('verschwundene Eintraege in der Aufnahme stoeren nicht', () => {
    const natural = [item('b'), item('a')]
    expect(applyFrozenOrder(natural, ['a', 'geloescht', 'b']).map((i) => i.id))
      .toEqual(['a', 'b'])
  })

  it('veraendert die Eingabeliste nicht', () => {
    const natural = [item('c'), item('a')]
    applyFrozenOrder(natural, ['a', 'c'])
    expect(natural.map((i) => i.id)).toEqual(['c', 'a'])
  })
})

describe('flipDeltas', () => {
  it('liefert die Verschiebung, die eine Zeile optisch an ihrem alten Platz haelt', () => {
    const before = new Map([['a', 100], ['b', 160]])
    const after = new Map([['a', 160], ['b', 100]])
    expect(flipDeltas(before, after)).toEqual([
      { id: 'a', delta: -60 },   // a ist nach unten gewandert -> von oben kommen
      { id: 'b', delta: 60 },
    ])
  })

  it('unbewegte Zeilen werden nicht animiert', () => {
    const same = new Map([['a', 100], ['b', 160]])
    expect(flipDeltas(same, same)).toEqual([])
  })

  it('Subpixel-Rauschen wird ignoriert', () => {
    expect(flipDeltas(new Map([['a', 100]]), new Map([['a', 100.4]]))).toEqual([])
  })

  it('neu eingefuegte Zeilen bewegen sich nicht (kein Vorher)', () => {
    expect(flipDeltas(new Map(), new Map([['neu', 100]]))).toEqual([])
  })
})

describe('orderSnapshot', () => {
  it('flacht Gruppen in Anzeigereihenfolge ab', () => {
    expect(orderSnapshot([{ items: [item('a'), item('b')] }, { items: [item('c')] }]))
      .toEqual(['a', 'b', 'c'])
  })

  it('leere Gruppen ergeben eine leere Aufnahme', () => {
    expect(orderSnapshot([])).toEqual([])
  })
})
