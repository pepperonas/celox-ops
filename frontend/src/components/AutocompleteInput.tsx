import { useState, useRef, useEffect } from 'react'

const IT_SUGGESTIONS = [
  // Website (wertorientiert)
  'Website-Erstellung & Einrichtung',
  'Website-Redesign & Optimierung',
  'Website-Relaunch & Modernisierung',
  'Website-Erstellung (WordPress)',
  'Website-Erstellung (React)',
  'Website-Pflege & Aktualisierung',
  'Performance- & Ladezeit-Optimierung',
  'Website-Migration & Relaunch',
  'Landing Page mit Conversion-Optimierung',
  'Responsive Anpassung & Mobile-Optimierung',
  'Barrierefreiheit & Accessibility-Optimierung',
  // SEO
  'SEO-Optimierung',
  'SEO-Grundoptimierung',
  'SEO-Analyse und Beratung',
  'SEO-Audit',
  'Google Search Console Einrichtung',
  // Hosting & Domain
  'Hosting-Einrichtung',
  'Hosting-Migration',
  'Domain-Einrichtung',
  'SSL-Zertifikat Einrichtung',
  'Server-Konfiguration',
  'E-Mail-Einrichtung',
  // Entwicklung
  'Webentwicklung',
  'Frontend-Entwicklung',
  'Backend-Entwicklung',
  'Fullstack-Entwicklung',
  'App-Entwicklung',
  'API-Entwicklung',
  'Datenbankentwicklung',
  'Plugin-Entwicklung',
  'Schnittstellenentwicklung',
  'Softwareentwicklung',
  // Beratung
  'IT-Beratung',
  'Technische Beratung',
  'Digitalisierungsberatung',
  'Prozessoptimierung',
  'Systemarchitektur-Beratung',
  // Wartung & Support
  'Technischer Support',
  'Wartungsvertrag',
  'Fehlerbehebung',
  'Bugfix',
  'Sicherheitsupdate',
  'Performance-Optimierung',
  'Ladezeit-Optimierung',
  'Backup-Einrichtung',
  // Content & Design
  'Content-Einpflege',
  'Content-Erstellung',
  'Bildbearbeitung',
  'Logo-Erstellung',
  'Corporate Design',
  'UI/UX Design',
  'Grafikdesign',
  // Security
  'Sicherheitscheck',
  'Sicherheitsaudit',
  'Penetrationstest',
  'DSGVO-Beratung',
  'Datenschutzanpassung',
  'Cookie-Banner Einrichtung',
  // Sonstige
  'Schulung',
  'Workshop',
  'Projektmanagement',
  'Code-Review',
  'Datenübernahme',
  'KI-Integration',
  'KI-gestützte Entwicklung',
  'Automatisierung',
  'Monitoring-Einrichtung',
  'Analytics-Einrichtung',
  'Google Analytics Setup',
  'Social Media Integration',
]

export const POSITION_SUGGESTIONS = [
  // Website — Konzeption & Design
  'Konzeption und Wireframing',
  'UI/UX Design und Prototyping',
  'Webdesign (Startseite + Unterseiten)',
  'Responsive Design (Mobile/Tablet/Desktop)',
  'Design-Abstimmung und Revisionen',
  'Erstellung Designvorlage / Mockup',
  // Website — Entwicklung
  'Technische Umsetzung (HTML/CSS/JS)',
  'Frontend-Entwicklung (React)',
  'Frontend-Entwicklung (Next.js)',
  'Backend-Entwicklung (Node.js)',
  'Backend-Entwicklung (Python/FastAPI)',
  'WordPress-Theme-Entwicklung',
  'WordPress-Plugin-Anpassung',
  'CMS-Einrichtung und Konfiguration',
  'Datenbankmodellierung und -einrichtung',
  'API-Entwicklung und Integration',
  'Formularentwicklung mit Validierung',
  'Kontaktformular mit E-Mail-Versand',
  'Buchungssystem-Integration',
  'Zahlungsintegration (Stripe/PayPal)',
  // Content & SEO
  'Content-Einpflege und Formatierung',
  'Bildbearbeitung und -optimierung',
  'Texterstellung und -überarbeitung',
  'SEO-Grundoptimierung (Meta-Tags, Sitemap, robots.txt)',
  'SEO-Analyse und Keyword-Recherche',
  'Google Search Console Einrichtung',
  'Google Analytics / Tag Manager Setup',
  'Strukturierte Daten (Schema.org)',
  // Hosting & Infrastruktur
  'Server-Einrichtung und Konfiguration',
  'Hosting-Migration (inkl. DNS)',
  'SSL-Zertifikat Einrichtung',
  'Domain-Einrichtung und DNS-Konfiguration',
  'E-Mail-Einrichtung (IMAP/SMTP)',
  'Backup-System einrichten',
  'CDN-Konfiguration',
  'Docker-Setup und Deployment',
  'CI/CD Pipeline einrichten',
  'Monitoring und Alerting einrichten',
  // Performance & Sicherheit
  'Performance-Optimierung (Ladezeit)',
  'Bildkomprimierung und Lazy Loading',
  'Caching-Konfiguration',
  'Sicherheitsaudit und Härtung',
  'DSGVO-Anpassung (Cookie-Banner, Datenschutz)',
  'Impressum und Datenschutzerklärung',
  'Sicherheitsupdates einspielen',
  'Malware-Bereinigung',
  'Firewall-Konfiguration',
  // Wartung & Support
  'Monatliche Wartung und Updates',
  'CMS-Updates (Core + Plugins)',
  'Fehlerbehebung / Bugfix',
  'Technischer Support (Remote)',
  'Einweisung / Schulung CMS-Bedienung',
  'Dokumentation der technischen Umsetzung',
  // App & Software
  'App-Konzeption und Planung',
  'Mobile App Entwicklung',
  'Progressive Web App (PWA)',
  'Desktop-Anwendung',
  'Datenbank-Migration',
  'Schnittstellen-Entwicklung (REST/GraphQL)',
  'Automatisierung von Geschäftsprozessen',
  // Beratung
  'Technische Beratung (Erstgespräch)',
  'Anforderungsanalyse',
  'Architektur-Konzeption',
  'Digitalisierungsberatung',
  'Code-Review und Qualitätssicherung',
  'Projektmanagement und Koordination',
  // KI
  'KI-gestützte Entwicklung',
  'KI-API-Kosten',
  'KI-Integration und Konfiguration',
  'Chatbot-Einrichtung',
  'Automatisierung mit KI-Werkzeugen',
  // Vor-Ort / Remote-Support am Kundenrechner
  'Vor-Ort-Service beim Kunden',
  'Remote-Support (TeamViewer/AnyDesk)',
  'Einrichtung Arbeitsplatzrechner',
  'Einrichtung Notebook / Laptop',
  'Windows-Installation und Grundkonfiguration',
  'macOS-Installation und Grundkonfiguration',
  'Windows-Updates einspielen',
  'macOS-Updates einspielen',
  'Treiber-Installation und -Update',
  'Datenmigration auf neuen Rechner',
  'Druckereinrichtung (lokal/Netzwerk)',
  'WLAN-/Netzwerk-Einrichtung',
  'VPN-Einrichtung und Konfiguration',
  // E-Mail-Konfiguration
  'E-Mail-Konto einrichten (Outlook)',
  'E-Mail-Konto einrichten (Apple Mail)',
  'E-Mail-Konto einrichten (Thunderbird)',
  'E-Mail-Konto einrichten (Mobilgerät iOS/Android)',
  'E-Mail-Migration (Konten und Postfächer)',
  'Signatur und Abwesenheitsnotiz einrichten',
  'Spam-/Phishing-Filter konfigurieren',
  // Browser & Software
  'Google Chrome Installation und Einrichtung',
  'Firefox Installation und Einrichtung',
  'Microsoft Edge Konfiguration',
  'Browser-Lesezeichen und Passwort-Import',
  'Office-Paket Installation (Microsoft 365)',
  'Office-Paket Installation (LibreOffice)',
  'PDF-Software Installation (Adobe Reader)',
  'Antivirus-Software Installation',
  'Passwort-Manager Einrichtung',
  // Sicherheit am Kundenrechner
  'Firewall-Einstellungen prüfen und anpassen',
  'Windows Defender / Security prüfen',
  'Sicherheitsüberprüfung Arbeitsplatzrechner',
  'Update-Einstellungen prüfen und optimieren',
  'Datensicherung einrichten (lokal/Cloud)',
  'Cloud-Speicher Setup (OneDrive/Dropbox/iCloud)',
  'Zwei-Faktor-Authentifizierung einrichten',
  'Passwort-Audit und Neuvergabe',
  // Datenrettung & Fehlerdiagnose
  'Datenrettung und Wiederherstellung',
  'Fehlerdiagnose Hardware',
  'Fehlerdiagnose Software',
  'System-Reinigung und Performance-Optimierung',
  'Registry-Bereinigung',
  'Festplatten-Check und Defragmentierung',
  // Recherche & Dokumentation
  'Recherche zu technischem Sachverhalt',
  'Recherche zu rechtlichem Sachverhalt',
  'Recherche und Analyse',
  'Erstellung Recherche-Report',
  'Erstellung Statusbericht',
  'Erstellung Dokumentation / Report',
  'Gutachten / Stellungnahme',
  'Abklärung und Korrespondenz',
  'Vorbereitung Rechtsfall / Sachverhaltsklärung',
  'Bildschirmaufnahmen und Screenshots dokumentiert',
  // Kommunikation & Koordination
  'Telefonat (Beratung/Abstimmung)',
  'Videokonferenz (Beratung/Abstimmung)',
  'E-Mail-Korrespondenz',
  'Abstimmung mit Dienstleistern',
  'Abstimmung mit Behörden',
  // Schulung
  'Schulung E-Mail-Programm',
  'Schulung Office-Anwendungen',
  'Schulung Browser-Nutzung und Sicherheit',
  'Schulung Cloud-Speicher',
  'Schulung allgemeine PC-Nutzung',
]

interface Props {
  label?: string
  name: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  required?: boolean
  placeholder?: string
  suggestions?: string[]
  className?: string
  compact?: boolean
}

export default function AutocompleteInput({ label, name, value, onChange, required, placeholder, suggestions, className, compact }: Props) {
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const pool = suggestions || IT_SUGGESTIONS
  const filtered = value.length >= 1
    ? pool.filter(s => s.toLowerCase().includes(value.toLowerCase())).slice(0, 8)
    : []

  useEffect(() => {
    setSelectedIndex(-1)
  }, [value])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (suggestion: string) => {
    const syntheticEvent = {
      target: { name, value: suggestion },
    } as React.ChangeEvent<HTMLInputElement>
    onChange(syntheticEvent)
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || filtered.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(i => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault()
      handleSelect(filtered[selectedIndex])
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    }
  }

  return (
    <div ref={wrapperRef} className={`relative ${className || ''}`}>
      {label && (
        <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">
          {label}
          {required && <span className="text-danger ml-1">*</span>}
        </label>
      )}
      <input
        ref={inputRef}
        type="text"
        name={name}
        value={value}
        onChange={(e) => {
          onChange(e)
          setShowSuggestions(true)
        }}
        onFocus={() => { if (value.length >= 1) setShowSuggestions(true) }}
        onKeyDown={handleKeyDown}
        required={required}
        placeholder={placeholder}
        className={compact ? 'w-full text-sm' : 'w-full'}
        autoComplete="off"
      />
      {showSuggestions && filtered.length > 0 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-surface border border-border rounded-lg shadow-lg overflow-hidden">
          {filtered.map((s, i) => (
            <button
              key={s}
              type="button"
              onClick={() => handleSelect(s)}
              className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                i === selectedIndex
                  ? 'bg-accent/20 text-accent'
                  : 'text-text hover:bg-surface-2'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
