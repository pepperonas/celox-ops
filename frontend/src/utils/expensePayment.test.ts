import { describe, expect, it } from 'vitest'
import {
  cashDate,
  categoryFromDescriptionMap,
  countsInTaxYear,
  normalizePayment,
} from './expensePayment'
import {
  monthlyEquivalent,
  recurrenceLabel,
  yearlyEquivalent,
  RECURRENCE_OPTIONS,
} from './expenseRecurrence'

describe('normalizePayment', () => {
  it('clears paid_at when unpaid', () => {
    expect(normalizePayment({
      paid: false, paid_at: '2026-01-05', expense_date: '2026-01-01',
    })).toEqual({ paid: false, paid_at: null })
  })

  it('falls back to expense_date when paid without paid_at', () => {
    expect(normalizePayment({
      paid: true, paid_at: null, expense_date: '2026-03-15',
    })).toEqual({ paid: true, paid_at: '2026-03-15' })
  })

  it('keeps explicit paid_at', () => {
    expect(normalizePayment({
      paid: true, paid_at: '2026-04-01', expense_date: '2026-03-01',
    })).toEqual({ paid: true, paid_at: '2026-04-01' })
  })

  it('allows paid with neither date', () => {
    expect(normalizePayment({
      paid: true, paid_at: null, expense_date: null,
    })).toEqual({ paid: true, paid_at: null })
  })
})

describe('cashDate / tax year', () => {
  it('returns null for unpaid', () => {
    expect(cashDate({
      paid: false, paid_at: '2026-05-01', expense_date: '2026-01-01',
    })).toBeNull()
  })

  it('prefers paid_at over expense_date', () => {
    expect(cashDate({
      paid: true, paid_at: '2026-05-10', expense_date: '2026-01-01',
    })).toBe('2026-05-10')
  })

  it('counts cash year, not booking year', () => {
    const row = {
      paid: true as const,
      paid_at: '2025-12-28',
      expense_date: '2026-01-02',
    }
    expect(countsInTaxYear(row, 2025)).toBe(true)
    expect(countsInTaxYear(row, 2026)).toBe(false)
  })

  it('excludes open expenses from tax year', () => {
    expect(countsInTaxYear({
      paid: false, paid_at: null, expense_date: '2026-06-15',
    }, 2026)).toBe(false)
  })

  it('uses expense_date when paid_at missing', () => {
    expect(countsInTaxYear({
      paid: true, paid_at: null, expense_date: '2026-07-01',
    }, 2026)).toBe(true)
  })
})

describe('categoryFromDescriptionMap', () => {
  const map = {
    'Hetzner Cloud VPS': 'hosting',
    'Anthropic API Credits': 'ki_api',
  }

  it('exact match', () => {
    expect(categoryFromDescriptionMap('Hetzner Cloud VPS', map)).toBe('hosting')
  })

  it('case-insensitive match', () => {
    expect(categoryFromDescriptionMap('anthropic api credits', map)).toBe('ki_api')
  })

  it('unknown stays undefined', () => {
    expect(categoryFromDescriptionMap('Freitext XYZ', map)).toBeUndefined()
  })
})

describe('expenseRecurrence extended', () => {
  it('every option has a label', () => {
    for (const o of RECURRENCE_OPTIONS) {
      expect(recurrenceLabel(o.value)).toBe(o.label)
    }
  })

  it('weekly and biweekly monthly equivalents', () => {
    const weekly = monthlyEquivalent(52, 'weekly')!
    const biweekly = monthlyEquivalent(26, 'biweekly')!
    expect(weekly).toBeCloseTo(52 / (12 / 52), 2)
    expect(biweekly).toBeCloseTo(26 / (12 / 26), 2)
  })

  it('quarterly / semiannual / biennial', () => {
    expect(monthlyEquivalent(30, 'quarterly')).toBe(10)
    expect(yearlyEquivalent(30, 'quarterly')).toBe(120)
    expect(monthlyEquivalent(60, 'semiannual')).toBe(10)
    expect(yearlyEquivalent(24, 'biennial')).toBe(12)
  })

  it('unknown recurrence string is empty label', () => {
    expect(recurrenceLabel(undefined)).toBe('')
    expect(monthlyEquivalent(10, undefined)).toBeNull()
  })
})
