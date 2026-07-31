/** Cash-/EÜR-Helfer für Ausgaben (Spiegel zu backend expense_payment). */

export function normalizePayment(input: {
  paid: boolean
  paid_at: string | null | undefined
  expense_date: string | null | undefined
}): { paid: boolean; paid_at: string | null } {
  if (!input.paid) return { paid: false, paid_at: null }
  return { paid: true, paid_at: input.paid_at || input.expense_date || null }
}

/** Datum für Steuer/EÜR — nur bei bezahlt. */
export function cashDate(input: {
  paid: boolean
  paid_at: string | null | undefined
  expense_date: string | null | undefined
}): string | null {
  if (!input.paid) return null
  return input.paid_at || input.expense_date || null
}

export function countsInTaxYear(
  input: {
    paid: boolean
    paid_at: string | null | undefined
    expense_date: string | null | undefined
  },
  year: number,
): boolean {
  const d = cashDate(input)
  if (!d) return false
  return Number(d.slice(0, 4)) === year
}

/** Kategorie aus Vorschlags-Map (exakt, sonst case-insensitiv). */
export function categoryFromDescriptionMap(
  description: string,
  categories: Record<string, string>,
): string | undefined {
  if (description in categories) return categories[description]
  const folded = description.toLowerCase()
  for (const [key, value] of Object.entries(categories)) {
    if (key.toLowerCase() === folded) return value
  }
  return undefined
}
