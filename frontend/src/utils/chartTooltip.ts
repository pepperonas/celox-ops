import { formatCurrency } from './formatters'

export interface RevenuePeriodRow {
  label: string
  revenue: number
  expenses: number
  invoice_count: number
  customer_name: string | null
  issued_count: number
}

/**
 * Tooltip-Zeile für das Umsatz-&-Ausgaben-Diagramm:
 * - Zähl-Balken („Rechnungen gestellt") → "Gestellt: N Rechnung(en)"
 * - Umsatz-Balken → Betrag + Herkunft: bei >1 Rechnung die Anzahl,
 *   bei genau 1 der Kundenname
 * - Ausgaben → nur Betrag
 */
export function revenueTooltipLabel(
  datasetLabel: string,
  datasetIndex: number,
  value: number,
  row: RevenuePeriodRow | undefined,
): string {
  if (datasetLabel === 'Rechnungen gestellt') {
    return `Gestellt: ${value} Rechnung${value === 1 ? '' : 'en'}`
  }
  let line = `${datasetLabel}: ${formatCurrency(value)}`
  if (datasetIndex === 0 && row) {
    if (row.invoice_count > 1) line += ` (aus ${row.invoice_count} Rechnungen)`
    else if (row.invoice_count === 1 && row.customer_name) line += ` (${row.customer_name})`
  }
  return line
}
