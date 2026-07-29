#!/usr/bin/env node
/**
 * Drift-Wächter: Die Bewegungs-Token in `src/utils/motionTokens.ts` müssen mit
 * denen in `src/index.css` übereinstimmen.
 *
 * **Warum es zwei Fassungen gibt.** Die Web Animations API — und damit motion.dev
 * und `element.animate()` — akzeptiert keine CSS-Custom-Property als Easing. In
 * diesem Repo ist daran schon einmal etwas kaputtgegangen (Long-Press im
 * disco-controller: `easing: var(--m3-effect-default)` warf, der Zustand wurde
 * nie gespeichert). Seitdem gilt: in JS nur literale Werte. Die JS-Datei ist also
 * zwangsläufig eine Kopie — und eine Kopie ohne Wächter läuft auseinander.
 *
 * **Warum als Skript und nicht als vitest-Test.** Vitest ersetzt CSS-Importe durch
 * einen leeren String, auch mit `?raw` (nachgemessen: Länge 0). Der Test wäre
 * still grün gewesen und hätte nichts geprüft — schlimmer als kein Test. `css:
 * true` in der Konfiguration würde Tailwind bei jedem Lauf mitschleppen; das ist
 * dem einen Vergleich nicht angemessen.
 *
 * Läuft als `pretest`, also bei jedem `npm test`.
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const hier = dirname(fileURLToPath(import.meta.url))
const css = readFileSync(join(hier, '..', 'src', 'index.css'), 'utf8')
const ts = readFileSync(join(hier, '..', 'src', 'utils', 'motionTokens.ts'), 'utf8')

const NAMEN = [
  ['spatial-fast', 'spatialFast'],
  ['spatial-default', 'spatialDefault'],
  ['spatial-slow', 'spatialSlow'],
  ['effect-fast', 'effectFast'],
  ['effect-default', 'effectDefault'],
  ['effect-slow', 'effectSlow'],
]

/** Wert einer CSS-Custom-Property aus der Datei lesen. */
function cssVar(name) {
  const m = css.match(new RegExp(`--${name}:\\s*([^;]+);`))
  return m ? m[1].trim() : null
}

/** Zahl aus dem `DUR`-Block der TypeScript-Datei. */
function jsDur(name) {
  const block = ts.match(/export const DUR = \{([\s\S]*?)\} as const/)
  if (!block) return null
  const m = block[1].match(new RegExp(`${name}:\\s*(\\d+)`))
  return m ? Number(m[1]) : null
}

/** Kurve aus dem `EASE`-Block, als CSS-Zeichenkette. */
function jsEase(name) {
  const block = ts.match(/export const EASE = \{([\s\S]*?)\} as const/)
  if (!block) return null
  const m = block[1].match(new RegExp(`${name}:\\s*\\[([^\\]]+)\\]`))
  if (!m) return null
  const zahlen = m[1].split(',').map((x) => x.trim())
  return `cubic-bezier(${zahlen.join(', ')})`
}

const fehler = []

if (css.length < 1000) fehler.push('index.css wurde nicht gelesen (zu kurz)')
if (!ts.includes('export const EASE')) fehler.push('motionTokens.ts hat keinen EASE-Block')

for (const [cssName, jsName] of NAMEN) {
  const cssDur = cssVar(`m3-${cssName}-dur`)
  const tsDur = jsDur(jsName)
  if (cssDur === null) fehler.push(`--m3-${cssName}-dur fehlt in index.css`)
  else if (tsDur === null) fehler.push(`DUR.${jsName} fehlt in motionTokens.ts`)
  else if (cssDur !== `${tsDur}ms`) {
    fehler.push(`Dauer weicht ab: --m3-${cssName}-dur = ${cssDur}, DUR.${jsName} = ${tsDur}ms`)
  }

  const cssEase = cssVar(`m3-${cssName}`)
  const tsEase = jsEase(jsName)
  if (cssEase === null) fehler.push(`--m3-${cssName} fehlt in index.css`)
  else if (tsEase === null) fehler.push(`EASE.${jsName} fehlt in motionTokens.ts`)
  else if (cssEase !== tsEase) {
    fehler.push(`Kurve weicht ab: --m3-${cssName} = ${cssEase}, EASE.${jsName} = ${tsEase}`)
  }
}

if (fehler.length) {
  console.error('Bewegungs-Token weichen voneinander ab:\n')
  for (const f of fehler) console.error(`  · ${f}`)
  console.error('\nCSS und JS müssen dieselben Werte tragen (s. Kopf dieses Skripts).')
  process.exit(1)
}

console.log(`Bewegungs-Token stimmen überein (${NAMEN.length} Kurven + Dauern).`)
