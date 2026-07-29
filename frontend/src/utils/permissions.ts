// Rollen-Rechte im Frontend. Die verbindliche Sperre sitzt serverseitig
// (backend/app/middleware/permissions.py + role_scope.py) — das hier blendet nur
// aus, was ohnehin abgelehnt würde, damit niemand ins Leere klickt.

/** Rollen ohne destruktive Rechte (kein Löschen, kein Zusammenführen). */
const NON_DESTRUCTIVE = new Set(['mitarbeiter'])

/**
 * Rollen mit zugeschnittenem Zugriff (Erlaubnisliste statt Verbotsliste).
 * Muss zu `RULES` in backend/app/middleware/role_scope.py passen.
 */
const SCOPED = new Set(['verkaeufer'])

/**
 * Welche Nav-Pfade sieht eine zugeschnittene Rolle? `null` = keine Einschränkung.
 *
 * Bewusst eine Erlaubnisliste: Käme eine neue Seite hinzu, wäre sie für die
 * eingeschränkte Rolle im Zweifel unsichtbar statt versehentlich sichtbar — und
 * ein Klick darauf endete ohnehin im serverseitigen 403.
 */
const SCOPED_NAV: Record<string, string[]> = {
  // Einstellungen sind dabei, damit ein Verkäufer sein Passwort und 2FA
  // verwalten kann; die Seite zeigt ihm nur diesen Konto-Teil (Settings.tsx).
  verkaeufer: ['/pipeline', '/akquise', '/einstellungen'],
}

export function canDelete(role: string | null | undefined): boolean {
  return !NON_DESTRUCTIVE.has((role || '').trim())
}

/** Unterliegt diese Rolle einer Erlaubnisliste? */
export function isScopedRole(role: string | null | undefined): boolean {
  return SCOPED.has((role || '').trim())
}

/** Erlaubte Nav-Pfade oder `null`, wenn die Rolle alles sehen darf. */
export function navPathsForRole(role: string | null | undefined): string[] | null {
  return SCOPED_NAV[(role || '').trim()] ?? null
}

/**
 * Darf diese Rolle Papierkorb und Änderungsprotokoll verwalten — also
 * Löschungen zurückholen und Änderungen zurücknehmen?
 *
 * Nur der Bereichs-Inhaber. Die Aufsicht über die Arbeit eines Verkäufers darf
 * nicht bei ihm selbst liegen, sonst wäre der Papierkorb kein Sicherheitsnetz,
 * sondern ein Zwischenschritt beim Löschen. Spiegelt `may_administer_leads`.
 */
export function canAdministerLeads(role: string | null | undefined): boolean {
  const r = (role || '').trim()
  return r === 'admin' || r === 'user'
}

/** Darf diese Rolle Akquise-Vorlagen anlegen/ändern/löschen? Verkäufer: nur lesen. */
export function canEditOutreachTemplates(role: string | null | undefined): boolean {
  return !isScopedRole(role)
}

/** Darf diese Rolle E-Mails aus der App versenden? */
export function canSendEmail(role: string | null | undefined): boolean {
  return !isScopedRole(role)
}

/**
 * Darf diese Rolle kostenpflichtige KI-Funktionen auslösen (Entwurf, Recherche,
 * Tiefenanalyse, Erfassung aus Material)? Sie laufen auf das Budget des
 * Bereichs-Inhabers — deshalb nur er selbst.
 */
export function canUsePaidAi(role: string | null | undefined): boolean {
  return !isScopedRole(role)
}
