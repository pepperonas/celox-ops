// Darstellung eines Änderungssatzes — rein, damit die Anzeige testbar bleibt.

/** Feldnamen aus dem Protokoll in Klartext. Muss zu TRACKED_FIELDS im Backend
 *  passen (services/lead_supervision.py); fehlt ein Eintrag, zeigt die UI den
 *  technischen Namen — unschön, aber nie leer. */
export const FIELD_LABELS: Record<string, string> = {
  company: 'Firma',
  contact_name: 'Ansprechpartner',
  role: 'Funktion',
  email: 'E-Mail',
  phone: 'Telefon',
  website: 'Website',
  source: 'Quelle',
  status: 'Status',
  priority: 'Priorität',
  target: 'Target',
  notes: 'Notizen',
  tags: 'Tags',
  employee_count: 'Mitarbeiterzahl',
  decision_maker: 'Entscheider',
  value_estimate: 'Wert',
  pinned: 'Favorit',
}

const ACTIONS: Record<string, string> = {
  update: 'geändert',
  delete: 'in den Papierkorb',
  restore: 'zurückgeholt',
  create: 'angelegt',
}

export function actionLabel(action: string): string {
  return ACTIONS[action] || action
}

/** Ein Wert als kurze, lesbare Zeichenkette. */
export function formatValue(value: unknown, maxLen = 60): string {
  if (value === null || value === undefined || value === '') return '(leer)'
  if (typeof value === 'boolean') return value ? 'ja' : 'nein'
  if (Array.isArray(value)) return value.length ? value.join(', ') : '(leer)'
  const s = String(value)
  return s.length > maxLen ? `${s.slice(0, maxLen)}…` : s
}

export interface ChangeLine {
  field: string
  label: string
  from: string
  to: string
}

/** Änderungs-Objekt → anzeigbare Zeilen, stabil sortiert (sonst springt die
 *  Reihenfolge zwischen zwei Ladevorgängen, weil JSON-Schlüssel unsortiert sind). */
export function changeSummary(
  changes: Record<string, { old: unknown; new: unknown }> | null | undefined,
): ChangeLine[] {
  if (!changes) return []
  return Object.keys(changes)
    .sort()
    .map((field) => ({
      field,
      label: FIELD_LABELS[field] || field,
      from: formatValue(changes[field]?.old),
      to: formatValue(changes[field]?.new),
    }))
}
