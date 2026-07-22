// Reine Sortierlogik für das Pipeline-Board (ohne DOM, damit testbar).
import type { RainmakerLead } from '../../types'

export type LeadSort = 'default' | 'employees_desc' | 'employees_asc' | 'region'

export const LEAD_SORT_OPTIONS: { value: LeadSort; label: string }[] = [
  { value: 'default', label: 'Standard' },
  { value: 'employees_desc', label: 'Mitarbeiter: viele zuerst' },
  { value: 'employees_asc', label: 'Mitarbeiter: wenige zuerst' },
  { value: 'region', label: 'Region (PLZ)' },
]

/** 5-stellige PLZ aus dem Freitext-Adressfeld (oder null). Treibt die
 *  Regions-Sortierung: aufsteigend gruppiert die PLZ-Leitzonen (0 = Ost/Sachsen
 *  … 8 = Südbayern, 9 = Franken) geografisch. */
export function regionKey(address: string | null | undefined): string | null {
  if (!address) return null
  const m = address.match(/\b(\d{5})\b/)
  return m ? m[1] : null
}

/** „PLZ Ort" fürs Karten-Label beim Region-Sortieren (oder null). */
export function cityLabel(address: string | null | undefined): string | null {
  if (!address) return null
  const m = address.match(/\b(\d{5})\s+([^,]+)/)
  if (m) return `${m[1]} ${m[2].trim()}`
  const last = address.split(',').pop()?.trim()
  return last || null
}

/**
 * Sortiert eine Spalte: gepinnte immer oben, darunter nach dem gewählten Modus.
 * „Leer"-Werte (keine Mitarbeiterzahl / keine PLZ) landen ans Ende, egal in
 * welche Richtung sortiert wird. `default` behält die eingehende Reihenfolge
 * (nur pinned-first) — stabil.
 */
export function sortColumn(leads: RainmakerLead[], mode: LeadSort): RainmakerLead[] {
  const withIndex = leads.map((lead, i) => ({ lead, i }))

  const cmp = (a: { lead: RainmakerLead; i: number }, b: { lead: RainmakerLead; i: number }): number => {
    // Gepinnte immer zuerst.
    const pin = Number(b.lead.pinned) - Number(a.lead.pinned)
    if (pin !== 0) return pin

    if (mode === 'employees_desc' || mode === 'employees_asc') {
      const av = a.lead.employee_count
      const bv = b.lead.employee_count
      if (av == null && bv == null) return a.i - b.i
      if (av == null) return 1            // leer ans Ende
      if (bv == null) return -1
      if (av !== bv) return mode === 'employees_desc' ? bv - av : av - bv
      return a.i - b.i
    }

    if (mode === 'region') {
      const ak = regionKey(a.lead.address)
      const bk = regionKey(b.lead.address)
      if (!ak && !bk) return a.i - b.i
      if (!ak) return 1
      if (!bk) return -1
      if (ak !== bk) return ak < bk ? -1 : 1
      return a.i - b.i
    }

    return a.i - b.i                       // default: stabil
  }

  return withIndex.sort(cmp).map((x) => x.lead)
}
