// Stand der automatischen Website-Analyse als dezente Pille in der Pipeline.
// Pollt nur, solange etwas offen ist (bzw. alle 60 s zur Wiederaufnahme) — der
// Worker läuft im Backend, die UI muss ihn nicht antreiben.
import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { enqueueMissingAnalyses, getAnalysisQueue } from '../../api/rainmaker'
import type { AnalysisQueueStatus } from '../../types'
import Icon from '../../components/Icon'

const FAST_MS = 8000
const SLOW_MS = 60000

export default function AnalysisQueueBadge({ onFinished }: { onFinished?: () => void }) {
  const [status, setStatus] = useState<AnalysisQueueStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const prevPending = useRef(0)

  const load = useCallback(async () => {
    try {
      const s = await getAnalysisQueue()
      setStatus(s)
      // Beim Übergang „lief → fertig" die Liste einmal neu laden lassen, damit
      // die frischen Web-Scores auf den Karten auftauchen.
      if (prevPending.current > 0 && s.pending === 0) onFinished?.()
      prevPending.current = s.pending
    } catch {
      /* stiller Fehler — die Pille ist Zusatzinfo, kein Kernfeature */
    }
  }, [onFinished])

  useEffect(() => {
    load()
    const pending = status?.pending ?? 0
    const id = window.setInterval(load, pending > 0 ? FAST_MS : SLOW_MS)
    return () => window.clearInterval(id)
  }, [load, status?.pending])

  const enqueue = async () => {
    if (busy) return
    setBusy(true)
    try {
      const r = await enqueueMissingAnalyses()
      toast.success(r.queued > 0
        ? `${r.queued} Website${r.queued === 1 ? '' : 's'} zur Analyse eingereiht${r.capped ? ' (gedeckelt)' : ''}.`
        : 'Alle Leads mit Website sind bereits analysiert.')
      await load()
    } catch {
      toast.error('Einreihen fehlgeschlagen.')
    } finally {
      setBusy(false)
    }
  }

  if (!status) return null
  const pending = status.pending

  if (pending > 0) {
    return (
      <span
        className="inline-flex items-center gap-1.5 text-xs text-text-muted px-2 py-1 rounded-full bg-surface-container"
        title={`Automatische Website-Analyse: ${status.running} laufend, ${status.queued} wartend`}
      >
        <span className="inline-block w-3 h-3 rounded-full border-2 border-accent border-t-transparent animate-spin" />
        {pending} Website{pending === 1 ? '' : 's'} in Analyse
      </span>
    )
  }

  return (
    <button
      type="button"
      onClick={enqueue}
      disabled={busy}
      className="inline-flex items-center gap-1.5 text-xs text-text-muted px-2 py-1 rounded-full bg-surface-container md-state disabled:opacity-50"
      title={status.enabled
        ? 'Analysiert alle Leads mit Website, die noch keine Analyse haben (kostenlos).'
        : 'Auto-Analyse ist in den Einstellungen aus — hier trotzdem einmalig nachziehen.'}
    ><Icon name="globe" size={16} className="mr-1 -mt-0.5" /> {busy ? 'reiht ein…' : 'Websites analysieren'}
      {status.error > 0 && (
        <span className="text-danger" title={`${status.error} Analyse(n) fehlgeschlagen`}>
          · <Icon name="warning" size={13} className="ml-0.5" />{status.error}
        </span>
      )}
    </button>
  )
}
