import { create } from 'zustand'
import toast from 'react-hot-toast'
import { aiDiscoverPreview } from '../api/rainmaker'
import type { AiDiscoverResponse } from '../types'

/**
 * Globaler Zustand der KI-Lead-Suche. Bewusst NICHT an eine Seite gebunden: der
 * Suchlauf überlebt sowohl das Minimieren des Dialogs als auch das Verlassen der
 * Pipeline-Seite. Der `AiLeadHost` (in Layout, immer gemountet) rendert Dialog
 * bzw. Pill daraus. `importedSignal` benachrichtigt die Pipeline, neu zu laden.
 */
interface AiLeadState {
  brief: string
  useWeb: boolean
  running: boolean
  ranWeb: boolean
  res: AiDiscoverResponse | null
  startedAt: number | null
  open: boolean            // Dialog-Intent (sichtbar, sofern man auf /pipeline ist)
  importedSignal: number   // hochgezählt nach erfolgreichem Import
  importedCount: number
  setBrief: (v: string) => void
  setUseWeb: (v: boolean) => void
  setOpen: (v: boolean) => void
  run: () => Promise<void>
  close: () => void
  discard: () => void
  reset: () => void
  notifyImported: (created: number) => void
}

export const useAiLeadStore = create<AiLeadState>((set, get) => ({
  brief: '',
  useWeb: false,
  running: false,
  ranWeb: false,
  res: null,
  startedAt: null,
  open: false,
  importedSignal: 0,
  importedCount: 0,

  setBrief: (v) => set({ brief: v }),
  setUseWeb: (v) => set({ useWeb: v }),
  setOpen: (v) => set({ open: v }),

  run: async () => {
    const { brief, useWeb, running } = get()
    if (!brief.trim() || running) return
    set({ running: true, ranWeb: useWeb, res: null, startedAt: Date.now() })
    try {
      const r = await aiDiscoverPreview(brief.trim(), useWeb)
      set({ res: r, open: true }) // bei Fertigstellung wieder in den Vordergrund
      if (r.candidates.length === 0) toast('Keine passenden Treffer.', { icon: '🔍' })
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: string } } }
      toast.error(e?.response?.data?.detail || 'KI-Suche fehlgeschlagen.')
      set({ open: true })
    } finally {
      set({ running: false })
    }
  },

  // Dialog schließen OHNE Ergebnisverlust: läuft eine Suche ODER liegen Kandidaten
  // vor → nur minimieren (Pill bleibt, Ergebnisse erhalten). Nur ein leerer Dialog
  // (kein Lauf, keine Treffer) wird beim Schließen verworfen. Ergebnisse gezielt
  // wegwerfen geht ausschließlich über discard().
  close: () => {
    const { running, res } = get()
    const hasResults = !!res && res.candidates.length > 0
    set({ open: false })
    if (!running && !hasResults) get().reset()
  },

  // Explizites Verwerfen (Button „Verwerfen" / ✕ an der Pill).
  discard: () => {
    set({ open: false })
    get().reset()
  },

  reset: () => set({ res: null, brief: '', startedAt: null }),

  notifyImported: (created) =>
    set((s) => ({
      importedSignal: s.importedSignal + 1,
      importedCount: created,
      open: false,
      res: null,
      brief: '',
      startedAt: null,
    })),
}))
