import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { createLeadActivity, getRainmakerGoals } from '../../api/rainmaker'
import type { RainmakerActivityType, RainmakerGoal } from '../../types'
import { ACTIVITY_TYPE_LABELS } from './constants'

interface Props {
  leadId: string
  onClose: () => void
  onAdded: () => void
}

const TYPE_OPTIONS = Object.keys(ACTIVITY_TYPE_LABELS) as RainmakerActivityType[]

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

/** Plans a new activity (the lead's next step). */
export default function AddActivityModal({ leadId, onClose, onAdded }: Props) {
  const [type, setType] = useState<RainmakerActivityType>('call')
  const [dueDate, setDueDate] = useState(today())
  const [notes, setNotes] = useState('')
  const [goals, setGoals] = useState<RainmakerGoal[]>([])
  const [goalId, setGoalId] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  useEffect(() => {
    getRainmakerGoals().then((g) => setGoals(g.filter((x) => x.active))).catch(() => {})
  }, [])

  const pickGoal = (id: string) => {
    setGoalId(id)
    const g = goals.find((x) => x.id === id)
    if (g) setType(g.suggested_type) // prefill suggested type, still overridable
  }

  const handleSave = async () => {
    if (saving) return
    setSaving(true)
    try {
      await createLeadActivity(leadId, { type, due_date: dueDate || null, notes: notes || null, goal_id: goalId || null })
      toast.success('Aktion geplant.')
      onAdded()
    } catch {
      toast.error('Konnte nicht geplant werden.')
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={onClose} />
      <div className="relative bg-surface-high rounded-xl shadow-elev-3 p-7 max-w-[420px] w-full mx-4 animate-md-scale">
        <h3 className="text-xl font-semibold text-text mb-5">Nächste Aktion planen</h3>
        {goals.length > 0 && (
          <div className="mb-4">
            <label className="block text-xs text-text-muted mb-2">Akquise-Ziel (optional)</label>
            <select value={goalId} onChange={(e) => pickGoal(e.target.value)} className="w-full">
              <option value="">— kein Ziel —</option>
              {goals.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-text-muted mb-2">Aktion</label>
            <select value={type} onChange={(e) => setType(e.target.value as RainmakerActivityType)} className="w-full">
              {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{ACTIVITY_TYPE_LABELS[t]}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-2">Fällig am</label>
            <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="w-full" />
          </div>
        </div>
        <label className="block text-xs text-text-muted mb-2 mt-4">Notiz (optional)</label>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className="w-full" placeholder="Worum geht's?" />
        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="btn-secondary" disabled={saving}>Abbrechen</button>
          <button onClick={handleSave} className="btn-primary" disabled={!dueDate || saving}>
            {saving ? 'Speichern…' : 'Planen'}
          </button>
        </div>
      </div>
    </div>
  )
}
