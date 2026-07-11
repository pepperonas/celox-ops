import { describe, it, expect } from 'vitest'
import { revenueTooltipLabel, type RevenuePeriodRow } from './chartTooltip'

const row = (over: Partial<RevenuePeriodRow>): RevenuePeriodRow => ({
  label: 'Apr 26',
  revenue: 0,
  expenses: 0,
  invoice_count: 0,
  customer_name: null,
  issued_count: 0,
  ...over,
})

describe('revenueTooltipLabel', () => {
  it('zeigt bei mehreren Rechnungen die Anzahl', () => {
    const label = revenueTooltipLabel('Umsatz', 0, 590.94, row({ invoice_count: 2 }))
    expect(label).toContain('590,94')
    expect(label).toContain('(aus 2 Rechnungen)')
  })

  it('nennt bei genau einer Rechnung den Kunden', () => {
    const label = revenueTooltipLabel('Umsatz', 0, 493.27, row({ invoice_count: 1, customer_name: 'Lydia Bopf' }))
    expect(label).toContain('(Lydia Bopf)')
    expect(label).not.toContain('aus')
  })

  it('lässt den Zusatz weg, wenn keine Rechnung dahintersteckt', () => {
    const label = revenueTooltipLabel('Umsatz', 0, 0, row({ invoice_count: 0 }))
    expect(label).toBe(`Umsatz: ${label.split(': ')[1]}`)
    expect(label).not.toContain('(')
  })

  it('Zähl-Balken: Singular und Plural', () => {
    expect(revenueTooltipLabel('Rechnungen gestellt', 2, 1, row({}))).toBe('Gestellt: 1 Rechnung')
    expect(revenueTooltipLabel('Rechnungen gestellt', 2, 3, row({}))).toBe('Gestellt: 3 Rechnungen')
  })

  it('Ausgaben-Balken bekommt keinen Rechnungs-Zusatz', () => {
    const label = revenueTooltipLabel('Ausgaben', 1, 40, row({ invoice_count: 2 }))
    expect(label).not.toContain('aus')
  })
})
