import { describe, expect, it } from 'vitest'

/**
 * Wächter: keine Emojis in der Oberfläche.
 *
 * Emojis sind Schrift, keine Icons — sie ignorieren die Theme-Tokens, sehen je
 * Betriebssystem anders aus, tragen kein Raster und werden vom Screenreader mit
 * ihrem Unicode-Namen vorgelesen. Der Satz in `catalog.ts` ersetzt sie; damit das
 * so bleibt, prüft dieser Test den Quellcode.
 *
 * **Bewusst erlaubt:**
 * - Typografische Zeichen im Satz (→ ↑ ✓ ✕ …) — im Fließtext sind das
 *   Schriftzeichen, ein SVG dazwischen bräche die Grundlinie.
 * - Kommentare — dort dokumentieren sie, welches Emoji ein Icon ersetzt hat.
 * - Testdateien — `clipboard.test.ts` benutzt Emojis absichtlich als
 *   Unicode-Prüfmaterial; würde man sie ersetzen, prüfte der Test nichts mehr.
 *
 * Neues Symbol gebraucht? Icon in `catalog.ts` zeichnen (Live-Area 2…22,
 * Strich 2) und über `<Icon name="…" />` benutzen.
 */
/**
 * Quelldateien über Vites `import.meta.glob` einlesen — bewusst ohne `node:fs`,
 * damit der Test keine Node-Typen ins Frontend zieht (`@types/node` wäre eine
 * neue Abhängigkeit nur für einen Wächter).
 */
const FILES = import.meta.glob('/src/**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>

/** Bildzeichen — ohne die typografischen Pfeile/Haken, die Text sein dürfen. */
const PICTOGRAPHS =
  /[\u{1F300}-\u{1FAFF}\u{1F000}-\u{1F2FF}\u{2600}-\u{27BF}\u{FE0F}]/u
/**
 * Zusätzlich verboten: schriftabhängige Glyphen, die als Icon missbraucht wurden
 * (Aufklapp-Dreiecke, Trend-Pfeile, Info-Kreis, Uhr). Dieselbe Fehlerklasse wie
 * Emojis — sie sehen je Schriftart anders aus und tragen kein Raster.
 */
const GLYPHS_AS_ICONS = new Set(['▲', '▼', '▸', '▾', '▴', '▶', '◀', 'ⓘ', 'ℹ', '◷', '⏱'])
const ALLOWED = new Set(['→', '↑', '↓', '↔', '↗', '✓', '✕', '❌', '★', '☆', '·', '…'])

/** Kommentare entfernen — dort sind Emojis Dokumentation, nicht Oberfläche. */
function stripComments(code: string): string {
  return code
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/.*$/gm, '$1')
}

describe('keine Emojis in der Oberflaeche', () => {
  it('kein Quelldatei-Code enthaelt Bildzeichen', () => {
    const offenders: string[] = []
    // Gegenprobe, dass ueberhaupt Dateien gefunden wurden — sonst waere ein
    // gruener Lauf bedeutungslos.
    expect(Object.keys(FILES).length).toBeGreaterThan(100)
    for (const [file, raw] of Object.entries(FILES)) {
      if (/\.test\.tsx?$/.test(file)) continue          // Testfixtures sind erlaubt
      if (file.endsWith('icons/catalog.ts')) continue
      stripComments(raw).split('\n').forEach((line, i) => {
        for (const ch of line) {
          if (ALLOWED.has(ch)) continue
          if (PICTOGRAPHS.test(ch) || GLYPHS_AS_ICONS.has(ch)) {
            offenders.push(`${file}:${i + 1} ${ch}`)
          }
        }
      })
    }
    expect(offenders).toEqual([])
  })

  it('der Wächter greift ueberhaupt', () => {
    // Ohne diese Gegenprobe koennte die Regex still nichts finden und der Test
    // waere ein gruenes Nichts.
    expect(PICTOGRAPHS.test('🔥')).toBe(true)
    expect(PICTOGRAPHS.test('✨')).toBe(true)
    expect(PICTOGRAPHS.test('a')).toBe(false)
    expect(stripComments('// 🔥 nur ein Kommentar')).not.toContain('🔥')
    expect(stripComments('const x = "🔥"')).toContain('🔥')
  })
})
