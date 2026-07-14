// Zeitfilter für die Pipeline — reine, testbare Helfer (keine DOM-/Date.now-Abhängigkeit:
// `nowMs` wird injiziert, damit die Fenster deterministisch testbar sind).

export type TimeField = 'created' | 'updated'
export type TimePreset =
  | 'all' | '15m' | '1h' | 'today' | '24h' | '7d' | 'lastImport' | 'custom'

export interface TimeWindow {
  from: number | null   // ms (inklusive), null = unbegrenzt
  to: number | null     // ms (inklusive), null = unbegrenzt
}

const MIN = 60_000
const HOUR = 3_600_000
const DAY = 86_400_000

/** Fenster für die Relativ-/Custom-Presets. `lastImport` wird separat berechnet. */
export function presetWindow(
  preset: TimePreset, nowMs: number,
  customFrom?: string | null, customTo?: string | null,
): TimeWindow {
  switch (preset) {
    case '15m': return { from: nowMs - 15 * MIN, to: null }
    case '1h': return { from: nowMs - HOUR, to: null }
    case '24h': return { from: nowMs - 24 * HOUR, to: null }
    case '7d': return { from: nowMs - 7 * DAY, to: null }
    case 'today': {
      const d = new Date(nowMs)
      d.setHours(0, 0, 0, 0)             // lokale Mitternacht
      return { from: d.getTime(), to: null }
    }
    case 'custom': return {
      from: customFrom ? new Date(customFrom).getTime() : null,
      to: customTo ? new Date(customTo).getTime() : null,
    }
    default: return { from: null, to: null }   // 'all' / 'lastImport'
  }
}

/**
 * Erkennt das jüngste „Import-Fenster": nimmt den neuesten Zeitstempel und
 * dehnt das Fenster rückwärts aus, solange die Lücke zum nächstälteren ≤ gapMs
 * ist (Importe legen viele Leads binnen Sekunden/Minuten an). Ergebnis: von
 * Burst-Beginn (minus 1 s Puffer) bis offen.
 */
export function detectLastImportWindow(
  timestamps: number[], _nowMs: number, gapMs: number = 5 * MIN,
): TimeWindow {
  const sorted = timestamps.filter((t) => Number.isFinite(t)).sort((a, b) => b - a)
  if (sorted.length === 0) return { from: null, to: null }
  let burstStart = sorted[0]
  for (let i = 1; i < sorted.length; i++) {
    if (burstStart - sorted[i] <= gapMs) burstStart = sorted[i]
    else break
  }
  return { from: burstStart - 1000, to: null }
}

export function inWindow(ts: number, w: TimeWindow): boolean {
  const bounded = w.from != null || w.to != null
  if (Number.isNaN(ts)) return !bounded         // ungültiger Zeitstempel: nur bei „Alle" sichtbar
  if (w.from != null && ts < w.from) return false
  if (w.to != null && ts > w.to) return false
  return true
}

/** ISO-/Datumsstring → ms; NaN-sicher (ungültig → NaN, per inWindow ausgefiltert). */
export function toMs(value: string | null | undefined): number {
  return value ? new Date(value).getTime() : NaN
}
