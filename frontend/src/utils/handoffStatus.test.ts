import { describe, expect, it } from 'vitest'
import { buttonLabel, statusLabel, statusTone } from './handoffStatus'

describe('statusTone', () => {
  it('none ohne Status', () => {
    expect(statusTone(null)).toBe('none')
    expect(statusTone(undefined)).toBe('none')
    expect(statusTone({})).toBe('none')
  })

  it('ok bei created/updated', () => {
    expect(statusTone({ last_status: 'created' })).toBe('ok')
    expect(statusTone({ last_status: 'updated' })).toBe('ok')
  })

  it('error bei error:<code>', () => {
    expect(statusTone({ last_status: 'error:409' })).toBe('error')
    expect(statusTone({ last_status: 'error:timeout' })).toBe('error')
  })
})

describe('statusLabel', () => {
  it('Noch nicht übergeben ohne Status', () => {
    expect(statusLabel(null)).toBe('Noch nicht übergeben')
  })

  it('created mit Datum', () => {
    const label = statusLabel({ last_status: 'created', last_handoff_at: '2026-07-19T12:00:00Z' })
    expect(label).toContain('Übergeben')
    expect(label).toContain('neu angelegt')
    expect(label).toMatch(/\d{2}\.\d{2}\.2026/)
  })

  it('updated verweist auf Enrich-only-Anreicherung', () => {
    expect(statusLabel({ last_status: 'updated' })).toContain('angereichert')
  })

  it('error zeigt den Code und bleibt retry-fähig formuliert', () => {
    const label = statusLabel({ last_status: 'error:409' })
    expect(label).toContain('Fehler (409)')
    expect(label).toContain('erneut versuchen')
  })

  it('ungültiges Datum bricht nichts', () => {
    expect(statusLabel({ last_status: 'created', last_handoff_at: 'kaputt' })).toContain('Übergeben')
  })
})

describe('buttonLabel', () => {
  it('Übergeben ohne Status oder nach Fehler', () => {
    expect(buttonLabel(null)).toBe('Übergeben')
    expect(buttonLabel({ last_status: 'error:504' })).toBe('Übergeben')
  })

  it('Erneut übergeben nach Erfolg', () => {
    expect(buttonLabel({ last_status: 'created' })).toBe('Erneut übergeben')
    expect(buttonLabel({ last_status: 'updated' })).toBe('Erneut übergeben')
  })
})
