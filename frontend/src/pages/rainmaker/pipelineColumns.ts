// Reine Helfer für die Pipeline-Spalten (ohne DOM/React → unit-testbar).
// Trennt Datenaufbereitung von der Darstellung; hier hängt später auch
// serverseitige Pagination / Gruppierung an.
import type { RainmakerLead, RainmakerLeadStatus } from '../../types'

/** Anfangsmenge + Nachlade-Schritt je Spalte. */
export const PAGE_SIZE = 20

/**
 * Leads in EINEM Durchlauf nach Status gruppieren — statt pro Spalte einmal über
 * alle Leads zu filtern (bei 8 Spalten × n Leads = 8n Vergleiche pro Render).
 * Jeder bekannte Status ist im Ergebnis vorhanden (auch leer).
 */
export function groupByStatus(
  leads: RainmakerLead[], statuses: readonly RainmakerLeadStatus[],
): Record<string, RainmakerLead[]> {
  const out: Record<string, RainmakerLead[]> = {}
  for (const s of statuses) out[s] = []
  for (const l of leads) {
    const bucket = out[l.status]
    if (bucket) bucket.push(l)
  }
  return out
}

/** Wie viele Karten sind aktuell sichtbar (nie mehr als vorhanden). */
export function visibleCount(requested: number | undefined, total: number): number {
  return Math.min(requested ?? PAGE_SIZE, total)
}

/** Nächste Stufe beim Nachladen (auf `total` begrenzt). */
export function nextCount(current: number, total: number): number {
  return Math.min(current + PAGE_SIZE, total)
}

/** „20 von 351" — null, wenn alles sichtbar ist (dann kein Zusatztext nötig). */
export function countLabel(visible: number, total: number): string | null {
  return visible < total ? `${visible} von ${total}` : null
}
