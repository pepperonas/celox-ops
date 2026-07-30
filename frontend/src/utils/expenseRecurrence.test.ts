import { describe, expect, it } from 'vitest'
import {
  monthlyEquivalent,
  recurrenceLabel,
  yearlyEquivalent,
} from './expenseRecurrence'

describe('expenseRecurrence', () => {
  it('labels', () => {
    expect(recurrenceLabel(null)).toBe('')
    expect(recurrenceLabel('monthly')).toBe('monatlich')
    expect(recurrenceLabel('quadrennial')).toBe('4 Jahre')
  })

  it('monthly equivalent', () => {
    expect(monthlyEquivalent(11.99, 'monthly')).toBe(11.99)
    expect(monthlyEquivalent(120, 'yearly')).toBe(10)
    expect(monthlyEquivalent(10, null)).toBeNull()
  })

  it('yearly equivalent', () => {
    expect(yearlyEquivalent(10, 'monthly')).toBe(120)
    expect(yearlyEquivalent(48, 'quadrennial')).toBe(12)
  })
})
