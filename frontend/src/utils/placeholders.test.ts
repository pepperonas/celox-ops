import { describe, it, expect } from 'vitest'
import { extractPlaceholders, fillPlaceholders } from './placeholders'

describe('extractPlaceholders', () => {
  it('findet eindeutige Keys unabhängig von Whitespace/Case', () => {
    const t = 'Hallo {{name}}, bei {{ firma }} und nochmal {{NAME}} und {{risiko_branche}}.'
    expect(extractPlaceholders(t).sort()).toEqual(['firma', 'name', 'risiko_branche'])
  })
  it('leerer Text → keine Platzhalter', () => {
    expect(extractPlaceholders('kein Platzhalter hier')).toEqual([])
  })
})

describe('fillPlaceholders', () => {
  it('ersetzt gefüllte, lässt leere als {{key}} und meldet missing', () => {
    const { text, missing } = fillPlaceholders(
      'Hallo {{name}} von {{firma}}, Thema {{aufhaenger}}.',
      { name: 'Frau Meier', firma: 'Muster GmbH', aufhaenger: '' },
    )
    expect(text).toBe('Hallo Frau Meier von Muster GmbH, Thema {{aufhaenger}}.')
    expect(missing).toEqual(['aufhaenger'])
  })
  it('trimmt Werte und behandelt Whitespace-Werte als leer', () => {
    const { text, missing } = fillPlaceholders('{{a}}-{{b}}', { a: '  X  ', b: '   ' })
    expect(text).toBe('X-{{b}}')
    expect(missing).toEqual(['b'])
  })
  it('keine offenen Platzhalter → missing leer', () => {
    const { missing } = fillPlaceholders('{{name}}', { name: 'Test' })
    expect(missing).toEqual([])
  })
})
