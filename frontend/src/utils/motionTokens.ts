// Die Bewegungs-Token als JavaScript — Gegenstück zu `:root` in index.css.
//
// **Warum es diese Datei geben MUSS.** Die Web Animations API und damit auch
// motion.dev akzeptieren keine CSS-Custom-Property als Easing. Genau daran ist in
// diesem Repo schon einmal etwas kaputtgegangen (der Long-Press im
// disco-controller warf, weil `easing: var(--m3-effect-default)` übergeben wurde,
// und der Zustand wurde nie gespeichert). Die Regel lautet seitdem: in JS nur
// literale Werte. Diese Datei ist der eine Ort, an dem sie stehen.
//
// Die Werte sind aus `index.css` übernommen, nicht neu erfunden — ein Test
// (`motionTokens.test.ts`) liest die CSS-Datei und schlägt Alarm, wenn beide
// auseinanderlaufen. Ohne den Test wäre eine zweite Wahrheit entstanden, und die
// App hätte sich an CSS- und JS-Stellen unterschiedlich bewegt.
//
// **Arbeitsteilung der beiden Bibliotheken** (verbindlich, s.
// `.claude/rules/frontend-m3e.md`):
//   motion.dev — alles, was an React-Zustand oder Layout hängt: `layout`
//                (Umsortieren), `AnimatePresence` (Ein-/Austritt), Springs.
//   anime.js   — ereignisgesteuerte Einmal-Effekte auf dem DOM: Zahlen-Countup,
//                SVG-Zeichnen, Belohnungs-Impulse.
// Ohne diese Trennung überdecken sich beide fast vollständig und niemand weiß
// mehr, womit die nächste Animation gebaut wird.

/** Dauern in Millisekunden — Spiegel von `--m3-*-dur`. */
export const DUR = {
  spatialFast: 350,
  spatialDefault: 500,
  spatialSlow: 650,
  effectFast: 150,
  effectDefault: 200,
  effectSlow: 300,
} as const

/** Easing-Kurven — Spiegel von `--m3-*`. Literale, nie CSS-Vars (s. oben). */
export const EASE = {
  spatialFast: [0.42, 1.67, 0.21, 0.90],
  spatialDefault: [0.38, 1.21, 0.22, 1.00],
  spatialSlow: [0.39, 1.29, 0.35, 0.98],
  effectFast: [0.31, 0.94, 0.34, 1.00],
  effectDefault: [0.34, 0.80, 0.34, 1.00],
  effectSlow: [0.34, 0.88, 0.34, 1.00],
} as const

/** Als CSS-Zeichenkette, für anime.js und `element.animate()`. */
export function cubic(kurve: readonly number[]): string {
  return `cubic-bezier(${kurve.join(', ')})`
}

/**
 * motion.dev-Übergänge, benannt wie die Token-Matrix.
 *
 * Bewusst `ease` + `duration` statt motions eigener Feder-Physik: Die App bewegt
 * sich zu 95 % über CSS-Transitions mit genau diesen Kurven. Nutzte JS eine andere
 * Physik, sähe dieselbe Geste an zwei Stellen unterschiedlich aus — das fällt
 * niemandem einzeln auf und wirkt zusammen unruhig.
 */
export const T = {
  /** Kleine Elemente: Chips, Sterne, Badges. */
  spatialFast: { duration: DUR.spatialFast / 1000, ease: EASE.spatialFast },
  /** Karten-Transform, Umsortieren, Auf-/Zuklappen. */
  spatialDefault: { duration: DUR.spatialDefault / 1000, ease: EASE.spatialDefault },
  /** Farbe, Deckkraft — nie federn. */
  effectFast: { duration: DUR.effectFast / 1000, ease: EASE.effectFast },
  effectDefault: { duration: DUR.effectDefault / 1000, ease: EASE.effectDefault },
} as const

/**
 * Harter Riegel: Will der Nutzer keine Bewegung, gibt es keine.
 *
 * `index.css` schaltet am Ende ALLE CSS-Animationen unter
 * `prefers-reduced-motion` ab. JS-Animationen erreicht diese Regel nicht — sie
 * müssen selbst fragen. Ohne das wäre die neue Bewegung die einzige in der App,
 * die sich über die Systemeinstellung hinwegsetzt.
 *
 * Defensiv gegen fehlendes `matchMedia` (Testumgebung, alte Browser): dort wird
 * nicht reduziert, weil „keine Angabe" nicht „bitte keine Bewegung" heißt.
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
