import { describe, expect, it } from 'vitest'
import { filenameFromDisposition } from './downloadName'

describe('filenameFromDisposition', () => {
  it('liest quoted filename', () => {
    expect(
      filenameFromDisposition('attachment; filename="Rechnung_Beispiel-GmbH_CO-2026-0001.pdf"', 'x.pdf')
    ).toBe('Rechnung_Beispiel-GmbH_CO-2026-0001.pdf')
  })

  it('liest unquoted filename', () => {
    expect(filenameFromDisposition('attachment; filename=euer_2026.csv', 'x.csv')).toBe('euer_2026.csv')
  })

  it('bevorzugt RFC-5987 filename*', () => {
    expect(
      filenameFromDisposition(
        "attachment; filename=\"fallback.pdf\"; filename*=UTF-8''Stundennachweis%20S%C3%BCd.pdf",
        'x.pdf'
      )
    ).toBe('Stundennachweis Süd.pdf')
  })

  it('URL-encodete Namen werden dekodiert', () => {
    expect(filenameFromDisposition('attachment; filename="A%20B.pdf"', 'x.pdf')).toBe('A B.pdf')
  })

  it('Fallback ohne Header / ohne filename / bei kaputter Kodierung', () => {
    expect(filenameFromDisposition(undefined, 'fallback.pdf')).toBe('fallback.pdf')
    expect(filenameFromDisposition(null, 'fallback.pdf')).toBe('fallback.pdf')
    expect(filenameFromDisposition('inline', 'fallback.pdf')).toBe('fallback.pdf')
    // kaputtes %-Encoding im plain filename → roher Wert statt Exception
    expect(filenameFromDisposition('attachment; filename="100%_sicher.pdf"', 'x.pdf')).toBe(
      '100%_sicher.pdf'
    )
  })

  it('whitespace um = wird toleriert', () => {
    expect(filenameFromDisposition('attachment; filename = "a.zip"', 'x.zip')).toBe('a.zip')
  })
})
