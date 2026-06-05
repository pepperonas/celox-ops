import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

interface SearchHit {
  id: string
  type: 'customer' | 'invoice' | 'order' | 'contract' | 'lead' | 'action'
  title: string
  subtitle: string | null
  url: string
}

const typeLabel: Record<SearchHit['type'], string> = {
  customer: 'Kunde',
  invoice: 'Rechnung',
  order: 'Auftrag',
  contract: 'Vertrag',
  lead: 'Lead',
  action: 'Aktion',
}

const typeIcon: Record<SearchHit['type'], string> = {
  customer: '👤',
  invoice: '🧾',
  order: '📋',
  contract: '📄',
  lead: '🎯',
  action: '⚡',
}

// Static action shortcuts — match against query, prepend to results
const ACTIONS: { keywords: string; title: string; subtitle: string; url: string }[] = [
  { keywords: 'neue rechnung create invoice', title: 'Neue Rechnung erstellen', subtitle: 'Rechnungs-Formular öffnen', url: '/rechnungen/neu' },
  { keywords: 'neuer kunde create customer', title: 'Neuen Kunden anlegen', subtitle: 'Kunden-Formular öffnen', url: '/kunden/neu' },
  { keywords: 'neuer auftrag create order angebot', title: 'Neuen Auftrag anlegen', subtitle: 'Auftrags-Formular öffnen', url: '/auftraege/neu' },
  { keywords: 'neuer vertrag create contract', title: 'Neuen Vertrag anlegen', subtitle: 'Vertrags-Formular öffnen', url: '/vertraege/neu' },
  { keywords: 'neue ausgabe create expense spese beleg', title: 'Neue Ausgabe', subtitle: 'Ausgaben-Formular öffnen', url: '/ausgaben/neu' },
  { keywords: 'neuer lead create lead vorgemerkt', title: 'Neuen Lead anlegen', subtitle: 'Lead-Formular öffnen', url: '/vorgemerkt/neu' },
  { keywords: 'kalender termine fristen', title: 'Kalender öffnen', subtitle: 'Termine und Fristen', url: '/kalender' },
  { keywords: 'kanban board', title: 'Kanban-Board öffnen', subtitle: 'Aufträge visuell', url: '/kanban' },
  { keywords: 'aufgaben tasks todo', title: 'Aufgaben anzeigen', subtitle: 'Anstehende Aktionen', url: '/aufgaben' },
  { keywords: 'einstellungen settings', title: 'Einstellungen', subtitle: 'App-Konfiguration', url: '/einstellungen' },
  { keywords: 'analyse analytics rentabilität forecast', title: 'Analyse', subtitle: 'Kunden-Rentabilität + Forecast', url: '/analyse' },
  { keywords: 'eür euer steuerberater export', title: 'EÜR-Übersicht', subtitle: 'Einnahmen-Überschuss-Rechnung', url: '/euer' },
  { keywords: 'zeiterfassung time tracking stunden', title: 'Zeiterfassung', subtitle: 'Stunden-Timer + Liste', url: '/zeiterfassung' },
  { keywords: 'dokumente documents anhänge', title: 'Vertragsdokumente', subtitle: 'Rechtsvorlagen-Bibliothek', url: '/dokumente' },
]

export default function QuickSearch() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const debounceRef = useRef<number | null>(null)

  // Global Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((o) => !o)
      } else if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open])

  // Reset on open
  useEffect(() => {
    if (open) {
      setQuery('')
      setHits([])
      setSelected(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current)
    if (query.trim().length < 2) {
      setHits([])
      setLoading(false)
      return
    }
    setLoading(true)
    debounceRef.current = window.setTimeout(async () => {
      const q = query.trim().toLowerCase()
      // Action shortcuts (instant, client-side)
      const actionHits: SearchHit[] = ACTIONS
        .filter((a) => a.title.toLowerCase().includes(q) || a.keywords.includes(q))
        .slice(0, 5)
        .map((a, i) => ({ id: `action-${i}`, type: 'action', title: a.title, subtitle: a.subtitle, url: a.url }))
      try {
        const res = await api.get('/search', { params: { q: query.trim() } })
        const entityHits = res.data?.hits || []
        setHits([...actionHits, ...entityHits])
        setSelected(0)
      } catch (err) {
        console.warn('Suche fehlgeschlagen:', err)
        setHits(actionHits)
      }
      setLoading(false)
    }, 200)
  }, [query])

  // Arrow navigation + Enter
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelected((s) => Math.min(s + 1, hits.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelected((s) => Math.max(s - 1, 0))
    } else if (e.key === 'Enter' && hits[selected]) {
      e.preventDefault()
      navigate(hits[selected].url)
      setOpen(false)
    }
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/85 pt-[10vh]"
      onClick={() => setOpen(false)}
    >
      <div
        className="bg-surface border border-border rounded-card w-full max-w-xl mx-4 overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <svg className="w-4 h-4 text-text-muted flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Suche Kunden, Rechnungen, Aufträge…"
            className="flex-1 bg-transparent border-0 outline-none text-text placeholder:text-text-muted text-sm"
          />
          <kbd className="text-[10px] text-text-muted bg-surface-2 px-1.5 py-0.5 rounded border border-border">ESC</kbd>
        </div>

        <div className="max-h-[60vh] overflow-y-auto">
          {loading && (
            <div className="px-4 py-6 text-center text-sm text-text-muted">Suche…</div>
          )}
          {!loading && query.trim().length >= 2 && hits.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-text-muted">Keine Treffer für „{query}"</div>
          )}
          {!loading && query.trim().length < 2 && (
            <div className="px-4 py-6 text-center text-sm text-text-muted">
              Mindestens 2 Zeichen eingeben.<br />
              <span className="text-xs">↑↓ Navigieren · Enter Öffnen · Esc Schließen</span>
            </div>
          )}
          {hits.map((hit, i) => (
            <button
              key={`${hit.type}-${hit.id}`}
              onClick={() => { navigate(hit.url); setOpen(false) }}
              onMouseEnter={() => setSelected(i)}
              className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${
                i === selected ? 'bg-surface-2' : 'hover:bg-surface-2/50'
              }`}
            >
              <span className="text-lg flex-shrink-0">{typeIcon[hit.type]}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text truncate">{hit.title}</p>
                {hit.subtitle && (
                  <p className="text-xs text-text-muted truncate mt-0.5">{hit.subtitle}</p>
                )}
              </div>
              <span className="text-[10px] text-text-muted bg-surface-2 px-1.5 py-0.5 rounded flex-shrink-0">
                {typeLabel[hit.type]}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
