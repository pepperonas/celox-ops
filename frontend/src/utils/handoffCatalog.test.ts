import { describe, expect, it } from 'vitest'
import { PORTAL_PRODUCTS } from './handoffCatalog'

describe('handoffCatalog', () => {
  it('enthält 22 Produkte (6 Audits + 16 Schulungen, portal-Stand 2026-07)', () => {
    expect(PORTAL_PRODUCTS).toHaveLength(22)
    expect(PORTAL_PRODUCTS.filter((p) => p.kind === 'audit')).toHaveLength(6)
    expect(PORTAL_PRODUCTS.filter((p) => p.kind === 'training')).toHaveLength(16)
  })

  it('alle Keys folgen dem Entitlement-Format audit:<id>/training:<id>', () => {
    for (const p of PORTAL_PRODUCTS) {
      expect(p.key).toMatch(/^(audit|training):[a-z0-9-]+$/)
      expect(p.key.startsWith(`${p.kind}:`)).toBe(true)
    }
  })

  it('keine doppelten Keys', () => {
    const keys = PORTAL_PRODUCTS.map((p) => p.key)
    expect(new Set(keys).size).toBe(keys.length)
  })

  it('jedes Produkt hat ein nichtleeres Label', () => {
    for (const p of PORTAL_PRODUCTS) expect(p.label.trim().length).toBeGreaterThan(0)
  })

  it('bekannte Kern-Entitlements sind enthalten', () => {
    const keys = new Set(PORTAL_PRODUCTS.map((p) => p.key))
    expect(keys.has('audit:dsgvo')).toBe(true)
    expect(keys.has('training:security')).toBe(true)
    expect(keys.has('audit:ai-act-compliance')).toBe(true)
  })
})
