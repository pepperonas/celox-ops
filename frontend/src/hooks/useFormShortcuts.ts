import { useEffect } from 'react'

/**
 * Binds Ctrl/Cmd+S to submit a form, Esc to a custom cancel handler.
 * Call inside a component that owns the form.
 */
export function useFormShortcuts(opts: {
  onSubmit?: () => void
  onCancel?: () => void
  enabled?: boolean
}): void {
  const { onSubmit, onCancel, enabled = true } = opts
  useEffect(() => {
    if (!enabled) return
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's' && onSubmit) {
        e.preventDefault()
        onSubmit()
      } else if (e.key === 'Escape' && onCancel) {
        // Don't fire if the active element is an input that has open suggestions
        // — Esc should close those first. Best-effort check.
        const target = e.target as HTMLElement | null
        const tag = target?.tagName?.toLowerCase()
        if (tag === 'input' || tag === 'textarea') return
        onCancel()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onSubmit, onCancel, enabled])
}
