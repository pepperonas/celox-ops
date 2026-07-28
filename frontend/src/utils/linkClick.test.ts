import { describe, it, expect } from 'vitest'
import { isModifiedClick } from './linkClick'

describe('isModifiedClick', () => {
  it('behandelt den normalen Linksklick selbst (SPA-Navigation)', () => {
    expect(isModifiedClick({ button: 0 })).toBe(false)
    expect(isModifiedClick({})).toBe(false)
  })

  it('überlässt Cmd/Ctrl+Klick dem Browser (neuer Tab)', () => {
    expect(isModifiedClick({ metaKey: true })).toBe(true)
    expect(isModifiedClick({ ctrlKey: true })).toBe(true)
  })

  it('überlässt Shift/Alt dem Browser (neues Fenster / Download)', () => {
    expect(isModifiedClick({ shiftKey: true })).toBe(true)
    expect(isModifiedClick({ altKey: true })).toBe(true)
  })

  it('überlässt den Mittelklick dem Browser', () => {
    // Der am leichtesten vergessene Fall — Mittelklick öffnet einen neuen Tab.
    expect(isModifiedClick({ button: 1 })).toBe(true)
    expect(isModifiedClick({ button: 2 })).toBe(true)
  })
})
