import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useAppNavigate } from '../utils/transitions'
import { useAiLeadStore } from '../store/aiLeadStore'
import AiLeadModal from '../pages/rainmaker/AiLeadModal'
import AiLeadPill from '../pages/rainmaker/AiLeadPill'
import { aiPhaseLabels, aiPhaseFor, type AiLeadRun } from '../pages/rainmaker/aiLeadRun'

/**
 * Immer-gemounteter Host der globalen KI-Lead-Suche (in Layout, neben QuickSearch).
 * Rendert den Dialog (nur auf /pipeline) bzw. die minimierte Pill (auf jeder Seite)
 * und besitzt den Fortschritts-Timer. Der Suchzustand selbst lebt im Store und
 * überlebt so Dialog-Schließen UND Seitenwechsel.
 */
export default function AiLeadHost() {
  const store = useAiLeadStore()
  const navigate = useAppNavigate()
  const onPipeline = useLocation().pathname.startsWith('/pipeline')
  const [elapsed, setElapsed] = useState(0)

  // Timer läuft im immer-gemounteten Host → elapsed/phase aktualisieren, egal wo.
  useEffect(() => {
    if (!store.running || !store.startedAt) return
    const startedAt = store.startedAt
    const tick = () => setElapsed(Math.floor((Date.now() - startedAt) / 1000))
    tick()
    const id = setInterval(tick, 400)
    return () => clearInterval(id)
  }, [store.running, store.startedAt])

  const run: AiLeadRun = {
    brief: store.brief,
    setBrief: store.setBrief,
    useWeb: store.useWeb,
    setUseWeb: store.setUseWeb,
    running: store.running,
    ranWeb: store.ranWeb,
    res: store.res,
    elapsed,
    phase: aiPhaseFor(elapsed, store.ranWeb),
    phaseLabels: aiPhaseLabels(store.ranWeb),
    run: store.run,
    reset: store.reset,
  }

  const showModal = store.open && onPipeline
  const showPill = !showModal && (store.running || store.res != null)

  const openHere = () => {
    store.setOpen(true)
    if (!onPipeline) navigate('/pipeline')
  }

  return (
    <>
      {showModal && (
        <AiLeadModal
          run={run}
          onClose={store.close}
          onDiscard={store.discard}
          onImported={(created) => store.notifyImported(created)}
        />
      )}
      {showPill && (
        <AiLeadPill
          run={run}
          count={store.res?.candidates.length}
          onOpen={openHere}
          onDiscard={store.discard}
        />
      )}
    </>
  )
}
