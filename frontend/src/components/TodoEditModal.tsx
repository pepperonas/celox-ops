import { useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import { updateTodo } from '../api/todos'
import AutocompleteInput from './AutocompleteInput'
import Select from './Select'
import TodoRefPicker, { type TodoRef } from './TodoRefPicker'
import type { Todo, TodoPriority } from '../types'

interface Props {
  todo: Todo
  /** Bezug ist durch die Seite vorgegeben (Kunden-/Lead-Detail) → Picker aus. */
  scoped?: boolean
  onClose: () => void
  onSaved: () => void
}

function refOf(todo: Todo): TodoRef | null {
  if (todo.customer_id) return { customer_id: todo.customer_id, lead_id: null, label: todo.customer_name || 'Kunde' }
  if (todo.lead_id) return { customer_id: null, lead_id: todo.lead_id, label: todo.lead_name || 'Lead' }
  return null
}

/** Bearbeiten eines To-dos (Titel, Bezug, Fälligkeit, Priorität, Notizen).
 *  createPortal: `.page-enter` transformiert den Vorfahren (Repo-Regel). */
export default function TodoEditModal({ todo, scoped, onClose, onSaved }: Props) {
  const [title, setTitle] = useState(todo.title)
  const [ref, setRef] = useState<TodoRef | null>(refOf(todo))
  const [due, setDue] = useState(todo.due_date ?? '')
  const [priority, setPriority] = useState<TodoPriority>(todo.priority)
  const [notes, setNotes] = useState(todo.notes ?? '')
  const [saving, setSaving] = useState(false)

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    const clean = title.trim()
    if (!clean) return
    setSaving(true)
    try {
      await updateTodo(todo.id, {
        title: clean,
        notes: notes.trim() || null,
        due_date: due || null,
        priority,
        // Bei vorgegebenem Bezug den bestehenden nicht anfassen.
        ...(scoped ? {} : { customer_id: ref?.customer_id ?? null, lead_id: ref?.lead_id ?? null }),
      })
      toast.success('To-do gespeichert.')
      onSaved()
      onClose()
    } catch {
      toast.error('Speichern fehlgeschlagen.')
    }
    setSaving(false)
  }

  return createPortal(
    <div
      className="fixed inset-0 bg-black/85 flex items-center justify-center z-50 p-4"
      onClick={() => !saving && onClose()}
    >
      <form
        onSubmit={save}
        onClick={(e) => e.stopPropagation()}
        className="bg-surface border border-border rounded-dialog p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto animate-modal-in space-y-4"
      >
        <h3 className="text-lg font-semibold text-text">To-do bearbeiten</h3>

        <div>
          <label className="block text-xs text-text-muted mb-2">Aufgabe</label>
          <AutocompleteInput
            name="todo-title"
            field="todo"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Was ist zu tun?"
          />
        </div>

        {!scoped && (
          <div>
            <label className="block text-xs text-text-muted mb-2">Bezug (Kunde oder Lead)</label>
            <TodoRefPicker value={ref} onChange={setRef} />
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="todo-edit-due" className="block text-xs text-text-muted mb-2">Fällig am</label>
            <input
              id="todo-edit-due"
              type="date"
              value={due}
              onChange={(e) => setDue(e.target.value)}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-2">Priorität</label>
            <Select
              value={priority}
              onChange={(e) => setPriority(e.target.value as TodoPriority)}
              aria-label="Priorität"
              options={[
                { value: 'niedrig', label: 'Niedrig' },
                { value: 'normal', label: 'Normal' },
                { value: 'hoch', label: 'Hoch' },
              ]}
            />
          </div>
        </div>

        <div>
          <label htmlFor="todo-edit-notes" className="block text-xs text-text-muted mb-2">Notizen</label>
          <textarea
            id="todo-edit-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="Kontext, Details…"
            className="w-full resize-y"
          />
        </div>

        <div className="flex justify-end gap-3 pt-1">
          <button type="button" onClick={onClose} disabled={saving} className="btn-secondary">Abbrechen</button>
          <button type="submit" disabled={saving || !title.trim()} className="btn-primary">
            {saving ? 'Speichern…' : 'Speichern'}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  )
}
