import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { completeActivity } from '../../api/rainmaker'
import type {
  RainmakerActivity,
  RainmakerActivityType,
  RainmakerLead,
  RainmakerLeadStatus,
  RainmakerOutcome,
} from '../../types'
import { ACTIVITY_TYPE_LABELS, OUTCOME_LABELS } from './constants'

interface Props {
  activity: RainmakerActivity
  leadCompany: string
  onClose: () => void
  onCompleted: (lead: RainmakerLead) => void
}

const TYPE_OPTIONS = Object.keys(ACTIVITY_TYPE_LABELS) as RainmakerActivityType[]
const OUTCOME_OPTIONS = Object.keys(OUTCOME_LABELS) as RainmakerOutcome[]
const CLOSE_OPTIONS: { value: RainmakerLeadStatus; label: string }[] = [
  { value: 'won', label: 'Gewonnen 🎉' },
  { value: 'lost', label: 'Verloren' },
  { value: 'dormant', label: 'Ruhend' },
]

function plusDays(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

/**
 * Next-Action-Zwang: logs an activity as done. The confirm button stays disabled
 * until either a valid next action (type + date) is set OR the lead is closed.
 */
export default function CompleteActionModal({ activity, leadCompany, onClose, onCompleted }: Props) {
  const [outcome, setOutcome] = useState<RainmakerOutcome | ''>('')
  const [notes, setNotes] = useState('')
  const [mode, setMode] = useState<'next' | 'close'>('next')
  const [nextType, setNextType] = useState<RainmakerActivityType>('follow_up')
  const [nextDue, setNextDue] = useState<string>(plusDays(7))
  const [closeStatus, setCloseStatus] = useState<RainmakerLeadStatus>('won')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const canConfirm = mode === 'close' ? Boolean(closeStatus) : Boolean(nextType && nextDue)

  const handleConfirm = async () => {
    if (!canConfirm || saving) return
    setSaving(true)
    try {
      const lead = await completeActivity(activity.id, {
        outcome: outcome || null,
        notes: notes || null,
        ...(mode === 'close'
          ? { close_status: closeStatus }
          : { next_type: nextType, next_due: nextDue }),
      })
      toast.success('Erledigt ✓')
      onCompleted(lead)
    } catch {
      toast.error('Konnte nicht gespeichert werden.')
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={onClose} />
      <div className="relative bg-surface-high rounded-xl shadow-elev-3 p-7 max-w-[460px] w-full mx-4 animate-md-scale max-h-[90vh] overflow-y-auto">
        <h3 className="text-xl font-semibold text-text mb-1">
          {ACTIVITY_TYPE_LABELS[activity.type]} erledigt
        </h3>
        <p className="text-text-muted text-sm mb-5">{leadCompany}</p>

        {/* Outcome */}
        <label className="block text-xs text-text-muted mb-2">Ergebnis</label>
        <div className="flex flex-wrap gap-2 mb-4">
          {OUTCOME_OPTIONS.map((o) => (
            <button
              key={o}
              type="button"
              onClick={() => setOutcome(outcome === o ? '' : o)}
              className={`md-state px-3 h-8 rounded-lg text-xs font-medium transition-all duration-short ease-spring ${
                outcome === o ? 'bg-md-secondary-container text-on-secondary-container' : 'text-text-muted border border-border hover:text-text'
              }`}
            >
              {OUTCOME_LABELS[o]}
            </button>
          ))}
        </div>

        {/* Notes */}
        <label className="block text-xs text-text-muted mb-2">Notiz</label>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className="w-full mb-5" placeholder="Was lief, was wurde besprochen…" />

        {/* Next action vs close — mode toggle */}
        <div className="flex gap-1 p-1 rounded-full bg-surface-container w-fit mb-4">
          <button type="button" onClick={() => setMode('next')} className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-short ${mode === 'next' ? 'bg-md-primary text-on-primary' : 'text-text-muted'}`}>
            Nächster Schritt
          </button>
          <button type="button" onClick={() => setMode('close')} className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-short ${mode === 'close' ? 'bg-md-primary text-on-primary' : 'text-text-muted'}`}>
            Lead abschließen
          </button>
        </div>

        {mode === 'next' ? (
          <div className="grid grid-cols-2 gap-3 mb-2">
            <div>
              <label className="block text-xs text-text-muted mb-2">Aktion</label>
              <select value={nextType} onChange={(e) => setNextType(e.target.value as RainmakerActivityType)} className="w-full">
                {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{ACTIVITY_TYPE_LABELS[t]}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-2">Wiedervorlage</label>
              <input type="date" value={nextDue} onChange={(e) => setNextDue(e.target.value)} className="w-full" />
            </div>
          </div>
        ) : (
          <div className="mb-2">
            <label className="block text-xs text-text-muted mb-2">Abschluss-Status</label>
            <select value={closeStatus} onChange={(e) => setCloseStatus(e.target.value as RainmakerLeadStatus)} className="w-full">
              {CLOSE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <p className="text-xs text-text-muted mt-2">Abgeschlossene Leads brauchen keinen nächsten Schritt.</p>
          </div>
        )}

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="btn-secondary" disabled={saving}>Abbrechen</button>
          <button onClick={handleConfirm} className="btn-primary" disabled={!canConfirm || saving}>
            {saving ? 'Speichern…' : 'Erledigt'}
          </button>
        </div>
      </div>
    </div>
  )
}
