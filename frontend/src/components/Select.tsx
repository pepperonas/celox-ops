import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { comboboxKeydown, type ComboboxState } from '../utils/comboboxReducer'

export interface SelectOption {
  value: string | number
  label: string
  disabled?: boolean
}

/** Native-kompatibles Change-Event, damit bestehende `handleChange`-Handler
 *  (`setForm({ ...form, [e.target.name]: e.target.value })`) unverändert laufen. */
export interface SelectChangeEvent {
  target: { name: string; value: string }
}

interface Props {
  value: string | number | null | undefined
  onChange: (e: SelectChangeEvent) => void
  options: SelectOption[]
  name?: string
  id?: string
  /** Wird als erste, leere Option angeboten (wie `<option value="">…`). */
  placeholder?: string
  disabled?: boolean
  required?: boolean
  /** Kompakte Höhe für Filterleisten/Inline-Zeilen. */
  compact?: boolean
  className?: string
  /** Tooltip am Trigger (wie beim nativen select). */
  title?: string
  'aria-label'?: string
  'aria-labelledby'?: string
}

/**
 * App-eigenes Dropdown (MD3) — ersetzt `<select>` überall.
 *
 * Warum kein natives Select: das öffnet das OS-Popup und ignoriert damit
 * Theme, Radien und Motion-Token; im dunklen Theme sieht es fremd aus.
 *
 * Die Liste rendert per `createPortal` an `document.body` mit `position: fixed`
 * — sonst würde sie in Modals, Sticky-Leisten und `overflow-hidden`-Containern
 * abgeschnitten (Repo-Regel: transformierte Vorfahren sind der Bezugsrahmen für
 * fixed). Position wird beim Öffnen gemessen und bei Scroll/Resize nachgeführt.
 */
export default function Select({
  value, onChange, options, name = '', id, placeholder, disabled,
  required, compact, className = '', title, ...aria
}: Props) {
  const reactId = useId()
  const listId = `sel-${(id || name || reactId).replace(/[^\w-]/g, '')}`
  const triggerRef = useRef<HTMLButtonElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const [state, setState] = useState<ComboboxState>({ open: false, activeIndex: -1, count: 0 })
  const [rect, setRect] = useState<{ top: number; left: number; width: number; above: boolean } | null>(null)

  // Placeholder ist eine echte, wählbare Option (wie beim nativen Select).
  const items: SelectOption[] = placeholder
    ? [{ value: '', label: placeholder }, ...options]
    : options
  const selectedIndex = items.findIndex((o) => String(o.value) === String(value ?? ''))
  const selected = selectedIndex >= 0 ? items[selectedIndex] : undefined

  const measure = useCallback(() => {
    const el = triggerRef.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const spaceBelow = window.innerHeight - r.bottom
    // Nach oben klappen, wenn unten zu wenig Platz ist (Modal-Fußzeilen!).
    const above = spaceBelow < 220 && r.top > spaceBelow
    setRect({ top: above ? r.top : r.bottom, left: r.left, width: r.width, above })
  }, [])

  const open = useCallback(() => {
    if (disabled) return
    measure()
    setState({ open: true, count: items.length, activeIndex: Math.max(selectedIndex, 0) })
  }, [disabled, measure, items.length, selectedIndex])

  const close = useCallback(() => {
    setState((s) => ({ ...s, open: false, activeIndex: -1 }))
  }, [])

  const pick = useCallback((i: number) => {
    const opt = items[i]
    if (!opt || opt.disabled) return
    onChange({ target: { name, value: String(opt.value) } })
    close()
    triggerRef.current?.focus()
  }, [items, name, onChange, close])

  // Position nachführen + bei Klick außerhalb schließen.
  useLayoutEffect(() => {
    if (!state.open) return
    const onScrollOrResize = () => measure()
    // capture: fängt auch das Scrollen innerer Container (Modals, Tabellen)
    window.addEventListener('scroll', onScrollOrResize, true)
    window.addEventListener('resize', onScrollOrResize)
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node
      if (!triggerRef.current?.contains(t) && !listRef.current?.contains(t)) close()
    }
    document.addEventListener('mousedown', onDown)
    return () => {
      window.removeEventListener('scroll', onScrollOrResize, true)
      window.removeEventListener('resize', onScrollOrResize)
      document.removeEventListener('mousedown', onDown)
    }
  }, [state.open, measure, close])

  // Aktive Option in Sicht halten (Tastaturnavigation in langen Listen).
  useEffect(() => {
    if (!state.open || state.activeIndex < 0) return
    listRef.current?.querySelector<HTMLElement>(`#${listId}-${state.activeIndex}`)
      ?.scrollIntoView({ block: 'nearest' })
  }, [state.open, state.activeIndex, listId])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!state.open && (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
      e.preventDefault()
      open()
      return
    }
    const res = comboboxKeydown({ ...state, count: items.length }, e.key)
    if (res.action === 'select') {
      e.preventDefault()
      pick(state.activeIndex)
      return
    }
    if (res.state !== state) {
      if (e.key !== 'Tab') e.preventDefault()
      setState(res.state)
    }
    if (res.action === 'close') triggerRef.current?.focus()
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        id={id}
        role="combobox"
        aria-expanded={state.open}
        aria-controls={state.open ? listId : undefined}
        aria-haspopup="listbox"
        aria-required={required || undefined}
        aria-activedescendant={state.open && state.activeIndex >= 0 ? `${listId}-${state.activeIndex}` : undefined}
        disabled={disabled}
        title={title}
        onClick={() => (state.open ? close() : open())}
        onKeyDown={handleKeyDown}
        {...aria}
        className={`md-select-trigger ${compact ? 'md-select-compact' : ''} ${className}`}
      >
        <span className={`truncate ${selected && String(selected.value) !== '' ? 'text-text' : 'text-text-muted'}`}>
          {selected ? selected.label : (placeholder || '')}
        </span>
        <svg
          className={`w-4 h-4 shrink-0 text-text-muted transition-transform duration-short ${state.open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {state.open && rect && createPortal(
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          aria-label={aria['aria-label']}
          style={{
            position: 'fixed',
            left: rect.left,
            width: rect.width,
            ...(rect.above
              ? { bottom: window.innerHeight - rect.top + 4 }
              : { top: rect.top + 4 }),
          }}
          className="z-[60] max-h-64 overflow-y-auto bg-surface-2 border border-border rounded-md shadow-elev-3 py-1 animate-md-fade"
        >
          {items.map((opt, i) => {
            const isSelected = i === selectedIndex
            return (
              <li
                key={`${opt.value}-${i}`}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={isSelected}
                aria-disabled={opt.disabled || undefined}
                onMouseDown={(e) => { e.preventDefault(); pick(i) }}
                onMouseEnter={() => setState((s) => ({ ...s, activeIndex: i }))}
                className={`flex items-center gap-2 px-3 py-2 text-sm cursor-pointer transition-colors duration-short ${
                  opt.disabled ? 'opacity-40 cursor-not-allowed' : ''
                } ${i === state.activeIndex ? 'bg-accent/15' : ''} ${isSelected ? 'text-accent font-medium' : 'text-text'}`}
              >
                <span className="truncate flex-1">{opt.label}</span>
                {isSelected && (
                  <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </li>
            )
          })}
        </ul>,
        document.body,
      )}
    </>
  )
}
