import type { IconName } from '../../components/icons/catalog'
import type { OutreachCategory, OutreachChannel } from '../../types'

export const CHANNELS: { value: OutreachChannel; label: string }[] = [
  { value: 'email', label: 'E-Mail' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'phone', label: 'Telefon' },
]

/**
 * Grafik je Kanal — Umschlag, LinkedIn-Marke, Hörer.
 *
 * Totaler Record: Ein neuer Kanal ohne Grafik ist ein Compile-Fehler und kann
 * nicht stillschweigend ohne auskommen (gleiches Muster wie `CATEGORY_AXIS`).
 * `IconName` statt `string`, damit ein Tippfehler auffällt — `Icon` rendert bei
 * unbekanntem Namen `null`, der Fehler wäre also unsichtbar.
 *
 * Ersetzt das frühere `icon`-Feld auf `CHANNELS`: Das wurde nirgends gerendert,
 * trug für LinkedIn fälschlich `briefcase`, und der Test prüfte nur, dass
 * überhaupt eine Zeichenkette dastand.
 */
export const CHANNEL_ICON: Record<OutreachChannel, IconName> = {
  email: 'mail',
  linkedin: 'linkedin',
  phone: 'phone',
}

/**
 * Optischer Ausgleich für das Hintergrund-Wasserzeichen auf der Vorlagen-Karte.
 *
 * Gleiche Deckkraft heißt NICHT gleiche Wirkung: Gemessen an der Strichlänge im
 * 24er-Raster tragen die drei Zeichen unterschiedlich viel Farbe — LinkedIn 99,
 * Umschlag 85, Hörer 62 Einheiten. Das LinkedIn-Zeichen umschließt zusätzlich eine
 * Fläche und wirkt dadurch noch schwerer. Mit einem einheitlichen Wert wirkte es
 * aufdringlich und der Hörer blass (im Browser nebeneinander gesehen).
 *
 * Die Werte sind am Bild gewählt, nicht aus einer Formel — eine erfundene Formel
 * wäre nur ein Anstrich für dieselbe Augenentscheidung. Die Messung erklärt, WARUM
 * ein Ausgleich nötig ist; die Größe des Ausgleichs entscheidet der Blick.
 */
export const CHANNEL_WATERMARK_WEIGHT: Record<OutreachChannel, number> = {
  email: 1,
  linkedin: 0.78,
  phone: 1.2,
}

export const CHANNEL_LABEL: Record<OutreachChannel, string> = {
  email: 'E-Mail',
  linkedin: 'LinkedIn',
  phone: 'Telefon',
}

// Reihenfolge = Anzeige-Reihenfolge der Rubriken.
/**
 * Diese Reihenfolge IST die Anzeigereihenfolge — der Filterleiste (beide Reihen
 * filtern hieraus, s. CATEGORY_AXIS) und des Rubrik-Feldes im Vorlagen-Formular.
 * Nicht alphabetisch sortieren.
 *
 * Nach Achse gruppiert, damit man am Quelltext sieht, was wo erscheint. Bei den
 * Angeboten stehen die drei eigenen Produkte vorn — sie werden am häufigsten
 * gebraucht; die Dienstleistungsthemen folgen.
 */
export const CATEGORIES: { value: OutreachCategory; label: string }[] = [
  // Anlass — wann im Verkaufsprozess
  { value: 'kaltakquise', label: 'Kaltakquise' },
  { value: 'followup', label: 'Follow-up' },
  { value: 'reaktivierung', label: 'Reaktivierung' },
  { value: 'empfehlung', label: 'Empfehlung' },
  { value: 'angebot_nachfassen', label: 'Angebot nachfassen' },
  // Angebot — was verkauft wird: eigene Produkte zuerst
  { value: 'datenschutz_dsms', label: 'Datenschutz & DSB' },
  { value: 'portal_assessment', label: 'Assessments (Portal)' },
  { value: 'bcsbook_zeit', label: 'bcsbook (Zeiterfassung)' },
  { value: 'ki_automatisierung', label: 'KI-Automatisierung' },
  { value: 'security_audit', label: 'Security-Check / Audit' },
  { value: 'security_upsell', label: 'Security-Upsell' },
]

export const CATEGORY_LABEL: Record<OutreachCategory, string> = Object.fromEntries(
  CATEGORIES.map((c) => [c.value, c.label]),
) as Record<OutreachCategory, string>

/**
 * Gespeicherte Auswahl beim Laden prüfen — Stale-Guard.
 *
 * Kanal und Rubrik überleben einen Reload (localStorage). Ein Wert, den es nicht
 * mehr gibt — umbenannte Rubrik, entfernter Kanal, von Hand veränderter
 * Speicher — würde die Liste sonst dauerhaft leer filtern; der erste Eindruck
 * wäre „meine Vorlagen sind weg". Deshalb fällt Unbekanntes auf den Standard
 * zurück. Rein, damit es geprüft ist.
 */
export function restoreChannel(raw: string | null | undefined): OutreachChannel {
  return CHANNELS.some((c) => c.value === raw) ? (raw as OutreachChannel) : 'email'
}

export function restoreCategory(raw: string | null | undefined): string {
  if (raw === 'all') return 'all'
  return CATEGORIES.some((c) => c.value === raw) ? (raw as string) : 'all'
}

/**
 * Ist die Favoriten-Sektion aufgeklappt? **Standard: ja.**
 *
 * Nur ein ausdrückliches „0" klappt sie zu. Andersherum (nur „1" öffnet) wären
 * die Favoriten für jeden, der noch keinen Zustand gespeichert hat, beim ersten
 * Laden verschwunden — also für alle bisherigen Nutzer. Der Test hält diese
 * Richtung fest.
 */
export function restoreFavoritesOpen(raw: string | null | undefined): boolean {
  return raw !== '0'
}

/**
 * Zwei Achsen in einer Rubrikenliste: WANN im Verkaufsprozess (`anlass`) und WAS
 * verkauft wird (`angebot`). Vorher standen beide in einer Reihe — man musste
 * jedes Label lesen, um zu erkennen, welche Art Filter man anklickt.
 *
 * Bewusst nach Achse getrennt, NICHT nach „neu": eine Neuheiten-Ecke verfällt
 * mit dem vierten Produkt, und Security-Check/KI-Automatisierung sind längst
 * Angebote — sie stünden auf der falschen Seite. Unterscheidungstest: Sagt das
 * Label, WAS verkauft wird? Dann `angebot`.
 *
 * Der Record ist total — eine neue Rubrik ohne Achse ist ein Compile-Fehler und
 * kann damit nicht stillschweigend aus der Filterleiste fallen.
 */
export const CATEGORY_AXIS: Record<OutreachCategory, 'anlass' | 'angebot'> = {
  kaltakquise: 'anlass',
  followup: 'anlass',
  reaktivierung: 'anlass',
  empfehlung: 'anlass',
  angebot_nachfassen: 'anlass',
  ki_automatisierung: 'angebot',
  security_audit: 'angebot',
  security_upsell: 'angebot',
  datenschutz_dsms: 'angebot',
  portal_assessment: 'angebot',
  bcsbook_zeit: 'angebot',
}

/** Verkauft diese Rubrik ein konkretes Angebot? Steuert den Akzent-Ton in der
 *  Chip-Reihe UND die Rubrik-Pille auf der Karte — aus einer Quelle, damit die
 *  beiden nicht auseinanderlaufen. */
export const isOfferCategory = (c: OutreachCategory): boolean =>
  CATEGORY_AXIS[c] === 'angebot'

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
  // Mitarbeiterzahl: trägt die bcsbook-Rechnung (3.300 € pro Person und Jahr).
  // Kommt aus dem Lead (employee_count) — eine ROI-Aussage ohne die echte Zahl
  // ist eine Behauptung, mit ihr ein Angebot.
  { key: 'mitarbeiter', label: 'Mitarbeiterzahl', example: '50', fromLead: true },
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
