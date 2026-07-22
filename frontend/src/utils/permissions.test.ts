import { describe, expect, it } from 'vitest'
import { canDelete } from './permissions'

describe('canDelete', () => {
  it('erlaubt Löschen für Admin und Benutzer', () => {
    expect(canDelete('admin')).toBe(true)
    expect(canDelete('user')).toBe(true)
  })

  it('sperrt Löschen für Mitarbeiter', () => {
    expect(canDelete('mitarbeiter')).toBe(false)
  })

  it('fällt bei unbekannter/fehlender Rolle auf erlaubt zurück (Server entscheidet)', () => {
    expect(canDelete(null)).toBe(true)
    expect(canDelete(undefined)).toBe(true)
    expect(canDelete('')).toBe(true)
  })

  it('toleriert Leerraum', () => {
    expect(canDelete(' mitarbeiter ')).toBe(false)
  })
})
