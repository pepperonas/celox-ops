import { describe, expect, it } from 'vitest'
import { actionLabel, changeSummary, FIELD_LABELS, formatValue } from './leadChanges'

describe('formatValue', () => {
  it('macht leere Werte sichtbar statt sie zu verschweigen', () => {
    for (const v of [null, undefined, '']) expect(formatValue(v)).toBe('(leer)')
    expect(formatValue([])).toBe('(leer)')
  })

  it('übersetzt Wahrheitswerte und Listen', () => {
    expect(formatValue(true)).toBe('ja')
    expect(formatValue(false)).toBe('nein')
    expect(formatValue(['a', 'b'])).toBe('a, b')
  })

  it('kürzt lange Texte mit Auslassung', () => {
    const out = formatValue('x'.repeat(200))
    expect(out.length).toBeLessThanOrEqual(61)
    expect(out.endsWith('…')).toBe(true)
  })

  it('behält kurze Werte unverändert', () => {
    expect(formatValue('Alpha GmbH')).toBe('Alpha GmbH')
    expect(formatValue(42)).toBe('42')
  })
})

describe('changeSummary', () => {
  it('sortiert stabil, damit die Anzeige zwischen Ladevorgängen nicht springt', () => {
    const lines = changeSummary({
      notes: { old: 'alt', new: 'neu' },
      company: { old: 'A', new: 'B' },
    })
    expect(lines.map((l) => l.field)).toEqual(['company', 'notes'])
  })

  it('übersetzt Feldnamen und Werte', () => {
    const [line] = changeSummary({ employee_count: { old: null, new: 50 } })
    expect(line.label).toBe('Mitarbeiterzahl')
    expect(line.from).toBe('(leer)')
    expect(line.to).toBe('50')
  })

  it('fällt bei unbekanntem Feld auf den technischen Namen zurück', () => {
    const [line] = changeSummary({ irgendwas: { old: 1, new: 2 } })
    expect(line.label).toBe('irgendwas')
  })

  it('verträgt fehlende Angaben', () => {
    expect(changeSummary(null)).toEqual([])
    expect(changeSummary(undefined)).toEqual([])
    expect(changeSummary({})).toEqual([])
  })
})

describe('actionLabel', () => {
  it('benennt alle Vorgänge deutsch', () => {
    expect(actionLabel('update')).toBe('geändert')
    expect(actionLabel('delete')).toBe('in den Papierkorb')
    expect(actionLabel('restore')).toBe('zurückgeholt')
    expect(actionLabel('unbekannt')).toBe('unbekannt')
  })
})

describe('FIELD_LABELS', () => {
  it('deckt die protokollierten Felder ab', () => {
    // Spiegelt TRACKED_FIELDS im Backend — fehlt ein Label, zeigt die UI den
    // technischen Namen. Die Liste hier hält das sichtbar.
    for (const f of ['company', 'status', 'notes', 'tags', 'value_estimate', 'pinned']) {
      expect(FIELD_LABELS[f]).toBeTruthy()
    }
  })
})
