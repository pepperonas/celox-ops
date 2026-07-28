/**
 * Herkunft einer Abo→Domain-Zuordnung als Anzeigetext.
 *
 * Die Hostinger-API verknüpft ein Domain-Abo nicht mit einer Domain (siehe
 * `backend/app/services/hostinger.py`). Die Zuordnung wird aus der
 * Bestellreihenfolge abgeleitet — das muss in der Oberfläche sichtbar sein,
 * sonst hält man einen abgeleiteten Namen für eine Auskunft der API.
 *
 * Reine Funktion, damit die Formulierungen testbar sind.
 */
export type DomainConfidence = 'confirmed' | 'same_order' | 'sequence' | 'unmatched'

export interface DomainHint {
  /** Kurzzeichen in der Tabelle. */
  mark: string
  /** Farbklasse (Tailwind-Semantik aus den Tokens). */
  tone: 'ok' | 'warn' | 'muted'
  /** Tooltip mit der Begründung. */
  title: string
  /** Braucht diese Zeile einen Blick? */
  check: boolean
}

/** Sekunden → lesbare Dauer (spiegelt `_ago` im Backend). */
export function humanGap(seconds: number | null | undefined): string {
  if (seconds == null) return 'unbekannter Abstand'
  if (seconds < 90) return `${seconds} s`
  if (seconds < 5400) return `${Math.round(seconds / 60)} min`
  if (seconds < 172800) return `${Math.round(seconds / 3600)} h`
  return `${Math.round(seconds / 86400)} Tage`
}

export function domainHint(
  confidence: DomainConfidence | null | undefined,
  gapSeconds: number | null | undefined,
): DomainHint {
  switch (confidence) {
    case 'confirmed':
      return { mark: '✓', tone: 'ok', check: false,
        title: 'Zuordnung von dir bestätigt.' }
    case 'same_order':
      return { mark: '≈', tone: 'ok', check: false,
        title: `Abgeleitet: Domain ${humanGap(gapSeconds)} nach dem Abo registriert `
             + '— dieselbe Bestellung.' }
    case 'sequence':
      return { mark: '?', tone: 'warn', check: true,
        title: `Nur über die Reihenfolge abgeleitet (Abstand ${humanGap(gapSeconds)}). `
             + 'Bitte prüfen und bei Bedarf korrigieren.' }
    default:
      return { mark: '—', tone: 'muted', check: true,
        title: 'Keine Domain zuordenbar — bitte auswählen.' }
  }
}

/** Beschreibung ohne den Domainnamen, damit die Tabelle ihn separat zeigen kann. */
export function shortDescription(description: string, domain: string | null): string {
  if (!domain) return description
  return description.replace(`Domain ${domain} `, 'Domain ')
}
