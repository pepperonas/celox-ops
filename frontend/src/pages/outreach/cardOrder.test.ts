import { describe, expect, it } from 'vitest'
import { applyVisibleOrder, moveBy, moveItem, orderIds, sortFavorites } from './cardOrder'

const ids = (list: { id: string }[]) => list.map((t) => t.id).join('')
const liste = (s: string) => [...s].map((id) => ({ id }))

describe('moveItem', () => {
  it('verschiebt nach unten auf den Platz der Zielkarte', () => {
    // A auf die Position von C gezogen → A steht dort, C rückt auf.
    expect(ids(moveItem(liste('ABCD'), 0, 2))).toBe('BCAD')
  })

  it('verschiebt nach oben auf den Platz der Zielkarte', () => {
    expect(ids(moveItem(liste('ABCD'), 3, 1))).toBe('ADBC')
  })

  it('gleiche Position ändert nichts und liefert dieselbe Liste', () => {
    const l = liste('ABC')
    expect(moveItem(l, 1, 1)).toBe(l)
  })

  it('klemmt Ziele außerhalb der Liste statt Löcher zu erzeugen', () => {
    expect(ids(moveItem(liste('ABC'), 0, 99))).toBe('BCA')
    expect(ids(moveItem(liste('ABC'), 2, -5))).toBe('CAB')
  })

  it('ignoriert einen ungültigen Startindex', () => {
    const l = liste('ABC')
    expect(moveItem(l, 7, 0)).toBe(l)
    expect(moveItem(l, -1, 0)).toBe(l)
  })

  it('lässt die Eingabeliste unverändert', () => {
    const l = liste('ABC')
    moveItem(l, 0, 2)
    expect(ids(l)).toBe('ABC')
  })
})

describe('moveBy', () => {
  it('einen Platz hoch und runter', () => {
    expect(ids(moveBy(liste('ABCD'), 2, -1))).toBe('ACBD')
    expect(ids(moveBy(liste('ABCD'), 1, 1))).toBe('ACBD')
  })

  it('am Rand passiert nichts Kaputtes', () => {
    expect(ids(moveBy(liste('ABC'), 0, -1))).toBe('ABC')
    expect(ids(moveBy(liste('ABC'), 2, 1))).toBe('ABC')
  })
})

describe('applyVisibleOrder', () => {
  it('füllt nur die Plätze der sichtbaren Karten neu', () => {
    // Das ist der eigentliche Knackpunkt: Gezogen wird in einer gefilterten
    // Ansicht, gespeichert wird die Reihenfolge des ganzen Kanals. Die nicht
    // sichtbaren Karten (b, d) müssen ihre Plätze behalten — sonst sortiert ein
    // Zug in einer Rubrik unbemerkt den kompletten Kanal um.
    const voll = liste('AbCdE')
    const neueSicht = liste('EAC')
    expect(ids(applyVisibleOrder(voll, neueSicht))).toBe('EbAdC')
  })

  it('ohne Filter ist es die neue Reihenfolge selbst', () => {
    const voll = liste('ABC')
    expect(ids(applyVisibleOrder(voll, liste('CBA')))).toBe('CBA')
  })

  it('leere Sicht lässt alles unangetastet', () => {
    const voll = liste('ABC')
    expect(ids(applyVisibleOrder(voll, []))).toBe('ABC')
  })

  it('eine einzige sichtbare Karte kann nicht verschoben werden', () => {
    // Richtig so: In einer Ansicht mit einem Element gibt es keinen anderen Platz.
    expect(ids(applyVisibleOrder(liste('aBc'), liste('B')))).toBe('aBc')
  })

  it('behält die Länge der vollen Liste', () => {
    const voll = liste('AbCdEfG')
    expect(applyVisibleOrder(voll, liste('GECA'))).toHaveLength(voll.length)
  })
})

describe('orderIds', () => {
  it('liefert die IDs in Reihenfolge', () => {
    expect(orderIds(liste('CAB'))).toEqual(['C', 'A', 'B'])
  })
})

describe('sortFavorites', () => {
  const f = (title: string, favorite_order: number | null) => ({ title, favorite_order })

  it('sortiert nach der eigenen Favoriten-Reihenfolge', () => {
    // Eigene Ordnung, weil die Sektion kanalübergreifend ist: sort_order zählt je
    // Kanal ab 0, geerbt stünden eine Telefon- und eine E-Mail-Vorlage mit 0
    // willkürlich nebeneinander.
    const out = sortFavorites([f('C', 2), f('A', 0), f('B', 1)])
    expect(out.map((x) => x.title)).toEqual(['A', 'B', 'C'])
  })

  it('noch nicht einsortierte hängen hinten', () => {
    // Ein neu gesetzter Stern darf eine bestehende Anordnung nicht durchmischen.
    const out = sortFavorites([f('Neu', null), f('Alt', 0)])
    expect(out.map((x) => x.title)).toEqual(['Alt', 'Neu'])
  })

  it('ohne jede Reihenfolge nach Titel — vorhersagbar statt willkürlich', () => {
    const out = sortFavorites([f('Zeta', null), f('Alpha', null), f('Ärger', null)])
    expect(out.map((x) => x.title)).toEqual(['Alpha', 'Ärger', 'Zeta'])
  })

  it('gleiche Nummer wird über den Titel entschieden', () => {
    const out = sortFavorites([f('B', 3), f('A', 3)])
    expect(out.map((x) => x.title)).toEqual(['A', 'B'])
  })

  it('Nummer 0 gilt als gesetzt, nicht als leer', () => {
    // Klassischer Fehler: 0 ist falsy. Wäre die Prüfung `!favorite_order`, fiele
    // der erste Favorit an das Ende der Liste.
    const out = sortFavorites([f('Zweiter', null), f('Erster', 0)])
    expect(out.map((x) => x.title)).toEqual(['Erster', 'Zweiter'])
  })

  it('lässt die Eingabeliste unverändert', () => {
    const eingabe = [f('B', 1), f('A', 0)]
    sortFavorites(eingabe)
    expect(eingabe.map((x) => x.title)).toEqual(['B', 'A'])
  })
})
