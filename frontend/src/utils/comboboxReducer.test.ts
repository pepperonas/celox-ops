import { describe, it, expect } from 'vitest'
import { comboboxKeydown, optionsChanged, initialCombobox, type ComboboxState } from './comboboxReducer'

const open5: ComboboxState = { open: true, activeIndex: -1, count: 5 }

describe('optionsChanged', () => {
  it('öffnet bei Treffern, Index resettet', () => {
    expect(optionsChanged({ open: true, activeIndex: 3, count: 5 }, 2))
      .toEqual({ open: true, activeIndex: -1, count: 2 })
  })
  it('0 Treffer → geschlossen', () => {
    expect(optionsChanged(open5, 0).open).toBe(false)
  })
  it('open=false erzwingt geschlossen trotz Treffern', () => {
    expect(optionsChanged(open5, 3, false).open).toBe(false)
  })
})

describe('comboboxKeydown – Navigation', () => {
  it('↓ öffnet geschlossene Liste und markiert erste Option', () => {
    const { state } = comboboxKeydown({ open: false, activeIndex: -1, count: 3 }, 'ArrowDown')
    expect(state).toEqual({ open: true, activeIndex: 0, count: 3 })
  })
  it('↓ läuft runter und stoppt am Ende (kein Wrap)', () => {
    let s = { ...open5, activeIndex: 3 }
    s = comboboxKeydown(s, 'ArrowDown').state
    expect(s.activeIndex).toBe(4)
    s = comboboxKeydown(s, 'ArrowDown').state
    expect(s.activeIndex).toBe(4)
  })
  it('↑ läuft hoch und stoppt bei 0', () => {
    let s = { ...open5, activeIndex: 1 }
    s = comboboxKeydown(s, 'ArrowUp').state
    expect(s.activeIndex).toBe(0)
    s = comboboxKeydown(s, 'ArrowUp').state
    expect(s.activeIndex).toBe(0)
  })
  it('Home/End springen an Anfang/Ende', () => {
    expect(comboboxKeydown({ ...open5, activeIndex: 3 }, 'Home').state.activeIndex).toBe(0)
    expect(comboboxKeydown({ ...open5, activeIndex: 0 }, 'End').state.activeIndex).toBe(4)
  })
})

describe('comboboxKeydown – Auswahl & Schließen', () => {
  it('Enter mit Hervorhebung → select + schließt', () => {
    const { state, action } = comboboxKeydown({ ...open5, activeIndex: 2 }, 'Enter')
    expect(action).toBe('select')
    expect(state.open).toBe(false)
  })
  it('Enter ohne Hervorhebung → none (Form-Submit bleibt möglich)', () => {
    expect(comboboxKeydown(open5, 'Enter').action).toBe('none')
  })
  it('Tab mit Hervorhebung übernimmt die Option', () => {
    expect(comboboxKeydown({ ...open5, activeIndex: 1 }, 'Tab').action).toBe('select')
  })
  it('Tab ohne Hervorhebung schließt nur', () => {
    const { state, action } = comboboxKeydown(open5, 'Tab')
    expect(action).toBe('close')
    expect(state.open).toBe(false)
  })
  it('Escape schließt ohne Auswahl', () => {
    const { state, action } = comboboxKeydown({ ...open5, activeIndex: 2 }, 'Escape')
    expect(action).toBe('close')
    expect(state).toMatchObject({ open: false, activeIndex: -1 })
  })
  it('andere Tasten ändern nichts', () => {
    expect(comboboxKeydown(open5, 'a')).toEqual({ state: open5, action: 'none' })
  })
  it('geschlossen + leere Liste: alles no-op', () => {
    expect(comboboxKeydown(initialCombobox, 'ArrowDown').state).toEqual(initialCombobox)
    expect(comboboxKeydown(initialCombobox, 'Enter').action).toBe('none')
  })
})
