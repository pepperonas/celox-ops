import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { aiDiscoverPreview } from '../../api/rainmaker'
import type { AiDiscoverResponse } from '../../types'

/**
 * Hält den Zustand eines KI-Lead-Suchlaufs AUSSERHALB des Dialogs, damit er das
 * Schließen (Minimieren) des Dialogs überlebt: der Request läuft im Hintergrund
 * weiter, der Dialog kann sich bei Fertigstellung wieder öffnen. Wird in Pipeline
 * instanziiert (bleibt dort gemountet, während der Dialog kommt/geht).
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
  run: () => Promise<void>
  reset: () => void
}

export function useAiLeadRun(): AiLeadRun {
  const [brief, setBrief] = useState('')
  const [useWeb, setUseWeb] = useState(false)
  const [running, setRunning] = useState(false)
  const [ranWeb, setRanWeb] = useState(false)
  const [res, setRes] = useState<AiDiscoverResponse | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [phase, setPhase] = useState(0)
  const startRef = useRef(0)

  // Fortschritts-Stufen (die letzte hält, bis die Antwort da ist).
  const phaseLabels = ranWeb
    ? ['Brief analysieren', 'OSM + Web durchsuchen', 'Websites & E-Mails prüfen', 'Fit-Bewertung durch Claude']
    : ['Brief analysieren', 'Firmen in OpenStreetMap suchen', 'Websites & E-Mails prüfen', 'Fit-Bewertung durch Claude']

  useEffect(() => {
    if (!running) return
    const id = setInterval(() => {
      const s = Math.floor((Date.now() - startRef.current) / 1000)
      setElapsed(s)
      // grobe Zeit-Schätzung; Web dauert länger, letzte Stufe hält bis Ergebnis
      const t = ranWeb ? [3, 30, 45] : [2, 8, 14]
      setPhase(s < t[0] ? 0 : s < t[1] ? 1 : s < t[2] ? 2 : 3)
    }, 400)
    return () => clearInterval(id)
  }, [running, ranWeb])

  const run = useCallback(async () => {
    if (!brief.trim() || running) return
    setRanWeb(useWeb)
    setRunning(true); setRes(null); setElapsed(0); setPhase(0)
    startRef.current = Date.now()
    try {
      const r = await aiDiscoverPreview(brief.trim(), useWeb)
      setRes(r)
      if (r.candidates.length === 0) toast('Keine passenden Treffer.', { icon: '🔍' })
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: string } } }
      toast.error(e?.response?.data?.detail || 'KI-Suche fehlgeschlagen.')
    } finally {
      setRunning(false)
    }
  }, [brief, running, useWeb])

  const reset = useCallback(() => {
    setRes(null); setBrief(''); setElapsed(0); setPhase(0)
  }, [])

  return { brief, setBrief, useWeb, setUseWeb, running, ranWeb, res, elapsed, phase, phaseLabels, run, reset }
}
