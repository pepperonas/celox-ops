import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { createTodo, deleteTodo, getTodos, toggleTodo, updateTodo } from '../api/todos'
import { toastWithUndo } from '../utils/undoToast'
import { dueLabel, groupTodos } from '../utils/todoGroups'
import AutocompleteInput from './AutocompleteInput'
import TodoRefPicker, { type TodoRef } from './TodoRefPicker'
import type { Todo, TodoPriority } from '../types'

const PRIORITY_DOT: Record<TodoPriority, string> = {
  hoch: 'bg-danger',
  normal: 'bg-accent',
  niedrig: 'bg-border',
}

const PRIORITY_LABEL: Record<TodoPriority, string> = {
  hoch: 'Hoch', normal: 'Normal', niedrig: 'Niedrig',
}

interface Props {
  /** Vorbelegter Bezug — dann entfällt der Bezugs-Picker (Kunden-/Lead-Detail). */
  customerId?: string
  leadId?: string
  /** Überschrift ausblenden (wenn die Seite selbst schon eine hat). */
  hideHeading?: boolean
  onCountChange?: (openCount: number) => void
}

export default function TodoList({ customerId, leadId, hideHeading, onCountChange }: Props) {
  const [todos, setTodos] = useState<Todo[]>([])
  const [loading, setLoading] = useState(true)
  const [showDone, setShowDone] = useState(false)
  const [title, setTitle] = useState('')
  const [ref, setRef] = useState<TodoRef | null>(null)
  const [due, setDue] = useState('')
  const [priority, setPriority] = useState<TodoPriority>('normal')
  const [saving, setSaving] = useState(false)
  const scoped = Boolean(customerId || leadId)

  const load = useCallback(async () => {
    try {
      const res = await getTodos({
        customer_id: customerId,
        lead_id: leadId,
        page_size: 500,
      })
      setTodos(res.items)
      onCountChange?.(res.items.filter((t) => t.status === 'offen').length)
    } catch {
      toast.error('To-dos konnten nicht geladen werden.')
    }
    setLoading(false)
  }, [customerId, leadId, onCountChange])

  useEffect(() => { load() }, [load])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    const clean = title.trim()
    if (!clean) return
    setSaving(true)
    try {
      await createTodo({
        title: clean,
        customer_id: customerId ?? ref?.customer_id ?? null,
        lead_id: leadId ?? ref?.lead_id ?? null,
        due_date: due || null,
        priority,
      })
      setTitle(''); setRef(null); setDue(''); setPriority('normal')
      await load()
    } catch {
      toast.error('To-do konnte nicht angelegt werden.')
    }
    setSaving(false)
  }

  const handleToggle = async (todo: Todo) => {
    const done = todo.status === 'offen'
    // Optimistisch: das Abhaken muss sich sofort anfühlen.
    setTodos((prev) => prev.map((t) => (t.id === todo.id ? { ...t, status: done ? 'erledigt' : 'offen' } : t)))
    try {
      await toggleTodo(todo.id, done)
      await load()
      if (done) {
        toastWithUndo('Erledigt.', async () => {
          await toggleTodo(todo.id, false)
          await load()
        })
      }
    } catch {
      toast.error('Status konnte nicht geändert werden.')
      await load()
    }
  }

  const handleDelete = async (todo: Todo) => {
    try {
      await deleteTodo(todo.id)
      await load()
      toastWithUndo('To-do gelöscht.', async () => {
        await createTodo({
          title: todo.title, notes: todo.notes, customer_id: todo.customer_id,
          lead_id: todo.lead_id, due_date: todo.due_date, priority: todo.priority,
        })
        await load()
      })
    } catch {
      toast.error('Löschen fehlgeschlagen.')
    }
  }

  const cyclePriority = async (todo: Todo) => {
    const next: Record<TodoPriority, TodoPriority> = { niedrig: 'normal', normal: 'hoch', hoch: 'niedrig' }
    const value = next[todo.priority]
    setTodos((prev) => prev.map((t) => (t.id === todo.id ? { ...t, priority: value } : t)))
    try {
      await updateTodo(todo.id, { priority: value })
      await load()
    } catch {
      toast.error('Priorität konnte nicht geändert werden.')
      await load()
    }
  }

  const visible = showDone ? todos : todos.filter((t) => t.status === 'offen')
  const groups = groupTodos(visible)
  const openCount = todos.filter((t) => t.status === 'offen').length
  const doneCount = todos.length - openCount

  return (
    <div>
      {!hideHeading && (
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h3 className="text-sm font-semibold text-text">
            To-dos {openCount > 0 && <span className="text-text-muted font-normal">({openCount} offen)</span>}
          </h3>
          {doneCount > 0 && (
            <button
              onClick={() => setShowDone((v) => !v)}
              className="text-xs text-text-muted hover:text-text transition-colors"
            >
              {showDone ? 'Erledigte ausblenden' : `Erledigte anzeigen (${doneCount})`}
            </button>
          )}
        </div>
      )}

      {/* Schnellerfassung — Enter legt an */}
      <form onSubmit={handleAdd} className="bg-surface border border-border rounded-card p-3 mb-4">
        <div className="flex flex-wrap gap-2 items-start">
          <div className="flex-1 min-w-[200px]">
            <AutocompleteInput
              name="todo-title"
              field="todo"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Was ist zu tun?"
              compact
            />
          </div>
          {!scoped && (
            <div className="w-full sm:w-56">
              <TodoRefPicker value={ref} onChange={setRef} compact />
            </div>
          )}
          <input
            type="date"
            value={due}
            onChange={(e) => setDue(e.target.value)}
            aria-label="Fällig am"
            className="w-full sm:w-40 text-sm"
          />
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as TodoPriority)}
            aria-label="Priorität"
            className="w-full sm:w-28 text-sm"
          >
            <option value="niedrig">Niedrig</option>
            <option value="normal">Normal</option>
            <option value="hoch">Hoch</option>
          </select>
          <button type="submit" disabled={saving || !title.trim()} className="btn-primary text-sm">
            {saving ? '…' : 'Hinzufügen'}
          </button>
        </div>
      </form>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <div key={i} className="h-12 md-skeleton rounded-card" />)}
        </div>
      ) : groups.length === 0 ? (
        <div className="bg-surface border border-border rounded-card px-4 py-10 text-center">
          <p className="text-text-muted text-sm">
            {todos.length === 0
              ? 'Noch keine To-dos — trag oben ein, was ansteht.'
              : '🎉 Alles erledigt.'}
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {groups.map((group) => (
            <div key={group.key}>
              <p className={`text-xs font-semibold mb-2 ${group.key === 'overdue' ? 'text-danger' : 'text-text-muted'}`}>
                {group.label} ({group.items.length})
              </p>
              <div className="space-y-2">
                {group.items.map((todo) => {
                  const done = todo.status === 'erledigt'
                  const refName = todo.customer_name || todo.lead_name
                  return (
                    <div
                      key={todo.id}
                      className={`bg-surface border rounded-card p-3 flex items-start gap-3 transition-colors duration-short ${
                        group.key === 'overdue' ? 'border-danger/40' : 'border-border'
                      } ${done ? 'opacity-60' : ''}`}
                    >
                      <button
                        onClick={() => handleToggle(todo)}
                        aria-label={done ? 'Wieder öffnen' : 'Als erledigt markieren'}
                        aria-pressed={done}
                        className={`mt-0.5 w-5 h-5 shrink-0 rounded-full border-2 grid place-items-center transition-colors duration-short ${
                          done ? 'bg-success border-success text-bg' : 'border-text-muted hover:border-accent'
                        }`}
                      >
                        {done && (
                          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </button>

                      <div className="flex-1 min-w-0">
                        <p className={`text-sm text-text break-words ${done ? 'line-through' : ''}`}>{todo.title}</p>
                        <div className="flex flex-wrap items-center gap-2 mt-1">
                          {todo.due_date && (
                            <span className={`text-xs ${group.key === 'overdue' ? 'text-danger' : 'text-text-muted'}`}>
                              {dueLabel(todo.due_date)}
                            </span>
                          )}
                          {refName && !scoped && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-surface-2 text-text-muted truncate max-w-[180px]">
                              {todo.customer_name ? '🏢' : '🎯'} {refName}
                            </span>
                          )}
                          {todo.notes && <span className="text-xs text-text-muted truncate max-w-[240px]">{todo.notes}</span>}
                        </div>
                      </div>

                      <button
                        onClick={() => cyclePriority(todo)}
                        title={`Priorität: ${PRIORITY_LABEL[todo.priority]} — klicken zum Wechseln`}
                        aria-label={`Priorität ${PRIORITY_LABEL[todo.priority]} ändern`}
                        className="mt-1.5 shrink-0"
                      >
                        <span className={`block w-2.5 h-2.5 rounded-full ${PRIORITY_DOT[todo.priority]}`} />
                      </button>

                      <button
                        onClick={() => handleDelete(todo)}
                        aria-label="To-do löschen"
                        className="text-text-muted hover:text-danger transition-colors shrink-0"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {hideHeading && doneCount > 0 && (
        <button
          onClick={() => setShowDone((v) => !v)}
          className="mt-4 text-xs text-text-muted hover:text-text transition-colors"
        >
          {showDone ? 'Erledigte ausblenden' : `Erledigte anzeigen (${doneCount})`}
        </button>
      )}
    </div>
  )
}
