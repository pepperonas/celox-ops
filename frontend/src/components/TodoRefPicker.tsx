import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { getCustomers } from '../api/customers'
import { createRainmakerLead, getRainmakerLeads } from '../api/rainmaker'
import { comboboxKeydown, type ComboboxState } from '../utils/comboboxReducer'

export interface TodoRef {
  customer_id: string | null
  lead_id: string | null
  label: string
}

interface Option {
  kind: 'customer' | 'lead' | 'create-lead'
  id: string | null
  label: string
  hint: string
}

interface Props {
  value: TodoRef | null
  onChange: (ref: TodoRef | null) => void
  /** Kompakte Darstellung für die Schnellerfassungs-Zeile. */
  compact?: boolean
  disabled?: boolean
}

/**
 * Bezugsfeld für To-dos: sucht serverseitig in Kunden UND Leads (debounced) und
 * bietet zu einem unbekannten Namen direkt „Neuen Lead anlegen" an — damit ein
 * To-do zu einem noch nicht erfassten Interessenten nicht am Stammdatensatz
 * scheitert.
 */
export default function TodoRefPicker({ value, onChange, compact = false, disabled }: Props) {
  const [query, setQuery] = useState('')
  const [options, setOptions] = useState<Option[]>([])
  const [state, setState] = useState<ComboboxState>({ open: false, activeIndex: -1, count: 0 })
  const [creating, setCreating] = useState(false)
  const boxRef = useRef<HTMLDivElement>(null)
  const listId = useMemo(() => `todo-ref-${Math.random().toString(36).slice(2)}`, [])

  // Debounced Suche — erst ab 2 Zeichen, sonst rauscht jede Taste einen Request.
  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) {
      setOptions([])
      setState((s) => ({ ...s, count: 0, activeIndex: -1 }))
      return
    }
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const [customers, leads] = await Promise.all([
          getCustomers({ search: q, page_size: 6 }).catch(() => null),
          getRainmakerLeads({ search: q, page_size: 6 }).catch(() => null),
        ])
        if (cancelled) return
        const opts: Option[] = []
        for (const c of customers?.items || []) {
          opts.push({
            kind: 'customer', id: c.id,
            label: (c.company || '').trim() || c.name,
            hint: c.company && c.name && c.company !== c.name ? c.name : 'Kunde',
          })
        }
        for (const l of leads?.items || []) {
          opts.push({
            kind: 'lead', id: l.id,
            label: (l.company || '').trim() || l.contact_name || 'Lead',
            hint: l.contact_name && l.company ? l.contact_name : 'Lead',
          })
        }
        // Exakter Treffer vorhanden? Dann keine Neuanlage anbieten.
        const exists = opts.some((o) => o.label.toLowerCase() === q.toLowerCase())
        if (!exists) {
          opts.push({ kind: 'create-lead', id: null, label: q, hint: 'als neuen Lead anlegen' })
        }
        setOptions(opts)
        setState((s) => ({ ...s, open: true, count: opts.length, activeIndex: opts.length ? 0 : -1 }))
      } catch {
        /* Suche ist Komfort — ein Fehler darf das Formular nicht blockieren */
      }
    }, 220)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [query])

  // Klick außerhalb schließt die Liste
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setState((s) => ({ ...s, open: false }))
      }
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  const select = useCallback(async (opt: Option) => {
    if (opt.kind === 'create-lead') {
      setCreating(true)
      try {
        const lead = await createRainmakerLead({ company: opt.label, source: 'To-do' })
        onChange({ customer_id: null, lead_id: lead.id, label: opt.label })
        toast.success(`Lead „${opt.label}" angelegt.`)
      } catch (e: unknown) {
        // 409 = Dedup-Warnung des Backends; mit force anlegen wäre hier falsch,
        // der Nutzer soll den bestehenden Lead wählen.
        const err = e as { response?: { status?: number; data?: { detail?: { message?: string } } } }
        if (err.response?.status === 409) {
          toast.error(err.response.data?.detail?.message || 'Diesen Lead gibt es bereits — bitte auswählen.')
        } else {
          toast.error('Lead konnte nicht angelegt werden.')
        }
        setCreating(false)
        return
      }
      setCreating(false)
    } else {
      onChange({
        customer_id: opt.kind === 'customer' ? opt.id : null,
        lead_id: opt.kind === 'lead' ? opt.id : null,
        label: opt.label,
      })
    }
    setQuery('')
    setOptions([])
    setState({ open: false, activeIndex: -1, count: 0 })
  }, [onChange])

  if (value) {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-accent/15 text-accent text-xs max-w-full">
        <span className="truncate">{value.label}</span>
        {!disabled && (
          <button
            type="button"
            onClick={() => onChange(null)}
            aria-label="Bezug entfernen"
            className="hover:opacity-70 transition-opacity"
          >
            ✕
          </button>
        )}
      </span>
    )
  }

  return (
    <div ref={boxRef} className="relative">
      <input
        type="text"
        role="combobox"
        aria-expanded={state.open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={state.activeIndex >= 0 ? `${listId}-${state.activeIndex}` : undefined}
        value={query}
        disabled={disabled || creating}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          const result = comboboxKeydown(state, e.key)
          if (result.state !== state) setState(result.state)
          if (result.action === 'select' && options[state.activeIndex]) {
            e.preventDefault()
            select(options[state.activeIndex])
          } else if (result.action !== 'none') {
            e.preventDefault()
          }
        }}
        placeholder={compact ? 'Kunde/Lead…' : 'Kunde oder Lead suchen — oder neuen Lead anlegen'}
        className={compact ? 'w-full text-sm' : 'w-full'}
      />
      {state.open && options.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-30 mt-1 w-full max-h-64 overflow-y-auto bg-surface-2 border border-border rounded-md shadow-elev-2"
        >
          {options.map((opt, i) => (
            <li
              key={`${opt.kind}-${opt.id ?? 'new'}-${i}`}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === state.activeIndex}
              onMouseDown={(e) => { e.preventDefault(); select(opt) }}
              onMouseEnter={() => setState((s) => ({ ...s, activeIndex: i }))}
              className={`px-3 py-2 cursor-pointer text-sm flex items-center gap-2 ${
                i === state.activeIndex ? 'bg-accent/15 text-text' : 'text-text-muted'
              }`}
            >
              <span aria-hidden>
                {opt.kind === 'customer' ? '🏢' : opt.kind === 'lead' ? '🎯' : '＋'}
              </span>
              <span className="truncate text-text">{opt.kind === 'create-lead' ? `Neuer Lead: ${opt.label}` : opt.label}</span>
              <span className="ml-auto text-xs shrink-0">{opt.hint}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
