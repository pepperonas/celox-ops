import type { OutreachCategory, OutreachChannel } from '../../types'

export const CHANNELS: { value: OutreachChannel; label: string; icon: string }[] = [
  { value: 'email', label: 'E-Mail', icon: '📧' },
  { value: 'linkedin', label: 'LinkedIn', icon: '💼' },
  { value: 'phone', label: 'Telefon', icon: '📞' },
]

export const CHANNEL_LABEL: Record<OutreachChannel, string> = {
  email: 'E-Mail',
  linkedin: 'LinkedIn',
  phone: 'Telefon',
}

// Reihenfolge = Anzeige-Reihenfolge der Rubriken.
export const CATEGORIES: { value: OutreachCategory; label: string }[] = [
  { value: 'kaltakquise', label: 'Kaltakquise' },
  { value: 'ki_automatisierung', label: 'KI-Automatisierung' },
  { value: 'security_audit', label: 'Security-Check / Audit' },
  { value: 'followup', label: 'Follow-up' },
  { value: 'reaktivierung', label: 'Reaktivierung' },
  { value: 'empfehlung', label: 'Empfehlung' },
  { value: 'angebot_nachfassen', label: 'Angebot nachfassen' },
  { value: 'security_upsell', label: 'Security-Upsell' },
]

export const CATEGORY_LABEL: Record<OutreachCategory, string> = Object.fromEntries(
  CATEGORIES.map((c) => [c.value, c.label]),
) as Record<OutreachCategory, string>

// Platzhalter-Katalog: Reihenfolge im Formular, Label + Beispiel, und ob er
// automatisch aus einem Rainmaker-Lead befüllt werden kann.
export interface PlaceholderMeta {
  key: string
  label: string
  example: string
  fromLead: boolean
}

export const PLACEHOLDERS: PlaceholderMeta[] = [
  { key: 'anrede', label: 'Anrede', example: 'Guten Tag / Hallo', fromLead: false },
  { key: 'name', label: 'Name', example: 'Frau Meier', fromLead: true },
  { key: 'firma', label: 'Firma', example: 'Muster Hausverwaltung GmbH', fromLead: true },
  { key: 'branche', label: 'Branche', example: 'Hausverwaltung', fromLead: true },
  { key: 'risiko_branche', label: 'Branchen-Risiko', example: 'ein Ausfall der Auftragsverwaltung', fromLead: false },
  { key: 'aufhaenger', label: 'Aufhänger', example: 'die offene Backup-Lücke', fromLead: false },
  { key: 'zielsystem', label: 'Zielsystem', example: 'DATEV / ERP', fromLead: false },
  { key: 'audit_preis', label: 'Audit-Preis', example: '1.490 €', fromLead: false },
  { key: 'audit_dauer', label: 'Audit-Dauer', example: '5 Werktage', fromLead: false },
]

export const PLACEHOLDER_LABEL: Record<string, string> = Object.fromEntries(
  PLACEHOLDERS.map((p) => [p.key, p.label]),
)

// Generische Tags, die keine Branche sind (für {{branche}}-Ableitung aus einem Lead).
const GENERIC_TAGS = new Set(['discovery', 'rainmaker', 'linkedin', 'ki-recherche', 'vorgemerkt'])
export function brancheFromTags(tags: string[] | null): string {
  return tags?.find((t) => !GENERIC_TAGS.has(t.trim().toLowerCase())) ?? ''
}
