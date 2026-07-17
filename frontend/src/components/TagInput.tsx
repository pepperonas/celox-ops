import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { getSuggestions } from '../api/suggestions'
import { canonicalize, dedupeCanonical, foldKey, rankSuggestions, splitTags } from '../utils/taxonomy'
import { comboboxKeydown, initialCombobox, optionsChanged, type ComboboxState } from '../utils/comboboxReducer'

interface Props {
  label?: string
  value: string[]
  onChange: (tags: string[]) => void
  /** Taxonomie-Feld-Key für Vorschläge (Default 'tag'). */
  field?: string
  placeholder?: string
}

/**
 * Multi-Value-Eingabe mit MD3-Chips + hybriden Autocomplete-Vorschlägen.
 * Komma/Enter/Tab fügen hinzu, Backspace (leeres Feld) löscht den letzten Chip,
 * Paste von "a, b, c" splittet. Creatable: „Neu anlegen: …" für freie Werte.
 * Werte werden beim Hinzufügen kanonisiert (Synonyme → kanonische Schreibweise).
 */
export default function TagInput({ label, value, onChange, field = 'tag', placeholder }: Props) {
  const [input, setInput] = useState('')
  const [box, setBox] = useState<ComboboxState>(initialCombobox)
  const [pool, setPool] = useState<string[]>([])
  const [synonyms, setSynonyms] = useState<Record<string, string>>({})
  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listId = useId()

  useEffect(() => {
    getSuggestions(field).then((s) => { setPool(s.values); setSynonyms(s.synonyms) }).catch(() => {})
  }, [field])

  // Vorschläge: gerankt, bereits gewählte ausgeblendet; creatable-Zeile bei freiem Wert.
  const selectedKeys = useMemo(() => new Set(value.map(foldKey)), [value])
  const matches = useMemo(
    () => rankSuggestions(pool, input, 8).filter((s) => !selectedKeys.has(foldKey(s))),
    [pool, input, selectedKeys],
  )
  const trimmed = input.trim()
  const canCreate = !!trimmed && !matches.some((m) => foldKey(m) === foldKey(trimmed)) && !selectedKeys.has(foldKey(trimmed))
  const options = canCreate ? [...matches, `__create__${trimmed}`] : matches

  const addTags = (raw: string[]) => {
    const next = dedupeCanonical([...value, ...raw], pool, synonyms)
    if (next.length !== value.length || next.some((t, i) => t !== value[i])) onChange(next)
    setInput('')
    setBox((s) => ({ ...s, open: false, activeIndex: -1 }))
  }
  const removeAt = (i: number) => onChange(value.filter((_, j) => j !== i))

  const pick = (opt: string) =>
    addTags([opt.startsWith('__create__') ? opt.slice('__create__'.length) : opt])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Separatoren zuerst: Enter/Komma/Tab übernehmen Eingabe bzw. Hervorhebung
    if ((e.key === 'Enter' || e.key === ',') && box.activeIndex < 0 && trimmed) {
      e.preventDefault()
      addTags(splitTags(trimmed))
      return
    }
    if (e.key === 'Backspace' && !input && value.length > 0) {
      removeAt(value.length - 1)
      return
    }
    const { state, action } = comboboxKeydown(box, e.key)
    if (action === 'select' && box.activeIndex >= 0) {
      e.preventDefault()
      pick(options[box.activeIndex])
      return
    }
    if (state !== box) {
      if (e.key !== 'Tab') e.preventDefault()
      setBox(state)
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const text = e.clipboardData.getData('text')
    if (/[,;\n]/.test(text)) {
      e.preventDefault()
      addTags(splitTags(text))
    }
  }

  useEffect(() => {
    setBox((s) => (s.open ? optionsChanged(s, options.length) : { ...s, count: options.length }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, pool.length, value.length])

  useEffect(() => {
    const outside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setBox((s) => ({ ...s, open: false, activeIndex: -1 }))
      }
    }
    document.addEventListener('mousedown', outside)
    return () => document.removeEventListener('mousedown', outside)
  }, [])

  const open = box.open && options.length > 0

  return (
    <div ref={wrapperRef} className="relative">
      {label && <label className="block text-xs text-text-muted mb-2">{label}</label>}
      <div
        onClick={() => inputRef.current?.focus()}
        className="w-full min-h-[42px] flex flex-wrap items-center gap-1.5 bg-surface-container border border-border rounded-lg px-2 py-1.5 cursor-text focus-within:border-accent transition-colors duration-short"
      >
        {value.map((t, i) => (
          <span key={t} className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-surface-high text-text">
            {t}
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); removeAt(i) }}
              aria-label={`Tag ${t} entfernen`}
              className="text-text-muted hover:text-danger leading-none"
            >
              ×
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => { setInput(e.target.value); setBox((s) => optionsChanged(s, options.length || 1)) }}
          onFocus={() => setBox((s) => optionsChanged(s, options.length))}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={value.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[120px] !border-0 !bg-transparent !px-1 !py-0.5 text-sm outline-none"
          autoComplete="off"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          aria-controls={listId}
          aria-activedescendant={box.activeIndex >= 0 ? `${listId}-opt-${box.activeIndex}` : undefined}
        />
      </div>
      <span className="sr-only" aria-live="polite">{open ? `${options.length} Vorschläge verfügbar` : ''}</span>
      {open && (
        <div id={listId} role="listbox"
             className="absolute z-50 top-full left-0 right-0 mt-1 bg-surface border border-border rounded-lg shadow-lg overflow-hidden max-h-64 overflow-y-auto">
          {options.map((opt, i) => {
            const isCreate = opt.startsWith('__create__')
            const text = isCreate ? opt.slice('__create__'.length) : opt
            return (
              <button
                key={opt}
                id={`${listId}-opt-${i}`}
                role="option"
                aria-selected={i === box.activeIndex}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(opt)}
                className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                  i === box.activeIndex ? 'bg-accent/20 text-accent' : 'text-text hover:bg-surface-2'
                }`}
              >
                {isCreate ? <span className="text-text-muted">Neu anlegen: <span className="text-text font-medium">{text}</span></span> : text}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
