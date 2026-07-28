// KI-Vorschläge für To-dos zu einem Kunden — Vorschau, Auswahl, dann anlegen.
//
// Angelegt wird über das bestehende `POST /api/todos`: die Werte darf der Client
// dort ohnehin frei setzen, es entsteht also kein neuer Schreibpfad und kein
// Rechtezuwachs. Nichts wird automatisch geschrieben — jeder Vorschlag braucht
// einen Haken.
import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import {
  suggestCustomerTodos,
  type TodoSuggestion,
  type TodoSuggestionResponse,
} from '../../api/customerTodoAi'
import { createTodo } from '../../api/todos'
import Select from '../../components/Select'
import { formatCurrency } from '../../utils/formatters'
import type { TodoPriority } from '../../types'

const PRIORITY_OPTIONS = [
  { value: 'niedrig', label: 'Niedrig' },
  { value: 'normal', label: 'Normal' },
  { value: 'hoch', label: 'Hoch' },
]

interface Props {
  customerId: string
  customerName: string
  onClose: () => void
  onCreated: (count: number) => void
}

type Draft = TodoSuggestion & { picked: boolean }

export default function TodoSuggestionsDialog({
  customerId, customerName, onClose, onCreated,
}: Props) {
  const [res, setRes] = useState<TodoSuggestionResponse | null>(null)
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hint, setHint] = useState('')
  const [showIgnored, setShowIgnored] = useState(false)

  const run = async (opts: { force?: boolean } = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await suggestCustomerTodos(customerId, { ...opts, hint })
      setRes(data)
      // Duplikate nicht vorauswählen — sie stehen schon als offenes To-do.
      setDrafts(data.suggestions.map((s) => ({ ...s, picked: !s.duplicate })))
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      setError(detail || 'Die KI-Ableitung ist fehlgeschlagen.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void run() }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !loading && !saving) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [loading, saving, onClose])

  const pickedCount = useMemo(() => drafts.filter((d) => d.picked).length, [drafts])

  const patch = (index: number, change: Partial<Draft>) =>
    setDrafts((prev) => prev.map((d, i) => (i === index ? { ...d, ...change } : d)))

  const commit = async () => {
    const chosen = drafts.filter((d) => d.picked)
    if (!chosen.length || saving) return
    setSaving(true)
    let created = 0
    let failed = 0
    for (const draft of chosen) {
      try {
        await createTodo({
          title: draft.title,
          notes: draft.notes || undefined,
          customer_id: customerId,
          due_date: draft.due_date || null,
          priority: draft.priority as TodoPriority,
        })
        created++
      } catch {
        failed++
      }
    }
    setSaving(false)
    if (created) {
      toast.success(`${created} To-do${created === 1 ? '' : 's'} angelegt`
        + (failed ? `, ${failed} fehlgeschlagen.` : '.'))
      onCreated(created)
      onClose()
    } else {
      toast.error('Anlegen fehlgeschlagen.')
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={() => { if (!loading && !saving) onClose() }} />
      <div className="relative bg-surface-high rounded-dialog shadow-elev-3 p-5 sm:p-7
                      max-w-[820px] w-full mx-4 animate-modal-in max-h-[88vh] flex flex-col">
        <h3 className="text-lg font-semibold text-text mb-1">
          To-dos für {customerName} vorschlagen
        </h3>
        <p className="text-xs text-text-muted mb-4">
          Abgeleitet aus Stammdaten, Notizen, Aufträgen, Verträgen, Rechnungen,
          Kontakthistorie, Dokumenten und — falls vorhanden — der Lead-Vorgeschichte.
          Jeder Vorschlag trägt ein <strong className="text-text">Zitat</strong> aus
          den Kundendaten; ohne Beleg wird er verworfen. Was sich schon aus den
          Regeln ergibt (überfällige Rechnung, auslaufender Vertrag …), wird
          bewusst nicht wiederholt. <strong className="text-text">Angelegt wird
          nur, was du anhakst.</strong>
        </p>

        <div className="mb-4">
          <label htmlFor="todo-ai-hint" className="block text-xs text-text-muted mb-1.5">
            Eigener Hinweis (optional) — schlägt die Kundendaten
          </label>
          <input
            id="todo-ai-hint"
            value={hint}
            onChange={(e) => setHint(e.target.value)}
            placeholder="z. B. Fokus auf Wartungsvertrag, Budget steht bis Oktober"
            className="input-field"
            disabled={loading || saving}
          />
        </div>

        {loading && (
          <div className="py-10 text-center text-sm text-text-muted">
            <span className="inline-block w-4 h-4 rounded-full border-2 border-accent
                             border-t-transparent animate-spin mr-2 align-middle" />
            Kundendaten werden ausgewertet…
          </div>
        )}

        {error && <p className="text-sm text-danger py-4">{error}</p>}

        {res && !loading && (
          <>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-3 text-xs text-text-muted">
              <span>{drafts.length} Vorschlag{drafts.length === 1 ? '' : 'e'}</span>
              {res.cached && <span>· aus dem Zwischenspeicher (0 €)</span>}
              {!res.cached && <span>· Kosten {formatCurrency(res.run.cost_eur)}</span>}
              {res.budget.warn && (
                <span className="text-warning">
                  · Budget zu {Math.round(100 * res.budget.spent_eur / res.budget.budget_eur)} % genutzt
                </span>
              )}
              <button
                onClick={() => run({ force: true })}
                disabled={saving}
                className="md-state ml-auto text-accent rounded-xs px-1"
                title="Erneut ableiten, ohne Zwischenspeicher — kostet einen KI-Aufruf"
              >
                ✨ Neu ableiten
              </button>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto space-y-3">
              {drafts.length === 0 && (
                <p className="text-sm text-text-muted py-6 text-center">
                  Aus den vorliegenden Daten ergibt sich derzeit keine belegbare
                  Aufgabe. Das ist ein gültiges Ergebnis — kein Füllmaterial.
                </p>
              )}
              {drafts.map((draft, index) => (
                <div key={index}
                     className={`border rounded-card p-3 ${draft.picked
                       ? 'border-accent/50 bg-surface' : 'border-border bg-surface/60'}`}>
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={draft.picked}
                      onChange={() => patch(index, { picked: !draft.picked })}
                      aria-label={`${draft.title} übernehmen`}
                      className="mt-1 cursor-pointer"
                    />
                    <div className="flex-1 min-w-0">
                      <input
                        value={draft.title}
                        onChange={(e) => patch(index, { title: e.target.value })}
                        aria-label="Titel"
                        className="input-field !py-1.5 mb-2"
                      />
                      {draft.notes && (
                        <p className="text-xs text-text-muted mb-2 break-words">{draft.notes}</p>
                      )}
                      <div className="flex flex-wrap items-end gap-2 mb-2">
                        <div>
                          <label className="block text-[10px] text-text-muted mb-1">Priorität</label>
                          <Select
                            compact
                            value={draft.priority}
                            options={PRIORITY_OPTIONS}
                            onChange={(e) => patch(index, { priority: e.target.value })}
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] text-text-muted mb-1">Fällig</label>
                          <input
                            type="date"
                            value={draft.due_date || ''}
                            onChange={(e) => patch(index, { due_date: e.target.value || null })}
                            className="input-field !py-1.5 w-auto"
                          />
                        </div>
                        {draft.duplicate && (
                          <span className="text-[10px] text-warning self-center"
                                title="Ein offenes To-do mit diesem Titel existiert schon">
                            steht schon als To-do offen
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-text-muted border-l-2 border-border pl-2
                                    break-words">
                        Beleg: „{draft.evidence}“
                      </p>
                    </div>
                  </div>
                </div>
              ))}

              {res.ignored.length > 0 && (
                <details open={showIgnored}
                         onToggle={(e) => setShowIgnored((e.target as HTMLDetailsElement).open)}
                         className="border border-border rounded-card">
                  <summary className="px-3 py-2 text-xs text-text-muted cursor-pointer md-state">
                    {res.ignored.length} nicht übernommen — Grund anzeigen
                  </summary>
                  <ul className="px-3 pb-2 space-y-0.5">
                    {res.ignored.map((line, i) => (
                      <li key={i} className="text-[11px] text-text-muted">• {line}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          </>
        )}

        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="btn-secondary" disabled={saving}>
            Abbrechen
          </button>
          {drafts.length > 0 && (
            <button onClick={commit} className="btn-primary"
                    disabled={pickedCount === 0 || saving}>
              {saving ? 'Lege an…' : `${pickedCount} übernehmen`}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
