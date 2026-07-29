import { describe, expect, it } from 'vitest'
import { ICON_NAMES, ICONS, type IconEl } from './catalog'

/**
 * Der Icon-Satz wird gerechnet, nicht begutachtet.
 *
 * Material-Systemikonen sitzen auf 24×24 mit 2 dp Rand — die Zeichnung muss also
 * in der Live-Area 2…22 liegen. Faellt ein Icon heraus, wirkt es neben den
 * anderen zu gross oder wird an Kanten beschnitten; das faellt im Blick kaum auf,
 * hier aber sofort.
 */
const LIVE_MIN = 2
const LIVE_MAX = 22

/** Alle Koordinaten eines Elements — Pfade werden geparst, Formen gerechnet. */
function coords(el: IconEl): { xs: number[]; ys: number[] } {
  if (el.t === 'c') {
    return { xs: [el.cx - el.r, el.cx + el.r], ys: [el.cy - el.r, el.cy + el.r] }
  }
  if (el.t === 'l') return { xs: [el.x1, el.x2], ys: [el.y1, el.y2] }
  if (el.t === 'r') return { xs: [el.x, el.x + el.w], ys: [el.y, el.y + el.h] }

  // Pfad: Zahlenpaare einsammeln. Arc-Kommandos (A rx ry rot laf sf x y) tragen
  // vor dem Zielpunkt fuenf Parameter, die keine Koordinaten sind — die werden
  // uebersprungen, sonst melden Radien falsche Ausreisser.
  const xs: number[] = []
  const ys: number[] = []
  const tokens = el.d.match(/[A-Za-z]|-?\d*\.?\d+/g) || []
  let cmd = ''
  let buf: number[] = []
  const flush = () => {
    if (cmd === 'A' || cmd === 'a') {
      for (let i = 0; i + 6 < buf.length + 1; i += 7) {
        if (buf[i + 5] !== undefined) { xs.push(buf[i + 5]); ys.push(buf[i + 6]) }
      }
    } else if (cmd === 'H' || cmd === 'h') {
      buf.forEach((n) => xs.push(n))
    } else if (cmd === 'V' || cmd === 'v') {
      buf.forEach((n) => ys.push(n))
    } else {
      for (let i = 0; i + 1 < buf.length; i += 2) { xs.push(buf[i]); ys.push(buf[i + 1]) }
    }
    buf = []
  }
  for (const tok of tokens) {
    if (/[A-Za-z]/.test(tok)) { flush(); cmd = tok } else { buf.push(Number(tok)) }
  }
  flush()
  return { xs, ys }
}

describe('Icon-Katalog', () => {
  it('enthaelt Icons', () => {
    expect(ICON_NAMES.length).toBeGreaterThan(30)
  })

  it('jede Zeichnung bleibt in der Live-Area 2…22', () => {
    const outside: string[] = []
    for (const name of ICON_NAMES) {
      const def = ICONS[name]
      for (const variant of [def.outline, def.solid || []]) {
        for (const el of variant) {
          const { xs, ys } = coords(el)
          for (const n of [...xs, ...ys]) {
            if (n < LIVE_MIN - 0.001 || n > LIVE_MAX + 0.001) {
              outside.push(`${name}: ${n}`)
            }
          }
        }
      }
    }
    expect(outside).toEqual([])
  })

  it('jede Zeichnung nutzt die Live-Area auch aus', () => {
    // Ein Icon, das nur die Mitte bemalt, wirkt neben den anderen zu klein.
    const tooSmall: string[] = []
    for (const name of ICON_NAMES) {
      const all = ICONS[name].outline.flatMap((el) => {
        const { xs, ys } = coords(el)
        return [{ xs, ys }]
      })
      const xs = all.flatMap((a) => a.xs)
      const ys = all.flatMap((a) => a.ys)
      const w = Math.max(...xs) - Math.min(...xs)
      const h = Math.max(...ys) - Math.min(...ys)
      if (Math.max(w, h) < 14) tooSmall.push(`${name}: ${w.toFixed(1)}×${h.toFixed(1)}`)
    }
    expect(tooSmall).toEqual([])
  })

  it('ist ungefaehr zentriert (kein Icon klebt an einer Kante)', () => {
    const off: string[] = []
    for (const name of ICON_NAMES) {
      const all = ICONS[name].outline.map(coords)
      const xs = all.flatMap((a) => a.xs)
      const ys = all.flatMap((a) => a.ys)
      const cx = (Math.max(...xs) + Math.min(...xs)) / 2
      const cy = (Math.max(...ys) + Math.min(...ys)) / 2
      if (Math.abs(cx - 12) > 2.2 || Math.abs(cy - 12) > 2.2) {
        off.push(`${name}: Mitte ${cx.toFixed(1)}/${cy.toFixed(1)}`)
      }
    }
    expect(off).toEqual([])
  })

  it('Namen sind eindeutig und in camelCase', () => {
    expect(new Set(ICON_NAMES).size).toBe(ICON_NAMES.length)
    const bad = ICON_NAMES.filter((n) => !/^[a-z][a-zA-Z]*$/.test(n))
    expect(bad).toEqual([])
  })

  it('kein Icon ist leer', () => {
    const empty = ICON_NAMES.filter((n) => ICONS[n].outline.length === 0)
    expect(empty).toEqual([])
  })

  it('keine A-Boegen — sonst waere die Rasterpruefung unsicher', () => {
    // Bei einem Bogen (A) liegt der Scheitel NICHT in den Koordinaten des
    // Pfades; die Bounding-Box oben wuerde ein Ausbrechen also gar nicht sehen.
    // Bei Bezier-Kurven liegt die Kurve garantiert in der konvexen Huelle ihrer
    // Kontrollpunkte — damit ist die Pruefung eine echte Schranke.
    const withArc: string[] = []
    for (const name of ICON_NAMES) {
      for (const el of [...ICONS[name].outline, ...(ICONS[name].solid || [])]) {
        if (el.t === 'p' && /[Aa]\s*[\d.]/.test(el.d)) withArc.push(name)
      }
    }
    expect(withArc).toEqual([])
  })

  it('Pfade sind syntaktisch plausibel', () => {
    const broken: string[] = []
    for (const name of ICON_NAMES) {
      for (const el of [...ICONS[name].outline, ...(ICONS[name].solid || [])]) {
        if (el.t !== 'p') continue
        if (!/^[Mm]/.test(el.d.trim())) broken.push(`${name}: beginnt nicht mit M`)
        if (/[^MmLlHhVvCcSsQqTtAaZz0-9.,\-\s]/.test(el.d)) {
          broken.push(`${name}: unerlaubtes Zeichen`)
        }
      }
    }
    expect(broken).toEqual([])
  })

  it('Zustands-Icons haben eine gefuellte Fassung', () => {
    // Diese tragen einen Zustand (Favorit, gepinnt, aktiv) und brauchen den
    // fill-Wechsel — ohne ihn waere der Zustand nur farblich sichtbar.
    for (const name of ['star', 'pin', 'flame', 'spark'] as const) {
      expect(ICONS[name].solid, `${name} braucht eine solid-Fassung`).toBeTruthy()
    }
  })
})
