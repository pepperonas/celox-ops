import { useState, useRef, useEffect } from 'react'

const IT_SUGGESTIONS = [
  // Website
  'Website-Erstellung',
  'Website-Erstellung (WordPress)',
  'Website-Erstellung (React)',
  'Website-Redesign',
  'Website-Relaunch',
  'Website-Wartung',
  'Website-Pflege und Aktualisierung',
  'Website-Optimierung',
  'Website-Migration',
  'Landing Page Erstellung',
  'One-Page Website',
  'Responsive Anpassung',
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

interface Props {
  label: string
  name: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  required?: boolean
  placeholder?: string
}

export default function AutocompleteInput({ label, name, value, onChange, required, placeholder }: Props) {
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const filtered = value.length >= 1
    ? IT_SUGGESTIONS.filter(s => s.toLowerCase().includes(value.toLowerCase())).slice(0, 8)
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
    <div ref={wrapperRef} className="relative">
      <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">
        {label}
        {required && <span className="text-danger ml-1">*</span>}
      </label>
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
        className="w-full"
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
