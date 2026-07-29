import { describe, expect, it } from 'vitest'
import { cubic, EASE, prefersReducedMotion, T } from './motionTokens'
/**
 * Hier stehen nur die JS-Invarianten. Der Vergleich MIT der CSS-Datei läuft in
 * `scripts/check-motion-tokens.mjs` (als `pretest`, also bei jedem `npm test`):
 * Vitest ersetzt CSS-Importe durch einen leeren String, auch mit `?raw` —
 * nachgemessen, Länge 0. Ein Test darüber wäre still grün gewesen und hätte
 * nichts geprüft, und das ist schlimmer als kein Test.
 */

describe('cubic', () => {
  it('baut eine gültige CSS-Zeichenkette', () => {
    expect(cubic([0.1, 0.2, 0.3, 0.4])).toBe('cubic-bezier(0.1, 0.2, 0.3, 0.4)')
  })
})

describe('motion-Übergänge', () => {
  it('Dauer in Sekunden — motion rechnet nicht in Millisekunden', () => {
    // Der klassische Fehler: 500 statt 0.5 übergeben und eine Animation bekommt
    // achteinhalb Minuten. Fällt in der Entwicklung sofort auf, aber nur, wenn man
    // hinsieht.
    expect(T.spatialDefault.duration).toBeCloseTo(0.5)
    expect(T.effectFast.duration).toBeCloseTo(0.15)
    for (const t of Object.values(T)) {
      expect(t.duration).toBeLessThan(1)
      expect(t.duration).toBeGreaterThan(0)
    }
  })

  it('Effects-Kurven schwingen nicht über', () => {
    // Farbe und Deckkraft dürfen nie federn (M3E-Regel): der zweite
    // Kontrollpunkt muss ≤ 1 bleiben, sonst gibt es einen Überschwung.
    for (const name of ['effectFast', 'effectDefault', 'effectSlow'] as const) {
      expect(EASE[name][1]).toBeLessThanOrEqual(1)
    }
  })

  it('Spatial-Kurven schwingen über — das ist der Punkt', () => {
    for (const name of ['spatialFast', 'spatialDefault', 'spatialSlow'] as const) {
      expect(EASE[name][1]).toBeGreaterThan(1)
    }
  })
})

describe('prefersReducedMotion', () => {
  it('ohne matchMedia wird NICHT reduziert', () => {
    // „keine Angabe" heißt nicht „bitte keine Bewegung". In der Testumgebung gibt
    // es kein matchMedia — ein Absturz hier würde jede Animation lahmlegen.
    expect(prefersReducedMotion()).toBe(false)
  })

  it('liest die Systemeinstellung, wenn es sie gibt', () => {
    // Die Suite läuft in der Node-Umgebung, es gibt also kein `window`. Deshalb
    // wird eines gestellt statt eines vorhandenen verbogen — der erste Fall oben
    // prüft ja gerade, dass die Funktion ohne `window` nicht abstürzt.
    const vorher = (globalThis as Record<string, unknown>).window
    ;(globalThis as Record<string, unknown>).window = {
      matchMedia: (q: string) => ({ matches: q.includes('reduce') }),
    }
    try {
      expect(prefersReducedMotion()).toBe(true)
    } finally {
      if (vorher === undefined) delete (globalThis as Record<string, unknown>).window
      else (globalThis as Record<string, unknown>).window = vorher
    }
  })

  it('respektiert ein ausdrückliches „keine Reduktion"', () => {
    const vorher = (globalThis as Record<string, unknown>).window
    ;(globalThis as Record<string, unknown>).window = { matchMedia: () => ({ matches: false }) }
    try {
      expect(prefersReducedMotion()).toBe(false)
    } finally {
      if (vorher === undefined) delete (globalThis as Record<string, unknown>).window
      else (globalThis as Record<string, unknown>).window = vorher
    }
  })
})
