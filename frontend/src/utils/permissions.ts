// Rollen-Rechte im Frontend. Die verbindliche Sperre sitzt serverseitig
// (backend/app/middleware/permissions.py) — das hier blendet nur aus, was
// ohnehin abgelehnt würde, damit niemand ins Leere klickt.

/** Rollen ohne destruktive Rechte (kein Löschen, kein Zusammenführen). */
const NON_DESTRUCTIVE = new Set(['mitarbeiter'])

export function canDelete(role: string | null | undefined): boolean {
  return !NON_DESTRUCTIVE.has((role || '').trim())
}
