/**
 * Reine Tastatur-Zustandsmaschine für das ARIA-Combobox-Pattern — dadurch ist
 * die komplette Keyboard-Navigation unit-testbar (node-Env, kein DOM).
 * Die Komponente füttert Events rein und führt die zurückgegebene Aktion aus.
 */
export interface ComboboxState {
  open: boolean
  activeIndex: number   // -1 = nichts hervorgehoben
  count: number         // Anzahl sichtbarer Optionen
}

export type ComboboxAction = 'select' | 'close' | 'none'

export const initialCombobox: ComboboxState = { open: false, activeIndex: -1, count: 0 }

/** Optionen haben sich geändert (Tippen/Fetch): Index zurücksetzen, ggf. öffnen. */
export function optionsChanged(state: ComboboxState, count: number, open = true): ComboboxState {
  return { open: open && count > 0, activeIndex: -1, count }
}

export function comboboxKeydown(
  state: ComboboxState,
  key: string,
): { state: ComboboxState; action: ComboboxAction } {
  const { open, activeIndex, count } = state
  if (!open || count === 0) {
    // Geschlossen: ↓ öffnet die Liste (Standard-Combobox-Verhalten)
    if (key === 'ArrowDown' && count > 0) {
      return { state: { ...state, open: true, activeIndex: 0 }, action: 'none' }
    }
    return { state, action: 'none' }
  }
  switch (key) {
    case 'ArrowDown':
      return { state: { ...state, activeIndex: Math.min(activeIndex + 1, count - 1) }, action: 'none' }
    case 'ArrowUp':
      return { state: { ...state, activeIndex: Math.max(activeIndex - 1, 0) }, action: 'none' }
    case 'Home':
      return { state: { ...state, activeIndex: 0 }, action: 'none' }
    case 'End':
      return { state: { ...state, activeIndex: count - 1 }, action: 'none' }
    case 'Enter':
      if (activeIndex >= 0) {
        return { state: { ...state, open: false, activeIndex: -1 }, action: 'select' }
      }
      return { state, action: 'none' }   // ohne Auswahl: Enter normal (Form-Submit)
    case 'Tab':
      // Tab schließt die Liste; hervorgehobene Option wird übernommen
      if (activeIndex >= 0) {
        return { state: { ...state, open: false, activeIndex: -1 }, action: 'select' }
      }
      return { state: { ...state, open: false, activeIndex: -1 }, action: 'close' }
    case 'Escape':
      return { state: { ...state, open: false, activeIndex: -1 }, action: 'close' }
    default:
      return { state, action: 'none' }
  }
}
