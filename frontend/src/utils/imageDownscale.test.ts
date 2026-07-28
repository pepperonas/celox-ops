import { describe, it, expect } from 'vitest'
import { fitWithin, isAcceptedImage, MAX_EDGE_PX, ACCEPTED_TYPES } from './imageDownscale'

describe('fitWithin', () => {
  it('laesst kleine Bilder unangetastet (kein Vergroessern)', () => {
    expect(fitWithin(800, 600)).toEqual({ width: 800, height: 600 })
    expect(fitWithin(MAX_EDGE_PX, 900)).toEqual({ width: MAX_EDGE_PX, height: 900 })
  })

  it('skaliert die lange Kante auf den Deckel, Seitenverhaeltnis bleibt', () => {
    const r = fitWithin(3024, 4032)          // iPhone-Screenshot, hochkant
    expect(r.height).toBe(MAX_EDGE_PX)
    expect(r.width).toBe(Math.round(3024 * (MAX_EDGE_PX / 4032)))
    expect(r.width / r.height).toBeCloseTo(3024 / 4032, 2)
  })

  it('funktioniert quer und quadratisch', () => {
    expect(fitWithin(4000, 2000).width).toBe(MAX_EDGE_PX)
    expect(fitWithin(4000, 2000).height).toBe(784)
    expect(fitWithin(3000, 3000)).toEqual({ width: MAX_EDGE_PX, height: MAX_EDGE_PX })
  })

  it('faellt nie unter 1 px und vertraegt 0', () => {
    expect(fitWithin(10000, 1).height).toBeGreaterThanOrEqual(1)
    expect(fitWithin(0, 0)).toEqual({ width: 0, height: 0 })
  })
})

describe('isAcceptedImage', () => {
  it('nimmt die Formate, die auch der Server erlaubt', () => {
    for (const type of ACCEPTED_TYPES) {
      expect(isAcceptedImage({ type } as File)).toBe(true)
    }
  })

  it('lehnt anderes ab (PDF, HEIC — Claude kann sie nicht als Bild lesen)', () => {
    expect(isAcceptedImage({ type: 'application/pdf' } as File)).toBe(false)
    expect(isAcceptedImage({ type: 'image/heic' } as File)).toBe(false)
    expect(isAcceptedImage({ type: '' } as File)).toBe(false)
  })
})
