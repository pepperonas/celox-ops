import { describe, it, expect } from 'vitest'
import {
  DREAM_PRESETS, DREAM_MILESTONES, presetByKey,
  euroToKm, evPerContact, monthsEarlier,
} from './dreamPresets'

describe('DREAM_PRESETS', () => {
  it('has unique keys and a custom option', () => {
    const keys = DREAM_PRESETS.map((p) => p.key)
    expect(new Set(keys).size).toBe(keys.length)
    expect(keys).toContain('custom')
  })

  it('every preset has a positive price, emoji, tagline and specs', () => {
    for (const p of DREAM_PRESETS) {
      expect(p.price).toBeGreaterThan(0)
      expect(p.emoji.length).toBeGreaterThan(0)
      expect(p.tagline.length).toBeGreaterThan(0)
      expect(p.specs.length).toBeGreaterThan(0)
      expect(p.colors).toHaveLength(2)
    }
  })

  it('flagship cars carry their researched prices', () => {
    expect(presetByKey('cayenne_turbo_e').price).toBe(165500)
    expect(presetByKey('brabus_bodo').price).toBe(1200000)
  })

  it('presetByKey falls back to the first preset for unknown keys', () => {
    expect(presetByKey('does-not-exist')).toBe(DREAM_PRESETS[0])
    expect(presetByKey(null)).toBe(DREAM_PRESETS[0])
  })
})

describe('motivation math', () => {
  it('1.000 € equals 1 km of road', () => {
    expect(euroToKm(1000)).toBe(1)
    expect(euroToKm(165500)).toBeCloseTo(165.5)
  })

  it('default assumptions price a call at 225 €', () => {
    // Ø deal 15k € · 30 % savings rate · 20 contacts per win.
    expect(evPerContact(15000, 30, 20)).toBeCloseTo(225)
  })

  it('evPerContact guards against zero/negative inputs', () => {
    expect(evPerContact(15000, 30, 0)).toBe(0)
    expect(evPerContact(15000, 0, 20)).toBe(0)
  })

  it('monthsEarlier converts a windfall into saved calendar time', () => {
    // 3.044 € at 100 €/day ≈ 1 month earlier.
    expect(monthsEarlier(3044, 100)).toBeCloseTo(1, 1)
    expect(monthsEarlier(3044, 0)).toBeNull()
  })

  it('milestones are ordered and end at the key handover (100 %)', () => {
    const ats = DREAM_MILESTONES.map((m) => m.at)
    expect([...ats].sort((a, b) => a - b)).toEqual(ats)
    expect(ats[ats.length - 1]).toBe(1)
  })
})
