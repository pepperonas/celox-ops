import { formatCurrency } from './formatters'

export interface RevenuePeriodRow {
  label: string
  revenue: number
  expenses: number
  invoice_count: number
  customer_name: string | null
  issued_count: number
  paid_count: number
  open_count: number
  draft_count: number
}

/** "1 bezahlt · 1 gestellt · 3 Entwürfe" — nur nicht-leere Kategorien. */
function breakdown(row: RevenuePeriodRow): string[] {
  const parts: string[] = []
  if (row.paid_count > 0) parts.push(`${row.paid_count} bezahlt`)
  if (row.open_count > 0) parts.push(`${row.open_count} gestellt`)
  if (row.draft_count > 0) parts.push(row.draft_count === 1 ? '1 Entwurf' : `${row.draft_count} Entwürfe`)
  return parts
}

/**
 * Tooltip-Zeile für das Umsatz-&-Ausgaben-Diagramm:
 * - Zähl-Balken („Rechnungen gestellt") → "Gestellt: N Rechnung(en)"
 * - Umsatz-Balken → Betrag + Herkunft: bei >1 Rechnung die Anzahl plus
 *   Status-Aufschlüsselung (wenn gemischt), bei genau 1 der Kundenname
 *   (plus Status, wenn nicht bezahlt)
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
    const parts = breakdown(row)
    if (row.invoice_count > 1) {
      line += parts.length > 1
        ? ` (aus ${row.invoice_count} Rechnungen: ${parts.join(' · ')})`
        : ` (aus ${row.invoice_count} Rechnungen)`
    } else if (row.invoice_count === 1 && row.customer_name) {
      const status = row.draft_count === 1 ? ' · Entwurf' : row.open_count === 1 ? ' · gestellt' : ''
      line += ` (${row.customer_name}${status})`
    }
  }
  return line
}
