import { describe, it, expect } from 'vitest'
import { presetWindow, detectLastImportWindow, inWindow, toMs } from './timeFilter'

const NOW = 1_800_000_000_000  // fester Referenzzeitpunkt (ms)

describe('presetWindow', () => {
  it('relative Fenster sind now - delta, offen nach oben', () => {
    expect(presetWindow('15m', NOW)).toEqual({ from: NOW - 900_000, to: null })
    expect(presetWindow('1h', NOW)).toEqual({ from: NOW - 3_600_000, to: null })
    expect(presetWindow('24h', NOW)).toEqual({ from: NOW - 86_400_000, to: null })
    expect(presetWindow('7d', NOW)).toEqual({ from: NOW - 604_800_000, to: null })
  })
  it('all/lastImport = unbegrenzt', () => {
    expect(presetWindow('all', NOW)).toEqual({ from: null, to: null })
    expect(presetWindow('lastImport', NOW)).toEqual({ from: null, to: null })
  })
  it('today beginnt an lokaler Mitternacht ≤ now', () => {
    const w = presetWindow('today', NOW)
    expect(w.from).not.toBeNull()
    expect(w.from!).toBeLessThanOrEqual(NOW)
    expect(w.to).toBeNull()
  })
  it('custom nutzt beide Grenzen (leer = null)', () => {
    const w = presetWindow('custom', NOW, '2026-01-01T10:00', '2026-01-02T12:30')
    expect(w.from).toBe(new Date('2026-01-01T10:00').getTime())
    expect(w.to).toBe(new Date('2026-01-02T12:30').getTime())
    expect(presetWindow('custom', NOW, null, null)).toEqual({ from: null, to: null })
  })
})

describe('detectLastImportWindow', () => {
  it('greift den jüngsten Burst (Lücke trennt)', () => {
    const t = [
      NOW - 10_000, NOW - 20_000, NOW - 30_000,     // frischer Burst (eng)
      NOW - 3 * 3_600_000,                          // >gap davor → getrennt
      NOW - 4 * 3_600_000,
    ]
    const w = detectLastImportWindow(t, NOW)
    expect(w.from).toBe(NOW - 30_000 - 1000)        // Burst-Beginn minus 1s Puffer
    expect(w.to).toBeNull()
  })
  it('leere Liste → unbegrenzt', () => {
    expect(detectLastImportWindow([], NOW)).toEqual({ from: null, to: null })
  })
  it('ein Zeitstempel → Fenster ab diesem', () => {
    expect(detectLastImportWindow([NOW - 5000], NOW).from).toBe(NOW - 5000 - 1000)
  })
})

describe('inWindow', () => {
  it('respektiert beide Grenzen inklusiv', () => {
    expect(inWindow(50, { from: 10, to: 100 })).toBe(true)
    expect(inWindow(5, { from: 10, to: 100 })).toBe(false)
    expect(inWindow(150, { from: 10, to: 100 })).toBe(false)
    expect(inWindow(50, { from: null, to: null })).toBe(true)
  })
  it('NaN (ungültiger Zeitstempel) fällt raus, sobald eine Grenze gesetzt ist', () => {
    expect(inWindow(NaN, { from: 10, to: null })).toBe(false)
  })
})

describe('toMs', () => {
  it('parst ISO, leer → NaN', () => {
    expect(toMs('2026-01-01T00:00:00Z')).toBe(Date.parse('2026-01-01T00:00:00Z'))
    expect(Number.isNaN(toMs(null))).toBe(true)
  })
})
