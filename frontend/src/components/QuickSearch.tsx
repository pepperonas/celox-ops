import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

interface SearchHit {
  id: string
  type: 'customer' | 'invoice' | 'order' | 'contract' | 'lead'
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
}

const typeIcon: Record<SearchHit['type'], string> = {
  customer: '👤',
  invoice: '🧾',
  order: '📋',
  contract: '📄',
  lead: '🎯',
}

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
      try {
        const res = await api.get('/search', { params: { q: query.trim() } })
        setHits(res.data?.hits || [])
        setSelected(0)
      } catch (err) {
        console.warn('Suche fehlgeschlagen:', err)
        setHits([])
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
        className="bg-surface border border-border rounded-[12px] w-full max-w-xl mx-4 overflow-hidden shadow-2xl"
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
              <span className="text-[10px] text-text-muted bg-surface-2 px-1.5 py-0.5 rounded uppercase tracking-wider flex-shrink-0">
                {typeLabel[hit.type]}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
