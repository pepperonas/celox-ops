// Statischer portal-Produktkatalog für die Entitlement-Auswahl im Handoff-Dialog.
// Quelle: celox-portal server/content (PRODUCTS) — Stand 2026-07-19.
// Bewusst statisch (Phase-2-Entscheidung): neue portal-Module hier nachziehen;
// unbekannte Keys fängt die 422-Validierung des portals ab (Kontrakt §4.1).

export interface PortalProduct {
  key: string // Entitlement-Key, z. B. "audit:dsgvo" / "training:security"
  label: string
  kind: 'audit' | 'training'
}

export const PORTAL_PRODUCTS: PortalProduct[] = [
  { key: 'audit:it-sicherheit', label: 'IT-Sicherheits-Audit', kind: 'audit' },
  { key: 'audit:dsgvo', label: 'DSGVO-Compliance-Audit', kind: 'audit' },
  { key: 'audit:phishing', label: 'Phishing- & Social-Engineering-Audit', kind: 'audit' },
  { key: 'audit:ki-reifegrad', label: 'KI-Reifegrad-Audit', kind: 'audit' },
  { key: 'audit:ransomware', label: 'Ransomware-Resilienz-Audit', kind: 'audit' },
  { key: 'audit:ai-act-compliance', label: 'KI-Verordnung (AI Act) — Compliance-Audit', kind: 'audit' },
  { key: 'training:security', label: 'Cyber-Security-Schulung', kind: 'training' },
  { key: 'training:datenschutz', label: 'Datenschutz im Arbeitsalltag', kind: 'training' },
  { key: 'training:ki-nutzung', label: 'KI sicher nutzen & KI-Verordnung im Betrieb', kind: 'training' },
  { key: 'training:homeoffice', label: 'Sicher im Home-Office & unterwegs', kind: 'training' },
  { key: 'training:passwoerter', label: 'Passwörter & 2FA kompakt', kind: 'training' },
  { key: 'training:ransomware', label: 'Ransomware: erkennen, verhindern, überstehen', kind: 'training' },
  { key: 'training:bar-sicherheit', label: 'Sicherheit im Bar- & Clubbetrieb', kind: 'training' },
  { key: 'training:bar-betreiber', label: 'Betreiber-Schutz: Bar & Club sicher führen', kind: 'training' },
  { key: 'training:arztpraxis', label: 'Datenschutz & IT-Sicherheit in der Arztpraxis', kind: 'training' },
  { key: 'training:kanzlei', label: 'Informationssicherheit in der Kanzlei', kind: 'training' },
  { key: 'training:einzelhandel', label: 'Sicherheit im Einzelhandel', kind: 'training' },
  { key: 'training:hotel', label: 'Sicherheit in Hotel & Ferienunterkunft', kind: 'training' },
  { key: 'training:pflege', label: 'Datenschutz & Sicherheit im Pflegedienst', kind: 'training' },
  { key: 'training:immobilien', label: 'Datenschutz & Betrugsschutz in der Immobilienbranche', kind: 'training' },
  { key: 'training:fuehrung', label: 'Chefsache Sicherheit: Awareness & Haftung für die Führung', kind: 'training' },
  { key: 'training:advanced-angriffsvektoren', label: 'Angriffsvektoren, mit denen kaum ein Entwickler rechnet', kind: 'training' },
]
