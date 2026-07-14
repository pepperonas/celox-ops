import type { AiDiscoverResponse } from '../../types'

/**
 * Sicht auf einen KI-Lead-Suchlauf, wie ihn Dialog + Pill konsumieren. Der echte
 * Zustand lebt global in `store/aiLeadStore` (überlebt Seitenwechsel); der Host
 * baut daraus dieses Objekt (elapsed/phase kommen aus seinem Timer).
 */
export interface AiLeadRun {
  brief: string
  setBrief: (v: string) => void
  useWeb: boolean
  setUseWeb: (v: boolean) => void
  running: boolean
  ranWeb: boolean
  res: AiDiscoverResponse | null
  elapsed: number
  phase: number
  phaseLabels: string[]
  run: () => void | Promise<void>
  reset: () => void
}

// Fortschritts-Stufen (die letzte hält, bis die Antwort da ist).
export function aiPhaseLabels(ranWeb: boolean): string[] {
  return ranWeb
    ? ['Brief analysieren', 'OSM + Web durchsuchen', 'Websites & E-Mails prüfen', 'Fit-Bewertung durch Claude']
    : ['Brief analysieren', 'Firmen in OpenStreetMap suchen', 'Websites & E-Mails prüfen', 'Fit-Bewertung durch Claude']
}

// Aktuelle Phase (0–3) aus verstrichenen Sekunden; Web dauert länger.
export function aiPhaseFor(elapsedSec: number, ranWeb: boolean): number {
  const t = ranWeb ? [3, 30, 45] : [2, 8, 14]
  return elapsedSec < t[0] ? 0 : elapsedSec < t[1] ? 1 : elapsedSec < t[2] ? 2 : 3
}
