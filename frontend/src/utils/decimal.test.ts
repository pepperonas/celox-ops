import { describe, it, expect } from 'vitest'
import { parseDecimalInput } from './decimal'

describe('parseDecimalInput', () => {
  it('parses dot decimals', () => {
    expect(parseDecimalInput('0.45')).toBe(0.45)
    expect(parseDecimalInput('12.5')).toBe(12.5)
  })

  it('parses comma decimals (German)', () => {
    expect(parseDecimalInput('0,45')).toBe(0.45)
    expect(parseDecimalInput('1,5')).toBe(1.5)
  })

  it('treats comma and dot identically', () => {
    expect(parseDecimalInput('3,75')).toBe(parseDecimalInput('3.75'))
  })

  it('handles leading-separator and whitespace', () => {
    expect(parseDecimalInput(',5')).toBe(0.5)
    expect(parseDecimalInput('.5')).toBe(0.5)
    expect(parseDecimalInput('  2,25 ')).toBe(2.25)
  })

  it('returns 0 for empty / invalid / separator-only input', () => {
    expect(parseDecimalInput('')).toBe(0)
    expect(parseDecimalInput('abc')).toBe(0)
    expect(parseDecimalInput(',')).toBe(0)
    expect(parseDecimalInput('.')).toBe(0)
  })

  it('parses integers and negatives', () => {
    expect(parseDecimalInput('7')).toBe(7)
    expect(parseDecimalInput('-3,5')).toBe(-3.5)
  })
})
