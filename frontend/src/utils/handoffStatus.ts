// Reine Anzeige-Logik für den Handoff-Status (Kontrakt §6.4) — testbar ohne DOM.

export interface HandoffTargetStatus {
  target_id?: string
  external_ref_confirmed?: boolean
  last_handoff_at?: string
  last_status?: string // "created" | "updated" | "error:<code>"
  handoff_id?: string
}

export type HandoffTone = 'ok' | 'error' | 'none'

export function statusTone(status: HandoffTargetStatus | null | undefined): HandoffTone {
  if (!status?.last_status) return 'none'
  return status.last_status.startsWith('error:') ? 'error' : 'ok'
}

function formatDateTime(iso: string | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
    ' ' + d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

export function statusLabel(status: HandoffTargetStatus | null | undefined): string {
  if (!status?.last_status) return 'Noch nicht übergeben'
  const when = formatDateTime(status.last_handoff_at)
  const at = when ? ` am ${when}` : ''
  if (status.last_status === 'created') return `Übergeben${at} — im Ziel neu angelegt`
  if (status.last_status === 'updated') return `Erneut übergeben${at} — im Ziel angereichert`
  if (status.last_status.startsWith('error:')) {
    const code = status.last_status.slice('error:'.length)
    return `Fehler (${code})${at} — erneut versuchen möglich`
  }
  return `${status.last_status}${at}`
}

export function buttonLabel(status: HandoffTargetStatus | null | undefined): string {
  return statusTone(status) === 'ok' ? 'Erneut übergeben' : 'Übergeben'
}
