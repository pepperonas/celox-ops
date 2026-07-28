import { useLayoutEffect, useRef } from 'react'
import { flipDeltas } from './listOrder'

/**
 * FLIP: Zeilen gleiten an ihre neue Position statt zu springen.
 *
 * Vor dem Zeichnen werden die alten Positionen gemessen, danach die neuen; die
 * Differenz wird als Startversatz animiert. Angesprochen werden Elemente mit
 * `data-flip-id` innerhalb von `containerRef`.
 *
 * `orderKey` sagt, wann sich die Reihenfolge geändert haben KANN (z. B. die
 * verketteten IDs). Ändert er sich nicht, wird nichts animiert.
 *
 * Zwei Regeln aus dem Repo-Kanon sind hier wichtig:
 * - **Bewegung ist „spatial"** → Dauer/Kurve entsprechen `--m3-spatial-default`.
 * - In `element.animate()` darf die Easing **keine CSS-Custom-Property** sein
 *   (die Web Animations API akzeptiert das nicht und wirft) — deshalb steht die
 *   Kurve hier als Literal, spiegelbildlich zum Token in `index.css`.
 */
const SPATIAL_DEFAULT = 'cubic-bezier(0.2, 0, 0, 1)'   // = --m3-spatial-default
const SPATIAL_DURATION = 500                            // = --m3-spatial-default-dur

export function useFlipOrder(
  containerRef: React.RefObject<HTMLElement>,
  orderKey: string,
): void {
  const positions = useRef<Map<string, number>>(new Map())
  const lastKey = useRef<string>('')

  useLayoutEffect(() => {
    const root = containerRef.current
    if (!root) return

    const measure = () => {
      const map = new Map<string, number>()
      // Relativ zum Container messen, NICHT zum Viewport: zwischen zwei
      // Messungen kann gescrollt werden (das Auftau-Fenster ist über eine
      // Sekunde lang), und viewport-relative Werte hätten dann einen Versatz,
      // der als Positionswechsel missverstanden würde — jede Zeile würde
      // grundlos animieren.
      const base = root.getBoundingClientRect().top
      root.querySelectorAll<HTMLElement>('[data-flip-id]').forEach((el) => {
        map.set(el.dataset.flipId as string, el.getBoundingClientRect().top - base)
      })
      return map
    }

    const next = measure()
    const changed = lastKey.current !== '' && lastKey.current !== orderKey
    lastKey.current = orderKey

    const reduced = typeof window !== 'undefined'
      && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (changed && !reduced) {
      for (const { id, delta } of flipDeltas(positions.current, next)) {
        const el = root.querySelector<HTMLElement>(`[data-flip-id="${id}"]`)
        // `animate` kann in Testumgebungen fehlen — nie daran scheitern.
        el?.animate?.(
          [{ transform: `translateY(${delta}px)` }, { transform: 'none' }],
          { duration: SPATIAL_DURATION, easing: SPATIAL_DEFAULT },
        )
      }
    }
    positions.current = next
  }, [containerRef, orderKey])
}
