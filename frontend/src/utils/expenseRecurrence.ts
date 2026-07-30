/** Ausgaben-Turnus: Labels und Monats-/Jahresäquivalente (Frontend-Spiegel). */

export type ExpenseRecurrence =
  | 'weekly'
  | 'biweekly'
  | 'monthly'
  | 'quarterly'
  | 'semiannual'
  | 'yearly'
  | 'biennial'
  | 'quadrennial'

export const RECURRENCE_OPTIONS: { value: ExpenseRecurrence; label: string }[] = [
  { value: 'weekly', label: 'wöchentlich' },
  { value: 'biweekly', label: '2 Wochen' },
  { value: 'monthly', label: 'monatlich' },
  { value: 'quarterly', label: 'quartalsweise' },
  { value: 'semiannual', label: 'halbjährlich' },
  { value: 'yearly', label: 'jährlich' },
  { value: 'biennial', label: '2 Jahre' },
  { value: 'quadrennial', label: '4 Jahre' },
]

const MONTHS: Record<ExpenseRecurrence, number> = {
  weekly: 12 / 52,
  biweekly: 12 / 26,
  monthly: 1,
  quarterly: 3,
  semiannual: 6,
  yearly: 12,
  biennial: 24,
  quadrennial: 48,
}

export function recurrenceLabel(value: ExpenseRecurrence | null | undefined): string {
  if (!value) return ''
  return RECURRENCE_OPTIONS.find((o) => o.value === value)?.label ?? value
}

function money(n: number): number {
  return Math.round(n * 100) / 100
}

export function monthlyEquivalent(
  amount: number,
  recurrence: ExpenseRecurrence | null | undefined,
): number | null {
  if (!recurrence) return null
  const months = MONTHS[recurrence]
  if (!months) return null
  return money(amount / months)
}

export function yearlyEquivalent(
  amount: number,
  recurrence: ExpenseRecurrence | null | undefined,
): number | null {
  const m = monthlyEquivalent(amount, recurrence)
  return m == null ? null : money(m * 12)
}
