import { describe, it, expect } from 'vitest'
import { formatCurrency, formatDate, formatDateTime, formatRelativeTime } from './formatters'

describe('formatCurrency', () => {
  it('formats EUR in German style', () => {
    const s = formatCurrency(1234.5)
    expect(s).toContain('1.234,50')
    expect(s).toContain('€')
  })
  it('formats zero', () => {
    expect(formatCurrency(0)).toContain('0,00')
  })
  it('formats negatives', () => {
    expect(formatCurrency(-99.9)).toContain('99,90')
  })
})

describe('formatDate', () => {
  it('formats an ISO date as dd.mm.yyyy', () => {
    const s = formatDate('2026-06-17T12:00:00Z')
    expect(s).toMatch(/^\d{2}\.\d{2}\.\d{4}$/)
    expect(s).toContain('2026')
  })
  it('returns a dash for empty values', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate(undefined)).toBe('—')
    expect(formatDate('')).toBe('—')
  })
})

describe('formatDateTime', () => {
  it('includes a time component', () => {
    const s = formatDateTime('2026-06-17T08:30:00Z')
    expect(s).toContain('2026')
    expect(s).toMatch(/\d{2}:\d{2}/)
  })
  it('returns a dash for empty', () => {
    expect(formatDateTime(null)).toBe('—')
  })
})

describe('formatRelativeTime', () => {
  const ago = (ms: number) => new Date(Date.now() - ms).toISOString()
  it('says "gerade eben" for <1 min', () => {
    expect(formatRelativeTime(ago(30_000))).toBe('gerade eben')
  })
  it('uses singular for exactly 1 minute', () => {
    expect(formatRelativeTime(ago(60_000))).toBe('vor 1 Minute')
  })
  it('uses plural for several minutes', () => {
    expect(formatRelativeTime(ago(5 * 60_000))).toBe('vor 5 Minuten')
  })
  it('reports hours', () => {
    expect(formatRelativeTime(ago(2 * 3600_000))).toBe('vor 2 Stunden')
  })
  it('reports days', () => {
    expect(formatRelativeTime(ago(3 * 86400_000))).toBe('vor 3 Tagen')
  })
  it('falls back to a date for >7 days', () => {
    expect(formatRelativeTime(ago(10 * 86400_000))).toMatch(/^\d{2}\.\d{2}\.\d{4}$/)
  })
  it('returns a dash for empty', () => {
    expect(formatRelativeTime(null)).toBe('—')
  })
})
