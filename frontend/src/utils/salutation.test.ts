import { describe, it, expect } from 'vitest'
import { timeGreeting, FALLBACK_NAME } from './salutation'

const at = (h: number) => new Date(2026, 0, 1, h, 0, 0)

describe('timeGreeting', () => {
  it('morgens (5–10) → Guten Morgen', () => {
    expect(timeGreeting(at(5))).toBe('Guten Morgen')
    expect(timeGreeting(at(10))).toBe('Guten Morgen')
  })
  it('tagsüber (11–17) → Guten Tag', () => {
    expect(timeGreeting(at(11))).toBe('Guten Tag')
    expect(timeGreeting(at(17))).toBe('Guten Tag')
  })
  it('abends/nachts (18–4) → Guten Abend', () => {
    expect(timeGreeting(at(18))).toBe('Guten Abend')
    expect(timeGreeting(at(23))).toBe('Guten Abend')
    expect(timeGreeting(at(0))).toBe('Guten Abend')
    expect(timeGreeting(at(4))).toBe('Guten Abend')
  })
})

describe('FALLBACK_NAME', () => {
  it('ist nicht leer', () => {
    expect(FALLBACK_NAME.trim().length).toBeGreaterThan(0)
  })
})
