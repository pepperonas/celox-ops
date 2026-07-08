import { describe, it, expect } from 'vitest'
import { FALLBACK_USD_EUR, sanitizeRate } from './exchangeRate'

describe('sanitizeRate', () => {
  it('akzeptiert plausible Kurse', () => {
    expect(sanitizeRate(0.87689)).toBe(0.87689)
    expect(sanitizeRate('0.92')).toBe(0.92)
  })

  it('fällt bei implausiblen/kaputten Werten auf den Fallback zurück', () => {
    expect(sanitizeRate(92)).toBe(FALLBACK_USD_EUR)
    expect(sanitizeRate(0.009)).toBe(FALLBACK_USD_EUR)
    expect(sanitizeRate(NaN)).toBe(FALLBACK_USD_EUR)
    expect(sanitizeRate(undefined)).toBe(FALLBACK_USD_EUR)
    expect(sanitizeRate('kaputt')).toBe(FALLBACK_USD_EUR)
    expect(sanitizeRate(null)).toBe(FALLBACK_USD_EUR)
  })

  it('Fallback selbst ist plausibel', () => {
    expect(FALLBACK_USD_EUR).toBeGreaterThanOrEqual(0.5)
    expect(FALLBACK_USD_EUR).toBeLessThanOrEqual(1.5)
  })
})
