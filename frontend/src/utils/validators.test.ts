import { describe, it, expect } from 'vitest'
import { validateEmail, validateRequired } from './validators'

describe('validateEmail', () => {
  it('passes empty (optional field)', () => {
    expect(validateEmail('')).toBeNull()
  })
  it('accepts a valid address', () => {
    expect(validateEmail('martin@celox.io')).toBeNull()
  })
  it('rejects a missing domain dot', () => {
    expect(validateEmail('martin@celox')).not.toBeNull()
  })
  it('rejects a string without @', () => {
    expect(validateEmail('celox.io')).not.toBeNull()
  })
  it('rejects whitespace', () => {
    expect(validateEmail('a b@c.de')).not.toBeNull()
  })
})

describe('validateRequired', () => {
  it('rejects empty string with field name', () => {
    expect(validateRequired('', 'Firma')).toBe('Firma ist ein Pflichtfeld.')
  })
  it('rejects null and undefined', () => {
    expect(validateRequired(null, 'X')).not.toBeNull()
    expect(validateRequired(undefined, 'X')).not.toBeNull()
  })
  it('accepts a non-empty string', () => {
    expect(validateRequired('Celox', 'Firma')).toBeNull()
  })
  it('accepts zero (a valid number)', () => {
    expect(validateRequired(0, 'Betrag')).toBeNull()
  })
})
